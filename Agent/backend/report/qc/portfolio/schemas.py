from __future__ import annotations

import time
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PortfolioVerdict(str, Enum):
    """What the combination of these bots actually is, as a bucket a reader acts on.

    Deliberately NOT a risk tier: `RiskTier` already answers "how much can this
    hurt" for one bot, and the portfolio layer answers a different question --
    whether putting these particular bots together bought any diversification.
    A portfolio of three individually HEALTHY bots that all move as one is a
    real finding, and it has no expression in the per-bot tier scale.
    """

    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    DIVERSIFIED = "DIVERSIFIED"
    MODERATE_CO_MOVEMENT = "MODERATE_CO_MOVEMENT"
    HIGH_CORRELATION_CLUSTER = "HIGH_CORRELATION_CLUSTER"


class PairRelationship(str, Enum):
    UNKNOWN = "UNKNOWN"
    INVERSE = "INVERSE"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"


class PortfolioMember(BaseModel):
    """One bot as it enters the portfolio, with only what the portfolio layer needs.

    A member carries no lens scores of its own beyond the headline risk/quality
    numbers: anything deeper belongs to that bot's own `BotRiskAssessment`,
    which the caller already has and must not see duplicated (and drifting)
    here.
    """

    bot_id: str
    unique_code: str
    nick_name: str
    symbol: str
    venue: str = "OKX"
    label: str

    risk_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    risk_tier: Optional[str] = None
    verdict: Optional[str] = None

    closed_trade_count: int = Field(default=0, ge=0)
    realized_pnl: float = 0.0
    capital_at_risk: Optional[float] = Field(default=None, gt=0.0)
    # Share of the portfolio's total capital at risk, 0-1. `None` when at
    # least one member has no resolvable capital: an equal-weight guess would
    # silently change every capital-weighted number downstream, so the whole
    # weighting is withheld instead (see `PortfolioQCService`).
    capital_weight: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    current_notional: Optional[float] = Field(default=None, ge=0.0)
    position_side: str = "UNKNOWN"
    observed_symbols: List[str] = Field(default_factory=list)
    symbol_exposure_share: Dict[str, float] = Field(default_factory=dict)

    first_close_ms: Optional[int] = Field(default=None, ge=0)
    last_close_ms: Optional[int] = Field(default=None, ge=0)
    # Set when this member could not enter the correlation math at all (too
    # few closed trades, no overlap with the others). It still appears in the
    # member list -- a bot silently vanishing from its own portfolio report is
    # worse than one shown with the reason it was left out.
    excluded_reason: Optional[str] = None

    @property
    def is_measurable(self) -> bool:
        return self.excluded_reason is None


class AlignmentDiagnostics(BaseModel):
    """How the per-bot trade ledgers were put on one shared clock.

    Every correlation number below is a function of these choices, so they are
    reported rather than buried: a reader who disagrees with the bucket size or
    the overlap window can see exactly what was used.
    """

    bucket_label: str
    bucket_ms: int = Field(..., ge=1)
    bucket_reason: str = ""

    overlap_start_ms: Optional[int] = Field(default=None, ge=0)
    overlap_end_ms: Optional[int] = Field(default=None, ge=0)
    overlap_days: Optional[float] = Field(default=None, ge=0.0)

    # Buckets spanning the overlap window, before and after dropping the ones
    # in which NO member traded at all. An all-idle bucket carries no
    # information about co-movement but does inflate the sample size, which
    # would make a correlation look better resolved than it is.
    span_buckets: int = Field(default=0, ge=0)
    evaluated_buckets: int = Field(default=0, ge=0)
    dropped_idle_buckets: int = Field(default=0, ge=0)

    # Per member: in how many of the evaluated buckets that bot actually
    # closed a trade. A member active in 3 of 180 buckets is mostly
    # contributing zeros, and its correlations must be read as such.
    active_buckets: Dict[str, int] = Field(default_factory=dict)
    active_share: Dict[str, float] = Field(default_factory=dict)

    included_labels: List[str] = Field(default_factory=list)
    excluded: Dict[str, str] = Field(default_factory=dict)
    is_valid: bool = False
    warnings: List[str] = Field(default_factory=list)


class PairCorrelation(BaseModel):
    """One pair of bots, measured rather than asserted."""

    label_a: str
    label_b: str
    code_a: str
    code_b: str

    pearson: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    spearman: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    observations: int = Field(default=0, ge=0)
    # Buckets in which BOTH bots closed a trade. Pearson over a series padded
    # with joint zeros can be driven almost entirely by the two bots being
    # idle at the same times, which is not the same claim as "they lose money
    # together"; this is the number that tells the two apart.
    co_active_buckets: int = Field(default=0, ge=0)
    # Two-sided p-value from Fisher's z transform. Not a gate -- reported so a
    # correlation measured over 14 buckets is not read like one over 400.
    p_value: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    is_significant: bool = False

    shared_symbols: List[str] = Field(default_factory=list)
    # Cosine similarity of the two bots' exposure-share vectors, 0-1. Answers
    # "do they hold the same things", which is independent of, and often
    # disagrees with, "do their PnLs move together".
    exposure_overlap: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    relationship: PairRelationship = PairRelationship.UNKNOWN
    note: str = ""


class CorrelationMatrix(BaseModel):
    labels: List[str] = Field(default_factory=list)
    codes: List[str] = Field(default_factory=list)
    # Row-major N x N, `None` wherever a coefficient is undefined (a member
    # whose PnL never varies across the window has no correlation with
    # anything -- that is missing, not zero).
    pearson: List[List[Optional[float]]] = Field(default_factory=list)
    spearman: List[List[Optional[float]]] = Field(default_factory=list)
    pairs: List[PairCorrelation] = Field(default_factory=list)

    average_pearson: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    max_pearson: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    max_pearson_pair: Optional[List[str]] = None
    min_pearson: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    average_exposure_overlap: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    alignment: AlignmentDiagnostics
    is_valid: bool = False
    warnings: List[str] = Field(default_factory=list)


class JointSimulationResult(BaseModel):
    """Monte Carlo over the whole book, with the co-movement left in.

    The correlation matrix says how the bots move together; this says what that
    costs. The two counterfactual VaRs below are the point of the exercise:
    `sum_individual_var_95_pct` is the no-diversification benchmark, and
    `independent_var_95_pct` is what the same bots would risk if their
    co-movement were destroyed, so the gap between them and `var_95_pct`
    separates "these bots genuinely offset" from "these bots are one bet".
    """

    method: str = "STATIONARY_BOOTSTRAP_JOINT_BUCKETS"
    iterations: int = Field(default=0, ge=0)
    horizon_buckets: int = Field(default=0, ge=0)
    horizon_calendar_days: Optional[float] = Field(default=None, ge=0.0)
    sample_buckets: int = Field(default=0, ge=0)
    sample_is_thin: bool = False

    capital_at_risk: Optional[float] = Field(default=None, gt=0.0)
    capital_basis: str = "SUM_OF_MEMBER_CAPITAL"

    # All of the below are percentages OF `capital_at_risk`. A positive VaR /
    # CVaR is a LOSS, matching `SimulationResults`' own convention so the two
    # are never read with opposite signs.
    var_95_pct: Optional[float] = None
    var_99_pct: Optional[float] = None
    cvar_95_pct: Optional[float] = None
    cvar_99_pct: Optional[float] = None
    profit_pct_p05: Optional[float] = None
    profit_pct_p50: Optional[float] = None
    profit_pct_p95: Optional[float] = None
    probability_of_profit: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    median_max_drawdown: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p95_max_drawdown: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    p_ruin: Optional[float] = Field(default=None, ge=0.0, le=100.0)

    sum_individual_var_95_pct: Optional[float] = None
    independent_var_95_pct: Optional[float] = None
    # 1 - joint/undiversified. ~0 means combining these bots bought nothing;
    # negative means the combination is worse than the parts. `None` when the
    # benchmark is not positive, where the ratio would be meaningless rather
    # than merely extreme.
    diversification_ratio: Optional[float] = None
    # 1 - independent/undiversified: the diversification the SAME bots would
    # have delivered with their co-movement removed. The shortfall between
    # this and `diversification_ratio` is the part correlation ate.
    potential_diversification_ratio: Optional[float] = None
    correlation_cost_pct: Optional[float] = None

    per_member_var_95_pct: Dict[str, float] = Field(default_factory=dict)
    is_valid: bool = False
    warnings: List[str] = Field(default_factory=list)


class ExposureConcentration(BaseModel):
    """Where the book actually sits, ignoring how many bots it is spread over."""

    by_symbol: Dict[str, float] = Field(default_factory=dict)
    largest_symbol: Optional[str] = None
    largest_symbol_share_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    # Herfindahl-Hirschman index over notional share, normalised to 0-1 where
    # 0 is perfectly even across the symbols held and 1 is everything in one.
    # Raw HHI has a floor of 1/N that moves with the number of symbols, which
    # makes two portfolios of different size incomparable.
    normalised_hhi: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    gross_notional: Optional[float] = Field(default=None, ge=0.0)
    net_notional: Optional[float] = None
    # |net| / gross, 0-1. 1 means every open position points the same way, so
    # the book is a single directional bet however many bots placed it.
    directional_alignment: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    measured_members: int = Field(default=0, ge=0)
    warnings: List[str] = Field(default_factory=list)


class PortfolioRiskAssessment(BaseModel):
    """LOGIC 3 output for a SET of bots. Never replaces the per-bot assessment.

    Each member still has its own `BotRiskAssessment`, produced by the same ten
    lenses as always; this model adds only what cannot be seen from inside a
    single bot.
    """

    schema_version: str = "portfolio_risk_assessment.v1"
    methodology_version: str = "portfolio_qc.v1"
    portfolio_id: str
    assessment_id: str
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), ge=0)
    as_of_ms: int = Field(..., ge=0)

    members: List[PortfolioMember] = Field(default_factory=list)
    member_codes: List[str] = Field(default_factory=list)
    measurable_member_count: int = Field(default=0, ge=0)

    correlation: CorrelationMatrix
    joint_simulation: Optional[JointSimulationResult] = None
    concentration: ExposureConcentration

    # Capital-weighted mean of the members' own risk scores: the portfolio as
    # the sum of its parts, before any portfolio-level effect.
    member_weighted_risk_score: Optional[float] = Field(
        default=None, ge=0.0, le=100.0
    )
    # The above plus what only shows up in combination (co-movement,
    # concentration, a diversification benefit that failed to appear). It can
    # legitimately exceed every individual member's score -- that is the
    # finding, not a bug.
    portfolio_risk_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    risk_tier: str = "UNKNOWN"
    score_adjustments: Dict[str, float] = Field(default_factory=dict)

    verdict: PortfolioVerdict = PortfolioVerdict.INSUFFICIENT_EVIDENCE
    verdict_reason: str = ""
    evidence: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    recommended_action: str = ""
