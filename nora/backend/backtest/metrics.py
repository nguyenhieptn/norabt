"""Tính toán các chỉ số Hiệu năng (Metrics Calculation)."""
from typing import Dict, List

from backend.db.models import PositionModel


class MetricsCalculator:
    """Xử lý mảng vị thế (Positions) để xuất ra các chỉ số định lượng."""

    @staticmethod
    def calculate(positions: List[PositionModel], initial_balance: float = 10000.0) -> Dict[str, float]:
        if not positions:
            return {
                "total_trades": 0,
                "winrate": 0.0,
                "total_pnl_pct": 0.0,
                "max_drawdown": 0.0,
                "profit_factor": 0.0,
            }

        total_trades = len(positions)
        winning_trades = sum(1 for p in positions if p.profit_pct > 0)
        losing_trades = sum(1 for p in positions if p.profit_pct <= 0)
        
        gross_profit = sum(p.profit_pct for p in positions if p.profit_pct > 0)
        gross_loss = sum(p.profit_pct for p in positions if p.profit_pct <= 0)
        
        winrate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else (999.0 if gross_profit > 0 else 0.0)
        total_pnl_pct = sum(p.profit_pct for p in positions)
        
        # Max Drawdown (MDD) calculation
        # Tính toán trên luồng tích luỹ PnL
        cumulative = 0.0
        peak = 0.0
        max_drawdown = 0.0
        
        for p in positions:
            cumulative += p.profit_pct
            if cumulative > peak:
                peak = cumulative
            
            drawdown = peak - cumulative
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return {
            "total_trades": total_trades,
            "winrate": round(winrate, 2),
            "total_pnl_pct": round(total_pnl_pct, 4),
            "max_drawdown": round(max_drawdown, 4),
            "profit_factor": round(profit_factor, 2),
            "gross_profit": round(gross_profit, 4),
            "gross_loss": round(gross_loss, 4),
        }
