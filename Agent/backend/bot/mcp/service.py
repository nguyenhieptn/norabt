from __future__ import annotations

import concurrent.futures
import hashlib
import json
import time
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from Agent.backend.infra.config import config
from Agent.backend.infra.quality import (
    EvaluationMode,
    SourceStatus,
    grade_source,
)
from Agent.backend.bot.mcp.analytics.behavior.detector import BehavioralPatternDetector
from Agent.backend.bot.mcp.capital.equity_curve import CapitalResolver
from Agent.backend.external.sources.dex_registry import DEX_ASSET_REGISTRY
from Agent.backend.bot.mcp.analytics.drawdown.underwater import DrawdownUnderwaterAnalyzer
from Agent.backend.bot.mcp.analytics.performance.deferred_loss import DeferredLossAnalyzer
from Agent.backend.bot.mcp.analytics.performance.distribution import (
    TradeStatisticsCalculator,
)
from Agent.backend.bot.mcp.analytics.performance.metrics import PerformanceMetricsCalculator
from Agent.backend.bot.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.bot.mcp.analytics.simulation.inference import analyse as analyse_sharpe
from Agent.backend.bot.mcp.analytics.simulation.sharpe_reference import (
    population_sharpe_variance,
)
from Agent.backend.bot.mcp.analytics.simulation.stress import StressSimulator
from Agent.backend.bot.mcp.analytics.strategy.exit_rule import ExitRuleAnalyzer
from Agent.backend.bot.mcp.analytics.strategy.phases import PhaseTimeline, build_timeline
from Agent.backend.bot.mcp.analytics.strategy.profile import (
    StrategyPhaseAnalyzer,
    base_symbol,
)
from Agent.backend.bot.mcp.schemas.bot_result import (
    BotCurrentState,
    BotIdentity,
    BotResult,
    DataQualityAssessment,
    LedgerReconciliation,
    StrategyObservations,
    TradeLedgerItem,
)
from Agent.backend.bot.mcp.positions.snapshot import PositionSnapshotParser
from Agent.backend.bot.mcp.trades.identity import LedgerIdentityGuard
from Agent.backend.bot.mcp.trades.ledger import TradeLedgerManager
from Agent.backend.external.sources.bot_source import BotDataSource, FileBotDataSource


class BotDataUnavailableError(ValueError):
    pass


# --------------------------------------------------------------------------- #
# Translation boundary for warning text this service RECEIVES, rather than
# writes itself, from sibling modules this task's file list does not cover
# (Agent/backend/mcp/capital/equity_curve.py, .../positions/snapshot.py,
# .../trades/ledger.py, .../analytics/performance/deferred_loss.py). Those
# modules' English message templates are fixed and enumerable (each is one
# `warnings.append(f"...")` call site read directly off that module's own
# source), so every template is matched here by an exact regex and rebuilt in
# Vietnamese with the same numbers -- never a loose substring/keyword
# translation that could silently mistranslate an unrelated sentence.
#
# Why translate at the boundary instead of at the source: this task's file
# list is `Agent/backend/qc/evaluator/lenses/*.py` and
# `Agent/backend/mcp/service.py` only, "chỉ để dịch chuỗi hiển thị" -- the
# four sibling modules above belong to other work in flight and are
# explicitly off-limits ("Không đụng file khác"). This is the one place in
# THIS file every one of their warning strings passes through before
# reaching `data_quality.warnings` (see `get_bot_result` below), so it is
# also the one place that can fix them without touching their source.
#
# Deliberately fails OPEN, not closed: a warning text that matches none of
# the patterns below (a template renamed upstream, or a genuinely new one)
# is returned UNCHANGED rather than dropped or replaced with a placeholder --
# a leftover English sentence is a translation gap to fix next, but a
# silently vanished data-quality warning would be a worse, quieter bug.
# TẦNG DỊCH ANH -> VIỆT ĐÃ ĐƯỢC XOÁ (19/09).
#
# Trước đây khối này giữ ~10 cặp (regex, hàm dựng câu) để Việt hoá các cảnh
# báo do những module anh em phát ra: `capital/equity_curve.py`,
# `positions/snapshot.py`, `trades/ledger.py`,
# `analytics/performance/deferred_loss.py`. Các module đó vốn đã phát ra
# TIẾNG ANH ở nguồn; khối này tồn tại chỉ để dịch ngược lại.
#
# Sản phẩm chuyển sang tiếng Anh nên nó thành thừa: giữ lại là giữ một tầng
# phải bảo trì mà không làm gì cả, và tệ hơn, là một chỗ để cảnh báo mới ở
# nguồn lặng lẽ không khớp mẫu rồi đi qua mà không ai biết.
#
# `_vi_upstream_warning` giữ nguyên tên và chữ ký để mọi nơi gọi khỏi phải
# sửa, nhưng giờ là hàm đồng nhất: văn bản của nguồn đi thẳng tới người đọc,
# không qua trung gian nào.
def _vi_upstream_warning(text: str) -> str:
    """Trả về chính `text`. Xem khối chú thích ngay trên."""
    return text


class BotObservationService:
    """LOGIC 2: normalize a bot snapshot, analyze its ledger, and own simulation."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        evaluation_mode: EvaluationMode = EvaluationMode.SNAPSHOT,
        bot_source: Optional[BotDataSource] = None,
        reference_data_dir: Optional[Path] = None,
    ) -> None:
        self.data_dir = data_dir or Path(config.DATA_DIR)
        # `data_dir` is where this service reads/writes the BOT's own files
        # (overview.json/trade_list.json, or -- for a live lookup -- just the
        # one empty leaf directory that satisfies `_find_bot_dir`'s
        # existence check). A caller that isolates a live source's writes
        # behind a scratch directory (see `Agent/backend/web/data.py`'s
        # `_analyze_full`) passes THAT here.
        #
        # `_phase_timelines` below reads something entirely different: the
        # read-only reference candle series (`<venue>/<symbol>/market/
        # ohlcv_1h_*.json`, `phases/<symbol>.json`) used to label which
        # market regime each of the bot's own trades happened in. That data
        # is never written by this service and has nothing to do with bot
        # isolation, so it must keep pointing at the real dataset even when
        # `data_dir` itself is a scratch directory -- otherwise (the bug this
        # parameter fixes) an empty scratch dir silently starves
        # `_phase_timelines` of every candle, every trade resolves to
        # `MarketPhase.UNKNOWN`, and phase coverage/breakdown silently comes
        # back empty for every bot analyzed through that path.
        #
        # Defaults to `data_dir` (`None` here means "same as before"), so
        # every existing caller -- which never had this scratch-vs-real split
        # to begin with -- keeps behaving exactly as it did.
        self._reference_data_dir = (
            reference_data_dir if reference_data_dir is not None else self.data_dir
        )
        self._timeline_cache: Dict[str, Optional[PhaseTimeline]] = {}
        # Guards the cache above. One service instance is now shared by the
        # threads that read a portfolio's members in parallel (see
        # `PortfolioSupervisionPipeline.fetch_members`), and two members
        # trading the same symbol would otherwise both find the cache empty
        # and each build the same 30k-candle timeline. Dict writes are atomic
        # under the GIL so nothing corrupts either way -- what the lock buys
        # is not doing the expensive work twice.
        self._timeline_lock = threading.Lock()
        self.evaluation_mode = evaluation_mode
        # Defaults to the on-disk crawl output -- every existing caller keeps
        # reading exactly what Agent/none/scripts/crawl_bots.py wrote. Passing a
        # LiveBotDataSource here is the only thing that changes when a caller
        # wants OKX read straight into this analysis instead.
        self._bot_source = bot_source or FileBotDataSource(self.data_dir)

    @staticmethod
    def _clean_asset(asset: str) -> str:
        clean = asset.split("-")[0].split("/")[0].strip().upper()
        if not clean or not clean.replace("_", "").isalnum():
            raise ValueError(f"Invalid asset: {asset!r}")
        return clean

    @staticmethod
    def _float(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _observed_at(payload: Dict[str, Any], fallback_path: Path) -> int:
        """When a payload was fetched (not read off disk), used to grade source
        freshness in place of a file's mtime.

        `observed_at_ms` is the explicit field a source can set; every payload
        Agent/none/scripts/crawl_bots.py has ever written predates that field, so
        for on-disk data this always falls back to the file's own mtime --
        byte-identical to what this method replaces. A live payload always
        sets observed_at_ms itself (there is no file to stat), so the fallback
        branch is only ever exercised by pre-existing crawled data.
        """
        explicit = payload.get("observed_at_ms")
        if explicit is not None:
            try:
                return int(explicit)
            except (TypeError, ValueError):
                pass
        try:
            return int(fallback_path.stat().st_mtime * 1000)
        except OSError:
            return int(time.time() * 1000)

    def _find_bot_dir(
        self, asset: str, folder: str, venue_type: Optional[str]
    ) -> Tuple[Path, str]:
        if Path(folder).name != folder or folder in ("", ".", ".."):
            raise ValueError("bot_folder_name must be one directory name")
        requested = venue_type.upper() if venue_type else None
        if requested not in (None, "CEX", "DEX"):
            raise ValueError("venue_type must be CEX or DEX")
        # Unified layout: one folder per bot_id, no venue/asset segregation
        # (data/trade/<folder>/) -- see Agent/backend/sources/market_source.py's
        # _market_dir for the equivalent change on the market side. `kind` is
        # derived from DEX_ASSET_REGISTRY membership only because the caller
        # (see the one call site of this method) discards it; it is no longer
        # read off the directory the bot was found under.
        candidate = self.data_dir / "trade" / folder
        if candidate.is_dir():
            kind = requested or ("DEX" if asset.upper() in DEX_ASSET_REGISTRY else "CEX")
            return candidate, kind
        suffix = f" on {requested}" if requested else ""
        raise BotDataUnavailableError(f"No bot dataset {folder!r} for {asset}{suffix}")

    @staticmethod
    def _base_symbol(instrument: str) -> str:
        return instrument.split("-")[0].split("/")[0].strip().upper()

    @classmethod
    def _resolve_identity_market(
        cls,
        asset_context: str,
        trades: List[TradeLedgerItem],
        position_exposure: Optional[Dict[str, float]] = None,
    ) -> Tuple[Optional[str], Dict[str, float], List[str], List[str]]:
        """Derive the market the bot actually trades from its own ledger."""
        exposure: Dict[str, float] = {}
        for trade in trades:
            base = cls._base_symbol(trade.symbol)
            if base in ("", "UNKNOWN"):
                continue
            weight = trade.notional if trade.notional is not None else 0.0
            exposure[base] = exposure.get(base, 0.0) + max(weight, 0.0)
        if exposure and not any(value > 0 for value in exposure.values()):
            exposure = {}
        if not exposure:
            counts: Dict[str, float] = {}
            for trade in trades:
                base = cls._base_symbol(trade.symbol)
                if base in ("", "UNKNOWN"):
                    continue
                counts[base] = counts.get(base, 0.0) + 1.0
            exposure = counts
        source = "ledger"
        if not exposure and position_exposure:
            # No closed trades: the market it is trading right now still counts.
            exposure = dict(position_exposure)
            source = "open positions"

        total = sum(exposure.values())
        share = (
            {name: value / total for name, value in exposure.items()} if total else {}
        )
        observed = sorted(share, key=lambda name: share[name], reverse=True)
        primary = observed[0] if observed else None

        warnings: List[str] = []
        if primary is None:
            warnings.append(
                "Neither the closed book nor the open positions name any traded "
                "instrument; the market this bot actually trades could not be determined"
            )
        elif source == "open positions":
            warnings.append(
                f"No closed trades yet: the traded market {primary} is derived from "
                f"open positions"
            )
        elif asset_context not in share:
            warnings.append(
                f"Snapshot is filed under {asset_context}, but the closed book has "
                f"never traded this asset; the primary traded market is {primary} "
                f"({share[primary]:.0%} exposure)"
            )
        elif share.get(asset_context, 0.0) < 0.5:
            warnings.append(
                f"{asset_context} accounts for only {share[asset_context]:.0%} of "
                f"trading exposure; the primary traded market is {primary}"
            )
        if len(observed) > 1:
            warnings.append(
                f"Bot trades {len(observed)} instruments; this single-market "
                f"assessment covers {primary} only"
            )
        return primary, share, observed, warnings

    @classmethod
    def _current_state(
        cls,
        payload: Dict[str, Any],
        current_equity: Optional[float],
        reference_capital: Optional[float],
        reference_capital_source: Optional[str],
    ) -> Tuple[BotCurrentState, List[str]]:
        snapshot = PositionSnapshotParser.parse(payload)
        equity_for_ratio = current_equity or reference_capital
        margin_ratio = (
            snapshot.used_margin / current_equity * 100.0
            if snapshot.used_margin is not None and current_equity
            else None
        )
        margin_to_reference = (
            snapshot.used_margin / reference_capital * 100.0
            if snapshot.used_margin is not None and reference_capital
            else None
        )
        upl_pct = (
            snapshot.unrealized_pnl / equity_for_ratio * 100.0
            if snapshot.unrealized_pnl is not None and equity_for_ratio
            else None
        )
        consistency = "UNKNOWN"
        if snapshot.used_margin is not None and reference_capital:
            consistency = (
                "MARGIN_EXCEEDS_CAPITAL"
                if snapshot.used_margin > reference_capital
                else "CONSISTENT"
            )
        state = BotCurrentState(
            current_equity=current_equity,
            reference_capital=reference_capital,
            reference_capital_source=reference_capital_source,
            available_balance=cls._float(payload.get("available_balance")),
            used_margin=snapshot.used_margin,
            margin_ratio=margin_ratio,
            margin_to_reference_pct=margin_to_reference,
            capital_consistency=consistency,
            current_position_side=snapshot.aggregate_side,
            current_position_size=None,
            current_notional=snapshot.gross_exposure,
            gross_exposure=snapshot.gross_exposure,
            net_exposure=snapshot.net_exposure,
            long_notional=snapshot.long_notional,
            short_notional=snapshot.short_notional,
            current_leverage=snapshot.max_leverage,
            unrealized_pnl=snapshot.unrealized_pnl,
            unrealized_pnl_pct=upl_pct,
            open_positions_count=snapshot.declared_count,
            attributed_positions_count=snapshot.attributed_count,
            observed_positions_count=snapshot.observed_count,
            inferred_positions_count=snapshot.inferred_count,
            positions_outside_ledger_universe=snapshot.outside_universe_count,
            unknown_positions_count=snapshot.unattributed_count,
            instrument_withheld_upstream=(
                snapshot.observed_count == 0 and snapshot.declared_count > 0
            ),
            open_position_symbols=sorted(snapshot.exposure_by_symbol),
            exposure_by_symbol=snapshot.exposure_by_symbol,
            open_positions=snapshot.positions,
        )
        warnings = [_vi_upstream_warning(w) for w in snapshot.warnings]
        if consistency == "MARGIN_EXCEEDS_CAPITAL":
            warnings.append(
                f"Used margin ({snapshot.used_margin:,.0f}) exceeds reported capital "
                f"({reference_capital:,.0f}); ratios based on capital are unreliable "
                f"until the capital figure is confirmed"
            )
        return state, warnings

    # Việc 4 (song song hoá theo số nguồn dữ liệu, có trần cứng): một bot
    # lưới/đa mã có thể chạm hàng chục symbol khác nhau trong một sổ lệnh --
    # mỗi symbol CHƯA có trong `self._timeline_cache` cần đọc (tới) 5 file
    # JSON candle trên đĩa, độc lập hoàn toàn với mọi symbol khác. Đây là
    # I/O (đọc file, không phải tính toán CPU thuần), nên luồng vẫn có lợi
    # dù máy này chỉ cấp 2 CPU cho container (xem Agent/docker/docker-
    # compose.yml's `cpus: 2`): GIL được nhả ra trong lúc chờ hệ điều hành
    # trả dữ liệu file, y hệt lý do luồng có lợi cho việc chờ mạng OKX.
    # `_PHASE_TIMELINE_MAX_WORKERS = 6` là TRẦN CỨNG do chủ dự án đặt cho
    # toàn bộ phần I/O song song của dự án (máy 12 core/14GB, đang chạy
    # song song 15 site production + nhiều container khác) -- bậc song
    # song THỰC TẾ vẫn tự co theo số symbol còn thiếu (`min(số symbol còn
    # thiếu, 6)`), không bao giờ tạo nhiều luồng hơn số việc cần làm.
    _PHASE_TIMELINE_MAX_WORKERS = 6

    def _load_phase_timeline(self, symbol: str) -> Optional[PhaseTimeline]:
        """Đọc/dựng timeline pha cho ĐÚNG MỘT symbol -- tách riêng khỏi
        `_phase_timelines` để có thể chạy nó trên một luồng nền, xem
        docstring của hàm đó."""
        candles = None
        # Universe assets first, then the reference series kept only for phase
        # labelling (data/phases), which never widen Logic 1's universe.
        # Read from `_reference_data_dir`, NOT `self.data_dir`: this is
        # read-only reference data, not part of the bot's own
        # (possibly-scratch) working directory -- see this class's
        # `__init__` docstring for why the two must stay separate.
        paths = [
            self._reference_data_dir / "market" / venue / symbol / name
            for venue in ("cex", "dex")
            for name in ("ohlcv_1h_2023_present.json", "ohlcv_1h_2026.json")
        ]
        paths.append(self._reference_data_dir / "market" / "phases" / f"{symbol}.json")
        for path in paths:
            if not path.exists():
                continue
            try:
                candles = json.loads(path.read_text(encoding="utf-8")).get("candles")
            except (OSError, json.JSONDecodeError):
                candles = None
            if candles:
                break
        return build_timeline(symbol, candles) if candles else None

    def phase_timelines(self, symbols: Iterable[str]) -> Dict[str, PhaseTimeline]:
        """Public access to the cached phase timelines.

        The portfolio path needs them for a ledger merged from several bots,
        which no single `get_bot_result` call covers. Exposed rather than
        rebuilt so the caller shares this instance's cache instead of parsing
        30k candles per symbol a second time.
        """
        return self._phase_timelines(symbols)

    def _phase_timelines(self, symbols: Iterable[str]) -> Dict[str, PhaseTimeline]:
        """Hourly phase labels for every symbol we hold candles for.

        Cached per service instance: one bot can touch a hundred instruments and
        rebuilding a 30k-point timeline for each would dominate the run.

        The whole body is serialised on `self._timeline_lock`. That is not
        about correctness -- writes here were always safe, for the reason the
        comment below the loop gives -- it is about not doing the same work
        twice. One service instance is now shared by the threads that read a
        portfolio's members concurrently, and those members overwhelmingly
        trade the same few symbols; without the lock, four threads all find
        BTC missing at the same instant and all four build the same
        30k-candle timeline. Serialising here makes the total work the UNION
        of the members' symbols, built once, which is strictly less than what
        the threads would otherwise duplicate. The build inside is still
        parallel across symbols, so the critical section is as short as the
        work allows.
        """
        with self._timeline_lock:
            return self._phase_timelines_locked(symbols)

    def _phase_timelines_locked(
        self, symbols: Iterable[str]
    ) -> Dict[str, PhaseTimeline]:
        timelines: Dict[str, PhaseTimeline] = {}
        unique_symbols = {str(s).upper() for s in symbols if s}
        missing: List[str] = []
        for symbol in unique_symbols:
            if symbol in self._timeline_cache:
                cached = self._timeline_cache[symbol]
                if cached is not None:
                    timelines[symbol] = cached
            else:
                missing.append(symbol)

        if not missing:
            return timelines

        # Mỗi symbol trong `missing` ghi vào một KHOÁ RIÊNG của
        # `self._timeline_cache`/`timelines` (đã khử trùng lặp ở
        # `unique_symbols` phía trên) -- không có hai luồng nào cùng ghi
        # một khoá, nên không cần khoá (`threading.Lock`) ở đây: gán một
        # khoá dict trong CPython vốn đã nguyên tử.
        worker_count = min(len(missing), self._PHASE_TIMELINE_MAX_WORKERS)
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=worker_count, thread_name_prefix="norabt-phase-timeline"
        ) as pool:
            future_to_symbol = {
                pool.submit(self._load_phase_timeline, symbol): symbol
                for symbol in missing
            }
            for future in concurrent.futures.as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                timeline = future.result()
                self._timeline_cache[symbol] = timeline
                if timeline is not None:
                    timelines[symbol] = timeline
        return timelines

    @staticmethod
    def _strategy_observations(
        declared: Optional[str], behavior, performance
    ) -> StrategyObservations:
        frequency = performance.trade_frequency_per_day or 0.0
        hold = performance.median_hold_time_minutes or 0.0
        if behavior.martingale_escalation_detected or behavior.averaging_down_detected:
            observed = "Grid/Martingale-like"
        elif frequency >= 20 or hold <= 30:
            observed = "Scalping"
        elif hold >= 24 * 60:
            observed = "Swing"
        else:
            observed = "DayTrading"
        if not declared:
            return StrategyObservations(
                observed_profile=observed,
                declared_strategy=None,
                strategy_drift_score=None,
            )
        normalized_declared = declared.lower().replace(" ", "")
        normalized_observed = (
            observed.lower().replace("/", "").replace("-", "").replace(" ", "")
        )
        aligned = (
            normalized_declared in normalized_observed
            or normalized_observed in normalized_declared
        )
        score = 0.1 if aligned else 0.75
        # `observed` ("Grid/Martingale-like"/"Scalping"/"Swing"/"DayTrading")
        # doubles as a normalization key matched against the bot's own raw
        # `declared` strategy text right above -- kept in English rather than
        # translated, since translating it would change which declared
        # strings match and silently shift `strategy_drift_score` (a scoring
        # input), which this task must not touch. `details` itself is not
        # currently read by any renderer (see StrategyObservations.drift_details).
        details = [] if aligned else [f"Declared {declared}, observed {observed}"]
        return StrategyObservations(
            observed_profile=observed,
            declared_strategy=declared,
            strategy_drift_score=score,
            drift_details=details,
        )

    def get_bot_result(
        self,
        asset: str,
        bot_folder_name: str = "bot_top_performer",
        seed: Optional[int] = 42,
        venue_type: Optional[str] = None,
        as_of_ms: Optional[int] = None,
        simulation_iterations: int = 10_000,
        # None replays the bot's own trade count, which is what a percentile
        # of its profit should be measured over.
        simulation_horizon: Optional[int] = None,
        # How many candidates this bot was chosen from, for the deflated Sharpe.
        selection_trials: Optional[int] = None,
    ) -> BotResult:
        clean = self._clean_asset(asset)
        bot_dir, _ = self._find_bot_dir(clean, bot_folder_name, venue_type)
        # The folder name is usually the bot's own OKX uniqueCode
        # ("bot_<CODE>", true of every real dataset under Agent/data), but not
        # guaranteed -- test fixtures use names like "bot_TEST" with an
        # unrelated code inside the file. FileBotDataSource ignores this value
        # entirely (bot_dir alone finds its files); only a live source needs
        # it, to know which bot to ask OKX for.
        code_hint = (
            bot_folder_name[4:]
            if bot_folder_name.startswith("bot_")
            else bot_folder_name
        )
        # Việc 4 (song song hoá theo nguồn dữ liệu độc lập): `get_overview`
        # (weekly_pnl + xếp hạng lead-trader + public-stats) và `get_ledger`
        # (vị thế mở + phân trang lịch sử) là HAI NHÓM lời gọi OKX hoàn toàn
        # độc lập -- ledger không cần bất kỳ trường nào overview trả về và
        # ngược lại, chỉ vì trước bản sửa này chúng được viết NỐI TIẾP trong
        # cùng một hàm. Đo thật (project owner, 2026-09-17):
        # `BotObservationService.get_bot_result` tốn 12.4s trên một bot
        # nguội, phần lớn nằm ở đúng chuỗi lời gọi OKX nối tiếp này. Cho
        # chạy trên hai luồng cùng lúc, đi qua ĐÚNG `TokenBucket` tiết chế
        # OKX hiện có (bot_source.py's `_DEFAULT_RATE_LIMITER`/
        # `self._rate_limiter`, tự nhận "an toàn khi dùng chung giữa nhiều
        # luồng" -- xem live/ratelimit.py) chứ không vòng qua nó. Với
        # `FileBotDataSource` (đường file/backtest), cả hai chỉ là đọc đĩa
        # cục bộ độc lập -- vẫn đúng và an toàn để song song, chỉ là không
        # tốn kém sẵn nên lợi ích ở đó là không đáng kể.
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="norabt-bot-fetch"
        ) as pool:
            overview_future = pool.submit(
                self._bot_source.get_overview, code_hint, bot_dir=bot_dir
            )
            ledger_future = pool.submit(
                self._bot_source.get_ledger, code_hint, bot_dir=bot_dir
            )
            overview = overview_future.result()
            if overview is None:
                raise BotDataUnavailableError(
                    f"Missing bot data file: overview.json ({bot_dir})"
                )
            raw_ledger = ledger_future.result()
            if raw_ledger is None:
                raise BotDataUnavailableError(
                    f"Missing bot data file: trade_list.json ({bot_dir})"
                )
        overview_observed_at = self._observed_at(overview, bot_dir / "overview.json")
        ledger_observed_at = self._observed_at(raw_ledger, bot_dir / "trade_list.json")
        now = as_of_ms if as_of_ms is not None else int(time.time() * 1000)

        ownership = LedgerIdentityGuard.verify(overview, raw_ledger)
        identity_rejected = ownership.belongs_to_another_bot
        if identity_rejected:
            # The ledger is another trader's: analysing it would describe the wrong bot.
            raw_ledger = {
                "open_positions_count": 0,
                "open_positions": [],
                "closed_trades": [],
            }
        parsed = TradeLedgerManager.parse_trade_list_with_diagnostics(raw_ledger)
        trades = parsed.trades
        mode = TradeLedgerManager.determine_measurement_mode(trades)
        current_equity = self._float(
            overview.get(
                "currentEquity", overview.get("equity", overview.get("equity_usdt"))
            )
        )
        reported_aum = self._float(overview.get("aum", overview.get("aum_usdt")))
        capital = CapitalResolver.resolve(overview, reported_aum)
        reference_capital = capital.capital_at_risk
        reference_source = capital.basis

        # Translated at the boundary: `capital.warnings` is built inside
        # Agent/backend/mcp/capital/equity_curve.py (a sibling module this
        # task's file list does not cover), so its English message templates
        # are mapped to Vietnamese here, at the one place this service reads
        # them, rather than at their source. See `_vi_upstream_warning`'s own
        # docstring for the exact set of templates it recognizes.
        capital_warnings: List[str] = [
            _vi_upstream_warning(w) for w in capital.warnings
        ]
        if reference_capital is not None and reference_capital <= 0:
            capital_warnings.append(
                f"Reported AUM is {reference_capital:g}; reference capital is treated as absent"
            )
            reference_capital = None
        if current_equity is not None and current_equity <= 0:
            current_equity = None
        current, position_warnings = self._current_state(
            raw_ledger, current_equity, reference_capital, reference_source
        )
        reported_pnl = self._float(overview.get("pnl", overview.get("pnl_usdt")))
        provenance = overview.get("provenance") or {}
        reported_provenance = str(provenance.get("profile_fields", "UNKNOWN"))
        ledger_pnl = sum(trade.realized_pnl for trade in trades)
        pnl_difference = ledger_pnl - reported_pnl if reported_pnl is not None else None
        pnl_difference_pct = (
            abs(pnl_difference) / max(abs(reported_pnl), 1e-12) * 100.0
            if pnl_difference is not None
            else None
        )
        reconciled = pnl_difference_pct is not None and pnl_difference_pct <= 1.0

        truncated = bool(raw_ledger.get("ledger_truncated"))
        page_size = int(raw_ledger.get("ledger_page_size") or 0)
        if not truncated and page_size and len(trades) and len(trades) % page_size == 0:
            truncated = True
        coverage_days = None
        if trades:
            coverage_days = (
                max(t.close_time for t in trades) - min(t.open_time for t in trades)
            ) / 86_400_000.0
        lead_days_raw = overview.get("leadDays")
        try:
            lead_days = int(lead_days_raw) if lead_days_raw not in (None, "") else None
        except (TypeError, ValueError):
            lead_days = None
        short_coverage = bool(
            lead_days and coverage_days is not None and coverage_days < lead_days * 0.9
        )

        recon_warnings: List[str] = []
        if identity_rejected:
            status = "IDENTITY_MISMATCH"
            recon_warnings.append(
                f"The ledger belongs to {', '.join(ownership.foreign_codes)} but the "
                f"profile is {ownership.expected_code}; the ledger was rejected and this "
                f"bot is assessed as having no trading history"
            )
        elif reported_pnl is None:
            status = "UNKNOWN"
            recon_warnings.append("No reported PnL to reconcile against")
        elif reconciled:
            status = "RECONCILED"
        elif truncated or short_coverage:
            status = "PARTIAL_LEDGER"
            detail = (
                "hit the page limit"
                if truncated
                else "covers only part of its time as lead trader"
            )
            recon_warnings.append(
                f"The ledger is a partial slice of the full history ({detail}): "
                f"{len(trades)} trades over {coverage_days:.0f} days versus {lead_days} "
                f"days as lead trader"
                if coverage_days is not None and lead_days
                else f"The ledger is a partial slice of the full history ({detail})"
            )
        elif reported_provenance != "OKX_VERIFIED":
            status = "UNVERIFIED_REFERENCE"
            recon_warnings.append(
                "Reported PnL comes from an unverified internal snapshot (OKX does not "
                "publish a per-trader profile endpoint), so this discrepancy is not "
                "evidence the ledger is wrong"
            )
        else:
            status = "MISMATCH"
            recon_warnings.append(
                "The ledger is complete and the reference figure is verified, but the "
                "totals still disagree"
            )

        reconciliation = LedgerReconciliation(
            status=status,
            reported_pnl=reported_pnl,
            reported_pnl_provenance=reported_provenance,
            ledger_pnl=ledger_pnl,
            difference=pnl_difference,
            difference_pct=pnl_difference_pct,
            ledger_truncated=truncated,
            ledger_coverage_days=coverage_days,
            declared_lead_days=lead_days,
            foreign_owner_codes=ownership.foreign_codes,
            rejected_foreign_rows=ownership.foreign_rows if identity_rejected else 0,
            warnings=recon_warnings,
        )
        capital_basis = capital.basis

        reported_ratio = self._float(overview.get("pnlRatio"))
        reported_roi_pct = (
            reported_ratio * 100.0 if reported_ratio is not None else None
        )
        # Historical and forward risk share one capital basis, so a tiny historical
        # denominator can never sit next to a huge forward one.
        drawdown = DrawdownUnderwaterAnalyzer.analyze(trades, capital)
        performance = PerformanceMetricsCalculator.calculate(
            trades, capital, reported_roi_pct, drawdown
        )
        deferred_loss = DeferredLossAnalyzer.analyze(
            trades,
            current.open_positions,
            current.unrealized_pnl,
            capital.capital_at_risk,
        )
        trade_statistics = TradeStatisticsCalculator.calculate(trades, mode)
        # `open_positions` (danh sách chi tiết), KHÔNG chỉ số đếm: bộ dò cần
        # `symbol`/`side`/`unrealized_pnl`/`entry_price` của từng vị thế để kết
        # luận được gia tăng-khi-lỗ THẬT (nhiều vị thế cùng mã, cùng hướng, đang
        # lỗ). Trước đây chỗ này chỉ truyền số đếm, nên bộ dò buộc phải suy từ
        # "có >= 3 vị thế mở" -- một suy diễn sai đã cộng oan 25 điểm rủi ro cho
        # 24/31 bot trong dataset này, chủ yếu là bot đa mã/kiểu lưới. Bộ dò giờ
        # suy biến an toàn khi thiếu danh sách (không kết tội từ số đếm), nhưng
        # nếu không truyền danh sách vào đây thì nó cũng KHÔNG BAO GIỜ bắt được
        # ca thật -- tức là gỡ báo động giả xong lại tắt luôn cảm biến.
        behavior = BehavioralPatternDetector.analyze(
            trades,
            current.open_positions_count,
            open_positions=current.open_positions,
        )
        declared = overview.get("strategy")
        baseline = self._strategy_observations(
            str(declared) if declared else None, behavior, performance
        )
        # Replay the ledger against the phases each traded market went through:
        # the label alone says nothing about which regimes the record was earned in.
        timelines = self._phase_timelines(
            {base_symbol(trade.symbol) for trade in trades if trade.symbol}
        )
        # Đóng dấu phase lên TỪNG lệnh, không chỉ vào bảng tổng hợp.
        # `StrategyPhaseAnalyzer.analyze` dưới đây vẫn tính đúng nhãn đó cho
        # từng lệnh rồi bỏ đi sau khi gom nhóm; giữ lại ở đây cho phép mọi phân
        # tích theo regime về sau LỌC lệnh thật thay vì tái dựng chuỗi PnL từ
        # dòng tổng hợp. Lệnh không có timeline giữ `None` (không đo được),
        # lệnh có timeline nhưng ngoài phạm vi nến nhận `"UNKNOWN"` -- hai việc
        # khác nhau.
        trades = [
            trade.model_copy(
                update={
                    "market_phase": (
                        timelines[base_symbol(trade.symbol)]
                        .phase_at(trade.open_time)
                        .value
                        if trade.symbol and base_symbol(trade.symbol) in timelines
                        else None
                    )
                }
            )
            for trade in trades
        ]
        strategy = StrategyPhaseAnalyzer.analyze(
            trades,
            timelines,
            declared=str(declared) if declared else None,
            fallback_profile=baseline.observed_profile,
        ).model_copy(
            update={
                "strategy_drift_score": baseline.strategy_drift_score,
                "drift_details": baseline.drift_details,
            }
        )

        observed_at = max(overview_observed_at, ledger_observed_at)
        sources = [
            grade_source(
                "overview",
                overview_observed_at,
                observed_at,
                now,
                self.evaluation_mode,
                1,
            ),
            grade_source(
                "trade_ledger",
                ledger_observed_at,
                observed_at,
                now,
                self.evaluation_mode,
                len(trades),
            ),
            grade_source(
                "current_positions",
                ledger_observed_at,
                observed_at,
                now,
                self.evaluation_mode,
                current.open_positions_count,
            ),
        ]
        required_fields = [
            reference_capital is not None,
            bool(overview.get("uniqueCode")),
            bool(trades),
            parsed.rejected_count == 0,
            status in ("RECONCILED", "PARTIAL_LEDGER"),
        ]
        if current.open_positions_count:
            required_fields.extend(
                [
                    current.current_notional is not None,
                    current.unknown_positions_count == 0,
                ]
            )
        completeness = sum(required_fields) / len(required_fields)
        freshness = sum(
            source.status == SourceStatus.AVAILABLE for source in sources
        ) / len(sources)
        overall = completeness * 0.7 + freshness * 0.3
        coverage_days = None
        if trades:
            coverage_days = (
                max(t.close_time for t in trades) - min(t.open_time for t in trades)
            ) / 86_400_000.0
        unique_code = str(overview.get("uniqueCode", "UNKNOWN"))
        primary, share, observed_symbols, identity_warnings = (
            self._resolve_identity_market(
                clean, trades, current.exposure_by_symbol or None
            )
        )
        assessed_symbol = primary or clean
        fingerprint = hashlib.sha256(
            "|".join(
                f"{trade.trade_id}:{trade.realized_pnl:.8f}" for trade in trades
            ).encode("utf-8")
        ).hexdigest()[:16]

        # `parsed.warnings` (trades/ledger.py) and `deferred_loss.warnings`
        # (analytics/performance/deferred_loss.py) are sibling modules this
        # task's file list does not cover -- translated at this boundary via
        # `_vi_upstream_warning`, same as `capital_warnings` above.
        warnings = [
            *(_vi_upstream_warning(w) for w in parsed.warnings),
            *reconciliation.warnings,
            *identity_warnings,
            *capital_warnings,
            *position_warnings,
            *(_vi_upstream_warning(w) for w in deferred_loss.warnings),
        ]
        if capital.supports_historical_pct:
            warnings.append(
                f"Capital basis {capital.basis}: {capital.equity_curve.usable_points} "
                f"weekly capital points anchor both the historical drawdown and the "
                f"forward simulation"
            )
        if current_equity is None:
            warnings.append(
                "No current account equity available; AUM was not reported as account equity"
            )
        if parsed.rejected_count:
            warnings.append(f"Rejected {parsed.rejected_count} invalid trade(s)")
        if any(source.status == SourceStatus.STALE for source in sources):
            warnings.append("This bot's snapshot is stale")
        data_quality = DataQualityAssessment(
            completeness_score=completeness,
            freshness_score=freshness,
            overall_score=overall,
            freshness_ms=max((source.age_ms or 0 for source in sources), default=0),
            coverage_days=coverage_days,
            capital_reference_source=reference_source,
            capital_basis=capital_basis,
            measurement_mode=mode,
            valid_trade_count=len(trades),
            rejected_trade_count=parsed.rejected_count,
            sources=sources,
            warnings=warnings,
        )

        simulation = MonteCarloSimulationEngine.run_simulation(
            trades=trades,
            initial_equity=capital.capital_at_risk,
            capital_basis=capital.basis,
            iterations=simulation_iterations,
            horizon_trades=simulation_horizon,
            block_bootstrap=True,
            seed=seed,
            current_drawdown_pct=drawdown.current_dd_pct,
            trade_frequency_per_day=performance.trade_frequency_per_day,
        )
        # Whether the edge survives sample length, fat tails and the fact that
        # this bot was picked as the best of its pool.
        equity_base = capital.capital_at_risk
        if equity_base and trades:
            # `trial_sharpe_variance`: phương sai CHÉO của Sharpe trên quần
            # thể bot đã chấm -- đúng đại lượng V[{SR̂ₙ}] mà công thức
            # deflated Sharpe đòi. Không truyền vào thì hàm rơi về xấp xỉ
            # theo giả thuyết không, vốn đặt ngưỡng thấp hơn khoảng 5 lần
            # trên dữ liệu thật của dự án (xem sharpe_reference.py).
            # Đọc từ `_reference_data_dir` chứ không phải `self.data_dir`, vì
            # đây là kho tham chiếu dùng chung, cùng lý do như `_phase_timelines`.
            inference = analyse_sharpe(
                [trade.realized_pnl / equity_base for trade in trades],
                selection_trials=selection_trials,
                trial_sharpe_variance=population_sharpe_variance(
                    self._reference_data_dir
                ),
            )
            simulation = simulation.model_copy(
                update={
                    "sharpe_per_trade": inference.sharpe_per_trade,
                    "probabilistic_sharpe": inference.psr,
                    "min_track_record_trades": inference.min_track_record_trades,
                    "deflated_sharpe": inference.deflated_sharpe,
                    "selection_trials": inference.selection_trials,
                    "inference_reliable": inference.reliable,
                    "inference_notes": list(inference.notes),
                }
            )

        if deferred_loss.distorts_headline_metrics and deferred_loss.open_loss:
            # The resample draws only from losses the bot chose to take.
            simulation = simulation.model_copy(
                update={
                    "deferred_loss_bias": True,
                    "warnings": [
                        *simulation.warnings,
                        f"Resampling only draws from closed trades; "
                        f"{deferred_loss.open_loss:,.0f} USDT of unrealised loss is not "
                        f"part of this distribution",
                    ],
                }
            )
        stress = StressSimulator.run_stress(trades, capital.capital_at_risk)
        # Exit discipline from the ledger alone -- no market data, no other
        # bot, so it is produced for every bot including ones trading
        # instruments this project holds no candles for.
        exit_rule = ExitRuleAnalyzer.analyze(trades)
        return BotResult(
            identity=BotIdentity(
                bot_id=f"BOT_{unique_code}_{assessed_symbol}",
                unique_code=unique_code,
                nick_name=str(overview.get("nickName", "UNKNOWN")),
                account=overview.get("account"),
                symbol=assessed_symbol,
                asset_context=clean,
                primary_traded_symbol=primary,
                venue="OKX",
                declared_strategy=str(declared) if declared else None,
                observed_symbols=observed_symbols,
                symbol_exposure_share=share,
                identity_warnings=identity_warnings,
                ledger_fingerprint=fingerprint,
            ),
            timestamp=now,
            as_of_ms=observed_at or now,
            current_state=current,
            performance=performance,
            deferred_loss=deferred_loss,
            trade_statistics=trade_statistics,
            trade_ledger_summary=trades,
            behavioral_observations=behavior,
            strategy_observations=strategy,
            drawdown_analysis=drawdown,
            simulation_results=simulation,
            stress_results=stress,
            exit_rule=exit_rule,
            reconciliation=reconciliation,
            capital=capital,
            data_quality=data_quality,
        )
