"""Out-of-sample stability of an observed bot ledger.

What this is, precisely
-----------------------
A strategy backtester validates by re-fitting parameters on an in-sample window
and re-running the *same strategy* out-of-sample. NoraBT has no strategy object
to re-run: it observes a live bot's closed trades after the fact. So the honest
analogue -- and the only one the data supports -- is a **holdout validation of
observed performance**:

    split the closed-trade ledger chronologically, measure the same metrics on
    the early part and the late part, and report how far the late part departs
    from the early one.

That answers the question overfitting actually poses to a reader of this
product: *did what the early trades showed keep being true later, or is the
headline number carried by one window?* It does NOT claim the bot was
re-optimized, and nothing here is presented as a forecast.

The fold geometry and the accept/reject gate shape follow the walk-forward
runner in the sibling `nora` studio pipeline (`backend/studio_pipeline/wfa.py`)
so the two products grade stability the same way. The metrics are computed here
from realized PnL only; open positions never enter, exactly as in the rest of
the closed-book path.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from Agent.backend.bot.mcp.schemas.bot_result import BotResult, TradeLedgerItem


# Version of the holdout-validation method (fold geometry, gate thresholds).
METHODOLOGY_VERSION = "validation.v1"


# A fold whose test side holds fewer than this many trades cannot support a
# profit-factor comparison; it is reported, but graded UNRELIABLE.
MIN_FOLD_TRADES = 5

# Below this total the ledger cannot be split at all without both sides being
# noise. Stated as an explicit abstention rather than a silent skip.
MIN_LEDGER_FOR_SPLIT = 20


class WindowMetrics(BaseModel):
    """Closed-book metrics over one contiguous slice of the ledger."""

    model_config = ConfigDict(extra="forbid")

    trades: int = Field(default=0, ge=0)
    total_pnl: float = 0.0
    win_rate: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    profit_factor: Optional[float] = Field(default=None, ge=0.0)
    expectancy: Optional[float] = None
    max_drawdown_pct: Optional[float] = Field(default=None, ge=0.0)
    start_ms: Optional[int] = Field(default=None, ge=0)
    end_ms: Optional[int] = Field(default=None, ge=0)


class ValidationFold(BaseModel):
    """One in-sample / out-of-sample pair over the observed ledger."""

    model_config = ConfigDict(extra="forbid")

    fold_index: int = Field(..., ge=0)
    in_sample: WindowMetrics
    out_of_sample: WindowMetrics
    # OOS / IS for the headline metric. >1 means the later window did better.
    profit_factor_ratio: Optional[float] = Field(default=None, ge=0.0)
    win_rate_delta_pct: Optional[float] = None
    oos_profitable: Optional[bool] = None
    reliability: str = "UNRELIABLE"
    notes: List[str] = Field(default_factory=list)


class OutOfSampleValidation(BaseModel):
    """Holdout validation of observed performance across the ledger."""

    model_config = ConfigDict(extra="forbid")

    method: str = "CHRONOLOGICAL_HOLDOUT"
    status: str = "UNKNOWN"
    folds: List[ValidationFold] = Field(default_factory=list)
    folds_evaluated: int = Field(default=0, ge=0)
    oos_profitable_folds: int = Field(default=0, ge=0)
    median_profit_factor_ratio: Optional[float] = Field(default=None, ge=0.0)
    worst_oos_drawdown_pct: Optional[float] = Field(default=None, ge=0.0)
    # A single word a report can show: did later trades hold up?
    stability_grade: str = "UNKNOWN"
    gate_checks: Dict[str, Any] = Field(default_factory=dict)
    gate_passed: Optional[bool] = None
    evidence_ids: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


def _window_metrics(trades: Sequence[TradeLedgerItem]) -> WindowMetrics:
    if not trades:
        return WindowMetrics()
    pnls = [float(trade.realized_pnl) for trade in trades]
    wins = [value for value in pnls if value > 0.0]
    losses = [value for value in pnls if value < 0.0]
    gross_profit = sum(wins)
    gross_loss = -sum(losses)

    # Profit factor is undefined without a realized loss. Reporting a huge
    # number (or infinity) there would read as an extraordinary edge when it
    # only means "this window happens to contain no losing trade".
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0.0 else None

    equity = 0.0
    peak = 0.0
    max_dd_abs = 0.0
    for value in pnls:
        equity += value
        peak = max(peak, equity)
        max_dd_abs = max(max_dd_abs, peak - equity)
    max_dd_pct = (max_dd_abs / peak * 100.0) if peak > 0.0 else None

    return WindowMetrics(
        trades=len(trades),
        total_pnl=sum(pnls),
        win_rate=len(wins) / len(pnls) * 100.0,
        profit_factor=profit_factor,
        expectancy=sum(pnls) / len(pnls),
        max_drawdown_pct=max_dd_pct,
        start_ms=min(trade.close_time for trade in trades),
        end_ms=max(trade.close_time for trade in trades),
    )


def _grade(ratio: Optional[float], oos_trades: int) -> str:
    if oos_trades < MIN_FOLD_TRADES or ratio is None:
        return "UNRELIABLE"
    if ratio >= 0.8:
        return "STABLE"
    if ratio >= 0.5:
        return "DEGRADED"
    return "SEVERELY_DEGRADED"


def build_folds(
    ledger: Sequence[TradeLedgerItem], *, fold_count: int = 4
) -> List[ValidationFold]:
    """Expanding-window folds: each fold trains on the past, tests on what came next.

    An expanding window is used rather than a rolling one because the ledger is
    short; a rolling window would leave each in-sample side too small to be a
    meaningful baseline.
    """
    ordered = sorted(ledger, key=lambda trade: trade.close_time)
    total = len(ordered)
    if total < MIN_LEDGER_FOR_SPLIT:
        return []

    folds: List[ValidationFold] = []
    # Reserve the first 40% as the initial training base, then step forward.
    base = max(MIN_FOLD_TRADES, int(total * 0.4))
    remaining = total - base
    if remaining < MIN_FOLD_TRADES:
        return []
    step = max(MIN_FOLD_TRADES, remaining // max(1, fold_count))

    index = 0
    split = base
    while split < total and index < fold_count:
        test_end = min(total, split + step)
        if test_end - split < MIN_FOLD_TRADES:
            break
        in_sample = _window_metrics(ordered[:split])
        out_of_sample = _window_metrics(ordered[split:test_end])

        ratio: Optional[float] = None
        if in_sample.profit_factor and out_of_sample.profit_factor is not None:
            ratio = out_of_sample.profit_factor / in_sample.profit_factor

        notes: List[str] = []
        if out_of_sample.profit_factor is None:
            notes.append(
                "The out-of-sample window contains no losing trade, so its "
                "profit factor is undefined rather than favourable"
            )
        if out_of_sample.trades < MIN_FOLD_TRADES:
            notes.append("The out-of-sample window is too small to grade")

        win_delta = (
            out_of_sample.win_rate - in_sample.win_rate
            if out_of_sample.win_rate is not None and in_sample.win_rate is not None
            else None
        )

        folds.append(
            ValidationFold(
                fold_index=index,
                in_sample=in_sample,
                out_of_sample=out_of_sample,
                profit_factor_ratio=ratio,
                win_rate_delta_pct=win_delta,
                oos_profitable=out_of_sample.total_pnl > 0.0,
                reliability=_grade(ratio, out_of_sample.trades),
                notes=notes,
            )
        )
        index += 1
        split = test_end

    return folds


def _median(values: List[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def build_out_of_sample_validation(bot: BotResult) -> OutOfSampleValidation:
    """Validate observed performance on later trades against earlier trades."""
    ledger = list(bot.trade_ledger_summary or [])
    assumptions = [
        "Closed trades only; open positions are excluded by construction",
        "Windows are split chronologically by close time, never re-ordered",
        "This measures stability of observed results, not a re-optimized strategy",
    ]

    if len(ledger) < MIN_LEDGER_FOR_SPLIT:
        return OutOfSampleValidation(
            status="INSUFFICIENT_SAMPLE",
            stability_grade="UNKNOWN",
            evidence_ids=["bot.trade_ledger_summary"],
            assumptions=assumptions,
            limitations=[
                f"A ledger of {len(ledger)} closed trades cannot be split into "
                f"in-sample and out-of-sample windows (minimum {MIN_LEDGER_FOR_SPLIT})"
            ],
        )

    folds = build_folds(ledger)
    if not folds:
        return OutOfSampleValidation(
            status="INSUFFICIENT_SAMPLE",
            stability_grade="UNKNOWN",
            evidence_ids=["bot.trade_ledger_summary"],
            assumptions=assumptions,
            limitations=[
                "The ledger could not be split into windows large enough to compare"
            ],
        )

    gradable = [fold for fold in folds if fold.reliability != "UNRELIABLE"]
    ratios = [
        fold.profit_factor_ratio
        for fold in gradable
        if fold.profit_factor_ratio is not None
    ]
    median_ratio = _median(ratios)
    profitable = sum(1 for fold in folds if fold.oos_profitable)
    worst_dd = max(
        (
            fold.out_of_sample.max_drawdown_pct
            for fold in folds
            if fold.out_of_sample.max_drawdown_pct is not None
        ),
        default=None,
    )

    if not gradable:
        grade = "UNKNOWN"
    elif median_ratio is None:
        grade = "UNKNOWN"
    else:
        grade = _grade(median_ratio, min(f.out_of_sample.trades for f in gradable))

    gate_checks = {
        "majority_of_windows_profitable": {
            "label": f"Out-of-sample windows in profit ({profitable}/{len(folds)})",
            "required": "more than half",
            "actual": profitable,
            "passed": profitable * 2 > len(folds),
        },
        "performance_holds_up": {
            "label": "Median out-of-sample / in-sample profit factor",
            "required": ">= 0.8",
            "actual": median_ratio,
            "passed": median_ratio is not None and median_ratio >= 0.8,
        },
        "enough_gradable_windows": {
            "label": f"Gradable windows ({len(gradable)}/{len(folds)})",
            "required": ">= 2",
            "actual": len(gradable),
            "passed": len(gradable) >= 2,
        },
    }

    limitations: List[str] = []
    if len(gradable) < len(folds):
        limitations.append(
            f"{len(folds) - len(gradable)} of {len(folds)} windows were too small "
            "or had no losing trade, so they are shown but not graded"
        )
    if getattr(bot.reconciliation, "ledger_truncated", False):
        limitations.append(
            "The ledger is truncated, so the earliest window may not be the "
            "bot's earliest activity"
        )

    return OutOfSampleValidation(
        status="EVALUATED",
        folds=folds,
        folds_evaluated=len(folds),
        oos_profitable_folds=profitable,
        median_profit_factor_ratio=median_ratio,
        worst_oos_drawdown_pct=worst_dd,
        stability_grade=grade,
        gate_checks=gate_checks,
        gate_passed=all(check["passed"] for check in gate_checks.values()),
        evidence_ids=["bot.trade_ledger_summary"],
        assumptions=assumptions,
        limitations=limitations,
    )
