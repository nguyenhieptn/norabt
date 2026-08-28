"""Script kiểm thử tính năng Tối ưu hoá (Grid Search)."""

from backend.alpha import generate_full_keltner_strategy
from backend.optimize.generator import ParamGenerator
from backend.optimize.runner import OptimizeRunner
from backend.optimize.ranker import ResultsRanker
from datetime import datetime
import time

def run():
    print("=== BẮT ĐẦU CHẠY NORA 2.0 OPTIMIZER ===")
    
    account_id = 3379
    campaign_id = 1
    symbol = "APTUSDT"
    
    # Thời gian 10 ngày đầu năm 2025
    start_ts = int(datetime(2025, 1, 1).timestamp() * 1000)
    end_ts = int(datetime(2025, 1, 10).timestamp() * 1000)
    
    # 2. Định nghĩa Base Params và Ranges
    base_params = {
        "using_match_price": True,
        "take_profit_rate": 0.0,
        "stop_loss_rate": 0.0,
        "extra": {}
    }
    
    ranges = {
        "length": [11, 13, 15, 17, 19, 21, 23, 25, 27, 29], # 10 options
        "multiplier": [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1] # 10 options
    }
    # Tổng: 10 * 10 = 100 tổ hợp
    
    print("⏳ Đang sinh tổ hợp tham số...")
    params_list = ParamGenerator.generate_grid(base_params, ranges)
    print(f"✅ Đã tạo {len(params_list)} tổ hợp.")
    
    # 3. Chạy Optimizer
    # max_workers=None để nó tự dùng toàn bộ số lõi CPU của VPS
    runner = OptimizeRunner(max_workers=None)
    
    results = runner.run_optimization(
        account_id=account_id,
        campaign_id=campaign_id,
        symbol=symbol,
        start_ts=start_ts,
        end_ts=end_ts,
        params_list=params_list,
        ast_generator_func=generate_full_keltner_strategy
    )
    
    # 4. Phân tích kết quả
    print("\n🔍 Đang lọc và xếp hạng kết quả...")
    ranked_results = ResultsRanker.rank_results(
        results,
        sort_by="pnl",
        min_trades=3,
        max_drawdown=50.0,
        min_winrate=30.0
    )
    
    print(f"🎯 Tìm thấy {len(ranked_results)} bộ tham số đạt chuẩn.")
    
    print("\n🏆 TOP 5 CHIẾN LƯỢC TỐT NHẤT:")
    for i, res in enumerate(ranked_results[:5]):
        p = res["params"]
        m = res["metrics"]
        print(f"TOP {i+1}: Length={p.extra.get('length')}, Multiplier={p.extra.get('multiplier')}")
        print(f"  -> PnL: {m['total_pnl_pct']:.2f}% | Winrate: {m['winrate']:.2f}% | Trades: {res['trades']} | MaxDD: {m['max_drawdown_pct']:.2f}%")
        print(f"  -> Thời gian chạy lệnh này: {res['run_time_sec']:.3f}s")
        print("-" * 50)

if __name__ == "__main__":
    run()
