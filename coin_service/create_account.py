import os
import sys
import time
from datetime import datetime
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crypto_lab.settings")
django.setup()

from Console.Models.Coin_lab import LabAccount, LabCampaigns

def create_new_backtest_account(name, balance=10000, symbol="BTCUSDT", start_date="2023-01-01", stop_date="2023-12-31", strategy_id=204):
    print(f"\n🔄 Đang khởi tạo Account Backtest mới: '{name}'...")

    # Chuyển ngày YYYY-MM-DD sang Unix Timestamp (giây)
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
    stop_ts = int(datetime.strptime(stop_date, "%Y-%m-%d").timestamp())

    # 1. Tạo bản ghi trong bảng lab_account
    acc = LabAccount.objects.create(
        lab_account_name=name,
        lab_account_balance=float(balance),
        lab_account_margin_balance=float(balance),
        lab_account_margin_type="CROSS",
        lab_account_db="backtest_data_1m_custom",
        lab_account_data_type="1m",
        lab_account_data_length=1,
        lab_account_running=0
    )
    acc_id = acc.lab_account_id

    # 2. Tạo chiến dịch test trong bảng lab_campaigns
    LabCampaigns.objects.create(
        lab_campaign_name=f"{name}_{symbol}",
        lab_campaign_account=acc_id,
        lab_campaign_symbol=symbol,
        lab_campaign_start=start_ts,
        lab_campaign_stop=stop_ts,
        lab_campaign_strategy=int(strategy_id),
        lab_campaign_side="BOTH",
        lab_campaign_budget=float(balance),
        lab_campaign_running=0
    )

    print(f"✅ ĐÃ TẠO THÀNH CÔNG!")
    print(f"👉 ACCOUNT_ID mới của bạn là: {acc_id}")
    print(f"   - Tên: {name}")
    print(f"   - Vốn: ${balance:,.2f}")
    print(f"   - Cặp Coin: {symbol}")
    print(f"   - Khoảng thời gian: {start_date} -> {stop_date}")
    print(f"\n⚡ Để chạy backtest ngay cho Account này, bạn gõ:")
    print(f"   python run_backtest.py {acc_id}\n")
    return acc_id

if __name__ == "__main__":
    if len(sys.argv) > 1:
        name = sys.argv[1]
        balance = float(sys.argv[2]) if len(sys.argv) > 2 else 10000
        symbol = sys.argv[3] if len(sys.argv) > 3 else "BTCUSDT"
        start = sys.argv[4] if len(sys.argv) > 4 else "2023-01-01"
        stop = sys.argv[5] if len(sys.argv) > 5 else "2023-12-31"
        strat = int(sys.argv[6]) if len(sys.argv) > 6 else 204
        create_new_backtest_account(name, balance, symbol, start, stop, strat)
    else:
        print("💡 CÁCH DÙNG: python create_account.py <Tên_Test> <Vốn> <Cặp_Coin> <Từ_Ngày> <Đến_Ngày> <ID_Chiến_Lược>")
        print("   Ví dụ: python create_account.py \"Test_BTC_2023\" 10000 BTCUSDT 2023-01-01 2023-12-31 204")
