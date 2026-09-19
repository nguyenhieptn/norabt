"""Tests for the bot data source abstraction (Agent/backend/sources/bot_source.py).

No test here calls OKX for real -- every OKX interaction is a fake client with
canned responses, so these run at unit-test speed and never touch the network.
Rate-limit tests use TokenBucket's own injectable clock/sleep instead of real
wall-clock time, per the same pattern Agent/test/test_live_poller.py already
uses for the poller's rate limiting.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from Agent.backend.infra.config import config
from Agent.backend.live.ratelimit import TokenBucket
from Agent.backend.mcp.positions.snapshot import PositionSnapshotParser
from Agent.backend.mcp.schemas.bot_result import PositionSide
from Agent.backend.mcp.service import BotObservationService
from Agent.backend.mcp.trades.ledger import TradeLedgerManager
from Agent.backend.okx.client import OkxApiError, OkxTransportError
from Agent.backend.sources.bot_source import (
    HISTORY_PATH,
    LEAD_TRADERS_PATH,
    LEADERBOARD_PAGE_SIZE,
    MAX_PAGES,
    PAGE_SIZE,
    POSITIONS_PATH,
    STATS_LAST_DAYS,
    STATS_PATH,
    STATUS_LIMITED,
    STATUS_NOT_FOUND,
    TRADER_NOT_EXIST_CODE,
    WEEKLY_PNL_PATH,
    BotSourceError,
    FileBotDataSource,
    LedgerUnavailableError,
    LiveBotDataSource,
)
from Agent.test.conftest import FIXED_AS_OF_MS, write_bot_dataset, write_market_dataset


def fast_bucket() -> TokenBucket:
    """A rate limiter wide enough to never actually throttle in a test that
    isn't specifically exercising the throttle -- avoids every unrelated test
    paying TokenBucket's real-clock refill wait."""
    return TokenBucket(capacity=10_000, period_seconds=0.001)


def make_trade(
    trade_id: str,
    *,
    subPos: str = "1.01",
    posSide: str = "long",
    instId: str = "ETH-USDT-SWAP",
    open_time_ms: int = 1_789_000_000_000,
    close_time_ms: int = 1_789_000_600_000,
    pnl: str = "12.5",
    unique_code: str = "CODE1",
) -> Dict[str, Any]:
    """One closed trade shaped exactly like a real OKX
    public-subpositions-history row (field-for-field identical to a sample
    pulled from Agent/data/cex/ETH/bot/bot_74F7C7A53CD18275/trade_list.json)."""
    return {
        "ccy": "USDT",
        "closeAvgPx": "2463.2",
        "closeTime": str(close_time_ms),
        "instId": instId,
        "instType": "SWAP",
        "lever": "4",
        "margin": "62.42",
        "mgnMode": "cross",
        "openAvgPx": "2472.1",
        "openTime": str(open_time_ms),
        "pnl": pnl,
        "pnlRatio": "-0.0157968237530844",
        "posSide": posSide,
        "subPos": subPos,
        "subPosId": trade_id,
        "uniqueCode": unique_code,
    }


def make_position(
    position_id: str,
    *,
    instId: str = "ETH-USDT-SWAP",
    subPos: str = "-53.15",
    posSide: str = "net",
    unique_code: str = "CODE1",
) -> Dict[str, Any]:
    """One open position shaped like a real public-current-subpositions row."""
    return {
        "ccy": "USDT",
        "instId": instId,
        "instType": "SWAP",
        "lever": "4",
        "margin": "3272.977",
        "markPx": "2491.18",
        "mgnMode": "cross",
        "openAvgPx": "2463.2",
        "openTime": "",
        "posSide": posSide,
        "subPos": subPos,
        "subPosId": position_id,
        "uniqueCode": unique_code,
        "upl": "-148.7137",
        "uplRatio": "-0.0454368301396556",
    }


def make_weekly(
    begin_ts: int = 1_788_710_400_000, pnl: str = "4136.65"
) -> Dict[str, Any]:
    return {"beginTs": str(begin_ts), "pnl": pnl, "pnlRatio": "0.0078"}


def make_leaderboard_row(
    unique_code: str,
    *,
    nick_name: str = "Algotoria",
    aum: str = "41542.9642391975249393",
    pnl: str = "31309.0008477841785782",
    pnl_ratio: str = "0.0596",
    lead_days: str = "873",
) -> Dict[str, Any]:
    """One row shaped like a real public-lead-traders `ranks[]` entry (field
    names match Agent/data/universe/lead_traders.json, a real snapshot)."""
    return {
        "uniqueCode": unique_code,
        "nickName": nick_name,
        "aum": aum,
        "pnl": pnl,
        "pnlRatio": pnl_ratio,
        "winRatio": "0.3556",
        "leadDays": lead_days,
        "copyTraderNum": "8",
        "maxCopyTraderNum": "301",
        "copyState": "0",
        "traderInsts": ["ETH-USDT-SWAP"],
    }


def make_stats(
    win_ratio: str = "0.4164", invest_amt: str = "541250.6980067396397748"
) -> Dict[str, Any]:
    """Shaped like a real public-stats row (see the task's own captured
    output for uniqueCode 74F7C7A53CD18275, lastDays=4)."""
    return {
        "avgSubPosNotional": "27107.9617",
        "ccy": "USDT",
        "curCopyTraderPnl": "10975.6982339762816995",
        "investAmt": invest_amt,
        "lossDays": "213",
        "profitDays": "152",
        "winRatio": win_ratio,
    }


class FakeOkxClient:
    """Stands in for Agent.backend.okx.client.OkxClient. Models real OKX
    cursor pagination (`after=<subPosId>` means "strictly after this row") so
    LiveBotDataSource's own pagination loop is exercised for real, not just a
    canned per-call return value.
    """

    def __init__(
        self,
        history_rows: Optional[List[Dict[str, Any]]] = None,
        positions: Optional[List[Dict[str, Any]]] = None,
        weekly: Optional[List[Dict[str, Any]]] = None,
        fail_paths: Optional[Dict[str, Exception]] = None,
        leaderboard_rows: Optional[List[Dict[str, Any]]] = None,
        stats: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.base_url = "https://www.okx.com"
        self.history_rows = history_rows or []
        self.positions = positions if positions is not None else []
        self.weekly = weekly if weekly is not None else []
        self.fail_paths = fail_paths or {}
        # Un-paginated: the full ranking this fake OKX holds. public_get pages
        # through it LEADERBOARD_PAGE_SIZE at a time, same as the real
        # endpoint, so LiveBotDataSource's own pagination loop is exercised
        # for real rather than handed one canned page.
        self.leaderboard_rows = leaderboard_rows or []
        # None means "OKX has no stats for this code" (empty data list),
        # matching how a code outside public-stats' coverage behaves.
        self.stats = stats
        self.calls: List[Any] = []

    def public_get(self, request_path: str, params: Optional[Dict[str, Any]] = None):
        params = dict(params or {})
        self.calls.append((request_path, params))
        if request_path in self.fail_paths:
            raise self.fail_paths[request_path]
        if request_path == HISTORY_PATH:
            return self._page_history(params)
        if request_path == POSITIONS_PATH:
            return list(self.positions)
        if request_path == WEEKLY_PNL_PATH:
            return list(self.weekly)
        if request_path == LEAD_TRADERS_PATH:
            return self._page_leaderboard(params)
        if request_path == STATS_PATH:
            assert params.get("lastDays") == STATS_LAST_DAYS
            return [self.stats] if self.stats is not None else []
        raise AssertionError(f"unexpected path {request_path}")

    def _page_leaderboard(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        limit = int(params["limit"])
        page = int(params["page"])
        assert "sortType" not in params, (
            "sortType narrows OKX's ranking and must never be sent"
        )
        start = (page - 1) * limit
        chunk = self.leaderboard_rows[start : start + limit]
        if not chunk:
            return [{"ranks": []}]
        return [{"ranks": chunk}]

    def _page_history(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        limit = int(params["limit"])
        after = params.get("after")
        if after is None:
            start = 0
        else:
            index = next(
                i
                for i, row in enumerate(self.history_rows)
                if str(row.get("subPosId")) == str(after)
            )
            start = index + 1
        return self.history_rows[start : start + limit]


class RepeatingPageOkxClient(FakeOkxClient):
    """Simulates a pathological OKX history endpoint that ignores the `after`
    cursor entirely and always answers with the same first page.

    Exists for exactly one test: that a page containing nothing but records
    already seen stops the pagination loop immediately (via the `not fresh`
    branch), rather than relying on MAX_PAGES to eventually cut it off. Real
    OKX cursor pagination (FakeOkxClient._page_history) can't produce this
    scenario on its own, since `after=<subPosId>` always advances -- this
    class exists purely to force the pathological case the dedupe check
    guards against.
    """

    def _page_history(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        limit = int(params["limit"])
        return self.history_rows[:limit]


# ---------------------------------------------------------------------------
# FileBotDataSource: must behave exactly like the inline file-reading code it
# replaces in Agent/backend/mcp/service.py.
# ---------------------------------------------------------------------------


def test_file_source_reads_overview_and_ledger_verbatim(tmp_path: Path):
    overview = {"uniqueCode": "TESTCODE", "nickName": "Test Bot", "aum": "1000"}
    bot_dir = write_bot_dataset(
        tmp_path,
        overview=overview,
        closed_trades=[{"subPosId": "1", "pnl": "5"}],
        open_positions=[{"subPosId": "2", "instId": "BTC-USDT-SWAP"}],
    )
    source = FileBotDataSource(tmp_path)

    read_overview = source.get_overview("unused", bot_dir=bot_dir)
    read_ledger = source.get_ledger("unused", bot_dir=bot_dir)

    assert read_overview == json.loads((bot_dir / "overview.json").read_text())
    assert read_ledger == json.loads((bot_dir / "trade_list.json").read_text())


def test_file_source_missing_file_returns_none(tmp_path: Path):
    bot_dir = tmp_path / "cex" / "TEST" / "bot" / "bot_empty"
    bot_dir.mkdir(parents=True)
    source = FileBotDataSource(tmp_path)

    assert source.get_overview("X", bot_dir=bot_dir) is None
    assert source.get_ledger("X", bot_dir=bot_dir) is None


def test_file_source_corrupt_json_raises(tmp_path: Path):
    bot_dir = tmp_path / "cex" / "TEST" / "bot" / "bot_bad"
    bot_dir.mkdir(parents=True)
    (bot_dir / "overview.json").write_text("not valid json{", encoding="utf-8")
    source = FileBotDataSource(tmp_path)

    with pytest.raises(BotSourceError):
        source.get_overview("X", bot_dir=bot_dir)


def test_file_source_non_object_json_raises(tmp_path: Path):
    bot_dir = tmp_path / "cex" / "TEST" / "bot" / "bot_list"
    bot_dir.mkdir(parents=True)
    (bot_dir / "trade_list.json").write_text("[1, 2, 3]", encoding="utf-8")
    source = FileBotDataSource(tmp_path)

    with pytest.raises(BotSourceError):
        source.get_ledger("X", bot_dir=bot_dir)


# ---------------------------------------------------------------------------
# LiveBotDataSource: structural parity with the file-based payload.
# ---------------------------------------------------------------------------


def test_live_payload_has_every_key_the_file_payload_has():
    """The regression this guards against: a live payload silently missing a
    field service.py reads off the file-based one (e.g. ledger_truncated,
    provenance) would not fail loudly -- it would just make step 2 mis-grade
    the bot. Compares against a real, already-crawled bot in Agent/data.
    """
    real_dir = Path(config.DATA_DIR) / "cex" / "ETH" / "bot" / "bot_74F7C7A53CD18275"
    assert real_dir.is_dir(), "fixture bot missing from Agent/data"
    file_source = FileBotDataSource(Path(config.DATA_DIR))
    file_overview = file_source.get_overview("74F7C7A53CD18275", bot_dir=real_dir)
    file_ledger = file_source.get_ledger("74F7C7A53CD18275", bot_dir=real_dir)

    client = FakeOkxClient(
        history_rows=[make_trade("T1", unique_code="74F7C7A53CD18275")],
        positions=[make_position("P1", unique_code="74F7C7A53CD18275")],
        weekly=[make_weekly()],
    )
    live_source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())
    live_overview = live_source.get_overview("74F7C7A53CD18275")
    live_ledger = live_source.get_ledger("74F7C7A53CD18275")

    missing_overview_keys = set(file_overview) - set(live_overview)
    missing_ledger_keys = set(file_ledger) - set(live_ledger)
    assert not missing_overview_keys, (
        f"live overview is missing: {missing_overview_keys}"
    )
    assert not missing_ledger_keys, f"live ledger is missing: {missing_ledger_keys}"


def test_live_pagination_collects_all_pages_in_order_without_duplicates():
    rows = [
        make_trade(f"T{i:04d}", open_time_ms=1_789_000_000_000 + i * 1000)
        for i in range(250)
    ]
    client = FakeOkxClient(history_rows=rows, positions=[], weekly=[])
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    ledger = source.get_ledger("CODE1")

    assert ledger["closed_trades_count"] == 250
    assert len(ledger["closed_trades"]) == 250
    ids = [row["subPosId"] for row in ledger["closed_trades"]]
    assert ids == [row["subPosId"] for row in rows]  # same order, no duplicates
    assert len(set(ids)) == 250
    assert ledger["ledger_truncated"] is False
    assert ledger["ledger_page_size"] == 100
    history_calls = [call for call in client.calls if call[0] == HISTORY_PATH]
    assert len(history_calls) == 3  # 100 + 100 + 50


def test_live_pagination_marks_truncated_when_page_cap_is_hit():
    rows = [make_trade(f"T{i:04d}") for i in range(1000)]
    client = FakeOkxClient(history_rows=rows, positions=[], weekly=[])
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket(), max_pages=3)

    ledger = source.get_ledger("CODE1")

    assert ledger["closed_trades_count"] == 300
    assert ledger["ledger_truncated"] is True


def test_default_max_pages_matches_crawl_bots_cap_exactly():
    """The task this source exists for: a live-fetched ledger must reach the
    SAME depth Agent/scripts/crawl_bots.py's own default (--max-pages 5,
    PAGE_SIZE=100 -> 500 trades) would have reached for the same bot, not 10x
    or 20x deeper. Uses a source with 2000 available trades specifically to
    prove the default cap actually bites rather than merely happening to
    match a smaller fixture."""
    assert MAX_PAGES == 5
    rows = [make_trade(f"T{i:04d}") for i in range(2000)]
    client = FakeOkxClient(history_rows=rows, positions=[], weekly=[])
    source = LiveBotDataSource(
        client=client, rate_limiter=fast_bucket()
    )  # default max_pages

    ledger = source.get_ledger("CODE1")

    assert ledger["closed_trades_count"] == 500
    assert len(ledger["closed_trades"]) == 500
    assert ledger["ledger_truncated"] is True
    history_calls = [call for call in client.calls if call[0] == HISTORY_PATH]
    assert len(history_calls) == MAX_PAGES == 5


def test_history_page_of_only_seen_records_stops_immediately():
    """The other half of "exactly like crawl_history": a full-size page that
    contributes zero fresh records must break the loop right there (the `not
    fresh` branch), the same way crawl_bots.crawl_history does -- not spin
    through the remaining pages up to max_pages. Guards against an infinite
    loop if OKX ever repeats a page instead of advancing the cursor."""
    rows = [make_trade(f"T{i:04d}") for i in range(PAGE_SIZE)]
    client = RepeatingPageOkxClient(history_rows=rows, positions=[], weekly=[])
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    ledger = source.get_ledger("CODE1")

    assert ledger["closed_trades_count"] == PAGE_SIZE
    assert len(set(row["subPosId"] for row in ledger["closed_trades"])) == PAGE_SIZE
    # Not truncated: the loop stopped because the second page was all-dupes,
    # not because it ran out of max_pages budget.
    assert ledger["ledger_truncated"] is False
    history_calls = [call for call in client.calls if call[0] == HISTORY_PATH]
    # Page 1: 100 fresh rows, doesn't break (full page). Page 2: OKX repeats
    # the exact same 100 rows -> zero fresh -> breaks immediately, so only 2
    # calls total instead of running to MAX_PAGES (5).
    assert len(history_calls) == 2


def test_negative_subpos_is_signed_by_okx_and_normalizes_downstream():
    """A short can come back with a negative subPos (see
    Agent/backend/mcp/trades/ledger.py's own comment on this -- an earlier bug
    here dropped 10.5% of one bot's ledger). LiveBotDataSource must not
    "fix" the sign itself: it passes the row through untouched and the
    existing TradeLedgerManager normalizes it, exactly as it does for
    file-sourced data.
    """
    trade = make_trade("T1", subPos="-8151", posSide="short", pnl="120.5")
    client = FakeOkxClient(history_rows=[trade], positions=[], weekly=[])
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    ledger = source.get_ledger("CODE1")
    assert ledger["closed_trades"][0]["subPos"] == "-8151"  # untouched passthrough

    parsed = TradeLedgerManager.parse_trade_list_with_diagnostics(ledger)
    assert parsed.rejected_count == 0
    assert len(parsed.trades) == 1
    item = parsed.trades[0]
    assert item.quantity == pytest.approx(8151.0)
    assert item.side == PositionSide.SHORT


def test_empty_instid_position_counts_without_breaking_downstream():
    trade = make_trade("T1")
    position = make_position("P1", instId="")
    client = FakeOkxClient(history_rows=[trade], positions=[position], weekly=[])
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    ledger = source.get_ledger("CODE1")

    assert ledger["positions_without_instrument"] == 1
    assert ledger["open_positions"][0]["instId"] == ""
    # Doesn't blow up the existing position parser either.
    snapshot = PositionSnapshotParser.parse(ledger)
    assert snapshot.declared_count == 1
    assert snapshot.unattributed_count == 1


def test_okx_error_raises_instead_of_returning_empty_ledger():
    client = FakeOkxClient(
        history_rows=[],
        positions=[],
        weekly=[],
        fail_paths={HISTORY_PATH: OkxApiError("50011", "boom")},
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    with pytest.raises(BotSourceError):
        source.get_ledger("CODE1")


def test_okx_transport_failure_raises():
    client = FakeOkxClient(
        history_rows=[],
        positions=[],
        weekly=[],
        fail_paths={POSITIONS_PATH: OkxTransportError("no route to host")},
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    with pytest.raises(BotSourceError):
        source.get_ledger("CODE1")


def test_all_empty_response_raises_rather_than_faking_no_trades():
    """The specific danger the task calls out: an empty ledger must never be
    handed to step 3 as if the bot simply never traded."""
    client = FakeOkxClient(history_rows=[], positions=[], weekly=[])
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    with pytest.raises(BotSourceError):
        source.get_ledger("CODE1")


def test_weekly_pnl_empty_is_not_an_error():
    """Unlike the ledger guard above, a bot with no *weekly* points yet is a
    legitimate, already-handled case (CapitalResolver falls back to
    CURRENT_AUM/UNAVAILABLE) -- get_overview must not refuse it."""
    client = FakeOkxClient(history_rows=[], positions=[], weekly=[])
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    overview = source.get_overview("CODE1")
    assert overview["weekly_pnl_history"] == []
    assert overview["uniqueCode"] == "CODE1"


def test_observed_at_ms_is_set_on_both_payloads():
    client = FakeOkxClient(
        history_rows=[make_trade("T1")], positions=[], weekly=[make_weekly()]
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    overview = source.get_overview("CODE1")
    ledger = source.get_ledger("CODE1")
    assert (
        isinstance(overview["observed_at_ms"], int) and overview["observed_at_ms"] > 0
    )
    assert isinstance(ledger["observed_at_ms"], int) and ledger["observed_at_ms"] > 0


# ---------------------------------------------------------------------------
# Profile enrichment: public-lead-traders (leaderboard) + public-stats.
# ---------------------------------------------------------------------------


def test_bot_present_in_leaderboard_gets_profile_fields_filled():
    board_row = make_leaderboard_row(
        "CODE1", nick_name="Algotoria", aum="41542.96", pnl="31309.0"
    )
    client = FakeOkxClient(
        history_rows=[make_trade("T1")],
        positions=[],
        weekly=[],
        leaderboard_rows=[board_row],
        stats=make_stats(),
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    overview = source.get_overview("CODE1")

    assert overview["nickName"] == "Algotoria"
    assert overview["aum"] == "41542.96"
    assert overview["pnl"] == "31309.0"
    assert overview["pnlRatio"] == board_row["pnlRatio"]
    assert overview["leadDays"] == board_row["leadDays"]
    assert overview["okx_rank"] == 1
    assert overview["provenance"]["profile_fields"] == (
        "OKX_LEADERBOARD_SNAPSHOT_BY_UNIQUECODE"
    )


def test_bot_missing_from_leaderboard_gets_none_not_a_raise():
    """Requirement: a bot that has dropped rank (or isn't covered by the
    ranking) must still produce a usable overview -- None fields, a reason in
    provenance, never an exception and never a guessed number."""
    client = FakeOkxClient(
        history_rows=[make_trade("T1")],
        positions=[],
        weekly=[],
        leaderboard_rows=[make_leaderboard_row("SOME_OTHER_CODE")],
        stats=None,
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    overview = source.get_overview("CODE1")  # never crawls

    assert overview["nickName"] == "CODE1"  # falls back to the code, not None
    assert overview["aum"] is None
    assert overview["pnl"] is None
    assert overview["pnlRatio"] is None
    assert overview["leadDays"] is None
    assert overview["okx_rank"] is None
    assert overview["winRatio"] is None
    assert overview["investAmt"] is None
    assert overview["provenance"]["profile_fields"] == "UNAVAILABLE"
    assert "ranking" in overview["provenance"]["profile_note"]


def test_leaderboard_is_paged_and_fetched_only_once_across_many_bots():
    """The task's central design constraint: paging the whole board must
    happen exactly once per process, no matter how many bots ask for a
    profile -- a per-bot filtered request is impossible anyway (OKX ignores
    uniqueCode on this endpoint) and re-paging per bot would blow the shared
    rate-limit budget for no reason.
    """
    rows = [make_leaderboard_row(f"CODE{i}") for i in range(45)]  # 3 pages of 20
    client = FakeOkxClient(
        history_rows=[make_trade("T1")],
        positions=[],
        weekly=[],
        leaderboard_rows=rows,
        stats=make_stats(),
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    first = source.get_overview("CODE0")
    board_calls_after_first = [c for c in client.calls if c[0] == LEAD_TRADERS_PATH]
    second = source.get_overview("CODE44")
    third = source.get_overview("CODE_NOT_ON_BOARD")
    board_calls_after_all = [c for c in client.calls if c[0] == LEAD_TRADERS_PATH]

    assert first["nickName"] == rows[0]["nickName"]
    assert second["okx_rank"] == 45
    assert third["aum"] is None
    # 45 rows at LEADERBOARD_PAGE_SIZE (20) = 3 full pages, then one more
    # (empty) page that tells the loop to stop -- 4 requests total, and never
    # again after the first get_overview call.
    assert len(board_calls_after_first) == 4
    assert len(board_calls_after_all) == 4
    assert [c[1]["page"] for c in board_calls_after_first] == [1, 2, 3, 4]


def test_leaderboard_pagination_never_sends_more_than_the_okx_page_cap():
    rows = [make_leaderboard_row(f"CODE{i}") for i in range(3)]
    client = FakeOkxClient(
        history_rows=[make_trade("T1")],
        positions=[],
        weekly=[],
        leaderboard_rows=rows,
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    source.get_overview("CODE0")

    board_calls = [c for c in client.calls if c[0] == LEAD_TRADERS_PATH]
    for _, params in board_calls:
        assert params["limit"] == LEADERBOARD_PAGE_SIZE == 20


def test_leaderboard_fetch_failure_degrades_to_unavailable_without_raising():
    client = FakeOkxClient(
        history_rows=[make_trade("T1")],
        positions=[],
        weekly=[],
        fail_paths={LEAD_TRADERS_PATH: OkxApiError("50011", "boom")},
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    overview = source.get_overview("CODE1")  # must not raise

    assert overview["aum"] is None
    assert overview["provenance"]["profile_fields"] == "UNAVAILABLE"

    # The failure is cached too: a second bot must not re-trigger the doomed
    # leaderboard pagination and spend more rate-limit budget on a call
    # already known to fail.
    calls_after_first = len([c for c in client.calls if c[0] == LEAD_TRADERS_PATH])
    source.get_overview("CODE2")
    calls_after_second = len([c for c in client.calls if c[0] == LEAD_TRADERS_PATH])
    assert calls_after_first == calls_after_second == 1


def test_public_stats_fills_win_ratio_and_invest_amt():
    client = FakeOkxClient(
        history_rows=[make_trade("T1")],
        positions=[],
        weekly=[],
        stats=make_stats(win_ratio="0.4164", invest_amt="541250.6980067396397748"),
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    overview = source.get_overview("CODE1")

    assert overview["winRatio"] == "0.4164"
    assert overview["investAmt"] == "541250.6980067396397748"
    stats_calls = [c for c in client.calls if c[0] == STATS_PATH]
    assert len(stats_calls) == 1
    assert stats_calls[0][1]["lastDays"] == STATS_LAST_DAYS
    assert stats_calls[0][1]["uniqueCode"] == "CODE1"


def test_public_stats_failure_leaves_win_ratio_none_without_raising():
    client = FakeOkxClient(
        history_rows=[make_trade("T1")],
        positions=[],
        weekly=[],
        leaderboard_rows=[make_leaderboard_row("CODE1")],
        fail_paths={STATS_PATH: OkxApiError("51000", "Parameter lastDays error")},
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    overview = source.get_overview("CODE1")  # must not raise

    assert overview["winRatio"] is None
    assert overview["investAmt"] is None
    # The rest of the profile, sourced from the leaderboard, is unaffected by
    # the stats endpoint failing -- the two are independent best-effort calls.
    assert overview["nickName"] == "Algotoria"
    assert overview["aum"] is not None


def test_overview_key_set_matches_file_source_for_a_real_bot():
    """The task's own most important test: any overview key the file source
    produces for a real, already-crawled bot must also be produced by the
    live source once both profile endpoints are wired up -- this is what
    would have caught the original gap (nick_name/aum/pnl/roi/calmar all
    silently blank) before it ever reached a report.
    """
    real_dir = Path(config.DATA_DIR) / "cex" / "ETH" / "bot" / "bot_74F7C7A53CD18275"
    assert real_dir.is_dir(), "fixture bot missing from Agent/data"
    file_overview = FileBotDataSource(Path(config.DATA_DIR)).get_overview(
        "74F7C7A53CD18275", bot_dir=real_dir
    )

    client = FakeOkxClient(
        history_rows=[make_trade("T1", unique_code="74F7C7A53CD18275")],
        positions=[],
        weekly=[make_weekly()],
        leaderboard_rows=[make_leaderboard_row("74F7C7A53CD18275")],
        stats=make_stats(),
    )
    live_overview = LiveBotDataSource(
        client=client, rate_limiter=fast_bucket()
    ).get_overview("74F7C7A53CD18275")

    missing = set(file_overview) - set(live_overview)
    assert not missing, (
        f"live overview is missing keys the file overview has: {missing}"
    )


# ---------------------------------------------------------------------------
# Rate limiting: must throttle, and a test proving it must not burn real time.
# ---------------------------------------------------------------------------


def test_rate_limit_throttles_via_fake_clock_never_real_sleep():
    fake_now = [0.0]
    sleeps: List[float] = []

    def clock() -> float:
        return fake_now[0]

    def sleep(seconds: float) -> None:
        # Simulate time passing during the sleep instead of actually waiting,
        # so this test proves the throttle engages without costing real time.
        sleeps.append(seconds)
        fake_now[0] += seconds

    bucket = TokenBucket(capacity=5, period_seconds=2.0, clock=clock, sleep=sleep)
    # 650 trades -> 7 history pages (600 + 50) + 1 positions call = 8 requests,
    # comfortably more than the bucket's capacity of 5. Needs an explicit
    # max_pages here (unrelated to what's under test -- rate limiting, not
    # ledger depth) because the default MAX_PAGES is now 5, matching
    # crawl_bots.py's own cap, which would otherwise truncate this fixture
    # at 500 trades / 5 pages before the throttle even gets exercised.
    rows = [make_trade(f"T{i:04d}") for i in range(650)]
    client = FakeOkxClient(history_rows=rows, positions=[], weekly=[])
    source = LiveBotDataSource(client=client, rate_limiter=bucket, max_pages=10)

    ledger = source.get_ledger("CODE1")

    assert ledger["closed_trades_count"] == 650
    history_calls = [call for call in client.calls if call[0] == HISTORY_PATH]
    assert len(history_calls) == 7
    assert len(sleeps) >= 1, (
        "8 requests against a 5-token bucket must block at least once"
    )


# ---------------------------------------------------------------------------
# BotObservationService: adding bot_source must not change default behaviour.
# ---------------------------------------------------------------------------


def test_service_without_bot_source_behaves_exactly_as_before(tmp_path: Path):
    overview = {
        "uniqueCode": "TESTCODE",
        "nickName": "Test Bot",
        "aum": "10000",
        "pnl": "500",
        "pnlRatio": "0.05",
    }
    closed_trades = [
        {
            "subPosId": "1",
            "instId": "BTC-USDT-SWAP",
            "posSide": "long",
            "openTime": "1789000000000",
            "closeTime": "1789000600000",
            "pnl": "12.5",
            "pnlRatio": "0.01",
            "margin": "100",
            "lever": "5",
            "openAvgPx": "60000",
            "closeAvgPx": "60100",
            "subPos": "0.01",
            "uniqueCode": "TESTCODE",
        }
    ]
    bot_dir = write_bot_dataset(
        tmp_path, overview=overview, closed_trades=closed_trades, open_positions=[]
    )
    folder = bot_dir.name
    asset = bot_dir.parent.parent.name
    venue = bot_dir.parent.parent.parent.name.upper()

    default_service = BotObservationService(tmp_path)
    explicit_service = BotObservationService(
        tmp_path, bot_source=FileBotDataSource(tmp_path)
    )
    kwargs = dict(
        venue_type=venue,
        seed=42,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=200,
        simulation_horizon=50,
    )

    default_result = default_service.get_bot_result(asset, folder, **kwargs)
    explicit_result = explicit_service.get_bot_result(asset, folder, **kwargs)

    assert default_result == explicit_result


def test_reference_data_dir_defaults_to_data_dir_unchanged_behaviour(tmp_path: Path):
    """`reference_data_dir=None` (the default) must behave EXACTLY like
    before this parameter existed: `_phase_timelines` still reads candles
    from `data_dir` itself. Proven here by showing the default service and
    one given `reference_data_dir=` the SAME directory as `data_dir`
    produce identical results -- if the default ever silently changed which
    directory `_phase_timelines` reads, this would catch it.
    """
    overview = {"uniqueCode": "TESTCODE", "nickName": "Test Bot", "aum": "10000"}
    write_bot_dataset(tmp_path, overview=overview, closed_trades=[], open_positions=[])
    write_market_dataset(tmp_path, asset="TEST", candle_count=300)

    kwargs = dict(
        venue_type="CEX",
        seed=42,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=200,
        simulation_horizon=50,
    )
    default_service = BotObservationService(tmp_path)
    explicit_same_dir_service = BotObservationService(
        tmp_path, reference_data_dir=tmp_path
    )

    default_result = default_service.get_bot_result("TEST", "bot_TEST", **kwargs)
    explicit_result = explicit_same_dir_service.get_bot_result(
        "TEST", "bot_TEST", **kwargs
    )

    assert default_result == explicit_result


def test_reference_data_dir_lets_phase_timelines_read_the_real_dataset(
    tmp_path: Path,
):
    """The exact bug this parameter fixes (see BotObservationService's own
    `__init__` docstring): a caller that isolates a bot's own read/write
    side behind a private scratch `data_dir` (e.g.
    `WebDataService._analyze_full`) used to ALSO starve `_phase_timelines`
    of every reference candle, since that method only ever read
    `self.data_dir` -- an empty scratch dir has none. Every trade then
    resolved to `MarketPhase.UNKNOWN` and phase coverage silently came back
    0%, even though the real dataset (kept in a separate directory here)
    has everything needed to label it.

    `reference_data_dir` splits the two: the bot's own files stay on the
    scratch dir, phase labelling reads the real one, and phase coverage
    recovers without moving the bot's own files anywhere.
    """
    real_root = tmp_path / "real"
    scratch_root = tmp_path / "scratch"
    last_candle_ms = 1_789_000_000_000
    write_market_dataset(
        real_root, asset="TEST", candle_count=300, last_candle_ms=last_candle_ms
    )
    # 5 hours before the last candle -- well past WARMUP_HOURS(200) into the
    # dataset, so this timestamp resolves to a real (non-UNKNOWN) phase.
    open_ms = last_candle_ms - 5 * 3_600_000
    closed_trades = [
        make_trade(
            "1",
            instId="TEST-USDT-SWAP",
            open_time_ms=open_ms,
            close_time_ms=open_ms + 600_000,
            unique_code="TESTCODE",
        )
    ]
    overview = {"uniqueCode": "TESTCODE", "nickName": "Test Bot", "aum": "10000"}
    write_bot_dataset(
        scratch_root,
        overview=overview,
        closed_trades=closed_trades,
        open_positions=[],
    )

    kwargs = dict(
        venue_type="CEX",
        seed=42,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=200,
        simulation_horizon=50,
    )

    # Bug reproduction: scratch dir alone has no candles at all.
    starved = BotObservationService(scratch_root).get_bot_result(
        "TEST", "bot_TEST", **kwargs
    )
    assert starved.strategy_observations.phase_coverage_pct == 0.0
    assert starved.strategy_observations.phase_breakdown == []

    # Fix: same scratch bot dir, but phase timelines read the real dataset.
    fixed = BotObservationService(
        scratch_root, reference_data_dir=real_root
    ).get_bot_result("TEST", "bot_TEST", **kwargs)
    assert fixed.strategy_observations.phase_coverage_pct == 100.0
    assert len(fixed.strategy_observations.phase_breakdown) == 1
    assert fixed.strategy_observations.phase_breakdown[0].trades == 1


def test_service_uses_bot_source_for_a_real_bot_and_reads_the_same_dataset(tmp_path):
    """Full seam check: point BotObservationService at a FileBotDataSource
    bound to a different (but identical-content) data_dir and confirm nothing
    in get_bot_result reaches around the abstraction back to disk directly."""
    overview = {"uniqueCode": "TESTCODE", "nickName": "Test Bot", "aum": "10000"}
    closed_trades = [
        {
            "subPosId": "1",
            "instId": "BTC-USDT-SWAP",
            "posSide": "long",
            "openTime": "1789000000000",
            "closeTime": "1789000600000",
            "pnl": "12.5",
            "pnlRatio": "0.01",
            "margin": "100",
            "lever": "5",
            "openAvgPx": "60000",
            "closeAvgPx": "60100",
            "subPos": "0.01",
            "uniqueCode": "TESTCODE",
        }
    ]
    write_bot_dataset(
        tmp_path, overview=overview, closed_trades=closed_trades, open_positions=[]
    )

    service = BotObservationService(tmp_path)
    result = service.get_bot_result(
        "TEST",
        "bot_TEST",
        venue_type="CEX",
        seed=42,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=200,
        simulation_horizon=50,
    )
    assert result.identity.unique_code == "TESTCODE"
    assert len(result.trade_ledger_summary) == 1


# ---------------------------------------------------------------------------
# 60004 ("Trader doesn't exist") on the ledger endpoints: LiveBotDataSource
# must classify this into LIMITED/NOT_FOUND rather than raising a plain
# BotSourceError -- see LedgerUnavailableError's docstring in bot_source.py
# and the real-API measurement in TRADER_NOT_EXIST_CODE's own comment (7/36
# = 19% of a real lead-trader sample hit this).
# ---------------------------------------------------------------------------


def test_60004_with_surviving_weekly_pnl_classifies_as_limited_not_a_raise():
    """The task's central scenario: a bot hides its ledger (60004 on both
    POSITIONS_PATH and HISTORY_PATH) but still publishes weekly PnL. This
    must come back as a classified LedgerUnavailableError(status=LIMITED)
    carrying that weekly data -- never a generic BotSourceError that would
    force a caller to treat it exactly like an OKX outage."""
    client = FakeOkxClient(
        weekly=[make_weekly()],
        fail_paths={
            POSITIONS_PATH: OkxApiError(TRADER_NOT_EXIST_CODE, "Trader doesn't exist"),
            HISTORY_PATH: OkxApiError(TRADER_NOT_EXIST_CODE, "Trader doesn't exist"),
        },
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    with pytest.raises(LedgerUnavailableError) as excinfo:
        source.get_ledger("CODE1")

    exc = excinfo.value
    assert exc.status == STATUS_LIMITED
    assert exc.code == "CODE1"
    assert exc.weekly == [make_weekly()]
    assert "60004" in str(exc)
    assert "order book" in str(exc)


def test_60004_with_surviving_leaderboard_row_classifies_as_limited():
    """Weekly-pnl empty but the bot still ranks -- public-lead-traders alone
    is enough evidence that the code is real, so this is still LIMITED."""
    client = FakeOkxClient(
        weekly=[],
        leaderboard_rows=[make_leaderboard_row("CODE1")],
        fail_paths={
            POSITIONS_PATH: OkxApiError(TRADER_NOT_EXIST_CODE, "Trader doesn't exist"),
        },
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    with pytest.raises(LedgerUnavailableError) as excinfo:
        source.get_ledger("CODE1")

    exc = excinfo.value
    assert exc.status == STATUS_LIMITED
    assert exc.profile is not None
    assert exc.profile["uniqueCode"] == "CODE1"


def test_60004_with_surviving_public_stats_classifies_as_limited():
    """Neither weekly-pnl nor the leaderboard has this code, but public-stats
    still does -- still enough to call this LIMITED rather than NOT_FOUND."""
    client = FakeOkxClient(
        weekly=[],
        leaderboard_rows=[],
        stats=make_stats(),
        fail_paths={
            POSITIONS_PATH: OkxApiError(TRADER_NOT_EXIST_CODE, "Trader doesn't exist"),
        },
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    with pytest.raises(LedgerUnavailableError) as excinfo:
        source.get_ledger("CODE1")

    assert excinfo.value.status == STATUS_LIMITED
    assert excinfo.value.stats == make_stats()


def test_garbage_code_nowhere_classifies_as_not_found_with_vietnamese_message():
    """A uniqueCode that is wrong/fabricated: 60004 on the ledger AND nothing
    in the leaderboard, weekly-pnl, or public-stats either. Must come back
    NOT_FOUND, distinctly from LIMITED, with a clear Vietnamese explanation."""
    client = FakeOkxClient(
        weekly=[],
        leaderboard_rows=[],
        stats=None,
        fail_paths={
            POSITIONS_PATH: OkxApiError(TRADER_NOT_EXIST_CODE, "Trader doesn't exist"),
            HISTORY_PATH: OkxApiError(TRADER_NOT_EXIST_CODE, "Trader doesn't exist"),
        },
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    with pytest.raises(LedgerUnavailableError) as excinfo:
        source.get_ledger("GARBAGE")

    exc = excinfo.value
    assert exc.status == STATUS_NOT_FOUND
    assert exc.profile is None
    assert exc.stats is None
    assert not exc.weekly
    assert "was not found" in str(exc) or "nonexistent" in str(exc)


def test_weekly_pnl_probe_swallows_its_own_okx_error_during_classification():
    """The weekly-pnl probe used only for LIMITED/NOT_FOUND classification is
    best-effort, exactly like _fetch_public_stats: an error fetching it must
    not blow up the classification, it must just count as "no evidence"."""
    client = FakeOkxClient(
        weekly=[],
        leaderboard_rows=[],
        stats=None,
        fail_paths={
            POSITIONS_PATH: OkxApiError(TRADER_NOT_EXIST_CODE, "Trader doesn't exist"),
            WEEKLY_PNL_PATH: OkxApiError(TRADER_NOT_EXIST_CODE, "Trader doesn't exist"),
        },
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    with pytest.raises(LedgerUnavailableError) as excinfo:
        source.get_ledger("GARBAGE")

    assert excinfo.value.status == STATUS_NOT_FOUND


def test_60004_on_a_non_ledger_endpoint_is_not_reclassified():
    """60004 is only special-cased on the ledger endpoints themselves. If
    (hypothetically) public-stats answered 60004, that must stay a plain
    best-effort None, not a ledger classification -- _fetch_public_stats
    already swallows any OkxError, so this only guards that behaviour keeps
    working unchanged."""
    client = FakeOkxClient(
        history_rows=[make_trade("T1")],
        positions=[],
        weekly=[],
        fail_paths={
            STATS_PATH: OkxApiError(TRADER_NOT_EXIST_CODE, "Trader doesn't exist")
        },
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    ledger = source.get_ledger("CODE1")
    assert ledger["closed_trades_count"] == 1

    overview = source.get_overview("CODE1")
    assert overview["winRatio"] is None


def test_other_okx_api_errors_on_ledger_endpoints_still_raise_plainly():
    """Regression guard: a non-60004 OkxApiError on the ledger endpoints must
    keep raising a plain BotSourceError, exactly like before this task --
    only 60004 gets the classification treatment."""
    client = FakeOkxClient(
        history_rows=[],
        positions=[],
        weekly=[],
        fail_paths={HISTORY_PATH: OkxApiError("50011", "boom")},
    )
    source = LiveBotDataSource(client=client, rate_limiter=fast_bucket())

    with pytest.raises(BotSourceError) as excinfo:
        source.get_ledger("CODE1")
    assert not isinstance(excinfo.value, LedgerUnavailableError)
