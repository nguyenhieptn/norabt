"""Tests for the live incremental poller (Agent/backend/live/*).

No network: every OKX call goes through a small scripted fake client. The
goal is to pin down the properties the live-update design depends on --
shared rate limiting, change detection via fingerprint, append-only ledger
merges, and refusing to let a bad response overwrite a good file -- without
touching the real dataset or the real OKX API.
"""

from __future__ import annotations

import json
import time as real_time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from Agent.backend.live.poller import LivePoller, RescoreOutcome
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
from Agent.backend.external.okx.client import OkxApiError, OkxTransportError

CURRENT_POSITIONS_PATH = "/api/v5/copytrading/public-current-subpositions"
HISTORY_PATH = "/api/v5/copytrading/public-subpositions-history"


# ---------------------------------------------------------------------------
# ratelimit.py: token bucket, driven by a fake clock so no test ever sleeps
# ---------------------------------------------------------------------------


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _fake_sleep(clock: FakeClock):
    def _sleep(seconds: float) -> None:
        clock.advance(seconds)

    return _sleep


def test_token_bucket_allows_burst_up_to_capacity():
    clock = FakeClock()
    bucket = TokenBucket(
        capacity=5, period_seconds=2.0, clock=clock, sleep=_fake_sleep(clock)
    )
    for _ in range(5):
        assert bucket.try_acquire() is True
    # The 6th request within the same instant must be refused, not granted.
    assert bucket.try_acquire() is False


def test_token_bucket_blocks_and_waits_the_correct_simulated_time():
    clock = FakeClock()
    bucket = TokenBucket(
        capacity=5, period_seconds=2.0, clock=clock, sleep=_fake_sleep(clock)
    )
    for _ in range(5):
        assert bucket.try_acquire()

    real_started = real_time.perf_counter()
    bucket.acquire()  # bucket is empty: must block via the injected (fake) sleep
    real_elapsed = real_time.perf_counter() - real_started

    # refill rate is 5 tokens / 2s = 2.5 tokens/s, so one token takes 0.4s
    # of *simulated* time -- proven by the fake clock having advanced, not by
    # wall-clock time actually passing (asserted below to stay well under it).
    assert clock.now == pytest.approx(0.4, abs=1e-9)
    assert real_elapsed < 0.2, "acquire() must not really sleep in a test"


def test_token_bucket_refills_over_simulated_time():
    clock = FakeClock()
    bucket = TokenBucket(
        capacity=5, period_seconds=2.0, clock=clock, sleep=_fake_sleep(clock)
    )
    for _ in range(5):
        assert bucket.try_acquire()
    assert bucket.try_acquire() is False
    clock.advance(2.0)  # a full period later, the bucket should be full again
    for _ in range(5):
        assert bucket.try_acquire() is True
    assert bucket.try_acquire() is False


# ---------------------------------------------------------------------------
# store.py: fingerprinting, atomic writes, targets
# ---------------------------------------------------------------------------


def test_fingerprint_detects_open_close_and_no_change():
    before = fingerprint_positions(["1", "2", "3"])
    same_order_different = fingerprint_positions(["3", "1", "2"])
    opened = fingerprint_positions(["1", "2", "3", "4"])
    closed = fingerprint_positions(["1", "2"])

    assert before == same_order_different, "order must not affect the fingerprint"
    assert before != opened
    assert before != closed
    assert opened != closed


def test_load_bot_targets_reads_top_and_mid_per_asset(tmp_path):
    selection = {
        "assets": [
            {
                "venue": "CEX",
                "symbol": "BTC",
                "top": {"code": "AAA111", "name": "Top Trader"},
                "mid": {"code": "BBB222", "name": "Mid Trader"},
            },
            {
                "venue": "DEX",
                "symbol": "WBTC",
                "top": {"code": "CCC333", "name": "Dex Trader"},
                "mid": {"code": "DDD444", "name": "Dex Mid"},
            },
        ]
    }
    (tmp_path / "market" / "universe").mkdir(parents=True)
    (tmp_path / "market" / "universe" / "bot_selection.json").write_text(json.dumps(selection))

    targets = load_bot_targets(tmp_path)

    assert len(targets) == 4
    codes = {t.unique_code for t in targets}
    assert codes == {"AAA111", "BBB222", "CCC333", "DDD444"}
    btc_top = next(t for t in targets if t.unique_code == "AAA111")
    assert btc_top.venue == "CEX"
    assert btc_top.symbol == "BTC"
    assert btc_top.bot_folder == "bot_AAA111"


def test_write_atomic_round_trip(tmp_path):
    path = tmp_path / "sub" / "file.json"
    write_atomic(path, {"a": 1})
    assert json.loads(path.read_text()) == {"a": 1}
    # No leftover temp files after a clean write.
    leftovers = list(path.parent.glob(".*"))
    assert leftovers == []


def test_write_atomic_preserves_existing_file_permissions(tmp_path):
    """A real dataset file is typically 644 (crawl_bots.py writes with
    `Path.write_text`, which respects the umask); `tempfile.mkstemp` defaults
    to 600. Without carrying the old mode forward, the very first live
    update would downgrade every file it touches to owner-only."""
    path = tmp_path / "trade_list.json"
    path.write_text(json.dumps({"a": 1}))
    path.chmod(0o644)

    write_atomic(path, {"a": 2})

    assert (path.stat().st_mode & 0o777) == 0o644


def test_write_atomic_leaves_old_file_untouched_on_mid_write_failure(
    tmp_path, monkeypatch
):
    path = tmp_path / "trade_list.json"
    write_atomic(path, {"closed_trades": ["good data, 500 trades worth"]})
    original_bytes = path.read_bytes()

    import Agent.backend.live.store as store_module

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated crash mid-write, before the atomic swap")

    monkeypatch.setattr(store_module.json, "dump", _boom)

    with pytest.raises(RuntimeError):
        write_atomic(path, {"closed_trades": []})

    # The destination must be byte-for-byte the old file: a crash while
    # writing the temp file must never touch the real path (os.replace is
    # only ever called after the temp file is fully written and fsynced).
    assert path.read_bytes() == original_bytes
    assert list(path.parent.glob(".*.tmp")) == [] or all(
        not p.name.startswith(f".{path.name}.") for p in path.parent.glob(".*")
    )


# ---------------------------------------------------------------------------
# poller.py: scripted OKX client
# ---------------------------------------------------------------------------


class ScriptedClient:
    """Fake OkxClient.public_get: per (path, uniqueCode) queue of canned replies.

    A queued item that is a BaseException instance is raised instead of
    returned, so tests can script a transient OKX failure without any real
    network call ever happening.
    """

    def __init__(self) -> None:
        self._queues: Dict[tuple, List[Any]] = {}
        self.calls: List[tuple] = []

    def queue(self, path: str, code: str, value: Any) -> None:
        self._queues.setdefault((path, code), []).append(value)

    def public_get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        code = (params or {}).get("uniqueCode")
        self.calls.append((path, code))
        key = (path, code)
        queue = self._queues.get(key)
        if not queue:
            raise AssertionError(f"no scripted OKX response left for {key}")
        item = queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def _target(
    code: str, name: str = "Test Trader", venue: str = "CEX", symbol: str = "BTC"
) -> BotTarget:
    return BotTarget(
        unique_code=code,
        name=name,
        role="top",
        venue=venue,
        symbol=symbol,
        bot_folder=f"bot_{code}",
    )


def _seed_dataset(
    data_dir: Path,
    target: BotTarget,
    open_positions: List[Dict[str, Any]],
    closed_trades: List[Dict[str, Any]],
) -> Path:
    bot_dir = target.bot_dir(data_dir)
    bot_dir.mkdir(parents=True, exist_ok=True)
    (bot_dir / "crawl_slot.json").write_text(
        json.dumps({"venue": target.venue.upper(), "asset": target.symbol.upper()})
    )
    (bot_dir / "overview.json").write_text(
        json.dumps({"uniqueCode": target.unique_code, "nickName": target.name})
    )
    trade_list = {
        "uniqueCode": target.unique_code,
        "open_positions_count": len(open_positions),
        "open_positions": open_positions,
        "closed_trades_count": len(closed_trades),
        "closed_trades": closed_trades,
        "ledger_truncated": False,
        "ledger_page_size": 100,
        "positions_without_instrument": 0,
        "inference": {},
        "provenance": {"crawled_at_ms": 1},
    }
    (bot_dir / "trade_list.json").write_text(json.dumps(trade_list))
    return bot_dir


def _seed_dataset_at(
    data_dir: Path,
    venue: str,
    asset: str,
    code: str,
    name: str,
    open_positions: List[Dict[str, Any]],
    closed_trades: List[Dict[str, Any]],
) -> Path:
    """Seed a bot's real dataset directory at a venue/asset chosen directly by
    the test -- independent of any BotTarget slot. Used to reproduce the
    exact "slot != real instrument" mismatch LỖI 5 was about: a BotTarget can
    carry one venue/symbol (its selection slot) while its actual crawled data
    lives under a completely different venue/asset pair.
    """
    bot_dir = Path(data_dir) / "trade" / f"bot_{code}"
    bot_dir.mkdir(parents=True, exist_ok=True)
    (bot_dir / "crawl_slot.json").write_text(
        json.dumps({"venue": venue.upper(), "asset": asset.upper()})
    )
    (bot_dir / "overview.json").write_text(
        json.dumps({"uniqueCode": code, "nickName": name})
    )
    trade_list = {
        "uniqueCode": code,
        "open_positions_count": len(open_positions),
        "open_positions": open_positions,
        "closed_trades_count": len(closed_trades),
        "closed_trades": closed_trades,
        "ledger_truncated": False,
        "ledger_page_size": 100,
        "positions_without_instrument": 0,
        "inference": {},
        "provenance": {"crawled_at_ms": 1},
    }
    (bot_dir / "trade_list.json").write_text(json.dumps(trade_list))
    return bot_dir


def _all_bot_dirs(data_dir: Path) -> List[Path]:
    return sorted(p for p in Path(data_dir).rglob("bot_*") if p.is_dir())


def _position(sub_pos_id: str, **overrides) -> Dict[str, Any]:
    # No "uniqueCode" key by default: the ownership filter (`_owned_by`)
    # treats a missing/blank owner as trustworthy, same as crawl_bots.py's
    # own `owned_by`. Pass uniqueCode=... explicitly only to test the filter
    # itself (a row claiming a *different* bot's code).
    row = {
        "ccy": "USDT",
        "instId": "",
        "instType": "SWAP",
        "lever": "10",
        "margin": "100",
        "markPx": "",
        "mgnMode": "cross",
        "openAvgPx": "",
        "openTime": "",
        "posSide": "net",
        "subPos": "",
        "subPosId": sub_pos_id,
        "upl": "0",
        "uplRatio": "0",
    }
    row.update(overrides)
    return row


def _closed_trade(
    sub_pos_id: str, close_time: str = "1700000000000", **overrides
) -> Dict[str, Any]:
    row = {
        "ccy": "USDT",
        "closeAvgPx": "1.0",
        "closeTime": close_time,
        "instId": "BTC-USDT-SWAP",
        "instType": "SWAP",
        "lever": "10",
        "margin": "100",
        "mgnMode": "cross",
        "openAvgPx": "1.0",
        "openTime": "1699999999000",
        "pnl": "1.0",
        "pnlRatio": "0.01",
        "posSide": "long",
        "subPos": "10",
        "subPosId": sub_pos_id,
    }
    row.update(overrides)
    return row


def _make_poller(
    tmp_path, client: ScriptedClient, targets: List[BotTarget], **kwargs
) -> LivePoller:
    kwargs.setdefault("rescore_fn", lambda target: None)
    kwargs.setdefault("progress", lambda line: None)
    return LivePoller(
        targets=targets,
        data_dir=tmp_path,
        client=client,
        rate_limiter=TokenBucket(capacity=1000, period_seconds=1.0),
        **kwargs,
    )


def test_poll_bot_detects_opened_and_closed_positions(tmp_path):
    target = _target("CODE1")
    _seed_dataset(
        tmp_path,
        target,
        open_positions=[_position("100"), _position("200")],
        closed_trades=[],
    )
    client = ScriptedClient()
    # position 200 closed, position 300 opened; 100 stayed open.
    client.queue(CURRENT_POSITIONS_PATH, "CODE1", [_position("100"), _position("300")])
    client.queue(HISTORY_PATH, "CODE1", [_closed_trade("200")])
    poller = _make_poller(tmp_path, client, [target])

    change = poller.poll_bot(target)

    assert change.ok is True
    assert change.positions_changed is True
    assert change.opened_ids == ["300"]
    assert change.closed_ids == ["200"]
    assert change.new_closed_count == 1

    written = read_json(target.trade_list_path(tmp_path))
    assert {p["subPosId"] for p in written["open_positions"]} == {"100", "300"}
    assert {t["subPosId"] for t in written["closed_trades"]} == {"200"}


def test_poll_bot_no_change_when_positions_are_identical(tmp_path):
    target = _target("CODE2")
    _seed_dataset(
        tmp_path,
        target,
        open_positions=[_position("1"), _position("2")],
        closed_trades=[],
    )
    client = ScriptedClient()
    client.queue(
        CURRENT_POSITIONS_PATH, "CODE2", [_position("2"), _position("1")]
    )  # reordered
    poller = _make_poller(tmp_path, client, [target])

    change = poller.poll_bot(target)

    assert change.ok is True
    assert change.positions_changed is False
    assert change.opened_ids == []
    assert change.closed_ids == []
    # No pending close, so the history endpoint must never have been called.
    assert all(call[0] != HISTORY_PATH for call in client.calls)


def test_short_position_negative_subpos_preserved_and_parsed_by_abs_value(tmp_path):
    """subPos arrives negative for a short; the poller must pass it through
    verbatim (direction lives in posSide) and the existing downstream ledger
    parser must still recover a positive size + SHORT side from it -- the
    exact bug crawl_bots.py had to fix once already."""
    from Agent.backend.bot.mcp.schemas.bot_result import PositionSide
    from Agent.backend.bot.mcp.trades.ledger import TradeLedgerManager

    target = _target("CODE3")
    _seed_dataset(tmp_path, target, open_positions=[_position("1")], closed_trades=[])
    client = ScriptedClient()
    client.queue(CURRENT_POSITIONS_PATH, "CODE3", [])  # position "1" just closed
    short_trade = _closed_trade("1", posSide="short", subPos="-8151")
    client.queue(HISTORY_PATH, "CODE3", [short_trade])
    poller = _make_poller(tmp_path, client, [target])

    poller.poll_bot(target)

    written = read_json(target.trade_list_path(tmp_path))
    stored = written["closed_trades"][0]
    assert stored["subPos"] == "-8151", (
        "raw signed value must be preserved as OKX sent it"
    )
    assert stored["posSide"] == "short"

    result = TradeLedgerManager.parse_trade_list_with_diagnostics(written)
    assert len(result.trades) == 1
    item = result.trades[0]
    assert item.side == PositionSide.SHORT
    assert item.quantity == pytest.approx(8151.0), "size must be a positive magnitude"


def test_history_merge_dedupes_by_subposid(tmp_path):
    target = _target("CODE4")
    existing_closed = [_closed_trade("OLD1"), _closed_trade("OLD2")]
    _seed_dataset(
        tmp_path, target, open_positions=[_position("1")], closed_trades=existing_closed
    )
    client = ScriptedClient()
    client.queue(CURRENT_POSITIONS_PATH, "CODE4", [])  # "1" closed
    # First page repeats OLD1 (already on disk) and brings one genuinely new trade.
    client.queue(HISTORY_PATH, "CODE4", [_closed_trade("1"), _closed_trade("OLD1")])
    poller = _make_poller(tmp_path, client, [target])

    change = poller.poll_bot(target)

    written = read_json(target.trade_list_path(tmp_path))
    ids = [t["subPosId"] for t in written["closed_trades"]]
    assert sorted(ids) == sorted(["1", "OLD1", "OLD2"]), "no duplicate rows"
    assert len(ids) == len(set(ids))
    assert change.new_closed_count == 1


def test_empty_or_malformed_response_never_overwrites_good_data(tmp_path):
    """The single most important behaviour: a bad OKX answer must leave the
    existing dataset exactly as it was, never replace it with something
    thinner."""
    target = _target("CODE5")
    good_positions = [_position("1"), _position("2"), _position("3")]
    good_closed = [_closed_trade("OLD1"), _closed_trade("OLD2")]
    _seed_dataset(
        tmp_path, target, open_positions=good_positions, closed_trades=good_closed
    )
    before_bytes = target.trade_list_path(tmp_path).read_bytes()

    client = ScriptedClient()
    # OKX answers with something that is not a list at all (e.g. an error
    # envelope that slipped past code-checking, or a missing "data" key).
    client.queue(CURRENT_POSITIONS_PATH, "CODE5", {"unexpected": "shape"})
    poller = _make_poller(tmp_path, client, [target])

    change = poller.poll_bot(target)

    assert change.ok is False
    assert "invalid" in change.error
    after_bytes = target.trade_list_path(tmp_path).read_bytes()
    assert after_bytes == before_bytes, (
        "malformed response must not touch the file at all"
    )


def test_malformed_history_page_does_not_wipe_the_ledger(tmp_path):
    """The exact "mất sổ lệnh" scenario: positions closed, but the history
    page OKX answers with is garbage. closed_trades must stay exactly as it
    was (never replaced with the malformed/empty page), and the still-open
    positions must still be written since that half of the answer was fine."""
    target = _target("CODE6")
    good_closed = [_closed_trade(f"OLD{i}") for i in range(5)]
    _seed_dataset(
        tmp_path, target, open_positions=[_position("1")], closed_trades=good_closed
    )

    client = ScriptedClient()
    client.queue(CURRENT_POSITIONS_PATH, "CODE6", [])  # position "1" closed
    client.queue(HISTORY_PATH, "CODE6", {"data": None})  # malformed: not a list
    poller = _make_poller(tmp_path, client, [target])

    change = poller.poll_bot(target)

    assert change.ok is True  # the positions half of the round was fine
    assert change.new_closed_count == 0
    written = read_json(target.trade_list_path(tmp_path))
    assert len(written["closed_trades"]) == 5
    assert {t["subPosId"] for t in written["closed_trades"]} == {
        f"OLD{i}" for i in range(5)
    }
    assert written["open_positions"] == []

    # The close is still pending, so the next round must retry the fetch.
    state = load_state(tmp_path, "CODE6")
    assert "1" in state.pending_close_subpos_ids


def test_position_rows_missing_subposid_are_dropped_not_written(tmp_path):
    target = _target("CODE7")
    _seed_dataset(tmp_path, target, open_positions=[], closed_trades=[])
    client = ScriptedClient()
    broken_row = _position("1")
    del broken_row["subPosId"]
    client.queue(CURRENT_POSITIONS_PATH, "CODE7", [broken_row, _position("2")])
    poller = _make_poller(tmp_path, client, [target])

    change = poller.poll_bot(target)

    assert change.ok is True
    written = read_json(target.trade_list_path(tmp_path))
    assert [p["subPosId"] for p in written["open_positions"]] == ["2"]


def test_consecutive_failures_mark_bot_stale(tmp_path):
    target = _target("CODE8")
    _seed_dataset(tmp_path, target, open_positions=[_position("1")], closed_trades=[])
    client = ScriptedClient()
    for _ in range(5):
        client.queue(CURRENT_POSITIONS_PATH, "CODE8", OkxTransportError("mất kết nối"))
    poller = _make_poller(tmp_path, client, [target])

    changes = [poller.poll_bot(target) for _ in range(5)]

    assert all(c.ok is False for c in changes)
    assert changes[-1].stale is True
    assert changes[0].stale is False, "must not be STALE before reaching the threshold"
    state = load_state(tmp_path, "CODE8")
    assert state.status == "STALE"
    assert state.consecutive_errors == 5

    # A stale bot's dataset file must be untouched, not quietly kept "as if fresh".
    written = read_json(target.trade_list_path(tmp_path))
    assert [p["subPosId"] for p in written["open_positions"]] == ["1"]


def test_one_bot_failure_does_not_break_the_whole_round(tmp_path):
    good = _target("GOOD1")
    bad = _target("BAD1")
    _seed_dataset(tmp_path, good, open_positions=[], closed_trades=[])
    _seed_dataset(tmp_path, bad, open_positions=[_position("9")], closed_trades=[])

    client = ScriptedClient()
    client.queue(CURRENT_POSITIONS_PATH, "GOOD1", [_position("1")])
    client.queue(CURRENT_POSITIONS_PATH, "BAD1", OkxApiError("50001", "server busy"))

    poller = _make_poller(tmp_path, client, [bad, good])  # bad polled first on purpose

    changes = poller.poll_once()

    assert len(changes) == 2
    by_code = {c.target.unique_code: c for c in changes}
    assert by_code["BAD1"].ok is False
    assert by_code["GOOD1"].ok is True
    assert by_code["GOOD1"].positions_changed is True
    # The good bot's write must have happened despite the other bot's error.
    written = read_json(good.trade_list_path(tmp_path))
    assert [p["subPosId"] for p in written["open_positions"]] == ["1"]


# ---------------------------------------------------------------------------
# Re-score gating: only a newly CLOSED trade may trigger a re-score. The
# real-time analysis (scoring, Monte Carlo) is scoped to closed trades only
# -- an open position is never part of it -- so a bot merely opening or
# closing a position, with nothing yet confirmed into closed_trades, cannot
# move any number the analysis produces. Re-scoring it anyway is pure waste
# (measured at ~30% of re-scores in production, 1.5-5s each). These four
# tests pin down the exact trigger condition; do not loosen them to key off
# `positions_changed` again.
# ---------------------------------------------------------------------------


def _outcome_stub(code: str) -> RescoreOutcome:
    return RescoreOutcome(
        unique_code=code,
        assessment_path="unused",
        old_risk_score=40.0,
        new_risk_score=70.0,
        old_tier="HEALTHY",
        new_tier="HIGH",
        old_verdict="TIỀM NĂNG",
        new_verdict="NGUY HIỂM",
    )


def test_nothing_changed_never_triggers_rescoring(tmp_path):
    """Baseline: identical positions, no pending close -> no rescore call."""
    target = _target("CODE9")
    _seed_dataset(tmp_path, target, open_positions=[_position("1")], closed_trades=[])
    client = ScriptedClient()
    client.queue(CURRENT_POSITIONS_PATH, "CODE9", [_position("1")])  # identical

    calls = []

    def _counting_rescore(t: BotTarget) -> Optional[RescoreOutcome]:
        calls.append(t.unique_code)
        return None

    poller = _make_poller(tmp_path, client, [target], rescore_fn=_counting_rescore)
    changes = poller.poll_once()

    assert changes[0].positions_changed is False
    assert changes[0].new_closed_count == 0
    assert calls == [], "the QC pipeline must not be re-run when nothing changed"


def test_positions_changed_without_new_close_never_triggers_rescoring(tmp_path):
    """A bot opening a new position (no close involved at all) must NOT
    trigger a re-score: opening a position cannot move any number the
    closed-trades-only analysis computes. This is the exact waste the fix
    removes -- previously `changed` (the position-fingerprint diff) alone
    gated re-scoring, so this case incorrectly re-scored the bot."""
    target = _target("CODE10")
    _seed_dataset(tmp_path, target, open_positions=[], closed_trades=[])
    client = ScriptedClient()
    client.queue(CURRENT_POSITIONS_PATH, "CODE10", [_position("1")])  # newly opened

    calls = []

    def _counting_rescore(t: BotTarget) -> Optional[RescoreOutcome]:
        calls.append(t.unique_code)
        return _outcome_stub(t.unique_code)

    poller = _make_poller(tmp_path, client, [target], rescore_fn=_counting_rescore)
    changes = poller.poll_once()

    change = changes[0]
    assert change.positions_changed is True
    assert change.new_closed_count == 0
    assert calls == [], "opening a position alone must never trigger a rescore"
    assert change.rescore is None
    assert change.rescore_error is None, (
        "no rescore was attempted, so there must be no rescore error either"
    )


def test_new_closed_trade_without_position_change_triggers_rescoring_once(tmp_path):
    """A trade can be confirmed into closed_trades in a round where the open
    position set itself does not move -- e.g. it left the open set in a
    PREVIOUS round (recorded as pending_close_subpos_ids) and is only now
    confirmed via the history page. This is the cleanest proof that
    positions_changed and new_closed_count are genuinely independent facts,
    and it must still trigger exactly one rescore call."""
    target = _target("CODE11")
    _seed_dataset(tmp_path, target, open_positions=[_position("2")], closed_trades=[])
    # Simulate "1" having already disappeared from open positions last round.
    save_state(
        tmp_path,
        LiveState(unique_code="CODE11", pending_close_subpos_ids=["1"]),
    )
    client = ScriptedClient()
    # This round's open positions are identical to what's on disk already.
    client.queue(CURRENT_POSITIONS_PATH, "CODE11", [_position("2")])
    client.queue(HISTORY_PATH, "CODE11", [_closed_trade("1")])

    calls = []

    def _counting_rescore(t: BotTarget) -> Optional[RescoreOutcome]:
        calls.append(t.unique_code)
        return _outcome_stub(t.unique_code)

    poller = _make_poller(tmp_path, client, [target], rescore_fn=_counting_rescore)
    changes = poller.poll_once()

    change = changes[0]
    assert change.positions_changed is False, (
        "the open position set did not move THIS round"
    )
    assert change.new_closed_count == 1
    assert calls == ["CODE11"], "a newly closed trade must trigger exactly one rescore"


def test_positions_changed_and_new_close_together_trigger_rescoring_exactly_once(
    tmp_path,
):
    """The common case: a position closes this round AND is immediately
    confirmed via history in the same round. Must still rescore exactly
    once -- never twice, and never skipped just because both things
    happened together."""
    target = _target("CODE12")
    _seed_dataset(tmp_path, target, open_positions=[_position("1")], closed_trades=[])
    client = ScriptedClient()
    client.queue(CURRENT_POSITIONS_PATH, "CODE12", [])  # "1" just closed
    client.queue(HISTORY_PATH, "CODE12", [_closed_trade("1")])

    calls = []

    def _counting_rescore(t: BotTarget) -> Optional[RescoreOutcome]:
        calls.append(t.unique_code)
        return _outcome_stub(t.unique_code)

    poller = _make_poller(tmp_path, client, [target], rescore_fn=_counting_rescore)
    changes = poller.poll_once()

    change = changes[0]
    assert change.positions_changed is True
    assert change.new_closed_count == 1
    assert calls == ["CODE12"], "must rescore exactly once, not twice"
    assert change.rescore is not None
    assert change.rescore.tier_changed is True
    assert change.rescore.verdict_changed is True


# ---------------------------------------------------------------------------
# LỖI 5 -- the poller must write into a bot's REAL dataset directory
# (resolved by uniqueCode), never into a new directory derived from its
# bot_selection.json slot. This is the bug that created ~30 empty duplicate
# bot folders; these tests pin down the fail-closed replacement behaviour.
# ---------------------------------------------------------------------------


def test_find_bot_dir_locates_real_directory_regardless_of_slot(tmp_path):
    # Real data lives under cex/BTC, exactly like King_GG in the incident:
    # selected under a DEX/WBTC slot but actually trading on cex/BTC.
    real_dir = _seed_dataset_at(
        tmp_path, "CEX", "BTC", "REAL1", "King_GG", [_position("1")], []
    )

    found = find_bot_dir(tmp_path, "REAL1")

    assert found == real_dir


def test_find_bot_dir_returns_none_when_nothing_exists(tmp_path):
    assert find_bot_dir(tmp_path, "NOPE") is None



def test_poll_bot_writes_to_real_dir_when_slot_mismatches_and_creates_nothing(
    tmp_path,
):
    """The exact King_GG scenario: BotTarget's slot says DEX/WBTC, but the
    real crawled data is under cex/BTC. The poller must find and update that
    real directory, and must NOT create data/dex/wbtc/bot/bot_<code>."""
    real_dir = _seed_dataset_at(
        tmp_path, "CEX", "BTC", "MISMATCH1", "King_GG", [_position("1")], []
    )
    # The slot the bot was *selected* under -- deliberately different from
    # where its real data lives.
    target = _target("MISMATCH1", name="King_GG", venue="DEX", symbol="WBTC")

    dirs_before = _all_bot_dirs(tmp_path)

    client = ScriptedClient()
    client.queue(CURRENT_POSITIONS_PATH, "MISMATCH1", [_position("1"), _position("2")])
    poller = _make_poller(tmp_path, client, [target])

    change = poller.poll_bot(target)

    assert change.ok is True
    assert change.not_crawled is False

    dirs_after = _all_bot_dirs(tmp_path)
    # Unified layout: the slot-derived path and the real data path are now
    # structurally the SAME path (data/trade/bot_<code>/, no venue/asset
    # segregation) -- there is no longer a distinct "wrong" location this
    # could have written into instead, so the only invariant left to check
    # is that no NEW directory appeared.
    assert dirs_after == dirs_before, "no new bot directory may be created"

    written = read_json(real_dir / "trade_list.json")
    assert {p["subPosId"] for p in written["open_positions"]} == {"1", "2"}


def test_poll_bot_reports_chua_crawl_when_no_directory_exists_anywhere(tmp_path):
    """Fail-closed: a bot with no crawled directory at all must be reported
    as CHUA_CRAWL and skipped -- never crawled, written, or crashed on."""
    target = _target("GHOST1", name="Ghost Bot", venue="CEX", symbol="ETH")
    dirs_before = _all_bot_dirs(tmp_path)

    client = ScriptedClient()  # no responses queued: must never be called
    poller = _make_poller(tmp_path, client, [target])

    change = poller.poll_bot(target)

    assert change.ok is False
    assert change.not_crawled is True
    assert "NOT_CRAWLED" in _format_change_vi_or_error(change)
    assert client.calls == [], "no OKX call may be spent on an uncrawled bot"

    dirs_after = _all_bot_dirs(tmp_path)
    assert dirs_after == dirs_before, "no directory may be created"
    assert not (tmp_path / "trade" / "bot_GHOST1").exists()


def _format_change_vi_or_error(change) -> str:
    # Small local helper: reuse poller's own formatter so this test asserts
    # against the exact user-facing line, not a re-typed copy of it.
    from Agent.backend.live.poller import _format_change_vi

    return _format_change_vi(change)


def test_poll_once_skips_uncrawled_bot_and_keeps_polling_the_rest(tmp_path):
    ghost = _target("GHOST2", venue="CEX", symbol="ETH")
    good = _target("GOOD2", venue="CEX", symbol="BTC")
    _seed_dataset(tmp_path, good, open_positions=[], closed_trades=[])

    client = ScriptedClient()
    client.queue(CURRENT_POSITIONS_PATH, "GOOD2", [_position("1")])
    poller = _make_poller(tmp_path, client, [ghost, good])

    changes = poller.poll_once()  # must not raise

    assert len(changes) == 2
    by_code = {c.target.unique_code: c for c in changes}
    assert by_code["GHOST2"].not_crawled is True
    assert by_code["GOOD2"].ok is True
    written = read_json(good.trade_list_path(tmp_path))
    assert [p["subPosId"] for p in written["open_positions"]] == ["1"]


def test_large_existing_ledger_untouched_when_no_new_closes(tmp_path):
    """Sổ lệnh có sẵn 100 lệnh đã chốt, poll về 0 lệnh mới -> vẫn đúng 100."""
    target = _target("LEDGER100")
    existing_closed = [_closed_trade(f"OLD{i}") for i in range(100)]
    _seed_dataset(
        tmp_path,
        target,
        open_positions=[_position("1")],
        closed_trades=existing_closed,
    )
    client = ScriptedClient()
    client.queue(CURRENT_POSITIONS_PATH, "LEDGER100", [_position("1")])  # unchanged
    poller = _make_poller(tmp_path, client, [target])

    change = poller.poll_bot(target)

    assert change.ok is True
    assert change.new_closed_count == 0
    written = read_json(target.trade_list_path(tmp_path))
    assert len(written["closed_trades"]) == 100
    assert {t["subPosId"] for t in written["closed_trades"]} == {
        f"OLD{i}" for i in range(100)
    }


def test_two_new_closes_append_to_large_existing_ledger_without_duplicates(tmp_path):
    """Có 2 lệnh mới đã chốt -> sổ lệnh 100 lệnh cũ thành 102, không trùng lặp."""
    target = _target("LEDGER102")
    existing_closed = [_closed_trade(f"OLD{i}") for i in range(100)]
    _seed_dataset(
        tmp_path,
        target,
        open_positions=[_position("1"), _position("2")],
        closed_trades=existing_closed,
    )
    client = ScriptedClient()
    client.queue(CURRENT_POSITIONS_PATH, "LEDGER102", [])  # both just closed
    client.queue(HISTORY_PATH, "LEDGER102", [_closed_trade("1"), _closed_trade("2")])
    poller = _make_poller(tmp_path, client, [target])

    change = poller.poll_bot(target)

    assert change.ok is True
    assert change.new_closed_count == 2
    written = read_json(target.trade_list_path(tmp_path))
    ids = [t["subPosId"] for t in written["closed_trades"]]
    assert len(ids) == 102
    assert len(ids) == len(set(ids)), "no duplicate rows"
    assert set(ids) == {f"OLD{i}" for i in range(100)} | {"1", "2"}


# ---------------------------------------------------------------------------
# LỖI 6 -- rescoring a bot must scan the REAL venue its data lives under
# (BotTarget.data_venue), never the slot venue from bot_selection.json
# (BotTarget.venue). Same root cause as LỖI 5's duplicate folders: a bot's
# selection slot and its real traded instrument can disagree, and this time
# it was CohortAssessmentService.scan() searching the wrong data/<venue>/
# tree and silently coming back empty.
# ---------------------------------------------------------------------------


def test_with_data_location_reads_real_venue_and_symbol_from_bot_dir(tmp_path):
    # Slot says DEX/PEPE; the bot's real files are filed under cex/SNDK/,
    # mirroring one of the 11/30 real mismatches this bug was found from.
    target = _target("ANY1", venue="DEX", symbol="PEPE")
    bot_dir = tmp_path / "trade" / "bot_ANY1"
    bot_dir.mkdir(parents=True)
    (bot_dir / "crawl_slot.json").write_text(
        json.dumps({"venue": "CEX", "asset": "SNDK"}), encoding="utf-8"
    )

    resolved = target.with_data_location(bot_dir)

    assert resolved.data_venue == "CEX"
    assert resolved.data_symbol == "SNDK"
    # The slot fields must be untouched -- they are still the correct label
    # for reports, only the data location changed.
    assert resolved.venue == "DEX"
    assert resolved.symbol == "PEPE"


def test_poll_bot_resolves_real_data_location_onto_returned_target(tmp_path):
    real_dir = _seed_dataset_at(
        tmp_path, "CEX", "BTC", "MISMATCH2", "King_GG2", [_position("1")], []
    )
    target = _target("MISMATCH2", name="King_GG2", venue="DEX", symbol="WBTC")
    client = ScriptedClient()
    client.queue(CURRENT_POSITIONS_PATH, "MISMATCH2", [_position("1")])
    poller = _make_poller(tmp_path, client, [target])

    change = poller.poll_bot(target)

    assert change.ok is True
    assert real_dir.exists()
    # Slot label preserved for reporting...
    assert change.target.venue == "DEX"
    assert change.target.symbol == "WBTC"
    # ...but the real data location is now known too.
    assert change.target.data_venue == "CEX"
    assert change.target.data_symbol == "BTC"


def _capture_rescore(monkeypatch):
    """Bắt tham số `_rescore_bot` truyền xuống lõi chấm điểm CHUNG.

    Trước đây ba test dưới đây tiêm `poller._cohort_service` để bắt lời gọi
    `scan()`. Poller nay không còn tự chấm điểm: nó uỷ thác cho
    `run_report.rescore_one_bot_complete`, cùng hàm mà nút "Re-analyze" và
    lượt chấm cả đàn dùng -- nên không còn `scan()` nào của riêng nó để bắt.
    Thứ CẦN khoá vẫn y nguyên: venue truyền xuống phải là venue của DỮ LIỆU
    THẬT, không phải venue của khe.
    """
    calls = []

    def fake(data_dir, unique_code, *, data_venue=None):
        calls.append({"unique_code": unique_code, "data_venue": data_venue})
        return None

    monkeypatch.setattr(
        "Agent.backend.scripts.run_report.rescore_one_bot_complete", fake
    )
    return calls


def test_rescore_bot_uses_real_data_venue_not_slot_venue(tmp_path, monkeypatch):
    """Đúng con bug: khe DEX/WBTC nhưng dữ liệu thật ở cex/BTC -> lõi chấm
    điểm phải nhận "CEX", không phải "DEX"."""
    real_dir = _seed_dataset_at(
        tmp_path, "CEX", "BTC", "SLOTMIS1", "Slot Mismatch", [_position("1")], []
    )
    target = _target("SLOTMIS1", name="Slot Mismatch", venue="DEX", symbol="WBTC")
    resolved = target.with_data_location(real_dir)
    calls = _capture_rescore(monkeypatch)

    poller = _make_poller(tmp_path, ScriptedClient(), [target])
    with pytest.raises(RuntimeError):
        poller._rescore_bot(resolved)

    assert len(calls) == 1
    assert calls[0]["data_venue"] == "CEX", (
        "phải dùng venue của dữ liệu thật, không phải khe DEX"
    )
    assert calls[0]["unique_code"] == "SLOTMIS1"


def test_rescore_bot_venue_unchanged_when_slot_matches_real_venue(
    tmp_path, monkeypatch
):
    """Không hồi quy: khi khe và venue thật đã trùng (~19/30 bot), hành vi
    phải y hệt trước."""
    real_dir = _seed_dataset_at(
        tmp_path, "CEX", "BTC", "MATCH1", "Matched", [_position("1")], []
    )
    target = _target("MATCH1", name="Matched", venue="CEX", symbol="BTC")
    resolved = target.with_data_location(real_dir)
    calls = _capture_rescore(monkeypatch)

    poller = _make_poller(tmp_path, ScriptedClient(), [target])
    with pytest.raises(RuntimeError):
        poller._rescore_bot(resolved)

    assert calls[0]["data_venue"] == "CEX"


def test_rescore_bot_refuses_target_never_resolved_to_a_data_location(tmp_path):
    """Calling _rescore_bot on a target that never went through
    poll_bot()/with_data_location() must fail loudly, not silently fall back
    to the (possibly wrong) slot venue."""
    target = _target("UNRESOLVED1")
    poller = _make_poller(tmp_path, ScriptedClient(), [target])

    with pytest.raises(RuntimeError, match="data_venue"):
        poller._rescore_bot(target)


def test_empty_scan_gives_a_specific_diagnosable_rescore_error(tmp_path, monkeypatch):
    """When scan() comes back with no matching row, rescore_error must say
    which venue was scanned and which code was searched for -- the old
    generic "không tạo được bản chấm điểm mới" told nobody anything."""
    target = _target("EMPTYSCAN1", venue="CEX", symbol="BTC")
    _seed_dataset(tmp_path, target, open_positions=[_position("1")], closed_trades=[])
    client = ScriptedClient()
    client.queue(CURRENT_POSITIONS_PATH, "EMPTYSCAN1", [])  # "1" just closed
    client.queue(HISTORY_PATH, "EMPTYSCAN1", [_closed_trade("1")])
    poller = _make_poller(tmp_path, client, [target], rescore_fn=None)
    # Lõi chấm điểm không tìm thấy bot -> `_rescore_bot` phải nêu rõ mã
    # và venue đã tìm, không trả một `None` trần.
    monkeypatch.setattr(
        "Agent.backend.scripts.run_report.rescore_one_bot_complete",
        lambda data_dir, unique_code, *, data_venue=None: None,
    )

    changes = poller.poll_once()

    change = changes[0]
    assert change.rescore is None
    assert change.rescore_error is not None
    assert change.rescore_error != "không tạo được bản chấm điểm mới"
    assert "EMPTYSCAN1" in change.rescore_error
    assert "CEX" in change.rescore_error
