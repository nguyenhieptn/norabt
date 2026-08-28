"""Pydantic Schemas cho Nora 2.0 API.

Định nghĩa cấu trúc dữ liệu đầu vào (Request) và đầu ra (Response)
cho các API gọi Backtest và Optimize.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    """Payload gửi lên từ Web UI để chạy 1 kịch bản Backtest."""
    account_id: int = Field(default=3379, description="ID của Account trên DB")
    campaign_id: int = Field(default=1, description="ID của Campaign")
    symbol: str = Field(default="APTUSDT", description="Cặp giao dịch, ví dụ APTUSDT")
    start_ts: int = Field(..., description="Timestamp bắt đầu (ms)")
    end_ts: int = Field(..., description="Timestamp kết thúc (ms)")
    
    # Tham số chiến lược
    strategy_name: str = Field(default="keltner", description="Tên chiến lược")
    using_match_price: bool = Field(default=True)
    take_profit_rate: float = Field(default=0.0)
    stop_loss_rate: float = Field(default=0.0)
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="Các tham số riêng của chiến lược (length, multiplier,...)")


class OptimizeRequest(BaseModel):
    """Payload gửi lên từ Web UI để chạy Grid Search."""
    account_id: int = Field(default=3379)
    campaign_id: int = Field(default=1)
    symbol: str = Field(default="APTUSDT")
    start_ts: int = Field(..., description="Timestamp bắt đầu (ms)")
    end_ts: int = Field(..., description="Timestamp kết thúc (ms)")
    
    strategy_name: str = Field(default="keltner")
    base_params: Dict[str, Any] = Field(
        default_factory=lambda: {"using_match_price": True, "take_profit_rate": 0.0, "stop_loss_rate": 0.0}
    )
    ranges: Dict[str, List[Any]] = Field(
        ..., 
        description="Định nghĩa mảng các giá trị muốn tối ưu, ví dụ: {'length': [10, 20], 'multiplier': [0.5, 1.0]}"
    )
    
    # Bộ lọc kết quả
    min_trades: int = Field(default=3)
    max_drawdown: float = Field(default=50.0)
    min_winrate: float = Field(default=30.0)
    sort_by: str = Field(default="pnl")


class PositionResponse(BaseModel):
    """Cấu trúc của 1 Lệnh (Trade) trả về cho Frontend."""
    symbol: str
    type: str # LONG / SHORT
    enter_time: int
    enter_price: float
    close_time: Optional[int]
    close_price: Optional[float]
    pnl_pct: float
    reason: str


class MetricsResponse(BaseModel):
    """Các chỉ số hiệu năng trả về."""
    total_trades: int
    winrate: float
    total_pnl_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float


class BacktestResponse(BaseModel):
    """Payload trả về từ API Backtest."""
    metrics: MetricsResponse
    trades: List[PositionResponse]
    run_time_sec: float
