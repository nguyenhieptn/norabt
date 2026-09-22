"""Incremental, rate-limited polling for the 30 selected copy-trading bots.

Design constraints this module exists to satisfy (decided outside this
module, not open for revision here):

1. All 30 bots share one OKX `copytrading` request budget (5 req / 2s per
   IP), via a single `TokenBucket` -- see `ratelimit.py`.
2. Every round costs exactly one request per bot (`public-current-
   subpositions`). A second request (`public-subpositions-history`, first
   page only) is spent *only* on a bot whose open-position set just shrank,
   to fetch the trade(s) that just closed. Re-crawling full history every
   round is not an option -- see the task notes this was built from.
3. Every write into the existing dataset goes through `store.write_atomic`,
   so step 2/3 (which do a plain `json.load`) never observe a half-written
   file.

The other property this module has to hold on its own: a bad OKX response
must never look like "the bot has no positions/trades now". OKX answering
with `code == "0"` and an empty *current positions* list is a real, meaningful
state (the bot is flat) and is trusted. What is never trusted is anything
that fails to parse as the expected shape (a transport/API error, a payload
that isn't a list, a row missing the id that identifies it) -- those are
treated as a failed poll: the old file is left untouched and the round moves
on to the next bot.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.live.ratelimit import TokenBucket
from Agent.backend.live.store import (
    BotTarget,
    LiveState,
    find_bot_dir,
    fingerprint_positions,
    load_bot_targets,
    load_state,
    read_json,
    save_state,
    write_atomic,
)
from Agent.backend.bot.mcp.inference.public_signals import SubPositionClock
from Agent.backend.external.okx.client import OkxClient, OkxError

CURRENT_POSITIONS_PATH = "/api/v5/copytrading/public-current-subpositions"
HISTORY_PATH = "/api/v5/copytrading/public-subpositions-history"
HISTORY_PAGE_SIZE = 100  # first page only, per the "no re-crawl" decision

# >=5 consecutive failed polls -- explicit in the task's requirements -- is
# the line between "had a bad round" (data is a little old, still usable) and
# "STALE" (must not be presented as fresh anywhere).
DEFAULT_STALE_AFTER = 5


def _owned_by(rows: Sequence[Dict[str, Any]], code: str) -> List[Dict[str, Any]]:
    """Drop any row OKX attached to a different uniqueCode than the one asked for.

    Mirrors crawl_bots.py's own `owned_by`: some OKX endpoints have been seen
    to ignore a filter and answer with another trader's row, and a live
    poller writing that into this bot's file would silently corrupt it.
    """
    kept = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        owner = row.get("uniqueCode")
        if owner in (None, "", code):
            kept.append(row)
    return kept


def _valid_position_rows(raw: Any, code: str) -> Optional[List[Dict[str, Any]]]:
    """None means "untrustworthy response"; a list (possibly empty) means trust it.

    A well-formed OKX answer for public-current-subpositions is a JSON array
    -- empty when the bot is flat, non-empty otherwise. Anything else (the
    client raised, or `data` was missing/not a list) cannot be distinguished
    from "the bot is flat" by shape alone, so it must never be treated as one.
    """
    if not isinstance(raw, list):
        return None
    rows = _owned_by(raw, code)
    # A row with no subPosId cannot be tracked (it has no identity to fingerprint,
    # dedupe, or diff against), so it is dropped rather than kept half-broken.
    return [row for row in rows if row.get("subPosId")]


def _valid_history_rows(raw: Any, code: str) -> Optional[List[Dict[str, Any]]]:
    if not isinstance(raw, list):
        return None
    rows = _owned_by(raw, code)
    # closeTime is what LedgerParser rejects a trade on if missing, so a row
    # without it is not worth carrying into trade_list.json at all.
    return [row for row in rows if row.get("subPosId") and row.get("closeTime")]


def _attach_derived_open_time(position: Dict[str, Any]) -> Dict[str, Any]:
    """Fill in an open time from the id when OKX didn't publish one -- same
    trick crawl_bots.py uses (SUBPOS_ID_SNOWFLAKE), so a position crawled
    once and then only ever seen via the live poller still carries a time."""
    if position.get("openTime"):
        return position
    decoded = SubPositionClock.open_time_ms(position.get("subPosId"))
    if decoded:
        position = dict(position)
        position["derived_open_time"] = decoded
        position["derived_open_time_method"] = "SUBPOS_ID_SNOWFLAKE"
    return position


def _carry_forward_attribution(
    new_positions: List[Dict[str, Any]], previous_positions: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Keep a still-open position's instrument attribution instead of losing it.

    The live poller deliberately never runs the price-based instrument
    attributor (that would mean extra market-data requests every round, out
    of scope for this poller). A position that was already open at the last
    full crawl carries a real `attribution`/`inferred_instrument` computed
    there; if it is still open now, that evidence is still true and must not
    be dropped just because this round's raw OKX row does not repeat it. A
    brand-new position genuinely has no attribution yet -- that's honest, and
    the next full crawl_bots.py run will compute it.
    """
    by_id = {
        str(p.get("subPosId")): p
        for p in previous_positions
        if isinstance(p, dict) and p.get("subPosId")
    }
    merged = []
    for position in new_positions:
        prior = by_id.get(str(position.get("subPosId")))
        if prior and not position.get("instId") and not position.get("attribution"):
            position = dict(position)
            if prior.get("attribution"):
                position["attribution"] = prior["attribution"]
            if prior.get("inferred_instrument"):
                position["inferred_instrument"] = prior["inferred_instrument"]
            if prior.get("cost_model_round_trip_rate") is not None:
                position["cost_model_round_trip_rate"] = prior[
                    "cost_model_round_trip_rate"
                ]
        merged.append(position)
    return merged


def _inference_stats(positions: List[Dict[str, Any]]) -> Dict[str, int]:
    stats = {"decoded_time": 0, "determined": 0, "narrowed": 0, "outside": 0}
    for position in positions:
        if position.get("derived_open_time_method"):
            stats["decoded_time"] += 1
        verdict = (position.get("attribution") or {}).get("verdict")
        if verdict == "DETERMINED":
            stats["determined"] += 1
        elif verdict == "NARROWED":
            stats["narrowed"] += 1
        elif verdict == "OUTSIDE_LEDGER_UNIVERSE":
            stats["outside"] += 1
    return stats


@dataclass
class RescoreOutcome:
    """What changed about the QC verdict after re-scoring one bot."""

    unique_code: str
    assessment_path: str
    old_risk_score: Optional[float]
    new_risk_score: Optional[float]
    old_tier: Optional[str]
    new_tier: Optional[str]
    old_verdict: Optional[str]
    new_verdict: Optional[str]

    @property
    def tier_changed(self) -> bool:
        return bool(self.old_tier) and self.old_tier != self.new_tier

    @property
    def verdict_changed(self) -> bool:
        return bool(self.old_verdict) and self.old_verdict != self.new_verdict


@dataclass
class BotChange:
    """Result of polling one bot for one round.

    Two different things can happen to a bot in a round, and this fix exists
    specifically to keep them from being collapsed into one ambiguous flag
    (that collapse is exactly what used to trigger a wasted re-score on
    every bot that merely opened a new position -- see the module docstring
    and the "chốt lệnh" analysis-scope decision it references):

    - `positions_changed`: the OPEN position set moved this round (a
      subPosId appeared and/or disappeared from public-current-
      subpositions). This is collected/reported every round regardless --
      diffing it is the cheap, 1-request/bot way to notice a position that
      just closed (see module docstring point 2) -- but on its own it says
      nothing about whether the *analysis* (which only ever looks at closed
      trades) has anything new to work with.
    - `new_closed_count`: how many rows were actually merged into
      `closed_trades` THIS round. Since the analysis is scoped to closed
      trades only, this is the one and only fact that can move any number
      it computes, so it is the one and only condition allowed to trigger a
      re-score (see poll_once).
    """

    target: BotTarget
    ok: bool
    positions_changed: bool = False
    opened_ids: List[str] = field(default_factory=list)
    closed_ids: List[str] = field(default_factory=list)
    new_closed_count: int = 0
    open_positions_count: Optional[int] = None
    error: Optional[str] = None
    stale: bool = False
    # Set when no real dataset directory could be found for this bot's
    # uniqueCode at all (see find_bot_dir). Distinct from a normal `error`:
    # this bot was never crawled, not merely failing to poll right now, and
    # the round must skip it without writing or creating anything.
    not_crawled: bool = False
    rescore: Optional[RescoreOutcome] = None
    rescore_error: Optional[str] = None

    @property
    def changed(self) -> bool:
        """Backward-compatible alias for `positions_changed`.

        Kept only because `run_live.py` (its CLI summary text) is outside
        this fix's file scope and still reads `.changed`. It intentionally
        mirrors the raw "did the open-position set move" signal, NOT the
        re-score trigger -- use `new_closed_count` for that. Do not add new
        reads of this property inside this module: it is exactly the
        ambiguous single-flag name this fix removes internally.
        """
        return self.positions_changed


def _format_change_vi(change: BotChange) -> str:
    """One compact Vietnamese line describing a round for one bot.

    A verdict change is the single most actionable fact in this whole
    system (a bot silently flipping TIỀM NĂNG -> NGUY HIỂM is exactly what
    the live poller exists to catch quickly), so it is never buried at the
    end of the line -- it gets its own loud marker.

    Three distinct "no re-score happened" outcomes exist and must read
    differently to the operator, or "the bot is quiet" becomes
    indistinguishable from "the bot is busy but that alone never re-scores
    it" -- which is the exact confusion that hid the wasted-rescore problem
    this fix addresses:
      1. nothing changed at all this round;
      2. the open position set changed, but no trade has closed yet, so
         there is nothing new for the (closed-trades-only) analysis to see;
      3. a trade newly closed, so a re-score was actually attempted.
    """
    target = change.target
    label = f"{target.name} ({target.unique_code})"
    if change.not_crawled:
        return f"{label}: NOT_CRAWLED - {change.error}"
    if not change.ok:
        tag = "STALE" if change.stale else "error"
        return f"{label}: {tag} - {change.error}"

    if not change.positions_changed and change.new_closed_count == 0:
        # Case 1: genuinely nothing happened.
        return f"{label}: nothing changed, skipping scoring"

    if change.new_closed_count == 0:
        # Case 2: positions_changed is True here (that's the only other way
        # to reach this branch) -- something opened and/or left the open
        # set, but it has not yet been confirmed into closed_trades (a
        # just-closed position sits in `pending` for a round or more, see
        # module docstring point 2). Per the closed-trades-only analysis
        # scope, there is nothing yet worth re-scoring over.
        bits = []
        if change.opened_ids:
            bits.append(f"opened {len(change.opened_ids)} more position(s)")
        if change.closed_ids:
            bits.append(f"closed {len(change.closed_ids)} position(s) (pending history match)")
        detail = ", ".join(bits) if bits else "position set changed"
        return f"{label}: {detail}, NO new closed trade yet -> skipping scoring"

    # Case 3: at least one trade newly closed this round -- the only case a
    # re-score was actually attempted (see poll_once).
    bits = []
    if change.opened_ids:
        bits.append(f"opened {len(change.opened_ids)} more position(s)")
    if change.closed_ids:
        bits.append(f"closed {len(change.closed_ids)} position(s)")
    bits.append(f"merged {change.new_closed_count} new trade(s) into the ledger")
    detail = ", ".join(bits)

    if change.rescore is None:
        suffix = f" | rescoring failed: {change.rescore_error}"
        return f"{label}: {detail}{suffix}"

    outcome = change.rescore
    old_score = (
        "?" if outcome.old_risk_score is None else f"{outcome.old_risk_score:.1f}"
    )
    new_score = (
        "?" if outcome.new_risk_score is None else f"{outcome.new_risk_score:.1f}"
    )
    score_bit = f"risk score {old_score} -> {new_score}"
    tier_bit = f"{outcome.old_tier or '?'} -> {outcome.new_tier}"
    line = f"{label}: {detail} | {score_bit} | tier {tier_bit}"
    if outcome.tier_changed:
        line += f"  *** TIER CHANGED: {outcome.old_tier} -> {outcome.new_tier} ***"
    elif outcome.verdict_changed:
        line += (
            f"  *** VERDICT CHANGED: {outcome.old_verdict} -> {outcome.new_verdict} ***"
        )
    return line


class LivePoller:
    """Polls the 30 selected bots incrementally and re-scores whichever bot
    got a newly closed trade this round (never merely a changed open
    position -- see BotChange and poll_once)."""

    def __init__(
        self,
        targets: Optional[List[BotTarget]] = None,
        data_dir: Optional[Any] = None,
        client: Optional[Any] = None,
        rate_limiter: Optional[TokenBucket] = None,
        stale_after: int = DEFAULT_STALE_AFTER,
        evaluation_mode: EvaluationMode = EvaluationMode.SNAPSHOT,
        rescore_fn: Optional[Callable[[BotTarget], Optional[RescoreOutcome]]] = None,
        progress: Callable[[str], None] = print,
        now_fn: Callable[[], int] = lambda: int(time.time() * 1000),
    ) -> None:
        from Agent.backend.live.store import default_data_dir

        self.data_dir = data_dir if data_dir is not None else default_data_dir()
        self.targets = (
            targets if targets is not None else load_bot_targets(self.data_dir)
        )
        self.client = client or OkxClient()
        self.rate_limiter = rate_limiter or TokenBucket()
        self.stale_after = stale_after
        # Giữ lại cho nơi gọi đọc/ghi; phần chấm điểm nay do
        # `run_report.rescore_one_bot_complete` lo, và hàm đó tự chọn
        # SNAPSHOT -- cùng chế độ lượt chấm cả đàn dùng, nên poller
        # không còn tự dựng cohort service với một chế độ riêng nữa.
        self.evaluation_mode = evaluation_mode
        self.progress = progress
        self.now_fn = now_fn
        # Overridable so tests can count/stub calls without paying for a real
        # Monte Carlo run; the default wires up the real QC pipeline.
        self._rescore_fn = rescore_fn or self._rescore_bot

    # -- one bot -----------------------------------------------------------

    def poll_bot(self, target: BotTarget) -> BotChange:
        # Resolve the bot's REAL dataset directory by uniqueCode before doing
        # anything else -- not target.bot_dir(), which is only the slot
        # bot_selection.json assigned it and can point at an instrument the
        # bot doesn't actually trade (see find_bot_dir's docstring). This is
        # a local, no-network lookup, so it costs nothing to do first.
        bot_dir = find_bot_dir(self.data_dir, target.unique_code)
        if bot_dir is None:
            # Fail-closed per design: never invent a path and never create a
            # directory here. No state load/save either -- this bot genuinely
            # has no crawled data yet, so there is nothing local to update,
            # and no OKX call is spent on a bot with nowhere to write results.
            return BotChange(
                target=target,
                ok=False,
                not_crawled=True,
                error=(
                    "no crawled data for this bot yet (directory "
                    f"bot_{target.unique_code} not found under any venue/asset)"
                ),
            )
        trade_list_path = bot_dir / "trade_list.json"
        # From here on, use the target resolved against its REAL data
        # location (data_venue/data_symbol) instead of the slot one -- this
        # is what _rescore_bot's scan() call needs, and BotChange.target is
        # what poll_once() hands to the rescore step (see LỖI 5 for why the
        # slot and the real location can differ).
        target = target.with_data_location(bot_dir)

        state = load_state(self.data_dir, target.unique_code)
        now = self.now_fn()

        self.rate_limiter.acquire()
        try:
            raw_positions = self.client.public_get(
                CURRENT_POSITIONS_PATH,
                {"uniqueCode": target.unique_code, "instType": "SWAP"},
            )
        except OkxError as exc:
            return self._record_failure(target, state, now, str(exc))

        positions = _valid_position_rows(raw_positions, target.unique_code)
        if positions is None:
            return self._record_failure(
                target,
                state,
                now,
                "current-positions response is invalid (not a list)",
            )

        existing_trade_list = read_json(trade_list_path) or {}
        existing_positions = existing_trade_list.get("open_positions") or []
        existing_closed = existing_trade_list.get("closed_trades") or []

        existing_open_ids = {
            str(p.get("subPosId")) for p in existing_positions if p.get("subPosId")
        }
        new_open_ids = {str(p.get("subPosId")) for p in positions}
        opened_ids = sorted(new_open_ids - existing_open_ids)
        closed_ids = sorted(existing_open_ids - new_open_ids)
        # This is only "did the open-position set move", never "should we
        # re-score" -- see BotChange's docstring. new_closed_count below is
        # the only signal poll_once is allowed to gate a re-score on.
        positions_changed = bool(opened_ids or closed_ids)

        positions = [_attach_derived_open_time(p) for p in positions]
        positions = _carry_forward_attribution(positions, existing_positions)

        pending = sorted(set(state.pending_close_subpos_ids) | set(closed_ids))
        new_closed_count = 0
        closed_trades = existing_closed
        last_close_ms = state.last_close_ms
        still_pending = pending

        if pending:
            self.rate_limiter.acquire()
            try:
                raw_history = self.client.public_get(
                    HISTORY_PATH,
                    {
                        "uniqueCode": target.unique_code,
                        "instType": "SWAP",
                        "limit": HISTORY_PAGE_SIZE,
                    },
                )
            except OkxError as exc:
                # Not fatal for the whole bot: the fresh open_positions below
                # are still good and get written; only the ledger merge is
                # deferred. `pending` stays as-is so the next round retries.
                self.progress(
                    f"  ! {target.name}: could not fetch history to merge the "
                    f"just-closed trade ({exc}), will retry next round"
                )
            else:
                history_rows = _valid_history_rows(raw_history, target.unique_code)
                if history_rows is None:
                    self.progress(
                        f"  ! {target.name}: history page returned is invalid, not "
                        "merged into the ledger this round (existing data kept unchanged)"
                    )
                else:
                    existing_ids = {
                        str(t.get("subPosId"))
                        for t in existing_closed
                        if t.get("subPosId")
                    }
                    pending_set = set(pending)
                    found = [
                        row
                        for row in history_rows
                        if str(row.get("subPosId")) in pending_set
                        and str(row.get("subPosId")) not in existing_ids
                    ]
                    if found:
                        # Newest-first, matching the existing file's ordering
                        # convention (page 1 of the history endpoint is the
                        # newest trades) -- new rows go in front, never replace.
                        closed_trades = found + list(existing_closed)
                        new_closed_count = len(found)
                        close_times = [
                            int(row["closeTime"])
                            for row in found
                            if str(row.get("closeTime") or "").isdigit()
                        ]
                        if close_times:
                            last_close_ms = max([last_close_ms or 0, *close_times])
                    found_ids = {str(row.get("subPosId")) for row in found}
                    still_pending = sorted(pending_set - found_ids)

        trade_list_payload = {
            "uniqueCode": target.unique_code,
            "open_positions_count": len(positions),
            "open_positions": positions,
            "closed_trades_count": len(closed_trades),
            "closed_trades": closed_trades,
            "ledger_truncated": existing_trade_list.get("ledger_truncated", False),
            "ledger_page_size": existing_trade_list.get(
                "ledger_page_size", HISTORY_PAGE_SIZE
            ),
            "positions_without_instrument": sum(
                1
                for p in positions
                if not p.get("instId") and not p.get("inferred_instrument")
            ),
            "inference": _inference_stats(positions),
            "provenance": {
                "crawled_at_ms": now,
                "source": "LIVE_POLLER_INCREMENTAL",
                "note": (
                    "open_positions is refreshed every round via "
                    "public-current-subpositions; closed_trades is only APPENDED to "
                    "(never re-crawled) when a just-closed position is detected, via "
                    "the first page of public-subpositions-history"
                ),
            },
        }
        write_atomic(trade_list_path, trade_list_payload)

        state.last_polled_ms = now
        state.last_success_ms = now
        state.position_fingerprint = fingerprint_positions(new_open_ids)
        state.last_close_ms = last_close_ms
        state.pending_close_subpos_ids = still_pending
        state.consecutive_errors = 0
        state.status = "OK"
        state.last_error = None
        save_state(self.data_dir, state)

        return BotChange(
            target=target,
            ok=True,
            positions_changed=positions_changed,
            opened_ids=opened_ids,
            closed_ids=closed_ids,
            new_closed_count=new_closed_count,
            open_positions_count=len(positions),
        )

    def _record_failure(
        self, target: BotTarget, state: LiveState, now: int, message: str
    ) -> BotChange:
        state.last_polled_ms = now
        state.consecutive_errors += 1
        state.last_error = message
        became_stale = state.consecutive_errors >= self.stale_after
        state.status = "STALE" if became_stale else state.status
        save_state(self.data_dir, state)
        if became_stale:
            self.progress(
                f"  !!! {target.name} ({target.unique_code}): STALE - "
                f"{state.consecutive_errors} consecutive failures, data is NO LONGER "
                f"considered fresh"
            )
        return BotChange(
            target=target,
            ok=False,
            error=message,
            stale=state.status == "STALE",
        )

    # -- scoring -------------------------------------------------------------

    def _rescore_bot(self, target: BotTarget) -> Optional[RescoreOutcome]:
        """Chấm lại MỘT bot rồi ghi đè `assessment.json` của nó.

        Uỷ THÁC toàn bộ phần chấm+ghi cho
        `Agent/backend/run_report.rescore_one_bot_complete` -- cùng đúng hàm
        mà nút "Re-analyze" trên web và lượt chấm cả đàn dùng. Trước đây chỗ
        này là bản cài ĐỘC LẬP thứ ba và nó đã trôi khỏi hai bản kia theo ba
        hướng cùng lúc:

          * tham số mô phỏng rơi vào mặc định của `scan` (5.000 lượt, tầm
            CỐ ĐỊNH 500 lệnh) thay vì 10.000 lượt / tầm = số lệnh bot thật
            sự đã đóng -- cùng một bot ra hai bộ số khác hẳn tuỳ đường nào
            chạm vào nó sau cùng;
          * gọi thẳng `build_assessment(row, ...)` mà KHÔNG có `extras`, nên
            `expert_assessment` bị ghi đè thành `None`: mỗi lượt poll thành
            công là một đoạn nhận định bị xoá, cùng với hồ sơ chiến lược,
            chuỗi lệnh đã đóng, kịch bản theo tầm và danh sách tài sản;
          * tự hợp nhất `index.json` bằng `_update_assessment_index`, viết ra
            vì `persist` khi đó dựng lại index từ đúng tập bot được đưa vào.
            `persist` nay tự hợp nhất, nên bản riêng đó thành thừa.

        Phần CÒN LẠI ở đây -- so trước/sau để dựng `RescoreOutcome` -- là
        việc riêng của poller, không phải của lượt chấm, nên vẫn nằm lại.
        """
        from pathlib import Path

        from Agent.backend.report.qc.reporting.assessment_store import (
            load_bot as load_assessment,
        )
        from Agent.backend.scripts.run_report import rescore_one_bot_complete

        # data/assessment/ xếp theo SLOT (`assessment_store._slot_index()`
        # đọc bot_selection.json giống `load_bot_targets()`), nên tra bằng
        # target.venue/target.symbol -- khác với việc quét cây dữ liệu thật
        # bên dưới, vốn phải dùng data_venue.
        previous = load_assessment(
            Path(self.data_dir), target.venue, target.symbol, target.unique_code
        )

        if target.data_venue is None:
            # Chỉ xảy ra khi `_rescore_bot` được gọi trên một target chưa đi
            # qua `poll_bot()`/`with_data_location()`. Từ chối ồn ào ở đây
            # chính là mục đích của bản sửa trước: im lặng lui về venue của
            # slot đúng là con bug làm `scan()` tìm nhầm thư mục.
            raise RuntimeError(
                f"target {target.unique_code} has not been resolved against its "
                "real data (data_venue is None) -- must go through poll_bot() "
                "before rescoring"
            )

        written = rescore_one_bot_complete(
            Path(self.data_dir),
            target.unique_code,
            data_venue=target.data_venue,
        )
        if written is None:
            # Nêu rõ tham số đã dùng: một `None` trần không nói được gì về
            # VÌ SAO, và đó đúng là cách con bug venue_types lọt lưới lâu.
            raise RuntimeError(
                f"rescore_one_bot_complete found nothing for bot "
                f"{target.unique_code} under data venue {target.data_venue!r}"
            )

        current = load_assessment(
            Path(self.data_dir), target.venue, target.symbol, target.unique_code
        ) or {}
        new_scoring = current.get("scoring", {})
        new_recommendation = current.get("recommendation", {})
        old_scoring = (previous or {}).get("scoring", {})
        old_recommendation = (previous or {}).get("recommendation", {})
        return RescoreOutcome(
            unique_code=target.unique_code,
            assessment_path=written,
            old_risk_score=old_scoring.get("risk_score"),
            new_risk_score=new_scoring.get("risk_score"),
            old_tier=old_scoring.get("risk_tier"),
            new_tier=new_scoring.get("risk_tier"),
            old_verdict=old_recommendation.get("verdict"),
            new_verdict=new_recommendation.get("verdict"),
        )

    def poll_once(self) -> List[BotChange]:
        results: List[BotChange] = []
        total = len(self.targets)
        for i, target in enumerate(self.targets, start=1):
            self.progress(
                f"[{i}/{total}] {target.name} ({target.unique_code}, "
                f"{target.venue}/{target.symbol}) - fetching positions..."
            )
            try:
                change = self.poll_bot(target)
            except Exception as exc:  # noqa: BLE001 - one bot must never kill the round
                change = BotChange(
                    target=target, ok=False, error=f"unexpected error: {exc}"
                )

            # Gate re-scoring on new_closed_count, NOT on positions_changed:
            # the real-time analysis (scoring, Monte Carlo) is scoped to
            # CLOSED trades only, exactly as before this fix -- an open
            # position never enters it. A bot opening (or even closing, until
            # the close is confirmed via history) a position therefore cannot
            # move a single number the analysis produces, so re-scoring it
            # would just recompute the same result at 1.5-5s of cost for
            # nothing. Only a trade actually merged into closed_trades this
            # round can change the output, so only that is allowed to trigger
            # a re-score.
            if change.ok and change.new_closed_count > 0:
                try:
                    # change.target, not the loop's `target`: poll_bot()
                    # resolves data_venue/data_symbol onto the target it
                    # returns in BotChange, and _rescore_bot needs those, not
                    # the un-resolved slot-only target this loop still holds.
                    change.rescore = self._rescore_fn(change.target)
                    if change.rescore is None:
                        change.rescore_error = "could not produce a new assessment"
                except Exception as exc:  # noqa: BLE001 - scoring failure != poll failure
                    change.rescore_error = str(exc)

            self.progress("  " + _format_change_vi(change))
            results.append(change)
        return results

    # -- continuous mode ---------------------------------------------------

    def run_forever(
        self, interval_seconds: float, stop_event: Optional[threading.Event] = None
    ) -> None:
        stop_event = stop_event or threading.Event()
        try:
            while not stop_event.is_set():
                started = time.monotonic()
                self.poll_once()
                elapsed = time.monotonic() - started
                remaining = max(0.0, interval_seconds - elapsed)
                self.progress(
                    f"Round took {elapsed:.1f}s, waiting {remaining:.1f}s before the next round"
                )
                if stop_event.wait(remaining):
                    break
        except KeyboardInterrupt:
            self.progress("Received Ctrl+C, stopping live poller.")
