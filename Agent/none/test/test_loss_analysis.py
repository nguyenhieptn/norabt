"""Kiểm thử `Agent/backend/web/loss_analysis.py`.

Trọng tâm: mọi con số phải suy ra ĐÚNG từ sổ lệnh, và mọi nhánh thiếu dữ
liệu phải trả `None` thay vì một giá trị bịa (xem docstring của module đó).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from Agent.backend.web.loss_analysis import WORST_TRADE_SAMPLE, compute_loss_profile

HOUR_MS = 3_600_000


def _trade(index: int, pnl: float) -> Dict[str, Any]:
    """Một lệnh đã chốt, cách nhau đúng 1 giờ để thời lượng dễ kiểm."""
    return {"close_time": index * HOUR_MS, "realized_pnl": pnl}


def _evidence(
    pnls: List[float],
    *,
    capital: Optional[float] = 1000.0,
    source: Optional[str] = "WEEKLY_EQUITY_CURVE",
) -> Dict[str, Any]:
    state: Dict[str, Any] = {}
    if capital is not None:
        state["reference_capital"] = capital
    if source is not None:
        state["reference_capital_source"] = source
    return {
        "closed_trade_series": [_trade(i + 1, pnl) for i, pnl in enumerate(pnls)],
        "current_state": state,
    }


# --------------------------------------------------------------------------- #
# Không có gì để nói -> mục bị ẩn hẳn
# --------------------------------------------------------------------------- #


def test_returns_none_without_any_closed_trade() -> None:
    assert compute_loss_profile({"closed_trade_series": []}) is None
    assert compute_loss_profile({}) is None
    assert compute_loss_profile(None) is None


def test_trades_missing_either_field_are_dropped_not_zeroed() -> None:
    """Một lệnh không đọc được lãi/lỗ KHÔNG phải lệnh hoà vốn."""
    evidence = {
        "closed_trade_series": [
            {"close_time": HOUR_MS, "realized_pnl": -100.0},
            {"close_time": 2 * HOUR_MS},  # thiếu pnl
            {"realized_pnl": -50.0},  # thiếu thời gian
            {"close_time": 3 * HOUR_MS, "realized_pnl": None},
            "không phải dict",
        ],
        "current_state": {"reference_capital": 1000.0},
    }
    profile = compute_loss_profile(evidence)
    assert profile is not None
    assert profile["trade_count"] == 1
    assert profile["gross_loss"]["total"] == -100.0


def test_boolean_is_not_treated_as_a_number() -> None:
    """`True` là `int` trong Python -- không được thành lãi 1 USDT."""
    evidence = {
        "closed_trade_series": [{"close_time": HOUR_MS, "realized_pnl": True}],
        "current_state": {},
    }
    assert compute_loss_profile(evidence) is None


# --------------------------------------------------------------------------- #
# Lệnh lỗ nặng nhất
# --------------------------------------------------------------------------- #


def test_worst_trade_is_the_largest_loss_with_pct_of_capital() -> None:
    profile = compute_loss_profile(_evidence([50.0, -200.0, -30.0, 10.0]))
    assert profile is not None
    worst = profile["worst_trade"]
    assert worst["pnl"] == -200.0
    assert worst["pct_of_capital"] == 20.0  # 200 / 1000
    assert worst["close_time"] == 2 * HOUR_MS


def test_worst_trades_sorted_and_capped_to_the_sample_size() -> None:
    pnls = [-float(n) for n in range(1, WORST_TRADE_SAMPLE + 4)]
    profile = compute_loss_profile(_evidence(pnls))
    assert profile is not None
    listed = profile["worst_trades"]
    assert len(listed) == WORST_TRADE_SAMPLE
    assert [row["pnl"] for row in listed] == sorted(row["pnl"] for row in listed)
    assert listed[0]["pnl"] == min(pnls)


def test_a_bot_that_never_lost_reports_no_worst_trade() -> None:
    profile = compute_loss_profile(_evidence([10.0, 20.0, 0.0]))
    assert profile is not None
    assert profile["worst_trade"] is None
    assert profile["worst_trades"] == []
    assert profile["losing_trade_count"] == 0
    assert profile["gross_loss"]["total"] == 0.0


# --------------------------------------------------------------------------- #
# Chuỗi thua liên tiếp -- chọn theo TIỀN, không theo độ dài
# --------------------------------------------------------------------------- #


def test_worst_streak_picks_the_costliest_not_the_longest() -> None:
    # Chuỗi A: 4 lệnh mất tổng 40. Chuỗi B: 2 lệnh mất tổng 300.
    profile = compute_loss_profile(
        _evidence([-10.0, -10.0, -10.0, -10.0, 5.0, -150.0, -150.0])
    )
    assert profile is not None
    streak = profile["worst_losing_streak"]
    assert streak["count"] == 2
    assert streak["total_loss"] == -300.0
    assert streak["pct_of_capital"] == 30.0


def test_breakeven_trade_does_not_split_a_losing_streak() -> None:
    profile = compute_loss_profile(_evidence([-100.0, 0.0, -100.0]))
    assert profile is not None
    streak = profile["worst_losing_streak"]
    assert streak["count"] == 2
    assert streak["total_loss"] == -200.0


def test_winning_trade_does_split_a_losing_streak() -> None:
    profile = compute_loss_profile(_evidence([-100.0, 1.0, -100.0]))
    assert profile is not None
    assert profile["worst_losing_streak"]["count"] == 1


def test_no_losing_streak_when_there_is_no_loss() -> None:
    profile = compute_loss_profile(_evidence([5.0, 5.0]))
    assert profile is not None
    assert profile["worst_losing_streak"] is None


# --------------------------------------------------------------------------- #
# Đợt sụt vốn sâu nhất
# --------------------------------------------------------------------------- #


def test_deepest_episode_measures_peak_to_trough_and_recovery() -> None:
    # Cộng dồn: 100, 60, 20, 90, 130 -> đỉnh 100 (lệnh 1), đáy 20 (lệnh 3),
    # sâu 80, hồi lại ở lệnh 5 (130 >= 100).
    profile = compute_loss_profile(_evidence([100.0, -40.0, -40.0, 70.0, 40.0]))
    assert profile is not None
    ep = profile["deepest_episode"]
    assert ep["depth_abs"] == 80.0
    # Standard max drawdown since 2026-09-25: depth / peak equity, where
    # equity = capital + cumulative PnL -> 80 / (1000 + 100).
    assert abs(ep["depth_pct"] - 80.0 / 1100.0 * 100.0) < 1e-9
    assert ep["depth_pct_of_capital"] == 8.0  # 80 / 1000, the old share-of-capital figure
    assert ep["peak_cum"] == 100.0
    assert ep["trough_cum"] == 20.0
    assert ep["trade_count"] == 2  # từ đỉnh (lệnh 1) xuống đáy (lệnh 3)
    assert ep["recovered"] is True
    assert ep["recovered_at_ms"] == 5 * HOUR_MS
    assert ep["duration_hours"] == 4.0  # lệnh 1 -> lệnh 5


def test_episode_still_open_is_reported_as_not_recovered() -> None:
    profile = compute_loss_profile(_evidence([100.0, -60.0, 10.0]))
    assert profile is not None
    ep = profile["deepest_episode"]
    assert ep["recovered"] is False
    assert ep["recovered_at_ms"] is None
    # Kéo dài tới lệnh quan sát được cuối cùng, không dừng ở đáy.
    assert ep["duration_hours"] == 2.0


def test_episode_counted_from_the_zero_mark_when_bot_loses_immediately() -> None:
    """Chưa từng có đỉnh dương nào -- đợt sụt tính từ chính lệnh đầu tiên."""
    profile = compute_loss_profile(_evidence([-30.0, -20.0]))
    assert profile is not None
    ep = profile["deepest_episode"]
    assert ep["peak_cum"] == 0.0
    assert ep["depth_abs"] == 50.0
    assert ep["trade_count"] == 2
    assert ep["recovered"] is False


def test_no_episode_when_the_curve_never_goes_down() -> None:
    profile = compute_loss_profile(_evidence([10.0, 20.0, 30.0]))
    assert profile is not None
    assert profile["deepest_episode"] is None


def test_series_out_of_order_is_sorted_before_measuring() -> None:
    """Thứ tự xáo trộn không được tạo ra một đợt sụt chưa từng xảy ra."""
    ordered = compute_loss_profile(_evidence([100.0, -40.0, -40.0, 70.0, 40.0]))
    shuffled_series = list(
        _evidence([100.0, -40.0, -40.0, 70.0, 40.0])["closed_trade_series"]
    )
    shuffled_series.reverse()
    shuffled = compute_loss_profile(
        {
            "closed_trade_series": shuffled_series,
            "current_state": {"reference_capital": 1000.0},
        }
    )
    assert ordered is not None and shuffled is not None
    assert shuffled["deepest_episode"] == ordered["deepest_episode"]


# --------------------------------------------------------------------------- #
# Thiếu vốn tham chiếu -> % là None, KHÔNG phải 0
# --------------------------------------------------------------------------- #


def test_missing_capital_leaves_every_percentage_unmeasured() -> None:
    profile = compute_loss_profile(_evidence([100.0, -250.0, -50.0], capital=None))
    assert profile is not None
    assert profile["capital"] is None
    assert profile["worst_trade"]["pnl"] == -250.0
    assert profile["worst_trade"]["pct_of_capital"] is None
    assert profile["worst_losing_streak"]["pct_of_capital"] is None
    assert profile["deepest_episode"]["depth_pct"] is None
    assert profile["gross_loss"]["pct_of_capital"] is None


def test_non_positive_capital_is_treated_as_missing() -> None:
    for bad in (0.0, -5.0):
        profile = compute_loss_profile(_evidence([-100.0], capital=bad))
        assert profile is not None
        assert profile["capital"] is None
        assert profile["worst_trade"]["pct_of_capital"] is None


def test_capital_source_is_passed_through_for_the_methodology_block() -> None:
    profile = compute_loss_profile(_evidence([-100.0], source="LEDGER_DERIVED"))
    assert profile is not None
    assert profile["capital_source"] == "LEDGER_DERIVED"


# --------------------------------------------------------------------------- #
# Hai hình dạng `evidence` -- đường chấm sống và đường đọc từ đĩa
# --------------------------------------------------------------------------- #


def test_capital_read_from_performance_on_the_disk_path() -> None:
    """Trang đọc từ assessment.json KHÔNG có `current_state` -- vốn nằm ở
    `performance.capital_at_risk` (đo trên dữ liệu thật: 109.752 USDT).
    Bỏ sót nhánh này thì mọi bot đã chấm sẵn mất sạch phần trăm.
    """
    evidence = {
        "closed_trade_series": [_trade(1, -250.0)],
        "performance": {
            "capital_at_risk": 1000.0,
            "capital_basis": "WEEKLY_EQUITY_CURVE",
        },
    }
    profile = compute_loss_profile(evidence)
    assert profile is not None
    assert profile["capital"] == 1000.0
    assert profile["capital_source"] == "WEEKLY_EQUITY_CURVE"
    assert profile["worst_trade"]["pct_of_capital"] == 25.0


def test_current_state_wins_when_both_shapes_carry_capital() -> None:
    evidence = {
        "closed_trade_series": [_trade(1, -100.0)],
        "current_state": {
            "reference_capital": 1000.0,
            "reference_capital_source": "LEDGER",
        },
        "performance": {"capital_at_risk": 5000.0, "capital_basis": "OTHER"},
    }
    profile = compute_loss_profile(evidence)
    assert profile is not None
    assert profile["capital"] == 1000.0
    assert profile["capital_source"] == "LEDGER"


def test_falls_through_to_performance_when_current_state_capital_unusable() -> None:
    evidence = {
        "closed_trade_series": [_trade(1, -100.0)],
        "current_state": {"reference_capital": 0.0},
        "performance": {"capital_at_risk": 2000.0, "capital_basis": "WEEKLY"},
    }
    profile = compute_loss_profile(evidence)
    assert profile is not None
    assert profile["capital"] == 2000.0
    assert profile["worst_trade"]["pct_of_capital"] == 5.0
