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
    # OKX withholds this bot's order book (60004), so it has no trades, no
    # open positions and no exit-rule fingerprint -- but it IS measured for
    # co-movement and joint risk, from OKX's public daily PnL (see
    # `AlignmentDiagnostics.pnl_basis`). Distinct from `excluded_reason`: a
    # ledger-hidden member is inside the matrix, just not inside the
    # behaviour comparison or the merged ledger.
    ledger_hidden: bool = False
    # Where `capital_at_risk` came from: "LEDGER_MODEL" (this bot's own
    # equity-curve capital, what its merged-book figures are measured on) or
    # "OKX_INVEST_AMT" (OKX's public `investAmt`, used for every member at
    # once when the matrix runs on the public daily-PnL basis). The ledger
    # model is kept in `ledger_capital` either way, so per-bot drawdowns on
    # the Positions tab stay on the same basis as the merged book's.
    capital_source: str = "LEDGER_MODEL"
    ledger_capital: Optional[float] = Field(default=None, gt=0.0)
    # What `realized_pnl` is: closed-trade PnL from the order book
    # ("REALIZED"), or -- for a ledger-hidden member -- OKX's public
    # mark-to-market PnL summed over `public_window_days`. Two different
    # quantities over two different windows; the page labels them apart.
    pnl_basis: str = "REALIZED"
    public_window_days: Optional[int] = Field(default=None, ge=0)
    # The open book at analysis time (ledger members only).
    open_positions: Optional[int] = Field(default=None, ge=0)
    unrealized_pnl: Optional[float] = None

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
    # WHICH PnL every row of the matrix is. One value for the whole matrix,
    # never per row: a correlation between a realized-at-close series and a
    # mark-to-market series measures the ruler as much as the bots.
    #   REALIZED_LEDGER      -- closed-trade PnL bucketed by close time, from
    #                           each bot's own order book (needs a ledger).
    #   MARK_TO_MARKET_DAILY -- OKX's public daily PnL (`public-pnl`), which
    #                           OKX keeps publishing even for a bot whose
    #                           order book it withholds (60004). Validated
    #                           against 14 ledgers: same money over the same
    #                           window, booked when marked rather than when
    #                           closed (cumulative-curve r 0.85).
    pnl_basis: str = "REALIZED_LEDGER"


class StyleVerdict(str, Enum):
    """Whether the members run the same playbook, independent of results."""

    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    DISTINCT_PLAYBOOKS = "DISTINCT_PLAYBOOKS"
    PARTIAL_OVERLAP = "PARTIAL_OVERLAP"
    SAME_PLAYBOOK = "SAME_PLAYBOOK"


class PairStyle(BaseModel):
    """How alike two members TRADE, as opposed to how alike their results are.

    This exists because the two routinely disagree and the disagreement is the
    finding. PnL co-movement is a property of the window the bots happened to
    share; the exit discipline behind it is a property of the strategy. Two
    grid bots whose PnL offset over one quarter are not diversified, they are
    one idea that got lucky with timing, and only this half of the comparison
    can say so.
    """

    exit_distance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    exit_similarity: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    rule_distance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    hold_distance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    # Which half drove the headline distance: "RULE" or "HOLDING_PERIOD".
    driver: Optional[str] = None
    top_rule_component: Optional[str] = None
    top_rule_gap: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    exit_style_a: Optional[str] = None
    exit_style_b: Optional[str] = None
    same_exit_style: bool = False
    shared_patterns: List[str] = Field(default_factory=list)
    # The trap this feature exists to catch: results look uncorrelated while
    # the trading behind them is the same.
    style_vs_pnl_conflict: bool = False
    note: str = ""


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
    # `None` when at least one member's ledger is too thin to fingerprint.
    style: Optional[PairStyle] = None


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

    # What the page draws, from the SAME joint run (percent of
    # `capital_at_risk`, x in calendar days): percentile checkpoints of the
    # cumulative return, the terminal-return histogram, a few of the drawn
    # paths for the band chart, and each member's median contribution (its
    # PnL as % of the COMBINED capital). Empty on records written before
    # these were kept.
    path_checkpoints: List[Dict[str, float]] = Field(default_factory=list)
    terminal_histogram: Optional[Dict[str, List[float]]] = None
    sample_paths: List[List[List[float]]] = Field(default_factory=list)
    member_median_paths: Dict[str, List[List[float]]] = Field(default_factory=dict)
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


class SymbolExposure(BaseModel):
    """One instrument, seen from BOTH sides at once.

    The report has a market tab and a position tab, and a reader comparing
    them has to hold one in their head while looking at the other. The two
    belong together: "53% of the book is in ETH" means one thing when ETH is
    trending and another when it is not, and neither tab can say both. This
    is the row that does.

    The market half is filled in by the presentation layer from the coverage
    the pipeline resolved; the trading half is computed here, from the merged
    ledger and the open book.
    """

    symbol: str
    # --- what the portfolio DID here -----------------------------------
    closed_trades: int = Field(default=0, ge=0)
    realized_pnl: float = 0.0
    win_rate: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    # Which members touched this instrument. Two bots in the same symbol is
    # the concentration a per-bot view cannot show.
    members: List[str] = Field(default_factory=list)
    # --- what it HOLDS here now ----------------------------------------
    open_notional: Optional[float] = Field(default=None, ge=0.0)
    exposure_share: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    open_positions: int = Field(default=0, ge=0)


class MemberRiskShare(BaseModel):
    """One member's share of the book's capital versus its share of the book's RISK.

    The two differ, and the difference is the portfolio question: a bot with
    10% of the capital can carry 40% of the volatility if it is both volatile
    and moving with everything else.
    """

    label: str
    unique_code: str
    capital_weight_pct: Optional[float] = None
    # Annualised volatility of this member's own return on its own capital.
    standalone_volatility_pct: Optional[float] = None
    # Euler decomposition of portfolio volatility: w_i * (Cov w)_i / sigma_p.
    # Sums to 100 across members. Can be negative for a true hedge.
    risk_contribution_pct: Optional[float] = None
    pnl: Optional[float] = None


class PortfolioBookMetrics(BaseModel):
    """The book as ONE account: N PnL series summed on the shared clock.

    These are the portfolio-level versions of the headline numbers a single
    bot report shows -- computed from the aligned member series (the same
    ruler as the correlation matrix, see `AlignmentDiagnostics.pnl_basis`),
    never from a pooled trade list. Pooling trades of bots with different
    sizes answers "what did the average trade do", not "what did the account
    do": measured on a live 4-bot book (2026-09-24) the pooled per-trade
    Sharpe read 5.97 against a portfolio daily Sharpe of 2.06, and the pooled
    profit factor 2.47 against 1.41.
    """

    pnl_basis: str = "REALIZED_LEDGER"
    bucket_label: str = "1d"
    periods: int = Field(default=0, ge=0)
    periods_per_year: Optional[float] = None
    capital: Optional[float] = Field(default=None, gt=0.0)

    total_pnl: Optional[float] = None
    return_pct: Optional[float] = None
    max_drawdown_pct: Optional[float] = Field(default=None, ge=0.0)
    max_drawdown_abs: Optional[float] = Field(default=None, ge=0.0)
    current_drawdown_pct: Optional[float] = Field(default=None, ge=0.0)
    # Share of periods in which the WHOLE book made money.
    profitable_period_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    profit_factor: Optional[float] = Field(default=None, ge=0.0)
    volatility_annual_pct: Optional[float] = Field(default=None, ge=0.0)
    sharpe_annual: Optional[float] = None
    sortino_annual: Optional[float] = None
    # 1 - sigma_p / sum(w_i sigma_i): how much of the members' own volatility
    # cancels out inside the book.
    volatility_diversification_pct: Optional[float] = None
    members: List[MemberRiskShare] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class PortfolioRiskAssessment(BaseModel):
    """The diversification section of a portfolio report -- not the report.

    A multi-bot run produces ONE ordinary `BotRiskAssessment`, built by the
    usual ten lenses over the members' merged ledger, so it carries every
    section and every tab a single-bot report has. This model is the one thing
    that report cannot contain, because it is meaningless for a single bot:
    whether the members move together, whether they trade the same way, and
    what their co-movement costs the combined loss tail.

    It therefore holds no risk score of its own -- see `combined_*` below.
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
    # Per-instrument, ordered by how much of the book sits there. The market
    # side of each row is attached by the renderer -- see `SymbolExposure`.
    symbol_breakdown: List[SymbolExposure] = Field(default_factory=list)
    # The book as one account (see `PortfolioBookMetrics`): the portfolio
    # versions of the headline numbers, on the matrix's own ruler.
    book: Optional[PortfolioBookMetrics] = None

    # Pointers to the ONE assessment that carries the portfolio's risk score.
    #
    # There is deliberately no second score here. The portfolio's risk is
    # produced by the same ten lenses as any bot's, run over the merged ledger
    # (see `PortfolioAggregator`), so it lives in that `BotRiskAssessment` and
    # nowhere else. An independently computed "portfolio score" beside it
    # would be a second answer to a question that already has one, and the two
    # would drift. These fields are copies for listings and history tables
    # only -- the assessment remains the source of truth.
    combined_bot_id: Optional[str] = None
    combined_assessment_id: Optional[str] = None
    combined_risk_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    combined_quality_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    combined_risk_tier: Optional[str] = None
    combined_verdict: Optional[str] = None

    # What only a set of bots can be asked, and the reason this section exists
    # at all. Not a risk score and never mixed into one: a set can be
    # perfectly diversified and still be uniformly bad, or tightly correlated
    # and individually excellent.
    verdict: PortfolioVerdict = PortfolioVerdict.INSUFFICIENT_EVIDENCE
    verdict_reason: str = ""
    # How much of the SUBMITTED book (not just the measured one) this
    # section's figures actually cover, 0-100. 100 when every submitted bot
    # loaded; pulled down by each CONCEALED member, weighted by capital when
    # every concealed member's AUM is known, by plain headcount otherwise
    # (see `PortfolioQCService._measurement_coverage`). This is deliberately
    # NOT a second risk score -- it says nothing about whether the book is
    # risky, only how much of it correlation/joint-simulation/concentration
    # above actually looked at. A reader trusting `verdict` at face value
    # without checking this could be trusting a number computed over 60% of
    # the capital they actually hold.
    measurement_coverage_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    # How much of the submitted book the MERGED-BOOK figures describe: the
    # headline risk/quality score, Monte Carlo, drawdown and every trade
    # table are built from order books, so a member measured only from its
    # public daily PnL (`PortfolioMember.ledger_hidden`) is inside the
    # correlation matrix yet outside all of those. Capital-weighted when every
    # member's capital is known, headcount otherwise; 0-100. Equal to
    # `measurement_coverage_pct` when no member is ledger-hidden.
    score_coverage_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    score_member_count: Optional[int] = Field(default=None, ge=0)
    # How many bots were SUBMITTED, before any of them dropped out --
    # `len(members)` alone cannot answer this, because a concealed or
    # unreachable bot never becomes a `PortfolioMember` at all (see
    # `PortfolioAggregator.combine`, which never sees its trades). Found
    # live, 2026-09-24: a 4-code portfolio.analyze request persisted to
    # history as "3 bots" with no trace anywhere in `/api/portfolios` that a
    # 4th had ever been asked for -- the concealed-member fix from
    # 2026-09-23 covered the full report document (`report/multi/<id>/
    # latest.json`, which DOES carry `failures`) but not this lighter
    # history index, which stores a bare `PortfolioRiskAssessment` and had
    # nowhere to put the fact that one code never became a member.
    submitted_member_count: int = Field(default=0, ge=0)
    # Codes CONCEALED specifically -- kept separate from a generic "excluded"
    # count because concealment is a finding about the bot (see
    # `PortfolioMemberFailure.kind`'s own docstring) and a reader scanning
    # history needs to see WHICH exclusion this was, not just that one
    # happened.
    concealed_member_codes: List[str] = Field(default_factory=list)
    style_verdict: StyleVerdict = StyleVerdict.INSUFFICIENT_EVIDENCE
    style_verdict_reason: str = ""
    # At least one pair whose results look independent while its trading does
    # not. The single most actionable line in this whole section.
    style_vs_pnl_conflict: bool = False
    evidence: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    recommended_action: str = ""
