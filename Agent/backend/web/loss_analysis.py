"""Hồ sơ THUA LỖ của một bot, tính lại trực tiếp từ sổ lệnh đã chốt.

VÌ SAO TỒN TẠI: trang báo cáo trước đây trả lời được "bot lãi bao nhiêu" và
"sụt vốn tối đa bao nhiêu phần trăm", nhưng KHÔNG trả lời được ba câu mà
người đọc cần để đánh giá cách bot quản trị rủi ro:

  1. Một lệnh tệ nhất mất bao nhiêu so với vốn? (kỷ luật cắt lỗ + cỡ vị thế)
  2. Đợt sụt vốn sâu nhất diễn ra như thế nào -- mất mấy lệnh để rơi, kéo
     dài bao lâu, đã hồi lại chưa?
  3. Chuỗi thua liên tiếp dài nhất làm mất BAO NHIÊU TIỀN? (`max_loss_streak`
     cũ chỉ đếm SỐ LỆNH: "8 lệnh" không nói gì về mức độ thiệt hại.)

Module này CHỈ TÍNH, không dựng HTML -- phần trình bày nằm ở
`Agent/backend/web/report_page.py`. Tách ra để (a) phần logic đáng kiểm thử
được kiểm thử trực tiếp mà không phải dựng cả trang, và (b) giữ phần thêm
vào `report_page.py` đủ nhỏ.

KHÔNG BỊA SỐ -- hai nguyên tắc xuyên suốt:

  * Mọi con số ở đây suy ra từ `closed_trade_series` (`close_time`,
    `realized_pnl`) đã có sẵn trong `evidence`, cộng MỘT mẫu số duy nhất là
    `current_state.reference_capital`. Không có nguồn thứ ba nào.
  * Thiếu vốn tham chiếu thì mọi trường `*_pct` trả `None` -- tuyệt đối
    không thay bằng AUM tự báo cáo, không lấy tổng lãi/lỗ làm mẫu số, không
    coi "không đo được" là "bằng 0".

QUAN HỆ VỚI `performance.max_drawdown_pct` (con số "Sụt vốn tối đa" đã hiện
ở mục "Số liệu giao dịch"): hai tỉ lệ này KHÁC MẪU SỐ và có thể lệch nhau,
nên không được coi là mâu thuẫn:

  * `performance.max_drawdown_pct` chia mỗi mức sụt cho VỐN TẠI ĐÚNG THỜI
    ĐIỂM lệnh đó đóng, đọc từ đường vốn tuần
    (`Agent/backend/mcp/analytics/drawdown/underwater.py`), rồi chặn trần
    100%.
  * `depth_pct` ở đây chia cho MỘT mốc vốn tham chiếu duy nhất
    (`reference_capital`) -- trả lời câu "so với quy mô vốn của bot này thì
    đợt sụt đó lớn cỡ nào", một câu khác hẳn.

Trang báo cáo phải nói rõ sự khác biệt đó ở khối phương pháp luận thay vì
đặt hai phần trăm cạnh nhau như thể chúng đo cùng một thứ.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

__all__ = ["compute_loss_profile"]


# Số lệnh lỗ nặng nhất được liệt kê. 5 đủ để thấy một cú lỗ đơn lẻ là ngoại
# lệ hay là cả một nhóm cùng cỡ (thông tin thật sự cần), mà không biến khối
# này thành một bảng dài thứ hai bên cạnh "Danh sách lệnh đã chốt".
WORST_TRADE_SAMPLE = 5

_MS_PER_HOUR = 3_600_000.0


def _finite(value: Any) -> Optional[float]:
    """`float(value)` nếu đó là một số hữu hạn thật, ngược lại `None`.

    `bool` bị loại thẳng: `True` là `int` trong Python và sẽ lặng lẽ thành
    `1.0`, biến một cờ nào đó thành một khoản lãi 1 USDT.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _pct_of(amount: Optional[float], capital: Optional[float]) -> Optional[float]:
    """`amount` bằng bao nhiêu phần trăm của `capital`.

    `capital` thiếu/không dương -> `None` (xem nguyên tắc "không bịa" ở
    docstring module): không có mẫu số thì không có phần trăm, chấm hết.
    """
    if amount is None or capital is None or capital <= 0.0:
        return None
    return abs(amount) / capital * 100.0


def _ordered_trades(series: Any) -> List[Dict[str, float]]:
    """Các lệnh đã chốt có đủ (`close_time`, `realized_pnl`) hữu hạn, sắp
    theo thời gian đóng tăng dần.

    Lệnh thiếu một trong hai trường bị BỎ QUA hoàn toàn thay vì gán 0: một
    lệnh không đọc được lãi/lỗ không phải là một lệnh hoà vốn, và đưa nó
    vào chuỗi cộng dồn sẽ bóp méo đúng cái đường vốn mà cả module này dựa
    vào. Thứ tự sắp lại ở đây chứ không tin thứ tự sẵn có: `deepest_episode`
    đọc chuỗi cộng dồn theo trục thời gian, một chuỗi xáo trộn sẽ tạo ra
    "đợt sụt vốn" chưa từng xảy ra.
    """
    if not isinstance(series, Sequence) or isinstance(series, (str, bytes)):
        return []
    rows: List[Dict[str, float]] = []
    for item in series:
        if not isinstance(item, Mapping):
            continue
        close_time = _finite(item.get("close_time"))
        pnl = _finite(item.get("realized_pnl"))
        if close_time is None or pnl is None:
            continue
        rows.append({"close_time": close_time, "realized_pnl": pnl})
    rows.sort(key=lambda row: row["close_time"])
    return rows


def _worst_trades(
    trades: List[Dict[str, float]], capital: Optional[float]
) -> List[Dict[str, Any]]:
    """`WORST_TRADE_SAMPLE` lệnh LỖ nặng nhất, nặng nhất đứng đầu.

    Chỉ xét `realized_pnl < 0`: một bot chưa từng lỗ lệnh nào trả về danh
    sách rỗng (đúng sự thật), không phải "lệnh lỗ nhẹ nhất".
    """
    losses = [row for row in trades if row["realized_pnl"] < 0.0]
    losses.sort(key=lambda row: row["realized_pnl"])
    return [
        {
            "pnl": row["realized_pnl"],
            "close_time": row["close_time"],
            "pct_of_capital": _pct_of(row["realized_pnl"], capital),
        }
        for row in losses[:WORST_TRADE_SAMPLE]
    ]


def _worst_losing_streak(
    trades: List[Dict[str, float]], capital: Optional[float]
) -> Optional[Dict[str, Any]]:
    """Chuỗi lệnh LỖ LIÊN TIẾP gây thiệt hại tiền lớn nhất.

    Chọn theo TỔNG TIỀN MẤT, không theo độ dài: một chuỗi 3 lệnh mất 20%
    vốn nguy hiểm hơn hẳn chuỗi 8 lệnh mất 0,5% vốn, trong khi
    `performance.max_loss_streak` (chỉ đếm lệnh) lại xếp hạng ngược lại.
    Trả kèm `count` để đọc cùng con số cũ đó mà không nhầm hai đại lượng.

    Lệnh hoà vốn đúng 0 KHÔNG cắt chuỗi và cũng không cộng gì thêm: nó
    không phải một lệnh thắng, nên coi nó là điểm dừng sẽ chia đôi một đợt
    thua liên tục thành hai đợt nhỏ trông nhẹ hơn thực tế.
    """
    best_total = 0.0
    best_count = 0
    run_total = 0.0
    run_count = 0
    for row in trades:
        pnl = row["realized_pnl"]
        if pnl > 0.0:
            run_total = 0.0
            run_count = 0
            continue
        if pnl == 0.0:
            continue
        run_total += pnl
        run_count += 1
        if run_total < best_total:
            best_total = run_total
            best_count = run_count
    if best_count == 0:
        return None
    return {
        "count": best_count,
        "total_loss": best_total,
        "pct_of_capital": _pct_of(best_total, capital),
    }


def _deepest_episode(
    trades: List[Dict[str, float]], capital: Optional[float]
) -> Optional[Dict[str, Any]]:
    """Đợt sụt vốn SÂU NHẤT trên đường lãi/lỗ cộng dồn đã thực hiện.

    Đo đúng cách chuẩn: chạy dọc chuỗi cộng dồn, giữ đỉnh chạy
    (`running peak`), độ sụt tại mỗi điểm là `đỉnh - cộng dồn`, đợt sâu
    nhất là điểm có độ sụt lớn nhất. Mốc bắt đầu là lệnh đã LẬP RA cái đỉnh
    đó (không phải lệnh đầu chuỗi), nên `trade_count` đếm đúng số lệnh từ
    đỉnh xuống đáy.

    `recovered`: có lệnh nào SAU đáy đưa cộng dồn trở lại bằng/vượt đỉnh cũ
    không. Chưa hồi thì `recovered_at_ms=None` và đợt sụt vẫn đang mở tính
    tới lệnh cuối cùng quan sát được -- một sự thật quan trọng mà con số
    "sụt vốn tối đa" đơn lẻ không nói ra.

    Trả `None` khi bot chưa từng sụt (đường cộng dồn không lùi lần nào).
    """
    if not trades:
        return None
    peak = 0.0
    peak_ms: Optional[float] = None
    peak_index = -1
    cumulative = 0.0
    best_depth = 0.0
    best: Optional[Dict[str, Any]] = None
    for index, row in enumerate(trades):
        cumulative += row["realized_pnl"]
        if cumulative >= peak:
            peak = cumulative
            peak_ms = row["close_time"]
            peak_index = index
            continue
        depth = peak - cumulative
        if depth > best_depth:
            best_depth = depth
            best = {
                "depth_abs": depth,
                "peak_cum": peak,
                "trough_cum": cumulative,
                # Đỉnh nằm ở lệnh `peak_index`; số lệnh của đợt là quãng từ
                # đó tới đáy. `peak_index == -1` nghĩa là đỉnh là mốc 0 ban
                # đầu (bot lỗ ngay từ lệnh đầu tiên, chưa từng có đỉnh
                # dương nào) -- khi đó đợt tính từ chính lệnh đầu tiên.
                "trade_count": index - peak_index,
                "peak_at_ms": peak_ms,
                "trough_at_ms": row["close_time"],
            }
    if best is None:
        return None

    recovered_at_ms: Optional[float] = None
    running = 0.0
    for row in trades:
        running += row["realized_pnl"]
        if row["close_time"] > best["trough_at_ms"] and running >= best["peak_cum"]:
            recovered_at_ms = row["close_time"]
            break

    end_ms = (
        recovered_at_ms if recovered_at_ms is not None else trades[-1]["close_time"]
    )
    start_ms = (
        best["peak_at_ms"]
        if best["peak_at_ms"] is not None
        else trades[0]["close_time"]
    )
    best["recovered"] = recovered_at_ms is not None
    best["recovered_at_ms"] = recovered_at_ms
    best["duration_hours"] = max(end_ms - start_ms, 0.0) / _MS_PER_HOUR
    best["depth_pct"] = _pct_of(best["depth_abs"], capital)
    return best


def _reference_capital(
    evidence: Mapping[str, Any],
) -> tuple[Optional[float], Optional[str]]:
    """Mốc vốn tham chiếu, đọc được ở CẢ HAI hình dạng `evidence`.

    Hai đường dựng trang để vốn ở hai chỗ khác nhau -- đo trên dữ liệu thật,
    không phải phòng xa:

      * Đường CHẤM SỐNG (`WebDataService._full_result`): `current_state` là
        bản dump của `BotCurrentState`, vốn nằm ở `reference_capital` kèm
        `reference_capital_source`.
      * Đường ĐỌC TỪ ĐĨA (`assessment_to_analyze_result`, phục vụ mọi bot
        đã chấm sẵn -- tức PHẦN LỚN lượt xem): KHÔNG có `current_state` nào
        cả; vốn nằm ở `performance.capital_at_risk` kèm
        `performance.capital_basis` (ví dụ thật: 109.752 USDT,
        `WEEKLY_EQUITY_CURVE`).

    Chỉ đọc `current_state` thôi thì mọi trang đọc từ đĩa sẽ mất sạch phần
    trăm và hiện cảnh báo "không suy ra được vốn" dù vốn có sẵn ngay trong
    tài liệu -- đúng kiểu báo thiếu dữ liệu sai sự thật mà module này phải
    tránh. Ưu tiên `current_state` vì đó là bản mới nhất khi cả hai cùng có.
    """
    current_state = evidence.get("current_state")
    if isinstance(current_state, Mapping):
        capital = _finite(current_state.get("reference_capital"))
        if capital is not None and capital > 0.0:
            source = current_state.get("reference_capital_source")
            return capital, source if isinstance(source, str) else None

    performance = evidence.get("performance")
    if isinstance(performance, Mapping):
        capital = _finite(performance.get("capital_at_risk"))
        if capital is not None and capital > 0.0:
            source = performance.get("capital_basis")
            return capital, source if isinstance(source, str) else None

    return None, None


def compute_loss_profile(evidence: Any) -> Optional[Dict[str, Any]]:
    """Hồ sơ thua lỗ đầy đủ, hoặc `None` khi không có gì để nói.

    `None` (mục bị ẩn hoàn toàn ở trang báo cáo) chỉ khi không đọc được lệnh
    đã chốt nào -- kết quả LIMITED/NOT_FOUND, hoặc bot chưa chốt lệnh nào.
    Có lệnh nhưng THIẾU vốn tham chiếu thì vẫn trả hồ sơ: các con số tiền
    tuyệt đối vẫn đúng và vẫn đáng đọc, chỉ riêng phần trăm là `None` kèm
    `capital=None` để trang báo cáo nói thẳng "không quy ra % được".
    """
    if not isinstance(evidence, Mapping):
        return None
    trades = _ordered_trades(evidence.get("closed_trade_series"))
    if not trades:
        return None

    capital, capital_source = _reference_capital(evidence)

    losing = [row for row in trades if row["realized_pnl"] < 0.0]
    gross_loss = sum(row["realized_pnl"] for row in losing)
    worst = _worst_trades(trades, capital)

    return {
        "capital": capital,
        "capital_source": capital_source,
        "trade_count": len(trades),
        "losing_trade_count": len(losing),
        "worst_trade": worst[0] if worst else None,
        "worst_trades": worst,
        "worst_losing_streak": _worst_losing_streak(trades, capital),
        "deepest_episode": _deepest_episode(trades, capital),
        "gross_loss": {
            "total": gross_loss,
            "pct_of_capital": _pct_of(gross_loss, capital),
        },
    }
