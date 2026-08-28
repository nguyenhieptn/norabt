"""Package Core cho Nora Backtest.

Chứa các chức năng cốt lõi:
- Xử lý và chuẩn hóa tham số (params.py)
- Trình thông dịch logic chiến lược (evaluator.py)
- Bộ nạp dữ liệu hiệu năng cao với Cache (loader.py)
"""
from .evaluator import LogicEvaluator
from .loader import CandleLoader
from .params import StrategyParams

__all__ = [
    "StrategyParams",
    "CandleLoader",
    "LogicEvaluator",
]
