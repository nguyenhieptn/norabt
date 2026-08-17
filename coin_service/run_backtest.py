import os
import sys
import subprocess

# Thêm path để import ResourceGuard
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from helper.ResourceGuard import ResourceGuard

def run_full_backtest_pipeline(account_id):
    python_bin = "/home/ubuntu/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11"
    coin_service_dir = "/home/ubuntu/norabt/coin_service"

    print(f"\n================ 🚀 BẮT ĐẦU CHẠY BACKTEST CHO ACCOUNT ID: {account_id} ================\n")

    # KIỂM TRA BẢO VỆ TÀI NGUYÊN (RESOURCE GUARD)
    mem_info = ResourceGuard.get_memory_info()
    print(f"🖥️ [Resource Guard] RAM Đang Dùng: {mem_info['used_gb']} GB / {mem_info['total_gb']} GB (Khả dụng: {mem_info['available_gb']} GB)")
    
    is_safe, msg = ResourceGuard.is_safe_to_run(min_available_gb=2.0)
    if not is_safe:
        print(f"🛑 {msg}")
        print("❌ Dừng chạy để bảo vệ máy chủ không bị quá tải bộ nhớ!")
        return

    # BƯỚC 1: CHẠY ENGINE BACKTEST
    print(f"⚡ 1. Đang chạy Engine tính toán backtest (lab_account {account_id})...")
    cmd_engine = [python_bin, "manage.py", "lab_account", str(account_id)]
    res_engine = subprocess.run(cmd_engine, cwd=coin_service_dir)

    ResourceGuard.cleanup_memory()

    if res_engine.returncode != 0:
        print("❌ Lỗi xảy ra trong quá trình chạy Engine Backtest!")
        return

    print("✅ Engine đã tính toán xong!\n")

    # BƯỚC 2: TRÍCH XUẤT VÀ XUẤT FILE EXCEL
    print(f"📊 2. Đang tổng hợp chỉ số & xuất file Excel/CSV...")
    cmd_export = [python_bin, "export_excel.py", str(account_id)]
    subprocess.run(cmd_export, cwd=coin_service_dir)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        acc_id = int(sys.argv[1])
    else:
        acc_id = 3375
    run_full_backtest_pipeline(acc_id)
