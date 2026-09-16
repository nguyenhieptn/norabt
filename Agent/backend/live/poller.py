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
from Agent.backend.mcp.inference.public_signals import SubPositionClock
from Agent.backend.okx.client import OkxClient, OkxError

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
        return f"{label}: CHUA_CRAWL - {change.error}"
    if not change.ok:
        tag = "STALE" if change.stale else "lỗi"
        return f"{label}: {tag} - {change.error}"

    if not change.positions_changed and change.new_closed_count == 0:
        # Case 1: genuinely nothing happened.
        return f"{label}: không đổi gì, bỏ qua chấm điểm"

    if change.new_closed_count == 0:
        # Case 2: positions_changed is True here (that's the only other way
        # to reach this branch) -- something opened and/or left the open
        # set, but it has not yet been confirmed into closed_trades (a
        # just-closed position sits in `pending` for a round or more, see
        # module docstring point 2). Per the closed-trades-only analysis
        # scope, there is nothing yet worth re-scoring over.
        bits = []
        if change.opened_ids:
            bits.append(f"mở thêm {len(change.opened_ids)} vị thế")
        if change.closed_ids:
            bits.append(f"đóng {len(change.closed_ids)} vị thế (đang chờ khớp lịch sử)")
        detail = ", ".join(bits) if bits else "vị thế thay đổi"
        return f"{label}: {detail}, CHƯA có lệnh nào chốt thêm -> bỏ qua chấm điểm"

    # Case 3: at least one trade newly closed this round -- the only case a
    # re-score was actually attempted (see poll_once).
    bits = []
    if change.opened_ids:
        bits.append(f"mở thêm {len(change.opened_ids)} vị thế")
    if change.closed_ids:
        bits.append(f"đóng {len(change.closed_ids)} vị thế")
    bits.append(f"ghép {change.new_closed_count} lệnh mới vào sổ lệnh")
    detail = ", ".join(bits)

    if change.rescore is None:
        suffix = f" | chưa chấm lại được: {change.rescore_error}"
        return f"{label}: {detail}{suffix}"

    outcome = change.rescore
    old_score = (
        "?" if outcome.old_risk_score is None else f"{outcome.old_risk_score:.1f}"
    )
    new_score = (
        "?" if outcome.new_risk_score is None else f"{outcome.new_risk_score:.1f}"
    )
    score_bit = f"điểm rủi ro {old_score} -> {new_score}"
    tier_bit = f"{outcome.old_tier or '?'} -> {outcome.new_tier}"
    line = f"{label}: {detail} | {score_bit} | xếp loại {tier_bit}"
    if outcome.tier_changed:
        line += f"  *** ĐỔI XẾP LOẠI: {outcome.old_tier} -> {outcome.new_tier} ***"
    elif outcome.verdict_changed:
        line += (
            f"  *** ĐỔI KHUYẾN NGHỊ: {outcome.old_verdict} -> {outcome.new_verdict} ***"
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
        self.evaluation_mode = evaluation_mode
        self.progress = progress
        self.now_fn = now_fn
        # Overridable so tests can count/stub calls without paying for a real
        # Monte Carlo run; the default wires up the real QC pipeline.
        self._rescore_fn = rescore_fn or self._rescore_bot
        self._cohort_service = None  # built lazily, only if the default path runs

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
                    "chưa có dữ liệu crawl cho bot này (không tìm thấy thư mục "
                    f"bot_{target.unique_code} dưới bất kỳ venue/asset nào)"
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
                "phản hồi vị thế hiện tại không hợp lệ (không phải danh sách)",
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
                    f"  ! {target.name}: không lấy được lịch sử để ghép lệnh vừa "
                    f"đóng ({exc}), sẽ thử lại vòng sau"
                )
            else:
                history_rows = _valid_history_rows(raw_history, target.unique_code)
                if history_rows is None:
                    self.progress(
                        f"  ! {target.name}: trang lịch sử trả về không hợp lệ, "
                        "không ghép vào sổ lệnh vòng này (dữ liệu cũ được giữ nguyên)"
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
                    "open_positions cập nhật mỗi vòng qua public-current-subpositions; "
                    "closed_trades chỉ được GHÉP thêm (không crawl lại) khi phát hiện "
                    "vị thế vừa đóng, qua trang đầu public-subpositions-history"
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
                f"  !!! {target.name} ({target.unique_code}): STALE - lỗi liên tục "
                f"{state.consecutive_errors} lần, dữ liệu KHÔNG còn được coi là mới"
            )
        return BotChange(
            target=target,
            ok=False,
            error=message,
            stale=state.status == "STALE",
        )

    # -- scoring -------------------------------------------------------------

    def _rescore_bot(self, target: BotTarget) -> Optional[RescoreOutcome]:
        """Re-run step 3 for one bot and persist assessment.json in place.

        Uses `CohortAssessmentService.scan(only_codes={...})` rather than
        calling `RiskSupervisionPipeline.run()` directly: both run the exact
        same market/bot/QCCoreService.assess_bot computation, but only the
        cohort service already produces the fully-populated row shape
        `assessment_store.build_assessment()` expects (trade counts, MC
        percentiles, dimension scores, the Vietnamese narrative...). Rebuilding
        that ~150-line row from a bare BotRiskAssessment would duplicate
        logic that already exists and is already correct.
        """
        from pathlib import Path

        from Agent.backend.qc.reporting.analysis_store import folder_name
        from Agent.backend.qc.reporting.assessment_store import (
            build_assessment,
            load_bot as load_assessment,
        )
        from Agent.backend.qc.reporting.cohort import CohortAssessmentService

        # data/assessment/ is filed by SLOT (assessment_store._slot_index()
        # reads bot_selection.json the same way load_bot_targets() does), so
        # this lookup correctly uses target.venue/target.symbol, not
        # data_venue/data_symbol -- unlike scan() below, which walks the real
        # data/<venue>/ tree.
        previous = load_assessment(
            Path(self.data_dir), target.venue, target.symbol, target.unique_code
        )

        if target.data_venue is None:
            # Only happens if _rescore_bot is called on a target that never
            # went through poll_bot()/with_data_location() -- e.g. a caller
            # bypassing the normal flow. Refusing loudly here is the whole
            # point of this fix: silently falling back to the slot venue is
            # exactly the bug that made scan() search the wrong directory.
            raise RuntimeError(
                f"target {target.unique_code} chưa được resolve theo dữ liệu "
                "thật (data_venue is None) -- phải gọi qua poll_bot() trước "
                "khi chấm lại"
            )

        if self._cohort_service is None:
            # persist_history=False mirrors RiskSupervisionPipeline's own
            # default for on-demand scoring (see agent_server.py): a live
            # poll re-score is not the deliberate, periodic run that the risk
            # *trend* history is meant to track, so it must not feed it.
            self._cohort_service = CohortAssessmentService(
                data_dir=Path(self.data_dir),
                evaluation_mode=self.evaluation_mode,
                persist_history=False,
            )
        report = self._cohort_service.scan(
            as_of_ms=self.now_fn(),
            # `_discover()` walks data_dir/<venue>/ on disk, so this MUST be
            # the real venue the bot's files live under, not its slot venue
            # -- passing target.venue here is exactly the bug this fix
            # addresses (a DEX slot whose data is actually under cex/ made
            # scan() search dex/ and always come back with nothing).
            venue_types=(target.data_venue,),
            only_codes={target.unique_code},
        )
        matches = [r for r in report.rows if r.unique_code == target.unique_code]
        row = next((r for r in matches if r.error is None), None)
        if row is None:
            # Never return a bare None here: "không tạo được bản chấm điểm
            # mới" told the operator nothing about *why*, which is exactly
            # how the venue_types bug above went unnoticed for so long.
            # Raising with the concrete scan parameters lets poll_once()'s
            # existing exception handler surface a diagnosable rescore_error.
            if not matches:
                raise RuntimeError(
                    f"scan() không thấy bot {target.unique_code} khi quét "
                    f"venue_types=({target.data_venue!r},) -- {len(report.rows)} "
                    "dòng trả về tổng cộng, không dòng nào khớp uniqueCode"
                )
            reasons = sorted({r.error for r in matches if r.error})
            raise RuntimeError(
                f"scan() tìm thấy bot {target.unique_code} khi quét "
                f"venue_types=({target.data_venue!r},) nhưng {len(matches)} dòng "
                f"đều lỗi: {'; '.join(reasons) if reasons else '(không rõ lỗi)'}"
            )

        slot = f"{target.venue}/{target.symbol}"
        payload = build_assessment(row, report.generated_at_ms, slot)
        if previous:
            # `rank_in_cohort` is only meaningful across the full 30-bot
            # cohort; scoring one bot alone always computes rank 1. Keep the
            # last known rank rather than publish a number that looks
            # authoritative but was computed with a cohort of one bot.
            payload["bot"]["rank_in_cohort"] = previous.get("bot", {}).get(
                "rank_in_cohort"
            )
        bot_dir = (
            Path(self.data_dir)
            / "assessment"
            / target.venue.lower()
            / target.symbol
            / "bot"
            / folder_name(row.nick_name, row.unique_code)
        )
        write_atomic(bot_dir / "assessment.json", payload)
        self._update_assessment_index(target.venue, target.symbol, payload)

        old_cham_diem = (previous or {}).get("cham_diem", {})
        old_khuyen_nghi = (previous or {}).get("khuyen_nghi", {})
        return RescoreOutcome(
            unique_code=target.unique_code,
            assessment_path=str(bot_dir / "assessment.json"),
            old_risk_score=old_cham_diem.get("risk_score"),
            new_risk_score=row.risk_score,
            old_tier=old_cham_diem.get("risk_tier"),
            new_tier=row.risk_tier,
            old_verdict=old_khuyen_nghi.get("ket_luan"),
            new_verdict=row.verdict,
        )

    def _update_assessment_index(
        self, venue: str, symbol: str, payload: Dict[str, Any]
    ) -> None:
        """Merge one bot's summary into data/assessment/index.json in place.

        Never calls `assessment_store.persist()` for this: that function
        rebuilds the *whole* index from whatever rows it is given, so handing
        it a single-bot report would clobber the other 29 bots' entries.
        A surgical read-modify-write keeps every other bot's summary intact.
        """
        from pathlib import Path

        index_path = Path(self.data_dir) / "assessment" / "index.json"
        index = read_json(index_path) or {
            "step": "3_QC_DANH_GIA",
            "generated_at_ms": 0,
            "bots_assessed": 0,
            "note": (
                "Mỗi bot một file assessment.json: điểm chất lượng, điểm rủi ro, xếp "
                "loại, nguyên nhân và bản khuyến nghị text đầy đủ. Text là phần "
                "chính; các chỉ số bên dưới là bằng chứng cho text đó."
            ),
            "bots": [],
        }
        summary = {
            "nick_name": payload["bot"]["nick_name"],
            "unique_code": payload["bot"]["unique_code"],
            "slot": payload["bot"]["slot"],
            "verdict": payload["khuyen_nghi"]["ket_luan"],
            "quality_score": payload["khuyen_nghi"]["diem_chat_luong"],
            "risk_score": payload["cham_diem"]["risk_score"],
            "file": None,  # filled in below with the absolute path convention
        }
        bots = list(index.get("bots") or [])
        replaced = False
        for i, entry in enumerate(bots):
            if entry.get("unique_code") == summary["unique_code"]:
                summary["file"] = entry.get("file")
                bots[i] = summary
                replaced = True
                break
        if not replaced:
            bots.append(summary)
        index["bots"] = bots
        index["bots_assessed"] = len(bots)
        index["generated_at_ms"] = max(
            int(index.get("generated_at_ms") or 0), payload["generated_at_ms"]
        )
        write_atomic(index_path, index)

    # -- a whole round ---------------------------------------------------

    def poll_once(self) -> List[BotChange]:
        results: List[BotChange] = []
        total = len(self.targets)
        for i, target in enumerate(self.targets, start=1):
            self.progress(
                f"[{i}/{total}] {target.name} ({target.unique_code}, "
                f"{target.venue}/{target.symbol}) - đang lấy vị thế..."
            )
            try:
                change = self.poll_bot(target)
            except Exception as exc:  # noqa: BLE001 - one bot must never kill the round
                change = BotChange(
                    target=target, ok=False, error=f"lỗi không lường trước: {exc}"
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
                        change.rescore_error = "không tạo được bản chấm điểm mới"
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
                    f"Vòng quét mất {elapsed:.1f}s, chờ {remaining:.1f}s trước vòng kế tiếp"
                )
                if stop_event.wait(remaining):
                    break
        except KeyboardInterrupt:
            self.progress("Đã nhận Ctrl+C, dừng live poller.")
