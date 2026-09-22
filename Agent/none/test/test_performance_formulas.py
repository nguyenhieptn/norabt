"""Khoá Sortino và Calmar vào đúng định nghĩa chuẩn quốc tế.

Hai chỉ số này không chảy vào bất kỳ chiều chấm điểm nào -- chúng thuần hiển
thị -- nhưng đúng vì thế mà chúng dễ trôi: không test nào gãy khi chúng sai,
người đọc thì tưởng đang xem một con số chuẩn. Hai bài dưới đây tính lại vế
phải bằng tay từ định nghĩa gốc rồi so từng chữ số.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from Agent.backend.bot.mcp.analytics.performance.metrics import (
    PerformanceMetricsCalculator,
)
from Agent.backend.bot.mcp.capital.equity_curve import CapitalModel
from Agent.backend.bot.mcp.schemas.bot_result import (
    DrawdownAnalysis,
    PositionSide,
    TradeLedgerItem,
)

DAY_MS = 86_400_000
CAPITAL = 10_000.0


def _trades(pnls, *, days_apart: float = 1.0):
    start = 1_700_000_000_000
    step = int(DAY_MS * days_apart)
    return [
        TradeLedgerItem(
            trade_id=f"t{index}",
            symbol="BTC",
            side=PositionSide.LONG,
            open_time=start + index * step,
            close_time=start + index * step + 3_600_000,
            realized_pnl=float(pnl),
            holding_time_minutes=60.0,
        )
        for index, pnl in enumerate(pnls)
    ]


def _capital() -> CapitalModel:
    return CapitalModel(basis="TEST", capital_at_risk=CAPITAL)


def test_sortino_divides_by_all_observations_not_just_the_losing_ones() -> None:
    """DD = √( (1/N)·Σ min(rᵢ, 0)² ) -- N là TỔNG số quan sát.

    Bản cũ lấy trung bình bình phương chỉ trên các lệnh LỖ, tức chia cho
    N_lỗ. Điều đó thổi phồng DD lên hệ số √(N/N_lỗ) và hạ Sortino xuống đúng
    bằng hệ số đó: với bộ dữ liệu dưới đây (8 lệnh, 3 lệnh lỗ) là √(8/3) ≈
    1.63, tức chỉ số hiển thị chỉ còn ~61% giá trị đúng.
    """
    pnls = [120.0, -80.0, 200.0, 60.0, -150.0, 90.0, -40.0, 110.0]
    result = PerformanceMetricsCalculator.calculate(_trades(pnls), capital=_capital())

    returns = np.asarray(pnls, dtype=np.float64) / CAPITAL
    span_days = 7.0 + 3_600_000 / DAY_MS
    periods_per_year = min(max(len(pnls) / span_days * 365.25, 1.0), 365.25 * 24 * 60)
    downside_deviation = math.sqrt(float(np.mean(np.minimum(returns, 0.0) ** 2)))
    expected = (
        float(np.mean(returns)) / downside_deviation * math.sqrt(periods_per_year)
    )

    assert result.sortino_ratio == pytest.approx(expected, rel=1e-9)

    # Và khẳng định nó KHÁC hẳn công thức cũ, để bài test này không vô tình
    # đúng với cả hai.
    only_losses = np.asarray([r for r in returns if r < 0], dtype=np.float64)
    old_dd = math.sqrt(float(np.mean(only_losses**2)))
    old_value = float(np.mean(returns)) / old_dd * math.sqrt(periods_per_year)
    assert result.sortino_ratio > old_value * 1.5


def test_calmar_uses_an_annualised_return_not_a_cumulative_one() -> None:
    """Calmar = CAGR / sụt vốn tối đa, không phải ROI tích luỹ / sụt vốn.

    Cùng ROI tích luỹ và cùng sụt vốn, bot chạy ngắn phải được Calmar CAO hơn
    bot chạy dài -- vì nó tạo ra từng ấy lợi nhuận trong ít thời gian hơn.
    Bản cũ cho hai bot đó cùng một con số.
    """
    pnls = [100.0, -50.0, 180.0, -30.0, 140.0, 60.0]
    drawdown = DrawdownAnalysis(capital_basis="TEST", max_dd_pct=8.0)

    short = PerformanceMetricsCalculator.calculate(
        _trades(pnls, days_apart=12.0),
        capital=_capital(),
        reported_roi_pct=40.0,
        drawdown=drawdown,
    )
    long = PerformanceMetricsCalculator.calculate(
        _trades(pnls, days_apart=120.0),
        capital=_capital(),
        reported_roi_pct=40.0,
        drawdown=drawdown,
    )
    assert short.calmar_ratio is not None and long.calmar_ratio is not None
    assert short.calmar_ratio > long.calmar_ratio

    # Đối chiếu nguyên văn công thức trên trường hợp dài.
    span_days = 5 * 120.0 + 3_600_000 / DAY_MS
    annualised = ((1.0 + 40.0 / 100.0) ** (365.25 / span_days) - 1.0) * 100.0
    assert long.calmar_ratio == pytest.approx(annualised / 8.0, rel=1e-9)


def test_calmar_is_withheld_when_the_window_is_too_short_to_annualise() -> None:
    """Ngoại suy 5 ngày lên cả năm cho ra con số vô nghĩa -- thà không có."""
    result = PerformanceMetricsCalculator.calculate(
        _trades([50.0, -20.0, 80.0], days_apart=1.0),
        capital=_capital(),
        reported_roi_pct=20.0,
        drawdown=DrawdownAnalysis(capital_basis="TEST", max_dd_pct=5.0),
    )
    assert result.calmar_ratio is None
