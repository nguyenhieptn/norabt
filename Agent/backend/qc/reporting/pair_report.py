"""Step 2 report: the two bots chosen for each asset, side by side.

Why this shape: each asset was given one bot that is doing well and one that runs
but does not keep up, precisely so the pair can be compared. A flat list of every
bot folder in the dataset loses that pairing, and it also drags in bots that were
never selected. This report walks the selection, runs Logic 2 on both bots of each
slot, and prints the market they trade in beside them.

Logic 1 appears here only as context for reading the pair. The verdict belongs to
step 3; nothing in this file scores a bot.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.market.service import MarketDataUnavailableError, MarketService
from Agent.backend.mcp.service import BotDataUnavailableError, BotObservationService

# BotSourceError comes from BotObservationService's data source (a corrupt
# file, or an OKX failure under LiveBotDataSource) and passes through
# get_bot_result() unconverted -- it is intentionally not a
# BotDataUnavailableError/ValueError (see its docstring), so it needs its own
# except clause. No circular import: bot_source.py only imports from live/,
# mcp/inference/ and okx/, never from qc/reporting/.
from Agent.backend.sources.bot_source import BotSourceError
from Agent.backend.qc.reporting.market_posture import assess as assess_posture
from Agent.backend.qc.reporting.reasons import phase_vi

SELECTION = Path(config.DATA_DIR) / "universe" / "bot_selection.json"
ROLE_LEAD = "CHẠY NGON"
ROLE_LAGGARD = "YẾU HƠN"


class PairedBotRow(BaseModel):
    role: str
    nick_name: str
    unique_code: str
    okx_rank: Optional[int] = None
    board_roi_pct: Optional[float] = None

    trade_count: int = Field(default=0, ge=0)
    trades_on_asset: int = Field(default=0, ge=0)
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    marked_profit_factor: Optional[float] = None
    expectancy: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    max_drawdown_capped: bool = False
    ledger_pnl: Optional[float] = None

    open_positions: int = Field(default=0, ge=0)
    gross_exposure: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    open_loss: Optional[float] = None
    current_leverage: Optional[float] = None

    directional_bias: str = "UNKNOWN"
    entry_style: str = "UNKNOWN"
    entry_style_evidence: Optional[str] = None
    phase_coverage_pct: Optional[float] = None
    regime_dependence_pct: Optional[float] = None
    best_phase: Optional[str] = None
    worst_phase: Optional[str] = None
    losing_phases: List[str] = Field(default_factory=list)
    untested_phases: List[str] = Field(default_factory=list)
    tested_in_downtrend: bool = False
    phase_rows: List[Dict[str, Any]] = Field(default_factory=list)

    # Risk-adjusted return and trading rhythm: a profit factor alone does not
    # say whether the edge is worth the variance, or how often it is taken.
    payoff_ratio: Optional[float] = None
    average_win: Optional[float] = None
    average_loss: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    recovery_factor: Optional[float] = None
    max_win_streak: int = Field(default=0, ge=0)
    max_loss_streak: int = Field(default=0, ge=0)
    median_hold_minutes: Optional[float] = None
    trades_per_day: Optional[float] = None

    # Shape of the per-trade distribution, which is what the bootstrap resamples.
    pnl_median: Optional[float] = None
    pnl_std: Optional[float] = None
    pnl_skew: Optional[float] = None
    pnl_kurtosis: Optional[float] = None
    pnl_p05: Optional[float] = None
    pnl_p95: Optional[float] = None
    mean_pnl_ci: Optional[List[float]] = None
    measurement_mode: Optional[str] = None

    # Capital the percentages are measured against, and how it was derived.
    capital_at_risk: Optional[float] = None
    capital_basis: Optional[str] = None
    ledger_coverage_days: Optional[float] = None
    declared_lead_days: Optional[int] = None

    # Deterministic shocks, as a counterpart to the resampled ones.
    stress_volatility_2x: Optional[float] = None
    stress_spread_3x: Optional[float] = None
    stress_liquidity_half: Optional[float] = None
    stress_verdict: Optional[str] = None

    # Monte Carlo over the bot's own trade count: what the same edge could have
    # produced across 10k replays, and how bad the bad runs get.
    mc_iterations: Optional[int] = None
    mc_horizon: Optional[int] = None
    mc_sample_size: Optional[int] = None
    mc_deferred_loss_bias: bool = False
    mc_profit_worst_pct: Optional[float] = None
    mc_profit_p05_pct: Optional[float] = None
    mc_profit_p50_pct: Optional[float] = None
    mc_profit_p95_pct: Optional[float] = None
    mc_profit_best_pct: Optional[float] = None
    mc_p95_drawdown: Optional[float] = None
    mc_worst_drawdown: Optional[float] = None
    mc_p_ruin: Optional[float] = None
    mc_p_loss: Optional[float] = None
    mc_median_drawdown: Optional[float] = None
    cvar_95_pct: Optional[float] = None
    mar_ratio_median: Optional[float] = None
    probability_of_profit: Optional[float] = None
    sharpe_per_trade: Optional[float] = None
    psr: Optional[float] = None
    min_track_record_trades: Optional[float] = None
    deflated_sharpe: Optional[float] = None
    selection_trials: Optional[int] = None
    inference_reliable: bool = True
    inference_notes: List[str] = Field(default_factory=list)

    data_quality: Optional[float] = None
    reconciliation: str = "UNKNOWN"
    warnings: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class AssetPairBlock(BaseModel):
    venue_type: str
    symbol: str
    underlying: str
    market_available: bool = False
    market_posture: str = "CHƯA ĐỦ CƠ SỞ"
    market_evidence: List[str] = Field(default_factory=list)
    market_trend: Optional[str] = None
    market_volatility: Optional[str] = None
    market_liquidity: Optional[str] = None
    market_quality: Optional[float] = None
    market_error: Optional[str] = None
    bots: List[PairedBotRow] = Field(default_factory=list)
    comparison: List[str] = Field(default_factory=list)


class PairedBotReport(BaseModel):
    schema_version: str = "paired_bot_report.v1"
    generated_at_ms: int
    evaluation_mode: EvaluationMode
    slots: int = Field(default=0, ge=0)
    bots_evaluated: int = Field(default=0, ge=0)
    bots_failed: int = Field(default=0, ge=0)
    blocks: List[AssetPairBlock] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class PairedBotReportService:
    """Run Logic 1 and Logic 2 over the selection, paired by asset."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        evaluation_mode: EvaluationMode = EvaluationMode.SNAPSHOT,
    ) -> None:
        self.data_dir = data_dir or Path(config.DATA_DIR)
        self.evaluation_mode = evaluation_mode
        self.market = MarketService(self.data_dir, evaluation_mode)
        self.bots = BotObservationService(self.data_dir, evaluation_mode)

    def _locate(self, code: str) -> tuple[Optional[str], Optional[str]]:
        """Bot folders sit under the bot's own dominant market, not the slot's."""
        for path in self.data_dir.rglob(f"bot_{code}"):
            if (path / "trade_list.json").exists():
                parts = path.relative_to(self.data_dir).parts
                if len(parts) >= 2:
                    return parts[0].upper(), parts[1]
        return None, None

    def _trades_on_asset(self, code: str, underlying: str) -> Optional[int]:
        """Count from the crawled ledger, not the sampled profile.

        The selection profiled only the latest 100 fills per trader, so its
        per-asset count understates a bot whose full ledger runs to 500.
        """
        for path in self.data_dir.rglob(f"bot_{code}/trade_list.json"):
            try:
                ledger = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
            return sum(
                1
                for trade in ledger.get("closed_trades") or []
                if str(trade.get("instId", "")).split("-")[0].upper() == underlying
            )
        return None

    def _bot_row(
        self,
        role: str,
        entry: Dict[str, Any],
        underlying: str,
        as_of_ms: int,
        iterations: int,
        horizon: Optional[int],
        selection_trials: Optional[int] = None,
    ) -> PairedBotRow:
        code = entry["code"]
        base = PairedBotRow(
            role=role,
            nick_name=entry.get("name") or code,
            unique_code=code,
            okx_rank=entry.get("okx_rank"),
            board_roi_pct=entry.get("roi_pct"),
            trades_on_asset=self._trades_on_asset(code, underlying)
            or entry.get("trades_on_asset", 0),
        )
        venue, asset = self._locate(code)
        if venue is None or asset is None:
            return base.model_copy(update={"error": "chưa có dữ liệu đã crawl"})

        try:
            bot = self.bots.get_bot_result(
                asset,
                f"bot_{code}",
                venue_type=venue,
                seed=42,
                as_of_ms=as_of_ms,
                simulation_iterations=iterations,
                simulation_horizon=horizon,
                selection_trials=selection_trials,
            )
        except (BotDataUnavailableError, BotSourceError, ValueError) as exc:
            # A single bot's data failure (missing/corrupt file, or an OKX
            # error under the live source) must degrade to one FAILED row,
            # not abort build() for the whole selection -- build() walks
            # every asset's pair, and in live mode each bot already cost
            # several OKX requests to get this far.
            return base.model_copy(update={"error": f"{type(exc).__name__}: {exc}"})

        perf = bot.performance
        state = bot.current_state
        deferred = bot.deferred_loss
        strategy = bot.strategy_observations
        drawdown = bot.drawdown_analysis
        sim = bot.simulation_results
        stats = bot.trade_statistics
        stress = bot.stress_results
        return base.model_copy(
            update={
                "nick_name": bot.identity.nick_name or base.nick_name,
                "trade_count": perf.trade_count,
                "win_rate": perf.win_rate,
                "profit_factor": perf.profit_factor,
                "marked_profit_factor": deferred.marked_profit_factor,
                "expectancy": perf.expectancy,
                "sharpe_ratio": perf.sharpe_ratio,
                "max_drawdown_pct": perf.max_drawdown_pct,
                "max_drawdown_capped": drawdown.max_dd_pct_capped,
                "ledger_pnl": perf.total_pnl,
                "open_positions": state.open_positions_count,
                "gross_exposure": state.gross_exposure,
                "unrealized_pnl": state.unrealized_pnl,
                "open_loss": deferred.open_loss,
                "current_leverage": state.current_leverage,
                "directional_bias": strategy.directional_bias,
                "entry_style": strategy.entry_style,
                "entry_style_evidence": strategy.entry_style_evidence,
                "phase_coverage_pct": strategy.phase_coverage_pct,
                "regime_dependence_pct": strategy.regime_dependence_pct,
                "best_phase": strategy.best_phase,
                "worst_phase": strategy.worst_phase,
                "losing_phases": strategy.losing_phases,
                "untested_phases": strategy.untested_phases,
                "tested_in_downtrend": strategy.tested_in_downtrend,
                "phase_rows": [row.model_dump() for row in strategy.phase_breakdown],
                "payoff_ratio": perf.payoff_ratio,
                "average_win": perf.average_win,
                "average_loss": perf.average_loss,
                "sortino_ratio": perf.sortino_ratio,
                "calmar_ratio": perf.calmar_ratio,
                "recovery_factor": perf.recovery_factor,
                "max_win_streak": perf.max_win_streak,
                "max_loss_streak": perf.max_loss_streak,
                "median_hold_minutes": perf.median_hold_time_minutes,
                "trades_per_day": perf.trade_frequency_per_day,
                "pnl_median": stats.median_pnl,
                "pnl_std": stats.pnl_std,
                "pnl_skew": stats.pnl_skew,
                "pnl_kurtosis": stats.pnl_kurtosis,
                "pnl_p05": stats.p05_pnl,
                "pnl_p95": stats.p95_pnl,
                "mean_pnl_ci": stats.confidence_interval_mean_pnl,
                "measurement_mode": str(stats.measurement_mode.value),
                "capital_at_risk": bot.capital.capital_at_risk,
                "capital_basis": bot.capital.basis,
                "ledger_coverage_days": bot.reconciliation.ledger_coverage_days,
                "declared_lead_days": bot.reconciliation.declared_lead_days,
                "stress_volatility_2x": stress.volatility_2x_pnl_impact,
                "stress_spread_3x": stress.spread_3x_slippage_impact,
                "stress_liquidity_half": stress.liquidity_half_exit_impact,
                "stress_verdict": stress.stress_survival_verdict,
                "mc_iterations": sim.iterations,
                "mc_horizon": sim.horizon_trades,
                "mc_sample_size": sim.sample_size,
                "mc_deferred_loss_bias": sim.deferred_loss_bias,
                "mc_profit_worst_pct": sim.profit_pct_worst,
                "mc_profit_p05_pct": sim.profit_pct_p05,
                "mc_profit_p50_pct": sim.profit_pct_p50,
                "mc_profit_p95_pct": sim.profit_pct_p95,
                "mc_profit_best_pct": sim.profit_pct_best,
                "mc_p95_drawdown": sim.p95_max_drawdown,
                "mc_worst_drawdown": sim.worst_percentile_drawdown,
                "mc_p_ruin": sim.p_ruin,
                "mc_p_loss": sim.p_loss_after_horizon,
                "mc_median_drawdown": sim.median_max_drawdown,
                "cvar_95_pct": sim.cvar_95_pct,
                "mar_ratio_median": sim.mar_ratio_median,
                "probability_of_profit": sim.probability_of_profit,
                "sharpe_per_trade": sim.sharpe_per_trade,
                "psr": sim.probabilistic_sharpe,
                "min_track_record_trades": sim.min_track_record_trades,
                "deflated_sharpe": sim.deflated_sharpe,
                "selection_trials": sim.selection_trials,
                "inference_reliable": sim.inference_reliable,
                "inference_notes": list(sim.inference_notes),
                "data_quality": bot.data_quality.overall_score,
                "reconciliation": bot.reconciliation.status,
                "warnings": list(bot.data_quality.warnings)[:3],
            }
        )

    @staticmethod
    def _compare(block: AssetPairBlock) -> List[str]:
        """State what the pair actually shows, or why it cannot be compared."""
        usable = [b for b in block.bots if b.error is None and b.trade_count]
        if len(usable) < 2:
            return ["Chưa đủ hai bot có dữ liệu để so sánh."]
        lead, lag = usable[0], usable[1]
        notes: List[str] = []

        if lead.profit_factor is not None and lag.profit_factor is not None:
            notes.append(
                f"Profit factor {lead.nick_name} {lead.profit_factor:.2f} "
                f"so với {lag.nick_name} {lag.profit_factor:.2f}."
            )
        for bot in usable:
            if (
                bot.profit_factor is not None
                and bot.marked_profit_factor is not None
                and bot.profit_factor >= 1.0
                and bot.marked_profit_factor < 1.0
            ):
                notes.append(
                    f"{bot.nick_name} chỉ lãi trên sổ đã chốt: tính cả vị thế mở thì "
                    f"profit factor rơi xuống {bot.marked_profit_factor:.2f}."
                )
            if (
                bot.regime_dependence_pct is not None
                and bot.regime_dependence_pct >= 70
            ):
                notes.append(
                    f"{bot.nick_name} lấy {bot.regime_dependence_pct:.0f}% lợi nhuận từ "
                    f"riêng pha {phase_vi(bot.best_phase)}; đổi chế độ là mất lợi thế."
                )
            if bot.trade_count >= 20 and not bot.tested_in_downtrend:
                notes.append(
                    f"{bot.nick_name} chưa có đủ lệnh nào trong pha giảm — "
                    "chiến lược chưa được thử ở chiều xuống."
                )
            if len(bot.losing_phases) >= 4:
                notes.append(
                    f"{bot.nick_name} lỗ ở {len(bot.losing_phases)}/6 pha thị trường, "
                    "không chỉ riêng một chế độ."
                )
            if bot.max_drawdown_capped:
                notes.append(
                    f"{bot.nick_name}: mức sụt vốn vượt vốn ghi nhận tại thời điểm đó "
                    "nên con số phần trăm là sàn, không phải đo được."
                )
        return notes

    def build(
        self,
        as_of_ms: Optional[int] = None,
        simulation_iterations: int = 10_000,
        simulation_horizon: Optional[int] = None,
        selection_path: Optional[Path] = None,
        only_codes: Optional[set] = None,
    ) -> PairedBotReport:
        path = selection_path or (self.data_dir / "universe" / "bot_selection.json")
        selection = json.loads(path.read_text(encoding="utf-8"))
        now = as_of_ms or int(time.time() * 1000)

        blocks: List[AssetPairBlock] = []
        evaluated = failed = 0
        for record in selection["assets"]:
            if only_codes and not any(
                record.get(slot) and record[slot]["code"] in only_codes
                for slot in ("top", "mid")
            ):
                continue
            block = AssetPairBlock(
                venue_type=record["venue"],
                symbol=record["symbol"],
                underlying=record["underlying"],
            )
            try:
                market = self.market.get_market_result(
                    record["symbol"], venue_type=record["venue"], as_of_ms=now
                )
            except MarketDataUnavailableError as exc:
                block.market_error = str(exc)
            else:
                posture = assess_posture(market)
                evidence = {
                    "RỦI RO": posture.risk_flags,
                    "ĐANG PHÁT TRIỂN": posture.growth_flags,
                    "ỔN ĐỊNH": posture.stability_flags,
                }.get(posture.posture, [])
                block.market_available = True
                block.market_posture = posture.posture
                block.market_evidence = evidence
                block.market_trend = market.structure_state.trend_state.value
                block.market_volatility = market.structure_state.volatility_state.value
                block.market_liquidity = market.liquidity_state.state_tier.value
                block.market_quality = market.data_quality_score

            for role, slot in ((ROLE_LEAD, "top"), (ROLE_LAGGARD, "mid")):
                entry = record.get(slot)
                if not entry:
                    continue
                if only_codes and entry["code"] not in only_codes:
                    continue
                row = self._bot_row(
                    role,
                    entry,
                    record["underlying"],
                    now,
                    simulation_iterations,
                    simulation_horizon,
                    # The bot was picked as the best of this many candidates on
                    # the asset, which is the multiple testing the DSR corrects.
                    selection_trials=record.get("candidates"),
                )
                if row.error:
                    failed += 1
                else:
                    evaluated += 1
                block.bots.append(row)

            block.comparison = self._compare(block)
            blocks.append(block)

        return PairedBotReport(
            generated_at_ms=now,
            evaluation_mode=self.evaluation_mode,
            slots=len(blocks),
            bots_evaluated=evaluated,
            bots_failed=failed,
            blocks=blocks,
            notes=[
                "Mỗi asset gồm 1 bot chạy ngon và 1 bot cũng chạy nhưng kém hơn, "
                "chọn theo lợi nhuận thực hiện tại thời điểm quét.",
                "Pha thị trường lấy tại thời điểm MỞ lệnh; lệnh trên instrument "
                "không có nến được tính là chưa rõ pha, không gộp vào pha nào.",
                "Monte Carlo stationary bootstrap (Politis-Romano 1994), 10.000 kịch bản, mỗi kịch bản "
                "replay đúng số lệnh của chính bot. Mẫu CHỈ gồm lệnh đã chốt — "
                "vị thế đang mở cố ý không đưa vào, nên phần lỗ treo (nếu có) "
                "được nêu riêng chứ không trộn vào phân vị lợi nhuận.",
                "Đây là quan sát, chưa phải phán quyết rủi ro — phán quyết ở bước 3.",
            ],
        )
