from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.market.schemas.market_result import MarketResult
from Agent.backend.market.service import MarketDataUnavailableError, MarketService
from Agent.backend.mcp.schemas.bot_result import BotResult, PositionSide
from Agent.backend.mcp.service import BotDataUnavailableError, BotObservationService

# BotSourceError is raised by BotObservationService's underlying data source
# (FileBotDataSource for a corrupt file, LiveBotDataSource for an OKX
# failure) and propagates through get_bot_result() unconverted -- it is
# deliberately NOT a BotDataUnavailableError/ValueError (see its docstring),
# so it must be caught here explicitly. No circular import: bot_source.py
# only imports from live/, mcp/inference/ and okx/, never from qc/reporting/.
from Agent.backend.sources.bot_source import BotSourceError
from Agent.backend.qc.schemas.risk_assessment import (
    BotRiskAssessment,
    EvidenceStatus,
    RiskTier,
)
from Agent.backend.qc.history.store import AssessmentHistoryStore
from Agent.backend.qc.reporting.gaps import EvidenceGap, build_gaps
from Agent.backend.qc.scoring.fusion import DIMENSION_LABEL_VI
from Agent.backend.qc.service import QCCoreService
from Agent.backend.universe.registry import UniverseRegistry

TIER_ORDER = {
    RiskTier.EMERGENCY: 0,
    RiskTier.CRITICAL: 1,
    RiskTier.HIGH: 2,
    RiskTier.ELEVATED: 3,
    RiskTier.WATCH: 4,
    RiskTier.UNKNOWN: 5,
    RiskTier.HEALTHY: 6,
}


def _observed_at_ms(bot: BotResult) -> int:
    """Newest evidence timestamp across the snapshot's own sources."""
    return max((source.observed_at or 0) for source in bot.data_quality.sources)


def _hard_evidence_score(bot: BotResult) -> int:
    """Evidence that changes what can be measured at all."""
    score = 0
    if bot.capital.supports_historical_pct:
        score += 4
    elif bot.capital.capital_at_risk:
        score += 1
    if bot.current_state.attributed_positions_count:
        score += 2
    if bot.reconciliation.status == "IDENTITY_MISMATCH":
        score -= 10
    # More history is strictly more evidence.
    score += min(3, bot.performance.trade_count // 100)
    return score


def _soft_evidence_score(bot: BotResult) -> int:
    """Nice-to-have context that must not outrank a fresher observation."""
    score = 0
    if bot.reconciliation.status == "RECONCILED":
        score += 2
    if bot.reconciliation.status == "PARTIAL_LEDGER":
        score += 1
    if bot.identity.declared_strategy:
        score += 1
    return score


def _provenance_rank(bot: BotResult) -> Tuple[int, int, int]:
    """Order duplicate snapshots of one bot: hard evidence, then recency, then context.

    Recency sits above the reconciliation nudge on purpose. An open-position book is
    what the risk call is made from, so a day-old book must not be kept just because
    the older crawl also carried a reference figure to reconcile against.
    """
    return (
        _hard_evidence_score(bot),
        _observed_at_ms(bot),
        _soft_evidence_score(bot),
    )


class MarketSnapshotRow(BaseModel):
    """What Logic 1 observed for the market the bot actually trades."""

    symbol: str
    venue_type: str
    trend: str
    volatility: str
    liquidity_tier: str
    flow_bias: str
    last_price: float
    data_quality: float = Field(..., ge=0.0, le=1.0)


class BotEvaluationRow(BaseModel):
    rank: int = Field(..., ge=1)
    status: str
    bot_id: str
    unique_code: str
    nick_name: str
    traded_symbol: str
    asset_context: str
    venue_type: str
    snapshot_venue: str
    bot_folder: str
    duplicate_snapshots: int = Field(default=1, ge=1)
    selected_snapshot: Optional[str] = None
    snapshot_locations: List[str] = Field(default_factory=list)
    exposure_share: Dict[str, float] = Field(default_factory=dict)
    identity_warnings: List[str] = Field(default_factory=list)

    market_available: bool = False
    market_resolution: str = "NO_MARKET_DATA_FOR_TRADED_SYMBOL"
    universe_eligible: bool = False
    eligibility_reason: str = "NOT_EVALUATED"
    market: Optional[MarketSnapshotRow] = None

    position_side: Optional[str] = None
    open_positions: Optional[int] = None
    unknown_positions_count: int = 0
    instrument_withheld_upstream: bool = False
    observed_positions_count: int = 0
    inferred_positions_count: int = 0
    positions_outside_ledger_universe: int = 0
    net_exposure: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    open_loss: Optional[float] = None
    open_loss_to_capital_pct: Optional[float] = None
    loss_representativeness: Optional[str] = None
    booked_profit_factor: Optional[float] = None
    marked_profit_factor: Optional[float] = None
    never_realized_a_loss: bool = False
    simulation_deferred_loss_bias: bool = False
    capital_consistency: Optional[str] = None
    open_exposure_by_symbol: Dict[str, float] = Field(default_factory=dict)
    leverage: Optional[float] = None
    gross_exposure: Optional[float] = None

    trade_count: Optional[int] = None
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    expectancy: Optional[float] = None
    total_pnl: Optional[float] = None
    roi_pct: Optional[float] = None
    capital_basis: Optional[str] = None
    capital_at_risk: Optional[float] = None
    wiped_out: bool = False
    weekly_equity_max_dd_pct: Optional[float] = None
    max_drawdown_abs: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    current_drawdown_pct: Optional[float] = None
    max_loss_streak: Optional[int] = None

    # How the bot trades, which the narrative needs to describe behaviour rather
    # than only outcomes.
    directional_bias: Optional[str] = None
    entry_style: Optional[str] = None
    phase_coverage_pct: Optional[float] = None
    regime_dependence_pct: Optional[float] = None
    best_phase: Optional[str] = None
    worst_phase: Optional[str] = None
    losing_phases: List[str] = Field(default_factory=list)
    untested_phases: List[str] = Field(default_factory=list)
    tested_in_downtrend: bool = False

    payoff_ratio: Optional[float] = None
    average_win: Optional[float] = None
    average_loss: Optional[float] = None
    max_win_streak: Optional[int] = None
    pnl_median: Optional[float] = None
    pnl_skew: Optional[float] = None
    pnl_kurtosis: Optional[float] = None
    ledger_coverage_days: Optional[float] = None
    declared_lead_days: Optional[int] = None
    positions_without_instrument: int = 0
    stress_verdict: Optional[str] = None
    quality_components: Dict[str, float] = Field(default_factory=dict)
    quality_notes: List[str] = Field(default_factory=list)
    var_95_pct: Optional[float] = None
    cvar_95_pct: Optional[float] = None
    mar_ratio_median: Optional[float] = None
    profit_factor_median: Optional[float] = None

    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    median_hold_minutes: Optional[float] = None
    trades_per_day: Optional[float] = None

    # Monte Carlo over the bot's own trade count, and the published tests that
    # say whether the edge behind it is real or a product of selection.
    mc_iterations: Optional[int] = None
    mc_horizon: Optional[int] = None
    p_ruin: Optional[float] = None
    p_loss_after_horizon: Optional[float] = None
    p_mdd_gt_15: Optional[float] = None
    p95_max_drawdown: Optional[float] = None
    worst_drawdown: Optional[float] = None
    profit_pct_worst: Optional[float] = None
    profit_pct_p05: Optional[float] = None
    profit_pct_p50: Optional[float] = None
    profit_pct_p95: Optional[float] = None
    psr: Optional[float] = None
    deflated_sharpe: Optional[float] = None
    min_track_record_trades: Optional[float] = None
    selection_trials: Optional[int] = None
    inference_reliable: bool = True
    p_5_loss_streak: Optional[float] = None

    risk_score: Optional[float] = None
    quality_score: Optional[float] = None
    verdict: Optional[str] = None
    verdict_reason: Optional[str] = None
    hidden_risk_flags: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    risk_tier: Optional[str] = None
    risk_trend: Optional[str] = None
    recommended_action: Optional[str] = None

    measurement_mode: Optional[str] = None
    reconciliation_status: Optional[str] = None
    weighted_average: Optional[float] = None
    veto_floor: Optional[float] = None
    score_decided_by: Optional[str] = None
    veto_reasons: List[str] = Field(default_factory=list)
    raised_the_score: List[str] = Field(default_factory=list)
    held_the_score_down: List[str] = Field(default_factory=list)
    dimension_scores: Dict[str, float] = Field(default_factory=dict)
    top_risk_drivers: List[str] = Field(default_factory=list)
    unknown_dimensions: List[str] = Field(default_factory=list)
    limitations_count: int = 0

    conclusion: str
    error: Optional[str] = None


class CohortReport(BaseModel):
    schema_version: str = "cohort_report.v1"
    methodology_version: str = "qc_fusion.v1"
    generated_at_ms: int
    evaluation_mode: EvaluationMode
    snapshots_scanned: int = Field(..., ge=0)
    distinct_bots: int = Field(..., ge=0)
    bots_failed: int = Field(..., ge=0)
    markets_resolved: int = Field(..., ge=0)
    tier_summary: Dict[str, int] = Field(default_factory=dict)
    rows: List[BotEvaluationRow] = Field(default_factory=list)
    gaps: List[EvidenceGap] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class CohortAssessmentService:
    """Evaluate every distinct bot in the dataset against the market it really trades."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        evaluation_mode: EvaluationMode = EvaluationMode.SNAPSHOT,
        history: Optional[AssessmentHistoryStore] = None,
        persist_history: bool = True,
    ) -> None:
        self.data_dir = data_dir or Path(config.DATA_DIR)
        self.history = history or AssessmentHistoryStore(
            self.data_dir / "state" / "assessments"
        )
        self.persist_history = persist_history
        self.evaluation_mode = evaluation_mode
        self.market_service = MarketService(self.data_dir, evaluation_mode)
        self.bot_service = BotObservationService(self.data_dir, evaluation_mode)

    def _selection_trials(self) -> Dict[str, int]:
        """Pool size each bot was picked from, keyed by uniqueCode.

        The deflated Sharpe needs it: a bot chosen as the best of 68 candidates
        has to clear a far higher bar than one assessed on its own.
        """
        path = self.data_dir / "universe" / "bot_selection.json"
        if not path.exists():
            return {}
        try:
            selection = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        trials: Dict[str, int] = {}
        for record in selection.get("assets", []):
            candidates = record.get("candidates")
            if not candidates:
                continue
            for slot in ("top", "mid"):
                entry = record.get(slot)
                if entry:
                    trials[str(entry["code"])] = int(candidates)
        return trials

    def _discover(self, venue_types: Tuple[str, ...]) -> List[Tuple[str, str, str]]:
        found: List[Tuple[str, str, str]] = []
        for venue_type in venue_types:
            root = self.data_dir / venue_type.lower()
            if not root.is_dir():
                continue
            for asset_dir in sorted(path for path in root.iterdir() if path.is_dir()):
                bot_root = asset_dir / "bot"
                if not bot_root.is_dir():
                    continue
                for bot_dir in sorted(
                    path for path in bot_root.iterdir() if path.is_dir()
                ):
                    found.append((venue_type, asset_dir.name, bot_dir.name))
        return found

    def _resolve_market(
        self, traded_symbol: str, as_of_ms: Optional[int]
    ) -> Tuple[Optional[MarketResult], str]:
        for venue_type in ("CEX", "DEX"):
            try:
                return (
                    self.market_service.get_market_result(
                        traded_symbol, venue_type=venue_type, as_of_ms=as_of_ms
                    ),
                    f"RESOLVED_{venue_type}",
                )
            except (MarketDataUnavailableError, ValueError):
                continue
        return None, "NO_MARKET_DATA_FOR_TRADED_SYMBOL"

    @staticmethod
    def _market_row(market: MarketResult) -> MarketSnapshotRow:
        return MarketSnapshotRow(
            symbol=market.symbol,
            venue_type=market.venue_type,
            trend=market.structure_state.trend_state.value,
            volatility=market.structure_state.volatility_state.value,
            liquidity_tier=market.liquidity_state.state_tier.value,
            flow_bias=market.orderflow_state.flow_bias,
            last_price=market.price_state.last_price,
            data_quality=market.data_quality_score,
        )

    @staticmethod
    def _conclusion(
        market: Optional[MarketResult],
        bot: BotResult,
        assessment: BotRiskAssessment,
    ) -> str:
        parts: List[str] = []
        if market is None:
            parts.append(
                f"Chưa có dữ liệu thị trường cho {bot.identity.symbol} — instrument bot "
                f"thực sự giao dịch, nên các chiều phụ thuộc thị trường để UNKNOWN."
            )
        else:
            structure = market.structure_state
            parts.append(
                f"Thị trường {market.symbol} ({market.venue_type}) đang {structure.trend_state.value}, "
                f"biến động {structure.volatility_state.value}, thanh khoản "
                f"{market.liquidity_state.state_tier.value}, dòng tiền "
                f"{market.orderflow_state.flow_bias}."
            )

        state = bot.current_state
        if state.current_position_side == PositionSide.FLAT:
            posture = "Bot đang đóng hết vị thế (FLAT)"
        elif state.current_position_side == PositionSide.UNKNOWN:
            posture = f"Bot đang mở {state.open_positions_count} vị thế nhưng thiếu định danh instrument"
        else:
            bits = [f"{state.open_positions_count} vị thế"]
            if state.current_leverage is not None:
                bits.append(f"đòn bẩy tối đa {state.current_leverage:.0f}x")
            if state.gross_exposure is not None:
                bits.append(f"exposure gộp {state.gross_exposure:,.0f} USDT")
            if state.unrealized_pnl is not None and state.unrealized_pnl < 0:
                bits.append(f"lỗ chưa thực hiện {state.unrealized_pnl:,.0f} USDT")
            posture = (
                f"Bot đang giữ {state.current_position_side.value} ({', '.join(bits)})"
            )
            if state.exposure_by_symbol:
                top = sorted(state.exposure_by_symbol.items(), key=lambda kv: -kv[1])[
                    :3
                ]
                posture += " trên " + ", ".join(
                    f"{sym} {value:,.0f}" for sym, value in top
                )
            elif state.unknown_positions_count:
                posture += (
                    f", {state.unknown_positions_count} vị thế chưa rõ instrument"
                )
        performance = bot.performance
        metrics = [
            f"{performance.trade_count} lệnh",
            f"win {performance.win_rate:.0f}%",
        ]
        if performance.profit_factor is not None:
            metrics.append(f"PF {performance.profit_factor:.2f}")
        if performance.max_drawdown_pct is not None:
            metrics.append(f"MaxDD {performance.max_drawdown_pct:.1f}%")
        elif performance.max_drawdown_abs is not None:
            metrics.append(
                f"MaxDD {performance.max_drawdown_abs:,.0f} USDT (không có nền vốn hợp lệ)"
            )
        if bot.simulation_results.p95_max_drawdown is not None:
            metrics.append(
                f"P95DD {bot.simulation_results.p95_max_drawdown:.1f}% vốn hiện tại"
            )
        if bot.simulation_results.p_ruin:
            metrics.append(f"P(cháy TK) {bot.simulation_results.p_ruin:.1f}%")
        if bot.capital.capital_at_risk:
            metrics.append(
                f"vốn tham chiếu {bot.capital.capital_at_risk:,.0f} USDT "
                f"({bot.capital.basis})"
            )
        parts.append(f"{posture}; {', '.join(metrics)}.")

        deferred = bot.deferred_loss
        if deferred.distorts_headline_metrics and deferred.open_loss:
            lead = (
                "CHƯA TỪNG CHỐT LỖ"
                if deferred.never_realized_a_loss
                else "LỖ HOÃN NHẬN"
            )
            detail = f"{lead}: đang ôm {deferred.open_loss:,.0f} USDT lỗ chưa chốt"
            if deferred.open_loss_to_capital_pct:
                detail += f" ({deferred.open_loss_to_capital_pct:.0f}% vốn)"
            if (
                deferred.booked_profit_factor is not None
                and deferred.marked_profit_factor is not None
            ):
                detail += (
                    f". Chốt hết thì PF từ {deferred.booked_profit_factor:.2f} "
                    f"còn {deferred.marked_profit_factor:.2f}"
                )
            elif deferred.marked_profit_factor is not None:
                detail += (
                    f". Chưa từng chốt lỗ nên PF vô nghĩa; chốt hết thì PF là "
                    f"{deferred.marked_profit_factor:.2f}"
                )
            parts.append(
                detail
                + ". Win rate, PF và MaxDD bên dưới chỉ mô tả những lệnh bot chọn đóng."
            )

        drivers = [
            item
            for item in dict(assessment.dimensions).values()
            if item.status == EvidenceStatus.AVAILABLE and item.score >= 60
        ]
        if drivers:
            drivers.sort(key=lambda item: item.score, reverse=True)
            named = ", ".join(
                f"{item.dimension_name} {item.score:.0f}" for item in drivers[:3]
            )
            parts.append(f"Chiều rủi ro vượt ngưỡng: {named}.")
        else:
            parts.append("Không có chiều rủi ro nào vượt ngưỡng cảnh báo.")

        parts.append(
            f"Kết luận: {assessment.risk_tier.value} "
            f"({assessment.risk_score:.1f}/100, tin cậy {assessment.confidence:.0f}%) "
            f"→ đề xuất {assessment.recommended_action}."
        )
        if bot.drawdown_analysis.wiped_out:
            parts.append(
                "CẢNH BÁO: đường vốn tuần từng chạm 0 — tài khoản đã cháy ít nhất một lần "
                "trong cửa sổ quan sát."
            )
        if state.capital_consistency == "MARGIN_EXCEEDS_CAPITAL":
            parts.append(
                "Margin cam kết vượt vốn báo cáo — số vốn cần xác minh trước khi tin các tỷ lệ theo vốn."
            )
        if assessment.confidence < 60.0:
            parts.append(
                "Độ tin cậy thấp nên cần bổ sung bằng chứng trước khi hành động."
            )
        return " ".join(parts)

    def scan(
        self,
        as_of_ms: Optional[int] = None,
        venue_types: Tuple[str, ...] = ("CEX", "DEX"),
        seed: int = 42,
        simulation_iterations: int = 5_000,
        simulation_horizon: int = 500,
        only_codes: Optional[Set[str]] = None,
    ) -> CohortReport:
        now = as_of_ms if as_of_ms is not None else int(time.time() * 1000)
        registry = UniverseRegistry(self.data_dir)
        rejections = registry.list_rejections()
        eligible_ids = {asset.asset_id for asset in registry.list_all()}

        # How many candidates each bot was chosen from, for the deflated Sharpe.
        trials_by_code = self._selection_trials()
        targets = self._discover(venue_types)
        if only_codes:
            # Step 3 ranks the bots step 2 selected, not every folder that was
            # ever crawled; the folder name carries the uniqueCode.
            wanted = {str(code) for code in only_codes}
            targets = [
                target for target in targets if target[2].replace("bot_", "") in wanted
            ]
        distinct: Dict[str, Dict[str, object]] = {}
        failures: List[BotEvaluationRow] = []

        for venue_type, asset, bot_folder in targets:
            location = f"{venue_type}/{asset}/{bot_folder}"
            try:
                bot = self.bot_service.get_bot_result(
                    asset,
                    bot_folder,
                    seed=seed,
                    venue_type=venue_type,
                    as_of_ms=now,
                    simulation_iterations=simulation_iterations,
                    simulation_horizon=simulation_horizon,
                    selection_trials=trials_by_code.get(bot_folder.replace("bot_", "")),
                )
            except (BotDataUnavailableError, BotSourceError, ValueError) as exc:
                # One bad bot must not abort the whole cohort scan: in live
                # mode this loop can be 30 bots deep and each one already
                # cost several OKX requests, so a single network hiccup or
                # OKX-format surprise (BotSourceError) is turned into one
                # FAILED row -- exactly like a missing/corrupt file already
                # was -- and the loop moves on to the rest.
                failures.append(
                    BotEvaluationRow(
                        rank=1,
                        status="FAILED",
                        bot_id=location,
                        unique_code="UNKNOWN",
                        nick_name="UNKNOWN",
                        traded_symbol="UNKNOWN",
                        asset_context=asset.upper(),
                        venue_type=venue_type,
                        # Required field -- mirrors the EVALUATED row below
                        # (snapshot_venue=str(entry["venue_type"])), which is
                        # this same loop's `venue_type` before it gets stashed
                        # into `entry`. Left out here, pydantic raised a
                        # ValidationError instead of a clean FAILED row.
                        snapshot_venue=venue_type,
                        bot_folder=bot_folder,
                        snapshot_locations=[location],
                        conclusion="Không đánh giá được vì dữ liệu đầu vào không hợp lệ.",
                        # The exception message is the only diagnostic an
                        # operator has in live mode (which bot, which OKX
                        # endpoint, why) -- never swallow it.
                        error=str(exc),
                    )
                )
                continue
            # One bot is one uniqueCode. Two snapshots taken at different times are
            # the same bot, so the richer one must supersede the older one.
            key = bot.identity.unique_code
            # Evidence decides first; when two snapshots carry the same evidence the
            # newer crawl wins. Without the recency tiebreak the scan order settled
            # it, so an alphabetically earlier folder kept a stale open-position book.
            rank = _provenance_rank(bot)
            entry = distinct.get(key)
            if entry is None:
                distinct[key] = {
                    "bot": bot,
                    "venue_type": venue_type,
                    "locations": [location],
                    "score": rank,
                    "selected": location,
                }
            else:
                entry["locations"].append(location)  # type: ignore[union-attr]
                if rank > entry["score"]:  # type: ignore[operator]
                    entry["bot"] = bot
                    entry["venue_type"] = venue_type
                    entry["score"] = rank
                    entry["selected"] = location

        markets: Dict[str, Tuple[Optional[MarketResult], str]] = {}
        portfolio = [entry["bot"] for entry in distinct.values()]
        rows: List[BotEvaluationRow] = []

        for entry in distinct.values():
            bot: BotResult = entry["bot"]  # type: ignore[assignment]
            locations: List[str] = entry["locations"]  # type: ignore[assignment]
            selected: str = str(entry["selected"])
            traded = bot.identity.symbol
            if traded not in markets:
                markets[traded] = self._resolve_market(traded, now)
            market, resolution = markets[traded]

            assessment = QCCoreService.assess_bot(
                market,
                bot,
                previous_assessment=self.history.latest(bot.identity.bot_id),
                portfolio_bots=portfolio,
            )
            if self.persist_history:
                self.history.append(assessment)
            dimensions = dict(assessment.dimensions)
            available = {
                name: item.score
                for name, item in dimensions.items()
                if item.status == EvidenceStatus.AVAILABLE
            }
            unknown = [
                name
                for name, item in dimensions.items()
                if item.status == EvidenceStatus.UNKNOWN
            ]
            drivers = sorted(available.items(), key=lambda kv: kv[1], reverse=True)
            eligible = market is not None and market.asset_id in eligible_ids
            reason = (
                rejections.get(
                    market.asset_id, "ELIGIBLE" if eligible else "NOT_IN_UNIVERSE"
                )
                if market is not None
                else "NO_MARKET_DATA_FOR_TRADED_SYMBOL"
            )
            rows.append(
                BotEvaluationRow(
                    rank=1,
                    status="EVALUATED",
                    bot_id=bot.identity.bot_id,
                    unique_code=bot.identity.unique_code,
                    nick_name=bot.identity.nick_name,
                    traded_symbol=traded,
                    asset_context=bot.identity.asset_context,
                    venue_type=market.venue_type
                    if market
                    else str(entry["venue_type"]),
                    snapshot_venue=str(entry["venue_type"]),
                    bot_folder=selected.split("/")[-1],
                    duplicate_snapshots=len(locations),
                    selected_snapshot=selected,
                    snapshot_locations=locations,
                    exposure_share=bot.identity.symbol_exposure_share,
                    identity_warnings=bot.identity.identity_warnings,
                    market_available=market is not None,
                    market_resolution=resolution,
                    universe_eligible=eligible,
                    eligibility_reason=reason,
                    market=self._market_row(market) if market else None,
                    position_side=bot.current_state.current_position_side.value,
                    open_positions=bot.current_state.open_positions_count,
                    unknown_positions_count=bot.current_state.unknown_positions_count,
                    instrument_withheld_upstream=bot.current_state.instrument_withheld_upstream,
                    observed_positions_count=bot.current_state.observed_positions_count,
                    inferred_positions_count=bot.current_state.inferred_positions_count,
                    positions_outside_ledger_universe=bot.current_state.positions_outside_ledger_universe,
                    net_exposure=bot.current_state.net_exposure,
                    unrealized_pnl=bot.current_state.unrealized_pnl,
                    open_loss=bot.deferred_loss.open_loss,
                    open_loss_to_capital_pct=bot.deferred_loss.open_loss_to_capital_pct,
                    loss_representativeness=bot.deferred_loss.representativeness,
                    booked_profit_factor=bot.deferred_loss.booked_profit_factor,
                    marked_profit_factor=bot.deferred_loss.marked_profit_factor,
                    never_realized_a_loss=bot.deferred_loss.never_realized_a_loss,
                    simulation_deferred_loss_bias=bot.simulation_results.deferred_loss_bias,
                    capital_consistency=bot.current_state.capital_consistency,
                    open_exposure_by_symbol=bot.current_state.exposure_by_symbol,
                    leverage=bot.current_state.current_leverage,
                    gross_exposure=bot.current_state.gross_exposure,
                    trade_count=bot.performance.trade_count,
                    win_rate=bot.performance.win_rate,
                    profit_factor=bot.performance.profit_factor,
                    expectancy=bot.performance.expectancy,
                    total_pnl=bot.performance.total_pnl,
                    roi_pct=bot.performance.roi_pct,
                    capital_basis=bot.capital.basis,
                    capital_at_risk=bot.capital.capital_at_risk,
                    wiped_out=bot.drawdown_analysis.wiped_out,
                    weekly_equity_max_dd_pct=bot.drawdown_analysis.weekly_equity_max_dd_pct,
                    max_drawdown_abs=bot.performance.max_drawdown_abs,
                    max_drawdown_pct=bot.performance.max_drawdown_pct,
                    current_drawdown_pct=bot.performance.current_drawdown_pct,
                    max_loss_streak=bot.performance.max_loss_streak,
                    directional_bias=bot.strategy_observations.directional_bias,
                    entry_style=bot.strategy_observations.entry_style,
                    phase_coverage_pct=(bot.strategy_observations.phase_coverage_pct),
                    regime_dependence_pct=(
                        bot.strategy_observations.regime_dependence_pct
                    ),
                    best_phase=bot.strategy_observations.best_phase,
                    worst_phase=bot.strategy_observations.worst_phase,
                    losing_phases=list(bot.strategy_observations.losing_phases),
                    untested_phases=list(bot.strategy_observations.untested_phases),
                    tested_in_downtrend=(bot.strategy_observations.tested_in_downtrend),
                    payoff_ratio=bot.performance.payoff_ratio,
                    average_win=bot.performance.average_win,
                    average_loss=bot.performance.average_loss,
                    max_win_streak=bot.performance.max_win_streak,
                    pnl_median=bot.trade_statistics.median_pnl,
                    pnl_skew=bot.trade_statistics.pnl_skew,
                    pnl_kurtosis=bot.trade_statistics.pnl_kurtosis,
                    ledger_coverage_days=bot.reconciliation.ledger_coverage_days,
                    declared_lead_days=bot.reconciliation.declared_lead_days,
                    positions_without_instrument=(
                        bot.current_state.unknown_positions_count
                    ),
                    stress_verdict=bot.stress_results.stress_survival_verdict,
                    quality_components=assessment.quality_components,
                    quality_notes=assessment.quality_notes,
                    var_95_pct=bot.simulation_results.var_95_pct,
                    cvar_95_pct=bot.simulation_results.cvar_95_pct,
                    mar_ratio_median=bot.simulation_results.mar_ratio_median,
                    profit_factor_median=(bot.simulation_results.profit_factor_median),
                    sharpe_ratio=bot.performance.sharpe_ratio,
                    sortino_ratio=bot.performance.sortino_ratio,
                    median_hold_minutes=bot.performance.median_hold_time_minutes,
                    trades_per_day=bot.performance.trade_frequency_per_day,
                    mc_iterations=bot.simulation_results.iterations,
                    mc_horizon=bot.simulation_results.horizon_trades,
                    p_loss_after_horizon=bot.simulation_results.p_loss_after_horizon,
                    worst_drawdown=bot.simulation_results.worst_percentile_drawdown,
                    profit_pct_worst=bot.simulation_results.profit_pct_worst,
                    profit_pct_p05=bot.simulation_results.profit_pct_p05,
                    profit_pct_p50=bot.simulation_results.profit_pct_p50,
                    profit_pct_p95=bot.simulation_results.profit_pct_p95,
                    psr=bot.simulation_results.probabilistic_sharpe,
                    deflated_sharpe=bot.simulation_results.deflated_sharpe,
                    min_track_record_trades=(
                        bot.simulation_results.min_track_record_trades
                    ),
                    selection_trials=bot.simulation_results.selection_trials,
                    inference_reliable=bot.simulation_results.inference_reliable,
                    p_ruin=bot.simulation_results.p_ruin,
                    p_mdd_gt_15=bot.simulation_results.p_mdd_gt_15,
                    p95_max_drawdown=bot.simulation_results.p95_max_drawdown,
                    p_5_loss_streak=bot.simulation_results.p_5_loss_streak,
                    risk_score=assessment.risk_score,
                    quality_score=assessment.quality_score,
                    verdict=assessment.verdict,
                    verdict_reason=assessment.verdict_reason,
                    hidden_risk_flags=assessment.hidden_risk_flags,
                    confidence=assessment.confidence,
                    risk_tier=assessment.risk_tier.value,
                    risk_trend=assessment.risk_trend.value,
                    recommended_action=assessment.recommended_action,
                    measurement_mode=bot.data_quality.measurement_mode.value,
                    reconciliation_status=bot.reconciliation.status,
                    weighted_average=assessment.score_breakdown.weighted_average,
                    veto_floor=assessment.score_breakdown.veto_floor,
                    score_decided_by=assessment.score_breakdown.decided_by,
                    veto_reasons=assessment.score_breakdown.veto_reasons,
                    raised_the_score=assessment.score_breakdown.raised_the_score,
                    held_the_score_down=assessment.score_breakdown.held_the_score_down,
                    dimension_scores=available,
                    top_risk_drivers=[
                        # The raw key reads as a variable name in a report
                        # meant for a person.
                        f"{DIMENSION_LABEL_VI.get(name, name)} {score:.0f}"
                        for name, score in drivers[:3]
                        if score >= 45
                    ],
                    unknown_dimensions=unknown,
                    limitations_count=len(assessment.limitations),
                    conclusion=self._conclusion(market, bot, assessment),
                )
            )

        rows.sort(
            key=lambda row: (
                TIER_ORDER.get(RiskTier(row.risk_tier), 9) if row.risk_tier else 9,
                -(row.risk_score or 0.0),
                row.bot_id,
            )
        )
        ordered = [
            row.model_copy(update={"rank": index}) for index, row in enumerate(rows, 1)
        ]
        ordered.extend(
            row.model_copy(update={"rank": len(ordered) + offset})
            for offset, row in enumerate(failures, 1)
        )

        tier_summary: Dict[str, int] = {}
        for row in ordered:
            key_name = row.risk_tier or "NOT_EVALUATED"
            tier_summary[key_name] = tier_summary.get(key_name, 0) + 1

        warnings: List[str] = []
        duplicated = [row for row in ordered if row.duplicate_snapshots > 1]
        if duplicated:
            warnings.append(
                f"{len(duplicated)}/{len(rows)} bot bị nhân bản trong dataset "
                f"(tổng {sum(row.duplicate_snapshots for row in duplicated)} thư mục snapshot trùng nội dung)."
            )
        mismatched = [row for row in ordered if row.identity_warnings]
        if mismatched:
            warnings.append(
                f"{len(mismatched)} bot có asset_context không khớp instrument thực giao dịch; "
                "thị trường được lấy theo sổ lệnh, không theo tên thư mục."
            )
        no_market = [
            row
            for row in ordered
            if row.status == "EVALUATED" and not row.market_available
        ]
        if no_market:
            warnings.append(
                "Thiếu dữ liệu thị trường cho: "
                + ", ".join(sorted({row.traded_symbol for row in no_market}))
            )
        if failures:
            warnings.append(f"{len(failures)} snapshot không đánh giá được.")

        return CohortReport(
            generated_at_ms=now,
            evaluation_mode=self.evaluation_mode,
            snapshots_scanned=len(targets),
            distinct_bots=len(rows),
            bots_failed=len(failures),
            markets_resolved=sum(
                1 for market, _ in markets.values() if market is not None
            ),
            tier_summary=tier_summary,
            rows=ordered,
            gaps=build_gaps(ordered, {sym: mk for sym, (mk, _) in markets.items()}),
            warnings=warnings,
        )
