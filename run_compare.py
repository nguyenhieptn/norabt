import os
import sys
import time
import subprocess
import pandas as pd

from nora.backend.core import StrategyParams
from nora.backend.alpha import generate_full_keltner_strategy
from nora.backend.backtest import BacktestEngine, MetricsCalculator
from nora.backend.db.models import PositionType

def run_new_engine():
    print(f"=== BẮT ĐẦU CHẠY NORA 2.0 (NEW ENGINE) ===")
    start_date = "2025-01-01 00:00:00"
    end_date = "2025-01-10 00:00:00"
    start_ts = int(pd.Timestamp(start_date + "+07:00").timestamp() * 1000)
    end_ts = int(pd.Timestamp(end_date + "+07:00").timestamp() * 1000)

    t1 = time.time()
    
    # 1. Sinh AST cho Keltner (length=17, multiplier=0.5)
    ast = generate_full_keltner_strategy(17, 0.5)

    params_long = StrategyParams(name="LONG-4h", data_type="1m", using_match_price=True, max_open_trades=50, extra={"ast": ast["LONG-4h"]})
    params_short = StrategyParams(name="SHORT-4h", data_type="1m", using_match_price=True, max_open_trades=50, extra={"ast": ast["SHORT-4h"]})

    # 2. Chạy Backtest Engine
    engine = BacktestEngine(account_id=3379, campaign_id=1, symbol="APTUSDT", start_ts=start_ts, end_ts=end_ts)
    engine.load_data()
    engine.add_strategy_flow("LONG-4h", params_long)
    engine.add_strategy_flow("SHORT-4h", params_short)

    engine.run()
    results = engine.get_results()
    metrics = MetricsCalculator.calculate(results["positions"])
    t2 = time.time()

    print(f"✅ NORA 2.0 HOÀN THÀNH trong {t2-t1:.2f}s")
    print(f"👉 Winrate: {metrics['winrate']}%")
    print(f"👉 Total PnL: {metrics['total_pnl_pct']}%")
    print(f"👉 Total Trades: {metrics['total_trades']}")

    print("\n--- Danh sách lệnh (Nora 2.0) ---")
    for p in results['positions']:
        t_in = pd.to_datetime(p.enter_time, unit='ms', utc=True).tz_convert('Asia/Ho_Chi_Minh').strftime('%Y-%m-%d %H:%M')
        t_out = pd.to_datetime(p.close_time, unit='ms', utc=True).tz_convert('Asia/Ho_Chi_Minh').strftime('%Y-%m-%d %H:%M') if p.close_time else "OPEN"
        pos_type = "LONG" if p.pos_type == PositionType.LONG else "SHORT"
        print(f"{pos_type} | IN: {t_in} @ {p.enter_price:.4f} | OUT: {t_out} @ {p.close_price or 0:.4f} | PnL: {p.profit_pct:.2f}% | Lý do: {p.close_reason or 'None'}")
    
    return t2 - t1

def run_old_engine():
    print(f"\n============================================\n")
    print(f"=== BẮT ĐẦU CHẠY BẢN GỐC (OLD ENGINE) ===")
    t1 = time.time()
    
    # Kích hoạt hệ thống cũ chạy bằng manage.py của Django
    process = subprocess.Popen(
        ["/home/ubuntu/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11", "manage.py", "lab_account_v1", "3379"],
        cwd="/home/ubuntu/norabt/coin_service",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    t2 = time.time()
    
    if process.returncode != 0:
        print("Lỗi khi chạy bản gốc:")
        print(stderr.decode())
    else:
        print(f"✅ BẢN GỐC HOÀN THÀNH trong {t2-t1:.2f}s")
        print(f"👉 Lệnh gọi hoàn tất. Chi tiết lệnh nằm trong MySQL Database bảng `lab_results` ID 3379.")
        # Lấy từ MySQL ra để in
        db_process = subprocess.Popen(
            ["/home/ubuntu/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11", "manage.py", "shell", "-c", 
             "from Console.Models.Coin_lab import LabResult; "
             "res = LabResult.objects.filter(lab_result_account=3379).order_by('lab_result_id'); "
             "print(f'Total Trades: {len(res)}'); "
             "print('--- Danh sách lệnh (Old Engine) ---'); "
             "import json; "
             "from datetime import datetime; "
             "[print(f\"{r.lab_result_action.upper()} | IN: {datetime.fromtimestamp(json.loads(r.lab_result_enter)[0]/1000).strftime('%Y-%m-%d %H:%M')} @ {r.lab_result_enter_price:.4f} | OUT: {datetime.fromtimestamp(json.loads(r.lab_result_close)[0]/1000).strftime('%Y-%m-%d %H:%M') if r.lab_result_close else 'OPEN'} @ {r.lab_result_close_price or 0:.4f} | PnL: {r.lab_result_profit_p}%\") for r in res]"
            ],
            cwd="/home/ubuntu/norabt/coin_service",
            stdout=subprocess.PIPE
        )
        db_out, _ = db_process.communicate()
        print(db_out.decode('utf-8'))
        
if __name__ == "__main__":
    t_new = run_new_engine()
    run_old_engine()
