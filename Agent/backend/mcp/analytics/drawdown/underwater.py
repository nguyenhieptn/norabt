from __future__ import annotations

from typing import List, Optional

import numpy as np

from Agent.backend.mcp.capital.equity_curve import CapitalModel
from Agent.backend.mcp.schemas.bot_result import DrawdownAnalysis, TradeLedgerItem


class DrawdownUnderwaterAnalyzer:
    """Analyze drawdown amount and calendar underwater duration from the actual ledger."""

    @staticmethod
    def analyze(
        trades: List[TradeLedgerItem], capital: Optional[CapitalModel] = None
    ) -> DrawdownAnalysis:
        if not trades:
            return DrawdownAnalysis()

        ordered = sorted(trades, key=lambda trade: (trade.close_time, trade.open_time))
        cumulative = np.concatenate(
            ([0.0], np.cumsum([trade.realized_pnl for trade in ordered]))
        )
        peaks = np.maximum.accumulate(cumulative)
        drawdown_amounts = peaks - cumulative
        max_dd_amount = float(drawdown_amounts.max())
        current_dd_amount = float(drawdown_amounts[-1])

        max_underwater_ms = 0
        underwater_start: Optional[int] = None
        peak_value = 0.0
        last_timestamp = ordered[-1].close_time
        for trade, equity_delta in zip(ordered, cumulative[1:]):
            if equity_delta >= peak_value:
                if underwater_start is not None:
                    max_underwater_ms = max(
                        max_underwater_ms, trade.close_time - underwater_start
                    )
                    underwater_start = None
                peak_value = equity_delta
            elif underwater_start is None:
                underwater_start = trade.close_time
        if underwater_start is not None:
            max_underwater_ms = max(
                max_underwater_ms, last_timestamp - underwater_start
            )

        max_dd_pct = current_dd_pct = None
        capped_trades = 0
        basis = capital.basis if capital else "UNAVAILABLE"
        curve = capital.equity_curve if capital else None
        if capital and capital.supports_historical_pct and curve is not None:
            # Each drawdown is scaled by the equity actually in force at that time.
            ratios = []
            for trade, amount in zip(ordered, drawdown_amounts[1:]):
                equity = curve.equity_at(trade.close_time)
                if equity and equity > 0:
                    raw = amount / equity
                    if raw > 1.0:
                        # The drawdown is measured on cumulative realised PnL while
                        # the equity comes from the weekly curve; a ratio above one
                        # means the two do not line up for that trade, not that the
                        # account was emptied.
                        capped_trades += 1
                    ratios.append(min(raw, 1.0))
            if ratios:
                max_dd_pct = float(max(ratios) * 100.0)
                current_dd_pct = float(ratios[-1] * 100.0)

        losses = np.asarray([trade.realized_pnl < 0 for trade in ordered], dtype=bool)
        clustering = (
            float(np.mean(losses[1:] & losses[:-1])) if len(losses) > 1 else 0.0
        )
        return DrawdownAnalysis(
            capital_basis=basis,
            max_dd_pct_capped=capped_trades > 0,
            capped_trade_count=capped_trades,
            weekly_equity_max_dd_pct=curve.max_drawdown_pct if curve else None,
            wiped_out=bool(curve and curve.wiped_out),
            current_dd_abs=current_dd_amount,
            max_dd_abs=max_dd_amount,
            current_dd_pct=current_dd_pct,
            max_dd_pct=max_dd_pct,
            floating_dd_pct=None,
            max_floating_dd_pct=None,
            time_underwater_hours=max_underwater_ms / 3_600_000.0,
            recovery_time_hours=max_underwater_ms / 3_600_000.0,
            loss_clustering_index=clustering,
        )
