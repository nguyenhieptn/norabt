"""Bước 2 cho bot giấu sổ lệnh: dựng MA TRẬN các luồng dữ liệu công khai,
đối chiếu chúng, chọn ra chuỗi lợi suất HỢP LỆ, rồi giao cho đúng bộ máy
tính toán/mô phỏng mà nhánh đầy đủ đang dùng.

VÌ SAO TỒN TẠI: `Agent/backend/analysis/limited.py` trước đây đi thẳng từ
"vài con số rời rạc" sang "điểm rủi ro" bằng những công thức tự chế ngay tại
chỗ (`score = 15`, `+50 nếu sụt > 30%`, `(1 - tỉ lệ ngày lãi) * 100`...).
Không con số nào trong đó suy ra từ lý thuyết hay được hiệu chỉnh trên dữ
liệu. Module này thay thế bước nhảy đó bằng đúng trình tự mà một hệ định
lượng phải đi: **gom nhiều luồng -> đối chiếu -> chọn chuỗi hợp lệ -> tính
toán -> mô phỏng**, và chỉ trả về THAM SỐ ĐO ĐƯỢC. Nó KHÔNG chấm điểm, không
xếp hạng, không đặt ngưỡng.

--------------------------------------------------------------------------
HAI PHÁT HIỆN LÀM NỀN CHO MODULE NÀY (đã kiểm bằng số trên bot thật
ED2DE1A47EEF62EC, không phải giả định)

1) `profile.pnlRatios` là chuỗi lợi suất TÍCH LUỸ trên MỘT mẫu số cố định.
   Hiệu giữa các mốc cộng lại bằng ĐÚNG giá trị tích luỹ cuối (9,3951 =
   tổng 18 hiệu, khớp tuyệt đối). Lợi suất trên cùng một mẫu số thì ĐỔI CHỖ
   ĐƯỢC CHO NHAU -- tiền đề bắt buộc của bootstrap.

2) Mẫu số đó là `stats.investAmt`, đã công bố:
   `pnlRatio x investAmt = 9,3951 x 18.494,55 = 173.758,19` so với
   `profile.pnl = 173.758,73` -- lệch 0,0003%. Nhờ vậy chuỗi tỉ lệ quy
   ngược ra tiền được một cách nhất quán, và ngược lại.

Đối lập hoàn toàn với chuỗi PnL TUYỆT ĐỐI theo tuần (`public-weekly-pnl`):
vốn ngầm của nó (`pnl / pnlRatio`) chạy từ 1.020 tới 81.775 USDT -- chênh 80
lần -- nên các tuần KHÔNG đổi chỗ được cho nhau và không được phép làm đầu
vào mô phỏng (xem `_MAX_IMPLIED_BASE_SPREAD` bên `limited.py`).

--------------------------------------------------------------------------
LINH ĐỘNG: mỗi bot công khai một tập luồng khác nhau, nên module này không
giả định luồng nào phải có. Thiếu `investAmt` thì vẫn mô phỏng được trong
KHÔNG GIAN TỈ LỆ (đặt mốc vốn = 1 đơn vị): mọi con số phần trăm vẫn đúng,
chỉ là không quy ra tiền. Thiếu hẳn chuỗi tỉ lệ thì rơi về chuỗi tuần nếu
chuỗi đó qua được phép thử đổi chỗ. Không luồng nào dùng được thì trả
`None` -- không nặn ra một chuỗi thay thế.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from Agent.backend.bot.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.bot.mcp.schemas.bot_result import PositionSide, TradeLedgerItem

__all__ = [
    "DataStream",
    "ReturnSeries",
    "LimitedMatrix",
    "build_matrix",
    "simulate_matrix",
]

# Sai lệch tương đối tối đa còn chấp nhận khi kiểm định danh tính
# `pnlRatio x investAmt = pnl`. Đo thật trên bot đầu tiên: 0,0003%. Đặt 1%
# là biên rộng cho sai số làm tròn của chính OKX (họ công bố `pnlRatio` 4
# chữ số thập phân, riêng việc làm tròn đó đã gây lệch cỡ 0,005% ở mức tỉ
# lệ ~9,4) mà vẫn bắt được trường hợp hai trường thật sự không cùng một
# mẫu số.
_IDENTITY_TOLERANCE = 0.01

# Số quan sát tối thiểu để một chuỗi được coi là chuỗi lợi suất. 2 là mức
# tuyệt đối về mặt định nghĩa (phải có ít nhất một hiệu); việc chuỗi đó có
# ĐỦ DÀI để mô phỏng hay không là quyết định của
# `MonteCarloSimulationEngine.MIN_SAMPLE_SIZE`, không lặp lại ở đây.
_MIN_SERIES_POINTS = 2

_MS_PER_DAY = 86_400_000.0


def _finite(value: Any) -> Optional[float]:
    """Số hữu hạn thật, hoặc `None`. `bool` bị loại (True là int trong
    Python và sẽ lặng lẽ thành 1.0)."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _timestamp(value: Any) -> Optional[int]:
    number = _finite(value)
    return int(number) if number is not None else None


@dataclass
class DataStream:
    """Một luồng dữ liệu công khai và những gì đo được VỀ CHÍNH NÓ.

    Đây là phần "ma trận" theo nghĩa đen: mỗi luồng là một hàng, với cùng
    một bộ thuộc tính, để bước sau so sánh và chọn lựa dựa trên số liệu chứ
    không dựa trên thứ tự ưu tiên viết cứng.
    """

    name: str
    endpoint: str
    points: int
    span_days: Optional[float]
    cadence_days: Optional[float]
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "endpoint": self.endpoint,
            "points": self.points,
            "span_days": self.span_days,
            "cadence_days": self.cadence_days,
            "note": self.note,
        }


@dataclass
class ReturnSeries:
    """Một chuỗi lợi suất ỨNG VIÊN, kèm phán quyết có dùng được hay không.

    `usable=False` không bao giờ đi kèm một chuỗi đã bị "sửa cho dùng
    được" -- nó giữ nguyên giá trị gốc và ghi lý do, để nơi gọi (và người
    đọc báo cáo) thấy được vì sao nó bị loại.
    """

    name: str
    basis: str
    timestamps: List[int]
    values: List[float]
    usable: bool
    reason: str

    @property
    def count(self) -> int:
        return len(self.values)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "basis": self.basis,
            "count": self.count,
            "usable": self.usable,
            "reason": self.reason,
        }


@dataclass
class LimitedMatrix:
    """Kết quả bước 2: các luồng, các chuỗi ứng viên, chuỗi được chọn, và
    những phép đối chiếu chéo giữa các nguồn."""

    streams: List[DataStream] = field(default_factory=list)
    series: List[ReturnSeries] = field(default_factory=list)
    primary: Optional[ReturnSeries] = None
    reference_capital: Optional[float] = None
    capital_source: Optional[str] = None
    cross_checks: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "streams": [s.to_dict() for s in self.streams],
            "series": [s.to_dict() for s in self.series],
            "primary": self.primary.name if self.primary else None,
            "reference_capital": self.reference_capital,
            "capital_source": self.capital_source,
            "cross_checks": self.cross_checks,
        }


def _span_and_cadence(
    timestamps: Sequence[int],
) -> tuple[Optional[float], Optional[float]]:
    if len(timestamps) < 2:
        return None, None
    span = (max(timestamps) - min(timestamps)) / _MS_PER_DAY
    return span, span / (len(timestamps) - 1)


def _cumulative_ratio_points(profile: Any) -> List[Dict[str, float]]:
    raw = (profile or {}).get("pnlRatios") if isinstance(profile, Mapping) else None
    points: List[Dict[str, float]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            ts = _timestamp(item.get("beginTs"))
            ratio = _finite(item.get("pnlRatio"))
            if ts is None or ratio is None:
                continue
            points.append({"ts": float(ts), "ratio": ratio})
    points.sort(key=lambda row: row["ts"])
    return points


def _weekly_points(weekly: Any) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    if isinstance(weekly, list):
        for item in weekly:
            if not isinstance(item, Mapping):
                continue
            ts = _timestamp(item.get("beginTs", item.get("week_start")))
            pnl = _finite(item.get("pnl", item.get("pnl_usdt")))
            ratio = _finite(item.get("pnlRatio", item.get("pnl_ratio")))
            if ts is None:
                continue
            rows.append({"ts": float(ts), "pnl": pnl, "ratio": ratio})
    rows.sort(key=lambda row: row["ts"])
    return rows


def _verify_capital_identity(
    profile: Any, invest_amt: Optional[float]
) -> Optional[Dict[str, Any]]:
    """Kiểm định `pnlRatio x investAmt = pnl` trên chính bot này.

    KHÔNG giả định danh tính đó đúng: nó được kiểm lại mỗi lần, và kết quả
    (kể cả khi lệch) được ghi vào `cross_checks` để người đọc thấy mẫu số
    đang dùng có thật sự là mẫu số OKX dùng hay không.
    """
    if not isinstance(profile, Mapping) or invest_amt is None or invest_amt <= 0:
        return None
    pnl = _finite(profile.get("pnl"))
    ratio = _finite(profile.get("pnlRatio"))
    if pnl is None or ratio is None or pnl == 0:
        return None
    implied = ratio * invest_amt
    residual = abs(implied - pnl) / abs(pnl)
    return {
        "check": "pnlRatio × investAmt = pnl",
        "expected": pnl,
        "implied": implied,
        "relative_error": residual,
        "passed": residual <= _IDENTITY_TOLERANCE,
    }


def build_matrix(
    profile: Any = None,
    stats: Any = None,
    weekly: Any = None,
) -> LimitedMatrix:
    """Gom mọi luồng công khai thành một ma trận và chọn chuỗi lợi suất.

    Thứ tự ưu tiên KHÔNG viết cứng theo tên luồng mà theo hai tiêu chí đo
    được, xét lần lượt: (1) chuỗi có đổi chỗ được không, (2) trong các chuỗi
    đổi chỗ được thì chuỗi nào NHIỀU QUAN SÁT hơn. Một bot khác công khai
    tập luồng khác sẽ tự ra lựa chọn khác mà không cần sửa code.
    """
    matrix = LimitedMatrix()

    invest_amt = (
        _finite((stats or {}).get("investAmt")) if isinstance(stats, Mapping) else None
    )
    if invest_amt is not None and invest_amt > 0:
        matrix.reference_capital = invest_amt
        matrix.capital_source = "public-stats.investAmt"
    identity = _verify_capital_identity(profile, invest_amt)
    if identity is not None:
        matrix.cross_checks.append(identity)
        if not identity["passed"]:
            # Mẫu số không khớp -> không dùng nó để quy ra tiền. Chuỗi tỉ lệ
            # vẫn dùng được (phần trăm không cần mẫu số), chỉ mất khả năng
            # đổi sang USDT.
            matrix.reference_capital = None
            matrix.capital_source = None

    # --- Luồng 1: chuỗi lợi suất tích luỹ (public-lead-traders) -----------
    cumulative = _cumulative_ratio_points(profile)
    if cumulative:
        span, cadence = _span_and_cadence([int(p["ts"]) for p in cumulative])
        matrix.streams.append(
            DataStream(
                name="cumulative_pnl_ratio",
                endpoint="public-lead-traders.pnlRatios",
                points=len(cumulative),
                span_days=span,
                cadence_days=cadence,
                note="Cumulative return on invested capital (fixed denominator)",
            )
        )
    if len(cumulative) >= _MIN_SERIES_POINTS:
        deltas = [
            cumulative[i]["ratio"] - cumulative[i - 1]["ratio"]
            for i in range(1, len(cumulative))
        ]
        matrix.series.append(
            ReturnSeries(
                name="ratio_delta",
                basis="FIXED_INVESTED_CAPITAL",
                timestamps=[int(p["ts"]) for p in cumulative[1:]],
                values=deltas,
                usable=True,
                reason=(
                    "Delta of the cumulative return: every period shares the "
                    "same denominator (invested capital), and the deltas sum to "
                    "exactly the final cumulative value, so the periods are "
                    "interchangeable"
                ),
            )
        )

    # --- Luồng 2: PnL tuần (public-weekly-pnl) ----------------------------
    weekly_rows = _weekly_points(weekly)
    if weekly_rows:
        span, cadence = _span_and_cadence([int(r["ts"]) for r in weekly_rows])
        matrix.streams.append(
            DataStream(
                name="weekly_pnl",
                endpoint="public-weekly-pnl",
                points=len(weekly_rows),
                span_days=span,
                cadence_days=cadence,
                note="Absolute PnL + weekly ratio (denominator changes week to week)",
            )
        )
    weekly_ratios = [
        r for r in weekly_rows if r.get("ratio") is not None and r["ts"] is not None
    ]
    if len(weekly_ratios) >= _MIN_SERIES_POINTS:
        matrix.series.append(
            ReturnSeries(
                name="weekly_ratio",
                basis="EQUITY_IN_FORCE_EACH_WEEK",
                timestamps=[int(r["ts"]) for r in weekly_ratios],
                values=[float(r["ratio"]) for r in weekly_ratios],
                usable=True,
                reason=(
                    "The weekly ratio is the return on capital in that same "
                    "week (time-weighted), independent of the size of capital"
                ),
            )
        )
    weekly_abs = [r for r in weekly_rows if r.get("pnl") is not None]
    if len(weekly_abs) >= _MIN_SERIES_POINTS:
        bases = [
            abs(r["pnl"] / r["ratio"])
            for r in weekly_abs
            if r.get("ratio") not in (None, 0.0) and abs(r["ratio"]) > 1e-9
        ]
        spread = (
            (max(bases) / min(bases)) if len(bases) >= 2 and min(bases) > 0 else None
        )
        usable = spread is None or spread <= 3.0
        matrix.series.append(
            ReturnSeries(
                name="weekly_absolute",
                basis="ABSOLUTE_PNL",
                timestamps=[int(r["ts"]) for r in weekly_abs],
                values=[float(r["pnl"]) for r in weekly_abs],
                usable=usable,
                reason=(
                    "Absolute PnL on a stable capital base"
                    if usable
                    else (
                        f"Capital size varies {spread:,.0f}x across weeks -- the "
                        "periods are not interchangeable, not used as simulation "
                        "input"
                    )
                ),
            )
        )

    # --- Đối chiếu chéo hai chuỗi lợi suất --------------------------------
    by_name = {s.name: s for s in matrix.series}
    if "ratio_delta" in by_name and "weekly_ratio" in by_name:
        left = sum(by_name["ratio_delta"].values)
        right = sum(by_name["weekly_ratio"].values)
        matrix.cross_checks.append(
            {
                "check": "total return: ratio_delta vs weekly_ratio",
                "expected": left,
                "implied": right,
                "relative_error": (abs(right - left) / abs(left)) if left else None,
                # CỐ Ý không có `passed`: hai chuỗi đo hai thứ KHÁC NHAU (một
                # trên mẫu số cố định, một time-weighted) nên lệch nhau là
                # bình thường, không phải lỗi. Ghi ra để người đọc thấy mức
                # lệch, không để phán đúng/sai.
                "note": (
                    "The two series use different denominators so they are NOT "
                    "expected to match; this figure only shows the gap between "
                    "the two sources"
                ),
            }
        )

    # --- Chọn chuỗi chính: đổi chỗ được, rồi nhiều quan sát nhất ----------
    candidates = [s for s in matrix.series if s.usable]
    if candidates:
        matrix.primary = max(candidates, key=lambda s: s.count)
    return matrix


def simulate_matrix(
    matrix: LimitedMatrix,
    iterations: int = 2_000,
    seed: Optional[int] = 42,
) -> Optional[Any]:
    """Giao chuỗi chính cho ĐÚNG `MonteCarloSimulationEngine` của sản phẩm.

    Không viết lại một phép mô phỏng riêng: cùng stationary bootstrap, cùng
    ngưỡng cỡ mẫu, cùng cờ mẫu mỏng, cùng cách tính VaR/CVaR/p_ruin mà nhánh
    đầy đủ dùng -- nhờ vậy con số của bot giấu sổ lệnh và bot công khai sinh
    ra từ một đường tính toán duy nhất.

    Mốc vốn: dùng `reference_capital` đã kiểm định khi có (để quy ra tiền);
    không có thì đặt 1 đơn vị và mọi phần trăm vẫn đúng -- đây là phần
    "linh động" với bot không công bố `investAmt`.
    """
    if matrix.primary is None or not matrix.primary.values:
        return None
    base = matrix.reference_capital or 1.0
    scale = base if matrix.primary.basis != "ABSOLUTE_PNL" else 1.0
    trades: List[TradeLedgerItem] = []
    for index, (ts, value) in enumerate(
        zip(matrix.primary.timestamps, matrix.primary.values, strict=False)
    ):
        trades.append(
            TradeLedgerItem(
                trade_id=f"PERIOD_{index}",
                symbol="AGGREGATED_PERIOD",
                side=PositionSide.NET,
                open_time=int(ts),
                close_time=int(ts),
                realized_pnl=value * scale,
                holding_time_minutes=0.0,
            )
        )
    return MonteCarloSimulationEngine.run_simulation(
        trades=trades,
        initial_equity=base,
        iterations=iterations,
        horizon_trades=max(len(trades), 1),
        seed=seed,
    )
