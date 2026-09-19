"""Phân bố quần thể của các tham số mô phỏng, để chấm điểm bằng PHÂN VỊ THẬT
thay vì bằng ngưỡng do người viết nghĩ ra.

VẤN ĐỀ MODULE NÀY GIẢI: cách chấm cũ ở nhánh bot giấu sổ lệnh
(`Agent/backend/analysis/limited.py`) đi thẳng từ một con số đo được sang một
điểm rủi ro bằng những cut-point tự đặt:

    score = 15.0
    if max_dd_pct > 30: score += 50
    elif max_dd_pct > 15: score += 25

Không có lý thuyết nào nói "sụt 30% thì cộng 50 điểm". Ba con số đó không suy
ra từ đâu, không hiệu chỉnh trên dữ liệu nào, và không ai kiểm chứng được
chúng đúng hay sai -- đúng thứ chủ dự án gọi là "chọn bừa con số".

CÁCH THAY THẾ, VÀ VÌ SAO NÓ CÓ SỞ CỨ: 30 bot đã chấm trong kho tạo thành một
mẫu quan sát được của chính quần thể lead trader mà bot đang xét thuộc về.
Với mỗi tham số, điểm của một bot là **hạng phân vị của chính nó trong quần
thể đó**:

    điểm = 100 x (số bot trong quần thể có tham số TỐT HƠN bot này) / N

Đọc thẳng ra tiếng Việt: "điểm 80" nghĩa là "tệ hơn 80% số bot đã quan sát ở
chiều này". Không còn con số nào do người viết chọn: mọi mốc đều là dữ liệu
thật, và mốc tự dịch chuyển khi quần thể đổi.

Đây KHÔNG phải ý tưởng mới trong dự án -- `Agent/backend/mcp/analytics/
simulation/sharpe_reference.py` đã dùng đúng nguyên tắc "quần thể đã chấm là
mẫu của quần thể ứng viên" để lấy V[{SR̂ₙ}] cho deflated Sharpe. Module này
mở rộng nguyên tắc đó sang các tham số mô phỏng khác.

HỆ QUẢ PHẢI BIẾT (giống hệt cảnh báo của `sharpe_reference`): điểm theo phân
vị là điểm TƯƠNG ĐỐI. Thêm bot mới vào kho có thể làm điểm của bot cũ đổi.
Đó không phải lỗi -- đó đúng là điều mà câu hỏi "tệ tới mức nào SO VỚI những
bot cùng loại" hàm ý.

ĐIỀU MODULE NÀY KHÔNG LÀM: nó không quyết định tham số nào đáng chấm, không
gán trọng số, và không chấm chiều nào không có tham số so sánh được. Thiếu
quần thể thì trả `None` để nơi gọi rơi về nhánh "không đo được", chứ không
dựng một thang thay thế.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

__all__ = [
    "MIN_POPULATION",
    "clear_cache",
    "PARAMETER_DIRECTION",
    "percentile_rank",
    "population_values",
    "population_percentile",
]

# Dưới ngần này bot thì phân vị quá thô để nói lên điều gì: với N=5, mỗi bot
# nhảy 20 điểm một bậc. Lấy đúng ngưỡng `sharpe_reference.MIN_POPULATION`
# đang dùng cho cùng loại suy luận "quần thể đã chấm làm mẫu", để hai chỗ
# không nói hai chuẩn khác nhau.
MIN_POPULATION = 10

# Kho chỉ đổi sau mỗi đợt chấm (hàng chục phút tới hàng ngày). 600s là con số
# `sharpe_reference` đã dùng cho cùng loại dữ liệu trên cùng thư mục.
_CACHE_TTL_SECONDS = 600.0

# Tên tham số trong `monte_carlo.json` -> hướng "cao hơn là XẤU hơn".
# Đây là phát biểu về NGỮ NGHĨA của từng đại lượng, không phải ngưỡng: xác
# suất cháy tài khoản cao hơn thì rủi ro cao hơn, còn lợi nhuận trung vị cao
# hơn thì rủi ro thấp hơn. Không có con số nào ở đây để mà bịa.
PARAMETER_DIRECTION: Dict[str, bool] = {
    "mc_p_ruin": True,
    "mc_p_loss": True,
    "mc_p95_drawdown": True,
    "mc_worst_drawdown": True,
    "mc_profit_p50_pct": False,
}

_lock = threading.Lock()
_cache: Dict[str, tuple[float, List[float]]] = {}


def clear_cache() -> None:
    """Xoá cache quần thể.

    Cho test (kho giả thay đổi trong cùng một tiến trình, nhanh hơn TTL
    600s rất nhiều) và cho một lượt chấm hàng loạt muốn đọc lại kho ngay
    sau khi vừa ghi. Sản phẩm chạy bình thường không cần gọi: TTL tự lo.
    """
    with _lock:
        _cache.clear()


def _read_population(data_dir: Path, parameter: str) -> List[float]:
    values: List[float] = []
    for path in sorted(data_dir.glob("analysis/**/monte_carlo.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        value = payload.get(parameter)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            continue
        values.append(number)
    values.sort()
    return values


def population_values(data_dir: Path, parameter: str) -> List[float]:
    """Toàn bộ giá trị quan sát được của `parameter` trong kho đã chấm.

    Có cache theo thời gian để không quét đĩa ở mọi lượt phân tích; hỏng file
    nào thì bỏ qua file đó chứ không làm hỏng cả phép đo.
    """
    key = f"{data_dir}::{parameter}"
    now = time.monotonic()
    with _lock:
        cached = _cache.get(key)
        if cached is not None and now - cached[0] < _CACHE_TTL_SECONDS:
            return list(cached[1])
    values = _read_population(data_dir, parameter)
    with _lock:
        _cache[key] = (now, list(values))
    return values


def percentile_rank(
    value: float, population: Sequence[float], higher_is_worse: bool
) -> Optional[float]:
    """Hạng phân vị của `value` trong `population`, thang 0-100 với
    **cao = rủi ro cao hơn** (cùng chiều với thang điểm rủi ro của sản phẩm).

    Dùng định nghĩa phân vị theo hạng giữa (midrank): giá trị bằng nhau nhận
    cùng một hạng nằm giữa dải của chúng, thay vì cho giá trị đầu tiên hưởng
    trọn. Đây là quy ước chuẩn khi có giá trị trùng -- cũng chính là quy ước
    Spearman mà `Agent/backend/research/statistics.py` đang dùng, nên hai chỗ
    trong cùng một sản phẩm không đếm hạng theo hai kiểu khác nhau.

    Trả `None` khi quần thể nhỏ hơn `MIN_POPULATION`: thà nói "không đủ cơ
    sở so sánh" còn hơn dựng một thang trên 3 điểm dữ liệu.
    """
    if len(population) < MIN_POPULATION:
        return None
    below = sum(1 for item in population if item < value)
    equal = sum(1 for item in population if item == value)
    rank = (below + equal / 2.0) / len(population)
    score = rank * 100.0 if higher_is_worse else (1.0 - rank) * 100.0
    return max(0.0, min(100.0, score))


def population_percentile(
    data_dir: Path, parameter: str, value: Optional[float]
) -> Optional[Dict[str, object]]:
    """Điểm phân vị của một tham số, kèm đúng những con số cần để giải thích
    điểm đó cho người đọc (chú thích "sao" trên trang báo cáo đọc từ đây).

    `None` khi thiếu giá trị, thiếu quần thể, hoặc tham số không có hướng
    ngữ nghĩa khai báo trong `PARAMETER_DIRECTION` -- không đoán hướng.
    """
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    direction = PARAMETER_DIRECTION.get(parameter)
    if direction is None:
        return None
    population = population_values(data_dir, parameter)
    score = percentile_rank(float(value), population, direction)
    if score is None:
        return None
    sorted_pop = sorted(population)
    middle = len(sorted_pop) // 2
    median = (
        sorted_pop[middle]
        if len(sorted_pop) % 2
        else (sorted_pop[middle - 1] + sorted_pop[middle]) / 2.0
    )
    return {
        "parameter": parameter,
        "value": float(value),
        "score": score,
        "population_size": len(population),
        "population_median": median,
        "population_min": sorted_pop[0],
        "population_max": sorted_pop[-1],
        "higher_is_worse": direction,
    }
