"""A risk signal that fires on most of the population carries no information."""

from __future__ import annotations

from typing import List

import pytest

from Agent.backend.bot.mcp.analytics.behavior.detector import BehavioralPatternDetector
from Agent.backend.bot.mcp.schemas.bot_result import (
    BehavioralObservations,
    BotResult,
    OpenPosition,
    PositionSide,
    StrategyObservations,
    TradeLedgerItem,
)
from Agent.backend.report.qc.evaluator.lenses.behavioral_risk import BehavioralRiskLens
from Agent.backend.report.qc.evaluator.lenses.strategy_drift import StrategyDriftLens
from Agent.backend.report.qc.schemas.risk_assessment import EvidenceStatus

HOUR_MS = 3_600_000
START_MS = 1_780_000_000_000


def _trade(index: int, pnl: float, margin: float, symbol="BTC-USDT-SWAP", lever=10.0):
    open_ms = START_MS + index * HOUR_MS
    return TradeLedgerItem(
        trade_id=f"t{index}",
        symbol=symbol,
        side=PositionSide.LONG,
        open_time=open_ms,
        close_time=open_ms + 600_000,
        realized_pnl=pnl,
        margin=margin,
        leverage=lever,
        quantity=1.0,
        holding_time_minutes=10.0,
    )


def _analyze(trades: List[TradeLedgerItem], open_positions: int = 0):
    return BehavioralPatternDetector.analyze(trades, open_positions)


DAY_MS = 24 * HOUR_MS


def _calm_trades(count: int = 2) -> List[TradeLedgerItem]:
    """Closed-trade history that trips none of the OTHER behavioral signals.

    Widely spaced (30 days apart, so overtrading/loss-chasing/re-entry never
    fire), all winners with a constant margin (so martingale/leverage
    escalation never fire) and identical holding time (so the p90/median
    hold-time-explosion ratio is 1). This isolates whatever the test is
    actually checking -- the open-position-based averaging-down signal and
    the resulting `behavioral_risk_tier` -- from every other detector.
    """
    return [
        TradeLedgerItem(
            trade_id=f"calm{i}",
            symbol="BTC-USDT-SWAP",
            side=PositionSide.LONG,
            open_time=START_MS + i * 30 * DAY_MS,
            close_time=START_MS + i * 30 * DAY_MS + 600_000,
            realized_pnl=40.0,
            margin=100.0,
            leverage=10.0,
            quantity=1.0,
            holding_time_minutes=10.0,
        )
        for i in range(count)
    ]


def _open_position(
    position_id: str,
    *,
    symbol: str | None = "BTC-USDT-SWAP",
    side: PositionSide = PositionSide.LONG,
    attribution_source: str = "LEDGER",
    entry_price: float | None = 100.0,
    unrealized_pnl: float | None = None,
    open_time: int | None = START_MS,
) -> OpenPosition:
    return OpenPosition(
        position_id=position_id,
        symbol=symbol,
        side=side,
        attribution_source=attribution_source,
        entry_price=entry_price,
        unrealized_pnl=unrealized_pnl,
        open_time=open_time,
    )


def test_doubling_down_after_losses_on_one_market_is_flagged():
    trades, size = [], 100.0
    for i in range(20):
        losing = i % 2 == 0
        trades.append(_trade(i, -50.0 if losing else 40.0, size))
        size = size * 2.0 if losing else 100.0

    assert _analyze(trades).martingale_escalation_detected is True


def test_a_bot_that_simply_varies_its_size_is_not_called_martingale():
    """Without a control group, random sizing clears a bare post-loss threshold."""
    # Size cycles on a period of 4, outcome on a period of 3, so the two never
    # line up: escalation after a loss is as likely as escalation after a win.
    sizes = [100.0, 300.0, 120.0, 400.0]
    trades = [_trade(i, -50.0 if i % 3 == 0 else 40.0, sizes[i % 4]) for i in range(48)]

    result = _analyze(trades)

    assert result.martingale_escalation_detected is False


def test_escalation_is_judged_within_one_market_not_across_them():
    """Losing on BTC then opening a routine DOGE position is not doubling down."""
    trades = []
    for i in range(20):
        if i % 2 == 0:
            trades.append(_trade(i, -50.0, 100.0, symbol="BTC-USDT-SWAP"))
        else:
            trades.append(_trade(i, 40.0, 5_000.0, symbol="DOGE-USDT-SWAP"))

    assert _analyze(trades).martingale_escalation_detected is False


def test_one_leverage_bump_in_a_long_ledger_is_not_an_escalation_pattern():
    trades = [_trade(i, -10.0 if i == 0 else 20.0, 100.0) for i in range(40)]
    trades[1] = _trade(1, 20.0, 100.0, lever=25.0)

    assert _analyze(trades).leverage_escalation_detected is False


def _bot_with(strategy: StrategyObservations, trade_count: int = 100) -> BotResult:
    from Agent.none.test.conftest import FIXED_AS_OF_MS

    bot = BotResult.model_construct(
        strategy_observations=strategy,
        performance=type("P", (), {"trade_count": trade_count})(),
        trade_ledger_summary=[],
        as_of_ms=FIXED_AS_OF_MS,
    )
    return bot


def test_the_strategy_dimension_abstains_when_the_ledger_cannot_be_placed():
    """It used to return NOT_APPLICABLE for every bot, making the dimension dead."""
    result = StrategyDriftLens.evaluate(
        _bot_with(StrategyObservations(observed_profile="X", phase_coverage_pct=10.0))
    )

    assert result.status == EvidenceStatus.UNKNOWN


def test_profit_concentrated_in_one_regime_raises_the_strategy_score():
    spread = StrategyDriftLens.evaluate(
        _bot_with(
            StrategyObservations(
                observed_profile="X",
                phase_coverage_pct=90.0,
                regime_dependence_pct=30.0,
                tested_in_downtrend=True,
            )
        )
    )
    concentrated = StrategyDriftLens.evaluate(
        _bot_with(
            StrategyObservations(
                observed_profile="X",
                phase_coverage_pct=90.0,
                regime_dependence_pct=95.0,
                best_phase="UPTREND_VOLATILE",
                tested_in_downtrend=True,
            )
        )
    )

    assert concentrated.score > spread.score
    assert concentrated.status == EvidenceStatus.AVAILABLE
    assert any("95%" in finding for finding in concentrated.key_findings)


def test_never_having_traded_a_downtrend_counts_against_the_bot():
    untested = StrategyDriftLens.evaluate(
        _bot_with(
            StrategyObservations(
                observed_profile="X",
                phase_coverage_pct=90.0,
                tested_in_downtrend=False,
            )
        )
    )
    tested = StrategyDriftLens.evaluate(
        _bot_with(
            StrategyObservations(
                observed_profile="X",
                phase_coverage_pct=90.0,
                tested_in_downtrend=True,
            )
        )
    )

    assert untested.score > tested.score


def test_confidence_follows_how_much_of_the_ledger_was_placed():
    result = StrategyDriftLens.evaluate(
        _bot_with(
            StrategyObservations(
                observed_profile="X",
                phase_coverage_pct=60.0,
                tested_in_downtrend=True,
            )
        )
    )

    assert result.confidence == pytest.approx(0.6)


# --------------------------------------------------------------------------- #
# Việc 1-3: averaging down phải được đo từ THÊM vị thế vào một hướng ĐANG LỖ
# trên CÙNG một mã, không phải suy ra từ "đang mở >= 3 vị thế" -- xem
# Agent/backend/mcp/analytics/behavior/detector.py và
# Agent/backend/qc/evaluator/lenses/behavioral_risk.py.
# --------------------------------------------------------------------------- #


def test_many_open_positions_on_different_symbols_is_not_averaging_down():
    """50 vị thế mở trên 50 mã khác nhau là một bot đa mã, không phải bằng
    chứng gia tăng vị thế khi đang lỗ -- không mã nào lặp lại nên không có
    'nhóm' nào để xét lỗ/lãi."""
    positions = [
        _open_position(f"p{i}", symbol=f"SYM{i}-USDT-SWAP", unrealized_pnl=-1.0)
        for i in range(50)
    ]

    result = BehavioralPatternDetector.analyze(
        _calm_trades(), current_open_positions=50, open_positions=positions
    )

    assert result.averaging_down_detected is False
    assert result.averaging_down_suspected is False
    assert result.behavioral_risk_tier == "LOW"


def test_adding_to_a_losing_position_at_a_worse_price_is_averaging_down():
    """2 vị thế cùng mã, cùng hướng: vị thế sau vào giá thấp hơn (bất lợi hơn
    với LONG) và cả nhóm đang lỗ -- đây chính là averaging down."""
    positions = [
        _open_position(
            "p1",
            entry_price=100.0,
            unrealized_pnl=-5.0,
            open_time=START_MS,
        ),
        _open_position(
            "p2",
            entry_price=90.0,  # giá vào sau THẤP hơn -> bất lợi hơn với LONG
            unrealized_pnl=-8.0,
            open_time=START_MS + HOUR_MS,
        ),
    ]

    result = BehavioralPatternDetector.analyze(
        _calm_trades(), current_open_positions=2, open_positions=positions
    )

    assert result.averaging_down_detected is True
    assert result.averaging_down_suspected is False
    assert any("BTC-USDT-SWAP" in e for e in result.evidence)


def test_adding_to_a_winning_position_is_not_averaging_down():
    """Cùng mã, cùng hướng, cùng kiểu nhồi lệnh -- nhưng nhóm đang LÃI, không
    phải LỖ. Nhồi lệnh khi đúng hướng là chiến lược, không phải averaging
    down."""
    positions = [
        _open_position(
            "p1",
            entry_price=100.0,
            unrealized_pnl=5.0,
            open_time=START_MS,
        ),
        _open_position(
            "p2",
            entry_price=105.0,  # giá vào sau CAO hơn -> không bất lợi với LONG
            unrealized_pnl=8.0,
            open_time=START_MS + HOUR_MS,
        ),
    ]

    result = BehavioralPatternDetector.analyze(
        _calm_trades(), current_open_positions=2, open_positions=positions
    )

    assert result.averaging_down_detected is False
    assert result.averaging_down_suspected is False


def test_missing_symbol_or_pnl_is_not_scored_only_marked_unmeasured():
    """Vị thế thiếu symbol/PnL (OKX ẩn instrument) không được dùng làm bằng
    chứng buộc tội -- chỉ được phản ánh là chưa đo được."""
    positions = [
        _open_position(
            "p1", symbol=None, attribution_source="NONE", unrealized_pnl=None
        ),
        _open_position("p2", symbol="ETH-USDT-SWAP", unrealized_pnl=3.0),
    ]

    result = BehavioralPatternDetector.analyze(
        _calm_trades(), current_open_positions=2, open_positions=positions
    )

    assert result.averaging_down_detected is False
    # Không thể loại trừ averaging down trên vị thế bị ẩn -> phản ánh là
    # chưa đo được (suspected), nhưng lens (kiểm tra ở dưới) không được cộng
    # điểm cho việc này.
    assert result.averaging_down_suspected is True
    assert any("not enough data" in e or "not measurable" in e for e in result.evidence)

    lens_result = BehavioralRiskLens.evaluate(
        BotResult.model_construct(
            behavioral_observations=result, trade_ledger_summary=list(range(50))
        )
    )
    # Điểm nền là 10; không tín hiệu buộc tội nào khác được kích hoạt trong
    # kịch bản này (đã dùng _calm_trades), nên điểm phải giữ nguyên ở 10 --
    # không có +25 "nghi ngờ" như hành vi cũ.
    assert lens_result.score == pytest.approx(10.0)
    assert lens_result.confidence < 1.0  # bị hạ vì thiếu dữ liệu, không phải vì tội


def test_open_position_count_alone_no_longer_inflates_the_behavioral_tier():
    """Trước đây chỉ cần mở >= 3 vị thế là behavioral_risk_tier bị đẩy lên
    HIGH (0.75 trong composite max()), bất kể có bằng chứng gì hay không.
    Giờ số lượng vị thế mở đơn thuần (không có danh sách chi tiết, hoặc danh
    sách chi tiết nhưng không mã nào trùng) không còn được phép đẩy tier
    lên HIGH/CRITICAL."""
    # (a) Chỉ có số đếm, không có danh sách vị thế chi tiết -- trường hợp
    # service.py hiện tại (chưa truyền open_positions list).
    count_only = BehavioralPatternDetector.analyze(
        _calm_trades(), current_open_positions=5, open_positions=None
    )
    assert count_only.behavioral_risk_tier not in ("HIGH", "CRITICAL")

    # (b) Có danh sách chi tiết, >= 3 vị thế, nhưng không mã nào trùng.
    distinct_symbols = [
        _open_position(f"p{i}", symbol=f"SYM{i}-USDT-SWAP", unrealized_pnl=1.0)
        for i in range(5)
    ]
    with_list = BehavioralPatternDetector.analyze(
        _calm_trades(), current_open_positions=5, open_positions=distinct_symbols
    )
    assert with_list.behavioral_risk_tier not in ("HIGH", "CRITICAL")


def _lens_score(**flags) -> float:
    """Điểm chiều hành vi cho một bộ cờ, bỏ qua mọi tín hiệu khác."""
    obs = BehavioralObservations(behavioral_risk_tier="LOW", evidence=["x"], **flags)
    return BehavioralRiskLens.evaluate(
        BotResult.model_construct(
            behavioral_observations=obs, trade_ledger_summary=list(range(50))
        )
    ).score


def test_adding_to_loser_scales_continuously_with_measured_escalation() -> None:
    """Chấm theo ĐẠI LƯỢNG ĐO ĐƯỢC, không theo nhãn chiến lược.

    "DCA/lưới" và "martingale" là hai đầu của cùng một trục: nhồi thêm khi
    đang lỗ, và mỗi lần nhồi lớn hơn bao nhiêu. Điểm phải là hàm ĐƠN ĐIỆU
    TĂNG theo `size_escalation_excess` -- nếu thay bằng hai hằng số rẽ nhánh
    theo tên chiến lược thì mọi trường hợp nằm giữa đều bị ép về một trong
    hai hộp, và bài test này sẽ bắt được.
    """
    scores = [
        _lens_score(averaging_down_detected=True, size_escalation_excess=x)
        for x in (0.0, 0.05, 0.1, 0.2, 0.3, 0.6, 1.0)
    ]
    assert all(b >= a for a, b in zip(scores, scores[1:])), (
        f"phải đơn điệu tăng, đo được: {scores}"
    )
    assert scores[0] < scores[-1], "phải thực sự tăng, không phải hằng số"
    # Có ít nhất 4 mức khác nhau: một thang thật, không phải hai hằng số
    # đội lốt.
    assert len({round(x, 6) for x in scores}) >= 4, scores


def test_flat_size_adding_stays_below_the_destructive_veto_band() -> None:
    """Nhồi đều tay (không nâng cỡ) không được chạm sàn veto.

    Ngưỡng 85 trong `Agent/backend/qc/scoring/fusion.py` ép điểm rủi ro lên
    88 kèm lý do "hành vi giao dịch hủy hoại". Đo trên 31 bot thật: 12 bot
    nhồi thêm khi lỗ nhưng chỉ 1 bot nâng cỡ lệnh -- nếu cả 12 cùng chạm
    ngưỡng này thì 11 bot bình thường bị dán nhãn nguy hiểm
    (RuiJie 41 -> 88, Shallow-Pair-Frog 35 -> 88, Fly-000 49 -> 88).
    """
    flat = _lens_score(averaging_down_detected=True, size_escalation_excess=0.0)
    assert 0 < flat < 85
    # Cộng thêm một tín hiệu vừa phải vẫn chưa được chạm veto.
    with_one_more = _lens_score(
        averaging_down_detected=True,
        size_escalation_excess=0.0,
        overtrading_score=0.9,
    )
    assert with_one_more < 85


def test_strong_escalation_after_losses_still_reaches_the_veto_band() -> None:
    """Bản sửa trên không được làm hỏng việc bắt bot thật sự tự huỷ."""
    obs = BehavioralObservations(
        behavioral_risk_tier="CRITICAL",
        evidence=["x"],
        martingale_escalation_detected=True,
        averaging_down_detected=True,
        size_escalation_excess=0.45,
        loss_chasing_score=0.9,
    )
    result = BehavioralRiskLens.evaluate(
        BotResult.model_construct(
            behavioral_observations=obs, trade_ledger_summary=list(range(50))
        )
    )
    assert result.score >= 85


def test_escalation_after_wins_is_netted_out_by_the_control_group() -> None:
    """Bot chỉ hay đổi cỡ lệnh nói chung không được tính là gấp thếp.

    `size_escalation_excess` đã trừ nhóm đối chứng (nâng cỡ sau lệnh THẮNG)
    ngay trong detector, nên một bot nâng cỡ đều cả sau thắng lẫn sau thua
    sẽ có excess = 0 và chỉ nhận đúng mức nền.
    """
    varies_generally = _lens_score(
        averaging_down_detected=True, size_escalation_excess=0.0
    )
    targets_losses = _lens_score(
        averaging_down_detected=True, size_escalation_excess=0.45
    )
    assert targets_losses > varies_generally


def _trade_missing_size(index: int, pnl: float, *, lever=None):
    """Lệnh mà OKX KHÔNG trả cỡ lệnh (và tuỳ chọn cả đòn bẩy)."""
    open_ms = START_MS + index * HOUR_MS
    return TradeLedgerItem(
        trade_id=f"m{index}",
        symbol="BTC-USDT-SWAP",
        side=PositionSide.LONG,
        open_time=open_ms,
        close_time=open_ms + 600_000,
        realized_pnl=pnl,
        margin=None,
        notional=None,
        leverage=lever,
        quantity=1.0,
        holding_time_minutes=10.0,
    )


def test_missing_trade_size_is_not_read_as_an_escalation() -> None:
    """Thiếu dữ liệu KHÔNG được thay bằng 0 rồi đem so sánh.

    Bản cũ dùng `trade.margin or trade.notional or 0.0`. Phép so sau đó lệch
    một chiều: lệnh TRƯỚC thiếu cỡ -> `cỡ_sau > 0 * 1.25` gần như luôn đúng
    -> hệ thống bịa ra một lần nâng cỡ lệnh chưa từng xảy ra, và đủ vài lần
    như thế là thành cáo buộc martingale.

    Kịch bản dưới đây xen kẽ lệnh thiếu cỡ với lệnh có cỡ, toàn bộ sau lệnh
    lỗ -- đúng hình dạng mà bug cũ biến thành martingale.
    """
    trades = []
    for index in range(10):
        if index % 2 == 0:
            trades.append(_trade_missing_size(index, -50.0, lever=10.0))
        else:
            trades.append(_trade(index, -40.0, margin=1000.0))

    result = _analyze(trades)
    assert result.martingale_escalation_detected is False
    assert result.size_escalation_score == pytest.approx(0.0)
    assert result.size_escalation_excess == pytest.approx(0.0)


def test_missing_leverage_is_not_read_as_leverage_escalation() -> None:
    """`đòn_bẩy_sau > 0 + 1` đúng với hầu hết mọi lệnh -- không được để nó bắn.

    Cáo buộc "tăng đòn bẩy sau lệnh lỗ" cộng thẳng điểm ở lens, nên bịa ra nó
    từ một trường thiếu dữ liệu là sai nghiêm trọng.
    """
    trades = []
    for index in range(8):
        if index % 2 == 0:
            trades.append(_trade_missing_size(index, -50.0, lever=None))
        else:
            trades.append(_trade(index, -40.0, margin=1000.0, lever=20.0))

    assert _analyze(trades).leverage_escalation_detected is False


def test_a_real_escalation_is_still_caught_when_the_data_is_there() -> None:
    """Bản sửa trên không được làm câm cảm biến: có dữ liệu thì vẫn phải bắt."""
    trades = [
        _trade(0, -50.0, margin=100.0),
        _trade(1, -60.0, margin=200.0),
        _trade(2, -70.0, margin=400.0),
        _trade(3, -80.0, margin=900.0),
        _trade(4, -90.0, margin=2000.0),
    ]
    result = _analyze(trades)
    assert result.size_escalation_score > 0.5
    assert result.martingale_escalation_detected is True
