"""Turn Logic 1's observations into the three answers a reader actually wants.

Why this exists: the regime report listed trend, volatility, liquidity and flow
side by side and left the reader to combine them. The questions being asked of
this step are narrower -- where is the risk, where is something growing, where is
it steady -- so the evidence for each is collected explicitly and the strongest
one names the market's posture.

Every flag carries the number that raised it. A market missing the evidence for a
question scores nothing on it rather than being assumed calm.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

# Thresholds are stated here rather than inline so a reader can argue with them.
HIGH_VOL_PERCENTILE = 80.0
CALM_VOL_PERCENTILE = 50.0
CROWDED_LONG_SHORT = 2.5
STRETCHED_FUNDING_Z = 2.0
THIN_DEPTH_USD = 200_000.0
DEEP_DEPTH_USD = 1_000_000.0
COSTLY_SLIPPAGE_PCT = 0.5
RANGE_EDGE_PCT = 15.0
HIGH_BETA = 1.5
OI_EXPANSION_PCT = 1.0

POSTURE_RISK = "RISK"
POSTURE_GROWTH = "GROWTH"
POSTURE_STABLE = "STABLE"
POSTURE_UNCLEAR = "INSUFFICIENT EVIDENCE"

# Evidence is weighted, not counted: a book that cannot absorb a 50k exit is a
# different order of problem from a mild downtrend, and counting them equally let
# one soft flag outrank three strong ones.
SEVERE = 2
MODERATE = 1


@dataclass
class MarketPosture:
    posture: str
    risk_flags: List[str] = field(default_factory=list)
    growth_flags: List[str] = field(default_factory=list)
    stability_flags: List[str] = field(default_factory=list)
    risk_score: int = 0
    growth_score: int = 0
    stability_score: int = 0

    @property
    def headline(self) -> str:
        driver = {
            POSTURE_RISK: self.risk_flags,
            POSTURE_GROWTH: self.growth_flags,
            POSTURE_STABLE: self.stability_flags,
        }.get(self.posture, [])
        return f"{self.posture}: {driver[0]}" if driver else self.posture


def _num(value: Optional[float]) -> Optional[float]:
    return value if isinstance(value, (int, float)) else None


def assess(market) -> MarketPosture:
    structure = market.structure_state
    liquidity = market.liquidity_state
    flow = market.orderflow_state
    derivatives = market.derivatives_state
    macro = market.macro_state

    risk: List[str] = []
    growth: List[str] = []
    stable: List[str] = []
    scores = {"risk": 0, "growth": 0, "stability": 0}

    def note(bucket: List[str], key: str, text: str, weight: int) -> None:
        bucket.append(text)
        scores[key] += weight

    vol_pct = _num(getattr(structure, "volatility_percentile", None))
    trend = getattr(structure, "trend_state", "UNKNOWN")
    vol_state = getattr(structure, "volatility_state", "UNKNOWN")

    if vol_state == "HIGH" or (vol_pct is not None and vol_pct >= HIGH_VOL_PERCENTILE):
        label = (
            f"high volatility (percentile {vol_pct:.0f})"
            if vol_pct is not None
            else "high volatility"
        )
        note(risk, "risk", label, SEVERE)
    elif vol_pct is not None and vol_pct <= CALM_VOL_PERCENTILE:
        note(stable, "stability", f"low volatility (percentile {vol_pct:.0f})", SEVERE)

    if trend == "BEARISH":
        note(risk, "risk", "downtrend", MODERATE)
    elif trend == "BULLISH":
        note(growth, "growth", "uptrend", SEVERE)
    elif trend in ("NEUTRAL", "RANGING"):
        note(stable, "stability", "sideways price action", MODERATE)

    position = _num(getattr(structure, "range_position_pct", None))
    if position is not None and (
        position <= RANGE_EDGE_PCT or position >= 100.0 - RANGE_EDGE_PCT
    ):
        note(
            risk,
            "risk",
            f"price sitting at the edge of its range ({position:.0f}% of range)",
            MODERATE,
        )

    depth = _num(getattr(liquidity, "total_depth_02_usd", None))
    tier = getattr(liquidity, "state_tier", None)
    tier_name = getattr(tier, "value", tier)
    if tier_name in ("ILLIQUID", "THIN") or (
        depth is not None and depth < THIN_DEPTH_USD
    ):
        label = (
            f"thin liquidity ({depth:,.0f} USD within ±0.2%)"
            if depth is not None
            else "thin liquidity"
        )
        note(risk, "risk", label, SEVERE)
    elif depth is not None and depth >= DEEP_DEPTH_USD:
        note(
            stable,
            "stability",
            f"deep order book ({depth:,.0f} USD within ±0.2%)",
            SEVERE,
        )

    slippage = _num(getattr(liquidity, "estimated_slippage_50k_pct", None))
    if slippage is not None and slippage >= COSTLY_SLIPPAGE_PCT:
        note(risk, "risk", f"estimated slippage on a 50k order {slippage:.2f}%", SEVERE)

    bias = getattr(flow, "flow_bias", "UNKNOWN")
    if bias == "BUY_PRESSURE":
        note(growth, "growth", "active buy pressure", MODERATE)
    elif bias == "SELL_PRESSURE":
        note(risk, "risk", "active sell pressure", MODERATE)
    elif bias == "NEUTRAL":
        note(stable, "stability", "balanced two-way flow", MODERATE)

    if derivatives is not None:
        ls = _num(getattr(derivatives, "long_short_ratio", None))
        if ls is not None and (
            ls >= CROWDED_LONG_SHORT or ls <= 1 / CROWDED_LONG_SHORT
        ):
            side = "long" if ls >= CROWDED_LONG_SHORT else "short"
            note(
                risk,
                "risk",
                f"positioning crowded on one side ({side}, L/S ratio {ls:.2f})",
                SEVERE,
            )

        funding_z = _num(getattr(derivatives, "funding_zscore", None))
        if funding_z is not None and abs(funding_z) >= STRETCHED_FUNDING_Z:
            note(risk, "risk", f"funding stretched ({funding_z:+.1f}σ)", SEVERE)

        delta_oi = _num(getattr(derivatives, "delta_oi_pct", None))
        if delta_oi is not None and delta_oi >= OI_EXPANSION_PCT:
            note(growth, "growth", f"open interest expanding ({delta_oi:+.1f}%)", MODERATE)

    beta = _num(getattr(macro, "btc_beta", None))
    if beta is not None and beta >= HIGH_BETA:
        note(
            risk,
            "risk",
            f"high beta to BTC ({beta:.2f}), amplifying broad market shocks",
            MODERATE,
        )

    best = max(scores.values())
    if best == 0:
        posture = POSTURE_UNCLEAR
    elif scores["risk"] == best:
        # Ties go to risk: a market that reads both risky and calm is the one
        # worth flagging, not the one worth reassuring anybody about.
        posture = POSTURE_RISK
    elif scores["growth"] == best:
        posture = POSTURE_GROWTH
    else:
        posture = POSTURE_STABLE

    return MarketPosture(
        posture,
        risk,
        growth,
        stable,
        scores["risk"],
        scores["growth"],
        scores["stability"],
    )
