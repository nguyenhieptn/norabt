"""Package Backtest Engine cho Nora.

Mô phỏng khớp lệnh, quản lý trạng thái vị thế và tính toán PnL.
"""
from .engine import BacktestEngine
from .execution import PositionTracker
from .metrics import MetricsCalculator

__all__ = [
    "BacktestEngine",
    "PositionTracker",
    "MetricsCalculator",
]
