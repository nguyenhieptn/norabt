import urllib.request
import json
import time

def run():
    print("=== TEST V2 BACKTEST API ===")
    start_ts = 1735689600000  # 2025-01-01
    end_ts = 1736467200000    # 2025-01-10
    
    payload = {
        "account_id": 3379,
        "campaign_id": 1,
        "symbol": "APTUSDT",
        "start_ts": start_ts,
        "end_ts": end_ts,
        "strategy_name": "keltner",
        "using_match_price": True,
        "take_profit_rate": 0.0,
        "stop_loss_rate": 0.0,
        "extra_params": {
            "length": 17,
            "multiplier": 0.5
        }
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request("http://127.0.0.1:18010/api/v2/backtest/run", data=data, headers={'Content-Type': 'application/json'})
    
    start = time.time()
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            print(f"Time taken: {time.time() - start:.2f}s")
            print("Metrics:", res_data["metrics"])
            print(f"Total Trades Returned: {len(res_data['trades'])}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run()
