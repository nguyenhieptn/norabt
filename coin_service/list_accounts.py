import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crypto_lab.settings")
django.setup()

from Console.Models.Coin_lab import LabAccount, LabCampaigns

def list_recent_accounts(limit=10):
    print("\n================ 📋 DANH SÁCH TÀI KHOẢN BACKTEST GẦN ĐÂY ================\n")
    accounts = LabAccount.objects.all().order_by('-lab_account_id')[:limit]
    
    if not accounts:
        print("❌ Không tìm thấy tài khoản nào trong hệ thống!")
        return

    print(f"{'ACCOUNT_ID':<12} | {'TÊN CHIẾN DỊCH / THÍ NGHIỆM':<45} | {'VỐN BAN ĐẦU':<12} | {'SỐ CẶP COIN'}")
    print("-" * 90)

    for acc in accounts:
        campaign_count = LabCampaigns.objects.filter(lab_campaign_account=acc.lab_account_id).count()
        acc_name = (acc.lab_account_name[:42] + '...') if acc.lab_account_name and len(acc.lab_account_name) > 45 else (acc.lab_account_name or 'N/A')
        balance = f"${acc.lab_account_balance:,.0f}" if acc.lab_account_balance else "$0"
        print(f"{acc.lab_account_id:<12} | {acc_name:<45} | {balance:<12} | {campaign_count} cặp coin")
    
    print("\n💡 MẸO: Bạn hãy chọn 1 ACCOUNT_ID ở cột đầu tiên để chạy backtest & xuất file Excel!")
    print("=========================================================================\n")

if __name__ == "__main__":
    list_recent_accounts()
