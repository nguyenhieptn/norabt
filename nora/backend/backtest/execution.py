"""Mô phỏng Khớp lệnh và Quản lý Vị thế (Execution & Position Tracker)."""
import time
from typing import Any, Dict, List, Optional

from backend.core.evaluator import LogicEvaluator
from backend.core.params import StrategyParams
from backend.db.models import OrderModel, OrderType, PositionModel, PositionStatus, PositionType


class PositionTracker:
    """Theo dõi vòng đời của một vị thế giao dịch (Entry -> DCA -> TP/SL/Exit)."""

    def __init__(
        self,
        account_id: int,
        campaign_id: int,
        symbol: str,
        flow_name: str,
        params: StrategyParams,
        pos_type: PositionType,
    ):
        self.account_id = account_id
        self.campaign_id = campaign_id
        self.symbol = symbol
        self.flow_name = flow_name
        self.params = params
        self.pos_type = pos_type
        
        self.position: Optional[PositionModel] = None
        self.orders: List[OrderModel] = []
        
        self.is_open = False
        self.avg_entry_price = 0.0
        self.total_qty = 0.0
        
        # Tiền biên dịch (Pre-compile) các AST JSON thành Python Lambdas (C-level execution)
        ast_dict = self.params.extra.get('ast', {})
        match_blocks = ast_dict.get('match', [])
        stop_blocks = ast_dict.get('stop', [])
        
        # Chỉ lấy condition của block đầu tiên (giả sử NORMAL type)
        match_ast = match_blocks[0].get('condition', []) if match_blocks else []
        stop_ast = stop_blocks[0].get('condition', []) if stop_blocks else []
        
        self.compiled_match = LogicEvaluator.compile_ast(match_ast)
        self.compiled_stop = LogicEvaluator.compile_ast(stop_ast)

    def update_candle(self, row_1m: Dict[str, Any], row_4h: Dict[str, Any]) -> None:
        """Được gọi mỗi khi có 1 cây nến 1m mới để kiểm tra điều kiện."""
        if not row_1m:
            return
            
        current_time = int(row_1m.get("open_time", 0))
        high_p = float(row_1m.get("high", 0.0))
        low_p = float(row_1m.get("low", 0.0))
        close_p = float(row_1m.get("close", 0.0))

        if not self.is_open:
            # 1. Trạng thái Đóng -> Cố gắng mở vị thế
            if self.compiled_match(row_1m, row_4h):
                # Khớp lệnh!
                entry_price = close_p
                if self.params.using_match_price:
                    # Nếu Long, giá khớp có thể gần Low hơn tùy tín hiệu (giả lập đơn giản)
                    entry_price = low_p if self.pos_type == PositionType.LONG else high_p
                    
                self._open_position(current_time, entry_price, {"type": "NORMAL"})
        else:
            # 2. Trạng thái Mở -> Kiểm tra TP/SL hoặc Stop condition
            if not self.position:
                return
                
            # Cập nhật min/max
            self.position.max_price = max(self.position.max_price, high_p)
            self.position.min_price = min(self.position.min_price, low_p)
            
            # Tính PnL hiện tại
            pnl_pct = 0.0
            if self.pos_type == PositionType.LONG:
                pnl_pct = (close_p - self.avg_entry_price) * 100 / self.avg_entry_price
            else:
                pnl_pct = (self.avg_entry_price - close_p) * 100 / self.avg_entry_price
                
            # Kiểm tra Cắt lỗ cứng (SL)
            if self.params.stop_loss_rate > 0 and pnl_pct <= -self.params.stop_loss_rate:
                self._close_position(current_time, close_p, PositionStatus.SL, f"StopLoss {pnl_pct:.2f}%", pnl_pct)
                return
                
            # Kiểm tra Chốt lời cứng (TP)
            if self.params.take_profit_rate > 0 and pnl_pct >= self.params.take_profit_rate:
                self._close_position(current_time, close_p, PositionStatus.TP, f"TakeProfit {pnl_pct:.2f}%", pnl_pct)
                return
                
            # Kiểm tra AST Stop condition (Chạy hàm Compile)
            if self.compiled_stop(row_1m, row_4h):
                    # Thoát lệnh do tín hiệu đảo chiều
                    exit_price = close_p
                    if self.params.using_match_price:
                        exit_price = high_p if self.pos_type == PositionType.LONG else low_p
                        
                    # Tính lại PnL theo giá exit chính xác
                    if self.pos_type == PositionType.LONG:
                        pnl_pct = (exit_price - self.avg_entry_price) * 100 / self.avg_entry_price
                    else:
                        pnl_pct = (self.avg_entry_price - exit_price) * 100 / self.avg_entry_price
                        
                    self._close_position(current_time, exit_price, PositionStatus.TP if pnl_pct > 0 else PositionStatus.SL, "Stop Condition Triggered", pnl_pct)
                    return
            
            # TODO: Triển khai DCA (nhồi lệnh) theo `enter_step` ở đây trong tương lai.

    def _open_position(self, current_time: int, entry_price: float, match_block: Dict):
        self.is_open = True
        self.avg_entry_price = entry_price
        
        # Giả lập 1 position ID tạm
        pos_id = int(time.time() * 1000)
        
        self.position = PositionModel(
            result_id=pos_id,
            account_id=self.account_id,
            campaign_id=self.campaign_id,
            symbol=self.symbol,
            pos_type=self.pos_type,
            phase=0,
            enter_time=current_time,
            enter_price=entry_price,
            status=PositionStatus.OPEN,
            flow=self.flow_name,
            start_reason="Match Condition AST",
            max_price=entry_price,
            min_price=entry_price
        )
        
        order = OrderModel(
            order_id=pos_id + 1,
            account_id=self.account_id,
            position_id=pos_id,
            order_time=current_time,
            order_type=OrderType.BUY if self.pos_type == PositionType.LONG else OrderType.SELL,
            order_price=entry_price,
            qty=1.0, # Dummy qty
            phase=0
        )
        self.orders.append(order)

    def _close_position(self, current_time: int, close_price: float, status: PositionStatus, reason: str, pnl_pct: float):
        self.is_open = False
        if not self.position:
            return
            
        self.position.close_time = current_time
        self.position.close_price = close_price
        self.position.status = status
        self.position.close_reason = reason
        self.position.profit_pct = pnl_pct
        self.position.real_pnl = pnl_pct # Giả lập vốn $100 -> PnL = Pct%
        
        order = OrderModel(
            order_id=int(time.time() * 1000) + 2,
            account_id=self.account_id,
            position_id=self.position.result_id,
            order_time=current_time,
            order_type=OrderType.SELL if self.pos_type == PositionType.LONG else OrderType.BUY,
            order_price=close_price,
            qty=1.0,
            phase=0
        )
        self.orders.append(order)
