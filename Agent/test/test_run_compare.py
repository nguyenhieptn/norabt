"""Tests for the --source/--out-dir wiring in Agent/backend/run_report.py and
the two comparison modes in Agent/backend/run_compare.py.

No test here makes a real network call. Live sources are exercised only
through code paths already proven not to touch the network
(LiveMarketDataSource.resolve_venue for DEX raises before any HTTP request --
see market_source.py's get_market_result, which calls resolve_venue before
anything else) or are replaced outright with fakes/sentinels via monkeypatch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

import Agent.backend.run_compare as run_compare
import Agent.backend.run_report as run_report
from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.market.service import MarketService
from Agent.backend.mcp.service import BotDataUnavailableError, BotObservationService
from Agent.backend.qc.reporting.cohort import (
    BotEvaluationRow,
    CohortAssessmentService,
    MarketSnapshotRow,
)
from Agent.backend.qc.reporting.data_report import DataReportService
from Agent.backend.qc.reporting.market_report import MarketRegimeService
from Agent.backend.qc.reporting.pair_report import PairedBotReportService
from Agent.backend.run_compare import (
    GROUP_ANOMALY,
    GROUP_DRIFT,
    GROUP_SAME,
    GROUP_TIME,
    classify_bot_comparison,
    compare_cohorts,
    compare_same_data,
    render_live_vs_file,
    render_same_data,
)
from Agent.backend.sources.bot_source import FileBotDataSource
from Agent.backend.sources.market_source import (
    FileMarketDataSource,
    LiveMarketDataSource,
    MarketDataUnavailableError,
)

SIM_ITERATIONS = 200
SIM_HORIZON = 50
FIXED_MS = 1_789_230_000_000


# --------------------------------------------------------------------------- #
# Synthetic bot payload -- shaped like a real live overview/ledger fetch, but
# built by hand so no test needs the network.
# --------------------------------------------------------------------------- #


def _overview(**overrides: Any) -> Dict[str, Any]:
    base = {
        "uniqueCode": "TESTCODE",
        "nickName": "Test Bot",
        "aum": "1000",
        "pnl": "50",
        "pnlRatio": "0.05",
        "leadDays": 100,
        "winRatio": "0.6",
        "observed_at_ms": FIXED_MS,
        "provenance": {"profile_fields": "OKX_LEADERBOARD_SNAPSHOT_BY_UNIQUECODE"},
    }
    base.update(overrides)
    return base


def _trade(trade_id: str, **overrides: Any) -> Dict[str, Any]:
    base = {
        "ccy": "USDT",
        "closeAvgPx": "2463.2",
        "closeTime": "1789000600000",
        "instId": "ETH-USDT-SWAP",
        "instType": "SWAP",
        "lever": "4",
        "margin": "62.42",
        "mgnMode": "cross",
        "openAvgPx": "2472.1",
        "openTime": "1789000000000",
        "pnl": "12.5",
        "pnlRatio": "-0.0157968237530844",
        "posSide": "long",
        "subPos": "1.01",
        "subPosId": trade_id,
        "uniqueCode": "TESTCODE",
    }
    base.update(overrides)
    return base


def _ledger(
    trades: Optional[List[Dict[str, Any]]] = None, **overrides: Any
) -> Dict[str, Any]:
    base = {
        "uniqueCode": "TESTCODE",
        "open_positions_count": 0,
        "open_positions": [],
        "closed_trades": trades if trades is not None else [_trade("t1")],
        "observed_at_ms": FIXED_MS,
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------- #
# Kiểu A -- compare_same_data (Agent/backend/run_compare.py)
# --------------------------------------------------------------------------- #


class TestCompareSameData:
    def test_identical_payload_matches_exactly(self) -> None:
        cmp = compare_same_data(
            _overview(),
            _ledger(),
            asset="ETH",
            unique_code="TESTCODE",
            venue_type="CEX",
            as_of_ms=FIXED_MS,
            simulation_iterations=SIM_ITERATIONS,
            simulation_horizon=SIM_HORIZON,
        )
        assert cmp.identical
        assert cmp.fatal_diffs == []
        assert cmp.file_result.model_dump(mode="json") == cmp.fake_result.model_dump(
            mode="json"
        )

    def test_render_reports_success(self) -> None:
        cmp = compare_same_data(
            _overview(),
            _ledger(),
            asset="ETH",
            unique_code="TESTCODE",
            as_of_ms=FIXED_MS,
            simulation_iterations=SIM_ITERATIONS,
            simulation_horizon=SIM_HORIZON,
        )
        text = render_same_data(cmp)
        assert "SO SÁNH KIỂU A" in text
        assert "KẾT LUẬN: ĐÚNG" in text

    def test_detects_a_real_divergence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The diff machinery must actually catch a mismatch, not just always
        report success. Tamper with FileBotDataSource only, so the two paths
        disagree, and confirm compare_same_data flags it as a fatal diff."""
        original_get_ledger = FileBotDataSource.get_ledger

        def tampered_get_ledger(self, unique_code, bot_dir=None):
            payload = dict(original_get_ledger(self, unique_code, bot_dir))
            payload["closed_trades"] = [
                dict(t, pnl="999999") for t in payload["closed_trades"]
            ]
            return payload

        monkeypatch.setattr(FileBotDataSource, "get_ledger", tampered_get_ledger)
        cmp = compare_same_data(
            _overview(),
            _ledger(),
            asset="ETH",
            unique_code="TESTCODE",
            as_of_ms=FIXED_MS,
            simulation_iterations=SIM_ITERATIONS,
            simulation_horizon=SIM_HORIZON,
        )
        assert not cmp.identical
        assert cmp.fatal_diffs
        assert "KẾT LUẬN: SAI" in render_same_data(cmp)


# --------------------------------------------------------------------------- #
# Kiểu B -- classify_bot_comparison / compare_cohorts / render_live_vs_file
# --------------------------------------------------------------------------- #


def _row(**overrides: Any) -> BotEvaluationRow:
    base = dict(
        rank=1,
        status="EVALUATED",
        bot_id="BOT_X_ETH",
        unique_code="X",
        nick_name="X",
        traded_symbol="ETH",
        asset_context="ETH",
        venue_type="CEX",
        snapshot_venue="CEX",
        bot_folder="bot_X",
        conclusion="ok",
        trade_count=100,
        risk_tier="WATCH",
        risk_score=10.0,
        declared_lead_days=100,
    )
    base.update(overrides)
    return BotEvaluationRow(**base)


def _market(**overrides: Any) -> MarketSnapshotRow:
    base = dict(
        symbol="ETH",
        venue_type="CEX",
        trend="UP",
        volatility="LOW",
        liquidity_tier="DEEP",
        flow_bias="BUY",
        last_price=100.0,
        data_quality=0.9,
    )
    base.update(overrides)
    return MarketSnapshotRow(**base)


class TestClassifyBotComparison:
    def test_identical_rows_are_same(self) -> None:
        cmp = classify_bot_comparison(_row(), _row())
        assert cmp.group == GROUP_SAME
        assert not cmp.tier_changed

    def test_lead_days_only_diff_is_time(self) -> None:
        cmp = classify_bot_comparison(_row(), _row(declared_lead_days=102))
        assert cmp.group == GROUP_TIME

    def test_market_only_diff_is_drift(self) -> None:
        cmp = classify_bot_comparison(
            _row(market=_market()),
            _row(market=_market(trend="DOWN", volatility="HIGH", last_price=110.0)),
        )
        assert cmp.group == GROUP_DRIFT
        assert "thị trường" in cmp.explanation

    def test_trade_count_delta_explains_drift(self) -> None:
        cmp = classify_bot_comparison(
            _row(trade_count=100, risk_score=10.0),
            _row(trade_count=107, risk_score=15.0),
        )
        assert cmp.group == GROUP_DRIFT
        assert "+7" in cmp.explanation

    def test_unexplained_diff_is_anomaly_never_drift(self) -> None:
        """The one rule this module must never break: an unexplained numeric
        difference (identical trade_count, no market change) must land in
        BẤT THƯỜNG, never get waved through as DỮ LIỆU TRÔI."""
        cmp = classify_bot_comparison(
            _row(trade_count=100, risk_score=10.0),
            _row(trade_count=100, risk_score=80.0),
        )
        assert cmp.group == GROUP_ANOMALY
        assert cmp.group != GROUP_DRIFT

    def test_tier_change_is_flagged_alongside_its_group(self) -> None:
        cmp = classify_bot_comparison(
            _row(risk_tier="WATCH", trade_count=100),
            _row(risk_tier="CRITICAL", trade_count=107),
        )
        assert cmp.tier_changed
        assert cmp.group == GROUP_DRIFT  # explained by the trade-count delta

    def test_failed_row_on_either_side_is_anomaly(self) -> None:
        cmp = classify_bot_comparison(_row(status="FAILED", error="lỗi crawl"), _row())
        assert cmp.group == GROUP_ANOMALY
        cmp = classify_bot_comparison(_row(), _row(status="FAILED", error="lỗi OKX"))
        assert cmp.group == GROUP_ANOMALY

    def test_bot_present_on_only_one_side_is_anomaly(self) -> None:
        results = compare_cohorts(
            [_row(unique_code="A")],
            [_row(unique_code="A"), _row(unique_code="B")],
        )
        by_code = {r.unique_code: r for r in results}
        assert by_code["B"].group == GROUP_ANOMALY


class TestRenderLiveVsFile:
    def test_flags_anomaly_group_in_conclusion(self) -> None:
        comparisons = compare_cohorts(
            [
                _row(unique_code="A"),
                _row(unique_code="B", trade_count=100, risk_score=10.0),
            ],
            [
                _row(unique_code="A"),
                _row(unique_code="B", trade_count=100, risk_score=80.0),
            ],
        )
        text = render_live_vs_file(comparisons, FIXED_MS)
        assert "BẤT THƯỜNG" in text
        assert "CHƯA tương đương" in text

    def test_all_clear_conclusion_when_nothing_anomalous(self) -> None:
        comparisons = compare_cohorts([_row(unique_code="A")], [_row(unique_code="A")])
        text = render_live_vs_file(comparisons, FIXED_MS)
        assert "nhóm BẤT THƯỜNG rỗng" in text

    def test_tier_change_is_called_out(self) -> None:
        comparisons = compare_cohorts(
            [_row(unique_code="A", risk_tier="WATCH", trade_count=100)],
            [_row(unique_code="A", risk_tier="CRITICAL", trade_count=110)],
        )
        text = render_live_vs_file(comparisons, FIXED_MS)
        assert "ĐỔI XẾP LOẠI" in text
        assert "WATCH → CRITICAL" in text


# --------------------------------------------------------------------------- #
# DEX in live mode: must degrade cleanly, never crash, never look "risk-free".
# --------------------------------------------------------------------------- #


class TestDexUnsupportedInLiveMode:
    def test_resolve_venue_raises_a_clear_vietnamese_message(self) -> None:
        with pytest.raises(MarketDataUnavailableError) as excinfo:
            LiveMarketDataSource().resolve_venue("PEPE", "DEX")
        message = str(excinfo.value)
        assert "DEX" in message
        assert "OKX" in message

    def test_market_regime_service_does_not_crash_on_a_dex_asset(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "dex" / "PEPE" / "market").mkdir(parents=True)
        service = MarketRegimeService(tmp_path, EvaluationMode.SNAPSHOT)
        # resolve_venue raises for DEX before any HTTP call is made (see
        # market_source.py's get_market_result: resolve_venue runs first), so
        # this genuinely makes no network request.
        run_report.apply_live_source(
            service,
            data_dir=tmp_path,
            mode=EvaluationMode.SNAPSHOT,
            market_source=LiveMarketDataSource(),
        )
        report = service.build(as_of_ms=FIXED_MS)
        assert report.rows == []
        assert "DEX/PEPE" in report.failures
        # Never empty/silent: the reason must be a real Vietnamese-readable
        # explanation, not a blank string that reads as "no risk here".
        assert report.failures["DEX/PEPE"]
        assert "OKX" in report.failures["DEX/PEPE"]


# --------------------------------------------------------------------------- #
# apply_live_source / build_live_sources / default_selection_codes
# (Agent/backend/run_report.py)
# --------------------------------------------------------------------------- #


class _MarkerBotSource(FileBotDataSource):
    """Distinguishable-by-identity stand-in; never reads/writes anything."""


class _MarkerMarketSource(FileMarketDataSource):
    """Distinguishable-by-identity stand-in; never reads/writes anything."""


class TestApplyLiveSource:
    @pytest.mark.parametrize(
        "make_service, market_attr, bot_attr",
        [
            (lambda d: DataReportService(d, EvaluationMode.SNAPSHOT), "market", None),
            (
                lambda d: PairedBotReportService(d, EvaluationMode.SNAPSHOT),
                "market",
                "bots",
            ),
            (
                lambda d: MarketRegimeService(d, EvaluationMode.SNAPSHOT),
                "market_service",
                None,
            ),
            (
                lambda d: CohortAssessmentService(d, EvaluationMode.SNAPSHOT),
                "market_service",
                "bot_service",
            ),
        ],
    )
    def test_swaps_the_attribute_each_real_service_actually_uses(
        self, tmp_path: Path, make_service, market_attr, bot_attr
    ) -> None:
        service = make_service(tmp_path)
        marker_market = _MarkerMarketSource(tmp_path)
        marker_bot = _MarkerBotSource(tmp_path)

        run_report.apply_live_source(
            service,
            data_dir=tmp_path,
            mode=EvaluationMode.SNAPSHOT,
            bot_source=marker_bot,
            market_source=marker_market,
        )

        market_service = getattr(service, market_attr)
        assert isinstance(market_service, MarketService)
        assert market_service.market_source is marker_market

        if bot_attr:
            bot_service = getattr(service, bot_attr)
            assert isinstance(bot_service, BotObservationService)
            assert bot_service._bot_source is marker_bot

    def test_none_sources_leave_the_service_untouched(self, tmp_path: Path) -> None:
        """--source file passes bot_source=market_source=None -- this must be
        a true no-op, which is what keeps the default path byte-for-byte the
        old behaviour (no regression on the 394 pre-existing tests)."""
        service = CohortAssessmentService(tmp_path, EvaluationMode.SNAPSHOT)
        original_market, original_bots = service.market_service, service.bot_service
        run_report.apply_live_source(
            service, data_dir=tmp_path, mode=EvaluationMode.SNAPSHOT
        )
        assert service.market_service is original_market
        assert service.bot_service is original_bots


class TestBuildLiveSources:
    def test_returns_progress_wrapped_live_sources_with_no_network_call(self) -> None:
        bot_source, market_source = run_report.build_live_sources()
        assert isinstance(bot_source, run_report._ProgressBotSource)
        assert isinstance(market_source, run_report._ProgressMarketSource)
        # Sharing one OkxClient across both is deliberate (see build_live_sources'
        # docstring): confirm it actually happened rather than each source
        # getting its own.
        assert bot_source._inner._client is market_source._inner._client


# --------------------------------------------------------------------------- #
# _MemoizedMarketService / _MemoizedBotObservationService
# (Agent/backend/run_report.py) -- the in-process cache that sits in front of
# the one shared MarketService/BotObservationService main() now builds.
#
# Both wrapped services below are hand-rolled counting fakes, not the real
# MarketService/BotObservationService: the point of these tests is the
# wrapper's own caching logic (correct key, no false hits, no caching of a
# failure), which is independent of what the wrapped class actually does.
# TestSharedServicesAcrossReports further down exercises the real classes
# through run_report.main() end to end.
# --------------------------------------------------------------------------- #


class _CountingMarketService:
    """Records every get_market_result() call it actually received and
    returns a fresh, distinguishable dict each time -- so a cache bug that
    returns *some* previous result instead of a fabricated new one is still
    caught by an equality check, not just a call-count check."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def get_market_result(
        self,
        symbol: str,
        venue_type: Optional[str] = None,
        as_of_ms: Optional[int] = None,
    ) -> Dict[str, Any]:
        self.calls.append(
            {"symbol": symbol, "venue_type": venue_type, "as_of_ms": as_of_ms}
        )
        return {
            "symbol": symbol,
            "venue_type": venue_type,
            "as_of_ms": as_of_ms,
            "call_index": len(self.calls),
        }


class _CountingBotService:
    """get_bot_result() counterpart to _CountingMarketService above."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []

    def get_bot_result(
        self,
        asset: str,
        bot_folder_name: str = "bot_top_performer",
        seed: Optional[int] = 42,
        venue_type: Optional[str] = None,
        as_of_ms: Optional[int] = None,
        simulation_iterations: int = 10_000,
        simulation_horizon: Optional[int] = None,
        selection_trials: Optional[int] = None,
    ) -> Dict[str, Any]:
        self.calls.append(
            {
                "asset": asset,
                "bot_folder_name": bot_folder_name,
                "seed": seed,
                "venue_type": venue_type,
                "as_of_ms": as_of_ms,
                "simulation_iterations": simulation_iterations,
                "simulation_horizon": simulation_horizon,
                "selection_trials": selection_trials,
            }
        )
        return {
            "asset": asset,
            "bot_folder_name": bot_folder_name,
            "as_of_ms": as_of_ms,
            "seed": seed,
            "call_index": len(self.calls),
        }


class TestMemoizedMarketService:
    def test_identical_call_hits_cache_and_returns_the_identical_result(self) -> None:
        inner = _CountingMarketService()
        wrapped = run_report._MemoizedMarketService(inner)

        first = wrapped.get_market_result("ETH", venue_type="CEX", as_of_ms=1_000)
        second = wrapped.get_market_result("ETH", venue_type="CEX", as_of_ms=1_000)

        assert len(inner.calls) == 1  # the real service was asked only once
        assert first == second
        assert wrapped.cache_hits == 1
        assert wrapped.cache_calls == 2

    def test_different_as_of_ms_is_never_served_from_cache(self) -> None:
        """The one rule this task calls out by name: as_of_ms drifting must
        never be papered over by the cache -- it changes what "as of" means
        for the whole report."""
        inner = _CountingMarketService()
        wrapped = run_report._MemoizedMarketService(inner)

        first = wrapped.get_market_result("ETH", as_of_ms=1_000)
        second = wrapped.get_market_result("ETH", as_of_ms=2_000)

        assert len(inner.calls) == 2
        assert wrapped.cache_hits == 0
        assert first["as_of_ms"] != second["as_of_ms"]

    def test_different_venue_type_is_never_served_from_cache(self) -> None:
        inner = _CountingMarketService()
        wrapped = run_report._MemoizedMarketService(inner)

        wrapped.get_market_result("ETH", venue_type="CEX", as_of_ms=1_000)
        wrapped.get_market_result("ETH", venue_type="DEX", as_of_ms=1_000)

        assert len(inner.calls) == 2

    def test_a_raised_error_is_never_cached(self) -> None:
        """A failed call must not poison the cache with a fabricated success,
        nor must it be remembered as a permanent failure -- the next call
        with the same arguments has to retry exactly like the unwrapped
        service would."""

        class _AlwaysFails:
            def __init__(self) -> None:
                self.calls = 0

            def get_market_result(self, symbol, venue_type=None, as_of_ms=None):
                self.calls += 1
                raise MarketDataUnavailableError("no candles")

        inner = _AlwaysFails()
        wrapped = run_report._MemoizedMarketService(inner)
        with pytest.raises(MarketDataUnavailableError):
            wrapped.get_market_result("PEPE", as_of_ms=1_000)
        with pytest.raises(MarketDataUnavailableError):
            wrapped.get_market_result("PEPE", as_of_ms=1_000)
        assert inner.calls == 2
        assert wrapped.cache_hits == 0

    def test_unwrapped_attributes_forward_to_the_real_service(
        self, tmp_path: Path
    ) -> None:
        """qc/reporting/* only ever calls get_market_result() on this
        wrapper, but __getattr__ still has to forward everything else
        transparently for it to be a true drop-in stand-in for MarketService."""
        real = MarketService(tmp_path, EvaluationMode.SNAPSHOT)
        wrapped = run_report._MemoizedMarketService(real)
        assert wrapped.data_dir is real.data_dir
        assert wrapped.market_source is real.market_source


class TestMemoizedBotObservationService:
    def test_identical_call_hits_cache_and_returns_the_identical_result(self) -> None:
        inner = _CountingBotService()
        wrapped = run_report._MemoizedBotObservationService(inner)

        first = wrapped.get_bot_result(
            "ETH", "bot_X", seed=42, venue_type="CEX", as_of_ms=1_000
        )
        second = wrapped.get_bot_result(
            "ETH", "bot_X", seed=42, venue_type="CEX", as_of_ms=1_000
        )

        assert len(inner.calls) == 1  # the real service was asked only once
        assert first == second
        assert wrapped.cache_hits == 1
        assert wrapped.cache_calls == 2

    def test_different_as_of_ms_is_never_served_from_cache(self) -> None:
        inner = _CountingBotService()
        wrapped = run_report._MemoizedBotObservationService(inner)

        first = wrapped.get_bot_result("ETH", "bot_X", as_of_ms=1_000)
        second = wrapped.get_bot_result("ETH", "bot_X", as_of_ms=2_000)

        assert len(inner.calls) == 2
        assert first["as_of_ms"] != second["as_of_ms"]

    def test_different_seed_is_never_served_from_cache(self) -> None:
        """Two Monte Carlo runs with a different seed are not the same call,
        even if every other argument matches."""
        inner = _CountingBotService()
        wrapped = run_report._MemoizedBotObservationService(inner)

        wrapped.get_bot_result("ETH", "bot_X", seed=1, as_of_ms=1_000)
        wrapped.get_bot_result("ETH", "bot_X", seed=2, as_of_ms=1_000)

        assert len(inner.calls) == 2

    def test_different_selection_trials_is_never_served_from_cache(self) -> None:
        """selection_trials feeds the deflated Sharpe calculation, so two
        calls that differ only there must not collapse into one cache entry
        even though every other argument (asset/folder/venue/seed/as_of_ms/
        iterations/horizon) matches -- see _MemoizedBotObservationService's
        docstring for why it is part of the key."""
        inner = _CountingBotService()
        wrapped = run_report._MemoizedBotObservationService(inner)

        wrapped.get_bot_result("ETH", "bot_X", as_of_ms=1_000, selection_trials=10)
        wrapped.get_bot_result("ETH", "bot_X", as_of_ms=1_000, selection_trials=68)

        assert len(inner.calls) == 2

    def test_a_raised_error_is_never_cached(self) -> None:
        class _AlwaysFails:
            def __init__(self) -> None:
                self.calls = 0

            def get_bot_result(self, asset, bot_folder_name="bot_top_performer", **kw):
                self.calls += 1
                raise BotDataUnavailableError("missing ledger")

        inner = _AlwaysFails()
        wrapped = run_report._MemoizedBotObservationService(inner)
        with pytest.raises(BotDataUnavailableError):
            wrapped.get_bot_result("ETH", "bot_X", as_of_ms=1_000)
        with pytest.raises(BotDataUnavailableError):
            wrapped.get_bot_result("ETH", "bot_X", as_of_ms=1_000)
        assert inner.calls == 2
        assert wrapped.cache_hits == 0

    def test_unwrapped_attributes_forward_to_the_real_service(
        self, tmp_path: Path
    ) -> None:
        real = BotObservationService(tmp_path, EvaluationMode.SNAPSHOT)
        wrapped = run_report._MemoizedBotObservationService(real)
        assert wrapped.data_dir is real.data_dir
        assert wrapped._bot_source is real._bot_source


class TestDefaultSelectionCodes:
    def test_bot_overrides_everything(self, tmp_path: Path) -> None:
        assert run_report.default_selection_codes(
            tmp_path, bot="ABC", all_bots=True
        ) == {"ABC"}

    def test_all_bots_returns_none(self, tmp_path: Path) -> None:
        assert (
            run_report.default_selection_codes(tmp_path, bot=None, all_bots=True)
            is None
        )

    def test_missing_selection_file_returns_none(self, tmp_path: Path) -> None:
        assert (
            run_report.default_selection_codes(tmp_path, bot=None, all_bots=False)
            is None
        )

    def test_reads_selection_file_when_present(self, tmp_path: Path) -> None:
        selection_dir = tmp_path / "universe"
        selection_dir.mkdir()
        (selection_dir / "bot_selection.json").write_text(
            json.dumps({"unique_codes": ["A", "B"]}), encoding="utf-8"
        )
        assert run_report.default_selection_codes(
            tmp_path, bot=None, all_bots=False
        ) == {"A", "B"}


# --------------------------------------------------------------------------- #
# run_report.main(): --source/--out-dir CLI wiring, isolated from the heavy
# qc/reporting services via recording doubles -- these tests are about
# run_report.py's own new logic, not a re-test of already-verified services.
# --------------------------------------------------------------------------- #


class _FakeReport:
    """Minimal stand-in for a *Report pydantic model: only what main() touches
    under --json (model_dump) or under persist_* (blocks/rows) is needed."""

    blocks: List[Any] = []
    rows: List[Any] = []

    def model_dump(self, mode: str = "json") -> Dict[str, Any]:
        return {"fake": True}


class _RecordingCohortService:
    instances: List["_RecordingCohortService"] = []

    def __init__(
        self, evaluation_mode: Optional[EvaluationMode] = None, **_: Any
    ) -> None:
        self.evaluation_mode = evaluation_mode
        self.market_service = "unset-market"
        self.bot_service = "unset-bot"
        self.scan_kwargs: Optional[Dict[str, Any]] = None
        type(self).instances.append(self)

    def scan(self, **kwargs: Any) -> _FakeReport:
        self.scan_kwargs = kwargs
        return _FakeReport()


class _RecordingPairService:
    instances: List["_RecordingPairService"] = []

    def __init__(
        self, evaluation_mode: Optional[EvaluationMode] = None, **_: Any
    ) -> None:
        self.evaluation_mode = evaluation_mode
        self.market = "unset-market"
        self.bots = "unset-bot"
        self.build_kwargs: Optional[Dict[str, Any]] = None
        type(self).instances.append(self)

    def build(self, **kwargs: Any) -> _FakeReport:
        self.build_kwargs = kwargs
        return _FakeReport()


class _RecordingDataService:
    """DataReportService double: only ever gets the market side wired in
    (see TestApplyLiveSource's own market_attr/bot_attr table), so it has no
    bot_service/bots attribute at all -- exactly like the real class."""

    instances: List["_RecordingDataService"] = []

    def __init__(
        self, evaluation_mode: Optional[EvaluationMode] = None, **_: Any
    ) -> None:
        self.evaluation_mode = evaluation_mode
        self.market = "unset-market"
        type(self).instances.append(self)

    def build(self, **kwargs: Any) -> _FakeReport:
        return _FakeReport()


class _RecordingMarketRegimeService:
    instances: List["_RecordingMarketRegimeService"] = []

    def __init__(
        self, evaluation_mode: Optional[EvaluationMode] = None, **_: Any
    ) -> None:
        self.evaluation_mode = evaluation_mode
        self.market_service = "unset-market"
        type(self).instances.append(self)

    def build(self, **kwargs: Any) -> _FakeReport:
        return _FakeReport()


class TestSourceCliWiring:
    def setup_method(self) -> None:
        _RecordingCohortService.instances.clear()

    def test_source_file_default_never_builds_live_sources(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            run_report, "CohortAssessmentService", _RecordingCohortService
        )

        def _must_not_run() -> None:
            raise AssertionError("build_live_sources must not run for --source file")

        monkeypatch.setattr(run_report, "build_live_sources", _must_not_run)

        code = run_report.main(["--report", "cohort", "--bot", "ANY", "--json"])
        assert code == 0
        service = _RecordingCohortService.instances[-1]
        # main() always wires the one shared, memoized service into every
        # report service now (see build_shared_services/apply_shared_services
        # in run_report.py) -- for --source file, that shared MarketService/
        # BotObservationService falls back to its own default file-backed
        # source, exactly like the private per-service instance it replaces
        # used to. __getattr__ on the memoizing wrapper forwards straight to
        # the real instance, so .market_source/._bot_source below read off
        # the wrapped MarketService/BotObservationService, not the wrapper.
        assert isinstance(service.market_service, run_report._MemoizedMarketService)
        assert isinstance(service.market_service.market_source, FileMarketDataSource)
        assert isinstance(
            service.bot_service, run_report._MemoizedBotObservationService
        )
        assert isinstance(service.bot_service._bot_source, FileBotDataSource)

    def test_source_live_wires_the_live_sources_into_the_service(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            run_report, "CohortAssessmentService", _RecordingCohortService
        )
        sentinel_bot, sentinel_market = object(), object()
        monkeypatch.setattr(
            run_report, "build_live_sources", lambda: (sentinel_bot, sentinel_market)
        )

        code = run_report.main(
            ["--report", "cohort", "--bot", "ANY", "--json", "--source", "live"]
        )
        assert code == 0
        service = _RecordingCohortService.instances[-1]
        # Same shared-service wiring as the file-mode test above, this time
        # built around the live sources build_live_sources() (faked here)
        # returned -- see that test's comment on why .market_source/
        # ._bot_source read through the memoizing wrapper to the real
        # MarketService/BotObservationService underneath.
        assert isinstance(service.market_service, run_report._MemoizedMarketService)
        assert service.market_service.market_source is sentinel_market
        assert isinstance(
            service.bot_service, run_report._MemoizedBotObservationService
        )
        assert service.bot_service._bot_source is sentinel_bot


class TestOutDirWiring:
    def setup_method(self) -> None:
        _RecordingPairService.instances.clear()
        _RecordingCohortService.instances.clear()

    def test_out_dir_is_passed_to_persist_analysis(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(run_report, "PairedBotReportService", _RecordingPairService)
        captured: Dict[str, Path] = {}
        monkeypatch.setattr(
            run_report,
            "persist_analysis",
            lambda report, data_dir: (
                captured.setdefault("data_dir", Path(data_dir)) and []
            ),
        )
        out_dir = tmp_path / "out_analysis"

        code = run_report.main(
            ["--report", "bot", "--bot", "ANY", "--json", "--out-dir", str(out_dir)]
        )
        assert code == 0
        assert captured["data_dir"] == out_dir
        assert captured["data_dir"] != Path(config.DATA_DIR)

    def test_missing_out_dir_defaults_to_data_dir(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(run_report, "PairedBotReportService", _RecordingPairService)
        captured: Dict[str, Path] = {}
        monkeypatch.setattr(
            run_report,
            "persist_analysis",
            lambda report, data_dir: (
                captured.setdefault("data_dir", Path(data_dir)) and []
            ),
        )

        code = run_report.main(["--report", "bot", "--bot", "ANY", "--json"])
        assert code == 0
        assert captured["data_dir"] == Path(config.DATA_DIR)

    def test_out_dir_is_passed_to_persist_assessment(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(
            run_report, "CohortAssessmentService", _RecordingCohortService
        )
        captured: Dict[str, Path] = {}
        monkeypatch.setattr(
            run_report,
            "persist_assessment",
            lambda report, data_dir: (
                captured.setdefault("data_dir", Path(data_dir)) and []
            ),
        )
        out_dir = tmp_path / "out_assessment"

        code = run_report.main(
            ["--report", "qc", "--bot", "ANY", "--json", "--out-dir", str(out_dir)]
        )
        assert code == 0
        assert captured["data_dir"] == out_dir
        assert captured["data_dir"] != Path(config.DATA_DIR)


class TestSharedServicesAcrossReports:
    """The point of this whole task: --report all must build exactly one
    MarketService and one BotObservationService and hand the same instance
    to all four report services, instead of each one building its own.

    All four *ReportService classes are replaced with recording doubles, so
    this only exercises run_report.py's own wiring in main() -- not a
    re-test of DataReportService/MarketRegimeService/PairedBotReportService/
    CohortAssessmentService, which TestApplyLiveSource and the rest of this
    file already cover.
    """

    def setup_method(self) -> None:
        _RecordingDataService.instances.clear()
        _RecordingCohortService.instances.clear()
        _RecordingPairService.instances.clear()
        _RecordingMarketRegimeService.instances.clear()

    def test_all_four_reports_share_one_market_and_one_bot_service(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(run_report, "DataReportService", _RecordingDataService)
        monkeypatch.setattr(
            run_report, "CohortAssessmentService", _RecordingCohortService
        )
        monkeypatch.setattr(run_report, "PairedBotReportService", _RecordingPairService)
        monkeypatch.setattr(
            run_report, "MarketRegimeService", _RecordingMarketRegimeService
        )

        construction_count = {"market": 0, "bot": 0}
        real_market_init = MarketService.__init__
        real_bot_init = BotObservationService.__init__

        def counting_market_init(self, *args: Any, **kwargs: Any) -> None:
            construction_count["market"] += 1
            real_market_init(self, *args, **kwargs)

        def counting_bot_init(self, *args: Any, **kwargs: Any) -> None:
            construction_count["bot"] += 1
            real_bot_init(self, *args, **kwargs)

        monkeypatch.setattr(MarketService, "__init__", counting_market_init)
        monkeypatch.setattr(BotObservationService, "__init__", counting_bot_init)

        code = run_report.main(
            ["--report", "all", "--bot", "ANY", "--json", "--no-write"]
        )
        assert code == 0

        # Exactly one of each, however many of the four report services asked
        # for one -- this is the construction-level fix the four independent
        # constructors (see qc/reporting/*.py) can no longer do on their own.
        assert construction_count == {"market": 1, "bot": 1}

        data = _RecordingDataService.instances[-1]
        cohort = _RecordingCohortService.instances[-1]
        pair = _RecordingPairService.instances[-1]
        market = _RecordingMarketRegimeService.instances[-1]

        # Same object, not just equal objects -- so the memoisation cache
        # living on it is the same cache every report service consults.
        assert data.market is cohort.market_service
        assert cohort.market_service is pair.market
        assert pair.market is market.market_service
        assert cohort.bot_service is pair.bots

        assert isinstance(data.market, run_report._MemoizedMarketService)
        assert isinstance(cohort.bot_service, run_report._MemoizedBotObservationService)

    def test_sharing_also_applies_to_source_file_not_only_live(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The task explicitly calls out that --source file must benefit too
        -- confirm the shared wiring happens with no --source flag at all
        (the default), not only under --source live."""
        monkeypatch.setattr(
            run_report, "CohortAssessmentService", _RecordingCohortService
        )
        monkeypatch.setattr(run_report, "PairedBotReportService", _RecordingPairService)

        def _must_not_run() -> None:
            raise AssertionError("build_live_sources must not run for --source file")

        monkeypatch.setattr(run_report, "build_live_sources", _must_not_run)

        code = run_report.main(
            ["--report", "all", "--bot", "ANY", "--json", "--no-write"]
        )
        assert code == 0
        cohort = _RecordingCohortService.instances[-1]
        pair = _RecordingPairService.instances[-1]
        assert cohort.bot_service is pair.bots
        assert cohort.market_service is pair.market


# --------------------------------------------------------------------------- #
# run_compare.main(): full CLI wiring for both modes, network-free via fakes.
# --------------------------------------------------------------------------- #


class _FakeLiveBotDataSource:
    """Stands in for LiveBotDataSource: returns the synthetic payload above
    instead of calling OKX."""

    def __init__(self, client: Any = None) -> None:
        self._client = client

    def get_overview(self, unique_code: str, bot_dir: Optional[Path] = None):
        return _overview(uniqueCode=unique_code)

    def get_ledger(self, unique_code: str, bot_dir: Optional[Path] = None):
        return _ledger()


class _RecordingCohortServiceForCompare:
    """Tells the file scan and the live scan apart by whether apply_live_source
    has swapped bot_service off its initial sentinel string yet."""

    def __init__(
        self, data_dir: Any = None, evaluation_mode: Any = None, **_: Any
    ) -> None:
        self.data_dir = data_dir
        self.evaluation_mode = evaluation_mode
        self.market_service = "unset-market"
        self.bot_service = "unset-bot"

    def scan(self, **kwargs: Any):
        is_live = self.bot_service != "unset-bot"
        row = _row(
            unique_code="A",
            trade_count=107 if is_live else 100,
            risk_score=15.0 if is_live else 10.0,
        )
        return _RowsOnly([row])


class _RowsOnly:
    def __init__(self, rows: List[BotEvaluationRow]) -> None:
        self.rows = rows


class TestRunCompareCli:
    def test_same_data_end_to_end_without_network(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        bot_dir = tmp_path / "cex" / "ETH" / "bot" / "bot_TESTCODE"
        bot_dir.mkdir(parents=True)
        (bot_dir / "trade_list.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
        monkeypatch.setattr(run_compare, "OkxClient", lambda: object())
        monkeypatch.setattr(run_compare, "LiveBotDataSource", _FakeLiveBotDataSource)

        code = run_compare.main(
            [
                "--mode",
                "same-data",
                "--bot",
                "TESTCODE",
                "--iterations",
                str(SIM_ITERATIONS),
                "--horizon",
                str(SIM_HORIZON),
            ]
        )
        assert code == 0

    def test_same_data_requires_bot(self) -> None:
        with pytest.raises(SystemExit):
            run_compare.main(["--mode", "same-data"])

    def test_live_vs_file_end_to_end_without_network(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
        monkeypatch.setattr(
            run_compare, "CohortAssessmentService", _RecordingCohortServiceForCompare
        )
        monkeypatch.setattr(
            run_compare, "build_live_sources", lambda: (object(), object())
        )

        code = run_compare.main(["--mode", "live-vs-file", "--bot", "A"])
        # trade_count differs by exactly the amount the fake live scan adds,
        # so this must classify as DỮ LIỆU TRÔI (explained), not BẤT THƯỜNG --
        # hence exit 0.
        assert code == 0
