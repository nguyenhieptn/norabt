"""Nora Backtest — API thống kê.

Đọc dữ liệu backtest từ MySQL của hệ thống cũ (chỉ đọc, không ghi),
tổng hợp thành 6 tầng thống kê cho giao diện mới.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import asyncio

from fastapi import Body, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.db import cursor, fetch_all, fetch_one   # noqa: E402
from backend.stats import queries as q               # noqa: E402
from backend.stats import metrics as mt              # noqa: E402
from backend import control as ctl                   # noqa: E402

app = FastAPI(title="Nora Backtest API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

CHART_DIR = Path("/home/ubuntu/norabt/coin_monitor/frontend/build/plot")
MONITOR_DIR = Path("/home/ubuntu/norabt/coin_monitor")
PYBIN = "/home/ubuntu/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11"


# ---------------------------------------------------------------- danh sách

@app.get("/api/runs")
def list_runs(group: str = None, q_: str = Query(None, alias="q"), limit: int = 50):
    """Danh sách lần chạy backtest. Luôn có LIMIT — không bao giờ kéo cả bảng."""
    where, params = ["1=1"], []
    if group:
        where.append("lab_account_group = %s")
        params.append(group)
    if q_:
        where.append("(lab_account_name LIKE %s OR lab_account_id = %s)")
        params += [f"%{q_}%", q_ if q_.isdigit() else -1]
    rows = fetch_all(
        f"""SELECT lab_account_id AS id, lab_account_name AS name,
                   lab_account_group AS `group`, lab_account_db AS dataset,
                   lab_account_balance AS balance, lab_account_running AS running,
                   lab_account_margin_type AS margin_type
            FROM lab_account WHERE {' AND '.join(where)}
            ORDER BY lab_account_id DESC LIMIT %s""",
        params + [limit],
    )
    # đếm số lệnh của từng run (một truy vấn gộp, không lặp)
    if rows:
        ids = tuple(r["id"] for r in rows)
        ph = ",".join(["%s"] * len(ids))
        counts = {
            c["a"]: c["n"]
            for c in fetch_all(
                f"""SELECT lab_result_account AS a, COUNT(*) AS n FROM lab_results
                    WHERE lab_result_account IN ({ph}) GROUP BY lab_result_account""",
                list(ids),
            )
        }
        # Cờ trong bảng chỉ đáng tin khi engine kết thúc bình thường; đối chiếu
        # với tiến trình thật để danh sách không báo "đang chạy" mãi mãi.
        dang_chay = ctl.running_ids()
        for r in rows:
            r["trades"] = counts.get(r["id"], 0)
            r["running"] = 1 if r["id"] in dang_chay else 0
    return {"rows": rows}


@app.get("/api/groups")
def list_groups():
    return {
        "rows": fetch_all(
            """SELECT lab_account_group AS name, COUNT(*) AS n FROM lab_account
               WHERE lab_account_group IS NOT NULL AND lab_account_group <> ''
               GROUP BY lab_account_group ORDER BY n DESC LIMIT 50"""
        )
    }


# ---------------------------------------------------------------- thống kê

@app.get("/api/runs/{run_id}")
def get_run(run_id: int):
    info = q.run_info(run_id)
    if not info:
        raise HTTPException(404, "Không tìm thấy lần chạy này")
    return info


@app.get("/api/runs/{run_id}/overview")
def get_overview(run_id: int):
    r = q.overview(run_id)
    if not r:
        raise HTTPException(404, "Lần chạy chưa có kết quả")
    return r


@app.get("/api/runs/{run_id}/by-flow")
def get_by_flow(run_id: int):
    return {"rows": q.by_flow(run_id)}


@app.get("/api/runs/{run_id}/behavior")
def get_behavior(run_id: int):
    return q.behavior(run_id)


@app.get("/api/runs/{run_id}/by-symbol")
def get_by_symbol(run_id: int, limit: int = 100):
    return {"rows": q.by_symbol(run_id, limit)}


@app.get("/api/runs/{run_id}/timeline")
def get_timeline(run_id: int):
    return {"rows": q.timeline(run_id)}


@app.get("/api/runs/{run_id}/equity")
def get_equity(run_id: int, points: int = 2000):
    return q.equity(run_id, points)


@app.get("/api/runs/{run_id}/trades")
def get_trades(run_id: int, page: int = 1, size: int = 50,
               symbol: str = None, flow: str = None, only: str = None):
    return q.trades(run_id, page, min(size, 200), symbol, flow, only)


@app.get("/api/runs/{run_id}/insights")
def get_insights(run_id: int):
    return {"rows": q.insights(run_id)}






# ---------------------------------------------------------------- điều khiển chạy

@app.get("/api/node")
def get_node():
    return ctl.node_status()


@app.get("/api/runs/{run_id}/preflight")
def get_preflight(run_id: int):
    """Kiểm tra cấu hình trước khi chạy."""
    return ctl.preflight(run_id)


@app.post("/api/runs/{run_id}/start")
def post_start(run_id: int):
    r = ctl.start(run_id)
    if not r.get("result"):
        raise HTTPException(400, r.get("message") or "Không chạy được")
    return r


@app.post("/api/runs/{run_id}/stop")
def post_stop(run_id: int):
    return ctl.stop(run_id)


@app.get("/api/runs/{run_id}/log")
def get_log(run_id: int, tail: int = 120):
    return ctl.log(run_id, tail)


@app.get("/api/runs/{run_id}/progress")
def get_progress(run_id: int):
    return ctl.progress(run_id)



# ---------------------------------------------------------------- kênh thời gian thực

@app.websocket("/ws/runs/{run_id}/progress")
async def ws_progress(ws: WebSocket, run_id: int):
    """Đẩy tiến độ theo thời gian thực trong lúc backtest chạy.

    Nhịp gửi tự co giãn: đang chạy thì 2 giây một lần, đã dừng thì 10 giây —
    vừa mượt khi cần, vừa không hỏi cơ sở dữ liệu vô ích khi rảnh.
    Chỉ gửi khi số liệu thay đổi, trừ nhịp giữ kết nối mỗi 30 giây.
    """
    await ws.accept()
    truoc = None
    lan_gui_cuoi = 0.0
    try:
        while True:
            # truy vấn chạy ở luồng phụ để không chặn vòng lặp sự kiện
            data = await asyncio.to_thread(ctl.progress, run_id)
            now = asyncio.get_event_loop().time()
            moc = (data["processed"], data["trades"], data["state"])

            if moc != truoc or now - lan_gui_cuoi > 30:
                await ws.send_json(data)
                truoc = moc
                lan_gui_cuoi = now

            # backtest xong thì gửi lần cuối rồi đóng
            if data["state"] in ("done", "interrupted") and not data["running"]:
                await ws.send_json({**data, "final": True})
                break

            await asyncio.sleep(2 if data.get("busy") else 10)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"error": str(e)[:200]})
        except Exception:
            pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass


@app.websocket("/ws/runs/{run_id}/log")
async def ws_log(ws: WebSocket, run_id: int, tail: int = 60):
    """Đẩy log chạy theo thời gian thực."""
    await ws.accept()
    truoc = None
    try:
        while True:
            r = await asyncio.to_thread(ctl.log, run_id, tail)
            text = r.get("data") if isinstance(r, dict) else None
            if text and text != truoc:
                await ws.send_json({"log": text})
                truoc = text
            p = await asyncio.to_thread(ctl.progress, run_id)
            if not p.get("busy"):
                await ws.send_json({"log": text, "final": True})
                break
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        try:
            await ws.close()
        except Exception:
            pass

# ---------------------------------------------- alpha mới sinh ra từ phiên đào

DAU_ALPHA = "nora:alpha:"     # ghi vào lab_account_note để biết run nào dựng từ alpha nào
NHOM_ALPHA = "Nora Alpha"


def _da_dung_run():
    """Bản đồ mã kết quả -> mã lần chạy đã dựng từ nó."""
    rows = fetch_all(
        "SELECT lab_account_id AS id, lab_account_note AS note FROM lab_account "
        "WHERE lab_account_note LIKE %s", (DAU_ALPHA + "%",))
    ra = {}
    for r in rows:
        try:
            ra[int(str(r["note"]).split(":")[-1])] = r["id"]
        except ValueError:
            pass
    return ra


@app.get("/api/base/alpha-moi")
def alpha_moi(opt: int = None, limit: int = 60, sort: str = "balance"):
    """Alpha do phiên đào sinh ra — mỗi tổ hợp thắng cuộc là một chiến lược mới.

    Chúng chỉ tồn tại dưới dạng ảnh chụp trong lab_opt_result, chưa có lần chạy
    thật nào, nên trạng thái mặc định là "chưa chạy".
    """
    where, params = ["r.lab_opt_result_done = 1"], []
    if opt:
        where.append("r.lab_opt_result_optimization = %s")
        params.append(opt)
    order = ("r.lab_opt_result_id DESC" if sort == "moi"
             else "r.lab_opt_result_balance DESC")
    rows = fetch_all(
        f"""SELECT r.lab_opt_result_id              AS id,
                   r.lab_opt_result_optimization    AS opt_id,
                   o.lab_opt_name                   AS opt_name,
                   o.lab_opt_account                AS base_run,
                   ROUND(r.lab_opt_result_balance, 2)      AS balance,
                   ROUND(r.lab_opt_result_invest_max, 2)   AS invest_max,
                   ROUND(r.lab_opt_result_unrelize_max, 2) AS unrealize_max,
                   r.lab_opt_result_total_position  AS positions,
                   r.lab_opt_result_total_long      AS longs,
                   r.lab_opt_result_total_short     AS shorts,
                   r.lab_opt_result_total_takeprofit AS takeprofit,
                   r.lab_opt_result_total_stoploss   AS stoploss,
                   r.lab_opt_result_params          AS params
            FROM lab_opt_result r
            LEFT JOIN lab_optimization o ON o.lab_opt_id = r.lab_opt_result_optimization
            WHERE {' AND '.join(where)}
            ORDER BY {order} LIMIT %s""",
        params + [limit],
    )
    da = _da_dung_run()
    for r in rows:
        r["run_id"] = da.get(r["id"])
        r["state"] = "da_dung" if r["run_id"] else "chua_chay"
        r["params"] = str(r.get("params") or "")[:400]
    return {"rows": rows}


# Hai khoá này do bộ nạp chiến lược tự gắn lại khi chạy (name = khoá của luồng,
# strategy = mã chiến lược), nên phải bỏ ra khi ghi ngược vào bảng.
KHOA_TU_GAN = ("name", "strategy")

# Chín trường cấp chiến lược nằm ở cột riêng của bảng lab_strategies.
TRUONG_CHIEN_LUOC = ("takeprofit", "stoploss", "baseprofit", "step_profit", "back_profit",
                     "baseprofit_baseon", "timelife", "interval", "margin")


def _tach_alpha(st_raw):
    """Tách ảnh chụp chiến lược thành nội dung + các trường cấp chiến lược.

    Ảnh chụp có dạng {"<mã>": {"<mã>--<tên luồng>": {luồng đã dựng xong}}}, tức
    là kết quả SAU khi bộ nạp gốc (processLabChildStrategy) đã thay tham số,
    gắn name/strategy và đổ các trường cấp chiến lược xuống luồng.

    Muốn chạy lại y hệt thì phải ghi ngược sao cho bộ nạp gốc dựng ra đúng
    luồng đó. Cách chắc chắn nhất là giữ NGUYÊN mọi khoá của luồng trong nội
    dung — kể cả takeprofit/margin… — vì bộ nạp chỉ đổ giá trị từ cột xuống khi
    luồng chưa có khoá đó. Chỉ bỏ name/strategy vì bộ nạp tự gắn lại.

    Whitelist theo kiểu chỉ giữ type/match/stop là sai: dữ liệu thật còn có
    allow_negative_price_rate, max_open_trades, using_matched_price…
    """
    st = json.loads(st_raw or "{}")
    noi_dung, truong, ten = {}, {}, None
    for _, luongs in st.items():
        for khoa, luong in (luongs or {}).items():
            ten_luong = luong.get("name") or khoa.split("--", 1)[-1]
            noi_dung[ten_luong] = {k: v for k, v in luong.items() if k not in KHOA_TU_GAN}
            if not truong:
                ten = ten_luong
                truong = {k: luong.get(k) for k in TRUONG_CHIEN_LUOC}
    return noi_dung, truong, ten


def _co_bo_chua(st_raw):
    """Ảnh chụp có phải của một bộ chứa nhiều chiến lược con không."""
    try:
        st = json.loads(st_raw or "{}")
    except Exception:
        return False
    return any("container" in (f or {}) for luongs in st.values() for f in (luongs or {}).values())


@app.get("/api/datasets")
def datasets():
    """Các bộ dữ liệu nến đang được dùng, để chọn khi dựng lần chạy."""
    return {"rows": [r["name"] for r in fetch_all(
        "SELECT lab_account_db AS name, COUNT(*) AS n FROM lab_account "
        "WHERE lab_account_db IS NOT NULL AND lab_account_db <> '' "
        "GROUP BY lab_account_db ORDER BY n DESC")]}


@app.get("/api/base/alpha-moi/{rid}")
def alpha_chi_tiet(rid: int):
    """Xem trước một alpha trước khi dựng thành lần chạy."""
    r = fetch_one(
        """SELECT lab_opt_result_id AS id, lab_opt_result_optimization AS opt_id,
                  lab_opt_result_strategy AS st, lab_opt_result_account AS ac,
                  lab_opt_result_campaign AS ca, ROUND(lab_opt_result_balance, 2) AS balance
           FROM lab_opt_result WHERE lab_opt_result_id = %s""", (rid,))
    if not r:
        raise HTTPException(404, "Không tìm thấy alpha")
    noi_dung, truong, ten = _tach_alpha(r["st"])
    try:
        ac = json.loads(r["ac"] or "{}")
    except Exception:
        ac = {}
    try:
        ca = json.loads(r["ca"] or "[]")
    except Exception:
        ca = []
    goc = fetch_one("SELECT lab_account_db AS dataset FROM lab_account WHERE lab_account_id = "
                    "(SELECT lab_opt_account FROM lab_optimization WHERE lab_opt_id = %s)",
                    (r["opt_id"],)) or {}
    phien = fetch_one("SELECT lab_opt_data_leng AS dl FROM lab_optimization WHERE lab_opt_id = %s",
                      (r["opt_id"],)) or {}
    return {
        "id": rid,
        "opt_id": r["opt_id"],
        "balance": r["balance"],
        "ten_goi_y": f"ALPHA-{r['opt_id']}-{rid}" + (f"-{ten}" if ten else ""),
        "luong": list(noi_dung.keys()),
        "truong": truong,
        "so_coin": len(ca),
        "coin": [c.get("lab_campaign_symbol") for c in ca[:12]],
        "von": ac.get("lab_account_margin_balance") or ac.get("lab_account_balance"),
        "margin_type": ac.get("lab_account_margin_type") or "CROSS",
        "data_type": ac["lab_account_data_type"] if "lab_account_data_type" in ac else "1m",
        "data_len": phien.get("dl") or 1,
        "compound": ac.get("lab_account_compound"),
        "reserve": ac.get("lab_account_reserve"),
        "dataset_goi_y": goc.get("dataset") or ac.get("lab_account_db"),
        "run_id": _da_dung_run().get(rid),
    }


@app.post("/api/base/alpha-moi/{rid}/tao-run")
def tao_run_tu_alpha(rid: int, body: dict = Body(default={})):
    """Dựng một alpha thành lần chạy thật để backtest được.

    Chỉ thêm bản ghi mới (chiến lược, lần chạy, danh sách coin) — không đụng
    vào bất kỳ dòng nào của hệ thống cũ.
    """
    da = _da_dung_run()
    if rid in da and not body.get("cho_trung"):
        return {"result": True, "run_id": da[rid], "da_co": True,
                "message": f"Alpha này đã được dựng thành lần chạy {da[rid]}"}

    r = fetch_one(
        """SELECT lab_opt_result_optimization AS opt_id, lab_opt_result_strategy AS st,
                  lab_opt_result_account AS ac, lab_opt_result_campaign AS ca
           FROM lab_opt_result WHERE lab_opt_result_id = %s""", (rid,))
    if not r:
        raise HTTPException(404, "Không tìm thấy alpha")

    if _co_bo_chua(r["st"]):
        raise HTTPException(
            400, "Alpha này sinh từ bộ chứa nhiều chiến lược con — dựng lại cần tạo cả "
                 "bảng liên kết bộ chứa, chưa hỗ trợ")
    noi_dung, truong, ten_luong = _tach_alpha(r["st"])
    if not noi_dung:
        raise HTTPException(400, "Ảnh chụp chiến lược trống, không dựng được")

    ac = json.loads(r["ac"] or "{}")
    ca = json.loads(r["ca"] or "[]")
    if not ca:
        raise HTTPException(400, "Alpha này không kèm danh sách coin nào")

    ten = (body.get("name") or f"ALPHA-{r['opt_id']}-{rid}").strip()
    dataset = (body.get("dataset") or ac.get("lab_account_db") or "").strip()
    if not dataset:
        goc = fetch_one("SELECT lab_account_db AS d FROM lab_account WHERE lab_account_id = "
                        "(SELECT lab_opt_account FROM lab_optimization WHERE lab_opt_id = %s)",
                        (r["opt_id"],)) or {}
        dataset = goc.get("d") or ""
    if not dataset:
        raise HTTPException(400, "Chưa chọn bộ dữ liệu nến")
    von = float(body.get("balance") or ac.get("lab_account_margin_balance")
                or ac.get("lab_account_balance") or 10000)

    # Khối dữ liệu phải lấy đúng của phiên đào; chạy khối khác là ra kết quả khác.
    phien = fetch_one("SELECT lab_opt_data_leng AS dl FROM lab_optimization WHERE lab_opt_id = %s",
                      (r["opt_id"],)) or {}
    data_len = int(body.get("data_len") or phien.get("dl") or 1)

    with cursor() as c:
        c.execute(
            """INSERT INTO lab_strategies
                 (lab_strategy_name, lab_strategy_content, lab_strategy_takeprofit,
                  lab_strategy_stoploss, lab_strategy_baseprofit, lab_strategy_stepprofit,
                  lab_strategy_backprofit, lab_strategy_baseprofit_baseon,
                  lab_strategy_timelife, lab_strategy_interval, lab_strategy_margin,
                  lab_strategy_note, lab_strategy_group)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (ten, json.dumps(noi_dung, ensure_ascii=False),
             truong.get("takeprofit"), truong.get("stoploss"), truong.get("baseprofit"),
             truong.get("step_profit"), truong.get("back_profit"),
             truong.get("baseprofit_baseon"), truong.get("timelife"),
             truong.get("interval"), truong.get("margin"),
             f"Sinh từ phiên đào {r['opt_id']}, kết quả {rid}", NHOM_ALPHA))
        c.connection.commit()
        c.execute("SELECT LAST_INSERT_ID() AS id")
        sid = (c.fetchone() or {}).get("id")

        # Chép nguyên các thiết lập ảnh hưởng tới cách vào lệnh (dồn lãi, vốn dự
        # phòng, kiểu ký quỹ, nhảy nến…) — sai một cái là kết quả chạy lại lệch.
        c.execute(
            """INSERT INTO lab_account
                 (lab_account_name, lab_account_balance, lab_account_margin_balance,
                  lab_account_reserve, lab_account_compound, lab_account_margin_type,
                  lab_account_track_balance, lab_account_running, lab_account_sync,
                  lab_account_leap, lab_account_db, lab_account_data_type,
                  lab_account_data_length, lab_account_server, lab_account_note,
                  lab_account_group)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (ten, von, von,
             ac.get("lab_account_reserve"), ac.get("lab_account_compound"),
             ac.get("lab_account_margin_type") or "CROSS",
             # Giữ nguyên cả giá trị rỗng: ảnh chụp ghi sao thì chạy lại phải vậy,
             # thay rỗng bằng mặc định là đã đổi cách engine tính vốn.
             ac["lab_account_track_balance"] if "lab_account_track_balance" in ac else 1,
             ac["lab_account_sync"] if "lab_account_sync" in ac else 1,
             ac["lab_account_leap"] if "lab_account_leap" in ac else 0,
             dataset,
             # Kiểu dữ liệu quyết định engine khớp lệnh theo nến 1 phút hay không.
             # Ảnh chụp cũ để rỗng thì phải giữ rỗng, ép thành "1m" là đổi cách khớp.
             body.get("data_type") if body.get("data_type") is not None
             else (ac["lab_account_data_type"] if "lab_account_data_type" in ac else "1m"),
             data_len, ctl.NODE, f"{DAU_ALPHA}{rid}", NHOM_ALPHA))
        c.connection.commit()
        c.execute("SELECT LAST_INSERT_ID() AS id")
        run_id = (c.fetchone() or {}).get("id")

        hang = []
        for cp in ca:
            sym = cp.get("lab_campaign_symbol")
            if not sym:
                continue
            hang.append((
                f"{ten}-{sym}", sym,
                cp.get("lab_campaign_start"), cp.get("lab_campaign_stop"),
                cp.get("lab_campaign_params"),
                cp.get("lab_campaign_side") or "BOTH", sid, run_id,
                cp.get("lab_campaign_budget") or von,
                cp.get("lab_campaign_reserve"),
                cp.get("lab_campaign_compound"),
                cp.get("lab_campaign_money"),
                cp.get("lab_campaign_active_budget") or 100,
                cp.get("lab_campaign_priority") or 1,
            ))
        c.executemany(
            """INSERT INTO lab_campaigns
                 (lab_campaign_name, lab_campaign_symbol, lab_campaign_start,
                  lab_campaign_stop, lab_campaign_params, lab_campaign_side,
                  lab_campaign_strategy, lab_campaign_account, lab_campaign_budget,
                  lab_campaign_reserve, lab_campaign_compound, lab_campaign_money,
                  lab_campaign_active_budget, lab_campaign_priority,
                  lab_campaign_status, lab_campaign_running)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '0,0', 0)""",
            hang)
        c.connection.commit()

    return {"result": True, "run_id": run_id, "strategy_id": sid,
            "so_coin": len(hang), "dataset": dataset,
            "message": f"Đã dựng lần chạy {run_id} với {len(hang)} coin"}


# ------------------------------------------- chạy lại một backtest đã chạy xong

# Khoá mang ý nghĩa cấu trúc, không phải con số để tinh chỉnh
KHOA_CAU_TRUC = {"frame", "column", "index", "type", "enter_price", "name",
                 "baseprofit_baseon", "symbol", "logic", "strategy"}


def _la_so(v):
    if isinstance(v, bool):
        return True
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, str):
        try:
            float(v)
            return True
        except ValueError:
            return False
    return False


def _quet_num(nut, duong, nhan, ra, nhom):
    """Đi khắp cây JSON, nhặt mọi con số có thể chỉnh được kèm đường dẫn tới nó."""
    if isinstance(nut, dict):
        for k, v in nut.items():
            if k in KHOA_CAU_TRUC:
                continue
            _quet_num(v, duong + [k], f"{nhan}.{k}" if nhan else k, ra, nhom)
    elif isinstance(nut, list):
        for i, v in enumerate(nut):
            # phần tử giữa của phép so sánh là toán tử, bỏ qua
            if isinstance(v, str) and v in (">", "<", "=", ">=", "<=", "!="):
                continue
            _quet_num(v, duong + [i], f"{nhan}[{i}]", ra, nhom)
    elif _la_so(nut):
        ra.append({"duong_dan": duong, "nhan": nhan, "gia_tri": nut, "nhom": nhom})


def _num_chien_luoc(sid):
    """Danh sách con số chỉnh được của một chiến lược, gom theo luồng và bậc."""
    st = fetch_one(
        """SELECT lab_strategy_id AS id, lab_strategy_name AS name, lab_strategy_group AS `group`,
                  lab_strategy_content AS content, lab_strategy_takeprofit AS takeprofit,
                  lab_strategy_stoploss AS stoploss, lab_strategy_baseprofit AS baseprofit,
                  lab_strategy_stepprofit AS step_profit, lab_strategy_backprofit AS back_profit,
                  lab_strategy_baseprofit_baseon AS baseprofit_baseon,
                  lab_strategy_timelife AS timelife, lab_strategy_interval AS `interval`,
                  lab_strategy_margin AS margin, lab_strategy_container AS container
           FROM lab_strategies WHERE lab_strategy_id = %s""", (sid,))
    if not st:
        return None

    knobs = []
    for k in TRUONG_CHIEN_LUOC:
        if st.get(k) is not None and k != "baseprofit_baseon":
            knobs.append({"duong_dan": ["__truong__", k], "nhan": k,
                          "gia_tri": st[k], "nhom": "Chiến lược"})

    try:
        content = json.loads(st.get("content") or "{}")
    except Exception:
        content = {}

    for ten_luong, luong in content.items():
        if not isinstance(luong, dict):
            _quet_num(luong, [ten_luong], ten_luong, knobs, "Khoá dùng chung")
            continue
        for i, bac in enumerate(luong.get("match") or []):
            _quet_num(bac, [ten_luong, "match", i], "", knobs,
                      f"{ten_luong} · bậc {i}")
        if "stop" in luong:
            _quet_num(luong["stop"], [ten_luong, "stop"], "", knobs,
                      f"{ten_luong} · điều kiện thoát")
        for k, v in luong.items():
            if k in ("match", "stop", "type"):
                continue
            _quet_num(v, [ten_luong, k], k, knobs, f"{ten_luong} · khác")

    return {"id": st["id"], "name": st["name"], "group": st["group"],
            "container": bool(st.get("container")), "tham_so": knobs}


@app.get("/api/runs/{run_id}/tham-so")
def tham_so_chien_luoc(run_id: int):
    """Các con số của chiến lược mà lần chạy này đang dùng."""
    sids = [r["s"] for r in fetch_all(
        "SELECT DISTINCT lab_campaign_strategy AS s FROM lab_campaigns "
        "WHERE lab_campaign_account = %s AND lab_campaign_strategy IS NOT NULL", (run_id,))]
    acc = fetch_one(
        """SELECT lab_account_name AS name, lab_account_db AS dataset,
                  lab_account_balance AS balance, lab_account_data_length AS data_len
           FROM lab_account WHERE lab_account_id = %s""", (run_id,)) or {}
    ds = [x for x in (_num_chien_luoc(s) for s in sids) if x]
    return {"run_id": run_id, "run": acc, "chien_luoc": ds,
            "so_lenh_cu": (fetch_one(
                "SELECT COUNT(*) AS n FROM lab_results WHERE lab_result_account = %s",
                (run_id,)) or {}).get("n", 0)}


def _dat_theo_duong(goc, duong, gia_tri):
    """Ghi một giá trị vào đúng vị trí trong cây JSON theo đường dẫn."""
    nut = goc
    for b in duong[:-1]:
        nut = nut[b]
    cu = nut[duong[-1]]
    # giữ nguyên kiểu dữ liệu cũ để engine đọc y như trước
    if isinstance(cu, bool):
        moi = str(gia_tri).lower() in ("1", "true", "yes")
    elif isinstance(cu, int) and not isinstance(cu, bool):
        moi = int(float(gia_tri))
    elif isinstance(cu, float):
        moi = float(gia_tri)
    else:
        moi = str(gia_tri)
    nut[duong[-1]] = moi
    return cu, moi


@app.post("/api/runs/{run_id}/chay-lai")
def chay_lai(run_id: int, body: dict = Body(default={})):
    """Chạy lại một backtest theo hai kiểu.

      nguyen        — dùng đúng chiến lược cũ, chạy đè lên kết quả cũ
      doi_tham_so   — đổi con số rồi sinh chiến lược mới và lần chạy mới,
                      đi đúng đường sinh alpha đã đối chiếu với engine gốc,
                      nên lần chạy cũ vẫn còn nguyên để so sánh
    """
    kieu = body.get("kieu") or "nguyen"
    cu = fetch_one(
        """SELECT lab_account_id AS id, lab_account_name AS name, lab_account_balance AS balance,
                  lab_account_margin_balance AS margin_balance, lab_account_reserve AS reserve,
                  lab_account_compound AS compound, lab_account_margin_type AS margin_type,
                  lab_account_track_balance AS track_balance, lab_account_sync AS sync,
                  lab_account_leap AS leap, lab_account_db AS db,
                  lab_account_data_type AS data_type, lab_account_data_length AS data_len,
                  lab_account_group AS `group`
           FROM lab_account WHERE lab_account_id = %s""", (run_id,))
    if not cu:
        raise HTTPException(404, "Không tìm thấy lần chạy")

    if kieu == "nguyen":
        return {**ctl.start(run_id), "run_id": run_id, "kieu": "nguyen"}

    sua = body.get("thay_doi") or []
    if not sua:
        raise HTTPException(400, "Chưa đổi con số nào — chọn kiểu giữ nguyên thì hơn")

    # gom thay đổi theo từng chiến lược
    theo_cl = {}
    for x in sua:
        theo_cl.setdefault(int(x["strategy"]), []).append(x)

    ten_moi = (body.get("name") or f"{cu['name']}-v2").strip()
    dataset = (body.get("dataset") or cu["db"] or "").strip()
    if not dataset:
        raise HTTPException(400, "Chưa chọn bộ dữ liệu nến")

    doi_ma, nhat_ky = {}, []
    with cursor() as c:
        for sid, ds in theo_cl.items():
            st = fetch_one("SELECT * FROM lab_strategies WHERE lab_strategy_id = %s", (sid,))
            if not st:
                raise HTTPException(404, f"Không tìm thấy chiến lược {sid}")
            if st.get("lab_strategy_container"):
                raise HTTPException(400, "Chiến lược dạng bộ chứa chưa hỗ trợ đổi tham số")
            content = json.loads(st.get("lab_strategy_content") or "{}")
            truong = {k: st.get("lab_strategy_" + ("stepprofit" if k == "step_profit"
                                                   else "backprofit" if k == "back_profit" else k))
                      for k in TRUONG_CHIEN_LUOC}
            for x in ds:
                duong = x["duong_dan"]
                if duong and duong[0] == "__truong__":
                    k = duong[1]
                    cu_gt, moi_gt = truong.get(k), x["gia_tri"]
                    truong[k] = moi_gt
                else:
                    try:
                        cu_gt, moi_gt = _dat_theo_duong(content, duong, x["gia_tri"])
                    except Exception:
                        raise HTTPException(400, f"Đường dẫn không hợp lệ: {'/'.join(map(str, duong))}")
                nhat_ky.append({"strategy": sid, "duong_dan": duong,
                                "cu": cu_gt, "moi": moi_gt})

            c.execute(
                """INSERT INTO lab_strategies
                     (lab_strategy_name, lab_strategy_content, lab_strategy_takeprofit,
                      lab_strategy_stoploss, lab_strategy_baseprofit, lab_strategy_stepprofit,
                      lab_strategy_backprofit, lab_strategy_baseprofit_baseon,
                      lab_strategy_timelife, lab_strategy_interval, lab_strategy_margin,
                      lab_strategy_note, lab_strategy_group)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (f"{st['lab_strategy_name']}-v2", json.dumps(content, ensure_ascii=False),
                 truong.get("takeprofit"), truong.get("stoploss"), truong.get("baseprofit"),
                 truong.get("step_profit"), truong.get("back_profit"),
                 truong.get("baseprofit_baseon"), truong.get("timelife"),
                 truong.get("interval"), truong.get("margin"),
                 f"Đổi tham số từ chiến lược {sid}, lần chạy {run_id}", NHOM_ALPHA))
            c.connection.commit()
            c.execute("SELECT LAST_INSERT_ID() AS id")
            doi_ma[sid] = (c.fetchone() or {}).get("id")

        c.execute(
            """INSERT INTO lab_account
                 (lab_account_name, lab_account_balance, lab_account_margin_balance,
                  lab_account_reserve, lab_account_compound, lab_account_margin_type,
                  lab_account_track_balance, lab_account_running, lab_account_sync,
                  lab_account_leap, lab_account_db, lab_account_data_type,
                  lab_account_data_length, lab_account_server, lab_account_note,
                  lab_account_group)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (ten_moi, cu["balance"], cu["margin_balance"], cu["reserve"], cu["compound"],
             cu["margin_type"], cu["track_balance"], cu["sync"], cu["leap"],
             dataset, cu["data_type"], cu["data_len"], ctl.NODE,
             f"nora:chaylai:{run_id}", cu["group"] or NHOM_ALPHA))
        c.connection.commit()
        c.execute("SELECT LAST_INSERT_ID() AS id")
        run_moi = (c.fetchone() or {}).get("id")

        c.execute(
            """SELECT lab_campaign_name AS name, lab_campaign_symbol AS symbol,
                      lab_campaign_start AS start, lab_campaign_stop AS stop,
                      lab_campaign_params AS params, lab_campaign_side AS side,
                      lab_campaign_strategy AS strategy, lab_campaign_budget AS budget,
                      lab_campaign_reserve AS reserve, lab_campaign_compound AS compound,
                      lab_campaign_money AS money, lab_campaign_active_budget AS active_budget,
                      lab_campaign_priority AS priority
               FROM lab_campaigns WHERE lab_campaign_account = %s""", (run_id,))
        hang = [(
            f"{ten_moi}-{cp['symbol']}", cp["symbol"], cp["start"], cp["stop"], cp["params"],
            cp["side"], doi_ma.get(cp["strategy"], cp["strategy"]), run_moi,
            cp["budget"], cp["reserve"], cp["compound"], cp["money"],
            cp["active_budget"], cp["priority"],
        ) for cp in c.fetchall()]
        c.executemany(
            """INSERT INTO lab_campaigns
                 (lab_campaign_name, lab_campaign_symbol, lab_campaign_start,
                  lab_campaign_stop, lab_campaign_params, lab_campaign_side,
                  lab_campaign_strategy, lab_campaign_account, lab_campaign_budget,
                  lab_campaign_reserve, lab_campaign_compound, lab_campaign_money,
                  lab_campaign_active_budget, lab_campaign_priority,
                  lab_campaign_status, lab_campaign_running)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, '0,0', 0)""",
            hang)
        c.connection.commit()

    return {"result": True, "kieu": "doi_tham_so", "run_id": run_moi,
            "chien_luoc_moi": doi_ma, "so_coin": len(hang), "thay_doi": nhat_ky,
            "message": f"Đã sinh lần chạy {run_moi} với {len(hang)} coin từ {len(doi_ma)} chiến lược mới"}


# ---------------------------------------------------------------- chỉ số nâng cao

@app.get("/api/dashboard")
def dashboard():
    """Tổng quan toàn hệ thống."""
    return mt.dashboard_summary()


@app.get("/api/runs/{run_id}/metrics")
def get_metrics(run_id: int):
    """Bộ chỉ số đầy đủ: MDD, Sharpe, Sortino, Calmar, Profit Factor, chuỗi thắng/thua."""
    r = mt.full_metrics_cached(run_id)
    if not r or not r.get("trades"):
        raise HTTPException(404, "Lần chạy chưa có kết quả")
    return r


@app.get("/api/runs/{run_id}/metrics-brief")
def get_metrics_brief(run_id: int):
    """Bản rút gọn — không kèm đường vốn, dùng cho bảng danh sách."""
    r = mt.full_metrics_cached(run_id)
    if not r or not r.get("trades"):
        raise HTTPException(404, "Lần chạy chưa có kết quả")
    r.pop("equity_daily", None)
    return r

# ---------------------------------------------------------------- chiến thuật

@app.get("/api/strategies")
def list_strategies(group: str = None, q_: str = Query(None, alias="q"), limit: int = 200):
    where, params = ["1=1"], []
    if group:
        where.append("lab_strategy_group = %s")
        params.append(group)
    if q_:
        where.append("lab_strategy_name LIKE %s")
        params.append(f"%{q_}%")
    rows = fetch_all(
        f"""SELECT lab_strategy_id AS id, lab_strategy_name AS name,
                   lab_strategy_group AS `group`, lab_strategy_container AS is_container,
                   lab_strategy_takeprofit AS takeprofit, lab_strategy_stoploss AS stoploss,
                   lab_strategy_margin AS margin, lab_strategy_timelife AS timelife,
                   CHAR_LENGTH(lab_strategy_content) AS content_size
            FROM lab_strategies WHERE {' AND '.join(where)}
            ORDER BY lab_strategy_id DESC LIMIT %s""",
        params + [limit],
    )
    return {"rows": rows}


@app.get("/api/strategies/{sid}")
def get_strategy(sid: int):
    row = fetch_one(
        """SELECT lab_strategy_id AS id, lab_strategy_name AS name,
                  lab_strategy_group AS `group`, lab_strategy_content AS content,
                  lab_strategy_note AS note, lab_strategy_container AS is_container,
                  lab_strategy_takeprofit AS takeprofit, lab_strategy_stoploss AS stoploss,
                  lab_strategy_margin AS margin, lab_strategy_timelife AS timelife
           FROM lab_strategies WHERE lab_strategy_id = %s""",
        (sid,),
    )
    if not row:
        raise HTTPException(404, "Không tìm thấy chiến thuật")
    if row["is_container"]:
        row["children"] = fetch_all(
            """SELECT c.lab_stra_con_child AS id, s.lab_strategy_name AS name,
                      c.lab_stra_con_weight AS weight, c.lab_stra_con_slot AS slot
               FROM lab_strategy_container c
               JOIN lab_strategies s ON s.lab_strategy_id = c.lab_stra_con_child
               WHERE c.lab_stra_con_container = %s ORDER BY c.lab_stra_con_weight""",
            (sid,),
        )
    return row


@app.get("/api/strategy-groups")
def strategy_groups():
    return {
        "rows": fetch_all(
            """SELECT lab_strategy_group AS name, COUNT(*) AS n FROM lab_strategies
               WHERE lab_strategy_group IS NOT NULL AND lab_strategy_group <> ''
               GROUP BY lab_strategy_group ORDER BY n DESC"""
        )
    }




# ---------------------------------------------------------------- đào chiến lược

@app.get("/api/miner/optimizations")
def list_optimizations(limit: int = 60, q_: str = Query(None, alias="q")):
    """Các phiên đào chiến lược (grid-search tham số)."""
    where, params = ["1=1"], []
    if q_:
        where.append("lab_opt_name LIKE %s")
        params.append(f"%{q_}%")
    rows = fetch_all(
        f"""SELECT lab_opt_id AS id, lab_opt_name AS name, lab_opt_account AS base_run,
                   lab_opt_thread AS workers, lab_opt_data_leng AS data_len,
                   lab_opt_start_time AS start_time, lab_opt_stop_time AS stop_time,
                   lab_opt_server AS node, CHAR_LENGTH(lab_opt_params) AS params_size
            FROM lab_optimization WHERE {' AND '.join(where)}
            ORDER BY lab_opt_id DESC LIMIT %s""",
        params + [limit],
    )
    if rows:
        ids = tuple(r["id"] for r in rows)
        ph = ",".join(["%s"] * len(ids))
        done = {
            d["o"]: d
            for d in fetch_all(
                f"""SELECT lab_opt_result_optimization AS o, COUNT(*) AS tong,
                           SUM(lab_opt_result_done = 1) AS xong
                    FROM lab_opt_result WHERE lab_opt_result_optimization IN ({ph})
                    GROUP BY lab_opt_result_optimization""",
                list(ids),
            )
        }
        for r in rows:
            d = done.get(r["id"], {})
            r["total"] = d.get("tong", 0)
            r["done"] = d.get("xong", 0)
    return {"rows": rows}


@app.get("/api/miner/optimizations/{oid}")
def get_optimization(oid: int):
    row = fetch_one(
        """SELECT lab_opt_id AS id, lab_opt_name AS name, lab_opt_account AS base_run,
                  lab_opt_params AS params, lab_opt_thread AS workers,
                  lab_opt_log AS log, lab_opt_note AS note
           FROM lab_optimization WHERE lab_opt_id = %s""",
        (oid,),
    )
    if not row:
        raise HTTPException(404, "Không tìm thấy phiên đào")
    return row


# ------------------------------------------------- tham số quét của phiên đào

MAX_WORKERS = 6   # trần cứng của ResourceGuard, không được vượt

def _doc_bien(raw):
    """Tách chuỗi JSON tham số thành danh sách biến dễ chỉnh.

    Ba kiểu biến trong dữ liệu gốc:
      INPUT       — danh sách giá trị rời, mỗi giá trị là một nhánh quét
      SETS        — danh sách bộ giá trị (ví dụ tỷ lệ vốn từng bậc DCA)
      EXPRESSIONS — công thức tính từ biến khác, viết dạng #tên_biến#
    Chỉ INPUT và SETS mới nhân số tổ hợp lên.
    """
    try:
        arr = json.loads(raw or "[]")
    except Exception:
        return [], 0
    bien, to_hop = [], 1
    for b in arr if isinstance(arr, list) else []:
        d = b.get("data")
        kieu = b.get("type") or "INPUT"
        if isinstance(d, list):
            gia_tri = [json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else str(x)
                       for x in d]
            to_hop *= max(1, len(gia_tri))
        else:
            gia_tri = [str(d)] if d is not None else []
        bien.append({
            "id": b.get("id"),
            "name": b.get("name"),
            "type": kieu,
            "values": gia_tri,
            "quet": kieu in ("INPUT", "SETS"),
        })
    return bien, to_hop


def _viet_bien(bien):
    """Dựng lại chuỗi JSON tham số từ danh sách biến đã chỉnh."""
    ra = []
    for b in bien:
        kieu = b.get("type") or "INPUT"
        gia_tri = [str(v).strip() for v in (b.get("values") or []) if str(v).strip() != ""]
        if kieu == "EXPRESSIONS":
            data = gia_tri[0] if gia_tri else ""
        else:
            data = []
            for v in gia_tri:
                if v.startswith("[") or v.startswith("{"):
                    try:
                        data.append(json.loads(v))
                        continue
                    except Exception:
                        pass
                data.append(v)
        ra.append({"id": str(b.get("id") or ""), "name": b.get("name"),
                   "type": kieu, "data": data})
    return json.dumps(ra, ensure_ascii=False)


def _chien_luoc_cua_run(run_id: int):
    """Các mã chiến lược mà một lần chạy đang dùng."""
    rows = fetch_all(
        "SELECT DISTINCT lab_campaign_strategy AS s FROM lab_campaigns "
        "WHERE lab_campaign_account = %s AND lab_campaign_strategy IS NOT NULL",
        (run_id,),
    )
    return [r["s"] for r in rows if r["s"]]


def _phien_tot_nhat(opt_ids):
    """Trong các phiên đã cho, lấy tổ hợp cho số dư cuối cao nhất."""
    if not opt_ids:
        return None
    ph = ",".join(["%s"] * len(opt_ids))
    return fetch_one(
        f"""SELECT lab_opt_result_optimization AS opt_id,
                   lab_opt_result_params        AS params,
                   ROUND(lab_opt_result_balance, 2) AS balance
            FROM lab_opt_result
            WHERE lab_opt_result_optimization IN ({ph}) AND lab_opt_result_done = 1
            ORDER BY lab_opt_result_balance DESC LIMIT 1""",
        list(opt_ids),
    )


def _tot_nhat_cho(base_run: int = None, opt: int = None):
    """Tìm bộ tham số cho lợi tức cao nhất để làm mẫu điền sẵn.

    Ưu tiên từ gần tới xa:
      1. chính phiên đang xem
      2. các phiên quét trên đúng lần chạy này
      3. các phiên quét trên lần chạy khác nhưng dùng cùng chiến lược
    Không có gì thì thôi, không bịa số.
    """
    if opt:
        kq = _phien_tot_nhat([opt])
        if kq:
            return kq, "chính phiên này"

    if base_run:
        ids = [r["id"] for r in fetch_all(
            "SELECT lab_opt_id AS id FROM lab_optimization WHERE lab_opt_account = %s",
            (base_run,))]
        kq = _phien_tot_nhat(ids)
        if kq:
            return kq, "phiên quét khác trên cùng lần chạy"

        chien_luoc = _chien_luoc_cua_run(base_run)
        if chien_luoc:
            ph = ",".join(["%s"] * len(chien_luoc))
            ids = [r["id"] for r in fetch_all(
                f"""SELECT DISTINCT o.lab_opt_id AS id
                    FROM lab_optimization o
                    JOIN lab_campaigns c ON c.lab_campaign_account = o.lab_opt_account
                    WHERE c.lab_campaign_strategy IN ({ph})""",
                list(chien_luoc))]
            kq = _phien_tot_nhat(ids)
            if kq:
                return kq, "phiên quét của chiến lược này"

    # Không có gì gần thì lấy phiên lợi tức cao nhất toàn hệ thống làm mẫu khởi đầu,
    # và nói rõ nó không cùng chiến lược để người dùng còn biết mà sửa.
    kq = fetch_one(
        """SELECT lab_opt_result_optimization AS opt_id, lab_opt_result_params AS params,
                  ROUND(lab_opt_result_balance, 2) AS balance
           FROM lab_opt_result WHERE lab_opt_result_done = 1
           ORDER BY lab_opt_result_balance DESC LIMIT 1"""
    )
    if kq:
        return kq, "phiên lợi tức cao nhất trong hệ thống (khác chiến lược)"
    return None, None


def _gan_tot_nhat(bien, kq):
    """Gắn giá trị thắng cuộc vào từng biến để hiện làm gợi ý."""
    if not kq:
        return bien
    try:
        thang = json.loads(kq["params"] or "{}")
    except Exception:
        thang = {}
    for b in bien:
        ten = b.get("name")
        v = thang.get(f"#{ten}#")
        if v is None and b.get("type") == "SETS":
            # bộ giá trị bị trải phẳng thành #tên[0]#, #tên[1]#…
            bo, i = [], 0
            while f"#{ten}[{i}]#" in thang:
                bo.append(thang[f"#{ten}[{i}]#"])
                i += 1
            v = bo or None
        if v is not None:
            b["tot_nhat"] = (json.dumps(v, ensure_ascii=False)
                             if isinstance(v, (list, dict)) else str(v))
    return bien


@app.get("/api/miner/mau")
def mau_tham_so(base_run: int = None, opt: int = None):
    """Bộ tham số mẫu để mở sẵn khi tạo phiên đào mới.

    Lấy cấu trúc biến từ phiên quét gần nhất của lần chạy, và điền kèm giá trị
    của tổ hợp cho lợi tức cao nhất — có cái để bắt đầu thay vì màn hình trắng.
    """
    kq, nguon = _tot_nhat_cho(base_run, opt)
    goc_id = opt or (kq or {}).get("opt_id")
    if not goc_id:
        return {"bien": [], "to_hop": 0, "tot_nhat": None,
                "max_workers": MAX_WORKERS, "workers": 2, "data_len": 10,
                "node": ctl.NODE, "base_run": base_run,
                "ghi_chu": "Chưa có phiên quét nào cho lần chạy này để lấy làm mẫu"}

    goc = fetch_one(
        """SELECT lab_opt_id AS id, lab_opt_name AS name, lab_opt_params AS params,
                  lab_opt_thread AS workers, lab_opt_data_leng AS data_len,
                  lab_opt_server AS node
           FROM lab_optimization WHERE lab_opt_id = %s""",
        (goc_id,),
    ) or {}
    bien, to_hop = _doc_bien(goc.get("params"))
    bien = _gan_tot_nhat(bien, kq)

    return {
        "base_run": base_run or None,
        "workers": min(goc.get("workers") or 2, MAX_WORKERS),
        "data_len": goc.get("data_len") or 10,
        "node": goc.get("node") or ctl.NODE,
        "max_workers": MAX_WORKERS,
        "bien": bien,
        "to_hop": to_hop,
        "tot_nhat": {
            "opt_id": goc.get("id"),
            "opt_name": goc.get("name"),
            "balance": (kq or {}).get("balance"),
            "nguon": nguon,
        } if kq else None,
    }


@app.get("/api/miner/optimizations/{oid}/params")
def optimization_params(oid: int):
    """Tham số quét của một phiên, đã tách sẵn để chỉnh trên giao diện."""
    row = fetch_one(
        """SELECT lab_opt_id AS id, lab_opt_name AS name, lab_opt_account AS base_run,
                  lab_opt_params AS params, lab_opt_thread AS workers,
                  lab_opt_data_leng AS data_len, lab_opt_server AS node
           FROM lab_optimization WHERE lab_opt_id = %s""",
        (oid,),
    )
    if not row:
        raise HTTPException(404, "Không tìm thấy phiên đào")
    bien, to_hop = _doc_bien(row.pop("params"))
    kq, nguon = _tot_nhat_cho(row.get("base_run"), oid)
    bien = _gan_tot_nhat(bien, kq)
    return {
        **row, "bien": bien, "to_hop": to_hop, "max_workers": MAX_WORKERS,
        "tot_nhat": {"opt_id": (kq or {}).get("opt_id"), "balance": (kq or {}).get("balance"),
                     "nguon": nguon} if kq else None,
    }


@app.post("/api/miner/optimizations")
def create_optimization(body: dict = Body(...)):
    """Lưu bộ tham số đã tinh chỉnh thành một phiên quét MỚI.

    Cố ý không ghi đè phiên cũ: bảng này dùng chung với hệ thống thật, sửa
    thẳng vào một phiên đang có kết quả là xoá mất lịch sử của người khác.
    """
    ten = (body.get("name") or "").strip()
    base_run = body.get("base_run")
    bien = body.get("bien") or []
    if not ten:
        raise HTTPException(400, "Chưa đặt tên phiên")
    if not base_run:
        raise HTTPException(400, "Chưa chọn lần chạy gốc")
    if not bien:
        raise HTTPException(400, "Chưa có biến nào để quét")

    workers = max(1, min(int(body.get("workers") or 2), MAX_WORKERS))
    data_len = max(1, int(body.get("data_len") or 10))
    node = body.get("node") or ctl.NODE
    params = _viet_bien(bien)
    _, to_hop = _doc_bien(params)

    with cursor() as c:
        c.execute(
            """INSERT INTO lab_optimization
                 (lab_opt_name, lab_opt_account, lab_opt_params, lab_opt_thread,
                  lab_opt_data_leng, lab_opt_server, lab_opt_note)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (ten, int(base_run), params, workers, data_len, node,
             "Tạo từ giao diện Nora"),
        )
        c.connection.commit()
        c.execute("SELECT LAST_INSERT_ID() AS id")
        moi_id = (c.fetchone() or {}).get("id")

    return {"id": moi_id, "to_hop": to_hop, "workers": workers}


@app.get("/api/miner/optimizations/{oid}/progress")
def optimization_progress(oid: int):
    return ctl.opt_progress(oid)


@app.post("/api/miner/optimizations/{oid}/start")
def optimization_start(oid: int):
    r = ctl.opt_start(oid)
    if not r.get("result"):
        raise HTTPException(400, r.get("message") or "Không chạy được phiên quét")
    return r


@app.post("/api/miner/optimizations/{oid}/stop")
def optimization_stop(oid: int):
    return ctl.opt_stop(oid)


@app.get("/api/miner/optimizations/{oid}/log")
def optimization_log(oid: int, tail: int = 120):
    return ctl.opt_log(oid, tail)


@app.get("/api/miner/optimizations/{oid}/results")
def optimization_results(oid: int, limit: int = 100, sort: str = "balance"):
    """Bảng xếp hạng các tổ hợp tham số. LUÔN lọc theo phiên — bảng có 102.860 dòng."""
    order = {
        "balance": "lab_opt_result_balance DESC",
        "position": "lab_opt_result_total_position DESC",
        "invest": "lab_opt_result_invest_max ASC",
        "unrealize": "lab_opt_result_unrelize_max ASC",
    }.get(sort, "lab_opt_result_balance DESC")
    rows = fetch_all(
        f"""SELECT lab_opt_result_id AS id, lab_opt_result_params AS params,
                   ROUND(lab_opt_result_balance, 2)        AS balance,
                   ROUND(lab_opt_result_margin_balance, 2) AS margin_balance,
                   ROUND(lab_opt_result_unrelize_max, 2)   AS unrealize_max,
                   ROUND(lab_opt_result_invest_max, 2)     AS invest_max,
                   lab_opt_result_total_position           AS positions,
                   lab_opt_result_total_long               AS longs,
                   lab_opt_result_total_short              AS shorts,
                   lab_opt_result_total_takeprofit         AS takeprofit,
                   lab_opt_result_total_stoploss           AS stoploss,
                   lab_opt_result_interval_avg             AS interval_avg,
                   lab_opt_result_done                     AS done
            FROM lab_opt_result WHERE lab_opt_result_optimization = %s
            ORDER BY {order} LIMIT %s""",
        (oid, limit),
    )
    for r in rows:
        tp = r["takeprofit"] or 0
        sl = r["stoploss"] or 0
        tot = tp + sl
        r["winrate"] = round(100 * tp / tot, 1) if tot else None
    return {"rows": rows}

# ---------------------------------------------------------------- biểu đồ

@app.get("/api/runs/{run_id}/chart-options")
def chart_options(run_id: int):
    """Coin và ngày có nhiều lệnh nhất — để giao diện gợi ý sẵn."""
    return {
        "symbols": fetch_all(
            """SELECT lab_result_symbol AS symbol, COUNT(*) AS n FROM lab_results
               WHERE lab_result_account = %s GROUP BY lab_result_symbol ORDER BY n DESC""",
            (run_id,),
        ),
        "presets": [
            {"id": "keltner9", "name": "Biên độ — dải Keltner"},
            {"id": "macross", "name": "Bám xu hướng — EMA × WMA"},
            {"id": "dca", "name": "DCA — RSI"},
            {"id": "all", "name": "Tất cả"},
        ],
    }


@app.get("/api/runs/{run_id}/chart-days")
def chart_days(run_id: int, symbol: str, limit: int = 20):
    return {
        "rows": fetch_all(
            """SELECT DATE(FROM_UNIXTIME(lab_result_chart / 1000)) AS ngay, COUNT(*) AS n
               FROM lab_results
               WHERE lab_result_account = %s AND lab_result_symbol = %s AND lab_result_chart > 0
               GROUP BY ngay ORDER BY n DESC, ngay DESC LIMIT %s""",
            (run_id, symbol, limit),
        )
    }


@app.post("/api/runs/{run_id}/chart")
def make_chart(run_id: int, symbol: str, day: str, frame: str = "4h", indicator: str = "keltner9"):
    """Sinh biểu đồ nến kèm chỉ báo và điểm vào lệnh."""
    fname = f"backtest_{run_id}_{symbol}_{day}.html"
    cmd = [
        "taskset", "-c", "8-11", "nice", "-n", "10",
        PYBIN, "manage.py", "backtest_chart",
        "-a", str(run_id), "-s", symbol, "-d", day,
        "--indicator", indicator, "--frame", frame,
    ]
    try:
        p = subprocess.run(cmd, cwd=MONITOR_DIR, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Sinh biểu đồ quá lâu (>180 giây)")
    path = CHART_DIR / fname
    if not path.exists():
        tail = (p.stdout or p.stderr or "")[-400:]
        raise HTTPException(500, f"Không sinh được biểu đồ. {tail}")
    return {"file": fname, "url": f"/charts/{fname}", "log": (p.stdout or "")[-600:]}


if CHART_DIR.exists():
    app.mount("/charts", StaticFiles(directory=str(CHART_DIR)), name="charts")


# ---------------------------------------------------------------- giao diện

WEB = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if WEB.exists():
    app.mount("/assets", StaticFiles(directory=str(WEB / "assets")), name="assets")

    # index.html trỏ tới tên tệp có băm nội dung; nếu trình duyệt giữ lại bản cũ
    # thì người dùng vẫn thấy giao diện cũ sau khi đã build lại. Bắt kiểm tra lại
    # mỗi lần tải — riêng /assets có băm trong tên nên nhớ đệm thoải mái.
    def trang_chu():
        return FileResponse(WEB / "index.html",
                            headers={"Cache-Control": "no-cache, must-revalidate"})

    @app.get("/")
    def index():
        return trang_chu()

    @app.get("/{path:path}")
    def spa(path: str):
        f = WEB / path
        if f.is_file():
            return FileResponse(f)
        return trang_chu()


@app.get("/api/health")
def health():
    return {"ok": True}
