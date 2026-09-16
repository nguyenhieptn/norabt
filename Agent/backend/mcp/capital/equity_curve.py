from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# pnlRatio is published rounded to 4 decimals, so equity = pnl / ratio is only
# precise when the ratio is large enough. At |ratio| >= 0.01 the rounding error
# on the derived equity stays under ~0.5%.
MIN_RELIABLE_RATIO = 0.01


class WeeklyEquityPoint(BaseModel):
    week_start_ms: int = Field(..., ge=0)
    pnl: float
    pnl_ratio: float
    start_equity: Optional[float] = Field(default=None, gt=0.0)
    end_equity: Optional[float] = None
    usable: bool = False
    reason: Optional[str] = None


class EquityCurve(BaseModel):
    """Weekly account equity reconstructed from published PnL and PnL ratio."""

    basis: str = "UNAVAILABLE"
    points: List[WeeklyEquityPoint] = Field(default_factory=list)
    usable_points: int = Field(default=0, ge=0)
    coverage_weeks: int = Field(default=0, ge=0)
    start_equity: Optional[float] = Field(default=None, gt=0.0)
    latest_equity: Optional[float] = Field(default=None, gt=0.0)
    peak_equity: Optional[float] = Field(default=None, gt=0.0)
    max_drawdown_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    implied_net_flow: Optional[float] = None
    implied_gross_flow: Optional[float] = None
    wiped_out: bool = False
    consistency: str = "UNVERIFIED"
    warnings: List[str] = Field(default_factory=list)

    @property
    def is_usable(self) -> bool:
        return self.basis == "WEEKLY_EQUITY_CURVE" and self.latest_equity is not None

    def equity_at(self, timestamp_ms: int) -> Optional[float]:
        """Account equity in force at a point in time, from observed weeks only."""
        usable = [p for p in self.points if p.usable and p.start_equity]
        if not usable:
            return None
        prior = [p for p in usable if p.week_start_ms <= timestamp_ms]
        if prior:
            return prior[-1].start_equity
        return usable[0].start_equity


class EquityCurveBuilder:
    """Build a weekly equity series; never collapse it to a single scalar."""

    @staticmethod
    def _float(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _timestamp_ms(value: Any) -> Optional[int]:
        if value in (None, ""):
            return None
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value).strip()
        if text.isdigit():
            return int(text)
        cleaned = text.replace("UTC", "").strip().replace("Z", "")
        for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(cleaned, pattern).replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue
            return int(parsed.timestamp() * 1000)
        return None

    @classmethod
    def build(cls, rows: Any) -> EquityCurve:
        if not isinstance(rows, list) or not rows:
            return EquityCurve(
                basis="UNAVAILABLE",
                warnings=["No weekly PnL history published for this bot"],
            )

        points: List[WeeklyEquityPoint] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            week = cls._timestamp_ms(row.get("beginTs", row.get("week_start")))
            pnl = cls._float(row.get("pnl", row.get("pnl_usdt")))
            ratio = cls._float(row.get("pnlRatio", row.get("pnl_ratio")))
            if week is None or pnl is None or ratio is None:
                continue

            point = WeeklyEquityPoint(week_start_ms=week, pnl=pnl, pnl_ratio=ratio)
            if abs(ratio) < MIN_RELIABLE_RATIO:
                point.reason = (
                    f"|pnlRatio| {abs(ratio):.4f} is below the {MIN_RELIABLE_RATIO} "
                    f"precision floor; equity cannot be derived reliably"
                )
            elif pnl == 0:
                point.reason = "Zero PnL carries no equity information"
            else:
                equity = pnl / ratio
                if equity > 0:
                    point.start_equity = equity
                    point.end_equity = equity + pnl
                    point.usable = True
                else:
                    point.reason = "Derived equity is not positive"
            points.append(point)

        points.sort(key=lambda p: p.week_start_ms)
        usable = [p for p in points if p.usable and p.start_equity]
        if not usable:
            return EquityCurve(
                basis="UNAVAILABLE",
                points=points,
                coverage_weeks=len(points),
                warnings=[
                    "Weekly PnL is published but no week has a ratio precise enough "
                    "to derive equity"
                ],
            )

        series: List[float] = []
        for point in usable:
            series.append(point.start_equity)
            if point.end_equity is not None:
                series.append(point.end_equity)

        peak = series[0]
        max_dd = 0.0
        for value in series:
            peak = max(peak, value)
            if peak > 0:
                max_dd = max(max_dd, (peak - value) / peak)

        # Equity not explained by trading PnL is deposits or withdrawals. Net flow
        # can cancel out across the window, so the verdict uses gross movement.
        flow = 0.0
        gross_flow = 0.0
        for previous, current in zip(usable[:-1], usable[1:]):
            expected = previous.end_equity or previous.start_equity
            step = (current.start_equity or 0.0) - (expected or 0.0)
            flow += step
            gross_flow += abs(step)

        latest = usable[-1].end_equity or usable[-1].start_equity
        warnings: List[str] = []
        skipped = [p for p in points if not p.usable]
        if skipped:
            warnings.append(
                f"{len(skipped)}/{len(points)} weekly points skipped for imprecise ratios"
            )
        consistency = "CHAINED"
        if latest and gross_flow > 0.05 * latest:
            consistency = "FLOWS_DETECTED"
            warnings.append(
                f"Implied deposits/withdrawals of {gross_flow:,.0f} USDT gross "
                f"({flow:,.0f} net) across the window; equity change is not purely "
                f"trading performance"
            )
        if max_dd >= 0.999:
            warnings.append(
                "Weekly equity reached zero at least once: this account has already "
                "been wiped out within the observed window"
            )
        return EquityCurve(
            basis="WEEKLY_EQUITY_CURVE",
            points=points,
            usable_points=len(usable),
            coverage_weeks=len(points),
            start_equity=usable[0].start_equity,
            latest_equity=latest,
            peak_equity=max(series),
            max_drawdown_pct=max_dd * 100.0,
            implied_net_flow=flow,
            implied_gross_flow=gross_flow,
            wiped_out=max_dd >= 0.999,
            consistency=consistency,
            warnings=warnings,
        )


class CapitalModel(BaseModel):
    """One capital basis for the whole assessment: historical and forward agree."""

    basis: str
    capital_at_risk: Optional[float] = Field(default=None, gt=0.0)
    reported_aum: Optional[float] = Field(default=None, ge=0.0)
    equity_curve: EquityCurve = Field(default_factory=EquityCurve)
    supports_historical_pct: bool = False
    warnings: List[str] = Field(default_factory=list)


class CapitalResolver:
    """Resolve capital once. No favourable-direction gating, no silent mixing."""

    @staticmethod
    def resolve(
        overview: Dict[str, Any], reported_aum: Optional[float]
    ) -> CapitalModel:
        curve = EquityCurveBuilder.build(overview.get("weekly_pnl_history"))
        warnings = list(curve.warnings)

        if curve.is_usable:
            if reported_aum and curve.latest_equity:
                ratio = curve.latest_equity / reported_aum
                if ratio > 2 or ratio < 0.5:
                    warnings.append(
                        f"Derived equity {curve.latest_equity:,.0f} USDT differs from reported "
                        f"AUM {reported_aum:,.0f} USDT by {ratio:.1f}x — on OKX copy trading "
                        f"AUM is copier funds, not the lead trader's own equity"
                    )
            return CapitalModel(
                basis="WEEKLY_EQUITY_CURVE",
                capital_at_risk=curve.latest_equity,
                reported_aum=reported_aum,
                equity_curve=curve,
                supports_historical_pct=True,
                warnings=warnings,
            )

        if reported_aum and reported_aum > 0:
            warnings.append(
                "No usable weekly equity curve; forward risk is measured against reported "
                "AUM and historical drawdown percentage is withheld"
            )
            return CapitalModel(
                basis="CURRENT_AUM",
                capital_at_risk=reported_aum,
                reported_aum=reported_aum,
                equity_curve=curve,
                supports_historical_pct=False,
                warnings=warnings,
            )

        warnings.append(
            "No capital figure available; capital-relative risk is unavailable"
        )
        return CapitalModel(
            basis="UNAVAILABLE",
            capital_at_risk=None,
            reported_aum=reported_aum,
            equity_curve=curve,
            supports_historical_pct=False,
            warnings=warnings,
        )
