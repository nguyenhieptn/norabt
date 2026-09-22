"""Deterministic, read-only insight builders for the analysis dossier.

These functions deliberately consume typed observation objects and return plain
structured data. They do not score, persist, fetch, or issue actions. The
existing QC fusion remains authoritative for its score and verdict.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from Agent.backend.market.schemas.market_result import MarketResult
from Agent.backend.bot.mcp.schemas.bot_result import BotResult


# Version of the behavioural/compatibility method in this module. Bump it
# whenever a trait, failure mode or compatibility cell changes how it is
# derived, so a stored dossier says which method produced its numbers.
METHODOLOGY_VERSION = "insights.v1"


class InsightTrait(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    value: Any = None
    status: str = "UNKNOWN"
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sample_size: int = Field(default=0, ge=0)
    evidence_ids: List[str] = Field(default_factory=list)
    counter_evidence_ids: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class BehavioralDNA(BaseModel):
    model_config = ConfigDict(extra="forbid")

    traits: List[InsightTrait] = Field(default_factory=list)
    dominant_patterns: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)


class RiskTwinState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    status: str = "OBSERVED"
    assumptions: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class RiskTwin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reported: RiskTwinState
    marked: RiskTwinState
    stressed: List[RiskTwinState] = Field(default_factory=list)
    transformations: List[Dict[str, Any]] = Field(default_factory=list)


class FailureMode(BaseModel):
    """One mechanism by which this bot could fail, with its receipts.

    A failure mode is NOT a prediction that failure will happen. It names a
    mechanism, the observation that put it on the list, what would set it off,
    what would show up first, and what would knock it off the list again.
    """

    model_config = ConfigDict(extra="forbid")

    code: str
    mechanism: str
    # The measurement that put this mode on the list, stated as a number a
    # reader can check -- not a restatement of the mechanism.
    observed_support: str
    evidence_ids: List[str] = Field(default_factory=list)
    trigger_conditions: List[str] = Field(default_factory=list)
    early_indicators: List[str] = Field(default_factory=list)
    # Metrics that move first if this mode starts playing out.
    affected_metrics: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    counter_evidence: List[str] = Field(default_factory=list)
    falsifiers: List[str] = Field(default_factory=list)
    status: str = "INFERRED"
    limitations: List[str] = Field(default_factory=list)


def build_failure_modes(
    bot: BotResult, market: Optional[MarketResult] = None
) -> List[FailureMode]:
    """The catalogue in section 6.5 of the design, as far as the data supports it.

    A mode is listed only when a measurement actually puts it on the list, and
    each one states that measurement in `observed_support`. Modes the available
    data cannot speak to are simply absent -- an absent mode means "not
    observed", never "ruled out", which is what `limitations` records.
    """
    behavior = bot.behavioral_observations
    strategy = bot.strategy_observations
    deferred = bot.deferred_loss
    state = bot.current_state
    performance = bot.performance
    quality = bot.data_quality
    identity = bot.identity
    ledger = bot.trade_ledger_summary or []
    modes: List[FailureMode] = []

    def add(**kwargs: Any) -> None:
        modes.append(FailureMode(**kwargs))

    # 1. Deferred-loss realization ------------------------------------------
    if deferred.turns_unprofitable_when_marked or deferred.open_loss:
        add(
            code="DEFERRED_LOSS_REALIZATION",
            mechanism="Closed-book gains are booked while losing exposure stays open.",
            observed_support=(
                f"Open loss {deferred.open_loss:,.0f} against a booked profit factor of "
                f"{deferred.booked_profit_factor:.2f}"
                if deferred.open_loss and deferred.booked_profit_factor
                else "Open losing exposure is present alongside a profitable closed book"
            ),
            evidence_ids=["bot.deferred_loss", "bot.current_state"],
            trigger_conditions=["The open losses are closed", "The open losses keep growing"],
            early_indicators=["Marked profit factor falls below the booked one"],
            affected_metrics=["marked_profit_factor", "unrealized_pnl", "open_loss_to_capital_pct"],
            assumptions=["Open positions are marked at the supplied public mark price"],
            counter_evidence=["bot.performance"],
            falsifiers=["Full position data shows no material open-loss exposure"],
            limitations=list(deferred.warnings),
        )

    # 2. Persistent trend against accumulated exposure ----------------------
    if behavior.averaging_down_detected or behavior.averaging_down_suspected:
        add(
            code="ADVERSE_AVERAGING",
            mechanism="Exposure is added after price has already moved against the position.",
            observed_support=(
                "Averaging down confirmed in the ledger"
                if behavior.averaging_down_detected
                else "Averaging down suspected but not confirmed"
            ),
            evidence_ids=["bot.behavior.averaging_down"],
            trigger_conditions=["A move continues against the accumulated position"],
            early_indicators=["Repeated entries at progressively worse prices"],
            affected_metrics=["average_loss", "max_drawdown_pct", "open_loss"],
            assumptions=["Same-direction re-entries on one symbol form one exposure"],
            counter_evidence=["bot.performance"],
            falsifiers=["Sequencing shows no adverse re-entry once symbol and side are controlled for"],
        )

    # 3. Liquidity contraction ----------------------------------------------
    if market is not None:
        tier = market.liquidity_state.state_tier.value
        if tier in ("THIN", "ILLIQUID", "UNKNOWN"):
            add(
                code="LIQUIDITY_CONTRACTION",
                mechanism="Exit size exceeds what the observed book absorbs without moving price.",
                observed_support=f"Observed liquidity tier is {tier}",
                evidence_ids=["market.primary", "bot.current_state"],
                trigger_conditions=["Depth thins further while exposure is open"],
                early_indicators=["Widening spread", "Falling depth at 0.2%"],
                affected_metrics=["estimated_slippage_10k_pct", "spread_pct"],
                assumptions=["The observed book is representative of exit conditions"],
                falsifiers=["Depth remains adequate for the bot's typical notional"],
                limitations=["Liquidity is unknown" if tier == "UNKNOWN" else ""] if tier == "UNKNOWN" else [],
            )

    # 4. Leverage escalation -------------------------------------------------
    if behavior.leverage_escalation_detected:
        add(
            code="LEVERAGE_ESCALATION",
            mechanism="Leverage is raised after losing trades rather than reduced.",
            observed_support="Leverage escalation after losses detected in the ledger",
            evidence_ids=["bot.behavior.leverage_escalation"],
            trigger_conditions=["A losing sequence continues at the raised leverage"],
            early_indicators=["Average leverage rising while equity falls"],
            affected_metrics=["current_leverage", "liquidation_distance_pct"],
            assumptions=["Leverage after wins is the control group"],
            falsifiers=["The pattern disappears once symbol and regime are controlled for"],
        )

    # 5. Loss-side size escalation ------------------------------------------
    if behavior.size_escalation_excess >= 0.25 or behavior.martingale_escalation_detected:
        add(
            code="LOSS_SIDE_SIZE_ESCALATION",
            mechanism="Position size grows disproportionately after a loss.",
            observed_support=(
                f"Size escalation after losses exceeds the after-win baseline by "
                f"{behavior.size_escalation_excess * 100:.0f}%"
            ),
            evidence_ids=["bot.behavior.size_escalation_excess"],
            trigger_conditions=["A loss streak runs longer than the observed sample"],
            early_indicators=["Notional after a loss rising versus after a win"],
            affected_metrics=["average_loss", "max_loss_streak", "max_drawdown_pct"],
            assumptions=["Size after wins is the control group for size after losses"],
            falsifiers=["The excess vanishes once symbol and market phase are controlled for"],
        )

    # 6. Margin exhaustion ---------------------------------------------------
    if state.margin_to_reference_pct is not None and state.margin_to_reference_pct >= 20.0:
        add(
            code="MARGIN_EXHAUSTION",
            mechanism="Committed margin leaves little buffer for an adverse move.",
            observed_support=(
                f"Margin is {state.margin_to_reference_pct:.1f}% of reference capital"
            ),
            evidence_ids=["bot.current_state"],
            trigger_conditions=["An adverse move consumes the remaining free margin"],
            early_indicators=["Rising margin ratio", "Falling liquidation distance"],
            affected_metrics=["margin_ratio", "liquidation_distance_pct", "available_balance"],
            assumptions=["Reference capital is the right denominator for this account"],
            falsifiers=["Free balance outside the measured account covers the exposure"],
            limitations=(
                []
                if state.liquidation_distance_pct is not None
                else ["Liquidation distance is not published, so the buffer cannot be measured directly"]
            ),
        )

    # 7. Profit concentration -------------------------------------------------
    shares = [
        p.profit_share_pct
        for p in strategy.phase_breakdown
        if p.profit_share_pct is not None
    ]
    if shares and max(shares) >= 50.0:
        add(
            code="PROFIT_CONCENTRATION",
            mechanism="Most of the profit comes from a narrow slice of conditions.",
            observed_support=f"A single market phase carries {max(shares):.0f}% of gross profit",
            evidence_ids=["bot.strategy.phase_breakdown"],
            trigger_conditions=["That phase stops recurring"],
            early_indicators=["Profit share shifting as new phases enter the window"],
            affected_metrics=["expectancy", "profit_factor"],
            assumptions=["Phase labels at entry represent the conditions the trade ran in"],
            falsifiers=["Profit spreads once every phase has a comparable sample"],
        )

    # 8. Regime dependence ----------------------------------------------------
    if strategy.regime_dependence_pct is not None and strategy.regime_dependence_pct >= 50.0:
        add(
            code="REGIME_DEPENDENCE",
            mechanism="Results are concentrated in a subset of market phases.",
            observed_support=f"Regime dependence measured at {strategy.regime_dependence_pct:.0f}%",
            evidence_ids=["bot.strategy.phase_breakdown"],
            trigger_conditions=["The market leaves the observed profitable phase"],
            early_indicators=["Untested or losing phases expanding in the window"],
            affected_metrics=["expectancy", "win_rate"],
            assumptions=["Observed phases are representative of future conditions"],
            falsifiers=["Walk-forward samples show stable behaviour across regimes"],
        )

    # 9. Loss clustering ------------------------------------------------------
    if performance.max_loss_streak >= 5 or behavior.loss_chasing_score >= 0.5:
        add(
            code="LOSS_CLUSTERING",
            mechanism="Losses arrive in runs rather than independently.",
            observed_support=f"Longest observed losing streak is {performance.max_loss_streak} trades",
            evidence_ids=["bot.performance", "bot.behavior.loss_chasing"],
            trigger_conditions=["A run longer than the observed maximum"],
            early_indicators=["Streak probability running above its random baseline"],
            affected_metrics=["max_loss_streak", "max_drawdown_pct"],
            assumptions=["Trade order in the ledger is the order they were taken"],
            falsifiers=["Streak frequency matches the independent baseline for this loss rate"],
        )

    # 10. Position concentration ----------------------------------------------
    exposure = state.exposure_by_symbol or {}
    if exposure:
        total_exposure = sum(abs(float(v)) for v in exposure.values())
        top = max(abs(float(v)) for v in exposure.values())
        if total_exposure > 0 and top / total_exposure >= 0.8:
            add(
                code="POSITION_CONCENTRATION",
                mechanism="Open exposure sits in a single instrument.",
                observed_support=(
                    f"One instrument holds {top / total_exposure * 100:.0f}% of open exposure"
                ),
                evidence_ids=["bot.current_state"],
                trigger_conditions=["An instrument-specific shock"],
                early_indicators=["Exposure share rising further"],
                affected_metrics=["gross_exposure", "unrealized_pnl"],
                assumptions=["Reported exposure covers every open position"],
                falsifiers=["Exposure is spread across uncorrelated instruments"],
            )

    # 11. Funding drag ---------------------------------------------------------
    funded = [t for t in ledger if t.funding is not None]
    if funded:
        funding_total = sum(float(t.funding or 0.0) for t in funded)
        if funding_total < 0 and performance.total_pnl and abs(funding_total) >= abs(performance.total_pnl) * 0.1:
            add(
                code="FUNDING_DRAG",
                mechanism="Carrying cost erodes a meaningful share of the result.",
                observed_support=(
                    f"Funding paid totals {funding_total:,.0f} against a net result of "
                    f"{performance.total_pnl:,.0f}"
                ),
                evidence_ids=["bot.trade_ledger_summary"],
                trigger_conditions=["Positions held longer", "Funding rate rising"],
                early_indicators=["Funding share of PnL increasing"],
                affected_metrics=["total_pnl", "expectancy"],
                assumptions=["Recorded funding covers the full holding period"],
                falsifiers=["Funding is negligible once the full period is accounted for"],
            )
    elif ledger:
        # No trade records funding at all: this is data opacity about carry,
        # not evidence that carry is free.
        add(
            code="FUNDING_DRAG",
            mechanism="Carrying cost cannot be measured from the published ledger.",
            observed_support=f"None of {len(ledger)} closed trades records a funding amount",
            evidence_ids=["bot.trade_ledger_summary"],
            trigger_conditions=["Positions held across funding intervals"],
            early_indicators=["Not observable from public data"],
            affected_metrics=["total_pnl", "expectancy"],
            assumptions=["Absence of a funding field means unpublished, not zero"],
            falsifiers=["A ledger with funding shows it to be immaterial"],
            status="UNKNOWN",
            limitations=["Funding is not published for this bot"],
        )

    # 12. Execution / slippage sensitivity --------------------------------------
    notional_known = [t for t in ledger if t.notional is not None]
    if notional_known and performance.expectancy is not None:
        avg_notional = sum(float(t.notional or 0.0) for t in notional_known) / len(notional_known)
        spread_pct = (
            market.price_state.spread_pct
            if market is not None and market.price_state.spread_pct is not None
            else None
        )
        if spread_pct is not None and avg_notional > 0:
            round_trip = avg_notional * (spread_pct / 100.0) * 2.0
            if performance.expectancy != 0 and round_trip >= abs(performance.expectancy) * 0.2:
                add(
                    code="EXECUTION_SLIPPAGE_SENSITIVITY",
                    mechanism="Per-trade edge is small relative to the cost of crossing the spread.",
                    observed_support=(
                        f"A round trip at the observed spread costs about {round_trip:,.2f} "
                        f"against an expectancy of {performance.expectancy:,.2f}"
                    ),
                    evidence_ids=["bot.trade_ledger_summary", "market.primary"],
                    trigger_conditions=["Spread widens", "Fill quality degrades"],
                    early_indicators=["Expectancy falling while win rate holds"],
                    affected_metrics=["expectancy", "payoff_ratio"],
                    assumptions=["The observed spread is representative of the bot's fills"],
                    falsifiers=["Actual fills show the bot posts rather than crosses"],
                )

    # 13. Data opacity -----------------------------------------------------------
    opacity: List[str] = []
    if identity.identity_warnings:
        opacity.append(f"{len(identity.identity_warnings)} identity warnings")
    if state.instrument_withheld_upstream:
        opacity.append("the venue withholds the traded instrument")
    if getattr(bot.reconciliation, "ledger_truncated", False):
        opacity.append("the ledger is truncated")
    if quality.overall_score < 0.8:
        opacity.append(f"data quality scores {quality.overall_score:.2f}")
    if opacity:
        add(
            code="DATA_OPACITY",
            mechanism="Parts of the record are not published, so some risk cannot be measured at all.",
            observed_support="; ".join(opacity),
            evidence_ids=["bot.data_quality", "bot.identity", "bot.reconciliation"],
            trigger_conditions=["Risk concentrating in exactly the unpublished part"],
            early_indicators=["Reported and ledger figures diverging"],
            affected_metrics=["confidence", "mark_coverage", "phase_coverage_pct"],
            assumptions=["Unpublished does not mean absent"],
            falsifiers=["A complete record reconciles with the published figures"],
            status="OBSERVED",
            limitations=list(quality.warnings),
        )

    modes.sort(key=lambda m: m.code)
    return modes


def _status(sample_size: int, *, complete: bool = True) -> str:
    if sample_size <= 0:
        return "UNKNOWN"
    if not complete:
        return "INFERRED"
    return "OBSERVED"


def _confidence(sample_size: int) -> Optional[float]:
    if sample_size <= 0:
        return None
    return round(min(1.0, sample_size / 100.0), 4)


def _trait(
    key: str,
    label: str,
    value: Any,
    sample_size: int,
    *,
    status: Optional[str] = None,
    limitations: Optional[List[str]] = None,
    evidence_ids: Optional[List[str]] = None,
    counter_evidence_ids: Optional[List[str]] = None,
) -> InsightTrait:
    return InsightTrait(
        key=key,
        label=label,
        value=value,
        # A trait whose value the engine could not measure stays UNKNOWN even
        # when the sample is large: an absent number is not a neutral one.
        status="UNKNOWN" if value is None else (status or _status(sample_size)),
        confidence=_confidence(sample_size),
        sample_size=sample_size,
        evidence_ids=list(evidence_ids or [f"bot.behavior.{key}"]),
        counter_evidence_ids=list(counter_evidence_ids or []),
        limitations=list(limitations or []),
    )


def build_behavioral_dna(bot: BotResult) -> BehavioralDNA:
    """Describe measured behavior without assigning an investment judgement."""
    behavior = bot.behavioral_observations
    strategy = bot.strategy_observations
    performance = bot.performance
    sample = bot.trade_statistics.sample_size
    deferred = bot.deferred_loss
    state = bot.current_state
    drawdown = bot.drawdown_analysis
    ledger = bot.trade_ledger_summary or []

    # Per-trait sample sizes.
    #
    # Every trait used to report the whole ledger's n, which overstated
    # confidence badly: a trait measured only on losing trades (size response
    # after a loss, loss chasing, leverage response) is supported by the LOSS
    # count, and a regime trait only by the phase-labelled count. On a typical
    # book those are several times smaller than the ledger, so the published
    # confidence was several times too high for exactly the traits the risk
    # verdict leans on.
    losses = sum(1 for t in ledger if t.realized_pnl < 0)
    wins = sum(1 for t in ledger if t.realized_pnl > 0)
    phased = sum(1 for t in ledger if t.market_phase and t.market_phase != "UNKNOWN")
    timed = sum(1 for t in ledger if t.holding_time_minutes is not None)
    levered = sum(1 for t in ledger if t.leverage is not None)
    open_positions = state.open_positions_count
    # An asymmetry needs both sides; the smaller side bounds what is measurable.
    both_sides = min(wins, losses)

    # Profit mechanism: whether the closed book earns from frequent small wins
    # or rare large ones. Payoff ratio and win rate together say which, and
    # neither alone does.
    profit_mechanism = None
    if performance.payoff_ratio is not None:
        if performance.win_rate >= 70.0 and performance.payoff_ratio < 1.0:
            profit_mechanism = "MANY_SMALL_WINS_FEW_LARGE_LOSSES"
        elif performance.win_rate <= 45.0 and performance.payoff_ratio > 1.5:
            profit_mechanism = "FEW_LARGE_WINS_MANY_SMALL_LOSSES"
        else:
            profit_mechanism = "BALANCED_WIN_LOSS_SIZING"

    # Capital intensity: how much of the reference capital is committed as
    # margin right now. `None` when capital could not be established at all --
    # an unmeasured exposure must not read as a small one.
    capital_intensity = state.margin_to_reference_pct

    # Temporal stability: the run of consecutive losses relative to the sample.
    # A long streak inside a short sample means the measured edge is fragile.
    temporal_stability = None
    if sample > 0 and performance.max_loss_streak:
        temporal_stability = round(1.0 - min(1.0, performance.max_loss_streak / float(sample)), 4)

    # Transparency: the share of open positions the engine could attribute to
    # this bot's own ledger universe rather than merely observe.
    attribution_quality = None
    if state.open_positions_count:
        attribution_quality = round(
            state.attributed_positions_count / float(state.open_positions_count), 4
        )

    traits = [
        _trait("observed_profile", "Observed trading profile", strategy.observed_profile, phased),
        _trait("profit_mechanism", "Profit mechanism", profit_mechanism, both_sides,
               evidence_ids=["bot.performance"],
               limitations=[] if profit_mechanism else ["Payoff ratio is not measurable from this ledger"]),
        _trait("directional_bias", "Directional bias", strategy.directional_bias, sample,
               evidence_ids=["bot.strategy.directional_bias"]),
        _trait("entry_style", "Entry style", strategy.entry_style, sample,
               evidence_ids=["bot.strategy.entry_style"]),
        _trait("hold_time_asymmetry", "Win/loss holding-time asymmetry",
               behavior.holding_time_explosion_score, min(timed, both_sides),
               evidence_ids=["bot.behavior.holding_time_explosion"],
               counter_evidence_ids=["bot.performance"]),
        _trait("loss_realization", "Loss realization behavior",
               "NEVER_REALIZED_A_LOSS" if deferred.never_realized_a_loss else "REALIZES_LOSSES",
               losses + open_positions, evidence_ids=["bot.deferred_loss"],
               counter_evidence_ids=["bot.current_state"]),
        _trait("loss_chasing", "Loss-chasing signal", behavior.loss_chasing_score, losses),
        _trait("size_escalation_excess", "Position-size response after losses",
               behavior.size_escalation_excess, both_sides,
               counter_evidence_ids=["bot.performance"]),
        _trait("leverage_response", "Leverage response after losses",
               behavior.leverage_escalation_detected, min(levered, both_sides),
               evidence_ids=["bot.behavior.leverage_escalation"]),
        _trait("reentry_behavior", "Re-entry behavior", behavior.reentry_loop_detected, sample,
               evidence_ids=["bot.behavior.reentry_loop"]),
        _trait("profit_concentration", "Profit concentration across regimes",
               strategy.regime_dependence_pct, phased,
               evidence_ids=["bot.strategy.phase_breakdown"],
               limitations=[] if strategy.regime_dependence_pct is not None
               else ["Profit could not be split across market phases"]),
        _trait("regime_dependence", "Regime dependence", strategy.regime_dependence_pct, phased,
               evidence_ids=["bot.strategy.phase_breakdown"]),
        _trait("capital_intensity", "Capital intensity (margin vs reference capital)",
               capital_intensity, open_positions, evidence_ids=["bot.current_state"],
               limitations=[] if capital_intensity is not None
               else ["Reference capital could not be established, so intensity is undetermined"]),
        _trait("temporal_stability", "Temporal stability", temporal_stability, sample,
               evidence_ids=["bot.performance"],
               limitations=[] if temporal_stability is not None
               else ["No loss streak is measurable from this sample"]),
        _trait("attribution_quality", "Transparency and attribution quality",
               attribution_quality, open_positions,
               status="INFERRED" if attribution_quality is not None and attribution_quality < 1.0 else None,
               evidence_ids=["bot.current_state"],
               limitations=[] if attribution_quality is not None
               else ["No open position is present to attribute"]),
        _trait("deferred_loss_dependency", "Deferred-loss dependency", deferred.representativeness, open_positions, status="INFERRED" if deferred.mark_coverage < 1.0 else "OBSERVED"),
        _trait("profit_factor", "Closed-book profit factor", performance.profit_factor, sample,
               evidence_ids=["bot.performance"],
               counter_evidence_ids=["bot.deferred_loss"] if deferred.turns_unprofitable_when_marked else []),
        _trait("max_drawdown_pct", "Maximum observed drawdown", drawdown.max_dd_pct, sample,
               evidence_ids=["bot.drawdown_analysis"],
               limitations=list(["Drawdown is capped by the available capital basis"] if drawdown.max_dd_pct_capped else [])),
    ]
    dominant: List[str] = []
    if behavior.averaging_down_detected or behavior.averaging_down_suspected:
        dominant.append("AVERAGING_DOWN_CHARACTERISTICS")
    if behavior.martingale_escalation_detected or behavior.size_escalation_excess >= 0.25:
        dominant.append("LOSS_SIDE_SIZE_ESCALATION")
    if deferred.turns_unprofitable_when_marked:
        dominant.append("MARKED_BOOK_REVERSES_CLOSED_BOOK")
    if strategy.regime_dependence_pct is not None and strategy.regime_dependence_pct >= 50.0:
        dominant.append("REGIME_DEPENDENCE")
    unknowns: List[str] = []
    if not strategy.tested_in_downtrend:
        unknowns.append("Persistent downtrend behavior is not observed")
    if deferred.mark_coverage < 1.0:
        unknowns.append("Some open-position attribution is incomplete")
    return BehavioralDNA(traits=traits, dominant_patterns=dominant, unknowns=unknowns)


def build_risk_twin(
    bot: BotResult, stressed_states: Optional[List[RiskTwinState]] = None
) -> RiskTwin:
    """Build reported and marked states; no future outcome is forecast here."""
    performance = bot.performance
    deferred = bot.deferred_loss
    current = bot.current_state
    reported_metrics = {
        "trade_count": performance.trade_count,
        "win_rate": performance.win_rate,
        "profit_factor": performance.profit_factor,
        "total_pnl": performance.total_pnl,
        "drawdown_pct": performance.max_drawdown_pct,
    }
    marked_metrics = {
        "trade_count": performance.trade_count,
        "win_rate": deferred.marked_win_rate,
        "profit_factor": deferred.marked_profit_factor,
        "total_pnl": deferred.marked_total_pnl,
        "open_loss": deferred.open_loss,
        "open_loss_to_capital_pct": deferred.open_loss_to_capital_pct,
        "mark_coverage": deferred.mark_coverage,
    }
    limitations = list(deferred.warnings)
    if deferred.mark_coverage < 1.0:
        limitations.append("Marked state does not cover every open position")
    reported = RiskTwinState(
        state="REPORTED",
        metrics=reported_metrics,
        status="OBSERVED",
        evidence_ids=["bot.performance"],
    )
    marked = RiskTwinState(
        state="MARKED",
        metrics=marked_metrics,
        status="INFERRED" if deferred.mark_coverage < 1.0 else "OBSERVED",
        assumptions=["Open positions are marked using the available public mark data"],
        evidence_ids=["bot.deferred_loss", "bot.current_state"],
        limitations=limitations,
    )
    transformations = []
    if deferred.booked_profit_factor is not None and deferred.marked_profit_factor is not None:
        transformations.append({
            "metric": "profit_factor",
            "reported": deferred.booked_profit_factor,
            "marked": deferred.marked_profit_factor,
            "reason": "open positions are included in the marked state",
        })
    if current.unrealized_pnl is not None:
        transformations.append({
            "metric": "unrealized_pnl",
            "reported": 0.0,
            "marked": current.unrealized_pnl,
            "reason": "current open exposure is not part of closed-book realized PnL",
        })
    # The third state the design asks for. It is supplied by the caller from
    # the scenario laboratory rather than recomputed here, so the page and the
    # dossier cannot disagree about what "stressed" means. Empty is honest when
    # no scenario produced an interval.
    stressed = list(stressed_states or [])
    for state in stressed:
        if deferred.booked_profit_factor is None:
            continue
        stressed_pnl = state.metrics.get("total_pnl_p05")
        if stressed_pnl is None:
            continue
        transformations.append({
            "metric": "total_pnl",
            "reported": performance.total_pnl,
            "stressed": stressed_pnl,
            "scenario": state.state,
            "reason": "5th percentile of the resampled scenario, not an expected value",
        })
    return RiskTwin(
        reported=reported,
        marked=marked,
        stressed=stressed,
        transformations=transformations,
    )


def build_market_summary(market: Optional[MarketResult]) -> Dict[str, Any]:
    if market is None:
        return {"status": "UNKNOWN", "metrics": {}, "limitations": ["No primary market observation"]}
    return {
        "status": "OBSERVED",
        "symbol": market.symbol,
        "venue": market.venue,
        "metrics": {
            "last_price": market.price_state.last_price,
            "spread_pct": market.price_state.spread_pct,
            "trend_state": market.structure_state.trend_state,
            "volatility_state": market.structure_state.volatility_state,
            "realized_volatility": market.structure_state.realized_volatility,
            "liquidity": market.liquidity_state.model_dump(mode="json") if market.liquidity_state else None,
        },
        "data_quality": market.data_quality.model_dump(mode="json"),
        "limitations": list(market.data_quality.warnings),
    }


class ExecutiveEssence(BaseModel):
    """The shortest accurate description of a bot's observed character.

    Deliberately not a verdict: no field here may hold a copy/avoid/allocate
    instruction. Each field is either a measured observation or `None`.
    """

    model_config = ConfigDict(extra="forbid")

    what_it_appears_to_do: str
    dominant_behavior: Optional[str] = None
    strongest_positive_evidence: Optional[str] = None
    strongest_fragility: Optional[str] = None
    evidence_reliability: str = "UNKNOWN"
    most_important_unknown: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)


class CompatibilityCell(BaseModel):
    """One (symbol, regime) square of the market compatibility matrix."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    venue_type: Optional[str] = None
    regime: str
    observed_trades: int = Field(default=0, ge=0)
    win_rate: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    total_pnl: Optional[float] = None
    expectancy: Optional[float] = None
    median_hold_minutes: Optional[float] = Field(default=None, ge=0.0)
    reliability: str = "UNRELIABLE"
    status: str = "OBSERVED"
    failure_modes: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


class MarketCompatibility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary_symbol: str
    cells: List[CompatibilityCell] = Field(default_factory=list)
    observed_regimes: List[str] = Field(default_factory=list)
    untested_regimes: List[str] = Field(default_factory=list)
    losing_regimes: List[str] = Field(default_factory=list)
    unresolved_symbols: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


def _reliability(trade_count: int) -> str:
    """Grade a cell by its own sample, using the report's existing thresholds.

    Kept identical to the phase-breakdown thresholds the HTML report already
    states to the reader (>=10 valid, 3-9 reference only, <3 unrepresentative)
    so the two surfaces cannot disagree about the same cell.
    """
    if trade_count >= 10:
        return "STATISTICALLY_VALID"
    if trade_count >= 3:
        return "REFERENCE_ONLY"
    return "UNREPRESENTATIVE"


def build_market_compatibility(
    bot: BotResult,
    *,
    unresolved_symbols: Optional[List[str]] = None,
) -> MarketCompatibility:
    """Build the conditional compatibility matrix described in §6.4.

    Compatibility is stated per (symbol, regime) cell and never collapsed into
    a single bot-level verdict. Only the symbol the phase breakdown was
    actually measured on is claimed; other resolved markets appear in coverage,
    not here, because no per-regime sample exists for them.
    """
    strategy = bot.strategy_observations
    failure_codes = [mode.code for mode in build_failure_modes(bot)]
    cells: List[CompatibilityCell] = []
    for phase in strategy.phase_breakdown:
        cells.append(
            CompatibilityCell(
                symbol=bot.identity.symbol,
                venue_type=getattr(bot.identity, "venue_type", None),
                regime=phase.phase,
                observed_trades=phase.trades,
                win_rate=phase.win_rate,
                total_pnl=phase.total_pnl,
                expectancy=phase.expectancy,
                median_hold_minutes=phase.median_hold_minutes,
                reliability=_reliability(phase.trades),
                status="OBSERVED",
                failure_modes=failure_codes if phase.total_pnl < 0 else [],
                evidence_ids=["bot.strategy.phase_breakdown"],
            )
        )

    # An untested regime is a real, reportable cell: it must appear as UNKNOWN
    # rather than be omitted, or a reader sees only the regimes that went well.
    for regime in strategy.untested_phases:
        cells.append(
            CompatibilityCell(
                symbol=bot.identity.symbol,
                venue_type=getattr(bot.identity, "venue_type", None),
                regime=regime,
                observed_trades=0,
                reliability="UNREPRESENTATIVE",
                status="UNKNOWN",
                evidence_ids=["bot.strategy.phase_breakdown"],
            )
        )

    limitations: List[str] = []
    if strategy.trades_without_phase:
        limitations.append(
            f"{strategy.trades_without_phase} closed trades could not be mapped to a market phase"
        )
    if not strategy.tested_in_downtrend:
        limitations.append("No downtrend sample exists for this bot")
    if unresolved_symbols:
        limitations.append(
            "Some traded symbols have no public market feed and are excluded from the matrix"
        )

    return MarketCompatibility(
        primary_symbol=bot.identity.symbol,
        cells=cells,
        observed_regimes=[phase.phase for phase in strategy.phase_breakdown],
        untested_regimes=list(strategy.untested_phases),
        losing_regimes=list(strategy.losing_phases),
        unresolved_symbols=list(unresolved_symbols or []),
        limitations=limitations,
    )


def build_executive_essence(
    bot: BotResult,
    dna: BehavioralDNA,
    failure_modes: List[FailureMode],
    reliability: str,
) -> ExecutiveEssence:
    """Summarize observed character without stating an action for the reader."""
    strategy = bot.strategy_observations
    performance = bot.performance
    deferred = bot.deferred_loss

    positive: Optional[str] = None
    if performance.profit_factor is not None and performance.profit_factor > 1.0:
        positive = (
            f"Closed trades show a profit factor of {performance.profit_factor:.2f} "
            f"across {performance.trade_count} trades"
        )
    elif performance.trade_count:
        positive = f"A closed-trade ledger of {performance.trade_count} trades is available to measure"

    fragility: Optional[str] = None
    if failure_modes:
        fragility = failure_modes[0].mechanism
    elif deferred.open_loss_to_capital_pct:
        fragility = "Open losing exposure is material relative to reference capital"

    unknown: Optional[str] = dna.unknowns[0] if dna.unknowns else None
    if unknown is None and strategy.untested_phases:
        unknown = f"Untested market phases: {', '.join(strategy.untested_phases)}"

    return ExecutiveEssence(
        what_it_appears_to_do=strategy.observed_profile,
        dominant_behavior=dna.dominant_patterns[0] if dna.dominant_patterns else None,
        strongest_positive_evidence=positive,
        strongest_fragility=fragility,
        evidence_reliability=reliability,
        most_important_unknown=unknown,
        evidence_ids=["bot.performance", "bot.strategy.phase_breakdown", "bot.deferred_loss"],
    )
