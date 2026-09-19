"""Registry cấp process cho thanh tiến độ THẬT của `POST /api/analyze`
(xem `/tmp/.../plan_progress.md` mục B, và
`Agent/backend/pipeline.py`/`Agent/backend/web/data.py` cho 5 chặng THẬT
này thật sự bắn callback ở đâu: "ledger" -> "markets" -> "scoring" ->
"decision" (cả bốn trong `RiskSupervisionPipeline.run()`) -> "narrative"
(trong `WebDataService._analyze_full`, ngay trước `_full_result()`) rồi
"done" (cùng chỗ, ngay trước khi trả về).

Vì sao module-level dict, không phải Redis: `backend/run_web.py` chạy
`uvicorn.run(app, ...)` với ĐÚNG một process/một worker (đã xác minh, xem
plan) -- một dict trong bộ nhớ process là đủ và đúng, và né được vòng round
-trip Redis cho một tính năng chỉ cần sống trong đúng vòng đời của MỘT lượt
phân tích (vài chục giây). Mất trạng thái tiến độ khi process khởi động lại
là chấp nhận được: kết quả CHẤM ĐIỂM thật sự (thứ có giá trị lâu dài) vẫn
nằm ở snapshot Redis / assessment.json trên đĩa, không phải ở đây.

Vì sao `threading.Lock`, không phải chỉ dựa vào GIL: pipeline thật sự chạy
trên một worker thread của Starlette (`run_in_threadpool`, xem app.py's
`_run_live_analyze`) -- `mark()`/`finish()`/`fail()` được gọi TỪ thread đó,
trong khi `GET /api/analyze/status` gọi `get()` TỪ thread chính chạy vòng
lặp asyncio. Hai thread khác nhau cùng đọc/ghi một dict Python -- dựa vào
GIL cho một thao tác đơn lẻ (`dict[key] = value`) có thể an toàn, nhưng
`_prune_locked()` bên dưới đọc-rồi-ghi nhiều bước (duyệt, xoá, sắp lại) --
không nguyên tử, cần khoá tường minh.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

# Đúng 5 chặng THẬT (không phải đồng hồ giả) mà pipeline.py + data.py bắn
# callback. Đổi danh sách này PHẢI đổi khớp cả hai nơi gọi `progress(stage)`.
#
# QUYẾT ĐỊNH ĐO THẬT (project owner, 2026-09-17, không đoán -- xem
# plan_progress.md mục A): đo trực tiếp `WebDataService.analyze()` (đúng
# đường /api/analyze thật đi qua) trên 6 bot lấy từ diff `GET
# /api/leaderboard` \ `GET /api/bots` (chưa từng được run_report.py chấm),
# narrative backend tắt hẳn (không tính thời gian CLI Claude -- bước đó
# luôn chạy NỀN, không nằm trên đường chờ, xem `_analyze_full`). 3/6 bot ra
# LIMITED (ledger OKX 60004, dừng ở chặng "ledger", không đo được các chặng
# sau) -- 5 bot còn lại ra FULL, đo được cả "ledger" (nạp sổ lệnh OKX +
# Monte Carlo 10k) và "markets" (giải các thị trường liên quan):
#
#   bot                     ledger(s)  markets(s)  total(s)
#   F2BCA22ABBB69F57          5.220      26.497      31.725
#   3DFF614AE5E0AE92          8.163       7.752      15.925
#   793739635259546051        5.773      14.444      20.230
#   741867347484730662        2.753       1.686       4.444
#   760386676346038930        7.237       8.515      15.759
#   -- trung vị --            5.773       8.515        --
#   -- max/min (phương sai) --  2.97x      15.7x        --
#
# ("scoring"/"decision"/"narrative" luôn <0.01s trên đường chờ -- chấm
# điểm/quyết định là CPU thuần, và narrative chỉ tự khởi một luồng nền rồi
# trả về ngay, xem `_start_background_narrative`.)
#
# CẢ HAI chặng có trọng lượng thật ("ledger", "markets") đều vượt xa
# ngưỡng phương sai 2x plan_progress.md mục A đặt ra (2.97x và 15.7x) --
# phụ thuộc trực tiếp vào nhịp OKX throttle/mạng lúc đó, không phải một
# hằng số ổn định của chính bot. Theo ĐÚNG quy tắc plan đã chốt ("phương
# sai >2x thì đừng hiện % cho chặng đó"), quyết định ở đây là: KHÔNG có bất
# kỳ % / thanh chạy theo trọng số nào trong hợp đồng `GET
# /api/analyze/status` cả -- toàn bộ chặng CHỈ hiện dạng "bước k/5 · tên
# chặng" (`stage_index`/`stage_count`/`stage_label` bên dưới), không có
# trường phần trăm nào được trả về để tránh lộ ra một cách gián tiếp qua
# hình dạng JSON. Không có hằng số trọng số nào cần khai báo vì lựa chọn
# cuối cùng là không dùng trọng số.
STAGES: List[str] = ["ledger", "markets", "scoring", "decision", "narrative"]
STAGE_COUNT = len(STAGES)

# Nhãn tiếng Việt cho từng chặng -- ĐÚNG chữ plan_progress.md mục D đã chốt,
# để app.py trả nguyên văn cho frontend thay vì frontend phải tự dịch lại
# tên chặng kỹ thuật ("ledger", "markets", ...) sang tiếng Việt lần thứ hai.
STAGE_LABELS_VI: Dict[str, str] = {
    "ledger": "Loading trade ledger from OKX",
    "markets": "Resolving related markets",
    "scoring": "Scoring 10 risk dimensions",
    "decision": "Simulation & conclusion",
    "narrative": "Writing narrative",
    "done": "Done",
}

# Bản ghi ĐÃ KẾT THÚC (done/error) được giữ tối đa ngần này trước khi bị
# `_prune_locked` dọn -- đủ lâu để một client poll mỗi 1.5-3s (xem
# plan_progress.md mục D) vẫn kịp thấy trạng thái cuối dù có lỡ vài nhịp,
# nhưng không giữ mãi mãi (registry không được phình theo số mã đã từng
# phân tích trong suốt vòng đời process).
DONE_TTL_SECONDS = 5 * 60

# Trần cứng số bản ghi cùng lúc (running + done/error chưa dọn) -- một bản
# ghi chỉ vài trăm byte, nhưng trần rõ ràng vẫn tốt hơn "để phình theo lưu
# lượng không kiểm soát". Vượt trần thì bản ghi CŨ NHẤT (theo `updated_ms`)
# bị dọn trước, kể cả khi nó đang "running" -- một mã đang chạy quá lâu, bị
# hàng trăm mã khác đè lên, chỉ mất thanh tiến độ (registry) chứ không mất
# kết quả (pipeline vẫn chạy tới cùng, không hề bị huỷ).
MAX_RECORDS = 500

_lock = threading.Lock()
_records: Dict[str, Dict[str, Any]] = {}


def _now_ms() -> int:
    # Đồng hồ ĐƠN ĐIỆU (monotonic) -- registry này chỉ tính khoảng thời
    # gian TRÔI QUA (elapsed), không bao giờ so sánh với một mốc thời gian
    # tường (wall-clock) nào khác, nên monotonic (không bị nhảy lùi bởi
    # NTP/đổi giờ hệ thống) là lựa chọn đúng, giống `_TTLCache` trong
    # data.py đã dùng cho cùng lý do.
    return int(time.monotonic() * 1000)


def _prune_locked() -> None:
    """Dọn bản ghi done/error đã quá `DONE_TTL_SECONDS`, rồi nếu vẫn còn
    vượt `MAX_RECORDS` thì dọn tiếp bản ghi CŨ NHẤT (theo `updated_ms`) cho
    tới khi về trần. PHẢI gọi trong lúc đang giữ `_lock` (hậu tố `_locked`
    chỉ để nhắc điều đó tại chỗ gọi -- hàm này không tự khoá).
    """
    now = _now_ms()
    expired = [
        code
        for code, rec in _records.items()
        if rec["state"] in ("done", "error")
        and now - rec["updated_ms"] > DONE_TTL_SECONDS * 1000
    ]
    for code in expired:
        _records.pop(code, None)
    overflow = len(_records) - MAX_RECORDS
    if overflow > 0:
        oldest = sorted(_records.items(), key=lambda kv: kv[1]["updated_ms"])
        for code, _rec in oldest[:overflow]:
            _records.pop(code, None)


def start(code: str) -> None:
    """Mở một bản ghi "running" mới cho `code`, ghi đè bản ghi cũ (nếu có)
    của chính mã này -- một lượt phân tích mới cho cùng mã luôn thắng, đúng
    tinh thần "start lại từ đầu" chứ không cộng dồn."""
    with _lock:
        now = _now_ms()
        _records[code] = {
            "state": "running",
            "stage": None,
            "stage_index": 0,
            "started_ms": now,
            "updated_ms": now,
            "error": None,
        }
        # Dọn SAU KHI đã chèn bản ghi mới -- prune TRƯỚC khi chèn sẽ đo
        # trần dựa trên kích thước CŨ, để lọt bản ghi thứ (MAX_RECORDS + 1)
        # qua không bị dọn ngay trong chính lượt gọi khiến nó vượt trần.
        _prune_locked()


def mark(code: str, stage: str) -> None:
    """Ghi nhận pipeline vừa BƯỚC VÀO `stage` (một trong `STAGES`) cho
    `code`. No-op im lặng khi `code` không có bản ghi "running" (đã bị
    `_prune_locked` dọn vì quá trần, hoặc `finish`/`fail` đã chốt trước đó,
    hoặc chưa từng `start()`) -- registry chỉ là một chỉ báo phụ trợ, không
    bao giờ được phép làm pipeline thật (nơi gọi hàm này) hỏng vì một race
    hiếm gặp."""
    with _lock:
        rec = _records.get(code)
        if rec is None or rec["state"] != "running":
            return
        try:
            stage_index = STAGES.index(stage) + 1
        except ValueError:
            # Một tên chặng lạ (không nằm trong STAGES) -- không đoán, giữ
            # nguyên stage_index cũ, chỉ cập nhật tên chặng để ít nhất còn
            # hiển thị được cái gì đó thay vì rơi rớt im lặng hoàn toàn.
            stage_index = rec["stage_index"]
        rec["stage"] = stage
        rec["stage_index"] = stage_index
        rec["updated_ms"] = _now_ms()


def finish(code: str) -> None:
    """Chốt `code` là "done" -- kể cả khi chưa từng `start()` (test/edge
    case) thì vẫn tạo một bản ghi done mới, để `get()` sau đó luôn thấy một
    trạng thái nhất quán thay vì None (None nghĩa là "chưa từng biết gì về
    mã này", khác hẳn "đã xong")."""
    with _lock:
        now = _now_ms()
        rec = _records.get(code)
        started = rec["started_ms"] if rec is not None else now
        _records[code] = {
            "state": "done",
            "stage": "done",
            "stage_index": STAGE_COUNT,
            "started_ms": started,
            "updated_ms": now,
            "error": None,
        }
        _prune_locked()


def fail(code: str, message: str) -> None:
    """Chốt `code` là "error" với `message` (tiếng Việt, an toàn để hiện
    thẳng cho người dùng -- xem app.py's các nhánh gọi hàm này, không bao
    giờ truyền thẳng nội dung exception thô/không kiểm soát)."""
    with _lock:
        now = _now_ms()
        rec = _records.get(code)
        started = rec["started_ms"] if rec is not None else now
        stage = rec["stage"] if rec is not None else None
        stage_index = rec["stage_index"] if rec is not None else 0
        _records[code] = {
            "state": "error",
            "stage": stage,
            "stage_index": stage_index,
            "started_ms": started,
            "updated_ms": now,
            "error": message,
        }
        _prune_locked()


def get(code: str) -> Optional[Dict[str, Any]]:
    """Bản sao (không phải object gốc -- an toàn để caller giữ/đọc sau khi
    đã nhả `_lock`) của bản ghi hiện tại cho `code`, hoặc `None` nếu chưa
    từng `start()`/đã bị dọn. Kèm `elapsed_ms` (tính tại thời điểm gọi, từ
    `started_ms`) -- computed ở đây, không lưu sẵn, để luôn phản ánh đúng
    "đã trôi bao lâu TÍNH ĐẾN LÚC POLL", đúng thứ frontend cần cho đồng hồ
    đã trôi (plan_progress.md mục D)."""
    with _lock:
        rec = _records.get(code)
        if rec is None:
            return None
        result = dict(rec)
    result["elapsed_ms"] = max(0, _now_ms() - result["started_ms"])
    result["stage_count"] = STAGE_COUNT
    result["stage_label"] = (
        STAGE_LABELS_VI.get(result["stage"]) if result["stage"] else None
    )
    return result


def _reset_for_tests() -> None:
    """Chỉ dùng trong test -- xoá sạch registry để hai test không thấy bản
    ghi của nhau (registry này là module-level, sống chung giữa mọi
    `create_app()` trong cùng tiến trình test)."""
    with _lock:
        _records.clear()
