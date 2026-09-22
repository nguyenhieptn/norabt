from __future__ import annotations

import time
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from Agent.backend.infra.quality import SourceQuality
from Agent.backend.bot.mcp.capital.equity_curve import CapitalModel


class RiskMeasurementMode(str, Enum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    LIMITED = "LIMITED"


class PositionSide(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NET = "NET"
    FLAT = "FLAT"
    UNKNOWN = "UNKNOWN"


class BotIdentity(BaseModel):
    """Who the bot is, and which market it is actually trading.

    `asset_context` is where the snapshot was filed; `primary_traded_symbol` is
    derived from the ledger. They can disagree, and QC must not silently pair a
    bot with a market it never traded.
    """

    bot_id: str
    unique_code: str
    nick_name: str
    account: Optional[str] = None
    symbol: str
    asset_context: str
    primary_traded_symbol: Optional[str] = None
    venue: str = "OKX"
    declared_strategy: Optional[str] = None
    observed_symbols: List[str] = Field(default_factory=list)
    symbol_exposure_share: Dict[str, float] = Field(default_factory=dict)
    identity_warnings: List[str] = Field(default_factory=list)
    ledger_fingerprint: Optional[str] = None


class OpenPosition(BaseModel):
    """One open position. Instrument attribution can be missing while size is known."""

    position_id: str
    instrument: Optional[str] = None
    symbol: Optional[str] = None
    attribution_source: str = "NONE"
    attribution_verdict: Optional[str] = None
    attribution_candidates: List[str] = Field(default_factory=list)
    implied_price_move: Optional[float] = None
    open_time: Optional[int] = Field(default=None, ge=0)
    open_time_source: Optional[str] = None
    side: PositionSide = PositionSide.UNKNOWN
    leverage: Optional[float] = Field(default=None, ge=0.0)
    margin: Optional[float] = Field(default=None, ge=0.0)
    contract_size: Optional[float] = Field(default=None, ge=0.0)
    notional: Optional[float] = Field(default=None, ge=0.0)
    entry_price: Optional[float] = Field(default=None, gt=0.0)
    mark_price: Optional[float] = Field(default=None, gt=0.0)
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None


class BotCurrentState(BaseModel):
    current_equity: Optional[float] = Field(default=None, gt=0.0)
    reference_capital: Optional[float] = Field(default=None, gt=0.0)
    reference_capital_source: Optional[str] = None
    available_balance: Optional[float] = Field(default=None, ge=0.0)
    used_margin: Optional[float] = Field(default=None, ge=0.0)
    margin_ratio: Optional[float] = Field(default=None, ge=0.0)
    margin_to_reference_pct: Optional[float] = Field(default=None, ge=0.0)
    capital_consistency: str = "UNKNOWN"
    current_position_side: PositionSide = PositionSide.UNKNOWN
    current_position_size: Optional[float] = Field(default=None, ge=0.0)
    current_notional: Optional[float] = Field(default=None, ge=0.0)
    gross_exposure: Optional[float] = Field(default=None, ge=0.0)
    net_exposure: Optional[float] = None
    current_leverage: Optional[float] = Field(default=None, ge=0.0)
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None
    liquidation_price: Optional[float] = Field(default=None, gt=0.0)
    liquidation_distance_pct: Optional[float] = Field(default=None, ge=0.0)
    long_notional: Optional[float] = Field(default=None, ge=0.0)
    short_notional: Optional[float] = Field(default=None, ge=0.0)
    open_positions_count: int = Field(default=0, ge=0)
    attributed_positions_count: int = Field(default=0, ge=0)
    observed_positions_count: int = Field(default=0, ge=0)
    inferred_positions_count: int = Field(default=0, ge=0)
    positions_outside_ledger_universe: int = Field(default=0, ge=0)
    unknown_positions_count: int = Field(default=0, ge=0)
    instrument_withheld_upstream: bool = False
    open_position_symbols: List[str] = Field(default_factory=list)
    exposure_by_symbol: Dict[str, float] = Field(default_factory=dict)
    open_positions: List[OpenPosition] = Field(default_factory=list)


class BotPerformanceMetrics(BaseModel):
    trade_count: int = Field(..., ge=0)
    win_rate: float = Field(..., ge=0.0, le=100.0)
    loss_rate: float = Field(..., ge=0.0, le=100.0)
    total_pnl: float
    roi_pct: Optional[float] = None
    profit_factor: Optional[float] = Field(default=None, ge=0.0)
    expectancy: Optional[float] = None
    payoff_ratio: Optional[float] = Field(default=None, ge=0.0)
    average_win: Optional[float] = None
    average_loss: Optional[float] = None
    max_drawdown_abs: Optional[float] = Field(default=None, ge=0.0)
    current_drawdown_abs: Optional[float] = Field(default=None, ge=0.0)
    max_drawdown_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    current_drawdown_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    floating_drawdown_pct: Optional[float] = Field(default=None, ge=0.0)
    max_floating_drawdown_pct: Optional[float] = Field(default=None, ge=0.0)
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    recovery_factor: Optional[float] = None
    current_streak: int = 0
    max_win_streak: int = Field(default=0, ge=0)
    max_loss_streak: int = Field(default=0, ge=0)
    average_hold_time_minutes: Optional[float] = Field(default=None, ge=0.0)
    median_hold_time_minutes: Optional[float] = Field(default=None, ge=0.0)
    trade_frequency_per_day: Optional[float] = Field(default=None, ge=0.0)


class DeferredLossProfile(BaseModel):
    """What the closed-trade metrics would look like if the open losses were booked.

    A bot that closes winners and holds losers shows a pristine win rate, profit
    factor and drawdown while the real loss sits open. Rather than argue about a
    ratio threshold, this marks the open book to market and recomputes the same
    metrics, so the distortion is arithmetic rather than a judgement call.
    """

    realized_pnl: float
    unrealized_pnl: Optional[float] = None
    open_loss: Optional[float] = Field(default=None, ge=0.0)
    gross_realized_profit: float = 0.0
    gross_realized_loss: float = Field(default=0.0, ge=0.0)
    # Net PnL vanishes when wins and losses cancel, so the stable denominator is
    # the gross loss the bot has actually booked.
    open_loss_to_realized_loss: Optional[float] = Field(default=None, ge=0.0)
    open_loss_to_capital_pct: Optional[float] = Field(default=None, ge=0.0)

    booked_profit_factor: Optional[float] = Field(default=None, ge=0.0)
    marked_profit_factor: Optional[float] = Field(default=None, ge=0.0)
    booked_win_rate: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    marked_win_rate: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    marked_total_pnl: Optional[float] = None
    mark_coverage: float = Field(default=0.0, ge=0.0, le=1.0)

    closed_loss_count: int = Field(default=0, ge=0)
    losing_open_positions: int = Field(default=0, ge=0)
    never_realized_a_loss: bool = False
    representativeness: str = "UNKNOWN"
    warnings: List[str] = Field(default_factory=list)

    @property
    def distorts_headline_metrics(self) -> bool:
        return self.representativeness in ("PARTIAL", "UNREPRESENTATIVE")

    @property
    def has_realized_metrics(self) -> bool:
        return self.representativeness != "NO_CLOSED_TRADES"

    @property
    def turns_unprofitable_when_marked(self) -> bool:
        return (
            self.marked_profit_factor is not None
            and self.marked_profit_factor < 1.0
            and (self.booked_profit_factor is None or self.booked_profit_factor >= 1.0)
        )


class TradeLedgerItem(BaseModel):
    trade_id: str
    symbol: str
    side: PositionSide
    open_time: int = Field(..., ge=0)
    close_time: int = Field(..., ge=0)
    entry_price: Optional[float] = Field(default=None, gt=0.0)
    exit_price: Optional[float] = Field(default=None, gt=0.0)
    quantity: Optional[float] = Field(default=None, ge=0.0)
    margin: Optional[float] = Field(default=None, ge=0.0)
    notional: Optional[float] = Field(default=None, ge=0.0)
    realized_pnl: float
    realized_pnl_pct: Optional[float] = None
    return_basis: str = "ABSOLUTE_PNL"
    # Phase thị trường tại thời điểm MỞ lệnh (`MarketPhase`, xem
    # `analytics/strategy/phases.py`). `None` khi bản ghi được dựng trước khi
    # trường này tồn tại; `"UNKNOWN"` khi có timeline nhưng giờ mở lệnh nằm
    # ngoài phạm vi nến -- hai trạng thái KHÁC nhau và không được gộp.
    # Trước đây nhãn này được tính cho từng lệnh rồi vứt đi ngay sau khi gom
    # nhóm (`StrategyPhaseAnalyzer.analyze`), buộc mọi phân tích theo regime về
    # sau phải tái dựng lại từ dòng tổng hợp.
    market_phase: Optional[str] = None
    initial_risk: Optional[float] = Field(default=None, gt=0.0)
    r_multiple: Optional[float] = None
    fee: Optional[float] = None
    funding: Optional[float] = None
    holding_time_minutes: float = Field(..., ge=0.0)
    mfe_pct: Optional[float] = None
    mae_pct: Optional[float] = None
    leverage: Optional[float] = Field(default=None, ge=0.0)
    stop_loss: Optional[float] = Field(default=None, gt=0.0)
    take_profit: Optional[float] = Field(default=None, gt=0.0)

    @field_validator("close_time")
    @classmethod
    def close_after_open(cls, value: int, info):
        open_time = info.data.get("open_time")
        if open_time is not None and value < open_time:
            raise ValueError("close_time must be >= open_time")
        return value


class TradeStatistics(BaseModel):
    sample_size: int = Field(..., ge=0)
    measurement_mode: RiskMeasurementMode
    return_basis: str
    mean_pnl: Optional[float] = None
    median_pnl: Optional[float] = None
    pnl_std: Optional[float] = Field(default=None, ge=0.0)
    pnl_skew: Optional[float] = None
    pnl_kurtosis: Optional[float] = None
    p05_pnl: Optional[float] = None
    p95_pnl: Optional[float] = None
    mean_return_pct: Optional[float] = None
    median_return_pct: Optional[float] = None
    mean_r_multiple: Optional[float] = None
    confidence_interval_mean_pnl: Optional[List[float]] = None


class BehavioralObservations(BaseModel):
    averaging_down_detected: bool = False
    averaging_down_suspected: bool = False
    martingale_escalation_detected: bool = False
    overtrading_score: float = Field(default=0.0, ge=0.0, le=1.0)
    loss_chasing_score: float = Field(default=0.0, ge=0.0, le=1.0)
    reentry_loop_detected: bool = False
    holding_time_explosion_score: float = Field(default=0.0, ge=0.0, le=1.0)
    leverage_escalation_detected: bool = False
    size_escalation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    # Phần VƯỢT TRỘI của việc nâng cỡ lệnh sau lệnh LỖ so với sau lệnh THẮNG,
    # tức `size_escalation_score` đã trừ đi nhóm đối chứng. Một bot chỉ đơn
    # giản hay thay đổi cỡ lệnh sẽ có hai tỉ lệ xấp xỉ nhau và đại lượng này
    # về 0; chỉ bot nâng cỡ RIÊNG sau lệnh lỗ mới đẩy nó lên. Đây là đại
    # lượng LIÊN TỤC mà lens chấm điểm dùng, thay cho việc rẽ nhánh theo tên
    # chiến lược (DCA/lưới/martingale) -- tên chiến lược là nhãn mô tả, không
    # phải thứ đo được.
    size_escalation_excess: float = Field(default=0.0, ge=0.0, le=1.0)
    behavioral_risk_tier: str = "UNKNOWN"
    evidence: List[str] = Field(default_factory=list)


class PhasePerformance(BaseModel):
    """What the bot did during one kind of market, on its own."""

    phase: str
    trades: int = Field(..., ge=0)
    win_rate: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    total_pnl: float
    expectancy: Optional[float] = None
    long_share_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    average_leverage: Optional[float] = Field(default=None, ge=0.0)
    median_hold_minutes: Optional[float] = Field(default=None, ge=0.0)
    profit_share_pct: Optional[float] = None


class StrategyObservations(BaseModel):
    observed_profile: str
    declared_strategy: Optional[str] = None
    strategy_drift_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    drift_details: List[str] = Field(default_factory=list)

    # How the book is taken: one-way books carry directional risk a win rate hides.
    directional_bias: str = "UNKNOWN"
    long_share_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    entry_style: str = "UNKNOWN"
    entry_style_evidence: Optional[str] = None

    # Where the record was actually earned. A phase never traded is untested, not
    # safe, and profit concentrated in one phase is one regime change from gone.
    phase_coverage_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    trades_without_phase: int = Field(default=0, ge=0)
    phase_breakdown: List[PhasePerformance] = Field(default_factory=list)
    best_phase: Optional[str] = None
    worst_phase: Optional[str] = None
    regime_dependence_pct: Optional[float] = None
    losing_phases: List[str] = Field(default_factory=list)
    untested_phases: List[str] = Field(default_factory=list)
    tested_in_downtrend: bool = False
    tested_in_trend: bool = False


class DrawdownAnalysis(BaseModel):
    capital_basis: str = "UNAVAILABLE"
    weekly_equity_max_dd_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    wiped_out: bool = False
    current_dd_abs: Optional[float] = Field(default=None, ge=0.0)
    max_dd_abs: Optional[float] = Field(default=None, ge=0.0)
    current_dd_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    max_dd_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    # True when a drawdown came out larger than the equity in force at the time,
    # so the percentage is a floor the cap produced, not a measurement. Reporting
    # a bare 100 % reads as a wipeout, which is a different claim entirely.
    max_dd_pct_capped: bool = False
    capped_trade_count: int = Field(default=0, ge=0)
    floating_dd_pct: Optional[float] = Field(default=None, ge=0.0)
    max_floating_dd_pct: Optional[float] = Field(default=None, ge=0.0)
    time_underwater_hours: Optional[float] = Field(default=None, ge=0.0)
    recovery_time_hours: Optional[float] = Field(default=None, ge=0.0)
    loss_clustering_index: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class HorizonOutcome(BaseModel):
    """One Monte-Carlo horizon's outcome, alongside the others in the same run.

    A single horizon answers "what if this bot's future looks like N more of
    its own trades" for exactly one N. That is a legitimate question, but it
    is not the only one worth asking: a scalper judged over 500 trades and
    the same scalper judged over the 20-50 trades it actually holds a position
    for can come back with opposite conclusions, and neither number is wrong
    -- they are answers to different questions. `SimulationResults` keeps its
    single-horizon fields (nothing here replaces them); this is the list that
    lets several of those questions be answered side by side instead of
    forcing the caller to pick one and lose the others.
    """

    label: str  # "SHORT" | "MEDIUM" | "LONG"
    horizon_trades: int = Field(..., ge=1)
    iterations: int = Field(..., ge=0)
    is_valid: bool
    profit_pct_p05: Optional[float] = None
    profit_pct_p50: Optional[float] = None
    profit_pct_p95: Optional[float] = None
    median_max_drawdown: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_loss_after_horizon: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_ruin: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    mar_ratio_median: Optional[float] = None
    # Derived as 100 - p_loss_after_horizon; kept as its own field so a reader
    # (or the classifier below) never has to re-derive it and risk a sign slip.
    probability_of_profit: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    warnings: List[str] = Field(default_factory=list)


class TerminalOutcomeHistogram(BaseModel):
    """Chart type A: binned terminal-outcome distribution (a real histogram,
    not an approximation from percentile points). `len(counts) ==
    len(bin_edges_pct) - 1`, standard `numpy.histogram` convention -- bin i
    spans `[bin_edges_pct[i], bin_edges_pct[i+1])`.
    """

    bin_edges_pct: List[float]
    counts: List[int] = Field(default_factory=list)


class HorizonCheckpoint(BaseModel):
    """Chart types B/C: equity percentiles at one trade count along the
    horizon -- `SimulationResults.horizon_checkpoints` is several of these,
    ascending by `trade_count`, sampled from the SAME simulated paths
    `horizon_scenarios`'s single MEDIUM-horizon entry summarizes only the
    endpoint of. A UI can render this list as a fan/area chart (p05-p95 band
    plus the p50 line) or as a plain line chart (p50 only) -- same data,
    different view, per the product owner's own chart-type-switcher request.
    """

    trade_count: int = Field(..., ge=1)
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float


class SimulationResults(BaseModel):
    simulation_method: str
    iterations: int = Field(..., ge=0)
    sample_size: int = Field(..., ge=0)
    # `True` khi mô phỏng CÓ chạy nhưng cỡ mẫu nằm dưới
    # `MonteCarloSimulationEngine.THIN_SAMPLE_SIZE` -- kết quả hợp lệ nhưng
    # sai số chuẩn ở hai đuôi rất lớn, tầng trình bày BẮT BUỘC kèm lưu ý
    # (xem hằng số đó và `THIN_SAMPLE_WARNING_VI`). Mặc định `False` nên mọi
    # nơi dựng `SimulationResults` từ trước không phải đổi gì.
    sample_is_thin: bool = False
    horizon_trades: int = Field(..., ge=0)
    return_basis: str
    capital_basis: str = "CURRENT_AUM"
    deferred_loss_bias: bool = False
    capital_at_risk: Optional[float] = Field(default=None, gt=0.0)
    is_valid: bool
    p_ruin: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_mdd_gt_10: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_mdd_gt_15: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_mdd_gt_25: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_loss_after_horizon: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_loss_after_500_trades: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_recovery_gt_30d: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_5_loss_streak: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_10_loss_streak: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    # Baseline: the probability an *independent* Bernoulli sequence with this
    # bot's own per-trade loss rate would show the same streak, purely from
    # playing `horizon_trades` hands -- streaks become near-certain over a long
    # enough run even with no real dependence between losses. Excess is what is
    # left after subtracting that baseline, which is the part that actually
    # reflects clustering/herding in this bot's own trades. Both are None for
    # assessments produced before this field existed (old stored data), which
    # is the signal downstream scoring uses to fall back to the raw number.
    p_5_loss_streak_baseline: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_10_loss_streak_baseline: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_5_loss_streak_excess: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_10_loss_streak_excess: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_capital_loss_gt_current_dd: Optional[float] = Field(
        default=None, ge=0.0, le=100.0
    )
    expected_terminal_equity: Optional[float] = None
    median_terminal_equity: Optional[float] = None
    p10_outcome: Optional[float] = None
    p50_outcome: Optional[float] = None
    p90_outcome: Optional[float] = None
    # Profit distribution across the runs, in percent of the capital at risk.
    # The worst case is the point of running 10k of these, so it is a field of
    # its own rather than something a reader has to infer from a percentile.
    profit_pct_worst: Optional[float] = None
    profit_pct_p05: Optional[float] = None
    profit_pct_p10: Optional[float] = None
    profit_pct_p25: Optional[float] = None
    profit_pct_p50: Optional[float] = None
    profit_pct_p75: Optional[float] = None
    profit_pct_p90: Optional[float] = None
    profit_pct_p95: Optional[float] = None
    profit_pct_best: Optional[float] = None
    worst_terminal_equity: Optional[float] = None

    # Loss-tail measures the percentile list alone does not give. VaR is the
    # threshold the worst 5 % of runs breach; CVaR (expected shortfall) is the
    # average loss once you are inside that tail, which is what actually hits
    # the account. Basel and the risk literature report both, never VaR alone.
    var_95_pct: Optional[float] = None
    var_99_pct: Optional[float] = None
    cvar_95_pct: Optional[float] = None
    cvar_99_pct: Optional[float] = None
    # Drawdown distribution, not just its tail.
    median_max_drawdown: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p90_max_drawdown: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    # Return earned per unit of drawdown suffered, across the runs.
    mar_ratio_median: Optional[float] = None
    mar_ratio_p05: Optional[float] = None
    # Profit factor is path independent, so its spread here comes purely from
    # which trades were drawn -- a wide spread means the headline PF is fragile.
    profit_factor_median: Optional[float] = None
    profit_factor_p05: Optional[float] = None
    probability_of_profit: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    horizon_basis: str = "OWN_TRADE_COUNT"

    # Bailey & López de Prado inference: is the edge real once sample length,
    # skew and fat tails are accounted for, and once the fact that this bot was
    # picked as the best of its pool is accounted for.
    sharpe_per_trade: Optional[float] = None
    probabilistic_sharpe: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    min_track_record_trades: Optional[float] = Field(default=None, ge=0.0)
    deflated_sharpe: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    selection_trials: Optional[int] = Field(default=None, ge=0)
    inference_reliable: bool = True
    inference_notes: List[str] = Field(default_factory=list)
    p95_max_drawdown: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p99_max_drawdown: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    worst_percentile_drawdown: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    warnings: List[str] = Field(default_factory=list)

    # Multi-horizon view, additive to everything above. The fields above this
    # point still describe exactly one horizon (MEDIUM: the bot's own trade
    # count, same as before this was added) so none of the 600+ existing
    # readers of this model have to change. `horizon_scenarios` is where the
    # SHORT/MEDIUM/LONG comparison actually lives.
    horizon_scenarios: List[HorizonOutcome] = Field(default_factory=list)
    # Chart-ready data for the 3-view chart-type switcher (histogram / fan
    # chart / line chart of the same Monte Carlo run) -- see
    # `TerminalOutcomeHistogram`/`HorizonCheckpoint`'s own docstrings.
    # Optional/default-empty so an assessment.json written before this field
    # existed still validates (degrades to "no chart data", never a fake one).
    terminal_outcome_histogram: Optional[TerminalOutcomeHistogram] = None
    horizon_checkpoints: List[HorizonCheckpoint] = Field(default_factory=list)
    # How much the outcome swings between the shortest and longest horizon
    # simulated, normalized to [0, 1] (0 = same probability of profit at
    # every horizon, 1 = flips from certain profit to certain loss). This is
    # a description of how horizon-dependent the record is, not a verdict.
    horizon_sensitivity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    # Vietnamese on purpose: this is a user-facing label, not an internal enum.
    # One of "ỔN ĐỊNH MỌI HORIZON", "CHỈ ỔN Ở NGẮN HẠN", "CẦN THỜI GIAN", or
    # None when too few horizons produced a usable result to compare.
    horizon_stability_label: Optional[str] = None

    # How many calendar days `horizon_trades` (a trade count) actually spans
    # for this specific bot, and whether the data on hand covers that span.
    # "500 trades" alone is unreadable -- it is a few days for a scalper and
    # years for a swing trader -- and a reader cannot tell when a conclusion
    # is an extrapolation without knowing both numbers. None whenever the
    # ledger's own timestamps cannot support the estimate (fewer than two
    # trades, or no observed elapsed time); never guessed.
    trades_per_day: Optional[float] = Field(default=None, ge=0.0)
    horizon_calendar_days: Optional[float] = Field(default=None, ge=0.0)
    observed_span_days: Optional[float] = Field(default=None, ge=0.0)
    horizon_exceeds_observed: Optional[bool] = None


class StressTestResults(BaseModel):
    volatility_2x_pnl_impact: Optional[float] = None
    spread_3x_slippage_impact: Optional[float] = None
    liquidity_half_exit_impact: Optional[float] = None
    stress_survival_verdict: str
    is_valid: bool = True
    warnings: List[str] = Field(default_factory=list)


class LedgerReconciliation(BaseModel):
    """Why ledger PnL and reported PnL differ, told apart by cause.

    A truncated ledger, a ledger belonging to another bot, and genuinely
    contradictory numbers are three different problems and must not share
    one MISMATCH label.
    """

    status: str
    reported_pnl: Optional[float] = None
    reported_pnl_provenance: str = "UNKNOWN"
    ledger_pnl: float
    difference: Optional[float] = None
    difference_pct: Optional[float] = None
    tolerance_pct: float = Field(default=1.0, ge=0.0)
    ledger_truncated: bool = False
    ledger_coverage_days: Optional[float] = Field(default=None, ge=0.0)
    declared_lead_days: Optional[int] = Field(default=None, ge=0)
    foreign_owner_codes: List[str] = Field(default_factory=list)
    rejected_foreign_rows: int = Field(default=0, ge=0)
    warnings: List[str] = Field(default_factory=list)


class DataQualityAssessment(BaseModel):
    completeness_score: float = Field(..., ge=0.0, le=1.0)
    freshness_score: float = Field(..., ge=0.0, le=1.0)
    overall_score: float = Field(..., ge=0.0, le=1.0)
    freshness_ms: int = Field(..., ge=0)
    coverage_days: Optional[float] = Field(default=None, ge=0.0)
    capital_reference_source: Optional[str] = None
    capital_basis: str = "UNAVAILABLE"
    measurement_mode: RiskMeasurementMode
    valid_trade_count: int = Field(default=0, ge=0)
    rejected_trade_count: int = Field(default=0, ge=0)
    sources: List[SourceQuality] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ExitStyle(str, Enum):
    """How a bot decides a trade is over. One label, from the ledger alone."""

    UNKNOWN = "UNKNOWN"
    FIXED_TARGET = "FIXED_TARGET"
    PROTECTIVE_STOP = "PROTECTIVE_STOP"
    RUN_WINNERS_CUT_LOSSES = "RUN_WINNERS_CUT_LOSSES"
    HOLD_LOSERS = "HOLD_LOSERS"
    TIME_EXIT = "TIME_EXIT"
    DISCRETIONARY = "DISCRETIONARY"


class ExitRuleFingerprint(BaseModel):
    """The bot's exit discipline, reconstructed from closed trades alone.

    WHY THIS IS MEASURED IN PRICE, NOT PnL. Every figure below is the
    direction-adjusted PRICE move between entry and exit
    (`(exit - entry) / entry`, negated for shorts), deliberately excluding
    leverage, size and fees. The question here is *when the bot decided to get
    out*, and PnL conflates that decision with how big the position was: two
    bots running the identical exit rule at 5x and 50x look like different
    strategies in PnL terms and identical ones here, which is the correct
    answer for a style comparison.

    WHY IT BELONGS TO LOGIC 2. It is a property of the trade ledger, derived
    with no market data, no QC verdict and no other bot in scope -- the same
    standing as `behavioral_observations`. That also means it is available on
    every bot, including one trading instruments no candles exist for.

    WHAT IT CANNOT SEE. Orders that were cancelled, positions still open, and
    anything hedged off-venue leave no trace in a closed-trade ledger, so this
    describes exits that HAPPENED, never the rule that was configured.
    """

    sample_size: int = Field(default=0, ge=0)
    priced_trades: int = Field(default=0, ge=0)
    # Share of closed trades carrying both an entry and an exit price. Every
    # figure below rests on this subset, so a reader can see how much of the
    # ledger the fingerprint actually speaks for.
    price_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    win_count: int = Field(default=0, ge=0)
    loss_count: int = Field(default=0, ge=0)

    # --- tails, in percent of entry price -------------------------------
    win_move_median: Optional[float] = None
    win_move_p90: Optional[float] = None
    win_move_max: Optional[float] = None
    loss_move_median: Optional[float] = None
    loss_move_p10: Optional[float] = None
    loss_move_worst: Optional[float] = None
    # |median loss| / median win. Above 1.0 the bot books losses larger than
    # its wins, which a win rate alone will never reveal.
    loss_to_win_ratio: Optional[float] = Field(default=None, ge=0.0)
    # Coefficient of variation within each side: low means the exits land in
    # the same place every time, high means they are decided case by case.
    win_dispersion: Optional[float] = Field(default=None, ge=0.0)
    loss_dispersion: Optional[float] = Field(default=None, ge=0.0)
    # p90/median for wins, p10/median for losses: how far the tail runs past
    # the typical exit. A hard target pins both near 1.
    win_tail_ratio: Optional[float] = Field(default=None, ge=0.0)
    loss_tail_ratio: Optional[float] = Field(default=None, ge=0.0)

    # --- hard take-profit / stop-loss detection --------------------------
    # Share of exits landing within +-15% of that side's median move. A rule
    # firing at a fixed level concentrates them; a judgement call does not.
    take_profit_clustering: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    stop_loss_clustering: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    has_hard_take_profit: bool = False
    has_hard_stop_loss: bool = False
    # Only populated when the corresponding clustering clears the threshold.
    # Reporting a "level" for scattered exits would be inventing one.
    take_profit_level_pct: Optional[float] = None
    stop_loss_level_pct: Optional[float] = None

    # --- holding behaviour ----------------------------------------------
    hold_median_minutes: Optional[float] = Field(default=None, ge=0.0)
    win_hold_median_minutes: Optional[float] = Field(default=None, ge=0.0)
    loss_hold_median_minutes: Optional[float] = Field(default=None, ge=0.0)
    # loss hold / win hold. Above 1 means losers are held longer than winners
    # -- cutting winners and sitting on losers, the single most common way a
    # healthy-looking win rate hides an unhealthy book.
    hold_asymmetry: Optional[float] = Field(default=None, ge=0.0)
    # Ordered histogram over fixed duration bands (see HOLD_BUCKET_LABELS).
    hold_buckets: Dict[str, int] = Field(default_factory=dict)
    hold_shape: List[float] = Field(default_factory=list)
    # More than one duration band standing out: the bot is running two
    # different behaviours under one name (e.g. scalps plus bag-holding).
    is_multi_modal: bool = False
    hold_modes: List[str] = Field(default_factory=list)

    # --- verdict ---------------------------------------------------------
    exit_style: ExitStyle = ExitStyle.UNKNOWN
    # Everything detected, not just the label that won the priority order.
    patterns: List[str] = Field(default_factory=list)
    # Fixed-order, dimensionless components used to compare two bots. Never
    # read positionally by name elsewhere -- see `ExitRuleAnalyzer.compare`.
    rule_vector: List[float] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    is_valid: bool = False
    warnings: List[str] = Field(default_factory=list)


class BotResult(BaseModel):
    """LOGIC 2 output: bot observations and simulations, never a QC verdict."""

    schema_version: str = "bot_result.v1"
    methodology_version: str = "bot_analytics.v1"
    identity: BotIdentity
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), ge=0)
    as_of_ms: int = Field(default_factory=lambda: int(time.time() * 1000), ge=0)
    current_state: BotCurrentState
    performance: BotPerformanceMetrics
    deferred_loss: DeferredLossProfile
    trade_statistics: TradeStatistics
    trade_ledger_summary: List[TradeLedgerItem] = Field(default_factory=list)
    behavioral_observations: BehavioralObservations
    strategy_observations: StrategyObservations
    drawdown_analysis: DrawdownAnalysis
    simulation_results: SimulationResults
    stress_results: Optional[StressTestResults] = None
    # Exit discipline reconstructed from the ledger (Logic 2, no market
    # data involved). Optional so every BotResult serialised before this
    # field existed still validates; always populated on a fresh run.
    exit_rule: Optional[ExitRuleFingerprint] = None
    reconciliation: LedgerReconciliation
    capital: CapitalModel
    data_quality: DataQualityAssessment
