"""Ngưỡng cỡ mẫu tối thiểu của Monte Carlo, và cách đánh dấu mẫu mỏng.

BỐI CẢNH: `MonteCarloSimulationEngine.MIN_SAMPLE_SIZE` từng là 20 -- con số
tròn duy nhất trong class đó không kèm một dòng giải thích nào, trong khi
cùng dự án đã định nghĩa "đủ mẫu" ở mức 10 (`PHASE_CONFIDENCE_ENOUGH_TRADES`
trong `Agent/backend/web/report_page.py`). Hệ quả thấy được: một bot giấu sổ
lệnh (OKX 60004) chỉ còn ~12 điểm vốn tuần bị từ chối mô phỏng hoàn toàn,
dù 12 > 10.

Quyết định (18/09): hạ xuống 10 và KÈM ĐIỀU KIỆN -- mọi kết quả chạy trên
cỡ mẫu dưới `THIN_SAMPLE_SIZE` phải tự mang cờ `sample_is_thin` cùng một câu
cảnh báo nêu đúng lý do thống kê, để tầng trình bày không thể lỡ quên. Bộ
test này khoá cả hai nửa của quyết định đó: chạy được ở mẫu nhỏ, và không
bao giờ im lặng khi mẫu nhỏ.
"""

from __future__ import annotations

from typing import List

from Agent.backend.bot.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine as Engine,
)
from Agent.backend.bot.mcp.schemas.bot_result import PositionSide, TradeLedgerItem

# Lãi/lỗ cố định, xen kẽ thắng/thua: không dùng random để một lần chạy hỏng
# không bao giờ phụ thuộc vào hạt giống ngẫu nhiên của máy chạy test.
_PNL_CYCLE = (120.0, -80.0, 95.0, -60.0, 140.0, -110.0, 70.0, -45.0)


def _trades(n: int) -> List[TradeLedgerItem]:
    return [
        TradeLedgerItem(
            trade_id=f"t{i}",
            symbol="ETH-USDT-SWAP",
            side=PositionSide.LONG,
            open_time=1_700_000_000_000 + i * 3_600_000,
            close_time=1_700_000_000_000 + (i + 1) * 3_600_000,
            realized_pnl=_PNL_CYCLE[i % len(_PNL_CYCLE)],
            holding_time_minutes=60.0,
        )
        for i in range(n)
    ]


def _run(n: int):
    return Engine.run_simulation(
        _trades(n), initial_equity=10_000.0, iterations=2_000, seed=42
    )


# --------------------------------------------------------------------------- #
# Ngưỡng mới
# --------------------------------------------------------------------------- #


def test_threshold_matches_the_projects_own_enough_sample_convention() -> None:
    """10, không phải 20 -- cùng ngưỡng "đủ mẫu" mà phần phân tích pha dùng."""
    from Agent.backend.web.report_page import PHASE_CONFIDENCE_ENOUGH_TRADES

    assert Engine.MIN_SAMPLE_SIZE == PHASE_CONFIDENCE_ENOUGH_TRADES == 10
    assert Engine.THIN_SAMPLE_SIZE > Engine.MIN_SAMPLE_SIZE


def test_just_below_the_threshold_still_refuses_and_says_why() -> None:
    result = _run(Engine.MIN_SAMPLE_SIZE - 1)
    assert result.is_valid is False
    assert result.sample_is_thin is False  # không chạy thì không có gì để gắn cờ
    assert any(str(Engine.MIN_SAMPLE_SIZE) in w for w in result.warnings)


def test_exactly_at_the_threshold_runs() -> None:
    result = _run(Engine.MIN_SAMPLE_SIZE)
    assert result.is_valid is True
    assert result.sample_size == Engine.MIN_SAMPLE_SIZE
    assert result.profit_pct_p50 is not None


def test_twelve_weekly_points_of_a_ledger_hidden_bot_now_run() -> None:
    """Đúng ca thực tế đã thúc đẩy thay đổi này (bot ED2DE1A47EEF62EC)."""
    result = _run(12)
    assert result.is_valid is True
    assert result.sample_is_thin is True


# --------------------------------------------------------------------------- #
# Mẫu mỏng không bao giờ được đi kèm sự im lặng
# --------------------------------------------------------------------------- #


def test_thin_sample_is_flagged_and_warned_across_the_whole_band() -> None:
    for n in range(Engine.MIN_SAMPLE_SIZE, Engine.THIN_SAMPLE_SIZE):
        result = _run(n)
        assert result.is_valid is True, n
        assert result.sample_is_thin is True, n
        assert result.warnings, n


def test_warning_names_the_real_statistical_reason_not_a_vague_caution() -> None:
    """Câu cảnh báo phải nói ĐƯỢC vì sao, nếu không người đọc sẽ bỏ qua."""
    result = _run(12)
    joined = " ".join(result.warnings)
    assert "12" in joined  # cỡ mẫu thật
    assert "1/n" in joined  # độ phân giải phân vị
    assert "standard error" in joined


def test_a_healthy_sample_carries_no_thin_flag_and_no_extra_warning() -> None:
    result = _run(Engine.THIN_SAMPLE_SIZE)
    assert result.is_valid is True
    assert result.sample_is_thin is False
    assert not any("Mẫu mỏng" in w for w in result.warnings)


def test_the_numbers_themselves_are_still_real_at_a_thin_sample() -> None:
    """Gắn cờ mỏng KHÔNG được biến kết quả thành rỗng: vẫn phải là một mô
    phỏng thật, chỉ là kèm cảnh báo -- đúng yêu cầu "ít thì đánh giá kiểu
    ít", không phải "ít thì bỏ".
    """
    thin = _run(12)
    assert thin.iterations > 0
    assert thin.profit_pct_p05 is not None
    assert thin.profit_pct_p95 is not None
    assert thin.profit_pct_p05 <= thin.profit_pct_p50 <= thin.profit_pct_p95


# --------------------------------------------------------------------------- #
# Tiền điều kiện của bootstrap: các quan sát phải đổi chỗ được cho nhau
# --------------------------------------------------------------------------- #


def test_absolute_weekly_series_is_never_the_simulation_input() -> None:
    """Chuỗi PnL TUYỆT ĐỐI với quy mô vốn trôi không được phép làm đầu vào.

    Ca thật (bot ED2DE1A47EEF62EC, 18/09): vốn ngầm (pnl/pnlRatio) chạy từ
    1.020 tới 81.775 USDT -- chênh 80 lần. Nạp thẳng chuỗi tuyệt đối đó vào
    bootstrap rồi chia cho MỘT mốc vốn cho ra trung vị +9.839% trong khi
    lợi nhuận tích luỹ thật là +940%.

    Bất biến cần giữ KHÔNG phải "từ chối cả lượt mô phỏng" -- ma trận dữ
    liệu có thể (và nên) chuyển sang một chuỗi lợi suất hợp lệ khác. Bất
    biến là: chuỗi tuyệt đối lệch quy mô phải bị ĐÁNH DẤU KHÔNG DÙNG ĐƯỢC
    và không bao giờ được chọn làm chuỗi chính.
    """
    from Agent.backend.bot.analysis.limited_matrix import build_matrix

    weekly = [
        {"beginTs": str(1_785_081_600_000 + i * 604_800_000), "pnl": pnl, "pnlRatio": r}
        for i, (pnl, r) in enumerate(
            [
                ("763.45", "0.4366"),
                ("407.87", "0.3999"),
                ("15614.28", "4.1753"),
                ("28246.91", "1.7289"),
                ("-6434.82", "-0.2441"),
                ("-2612.89", "-0.5588"),
                ("20512.03", "7.7603"),
                ("47095.92", "1.7766"),
                ("12658.71", "0.1548"),
                ("56553.60", "0.7145"),
                ("3000.00", "0.0400"),
                ("4000.00", "0.0500"),
            ]
        )
    ]
    matrix = build_matrix(weekly=weekly)
    absolute = next(s for s in matrix.series if s.name == "weekly_absolute")

    assert absolute.usable is False
    assert "varies" in absolute.reason and "x across weeks" in absolute.reason
    assert matrix.primary is None or matrix.primary.name != "weekly_absolute"


def test_matrix_prefers_the_fixed_denominator_series_when_both_exist() -> None:
    """Có cả hai chuỗi hợp lệ thì chọn chuỗi NHIỀU QUAN SÁT hơn, không phải
    chuỗi được viết trước trong code."""
    from Agent.backend.bot.analysis.limited_matrix import build_matrix

    profile = {
        "pnl": "1000",
        "pnlRatio": "0.5",
        "pnlRatios": [
            {
                "beginTs": str(1_785_081_600_000 + i * 432_000_000),
                "pnlRatio": f"{i * 0.02:.4f}",
            }
            for i in range(19)
        ],
    }
    weekly = [
        {
            "beginTs": str(1_785_081_600_000 + i * 604_800_000),
            "pnl": f"{100.0:.2f}",
            "pnlRatio": "0.0100",
        }
        for i in range(12)
    ]
    matrix = build_matrix(profile=profile, stats={"investAmt": "2000"}, weekly=weekly)

    assert matrix.primary is not None
    assert matrix.primary.name == "ratio_delta"
    assert matrix.primary.count == 18  # 19 mốc -> 18 hiệu


def test_capital_identity_is_verified_not_assumed() -> None:
    """`pnlRatio x investAmt = pnl` được KIỂM mỗi lần; lệch quá biên thì bỏ
    mốc vốn thay vì cứ thế quy ra tiền sai."""
    from Agent.backend.bot.analysis.limited_matrix import build_matrix

    ratios = [
        {
            "beginTs": str(1_785_081_600_000 + i * 432_000_000),
            "pnlRatio": f"{i * 0.1:.4f}",
        }
        for i in range(12)
    ]
    ok = build_matrix(
        profile={"pnl": "1000", "pnlRatio": "0.5", "pnlRatios": ratios},
        stats={"investAmt": "2000"},
    )
    assert ok.reference_capital == 2000.0
    assert any(c.get("passed") is True for c in ok.cross_checks)

    bad = build_matrix(
        profile={"pnl": "1000", "pnlRatio": "0.5", "pnlRatios": ratios},
        stats={"investAmt": "999999"},
    )
    assert bad.reference_capital is None
    assert any(c.get("passed") is False for c in bad.cross_checks)
    # Vẫn mô phỏng được trong không gian tỉ lệ -- mất khả năng quy ra tiền,
    # không mất cả phép đo.
    assert bad.primary is not None


def test_a_stable_capital_base_still_simulates() -> None:
    """Chốt chặn chỉ được chặn ca thật sự lệch quy mô, không chặn tràn lan."""
    from Agent.backend.bot.analysis.limited import _run_monte_carlo_probe
    from Agent.backend.bot.mcp.capital.equity_curve import EquityCurveBuilder

    # Vốn ngầm quanh 10.000 suốt 12 tuần (pnl/ratio ~ 10.000).
    weekly = [
        {
            "beginTs": str(1_785_081_600_000 + i * 604_800_000),
            "pnl": f"{pnl:.2f}",
            "pnlRatio": f"{pnl / 10_000.0:.4f}",
        }
        for i, pnl in enumerate(
            [800, -300, 650, 1200, -450, 900, 300, -200, 1100, 700, -150, 500]
        )
    ]
    curve = EquityCurveBuilder.build(weekly)
    result = _run_monte_carlo_probe(weekly, curve, iterations=500, seed=42)

    assert result.is_valid is True
    assert result.sample_is_thin is True  # 12 < 20 -> vẫn phải gắn cờ mỏng
