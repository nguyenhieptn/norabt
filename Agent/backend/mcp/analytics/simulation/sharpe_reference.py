"""Phân bố Sharpe của quần thể ứng viên — đầu vào V[{SR̂ₙ}] cho deflated Sharpe.

Công thức deflated Sharpe (Bailey và López de Prado, 2014) cần phương sai CHÉO
của Sharpe giữa N ứng viên mà bot này được chọn ra từ đó:

    SR*₀ = √(V[{SR̂ₙ}]) · [(1−γ)·Z⁻¹(1 − 1/N) + γ·Z⁻¹(1 − 1/(N·e))]

Dữ liệu công khai của OKX không kèm sẵn một mốc Sharpe nào để so, và ta cũng
không chấm điểm toàn bộ pool ứng viên (quá đắt). Nhưng V đó vẫn TÍNH RA ĐƯỢC:
chính những bot đã chấm là một mẫu quan sát được của cùng quần thể lead trader
đó. Module này gom Sharpe/lệnh của chúng lại và trả về phương sai mẫu.

Vì sao điều này đáng làm thay vì dùng xấp xỉ: đo trên 30 bot thật của dự án,
phương sai chéo là 0.0877 (độ lệch chuẩn Sharpe/lệnh 0.296), trong khi xấp xỉ
theo giả thuyết không cho một bot 300 lệnh chỉ ra ~0.0033. Ngưỡng
"may mắn chọn được kẻ tốt nhất trong N" vì thế là 0.67 chứ không phải 0.13 —
dùng xấp xỉ là tự hạ chuẩn của mình xuống 5 lần.

Hệ quả phải biết: DSR của một bot giờ PHỤ THUỘC VÀO QUẦN THỂ. Thêm bot mới vào
kho có thể làm DSR của bot cũ đổi. Đó không phải lỗi — đó đúng là điều công
thức nói: "tốt đến mức nào so với những kẻ cùng được sàng" là một câu hỏi tương
đối, không tuyệt đối.
"""

from __future__ import annotations

import json
import statistics
import threading
import time
from pathlib import Path
from typing import Optional

# Dưới mức này thì phương sai mẫu quá nhiễu để làm ngưỡng cho ai cả -- thà rơi
# về bản "giả thuyết không" kèm ghi chú còn hơn dựng một ngưỡng bịa.
MIN_POPULATION = 10

# Kho chỉ đổi sau mỗi đợt chấm điểm (hàng chục phút tới hàng ngày), nên đọc lại
# mỗi 10 phút là quá đủ mới, mà vẫn tránh quét đĩa ở mọi lượt phân tích.
CACHE_TTL_SECONDS = 600.0

_LOCK = threading.Lock()
_CACHE: dict = {}


def _scan(analysis_dir: Path) -> Optional[float]:
    values = []
    for path in analysis_dir.glob("**/monte_carlo.json"):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        sharpe = doc.get("sharpe_per_trade")
        if isinstance(sharpe, (int, float)) and sharpe == sharpe:  # loại NaN
            values.append(float(sharpe))
    if len(values) < MIN_POPULATION:
        return None
    return float(statistics.variance(values))


def population_sharpe_variance(data_dir: Path) -> Optional[float]:
    """V[{SR̂ₙ}] đo trên các bot đã chấm, hoặc `None` nếu chưa đủ mẫu.

    Có khoá và có TTL vì hàm này bị gọi từ nhiều luồng phân tích cùng lúc (xem
    phần song song hoá trong pipeline) và mỗi lần quét là một lượt đi đĩa.
    """
    analysis_dir = Path(data_dir) / "analysis"
    key = str(analysis_dir)
    now = time.monotonic()
    with _LOCK:
        hit = _CACHE.get(key)
        if hit is not None and now - hit[0] < CACHE_TTL_SECONDS:
            return hit[1]
    value = _scan(analysis_dir)
    with _LOCK:
        _CACHE[key] = (now, value)
    return value


def reset_cache() -> None:
    """Xoá bộ đệm -- chỉ dùng trong test để các ca không dính dữ liệu của nhau."""
    with _LOCK:
        _CACHE.clear()
