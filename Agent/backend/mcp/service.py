from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from Agent.backend.infra.config import config
from Agent.backend.infra.quality import (
    EvaluationMode,
    SourceStatus,
    grade_source,
)
from Agent.backend.mcp.analytics.behavior.detector import BehavioralPatternDetector
from Agent.backend.mcp.capital.equity_curve import CapitalResolver
from Agent.backend.mcp.analytics.drawdown.underwater import DrawdownUnderwaterAnalyzer
from Agent.backend.mcp.analytics.performance.deferred_loss import DeferredLossAnalyzer
from Agent.backend.mcp.analytics.performance.distribution import (
    TradeStatisticsCalculator,
)
from Agent.backend.mcp.analytics.performance.metrics import PerformanceMetricsCalculator
from Agent.backend.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.mcp.analytics.simulation.inference import analyse as analyse_sharpe
from Agent.backend.mcp.analytics.simulation.stress import StressSimulator
from Agent.backend.mcp.analytics.strategy.phases import PhaseTimeline, build_timeline
from Agent.backend.mcp.analytics.strategy.profile import (
    StrategyPhaseAnalyzer,
    base_symbol,
)
from Agent.backend.mcp.schemas.bot_result import (
    BotCurrentState,
    BotIdentity,
    BotResult,
    DataQualityAssessment,
    LedgerReconciliation,
    StrategyObservations,
    TradeLedgerItem,
)
from Agent.backend.mcp.positions.snapshot import PositionSnapshotParser
from Agent.backend.mcp.trades.identity import LedgerIdentityGuard
from Agent.backend.mcp.trades.ledger import TradeLedgerManager
from Agent.backend.sources.bot_source import BotDataSource, FileBotDataSource


class BotDataUnavailableError(ValueError):
    pass


class BotObservationService:
    """LOGIC 2: normalize a bot snapshot, analyze its ledger, and own simulation."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        evaluation_mode: EvaluationMode = EvaluationMode.SNAPSHOT,
        bot_source: Optional[BotDataSource] = None,
    ) -> None:
        self.data_dir = data_dir or Path(config.DATA_DIR)
        self._timeline_cache: Dict[str, Optional[PhaseTimeline]] = {}
        self.evaluation_mode = evaluation_mode
        # Defaults to the on-disk crawl output -- every existing caller keeps
        # reading exactly what Agent/scripts/crawl_bots.py wrote. Passing a
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
        Agent/scripts/crawl_bots.py has ever written predates that field, so
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
        for kind in (requested,) if requested else ("CEX", "DEX"):
            candidate = self.data_dir / kind.lower() / asset / "bot" / folder
            if candidate.is_dir():
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
                "Neither the trade ledger nor the open positions name an instrument; "
                "the traded market is unknown"
            )
        elif source == "open positions":
            warnings.append(
                f"No closed trades: traded market {primary} was taken from the currently "
                f"open positions"
            )
        elif asset_context not in share:
            warnings.append(
                f"Snapshot is filed under {asset_context} but the ledger never traded it; "
                f"dominant traded market is {primary} ({share[primary]:.0%} of exposure)"
            )
        elif share.get(asset_context, 0.0) < 0.5:
            warnings.append(
                f"{asset_context} is only {share[asset_context]:.0%} of traded exposure; "
                f"dominant traded market is {primary}"
            )
        if len(observed) > 1:
            warnings.append(
                f"Bot trades {len(observed)} instruments; single-market assessment covers "
                f"{primary} only"
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
        warnings = list(snapshot.warnings)
        if consistency == "MARGIN_EXCEEDS_CAPITAL":
            warnings.append(
                f"Committed margin ({snapshot.used_margin:,.0f}) exceeds reported capital "
                f"({reference_capital:,.0f}); capital-relative ratios are not trustworthy "
                f"until the capital figure is confirmed"
            )
        return state, warnings

    def _phase_timelines(self, symbols: Iterable[str]) -> Dict[str, PhaseTimeline]:
        """Hourly phase labels for every symbol we hold candles for.

        Cached per service instance: one bot can touch a hundred instruments and
        rebuilding a 30k-point timeline for each would dominate the run.
        """
        timelines: Dict[str, PhaseTimeline] = {}
        for symbol in {str(s).upper() for s in symbols if s}:
            if symbol in self._timeline_cache:
                cached = self._timeline_cache[symbol]
                if cached is not None:
                    timelines[symbol] = cached
                continue
            candles = None
            # Universe assets first, then the reference series kept only for phase
            # labelling (data/phases), which never widen Logic 1's universe.
            paths = [
                self.data_dir / venue / symbol / "market" / name
                for venue in ("cex", "dex")
                for name in ("ohlcv_1h_2023_present.json", "ohlcv_1h_2026.json")
            ]
            paths.append(self.data_dir / "phases" / f"{symbol}.json")
            for path in paths:
                if not path.exists():
                    continue
                try:
                    candles = json.loads(path.read_text(encoding="utf-8")).get(
                        "candles"
                    )
                except (OSError, json.JSONDecodeError):
                    candles = None
                if candles:
                    break
            timeline = build_timeline(symbol, candles) if candles else None
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
        overview = self._bot_source.get_overview(code_hint, bot_dir=bot_dir)
        if overview is None:
            raise BotDataUnavailableError(
                f"Missing bot data file: overview.json ({bot_dir})"
            )
        raw_ledger = self._bot_source.get_ledger(code_hint, bot_dir=bot_dir)
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

        capital_warnings: List[str] = list(capital.warnings)
        if reference_capital is not None and reference_capital <= 0:
            capital_warnings.append(
                f"Reported AUM is {reference_capital:g}; reference capital treated as unavailable"
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
                f"Trade ledger is owned by {', '.join(ownership.foreign_codes)} but the "
                f"profile is {ownership.expected_code}; the ledger was rejected and this "
                f"bot is assessed without trade history"
            )
        elif reported_pnl is None:
            status = "UNKNOWN"
            recon_warnings.append("Reported PnL is unavailable for reconciliation")
        elif reconciled:
            status = "RECONCILED"
        elif truncated or short_coverage:
            status = "PARTIAL_LEDGER"
            detail = (
                "page limit reached"
                if truncated
                else "covers only part of the lead period"
            )
            recon_warnings.append(
                f"Ledger is a subset of lifetime history ({detail}): "
                f"{len(trades)} trades over "
                f"{coverage_days:.0f} days vs {lead_days} lead days"
                if coverage_days is not None and lead_days
                else f"Ledger is a subset of lifetime history ({detail})"
            )
        elif reported_provenance != "OKX_VERIFIED":
            status = "UNVERIFIED_REFERENCE"
            recon_warnings.append(
                "Reported PnL comes from an unverified local snapshot (OKX publishes no "
                "per-trader profile endpoint), so the difference is not evidence of a bad ledger"
            )
        else:
            status = "MISMATCH"
            recon_warnings.append(
                "Ledger is complete and the reference is verified, yet the totals disagree"
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
        behavior = BehavioralPatternDetector.analyze(
            trades, current.open_positions_count
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

        warnings = [
            *parsed.warnings,
            *reconciliation.warnings,
            *identity_warnings,
            *capital_warnings,
            *position_warnings,
            *deferred_loss.warnings,
        ]
        if capital.supports_historical_pct:
            warnings.append(
                f"Capital basis {capital.basis}: {capital.equity_curve.usable_points} weekly "
                f"equity observations anchor both historical drawdown and forward simulation"
            )
        if current_equity is None:
            warnings.append(
                "Current account equity is unavailable; AUM is not reported as account equity"
            )
        if parsed.rejected_count:
            warnings.append(f"Rejected {parsed.rejected_count} invalid trades")
        if any(source.status == SourceStatus.STALE for source in sources):
            warnings.append("Bot snapshot is stale")
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
            inference = analyse_sharpe(
                [trade.realized_pnl / equity_base for trade in trades],
                selection_trials=selection_trials,
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
                        f"Resampled from closed trades only; {deferred_loss.open_loss:,.0f} "
                        f"USDT of unrealised loss is absent from this distribution",
                    ],
                }
            )
        stress = StressSimulator.run_stress(trades, capital.capital_at_risk)
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
            reconciliation=reconciliation,
            capital=capital,
            data_quality=data_quality,
        )
