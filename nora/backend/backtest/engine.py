"""Engine Mô phỏng Backtest Toàn diện (Backtest Simulation Engine)."""
import time
from typing import Dict, List, Optional

import pandas as pd
from backend.backtest.execution import PositionTracker
from backend.core.loader import CandleLoader
from backend.core.params import StrategyParams
from backend.db.models import PositionType, PositionStatus


class BacktestEngine:
    """Quản lý luồng thời gian và điều phối dữ liệu cho tất cả các chiến lược con."""

    def __init__(self, account_id: int, campaign_id: int, symbol: str, start_ts: int, end_ts: int):
        self.account_id = account_id
        self.campaign_id = campaign_id
        self.symbol = symbol
        self.start_ts = start_ts
        self.end_ts = end_ts
        
        self.trackers: List[PositionTracker] = []
        
        # An toàn hệ thống (System Safety Limits)
        self.MAX_BACKTEST_DAYS = 90  # Tối đa 90 ngày mỗi lần chạy
        self.MAX_STRATEGIES = 100    # Tối đa 100 flow chiến lược cùng lúc
        
        days_diff = (end_ts - start_ts) / (86400 * 1000)
        if days_diff > self.MAX_BACKTEST_DAYS:
            raise ValueError(f"Limit Exceeded: Yêu cầu chạy {days_diff:.1f} ngày. Server chỉ cho phép tối đa {self.MAX_BACKTEST_DAYS} ngày để bảo vệ tài nguyên!")
        
        self.df_1m: Optional[pd.DataFrame] = None
        self.df_4h: Optional[pd.DataFrame] = None
        
        # Kết quả
        self.closed_positions = []
        self.orders = []

    def load_data(self):
        """Kéo dữ liệu từ MongoDB thông qua CandleLoader (có caching)."""
        # Load 1m
        loader_1m = CandleLoader(self.symbol, frame="1m", use_cache=True)
        self.df_1m = loader_1m.load_data(self.start_ts, self.end_ts)
        
        # Load 4h (Cần lấy trước 1 chút để đảm bảo có nến 4h tương ứng lúc bắt đầu)
        # Nến 4h dài 14400000 ms, lấy lùi lại 2 cây (khoảng 8 tiếng)
        buffer_ms = 86400000
        loader_4h = CandleLoader(self.symbol, frame="4h", use_cache=True)
        self.df_4h = loader_4h.load_data(self.start_ts - buffer_ms, self.end_ts + buffer_ms)

    def add_strategy_flow(self, flow_name: str, params: StrategyParams):
        """Đăng ký một luồng chiến lược (vd LONG-4h)."""
        pos_type = PositionType.LONG if "LONG" in flow_name.upper() else PositionType.SHORT
        tracker = PositionTracker(
            account_id=self.account_id,
            campaign_id=self.campaign_id,
            symbol=self.symbol,
            flow_name=flow_name,
            params=params,
            pos_type=pos_type
        )
        self.trackers.append(tracker)

    def run(self):
        """Khởi động vòng lặp thời gian."""
        if self.df_1m is None or self.df_1m.empty:
            return
            
        print(f"🚀 Bắt đầu chạy backtest cho {self.symbol} ({len(self.df_1m)} nến 1 phút)...")
        start_time = time.time()
        
        # Tối ưu hóa Vector: Dóng nến 1m và 4h bằng merge_asof của Pandas siêu tốc
        # Sắp xếp để đảm bảo merge_asof hoạt động đúng
        df_1m_sorted = self.df_1m.sort_index()
        df_4h_sorted = self.df_4h.sort_index()
        
        # Đổi tên cột 4h để tránh trùng lặp khi gộp
        df_4h_renamed = df_4h_sorted.add_suffix('_4h')
        if 'open_time_4h' in df_4h_renamed.columns:
            df_4h_renamed = df_4h_renamed.rename(columns={'open_time_4h': 'open_time'})
        
        # Đảm bảo index không cản trở việc merge_asof trên column
        df_1m_sorted = df_1m_sorted.reset_index(drop=True)
        df_4h_renamed = df_4h_renamed.reset_index(drop=True)
        
        # Gộp dữ liệu: Tại mỗi thời điểm 1m, lấy cây nến 4h gần nhất trong quá khứ (backward)
        merged_df = pd.merge_asof(df_1m_sorted, df_4h_renamed, on='open_time', direction='backward')
        
        # Bỏ qua các cây nến 1m nằm trước cây nến 4h đầu tiên (nơi các cột 4h bị NaN)
        merged_df = merged_df.dropna(subset=['close_4h'])
        
        # Trích xuất dict thay vì lặp qua df.iterrows()
        records = merged_df.to_dict('records')
        
        cols_4h = set(df_4h_renamed.columns) - {'open_time'}
        
        for row in records:
            # Tách lại dict 1m và 4h từ dict tổng hợp
            # Việc này diễn ra trên dictionary rất nhanh (chỉ reference)
            row_4h = {k.replace('_4h', ''): v for k, v in row.items() if k in cols_4h}
            row_1m = {k: v for k, v in row.items() if k not in cols_4h}
            
            # Đưa dữ liệu môi trường vào từng bộ theo dõi chiến lược
            for tracker in self.trackers:
                tracker.update_candle(row_1m, row_4h)
                
                # Thu hoạch kết quả nếu lệnh vừa đóng
                if not tracker.is_open and tracker.position and tracker.position.status != PositionStatus.OPEN:
                    self.closed_positions.append(tracker.position)
                    self.orders.extend(tracker.orders)
                    # Reset tracker để sẵn sàng đánh vòng mới
                    tracker.position = None
                    tracker.orders = []

        # Xử lý kết thúc (Đóng bắt buộc các lệnh đang mở khi hết thời gian)
        for tracker in self.trackers:
            if tracker.is_open and tracker.position:
                # Đóng lệnh tại giá close của cây nến 1m cuối cùng
                last_close = records[-1].get("close", 0.0)
                last_time = records[-1].get("open_time", 0)
                pnl_pct = 0.0
                if tracker.pos_type == PositionType.LONG:
                    pnl_pct = (last_close - tracker.avg_entry_price) * 100 / tracker.avg_entry_price
                else:
                    pnl_pct = (tracker.avg_entry_price - last_close) * 100 / tracker.avg_entry_price
                    
                tracker._close_position(last_time, last_close, PositionStatus.CANCEL, "End of Backtest", pnl_pct)
                self.closed_positions.append(tracker.position)
                self.orders.extend(tracker.orders)
                
        elapsed = time.time() - start_time
        print(f"✅ Hoàn thành backtest. Thu được {len(self.closed_positions)} vị thế. Mất {elapsed:.2f} giây.")

    def get_results(self):
        return {
            "positions": self.closed_positions,
            "orders": self.orders,
        }
