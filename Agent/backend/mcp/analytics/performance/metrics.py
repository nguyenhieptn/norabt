from __future__ import annotations

import math
from typing import List, Optional

import numpy as np

from Agent.backend.mcp.capital.equity_curve import CapitalModel
from Agent.backend.mcp.schemas.bot_result import (
    BotPerformanceMetrics,
    DrawdownAnalysis,
    TradeLedgerItem,
)


class PerformanceMetricsCalculator:
    """Calculate trade statistics with time-aware annualization and explicit unknowns."""

    @staticmethod
    def calculate(
        trades: List[TradeLedgerItem],
        capital: Optional[CapitalModel] = None,
        reported_roi_pct: Optional[float] = None,
        drawdown: Optional[DrawdownAnalysis] = None,
    ) -> BotPerformanceMetrics:
        if not trades:
            return BotPerformanceMetrics(
                trade_count=0,
                win_rate=0.0,
                loss_rate=0.0,
                total_pnl=0.0,
                roi_pct=reported_roi_pct,
            )

        ordered = sorted(trades, key=lambda trade: (trade.close_time, trade.open_time))
        pnls = np.asarray([trade.realized_pnl for trade in ordered], dtype=np.float64)
        wins = pnls[pnls > 0]
        losses = pnls[pnls < 0]
        count = len(ordered)
        gross_profit = float(wins.sum()) if len(wins) else 0.0
        gross_loss = abs(float(losses.sum())) if len(losses) else 0.0
        total_pnl = float(pnls.sum())

        span_ms = max(trade.close_time for trade in ordered) - min(
            trade.open_time for trade in ordered
        )
        coverage_days = max(span_ms / 86_400_000.0, 1.0 / 24.0)
        frequency = count / coverage_days
        periods_per_year = min(max(frequency * 365.25, 1.0), 365.25 * 24 * 60)

        cumulative = np.concatenate(([0.0], np.cumsum(pnls)))
        cumulative_peaks = np.maximum.accumulate(cumulative)
        drawdown_abs = cumulative_peaks - cumulative
        max_dd_abs = float(drawdown_abs.max())
        current_dd_abs = float(drawdown_abs[-1])

        max_dd = drawdown.max_dd_pct if drawdown else None
        current_dd = drawdown.current_dd_pct if drawdown else None
        curve = capital.equity_curve if capital else None
        returns = None
        if curve is not None and capital and capital.supports_historical_pct:
            bases = [curve.equity_at(trade.close_time) for trade in ordered]
            if all(base and base > 0 for base in bases):
                returns = pnls / np.asarray(bases, dtype=np.float64)
        elif capital and capital.capital_at_risk:
            returns = pnls / capital.capital_at_risk

        sharpe = sortino = None
        if returns is not None and len(returns) >= 2:
            sample_std = float(np.std(returns, ddof=1))
            if sample_std > 1e-12:
                sharpe = float(
                    np.mean(returns) / sample_std * math.sqrt(periods_per_year)
                )
            downside = returns[returns < 0]
            if len(downside) >= 2:
                downside_deviation = float(np.sqrt(np.mean(np.square(downside))))
                if downside_deviation > 1e-12:
                    sortino = float(
                        np.mean(returns)
                        / downside_deviation
                        * math.sqrt(periods_per_year)
                    )

        average_win = float(wins.mean()) if len(wins) else None
        average_loss = abs(float(losses.mean())) if len(losses) else None
        expectancy = total_pnl / count
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else None
        payoff = (
            average_win / average_loss
            if average_win is not None and average_loss not in (None, 0.0)
            else None
        )
        roi = reported_roi_pct
        calmar = roi / max_dd if roi is not None and max_dd and max_dd > 0 else None
        recovery = total_pnl / max_dd_abs if max_dd_abs > 0 else None

        max_win_streak = max_loss_streak = current_streak = 0
        for pnl in pnls:
            if pnl > 0:
                current_streak = current_streak + 1 if current_streak > 0 else 1
                max_win_streak = max(max_win_streak, current_streak)
            elif pnl < 0:
                current_streak = current_streak - 1 if current_streak < 0 else -1
                max_loss_streak = max(max_loss_streak, abs(current_streak))
            else:
                current_streak = 0

        holds = np.asarray(
            [trade.holding_time_minutes for trade in ordered], dtype=np.float64
        )
        return BotPerformanceMetrics(
            trade_count=count,
            win_rate=float(len(wins) / count * 100.0),
            loss_rate=float(len(losses) / count * 100.0),
            total_pnl=total_pnl,
            roi_pct=roi,
            profit_factor=profit_factor,
            expectancy=expectancy,
            payoff_ratio=payoff,
            average_win=average_win,
            average_loss=average_loss,
            max_drawdown_abs=max_dd_abs,
            current_drawdown_abs=current_dd_abs,
            max_drawdown_pct=max_dd,
            current_drawdown_pct=current_dd,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            recovery_factor=recovery,
            current_streak=current_streak,
            max_win_streak=max_win_streak,
            max_loss_streak=max_loss_streak,
            average_hold_time_minutes=float(holds.mean()),
            median_hold_time_minutes=float(np.median(holds)),
            trade_frequency_per_day=frequency,
        )
