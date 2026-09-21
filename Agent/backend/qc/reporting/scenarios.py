"""Scenario Laboratory: named, bounded what-ifs over the observed ledger.

Three rules hold everywhere in this module.

1. **A scenario is not a forecast.** Every result carries the assumptions that
   produced it and is labelled `SIMULATED`, never `OBSERVED`. Nothing here says
   what the bot *will* do.
2. **A scenario is conditioned, not global.** "How does this bot do in a
   downtrend" is answered from the trades that actually happened in a
   downtrend. When there are none, the answer is `UNTESTED` -- not a number
   borrowed from another regime.
3. **A point estimate without an interval is not reported.** Each scenario
   resamples the conditioning trades to give a band, so a reader can see how
   much of the headline is sample noise.

Resampling uses the stationary bootstrap the engine already publishes
(Politis & Romano, 1994; expected block length n^(1/3), circular indices), so
this module states the same statistical method the rest of the report cites.
The percentile/risk-of-ruin presentation follows the sibling `nora` studio
pipeline's Monte Carlo contract so the two products read the same way.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from Agent.backend.market.schemas.market_result import MarketResult
from Agent.backend.mcp.schemas.bot_result import BotResult, TradeLedgerItem


# v2, not v1: regime scenarios used to RECONSTRUCT a PnL series from a phase
# summary's expectancy. They now resample the real trades carrying that phase
# label. Numbers from a v1 dossier are therefore not directly comparable with
# a v2 one, which is exactly what this version string exists to signal.
METHODOLOGY_VERSION = "scenarios.v2"


# Fewer conditioning trades than this and a resampled band is meaningless: the
# bootstrap would keep redrawing the same handful of numbers.
MIN_SCENARIO_TRADES = 5

DEFAULT_ITERATIONS = 2000
DEFAULT_SEED = 42

# Drawdown past this share of the conditioning window's own peak is what the
# ruin probability counts. It is a stated threshold, not a prediction of
# account closure.
RUIN_DRAWDOWN_PCT = 30.0


class ScenarioBand(BaseModel):
    """A resampled distribution, reported as percentiles rather than one number."""

    model_config = ConfigDict(extra="forbid")

    p05: Optional[float] = None
    p25: Optional[float] = None
    p50: Optional[float] = None
    p75: Optional[float] = None
    p95: Optional[float] = None


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    name: str
    family: str
    # SIMULATED when a band was produced; UNTESTED when the conditioning set is
    # empty; INSUFFICIENT when it exists but is too small to resample.
    status: str = "SIMULATED"
    conditioning: Dict[str, Any] = Field(default_factory=dict)
    sample_size: int = Field(default=0, ge=0)
    expectancy: Optional[ScenarioBand] = None
    total_pnl: Optional[ScenarioBand] = None
    max_drawdown_pct: Optional[ScenarioBand] = None
    probability_of_loss_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    probability_of_ruin_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    central_estimate: Optional[float] = None
    assumptions: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class ScenarioLaboratory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: str = "STATIONARY_BOOTSTRAP"
    iterations: int = Field(default=DEFAULT_ITERATIONS, ge=0)
    seed: int = DEFAULT_SEED
    scenarios: List[Scenario] = Field(default_factory=list)
    untested_conditions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


def _band(values: np.ndarray) -> ScenarioBand:
    return ScenarioBand(
        p05=round(float(np.percentile(values, 5)), 6),
        p25=round(float(np.percentile(values, 25)), 6),
        p50=round(float(np.percentile(values, 50)), 6),
        p75=round(float(np.percentile(values, 75)), 6),
        p95=round(float(np.percentile(values, 95)), 6),
    )


def _stationary_resample(
    pnls: np.ndarray, iterations: int, horizon: int, rng: np.random.Generator
) -> np.ndarray:
    """Circular stationary bootstrap with geometric block lengths.

    Restart probability is 1/L with L = n**(1/3), the standard rate; indices
    wrap modulo n so the resampled series is stationary. This mirrors the
    engine's own `_simulate_horizon`, deliberately: the report cites one
    method, so this module must not quietly use a different one.
    """
    count = len(pnls)
    block_length = max(1.0, float(count) ** (1.0 / 3.0))
    restart_p = 1.0 / block_length

    idx = rng.integers(0, count, size=iterations)
    out = np.empty((iterations, horizon), dtype=np.float64)
    for step in range(horizon):
        out[:, step] = pnls[idx]
        restart = rng.random(iterations) < restart_p
        idx = np.where(restart, rng.integers(0, count, size=iterations), (idx + 1) % count)
    return out


def _simulate(
    pnls: np.ndarray,
    *,
    iterations: int,
    rng: np.random.Generator,
) -> Dict[str, Any]:
    horizon = len(pnls)
    paths = _stationary_resample(pnls, iterations, horizon, rng)

    totals = paths.sum(axis=1)
    expectancies = paths.mean(axis=1)

    equity = np.cumsum(paths, axis=1)
    peaks = np.maximum.accumulate(np.hstack([np.zeros((iterations, 1)), equity]), axis=1)
    drawdowns = peaks - np.hstack([np.zeros((iterations, 1)), equity])
    # Percentage of the path's own peak; a path that never rose has no
    # meaningful percentage drawdown and contributes 0 rather than a divide.
    with np.errstate(divide="ignore", invalid="ignore"):
        dd_pct = np.where(peaks > 0.0, drawdowns / np.maximum(peaks, 1e-9) * 100.0, 0.0)
    max_dd = dd_pct.max(axis=1)

    return {
        "expectancy": _band(expectancies),
        "total_pnl": _band(totals),
        "max_drawdown_pct": _band(max_dd),
        "probability_of_loss_pct": round(float((totals < 0.0).mean() * 100.0), 2),
        "probability_of_ruin_pct": round(
            float((max_dd >= RUIN_DRAWDOWN_PCT).mean() * 100.0), 2
        ),
        "central_estimate": round(float(np.percentile(totals, 50)), 6),
    }


def _pnl_array(trades: Sequence[TradeLedgerItem]) -> np.ndarray:
    return np.array([float(t.realized_pnl) for t in trades], dtype=np.float64)


def _scenario_from(
    scenario_id: str,
    name: str,
    family: str,
    pnls: np.ndarray,
    *,
    conditioning: Dict[str, Any],
    assumptions: List[str],
    evidence_ids: List[str],
    iterations: int,
    rng: np.random.Generator,
    untested_note: str,
) -> Scenario:
    if len(pnls) == 0:
        return Scenario(
            scenario_id=scenario_id,
            name=name,
            family=family,
            status="UNTESTED",
            conditioning=conditioning,
            sample_size=0,
            assumptions=assumptions,
            evidence_ids=evidence_ids,
            limitations=[untested_note],
        )
    if len(pnls) < MIN_SCENARIO_TRADES:
        return Scenario(
            scenario_id=scenario_id,
            name=name,
            family=family,
            status="INSUFFICIENT",
            conditioning=conditioning,
            sample_size=len(pnls),
            assumptions=assumptions,
            evidence_ids=evidence_ids,
            limitations=[
                f"Only {len(pnls)} trades match this condition; a resampled "
                f"interval needs at least {MIN_SCENARIO_TRADES}"
            ],
        )
    stats = _simulate(pnls, iterations=iterations, rng=rng)
    return Scenario(
        scenario_id=scenario_id,
        name=name,
        family=family,
        status="SIMULATED",
        conditioning=conditioning,
        sample_size=len(pnls),
        assumptions=assumptions,
        evidence_ids=evidence_ids,
        **stats,
    )


def build_scenario_laboratory(
    bot: BotResult,
    market: Optional[MarketResult] = None,
    *,
    iterations: int = DEFAULT_ITERATIONS,
    seed: int = DEFAULT_SEED,
) -> ScenarioLaboratory:
    """Build every scenario the observed ledger can actually condition on."""
    ledger = list(bot.trade_ledger_summary or [])
    strategy = bot.strategy_observations
    base_assumptions = [
        "Resampled from this bot's own closed trades, not from a model of the market",
        "A scenario is a conditional what-if, never a forecast",
        "Open positions are excluded; this is the closed book only",
    ]

    if not ledger:
        return ScenarioLaboratory(
            iterations=iterations,
            seed=seed,
            limitations=["No closed-trade ledger is available to condition on"],
        )

    rng = np.random.default_rng(seed)
    scenarios: List[Scenario] = []

    # ---- Family 1: the full closed book, as a baseline to compare against. --
    scenarios.append(
        _scenario_from(
            "scenario.baseline",
            "Observed book, resampled",
            "BASELINE",
            _pnl_array(ledger),
            conditioning={"filter": "ALL_CLOSED_TRADES"},
            assumptions=base_assumptions,
            evidence_ids=["bot.trade_ledger_summary"],
            iterations=iterations,
            rng=rng,
            untested_note="No closed trades are available",
        )
    )

    # ---- Family 2: regime-conditioned. -------------------------------------
    # Each trade carries the market phase it was opened in
    # (`TradeLedgerItem.market_phase`), so a regime scenario resamples the
    # REAL trades from that regime. Nothing is reconstructed from a summary.
    by_phase: Dict[str, List[TradeLedgerItem]] = {}
    for trade in ledger:
        if trade.market_phase and trade.market_phase != "UNKNOWN":
            by_phase.setdefault(trade.market_phase, []).append(trade)

    for phase in strategy.phase_breakdown:
        matched = by_phase.get(phase.phase, [])
        conditioning = {
            "regime": phase.phase,
            "observed_trades": phase.trades,
            "matched_trades": len(matched),
        }
        scenario = _scenario_from(
            f"scenario.regime.{phase.phase}",
            phase.phase,
            "REGIME",
            _pnl_array(matched),
            conditioning=conditioning,
            assumptions=base_assumptions
            + [f"Only the trades opened during {phase.phase} are resampled"],
            evidence_ids=["bot.trade_ledger_summary", "bot.strategy.phase_breakdown"],
            iterations=iterations,
            rng=rng,
            untested_note=(
                f"No closed trade carries the {phase.phase} label, so this "
                "regime cannot be simulated"
            ),
        )
        if len(matched) != phase.trades:
            # The two counts come from the same labelling pass, so a mismatch
            # means the ledger summary was truncated relative to what the
            # phase analyser saw. Say so rather than quietly resampling fewer.
            scenario = scenario.model_copy(
                update={
                    "limitations": scenario.limitations
                    + [
                        f"{phase.trades} trades were measured in this regime but "
                        f"{len(matched)} are present in the ledger summary"
                    ]
                }
            )
        scenarios.append(scenario)

    # ---- Family 3: execution stress, conditioned on observed liquidity. -----
    # Costs are charged against notional, so a trade with no recorded notional
    # cannot be stressed and the scenario says so instead of assuming zero.
    notional_known = [t for t in ledger if t.notional is not None]
    missing_notional = len(ledger) - len(notional_known)
    liquidity_tier = (
        market.liquidity_state.state_tier.value if market is not None else "UNKNOWN"
    )
    for label, cost_bps, note in (
        ("Spread 3x", 10.0, "Spread widens to three times its observed level"),
        ("Liquidity halved", 15.0, "Executable depth halves, doubling slippage"),
    ):
        scenario_id = f"scenario.execution.{label.lower().replace(' ', '_')}"
        if not notional_known:
            scenarios.append(
                Scenario(
                    scenario_id=scenario_id,
                    name=label,
                    family="EXECUTION",
                    status="UNTESTED",
                    conditioning={"liquidity_tier": liquidity_tier},
                    assumptions=base_assumptions + [note],
                    evidence_ids=["bot.trade_ledger_summary", "market.liquidity"],
                    limitations=["No trade records a notional, so execution cost cannot be applied"],
                )
            )
            continue
        stressed = _pnl_array(notional_known) - np.array(
            [float(t.notional) * cost_bps / 10_000.0 for t in notional_known],
            dtype=np.float64,
        )
        limitations = []
        if missing_notional:
            limitations.append(
                f"{missing_notional} trades record no notional and are excluded "
                "from this scenario rather than charged a guessed cost"
            )
        if liquidity_tier == "UNKNOWN":
            limitations.append(
                "Observed liquidity is unknown, so the cost multiplier is a "
                "stated assumption rather than a measured one"
            )
        scenario = _scenario_from(
            scenario_id,
            label,
            "EXECUTION",
            stressed,
            conditioning={"liquidity_tier": liquidity_tier, "cost_bps": cost_bps},
            assumptions=base_assumptions + [note, f"Cost charged at {cost_bps:.0f} bps of notional"],
            evidence_ids=["bot.trade_ledger_summary", "market.liquidity"],
            iterations=iterations,
            rng=rng,
            untested_note="No trade could be stressed",
        )
        scenarios.append(scenario.model_copy(update={"limitations": scenario.limitations + limitations}))

    # ---- Family 4: realizing the currently open loss. -----------------------
    deferred = bot.deferred_loss
    if deferred.open_loss:
        combined = np.append(_pnl_array(ledger), -float(deferred.open_loss))
        scenarios.append(
            _scenario_from(
                "scenario.realize_open_loss",
                "Open losses realized today",
                "DEFERRED_LOSS",
                combined,
                conditioning={"open_loss": deferred.open_loss, "mark_coverage": deferred.mark_coverage},
                assumptions=base_assumptions
                + [
                    "The currently open loss is closed at the supplied public mark price",
                    "No further trade occurs in this scenario",
                ],
                evidence_ids=["bot.deferred_loss"],
                iterations=iterations,
                rng=rng,
                untested_note="No open loss is recorded",
            )
        )

    untested = list(strategy.untested_phases)
    limitations: List[str] = []
    if untested:
        limitations.append(
            "Regimes with no observed trade are listed as untested and carry no scenario"
        )
    if market is None:
        limitations.append(
            "No market observation is available, so execution scenarios use "
            "stated cost assumptions rather than observed liquidity"
        )

    return ScenarioLaboratory(
        iterations=iterations,
        seed=seed,
        scenarios=scenarios,
        untested_conditions=untested,
        limitations=limitations,
    )
