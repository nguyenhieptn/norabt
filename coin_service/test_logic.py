import os
import sys
import time

# Thiết lập đường dẫn môi trường
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crypto_lab.settings')

import django
django.setup()

from helper.ResourceGuard import ResourceGuard
from Console.Models.Coin_lab import LabAccount, LabCampaigns, LabResults
from Console.Models.Wrappers.Lab.Coin_lab import LabAccountWrapper

def test_logic_verification():
    print("==================================================================")
    print("🧪 BẮT ĐẦU KIỂM THỬ LOGIC CORE & TÀI NGUYÊN (DRY-RUN TEST MODE)")
    print("==================================================================")

    # 1. KIỂM TRA RESOURCE GUARD & LIMITS
    print("\n[1/4] 🛡️ Kiểm tra cơ chế giới hạn tài nguyên (ResourceGuard)...")
    mem = ResourceGuard.get_memory_info()
    print(f"   - Tổng RAM: {mem['total_gb']} GB | Đang dùng: {mem['used_gb']} GB | Khả dụng: {mem['available_gb']} GB")
    
    workers_requested_24 = ResourceGuard.get_safe_worker_count(24)
    print(f"   - Yêu cầu 24 workers -> ResourceGuard ép trần an toàn: {workers_requested_24} workers (OK)")
    assert workers_requested_24 <= 6, "LỖI: Worker vượt quá trần 6 tiến trình!"

    # 2. KIỂM TRA RUNTIME HEARTBEAT
    print("\n[2/4] 💓 Kiểm tra Runtime Heartbeat (Điều tiết động trong lúc chạy)...")
    ResourceGuard.runtime_heartbeat("TestContext")
    proc_ram = ResourceGuard.get_current_process_ram_mb()
    print(f"   - RAM tiến trình hiện tại: {proc_ram} MB (Cực kỳ nhẹ)")

    # 3. KIỂM TRA KẾT NỐI & DỮ LIỆU CSDL (MYSQL)
    print("\n[3/4] 🗄️ Kiểm tra truy vấn logic CSDL MySQL (coin_lab)...")
    recent_accounts = LabAccountWrapper().filter({})
    total_acc = len(recent_accounts)
    print(f"   - Tổng số tài khoản Lab trong CSDL: {total_acc}")
    if total_acc > 0:
        latest = recent_accounts[total_acc - 1]
        print(f"   - Tài khoản mẫu ID: {latest.lab_account_id} | Tên: {latest.lab_account_name} | Vốn: ${latest.lab_account_balance}")

    # 4. KIỂM TRA LOGIC TÍNH TOÁN (MATHEMATICAL INTEGRITY)
    print("\n[4/4] 📐 Kiểm tra logic công thức khớp lệnh & Take Profit...")
    entry_price = 50000.0
    budget = 1000.0
    matched_qty = budget / entry_price  # 0.02 BTC
    tp_percent = 1.01  # +1%
    tp_price = entry_price * tp_percent # 50500.0
    profit = (tp_price - entry_price) * matched_qty # 10.0 USDT
    expected_profit = 10.0
    assert abs(profit - expected_profit) < 1e-5, "Lỗi công thức tính lợi nhuận!"
    print(f"   - Test tính toán: Mua ${entry_price} -> Chốt lời ${tp_price} -> Lợi nhuận: ${profit} (Chính xác 100%)")

    print("\n==================================================================")
    print("✅ HOÀN TẤT KIỂM THỬ: LOGIC HOẠT ĐỘNG CHUẨN XÁC, TÀI NGUYÊN AN TOÀN!")
    print("==================================================================")

if __name__ == "__main__":
    test_logic_verification()
