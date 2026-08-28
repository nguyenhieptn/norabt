import os
import sys
import time
import json
import pandas as pd

# No django setup needed for New Engine

# Import New Engine
from nora.backend.core import StrategyParams
from nora.backend.alpha import generate_full_keltner_strategy
from nora.backend.backtest import BacktestEngine, MetricsCalculator

# Import Old Engine (using the CampaignImp1m directly)
# wait, actually the best way to run old engine is through LabResults processing
# Let's write a simple wrapper for New Engine first and print it.

start_date = "2025-01-01 00:00:00"
end_date = "2025-01-10 00:00:00"

start_ts = int(pd.Timestamp(start_date + "+07:00").timestamp() * 1000)
end_ts = int(pd.Timestamp(end_date + "+07:00").timestamp() * 1000)

print(f"=== BẮT ĐẦU CHẠY NORA 2.0 (NEW ENGINE) ===")
t1 = time.time()
ast = generate_full_keltner_strategy(17, 0.5)

# Thay đổi params khớp với gốc (baseprofit 2000000)
params_long = StrategyParams(name="LONG-4h", data_type="1m", using_match_price=True, max_open_trades=50, extra={"ast": ast["LONG-4h"]})
params_short = StrategyParams(name="SHORT-4h", data_type="1m", using_match_price=True, max_open_trades=50, extra={"ast": ast["SHORT-4h"]})

engine = BacktestEngine(account_id=999, campaign_id=999, symbol="APTUSDT", start_ts=start_ts, end_ts=end_ts)
engine.load_data()
engine.add_strategy_flow("LONG-4h", params_long)
engine.add_strategy_flow("SHORT-4h", params_short)

print("Đang quét nến...")
engine.run()
results = engine.get_results()
metrics = MetricsCalculator.calculate(results["positions"])
t2 = time.time()

print(f"✅ NORA 2.0 HOÀN THÀNH trong {t2-t1:.2f}s")
print(f"👉 Winrate: {metrics['winrate']}%")
print(f"👉 Total PnL: {metrics['total_pnl_pct']}%")
print(f"👉 Total Trades: {metrics['total_trades']}")

# Trích 3 lệnh đầu tiên để so sánh
print("--- 3 lệnh đầu tiên (Nora 2.0) ---")
for p in results['positions'][:3]:
    t_in = pd.to_datetime(p.enter_time, unit='ms', utc=True).tz_convert('Asia/Ho_Chi_Minh').strftime('%Y-%m-%d %H:%M')
    t_out = pd.to_datetime(p.close_time, unit='ms', utc=True).tz_convert('Asia/Ho_Chi_Minh').strftime('%Y-%m-%d %H:%M')
    print(f"{p.flow} | IN: {t_in} @ {p.enter_price:.4f} | OUT: {t_out} @ {p.close_price:.4f} | PnL: {p.profit_pct:.2f}% | Lý do: {p.close_reason}")

print("\n============================================\n")

print(f"=== BẮT ĐẦU CHẠY BẢN GỐC (OLD ENGINE) ===")
print("Xin vui lòng check DB bảng `lab_results` ID 3379 để so sánh với kết quả trên, vì bản gốc chạy nguyên khối trên web mất khoảng 2-3 phút.")
