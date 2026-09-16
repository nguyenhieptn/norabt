from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class EvaluationMode(str, Enum):
    """How freshness is judged.

    SNAPSHOT is the primary mode for this system: the dataset is crawled, so a
    source is judged against the dataset's own anchor (its newest observation),
    not against the wall clock. The wall-clock age is still carried so a stale
    dataset can never be presented as live.
    """

    LIVE = "LIVE"
    SNAPSHOT = "SNAPSHOT"


class SourceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    STALE = "STALE"
    MISSING = "MISSING"
    INVALID = "INVALID"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    FALLBACK = "FALLBACK"


class StalenessBudget(BaseModel):
    """Per-source tolerance, because a 1h aggregate and an order book age differently."""

    live_ms: int = Field(..., ge=0)
    snapshot_ms: int = Field(..., ge=0)

    def limit_for(self, mode: EvaluationMode) -> int:
        return self.live_ms if mode == EvaluationMode.LIVE else self.snapshot_ms


HOUR_MS = 3_600_000
MINUTE_MS = 60_000

DEFAULT_BUDGETS: Dict[str, StalenessBudget] = {
    "ohlcv_1h": StalenessBudget(live_ms=4 * HOUR_MS, snapshot_ms=6 * HOUR_MS),
    "orderbook_l2": StalenessBudget(live_ms=5 * MINUTE_MS, snapshot_ms=24 * HOUR_MS),
    "taker_flow": StalenessBudget(live_ms=2 * HOUR_MS, snapshot_ms=72 * HOUR_MS),
    "derivatives_oi": StalenessBudget(live_ms=30 * MINUTE_MS, snapshot_ms=72 * HOUR_MS),
    "sentiment": StalenessBudget(live_ms=6 * HOUR_MS, snapshot_ms=72 * HOUR_MS),
    "dex_ticks": StalenessBudget(live_ms=5 * MINUTE_MS, snapshot_ms=24 * HOUR_MS),
    "overview": StalenessBudget(live_ms=15 * MINUTE_MS, snapshot_ms=24 * HOUR_MS),
    "trade_ledger": StalenessBudget(live_ms=30 * MINUTE_MS, snapshot_ms=24 * HOUR_MS),
    "current_positions": StalenessBudget(
        live_ms=5 * MINUTE_MS, snapshot_ms=24 * HOUR_MS
    ),
}

FALLBACK_BUDGET = StalenessBudget(live_ms=15 * MINUTE_MS, snapshot_ms=24 * HOUR_MS)


def budget_for(source: str) -> StalenessBudget:
    return DEFAULT_BUDGETS.get(source, FALLBACK_BUDGET)


class SourceQuality(BaseModel):
    source: str
    status: SourceStatus
    observed_at: Optional[int] = None
    age_ms: Optional[int] = None
    wall_clock_age_ms: Optional[int] = None
    staleness_limit_ms: Optional[int] = None
    record_count: int = 0
    reason: Optional[str] = None


class DataQualitySummary(BaseModel):
    evaluation_mode: EvaluationMode = EvaluationMode.SNAPSHOT
    anchor_ms: Optional[int] = None
    dataset_age_ms: Optional[int] = None
    completeness_score: float = Field(..., ge=0.0, le=1.0)
    freshness_score: float = Field(..., ge=0.0, le=1.0)
    coherence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    overall_score: float = Field(..., ge=0.0, le=1.0)
    sources: List[SourceQuality] = Field(default_factory=list)
    missing_sources: List[str] = Field(default_factory=list)
    stale_sources: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    @property
    def is_usable(self) -> bool:
        return self.completeness_score >= 0.5 and not any(
            source.status == SourceStatus.INVALID for source in self.sources
        )


def grade_source(
    source: str,
    observed_at: Optional[int],
    anchor_ms: int,
    wall_clock_ms: int,
    mode: EvaluationMode,
    record_count: int = 0,
) -> SourceQuality:
    """Grade one source against the evaluation anchor for `mode`."""
    budget = budget_for(source)
    limit = budget.limit_for(mode)
    if observed_at is None:
        return SourceQuality(
            source=source,
            status=SourceStatus.INVALID,
            record_count=record_count,
            staleness_limit_ms=limit,
            reason="observation timestamp missing",
        )
    reference = anchor_ms if mode == EvaluationMode.SNAPSHOT else wall_clock_ms
    age_ms = max(0, reference - observed_at)
    return SourceQuality(
        source=source,
        status=SourceStatus.STALE if age_ms > limit else SourceStatus.AVAILABLE,
        observed_at=observed_at,
        age_ms=age_ms,
        wall_clock_age_ms=max(0, wall_clock_ms - observed_at),
        staleness_limit_ms=limit,
        record_count=record_count,
    )


def summarize_quality(
    sources: List[SourceQuality],
    mode: EvaluationMode,
    anchor_ms: Optional[int],
    wall_clock_ms: int,
) -> DataQualitySummary:
    applicable = [
        source for source in sources if source.status != SourceStatus.NOT_APPLICABLE
    ]
    dataset_age = max(0, wall_clock_ms - anchor_ms) if anchor_ms is not None else None
    if not applicable:
        return DataQualitySummary(
            evaluation_mode=mode,
            anchor_ms=anchor_ms,
            dataset_age_ms=dataset_age,
            completeness_score=0.0,
            freshness_score=0.0,
            coherence_score=0.0,
            overall_score=0.0,
        )

    present_states = {SourceStatus.AVAILABLE, SourceStatus.STALE, SourceStatus.FALLBACK}
    completeness = sum(source.status in present_states for source in applicable) / len(
        applicable
    )
    freshness_points = {
        SourceStatus.AVAILABLE: 1.0,
        SourceStatus.STALE: 0.25,
        SourceStatus.FALLBACK: 0.25,
        SourceStatus.MISSING: 0.0,
        SourceStatus.INVALID: 0.0,
    }
    freshness = sum(
        freshness_points.get(source.status, 0.0) for source in applicable
    ) / len(applicable)
    graded = [source for source in applicable if source.age_ms is not None]
    coherence = (
        sum(source.status == SourceStatus.AVAILABLE for source in graded) / len(graded)
        if graded
        else 0.0
    )
    overall = completeness * 0.55 + freshness * 0.30 + coherence * 0.15

    missing = [
        source.source
        for source in applicable
        if source.status in (SourceStatus.MISSING, SourceStatus.INVALID)
    ]
    stale = [
        source.source for source in applicable if source.status == SourceStatus.STALE
    ]
    warnings: List[str] = []
    if missing:
        warnings.append(f"Missing/invalid sources: {', '.join(missing)}")
    for source in applicable:
        if source.status == SourceStatus.STALE and source.age_ms is not None:
            warnings.append(
                f"Source {source.source} lags the dataset anchor by "
                f"{source.age_ms / HOUR_MS:.1f}h (budget {source.staleness_limit_ms / HOUR_MS:.1f}h)"
            )
    if mode == EvaluationMode.SNAPSHOT and dataset_age is not None:
        warnings.append(
            f"Snapshot analysis: dataset anchor is {dataset_age / HOUR_MS:.1f}h behind wall clock"
        )
    return DataQualitySummary(
        evaluation_mode=mode,
        anchor_ms=anchor_ms,
        dataset_age_ms=dataset_age,
        completeness_score=completeness,
        freshness_score=freshness,
        coherence_score=coherence,
        overall_score=overall,
        sources=sources,
        missing_sources=missing,
        stale_sources=stale,
        warnings=warnings,
    )
