"""Vân tay luật thoát: mỗi case ở đây tương ứng một cách sai lặng lẽ.

Sai kiểu "ra số trông hợp lý nhưng sai" nguy hiểm hơn hẳn sai kiểu ném lỗi:
một mức chốt lời bịa ra từ những lần thoát rải rác, một lệnh short bị tính
ngược dấu thành lỗ, hai bot cùng luật nhưng khác đòn bẩy bị coi là khác nhau,
hay hai khung thời gian giữ lệnh liền kề bị coi là xa nhau như scalp với ôm
hàng.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

import pytest

from Agent.backend.bot.mcp.analytics.strategy.exit_rule import (
    ExitRuleAnalyzer,
    HOLD_BUCKET_LABELS,
)
from Agent.backend.bot.mcp.schemas.bot_result import (
    ExitStyle,
    PositionSide,
    TradeLedgerItem,
)

_BASE_MS = 1_700_000_000_000
# Cố ý PHÂN TÁN: một dãy giá trị cụm lại quanh trung vị sẽ bị (đúng) nhận là
# TP/SL cứng, và nhãn luật cứng sẽ chiếm chỗ của nhãn hành vi mà test đang
# muốn kiểm tra. Ba lần fixture cụm vô tình đã làm hỏng test theo cách đó.
_SCATTERED_SMALL_WINS = [0.4, 1.0, 1.8, 0.6, 2.4, 1.2]
_SCATTERED_SMALL_LOSSES = [0.5, 1.5, 2.5, 0.8, 3.5, 1.2]
_SCATTERED_BIG_LOSSES = [2.0, 6.0, 3.5, 9.0, 4.5, 7.5]
_SCATTERED_RUNNING_WINS = [1.0, 0.4, 1.8, 2.4, 9.0, 16.0, 0.7, 22.0]
_ENTRY = 100.0


def _trade(
    index: int,
    move_pct: float,
    hold_minutes: float,
    side: PositionSide = PositionSide.LONG,
    entry: float = _ENTRY,
    leverage: Optional[float] = None,
    notional: Optional[float] = None,
    priced: bool = True,
) -> TradeLedgerItem:
    """One closed trade whose PRICE move is exactly `move_pct`, direction-adjusted."""
    signed = move_pct if side == PositionSide.LONG else -move_pct
    exit_price = entry * (1.0 + signed / 100.0)
    open_time = _BASE_MS + index * 3_600_000
    return TradeLedgerItem(
        trade_id=f"t{index}",
        symbol="BTC",
        side=side,
        open_time=open_time,
        close_time=open_time + int(hold_minutes * 60_000),
        entry_price=entry if priced else None,
        exit_price=exit_price if priced else None,
        leverage=leverage,
        notional=notional,
        # Deliberately inconsistent with the price move: nothing in the
        # analyzer may read it, and a test that mirrored it would not prove so.
        realized_pnl=-999.0,
        holding_time_minutes=hold_minutes,
    )


def _mix(
    wins: Sequence[float],
    losses: Sequence[float],
    win_hold: float = 600.0,
    loss_hold: float = 600.0,
    **kwargs,
) -> List[TradeLedgerItem]:
    rows = [_trade(i, m, win_hold, **kwargs) for i, m in enumerate(wins)]
    rows += [
        _trade(len(wins) + i, -m, loss_hold, **kwargs) for i, m in enumerate(losses)
    ]
    return rows


# --------------------------------------------------------------------------- #
# Đọc đúng sổ lệnh
# --------------------------------------------------------------------------- #


def test_short_closing_below_entry_is_a_win_not_a_loss() -> None:
    """Quên đảo dấu cho lệnh short thì mọi con số đảo ngược hoàn toàn."""
    trades = [_trade(i, 3.0, 600.0, side=PositionSide.SHORT) for i in range(12)]
    result = ExitRuleAnalyzer.analyze(trades)
    assert result.win_count == 12
    assert result.loss_count == 0
    assert result.win_move_median == pytest.approx(3.0, abs=1e-6)


def test_identical_rule_at_different_leverage_and_size_is_identical() -> None:
    """Đây là lý do mọi phép đo dùng GIÁ chứ không dùng PnL.

    Cùng một luật thoát chạy ở 5x và 50x là cùng một cách chơi; nếu đo bằng
    PnL thì chúng thành hai chiến lược khác nhau và toàn bộ việc so sánh
    phong cách mất nghĩa.
    """
    wins, losses = [2.0, 3.0, 4.0, 2.5, 3.5, 5.0], [1.0, 1.5, 2.0, 1.2, 1.8, 1.1]
    small = ExitRuleAnalyzer.analyze(_mix(wins, losses, leverage=5.0, notional=100.0))
    large = ExitRuleAnalyzer.analyze(
        _mix(wins, losses, leverage=50.0, notional=100_000.0)
    )
    assert small.rule_vector == large.rule_vector
    assert small.exit_style is large.exit_style
    assert ExitRuleAnalyzer.compare(small, large)["distance"] == 0.0


def test_unpriced_trades_are_reported_not_silently_dropped() -> None:
    priced = _mix([2.0] * 6, [1.0] * 6)
    blind = [_trade(100 + i, 2.0, 600.0, priced=False) for i in range(8)]
    result = ExitRuleAnalyzer.analyze(priced + blind)
    assert result.sample_size == 20
    assert result.priced_trades == 12
    assert result.price_coverage == pytest.approx(0.6)
    assert any("missing an entry or exit price" in w for w in result.warnings)


def test_thin_ledger_is_not_characterised() -> None:
    result = ExitRuleAnalyzer.analyze(_mix([2.0] * 3, [1.0] * 3))
    assert result.is_valid is False
    assert result.exit_style is ExitStyle.UNKNOWN
    assert result.rule_vector == []
    assert any("needs 10" in w for w in result.warnings)


# --------------------------------------------------------------------------- #
# Phát hiện luật cứng
# --------------------------------------------------------------------------- #


def test_fixed_take_profit_is_detected_with_its_level() -> None:
    wins = [2.0, 2.02, 1.98, 2.05, 1.95, 2.01, 1.99, 2.03]
    losses = [0.4, 3.1, 1.2, 5.0, 0.9, 2.2]
    result = ExitRuleAnalyzer.analyze(_mix(wins, losses))
    assert result.has_hard_take_profit is True
    assert result.take_profit_clustering == 1.0
    assert result.take_profit_level_pct == pytest.approx(2.005, abs=0.01)
    assert result.exit_style is ExitStyle.FIXED_TARGET


def test_scattered_exits_invent_no_level() -> None:
    """Một mức chốt lời bịa ra còn tệ hơn không có mức nào."""
    wins = [0.5, 1.4, 3.0, 6.2, 9.1, 12.0, 0.9, 4.4]
    losses = [0.3, 1.1, 2.7, 5.5, 8.0, 11.0]
    result = ExitRuleAnalyzer.analyze(_mix(wins, losses))
    assert result.has_hard_take_profit is False
    assert result.take_profit_level_pct is None
    assert result.has_hard_stop_loss is False
    assert result.stop_loss_level_pct is None


def test_fixed_stop_loss_is_detected() -> None:
    wins = [0.6, 2.4, 5.0, 8.8, 1.3, 3.7]
    losses = [1.0, 1.01, 0.99, 1.02, 0.98, 1.0, 1.03]
    result = ExitRuleAnalyzer.analyze(_mix(wins, losses))
    assert result.has_hard_stop_loss is True
    assert result.stop_loss_level_pct == pytest.approx(-1.0, abs=0.02)


# --------------------------------------------------------------------------- #
# Nhãn hành vi
# --------------------------------------------------------------------------- #


def test_cutting_winners_and_sitting_on_losers_is_labelled() -> None:
    """Thắng nhỏ, thoát nhanh; thua to, ôm lâu — tỉ lệ thắng giấu hết chuyện này."""
    result = ExitRuleAnalyzer.analyze(
        _mix(_SCATTERED_SMALL_WINS, _SCATTERED_BIG_LOSSES,
             win_hold=120.0, loss_hold=4_000.0)
    )
    assert result.exit_style is ExitStyle.HOLD_LOSERS
    assert result.loss_to_win_ratio > 1.0
    assert result.hold_asymmetry > ExitRuleAnalyzer.HOLD_ASYMMETRY_THRESHOLD
    assert any("sat on" in line for line in result.evidence)


def test_running_winners_with_bounded_losses_is_labelled() -> None:
    result = ExitRuleAnalyzer.analyze(
        _mix(_SCATTERED_RUNNING_WINS, _SCATTERED_SMALL_LOSSES)
    )
    assert result.exit_style is ExitStyle.RUN_WINNERS_CUT_LOSSES
    assert result.win_tail_ratio >= ExitRuleAnalyzer.RUN_WINNERS_TAIL_RATIO


def test_two_holding_regimes_under_one_bot_are_surfaced() -> None:
    """Scalp và ôm hàng cùng tồn tại là hai hành vi, không phải một."""
    fast = [_trade(i, 1.5 if i % 2 else -1.4, 20.0) for i in range(10)]
    slow = [_trade(20 + i, 1.5 if i % 2 else -1.4, 20_000.0) for i in range(10)]
    result = ExitRuleAnalyzer.analyze(fast + slow)
    assert result.is_multi_modal is True
    assert set(result.hold_modes) == {"<1h", ">8d"}
    assert "MULTI_MODAL_HOLDING" in result.patterns


def test_patterns_keep_what_the_single_label_drops() -> None:
    result = ExitRuleAnalyzer.analyze(
        _mix(_SCATTERED_SMALL_WINS, _SCATTERED_BIG_LOSSES,
             win_hold=20.0, loss_hold=20_000.0)
    )
    assert result.exit_style is ExitStyle.HOLD_LOSERS
    assert "MULTI_MODAL_HOLDING" in result.patterns


def test_hold_histogram_covers_every_band_exactly_once() -> None:
    result = ExitRuleAnalyzer.analyze(_mix([2.0] * 6, [1.0] * 6, win_hold=30.0,
                                           loss_hold=100_000.0))
    assert list(result.hold_buckets) == list(HOLD_BUCKET_LABELS)
    assert sum(result.hold_buckets.values()) == result.priced_trades
    assert result.hold_buckets["<1h"] == 6
    assert result.hold_buckets[">8d"] == 6
    assert sum(result.hold_shape) == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# So sánh hai bot
# --------------------------------------------------------------------------- #


def _hold_only(hold_minutes: float):
    return ExitRuleAnalyzer.analyze(
        _mix([2.0, 2.5, 1.8, 2.2, 2.1, 1.9], [1.0, 1.2, 0.9, 1.1, 1.05, 0.95],
             win_hold=hold_minutes, loss_hold=hold_minutes)
    )


def test_adjacent_holding_bands_are_closer_than_distant_ones() -> None:
    """Khung thời gian giữ lệnh CÓ THỨ TỰ, phép đo phải tôn trọng điều đó.

    Giao histogram coi 2-4d và 4-8d xa nhau đúng bằng scalp với ôm hàng, vì
    chúng không chung bucket nào. Đây là test chặn đúng lỗi đó.
    """
    two_to_four_days = _hold_only(4_000.0)
    four_to_eight_days = _hold_only(9_000.0)
    minutes = _hold_only(20.0)

    near = ExitRuleAnalyzer.compare(two_to_four_days, four_to_eight_days)
    far = ExitRuleAnalyzer.compare(two_to_four_days, minutes)
    assert 0.0 < near["hold_distance"] < far["hold_distance"]
    assert far["hold_distance"] > 3 * near["hold_distance"]


def test_headline_distance_is_the_worse_axis_not_the_average() -> None:
    """Cùng nhịp giữ lệnh không được phép che đi luật thoát ngược nhau."""
    disciplined = ExitRuleAnalyzer.analyze(
        _mix(_SCATTERED_RUNNING_WINS, _SCATTERED_SMALL_LOSSES,
             win_hold=600.0, loss_hold=600.0)
    )
    bagholder = ExitRuleAnalyzer.analyze(
        _mix(_SCATTERED_SMALL_WINS, _SCATTERED_BIG_LOSSES,
             win_hold=600.0, loss_hold=600.0)
    )
    result = ExitRuleAnalyzer.compare(disciplined, bagholder)
    assert result["driver"] == "RULE"
    assert result["distance"] == result["rule_distance"]
    assert result["distance"] > result["hold_distance"]
    assert result["same_exit_style"] is False


def test_compare_names_the_component_that_differs_most() -> None:
    disciplined = ExitRuleAnalyzer.analyze(
        _mix([1.0, 1.1, 0.9, 1.2, 1.05, 0.95], [0.8, 0.9, 0.7, 1.0, 0.85, 0.75],
             win_hold=600.0, loss_hold=600.0)
    )
    bagholder = ExitRuleAnalyzer.analyze(
        _mix([1.0, 1.1, 0.9, 1.2, 1.05, 0.95], [4.0, 5.0, 3.5, 6.0, 4.5, 3.8],
             win_hold=120.0, loss_hold=12_000.0)
    )
    result = ExitRuleAnalyzer.compare(disciplined, bagholder)
    assert result["top_rule_component"] in ("loss-to-win size", "hold asymmetry")
    assert result["top_rule_gap"] > 0.1


def test_compare_refuses_an_uncharacterised_bot() -> None:
    thin = ExitRuleAnalyzer.analyze(_mix([2.0] * 2, [1.0] * 2))
    full = _hold_only(600.0)
    assert ExitRuleAnalyzer.compare(thin, full) is None
    assert ExitRuleAnalyzer.compare(full, thin) is None


def test_two_discretionary_bots_are_not_called_the_same_style() -> None:
    """DISCRETIONARY nghĩa là "không thấy quy luật", không phải một quy luật chung."""
    a = ExitRuleAnalyzer.analyze(
        _mix([0.5, 1.4, 3.0, 6.2, 2.1, 0.9], [0.3, 1.1, 2.7, 1.5, 0.8, 2.0])
    )
    b = ExitRuleAnalyzer.analyze(
        _mix([0.6, 1.5, 2.9, 5.9, 2.2, 1.0], [0.4, 1.0, 2.6, 1.6, 0.9, 1.9])
    )
    if a.exit_style is ExitStyle.DISCRETIONARY and b.exit_style is ExitStyle.DISCRETIONARY:
        assert ExitRuleAnalyzer.compare(a, b)["same_exit_style"] is False


def test_hold_losers_outranks_a_fixed_target_in_the_headline() -> None:
    """Chốt lời cứng nhỏ + không cắt lỗ + ôm lỗ = lưới/martingale.

    Gắn nhãn con bot đó là FIXED_TARGET tức là đưa nửa vô hại của hành vi lên
    tiêu đề và giấu nửa làm cháy tài khoản xuống dưới.
    """
    tight_target = [2.0, 2.02, 1.98, 2.05, 1.95, 2.01]
    result = ExitRuleAnalyzer.analyze(
        _mix(tight_target, _SCATTERED_BIG_LOSSES, win_hold=60.0, loss_hold=30_000.0)
    )
    assert result.has_hard_take_profit is True
    assert result.has_hard_stop_loss is False
    assert result.exit_style is ExitStyle.HOLD_LOSERS
    assert "FIXED_TARGET" in result.patterns
