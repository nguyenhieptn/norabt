"""Realized outcome metrics for a half of a bot's closed-trade ledger.

Every number here is computed directly from realized PnL on already-closed
trades -- nothing is simulated or projected. That mirrors the project-wide
rule that open positions never count as a result: a position that has not
closed yet has no realized outcome to measure.

`reference_capital`, when known, should be the SAME capital figure the
product's own CapitalResolver resolved for the bot as of the scoring cutoff
(see Agent.backend.research.shadow_scoring), so "PnL as % of capital" and
"drawdown %" mean the same thing here as they do inside the real score. When
it is unknown (no usable weekly equity curve and no reported AUM), every
percentage figure is reported as None rather than guessed at.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence


@dataclass(frozen=True)
class OutcomeMetrics:
    trade_count: int
    total_pnl: float
    total_pnl_pct: Optional[float]
    win_rate_pct: float
    max_drawdown_abs: float
    max_drawdown_pct: Optional[float]
    max_losing_streak: int
    has_losing_streak_5: bool
    has_losing_streak_10: bool
    collapsed: Optional[bool]
    collapse_drawdown_threshold_pct: float
    reference_capital: Optional[float]


def compute_outcome_metrics(
    trades: Sequence[Any],
    reference_capital: Optional[float] = None,
    collapse_drawdown_pct: float = 30.0,
) -> OutcomeMetrics:
    """Compute realized-outcome metrics from a sequence of closed trades.

    `trades` items need only `.close_time` and `.realized_pnl` (duck-typed so
    both TradeLedgerItem and a plain test stub work). Trades are re-sorted by
    close_time defensively; callers are expected to already pass one
    time-ordered half of a TimeSplit.
    """
    ordered = sorted(trades, key=lambda t: t.close_time)
    n = len(ordered)
    if n == 0:
        raise ValueError("no trades to measure outcomes from")

    pnls = [float(t.realized_pnl) for t in ordered]
    total_pnl = sum(pnls)
    wins = sum(1 for p in pnls if p > 0)
    win_rate_pct = 100.0 * wins / n

    has_capital = reference_capital is not None and reference_capital > 0
    total_pnl_pct = (total_pnl / reference_capital * 100.0) if has_capital else None

    # Peak-to-trough drawdown on the cumulative realized-PnL curve. Starting
    # the curve at 0 (rather than at reference_capital) does not change the
    # drawdown amount at all -- a constant offset shifts peak and trough by
    # the same amount -- so max_drawdown_abs is meaningful even when no
    # capital figure is available. The percentage needs an actual capital
    # figure to divide by, so it stays None without one.
    cumulative = 0.0
    peak_cumulative = 0.0
    max_drawdown_abs = 0.0
    max_drawdown_pct: Optional[float] = 0.0 if has_capital else None
    for pnl in pnls:
        cumulative += pnl
        peak_cumulative = max(peak_cumulative, cumulative)
        drawdown_abs = peak_cumulative - cumulative
        max_drawdown_abs = max(max_drawdown_abs, drawdown_abs)
        if has_capital:
            peak_equity = reference_capital + peak_cumulative
            drawdown_pct = (
                (drawdown_abs / peak_equity * 100.0) if peak_equity > 0 else 0.0
            )
            max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)

    streak = 0
    max_streak = 0
    for pnl in pnls:
        if pnl < 0:
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    collapsed = (
        max_drawdown_pct >= collapse_drawdown_pct
        if max_drawdown_pct is not None
        else None
    )

    return OutcomeMetrics(
        trade_count=n,
        total_pnl=total_pnl,
        total_pnl_pct=total_pnl_pct,
        win_rate_pct=win_rate_pct,
        max_drawdown_abs=max_drawdown_abs,
        max_drawdown_pct=max_drawdown_pct,
        max_losing_streak=max_streak,
        has_losing_streak_5=max_streak >= 5,
        has_losing_streak_10=max_streak >= 10,
        collapsed=collapsed,
        collapse_drawdown_threshold_pct=collapse_drawdown_pct,
        reference_capital=reference_capital,
    )
