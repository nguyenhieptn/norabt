"""Đối chiếu alpha dựng lại với ảnh chụp gốc.

Dựng alpha thành chiến lược thật, rồi nạp bằng ĐÚNG bộ nạp của engine
(processLabStrategy trong Console/Phoenix/Lab/function.py) và so từng khoá
với ảnh chụp mà bộ tối ưu đã ghi lại. Khớp thì view mới nói đúng sự thật.
"""
import json
import os
import sys
import urllib.request

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crypto_lab.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from Console.Phoenix.Lab.function import processLabStrategy          # noqa: E402
from Console.Models.Coin_lab import LabStrategies, LabAccount, LabCampaigns  # noqa: E402
from django.db import connection                                     # noqa: E402

API = "http://127.0.0.1:18010"


def lay_mau(n):
    """Chọn mẫu phủ hết các dạng khó, không chỉ dạng phổ biến nhất.

    Ưu tiên chiến lược nhiều luồng và những khoá hiếm gặp
    (allow_negative_price_rate, max_open_trades, using_match_price…) —
    đó mới là chỗ dễ làm sai khi ghi ngược.
    """
    with connection.cursor() as c:
        c.execute("""SELECT MIN(lab_opt_result_id) FROM lab_opt_result
                     WHERE lab_opt_result_done = 1
                     GROUP BY lab_opt_result_optimization""")
        ids = [r[0] for r in c.fetchall()]

    kho, thuong, thay = [], [], set()
    for rid in ids:
        st = anh_chup(rid)
        luongs = [f for ls in st.values() for f in (ls or {}).values()]
        if not luongs:
            continue
        khoa = set().union(*[set(f) for f in luongs])
        la = khoa - {"type", "match", "stop", "name", "strategy", "takeprofit", "stoploss",
                     "baseprofit", "step_profit", "back_profit", "baseprofit_baseon",
                     "timelife", "interval", "margin"}
        if la - thay or len(luongs) > 1:
            thay |= la
            kho.append(rid)
        else:
            thuong.append(rid)
    print(f"mẫu khó (nhiều luồng / khoá hiếm): {len(kho)} · các khoá hiếm: {sorted(thay)}")
    return (kho + thuong)[:n]


def anh_chup(rid):
    with connection.cursor() as c:
        c.execute("SELECT lab_opt_result_strategy FROM lab_opt_result WHERE lab_opt_result_id=%s", [rid])
        return json.loads(c.fetchone()[0] or "{}")


def chuan_hoa(v):
    """So sánh theo nội dung, bỏ qua khác biệt kiểu số do đi qua JSON/cột."""
    if isinstance(v, dict):
        return {k: chuan_hoa(x) for k, x in v.items()}
    if isinstance(v, list):
        return [chuan_hoa(x) for x in v]
    if v is None:
        return None
    if isinstance(v, bool):          # JSON cho True/False, MySQL trả 1/0
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return f"{float(v):.10g}"
    s = str(v)
    try:
        return f"{float(s):.10g}"
    except ValueError:
        return s


def so_sanh(rid):
    goc = anh_chup(rid)
    if not goc:
        return None
    # ảnh chụp: {mã cũ: {"mã--tên": luồng}}
    luong_goc = {}
    for sid, luongs in goc.items():
        for khoa, f in luongs.items():
            luong_goc[f.get("name") or khoa.split("--", 1)[-1]] = f

    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        f"{API}/api/base/alpha-moi/{rid}/tao-run", method="POST",
        data=json.dumps({"dataset": "backtest_data_1m_strategy810"}).encode(),
        headers={"Content-Type": "application/json"}), timeout=120).read())
    run_id, sid_moi = r["run_id"], r["strategy_id"]

    try:
        # ---- 2. so cấu hình lần chạy và danh sách coin với ảnh chụp ----
        with connection.cursor() as c:
            c.execute("""SELECT lab_opt_result_account, lab_opt_result_campaign
                         FROM lab_opt_result WHERE lab_opt_result_id=%s""", [rid])
            ac_raw, ca_raw = c.fetchone()
        ac, ca = json.loads(ac_raw or "{}"), json.loads(ca_raw or "[]")
        moi = LabAccount.objects.filter(lab_account_id=run_id).values().first()
        lech_run = []
        for k in ("lab_account_reserve", "lab_account_compound", "lab_account_margin_type",
                  "lab_account_track_balance", "lab_account_sync", "lab_account_leap",
                  "lab_account_data_type"):
            if k in ac and chuan_hoa(ac[k]) != chuan_hoa(moi.get(k)):
                lech_run.append(f"lần chạy.{k}: {ac[k]} != {moi.get(k)}")
        cps = {c2["lab_campaign_symbol"]: c2 for c2 in
               LabCampaigns.objects.filter(lab_campaign_account=run_id).values()}
        if len(cps) != len(ca):
            lech_run.append(f"số coin: {len(ca)} != {len(cps)}")
        for c2 in ca:
            m = cps.get(c2["lab_campaign_symbol"])
            if not m:
                lech_run.append(f"thiếu coin {c2['lab_campaign_symbol']}"); continue
            for k in ("lab_campaign_start", "lab_campaign_stop", "lab_campaign_side",
                      "lab_campaign_budget", "lab_campaign_reserve", "lab_campaign_compound",
                      "lab_campaign_money", "lab_campaign_active_budget"):
                if k in c2 and chuan_hoa(c2[k]) != chuan_hoa(m.get(k)):
                    lech_run.append(f"{c2['lab_campaign_symbol']}.{k}: {c2[k]} != {m.get(k)}")

        dung_lai = processLabStrategy(sid_moi)      # chính bộ nạp của engine
        luong_moi = {f.get("name"): f for f in dung_lai.values()}

        lech = []
        if set(luong_goc) != set(luong_moi):
            lech.append(f"khác tập luồng: {sorted(luong_goc)} vs {sorted(luong_moi)}")
        for ten in set(luong_goc) & set(luong_moi):
            a, b = luong_goc[ten], luong_moi[ten]
            for k in set(a) | set(b):
                if k == "strategy":          # mã chiến lược mới, đương nhiên khác
                    continue
                if k not in a:
                    lech.append(f"{ten}: thừa khoá {k}")
                elif k not in b:
                    lech.append(f"{ten}: THIẾU khoá {k}")
                elif chuan_hoa(a[k]) != chuan_hoa(b[k]):
                    lech.append(f"{ten}.{k}: {str(a[k])[:70]}  !=  {str(b[k])[:70]}")
        lech = lech_run[:6] + lech
        return {"rid": rid, "so_luong": len(luong_goc), "lech": lech,
                "khoa": sorted(set().union(*[set(f) for f in luong_goc.values()]))}
    finally:
        LabCampaigns.objects.filter(lab_campaign_account=run_id).delete()
        LabAccount.objects.filter(lab_account_id=run_id).delete()
        LabStrategies.objects.filter(lab_strategy_id=sid_moi).delete()


tong = loi = 0
for rid in lay_mau(int(sys.argv[1]) if len(sys.argv) > 1 else 12):
    try:
        kq = so_sanh(rid)
    except Exception as e:
        print(f"alpha {rid}: BỎ QUA — {str(e)[:90]}")
        continue
    if kq is None:
        continue
    tong += 1
    if kq["lech"]:
        loi += 1
        print(f"alpha {kq['rid']}: ✗ {len(kq['lech'])} chỗ lệch")
        for x in kq["lech"][:6]:
            print("     ", x)
    else:
        print(f"alpha {kq['rid']}: ✓ khớp hoàn toàn "
              f"({kq['so_luong']} luồng, {len(kq['khoa'])} khoá)")
print(f"\n== {tong - loi}/{tong} alpha dựng lại khớp y hệt bản gốc ==")
