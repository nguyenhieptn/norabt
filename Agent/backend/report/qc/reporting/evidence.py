"""Evidence ledger, uncertainty passport and the deterministic claim engine.

Three separate jobs live here, all of them pure functions over already-computed
typed results:

* the **evidence ledger** turns every raw source record the pipeline actually
  read into an addressable row, so a claim can point at the exact source that
  backs it instead of at a module name;
* the **uncertainty passport** decomposes one confidence number into the
  components a reader can argue with;
* the **claim engine** decides which statements the evidence is strong enough
  to support, and -- just as importantly -- which wording level each statement
  is allowed to use.

Nothing here scores a bot, fetches data, or writes anything.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from Agent.backend.market.schemas.market_result import MarketResult
from Agent.backend.bot.mcp.schemas.bot_result import BotResult


# Version of the uncertainty decomposition and the claim rule table.
METHODOLOGY_VERSION = "evidence.v1"


# --------------------------------------------------------------------------- #
# Wording levels
#
# The point of grading wording is that the same claim object is consumed by the
# HTML report, MCP and a future LLM. Without an explicit ceiling, each surface
# invents its own verb and the three disagree about how sure the engine was.
# Ordered weakest to strongest; a consumer may weaken a claim, never strengthen
# one.
# --------------------------------------------------------------------------- #
WORDING_LEVELS = (
    "DATA_DOES_NOT_ESTABLISH",
    "CANNOT_DETERMINE",
    "SUGGESTS",
    "CONSISTENT_WITH",
    "DATA_SHOWS",
)

CLAIM_STRENGTHS = ("INSUFFICIENT", "WEAK", "INDICATIVE", "STRONG", "OBSERVED")


class SourceRecord(BaseModel):
    """One raw input the pipeline read, as the quality layer reported it."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    domain: str
    source: str
    status: str
    record_count: int = Field(default=0, ge=0)
    observed_at_ms: Optional[int] = Field(default=None, ge=0)
    age_ms: Optional[int] = Field(default=None, ge=0)
    staleness_limit_ms: Optional[int] = Field(default=None, ge=0)
    reason: Optional[str] = None


class UncertaintyPassport(BaseModel):
    """Confidence decomposed into components, each independently checkable.

    Every component is `None` when the engine has no basis to score it; a
    missing component must never be read as a good one.
    """

    model_config = ConfigDict(extra="forbid")

    identity_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reconciliation_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    data_completeness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    freshness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    instrument_attribution: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sample_adequacy: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    regime_coverage: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    extrapolation_distance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    seed_stability: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    model_agreement: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    evidence_coverage: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    overall_reliability: str = "UNKNOWN"
    # An abstention is a result, not a failure: it names the statement the
    # engine declined to make and why.
    abstention_reasons: List[str] = Field(default_factory=list)

    def component_scores(self) -> Dict[str, float]:
        return {
            name: value
            for name, value in (
                ("identity_confidence", self.identity_confidence),
                ("reconciliation_confidence", self.reconciliation_confidence),
                ("data_completeness", self.data_completeness),
                ("freshness", self.freshness),
                ("instrument_attribution", self.instrument_attribution),
                ("sample_adequacy", self.sample_adequacy),
                ("regime_coverage", self.regime_coverage),
                # These two were computed and then dropped from the average, so
                # a result extrapolated far past its sample, or run with too few
                # paths for the seed to stop mattering, scored the same as one
                # that was not. Both are now part of the reliability they
                # describe.
                ("extrapolation_distance", self.extrapolation_distance),
                ("seed_stability", self.seed_stability),
                ("model_agreement", self.model_agreement),
                ("evidence_coverage", self.evidence_coverage),
            )
            if value is not None
        }


class AnalysisClaim(BaseModel):
    """A statement the engine is willing to stand behind, with its receipts."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    claim_type: str
    statement_key: str
    strength: str = "INDICATIVE"
    supporting_evidence: List[str] = Field(default_factory=list)
    contradicting_evidence: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    uncertainty: Dict[str, Any] = Field(default_factory=dict)
    falsifiers: List[str] = Field(default_factory=list)
    allowed_wording_level: str = "SUGGESTS"


def _clamp(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value:  # NaN
        return None
    return max(0.0, min(1.0, float(value)))


def _source_records(domain: str, quality: Any) -> List[SourceRecord]:
    records: List[SourceRecord] = []
    for source in getattr(quality, "sources", None) or []:
        name = str(getattr(source, "source", "") or "unknown")
        records.append(
            SourceRecord(
                evidence_id=f"source.{domain}.{name}",
                domain=domain,
                source=name,
                status=str(getattr(getattr(source, "status", None), "value", getattr(source, "status", "UNKNOWN"))),
                record_count=int(getattr(source, "record_count", 0) or 0),
                observed_at_ms=getattr(source, "observed_at", None),
                age_ms=getattr(source, "age_ms", None),
                staleness_limit_ms=getattr(source, "staleness_limit_ms", None),
                reason=getattr(source, "reason", None),
            )
        )
    return records


def build_source_ledger(
    bot: BotResult, market: Optional[MarketResult]
) -> List[SourceRecord]:
    """Enumerate every raw source record behind the analysis, in a stable order.

    This is the bottom of the evidence graph: a claim references a metric, the
    metric references a source row, and the source row says how many records
    were read, how old they were and why one is missing.
    """
    records = _source_records("bot", bot.data_quality)
    if market is not None:
        records.extend(_source_records("market", market.data_quality))
    records.sort(key=lambda record: record.evidence_id)
    return records


def build_uncertainty(
    bot: BotResult,
    market: Optional[MarketResult],
    *,
    coverage_pct: Optional[float],
    limitations: Optional[List[str]] = None,
) -> UncertaintyPassport:
    """Decompose confidence into the components §6.7 of the design asks for."""
    identity = bot.identity
    quality = bot.data_quality
    strategy = bot.strategy_observations
    simulation = bot.simulation_results

    # Identity: a fingerprinted ledger with no identity warnings is the only
    # case that earns full marks; each warning is a concrete doubt.
    identity_score = 1.0 if identity.ledger_fingerprint else 0.6
    identity_score -= 0.2 * len(identity.identity_warnings)

    reconciliation_status = str(getattr(bot.reconciliation, "status", "") or "").upper()
    reconciliation = {
        "MATCH": 1.0,
        "WITHIN_TOLERANCE": 0.9,
        "LEDGER_TRUNCATED": 0.5,
        "FOREIGN_ROWS_REJECTED": 0.4,
        "MISMATCH": 0.2,
    }.get(reconciliation_status)

    # Instrument attribution: how much of the bot's exposure the engine could
    # actually tie to a named instrument.
    exposure = identity.symbol_exposure_share or {}
    attribution = _clamp(sum(float(v) for v in exposure.values())) if exposure else None

    sample_size = bot.trade_statistics.sample_size
    # 100 closed trades is the point at which the behavioral detectors stop
    # being dominated by a handful of rows; below that the score is linear.
    sample = _clamp(sample_size / 100.0)

    regime = _clamp(
        strategy.phase_coverage_pct / 100.0
        if strategy.phase_coverage_pct is not None
        else None
    )

    # Extrapolation distance: how far the simulation horizon reaches past the
    # observed sample. 1.0 means "the horizon is within the evidence".
    extrapolation = None
    if simulation.horizon_trades and sample_size:
        extrapolation = _clamp(sample_size / float(simulation.horizon_trades))

    # Seed stability is only claimable when the simulation ran enough paths for
    # the seed not to dominate the answer.
    seed_stability = _clamp(simulation.iterations / 10_000.0) if simulation.iterations else None

    coverage = _clamp(coverage_pct / 100.0) if coverage_pct is not None else None
    freshness = _clamp(
        market.data_quality.freshness_score if market is not None else quality.freshness_score
    )

    passport = UncertaintyPassport(
        identity_confidence=_clamp(identity_score),
        reconciliation_confidence=_clamp(reconciliation),
        data_completeness=_clamp(quality.completeness_score),
        freshness=freshness,
        instrument_attribution=attribution,
        sample_adequacy=sample,
        regime_coverage=regime,
        extrapolation_distance=extrapolation,
        seed_stability=seed_stability,
        model_agreement=_clamp(bot.deferred_loss.mark_coverage),
        evidence_coverage=coverage,
    )

    scores = passport.component_scores()
    overall = sum(scores.values()) / len(scores) if scores else None
    reliability = (
        "HIGH"
        if overall is not None and overall >= 0.8
        else "MEDIUM"
        if overall is not None and overall >= 0.5
        else "LOW"
        if overall is not None
        else "UNKNOWN"
    )

    reasons: List[str] = list(limitations or [])
    if sample_size < 20:
        reasons.append(
            f"Sample of {sample_size} closed trades is below the 20-trade floor "
            "for a strong behavioral claim"
        )
    if coverage is not None and coverage < 0.8:
        reasons.append("Market coverage is below the coverage target for this bot")
    if regime is not None and regime < 0.8:
        reasons.append("Part of the closed trades could not be mapped to a market phase")
    if not strategy.tested_in_downtrend:
        reasons.append("No downtrend sample exists, so downtrend behavior is undetermined")
    if reconciliation is not None and reconciliation < 0.9:
        reasons.append(f"Ledger reconciliation status is {reconciliation_status}")
    if extrapolation is not None and extrapolation < 0.5:
        reasons.append(
            "The simulated horizon reaches more than twice as far as the observed "
            "sample, so its tail is an extrapolation rather than a measurement"
        )
    if seed_stability is not None and seed_stability < 0.5:
        reasons.append(
            "Too few simulated paths for the result to be independent of the seed"
        )

    return passport.model_copy(
        update={
            "overall_reliability": reliability,
            "abstention_reasons": list(dict.fromkeys(reasons)),
        }
    )


def _cap_wording(level: str, passport: UncertaintyPassport) -> str:
    """Lower a wording level when the passport does not support it.

    The engine may always say less than it measured; this function is the only
    place allowed to decide it may say more.
    """
    if passport.overall_reliability == "HIGH":
        return level
    ceiling = "CONSISTENT_WITH" if passport.overall_reliability == "MEDIUM" else "SUGGESTS"
    if level in ("DATA_DOES_NOT_ESTABLISH", "CANNOT_DETERMINE"):
        # A negative/abstaining statement is a statement about missing evidence
        # and does not get weaker when other evidence is thin.
        return level
    return level if WORDING_LEVELS.index(level) <= WORDING_LEVELS.index(ceiling) else ceiling


def build_claims(
    bot: BotResult,
    market: Optional[MarketResult],
    passport: UncertaintyPassport,
) -> List[AnalysisClaim]:
    """Derive every claim the deterministic evidence supports.

    Each rule states its own supporting and contradicting evidence, so a
    consumer never has to re-derive why a claim exists.
    """
    deferred = bot.deferred_loss
    behavior = bot.behavioral_observations
    strategy = bot.strategy_observations
    performance = bot.performance
    sample_size = bot.trade_statistics.sample_size
    uncertainty = {
        "sample_size": sample_size,
        "overall_reliability": passport.overall_reliability,
        "regime_coverage": passport.regime_coverage,
    }
    claims: List[AnalysisClaim] = []

    def add(
        claim_id: str,
        claim_type: str,
        statement_key: str,
        strength: str,
        wording: str,
        *,
        supporting: List[str],
        contradicting: Optional[List[str]] = None,
        assumptions: Optional[List[str]] = None,
        falsifiers: Optional[List[str]] = None,
    ) -> None:
        claims.append(
            AnalysisClaim(
                claim_id=claim_id,
                claim_type=claim_type,
                statement_key=statement_key,
                strength=strength,
                supporting_evidence=supporting,
                contradicting_evidence=list(contradicting or []),
                assumptions=list(assumptions or []),
                uncertainty=dict(uncertainty),
                falsifiers=list(falsifiers or []),
                allowed_wording_level=_cap_wording(wording, passport),
            )
        )

    if deferred.turns_unprofitable_when_marked:
        add(
            "claim.marked_book_reversal",
            "RISK_STATE",
            "MARKED_BOOK_REVERSES_CLOSED_BOOK",
            "STRONG" if deferred.mark_coverage >= 0.8 else "INDICATIVE",
            "DATA_SHOWS" if deferred.mark_coverage >= 0.8 else "SUGGESTS",
            supporting=["bot.deferred_loss", "bot.current_state"],
            assumptions=[
                "Open positions are marked at the public mark price supplied with the snapshot"
            ],
            falsifiers=[
                "Full position attribution shows the marked loss is not representative",
                "The open positions close at or above their entry price",
            ],
        )

    if deferred.never_realized_a_loss and deferred.closed_loss_count == 0:
        add(
            "claim.no_realized_loss",
            "BEHAVIOR",
            "NEVER_REALIZED_A_LOSS",
            "OBSERVED",
            "DATA_SHOWS",
            supporting=["bot.deferred_loss"],
            contradicting=["bot.reconciliation"] if deferred.warnings else [],
            falsifiers=["A closed losing trade appears in the ledger"],
        )

    if behavior.averaging_down_detected:
        add(
            "claim.averaging_down",
            "BEHAVIOR",
            "ADDS_TO_LOSING_POSITIONS",
            "STRONG" if sample_size >= 20 else "INDICATIVE",
            "DATA_SHOWS" if sample_size >= 20 else "SUGGESTS",
            supporting=["bot.behavior.averaging_down"],
            falsifiers=["Trade sequencing does not confirm adverse re-entry once symbol and side are controlled for"],
        )
    elif behavior.averaging_down_suspected:
        add(
            "claim.averaging_down_suspected",
            "BEHAVIOR",
            "MAY_ADD_TO_LOSING_POSITIONS",
            "WEAK",
            "SUGGESTS",
            supporting=["bot.behavior.averaging_down"],
            falsifiers=["A complete ledger shows no adverse re-entry"],
        )

    if behavior.size_escalation_excess >= 0.25:
        add(
            "claim.size_escalation",
            "BEHAVIOR",
            "RAISES_SIZE_AFTER_LOSSES",
            "STRONG" if behavior.size_escalation_excess >= 0.5 else "INDICATIVE",
            "DATA_SHOWS" if behavior.size_escalation_excess >= 0.5 else "CONSISTENT_WITH",
            supporting=["bot.behavior.size_escalation_excess"],
            assumptions=["Size after wins is the control group for size after losses"],
            falsifiers=["The excess disappears once symbol and market phase are controlled for"],
        )

    if not strategy.tested_in_downtrend:
        add(
            "claim.downtrend_untested",
            "COVERAGE",
            "DOWNTREND_UNTESTED",
            "OBSERVED",
            "DATA_DOES_NOT_ESTABLISH",
            supporting=["bot.strategy.phase_breakdown"],
            falsifiers=["A verified downtrend sample enters the dataset"],
        )

    if strategy.regime_dependence_pct is not None and strategy.regime_dependence_pct >= 50.0:
        add(
            "claim.regime_dependence",
            "COVERAGE",
            "RESULT_CONCENTRATED_IN_ONE_REGIME",
            "INDICATIVE",
            "CONSISTENT_WITH",
            supporting=["bot.strategy.phase_breakdown"],
            falsifiers=["Profit is spread evenly once every phase has a comparable sample"],
        )

    if sample_size < 20:
        add(
            "claim.sample_too_small",
            "UNCERTAINTY",
            "SAMPLE_TOO_SMALL_FOR_BEHAVIORAL_CLAIM",
            "OBSERVED",
            "CANNOT_DETERMINE",
            supporting=["bot.data_quality"],
            falsifiers=["The closed-trade sample grows past the 20-trade floor"],
        )

    if performance.profit_factor is not None and sample_size >= 20:
        add(
            "claim.closed_book_profitability",
            "PERFORMANCE",
            "CLOSED_BOOK_PROFIT_FACTOR_MEASURED",
            "OBSERVED",
            "DATA_SHOWS",
            supporting=["bot.performance"],
            contradicting=["bot.deferred_loss"] if deferred.turns_unprofitable_when_marked else [],
            assumptions=["Closed trades only; open exposure is excluded by construction"],
            falsifiers=["The ledger is shown to be incomplete for the measured window"],
        )

    if market is None:
        add(
            "claim.market_unavailable",
            "COVERAGE",
            "PRIMARY_MARKET_UNAVAILABLE",
            "OBSERVED",
            "CANNOT_DETERMINE",
            supporting=["bot.identity"],
            falsifiers=["A public market feed for the traded instrument becomes available"],
        )

    claims.sort(key=lambda claim: claim.claim_id)
    return claims


# --------------------------------------------------------------------------- #
# User questions (design section 5's `user_questions`, section 3.2's "identify
# which pre-defined additional analysis the user may request next")
#
# A question is derived from what the evidence is MISSING, and each one names
# the deterministic analysis that would answer it. It is never a suggestion to
# act: "should I copy this bot" is not a question this engine asks or answers.
# --------------------------------------------------------------------------- #

# Analyses a question may point at. A question naming anything outside this set
# would be asking for work the engine cannot actually perform.
AVAILABLE_ANALYSES = (
    "RERUN_WITH_LARGER_SAMPLE",
    "UNTESTED_REGIME_SCENARIO",
    "POSITION_ATTRIBUTION",
    "LEDGER_RECONCILIATION",
    "MARKET_COVERAGE_EXPANSION",
    "DEFERRED_LOSS_BREAKDOWN",
)


class UserQuestion(BaseModel):
    """A question the current evidence leaves open, and how to close it."""

    model_config = ConfigDict(extra="forbid")

    question_id: str
    # Phrased as a question about the EVIDENCE, never about what to do.
    question: str
    why_it_is_open: str
    answered_by: str
    evidence_ids: List[str] = Field(default_factory=list)
    blocked_reason: Optional[str] = None


def build_user_questions(
    bot: BotResult,
    market: Optional[MarketResult],
    passport: UncertaintyPassport,
    *,
    coverage_pct: Optional[float] = None,
) -> List[UserQuestion]:
    """Derive the open questions this bot's evidence actually raises."""
    strategy = bot.strategy_observations
    deferred = bot.deferred_loss
    state = bot.current_state
    sample_size = bot.trade_statistics.sample_size
    questions: List[UserQuestion] = []

    if sample_size < 20:
        questions.append(
            UserQuestion(
                question_id="question.sample_size",
                question="Would a larger sample change the behavioural findings?",
                why_it_is_open=(
                    f"{sample_size} closed trades is below the 20-trade floor this "
                    "engine requires before it will state a behavioural finding strongly"
                ),
                answered_by="RERUN_WITH_LARGER_SAMPLE",
                evidence_ids=["bot.data_quality"],
                blocked_reason="Needs more closed trades than the bot has produced",
            )
        )

    for regime in strategy.untested_phases:
        questions.append(
            UserQuestion(
                question_id=f"question.untested_regime.{regime}",
                question=f"How does this bot behave in {regime}?",
                why_it_is_open="No closed trade was opened during this market phase",
                answered_by="UNTESTED_REGIME_SCENARIO",
                evidence_ids=["bot.strategy.phase_breakdown"],
                blocked_reason=(
                    "The bot has never traded this phase, so no observation exists "
                    "to condition on"
                ),
            )
        )

    if state.open_positions_count and state.attributed_positions_count < state.open_positions_count:
        unattributed = state.open_positions_count - state.attributed_positions_count
        questions.append(
            UserQuestion(
                question_id="question.position_attribution",
                question="Do the unattributed open positions belong to this bot?",
                why_it_is_open=(
                    f"{unattributed} of {state.open_positions_count} open positions "
                    "could not be tied to this bot's own ledger universe"
                ),
                answered_by="POSITION_ATTRIBUTION",
                evidence_ids=["bot.current_state"],
            )
        )

    if deferred.mark_coverage < 1.0 and deferred.open_loss:
        questions.append(
            UserQuestion(
                question_id="question.deferred_loss_coverage",
                question="How much of the open loss is actually measured?",
                why_it_is_open=(
                    f"Only {deferred.mark_coverage * 100:.0f}% of open exposure could "
                    "be marked, so the marked state is a partial view"
                ),
                answered_by="DEFERRED_LOSS_BREAKDOWN",
                evidence_ids=["bot.deferred_loss"],
            )
        )

    if str(getattr(bot.reconciliation, "status", "")).upper() not in (
        "MATCH",
        "WITHIN_TOLERANCE",
    ):
        questions.append(
            UserQuestion(
                question_id="question.reconciliation",
                question="Why do the reported and ledger PnL disagree?",
                why_it_is_open=(
                    f"Reconciliation status is {bot.reconciliation.status}"
                ),
                answered_by="LEDGER_RECONCILIATION",
                evidence_ids=["bot.reconciliation"],
            )
        )

    if coverage_pct is not None and coverage_pct < 80.0:
        questions.append(
            UserQuestion(
                question_id="question.market_coverage",
                question="What do the unresolved markets add to the picture?",
                why_it_is_open=(
                    f"Observed market coverage is {coverage_pct:.0f}%, below the "
                    "coverage target"
                ),
                answered_by="MARKET_COVERAGE_EXPANSION",
                evidence_ids=["market.primary"],
            )
        )

    questions.sort(key=lambda q: q.question_id)
    return questions
