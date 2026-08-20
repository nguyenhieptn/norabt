import os
import sys
import django
import pandas as pd

# Khởi tạo Django Context
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crypto_lab.settings")
django.setup()

# Mọi file kết quả xuất vào data/exports ở gốc repo (không vứt ra CWD)
EXPORT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "exports"))
os.makedirs(EXPORT_DIR, exist_ok=True)

from Console.Models.Coin_lab import LabResults, LabAccount

def export_backtest_to_csv(account_id):
    print(f"\n🔄 Đang trích xuất dữ liệu kết quả cho Account ID: {account_id}...")
    
    # 1. Query dữ liệu từ CSDL MySQL (Bảng lab_results)
    results = LabResults.objects.filter(lab_result_account=account_id).values(
        'lab_result_id',
        'lab_result_symbol',
        'lab_result_type',             # 1: Long, 2: Short
        'lab_result_phase',            # Phase DCA tối đa
        'lab_result_matched_price',    # Giá vào lệnh trung bình
        'lab_result_sell_price',       # Giá đóng lệnh
        'lab_result_eventprofit',      # Lợi nhuận %
        'lab_result_realpnl',          # Lợi nhuận USD (PnL)
        'lab_result_interval',         # Thời gian giữ lệnh (ms)
        'lab_result_params'            # Lý do đóng/mở lệnh
    )

    if not results:
        print(f"❌ Không tìm thấy dữ liệu kết quả nào cho Account ID: {account_id}!")
        return

    df = pd.DataFrame(list(results))

    # Chuẩn hóa dữ liệu cho trực quan
    df['Loại_Lệnh'] = df['lab_result_type'].map({1: 'LONG', 2: 'SHORT'})
    df['Thời_Gian_Giữ_Lệnh_Phút'] = (df['lab_result_interval'] / 60000).round(1)
    df['Lợi_Nhuận_%'] = df['lab_result_eventprofit'].round(2)
    df['Lãi_Lỗ_USD'] = df['lab_result_realpnl'].round(2)

    # Đổi tên cột chi tiết
    df_detail = df.rename(columns={
        'lab_result_id': 'ID_Lệnh',
        'lab_result_symbol': 'Cặp_Coin',
        'lab_result_phase': 'Phase_DCA_Cao_Nhất',
        'lab_result_matched_price': 'Giá_Trung_Bình',
        'lab_result_sell_price': 'Giá_Thoát',
        'lab_result_params': 'Lý_Do_Đóng_Lệnh'
    })[[
        'ID_Lệnh', 'Cặp_Coin', 'Loại_Lệnh', 'Phase_DCA_Cao_Nhất', 
        'Giá_Trung_Bình', 'Giá_Thoát', 'Lợi_Nhuận_%', 'Lãi_Lỗ_USD', 
        'Thời_Gian_Giữ_Lệnh_Phút', 'Lý_Do_Đóng_Lệnh'
    ]]

    # 2. XUẤT FILE 1: CHI TIẾT TỪNG LỆNH
    detail_filename = os.path.join(EXPORT_DIR, f"ket_qua_backtest_account_{account_id}_chi_tiet.csv")
    df_detail.to_csv(detail_filename, index=False, encoding='utf-8-sig')

    # 3. TẠO BẢNG TỔNG HỢP THEO TỪNG CẶP COIN (GROUP BY SYMBOL)
    summary_list = []
    for symbol, group in df_detail.groupby('Cặp_Coin'):
        total_trades = len(group)
        win_trades = len(group[group['Lãi_Lỗ_USD'] > 0])
        loss_trades = len(group[group['Lãi_Lỗ_USD'] < 0])
        winrate = round((win_trades / total_trades) * 100, 2) if total_trades > 0 else 0
        total_pnl = round(group['Lãi_Lỗ_USD'].sum(), 2)
        avg_profit = round(group['Lợi_Nhuận_%'].mean(), 2)
        max_dca = group['Phase_DCA_Cao_Nhất'].max()

        summary_list.append({
            'Cặp_Coin': symbol,
            'Tổng_Số_Lệnh': total_trades,
            'Số_Lệnh_Thắng': win_trades,
            'Số_Lệnh_Thua': loss_trades,
            'Tỷ_Lệ_Thắng_%': winrate,
            'Tổng_PnL_USD': total_pnl,
            'Lợi_Nhuận_TB_%': avg_profit,
            'Max_Phase_DCA': max_dca
        })

    df_summary = pd.DataFrame(summary_list)

    # XUẤT FILE 2: TỔNG HỢP THEO CẶP COIN
    summary_filename = os.path.join(EXPORT_DIR, f"ket_qua_backtest_account_{account_id}_tong_hop.csv")
    df_summary.to_csv(summary_filename, index=False, encoding='utf-8-sig')

    # 4. IN KẾT QUẢ TRỰC QUAN RA MÀN HÌNH
    total_all_trades = len(df_detail)
    total_all_pnl = df_detail['Lãi_Lỗ_USD'].sum()
    overall_winrate = round((len(df_detail[df_detail['Lãi_Lỗ_USD'] > 0]) / total_all_trades) * 100, 2) if total_all_trades > 0 else 0

    print(f"\n================ 📊 BẢNG TỔNG HỢP THEO CẶP COIN (ACCOUNT {account_id}) ================")
    print(df_summary.to_string(index=False))
    print("-----------------------------------------------------------------------------------------")
    print(f"🎯 Tổng số lệnh toàn chiến dịch: {total_all_trades} lệnh")
    print(f"🏆 Winrate tổng thể: {overall_winrate}%")
    print(f"💰 Tổng PnL chiến dịch: ${total_all_pnl:,.2f}")
    print("\n📁 DÃ XUẤT 2 FILE EXCEL/CSV:")
    print(f"   1️⃣ File tổng hợp theo cặp:  {summary_filename}")
    print(f"   2️⃣ File chi tiết từng lệnh: {detail_filename}")
    print("=========================================================================================\n")

if __name__ == "__main__":
    account_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3375
    export_backtest_to_csv(account_id)
