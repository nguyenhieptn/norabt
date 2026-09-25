"""Phân loại "zone" (EMERGENCY / CAUTION / bình thường) từ đúng MỘT chuỗi
đầu vào -- `headline` (== `recommendation.verdict`, cũng chính là phần đầu
dòng CONCLUSION trong `recommendation.text`).

TÁCH RA THÀNH MODULE RIÊNG (23/09), thay vì để logic này nằm cố định trong
`web/report_page.py`'s `_render_conclusion`: đó là nơi DUY NHẤT sinh ra
badge "EMERGENCY ZONE -- SEVERE RISK"/"ELEVATED CAUTION ZONE" mà người dùng
thấy trên report tĩnh, nhưng `llm/chat.py` cũng cần biết đúng cùng một phân
loại đó để trả lời câu hỏi rủi ro tổng quát bằng đúng headline người dùng
đã thấy ở đầu trang -- không phải một câu diễn giải khác đi dù cùng ý.
Nhân bản logic này thẳng vào `chat.py` sẽ tạo đúng kiểu rủi ro lệch-định-
nghĩa mà `chat_knowledge.py`'s module docstring đã cảnh báo (Giai đoạn 7,
5 định nghĩa lệch công thức engine) -- một module dùng chung, MỘT nguồn sự
thật, là cách duy nhất hai nơi không bao giờ trôi lệch nhau qua thời gian.
"""

from __future__ import annotations

ZONE_DANGER = "danger"
ZONE_WARNING = "warning"
ZONE_NORMAL = "success"

# Nhãn HIỂN THỊ, nguyên văn khớp `report_page.py`'s badge text -- một
# thay đổi câu chữ ở badge PHẢI sửa ở đây để chat không tự trích câu cũ.
_ZONE_BADGE_TEXT = {
    ZONE_DANGER: "EMERGENCY ZONE -- SEVERE RISK",
    ZONE_WARNING: "ELEVATED CAUTION ZONE",
    ZONE_NORMAL: "STANDARD RISK ZONE",
}

# Thứ tự nghiêm trọng tăng dần, dùng để so sánh khi áp `min_zone` -- "sàn"
# chỉ có nghĩa nếu có một thứ tự để so "cao hơn"/"thấp hơn" theo.
_ZONE_RANK = {ZONE_NORMAL: 0, ZONE_WARNING: 1, ZONE_DANGER: 2}


def classify_verdict_zone(headline: str, *, min_zone: str = ZONE_NORMAL) -> str:
    """`headline` là phần đầu dòng CONCLUSION (trước dấu " — "), == chính
    `recommendation.verdict` trong bản ghi -- KHÔNG phải toàn bộ câu
    CONCLUSION. Trả về một trong `ZONE_DANGER`/`ZONE_WARNING`/`ZONE_NORMAL`.

    Logic khớp NGUYÊN VĂN `report_page.py`'s `_render_conclusion` trước bản
    vá 23/09 (đã thay bằng lời gọi hàm này) -- không suy đoán lại, chỉ dời
    chỗ ở.

    `min_zone` (23/09, sau đó): SÀN của zone, không phải override -- kết quả
    không bao giờ THẤP hơn `min_zone`, nhưng vẫn có thể cao hơn nếu headline
    tự nó đã đủ nghiêm trọng. Tồn tại cho đúng một ca: một portfolio mà
    `PortfolioVerdict` là `HIGH_CORRELATION_CLUSTER` (nhiều bot thực chất là
    một vị thế nhân bản) nhưng sổ SÁCH GỘP tự nó đọc DRAWDOWN thấp -- hai
    trục khác nhau (rủi ro của sổ gộp, và mức các thành viên trùng nhau) mà
    badge chỉ có MỘT trục để nói. `report_page.py`'s `_render_conclusion` là
    nơi quyết định khi nào truyền `min_zone`; hàm này chỉ biết cách áp sàn,
    không biết khi nào cần áp."""
    upper = (headline or "").upper()
    is_veto = "VETO" in upper
    is_danger = "DRAWDOWN: HIGH" in upper or "HIDDEN RISK" in upper
    if is_veto or is_danger:
        zone = ZONE_DANGER
    elif "CẢNH BÁO" in upper:
        zone = ZONE_WARNING
    else:
        zone = ZONE_NORMAL
    if _ZONE_RANK[zone] < _ZONE_RANK[min_zone]:
        return min_zone
    return zone


def zone_badge_text(headline: str, *, min_zone: str = ZONE_NORMAL) -> str:
    """Nguyên văn badge report tĩnh hiển thị cho `headline` -- luôn có một
    trong ba, kể cả trường hợp "bình thường" (report tĩnh vẫn hiện badge
    "STANDARD RISK ZONE" cho ca đó, không ẩn hẳn)."""
    return _ZONE_BADGE_TEXT[classify_verdict_zone(headline, min_zone=min_zone)]
