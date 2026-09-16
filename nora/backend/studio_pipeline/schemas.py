"""Schemas & Data Contracts cho Studio Pipeline: Backtest -> WFA -> Monte Carlo."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StrategySnapshot(BaseModel):
    strategy_id: Optional[str] = None
    name: str = Field("Untitled Strategy", description="Tên chiến lược")
    symbol: str = Field("SOL", description="Cặp tài sản")
    start_ts: int = Field(0, description="Timestamp bắt đầu (ms)")
    end_ts: int = Field(0, description="Timestamp kết thúc (ms)")
    flows: List[Dict[str, Any]] = Field(default_factory=list, description="Danh sách flow AST")
    initial_capital: float = Field(10000.0, description="Vốn ban đầu")
    leverage: float = Field(1.0, description="Đòn bẩy")
    using_match_price: bool = Field(True)
    max_open_trades: int = Field(45)
    stop_loss_rate: float = Field(0.0)
    take_profit_rate: float = Field(0.0)
    timeout: int = Field(0)


class TradeLogEntry(BaseModel):
    trade_id: str
    pos_type: str
    entry_time: int
    entry_date: Optional[str] = None
    entry_price: float
    close_time: int
    close_date: Optional[str] = None
    close_price: float
    pnl_usd: float
    pnl_pct: float
    reason: Optional[str] = None


class BacktestResultContract(BaseModel):
    source_handle: str
    strategy_snapshot: StrategySnapshot
    symbol: str
    summary: Dict[str, Any]
    trades: List[Dict[str, Any]]
    equity_curve: List[Dict[str, Any]]
    generated_at: int


class WfaFoldConfig(BaseModel):
    train_window_months: int = Field(24, ge=1, le=120, description="Độ dài In-Sample (tháng)")
    test_window_months: int = Field(6, ge=1, le=60, description="Độ dài Out-of-Sample (tháng)")
    step_months: int = Field(6, ge=1, le=60, description="Bước trượt mỗi fold (tháng)")
    fold_count: int = Field(12, ge=1, le=50, description="Số lượng fold tối đa")
    min_is_profit_pct: float = Field(0.0, description="Lợi nhuận IS tối thiểu")
    max_is_mdd_pct: float = Field(15.0, description="MDD IS tối đa (%)")
    min_oos_profit_pct: float = Field(0.0, description="Lợi nhuận OOS tối thiểu (%)")
    max_oos_mdd_pct: float = Field(15.0, description="MDD OOS tối đa từng fold (%)")
    min_positive_folds: int = Field(10, description="Số fold OOS có lãi tối thiểu")
    min_total_oos_profit_pct: float = Field(100.0, description="Tổng lợi nhuận OOS mục tiêu (%)")


class WfaRunRequest(BaseModel):
    source_handle: Optional[str] = None
    strategy_snapshot: Optional[StrategySnapshot] = None
    symbol: Optional[str] = None
    start_ts: Optional[int] = None
    end_ts: Optional[int] = None
    config: Optional[WfaFoldConfig] = None


class WfaFoldResult(BaseModel):
    fold_index: int
    train_start_ts: int
    train_end_ts: int
    train_start_date: str
    train_end_date: str
    test_start_ts: int
    test_end_ts: int
    test_start_date: str
    test_end_date: str
    is_return_pct: float
    is_max_drawdown_pct: float
    is_trades_count: int
    is_win_rate: float
    oos_return_pct: float
    oos_max_drawdown_pct: float
    oos_trades_count: int
    oos_win_rate: float
    oos_profit_factor: float
    passed_gate: bool
    gate_notes: List[str] = Field(default_factory=list)
    oos_trades: List[Dict[str, Any]] = Field(default_factory=list)


class WfaResultContract(BaseModel):
    wfa_id: str
    source_handle: str
    strategy_name: str
    symbol: str
    total_folds: int
    folds: List[WfaFoldResult]
    positive_folds_count: int
    total_oos_return_pct: float
    avg_oos_return_pct: float
    worst_fold_mdd_pct: float
    avg_oos_mdd_pct: float
    total_oos_trades: int
    overall_oos_win_rate: float
    acceptance_gate_passed: bool
    gate_checks: Dict[str, Any]
    aggregate_oos_trades: List[Dict[str, Any]]
    aggregate_oos_equity: List[Dict[str, Any]]
    generated_at: int


class MonteCarloRunRequest(BaseModel):
    source_wfa_id: Optional[str] = None
    source_handle: Optional[str] = None
    trades: Optional[List[Dict[str, Any]]] = None
    strategy_name: Optional[str] = "Strategy"
    symbol: Optional[str] = "SOL"
    initial_capital: float = Field(10000.0, ge=1.0)
    simulations: int = Field(1000, ge=100, le=10000)
    ruin_threshold_pct: float = Field(30.0, ge=5.0, le=95.0, description="Ngưỡng sụt giảm vốn tính là Ruin (%)")
    confidence_levels: List[float] = Field(default_factory=lambda: [90.0, 95.0, 99.0])
    block_size: int = Field(1, ge=1, le=50, description="Kích thước block bootstrap (1 = trade độc lập)")


class MonteCarloResultContract(BaseModel):
    mc_id: str
    source_wfa_id: Optional[str] = None
    strategy_name: str
    symbol: str
    simulations: int
    trades_count: int
    initial_capital: float
    percentile_mdd: Dict[str, float]
    risk_of_ruin_pct: float
    ruin_threshold_pct: float
    terminal_return_pct: Dict[str, float]
    sample_paths: List[List[float]]
    summary: Dict[str, Any]
    generated_at: int
