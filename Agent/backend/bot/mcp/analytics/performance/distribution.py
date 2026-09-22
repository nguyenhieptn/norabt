from __future__ import annotations

from typing import List

import numpy as np

from Agent.backend.bot.mcp.schemas.bot_result import (
    RiskMeasurementMode,
    TradeLedgerItem,
    TradeStatistics,
)


class TradeStatisticsCalculator:
    @staticmethod
    def calculate(
        trades: List[TradeLedgerItem], mode: RiskMeasurementMode
    ) -> TradeStatistics:
        if not trades:
            return TradeStatistics(
                sample_size=0, measurement_mode=mode, return_basis="ABSOLUTE_PNL"
            )
        pnls = np.asarray([trade.realized_pnl for trade in trades], dtype=np.float64)
        centered = pnls - float(np.mean(pnls))
        std = float(np.std(pnls, ddof=1)) if len(pnls) > 1 else 0.0
        skew = float(np.mean(centered**3) / (std**3)) if std > 1e-12 else 0.0
        kurtosis = float(np.mean(centered**4) / (std**4) - 3.0) if std > 1e-12 else 0.0
        standard_error = std / np.sqrt(len(pnls)) if len(pnls) > 1 else 0.0
        mean = float(np.mean(pnls))
        returns = [
            trade.realized_pnl_pct
            for trade in trades
            if trade.realized_pnl_pct is not None
        ]
        r_values = [
            trade.r_multiple for trade in trades if trade.r_multiple is not None
        ]
        bases = {trade.return_basis for trade in trades}
        basis = bases.pop() if len(bases) == 1 else "MIXED"
        return TradeStatistics(
            sample_size=len(trades),
            measurement_mode=mode,
            return_basis=basis,
            mean_pnl=mean,
            median_pnl=float(np.median(pnls)),
            pnl_std=std,
            pnl_skew=skew,
            pnl_kurtosis=kurtosis,
            p05_pnl=float(np.percentile(pnls, 5)),
            p95_pnl=float(np.percentile(pnls, 95)),
            mean_return_pct=float(np.mean(returns)) if returns else None,
            median_return_pct=float(np.median(returns)) if returns else None,
            mean_r_multiple=float(np.mean(r_values)) if r_values else None,
            confidence_interval_mean_pnl=[
                mean - 1.96 * standard_error,
                mean + 1.96 * standard_error,
            ],
        )
