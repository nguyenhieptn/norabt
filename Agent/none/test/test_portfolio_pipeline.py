"""Gộp N bot thành MỘT báo cáo, và mục đa dạng hoá gắn kèm nó.

Hai nhóm câu hỏi tách bạch: bộ gộp có dựng đúng một cuốn sổ lệnh chung không
(`PortfolioAggregator`), và mục đa dạng hoá có nói đúng thứ chỉ một TẬP bot
mới có không (`PortfolioQCService`). Chạy thật trên fixture đã commit trong
repo, không cần mạng, không cần khoá OKX.
"""

from __future__ import annotations

import pytest

from Agent.backend.bot.mcp.aggregate import PortfolioAggregator
from Agent.backend.bot.mcp.schemas.bot_result import PositionSide, RiskMeasurementMode
from Agent.backend.pipeline_portfolio import (
    PortfolioBotRequest,
    PortfolioSupervisionPipeline,
)
from Agent.backend.report.qc.history.portfolio_store import PortfolioHistoryStore
from Agent.backend.report.qc.portfolio.schemas import PortfolioVerdict, StyleVerdict
from Agent.backend.report.qc.portfolio.service import (
    PortfolioCandidate,
    PortfolioQCService,
)
from Agent.none.test.conftest import FIXED_AS_OF_MS
from Agent.none.test.portfolio_factory import BASE_MS, DAY_MS, make_bot, make_trades

_SERIES = [1.0, -2.0, 3.0, -1.0, 0.5, -0.5, 2.0, -3.0, 1.5, -1.5] * 6

# Ba fixture đã commit, ~86 ngày lịch sử chung, ba công cụ khác nhau: đúng
# hình dạng bài toán -- một cuốn sổ trông có vẻ phân tán theo mã.
_MEMBERS = (
    PortfolioBotRequest(asset="BTC", bot_folder_name="bot_35F888C7BB441B2B"),
    PortfolioBotRequest(asset="ETH", bot_folder_name="bot_6F262ADB3B44266C"),
    PortfolioBotRequest(asset="WBTC", bot_folder_name="bot_58D7D205FB591484"),
)


def _assess(bots, **kwargs):
    return PortfolioQCService.assess_portfolio(
        [PortfolioCandidate(bot=bot) for bot in bots], iterations=500, **kwargs
    )


# --------------------------------------------------------------------------- #
# Bộ gộp: một cuốn sổ lệnh chung
# --------------------------------------------------------------------------- #


def test_merged_ledger_keeps_every_trade_in_time_order() -> None:
    a = make_bot("AAA", make_trades(_SERIES))
    b = make_bot("BBB", make_trades(_SERIES, start_ms=BASE_MS + 12 * 3_600_000))
    combined = PortfolioAggregator.combine([a, b], simulation_iterations=50)
    trades = combined.trade_ledger_summary
    assert len(trades) == 120
    assert [t.close_time for t in trades] == sorted(t.close_time for t in trades)
    assert combined.performance.total_pnl == pytest.approx(
        a.performance.total_pnl + b.performance.total_pnl
    )


def test_trade_ids_are_namespaced_so_two_members_never_collide() -> None:
    """OKX numbers trades per account, so `t0` exists in both ledgers."""
    a = make_bot("AAA", make_trades(_SERIES))
    b = make_bot("BBB", make_trades(_SERIES))
    combined = PortfolioAggregator.combine([a, b], simulation_iterations=50)
    ids = [trade.trade_id for trade in combined.trade_ledger_summary]
    assert len(set(ids)) == len(ids)
    assert any(tid.startswith("AAA:") for tid in ids)
    assert any(tid.startswith("BBB:") for tid in ids)


def test_drawdowns_at_different_times_do_not_stack() -> None:
    """Đây là lý do phải trộn sổ lệnh thay vì cộng hay bình quân chỉ số.

    Hai bot cùng sụt 10 đơn vị nhưng vào hai giai đoạn khác nhau. Tài khoản
    gộp chưa bao giờ sụt 20; cộng chỉ số lại sẽ nói là 20, còn bình quân nói
    là 10 một cách tình cờ đúng. Chỉ đường cong gộp mới trả lời được.
    """
    early = make_bot("AAA", make_trades([-1.0] * 10 + [1.0] * 20))
    late = make_bot(
        "BBB",
        make_trades([1.0] * 20 + [-1.0] * 10, start_ms=BASE_MS + 30 * DAY_MS),
    )
    combined = PortfolioAggregator.combine([early, late], simulation_iterations=50)
    merged = combined.drawdown_analysis.max_dd_abs
    a_dd = early.drawdown_analysis.max_dd_abs
    b_dd = late.drawdown_analysis.max_dd_abs
    assert merged == pytest.approx(max(a_dd, b_dd))
    assert merged < a_dd + b_dd
    assert combined.performance.total_pnl == pytest.approx(
        early.performance.total_pnl + late.performance.total_pnl
    )


def test_capital_is_summed_or_withheld_never_partially_summed() -> None:
    a = make_bot("AAA", make_trades(_SERIES), capital_at_risk=10_000.0)
    b = make_bot("BBB", make_trades(_SERIES), capital_at_risk=30_000.0)
    assert PortfolioAggregator.combine(
        [a, b], simulation_iterations=50
    ).capital.capital_at_risk == pytest.approx(40_000.0)

    blind = make_bot("CCC", make_trades(_SERIES), capital_at_risk=None)
    partial = PortfolioAggregator.combine([a, blind], simulation_iterations=50)
    assert partial.capital.capital_at_risk is None
    assert any("cannot be summed" in w for w in partial.capital.warnings)


def test_opposing_members_make_a_net_book_not_a_long_one() -> None:
    a = make_bot("AAA", make_trades(_SERIES), side=PositionSide.LONG,
                 current_notional=5_000.0)
    b = make_bot("BBB", make_trades(_SERIES), side=PositionSide.SHORT,
                 current_notional=3_000.0)
    state = PortfolioAggregator.combine([a, b], simulation_iterations=50).current_state
    assert state.current_position_side is PositionSide.NET
    assert state.current_notional == pytest.approx(8_000.0)
    assert state.net_exposure == pytest.approx(2_000.0)


def test_no_liquidation_price_is_fabricated_for_a_portfolio() -> None:
    """Giá thanh lý thuộc về MỘT vị thế trên MỘT công cụ. Bịa ra một con số ở
    đây sẽ bị đọc thành mức gọi ký quỹ thật."""
    bots = [make_bot(c, make_trades(_SERIES)) for c in ("AAA", "BBB")]
    state = PortfolioAggregator.combine(bots, simulation_iterations=50).current_state
    assert state.liquidation_price is None
    assert state.liquidation_distance_pct is None


def test_dominant_exposure_decides_which_market_the_lenses_judge() -> None:
    big = make_bot("AAA", make_trades(_SERIES), symbol="BTC",
                   current_notional=90_000.0)
    small = make_bot("BBB", make_trades(_SERIES, symbol="SOL"), symbol="SOL",
                     current_notional=10_000.0)
    combined = PortfolioAggregator.combine([big, small], simulation_iterations=50)
    assert combined.identity.symbol == "BTC"
    assert combined.identity.symbol_exposure_share["BTC"] == pytest.approx(0.9)
    assert any("largest exposure" in line
               for line in combined.identity.identity_warnings)


def test_evidence_quality_is_the_weakest_member_not_the_average() -> None:
    good = make_bot("AAA", make_trades(_SERIES))
    weak = make_bot("BBB", make_trades(_SERIES))
    weak.data_quality.completeness_score = 0.2
    weak.data_quality.freshness_ms = 999_999
    weak.data_quality.measurement_mode = RiskMeasurementMode.LIMITED
    combined = PortfolioAggregator.combine([good, weak], simulation_iterations=50)
    assert combined.data_quality.completeness_score == pytest.approx(0.2)
    assert combined.data_quality.freshness_ms == 999_999
    assert combined.data_quality.measurement_mode is RiskMeasurementMode.LIMITED


def test_merged_semantics_are_declared_not_left_to_assumption() -> None:
    bots = [make_bot(c, make_trades(_SERIES)) for c in ("AAA", "BBB")]
    combined = PortfolioAggregator.combine(bots, simulation_iterations=50)
    # Khoá Ý NGHĨA, không ghim nguyên văn: hai câu này đã phải rút gọn một
    # lần vì chúng trở thành body copy trên trang, và sẽ còn rút gọn nữa.
    # Điều phải giữ là người đọc được NÓI RÕ rằng mọi con số là của sổ gộp.
    joined = " ".join(combined.data_quality.warnings).lower()
    assert "merged" in joined or "combined" in joined
    assert "2 bots" in joined
    assert "ledger" in joined


def test_combined_bot_carries_an_exit_fingerprint_of_the_whole_book() -> None:
    bots = [make_bot(c, make_trades(_SERIES)) for c in ("AAA", "BBB")]
    combined = PortfolioAggregator.combine(bots, simulation_iterations=50)
    assert combined.exit_rule is not None
    assert combined.exit_rule.is_valid
    assert combined.exit_rule.priced_trades == 120


def test_a_portfolio_needs_two_distinct_bots() -> None:
    bot = make_bot("AAA", make_trades(_SERIES))
    with pytest.raises(ValueError, match="at least two"):
        PortfolioAggregator.combine([bot])
    with pytest.raises(ValueError, match="more than once"):
        PortfolioAggregator.combine([bot, bot])


def test_portfolio_id_is_the_member_set_not_the_order() -> None:
    assert PortfolioAggregator.portfolio_id(["B", "A"]) == (
        PortfolioAggregator.portfolio_id(["A", "B"])
    )


# --------------------------------------------------------------------------- #
# Mục đa dạng hoá: kết quả
# --------------------------------------------------------------------------- #


def test_identical_bots_are_called_a_correlation_cluster() -> None:
    result = _assess([make_bot(c, make_trades(_SERIES)) for c in ("AAA", "BBB")])
    assert result.verdict is PortfolioVerdict.HIGH_CORRELATION_CLUSTER
    assert "move as one" in result.verdict_reason


def test_offsetting_bots_are_called_diversified() -> None:
    result = _assess([
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades([-v for v in _SERIES])),
    ])
    assert result.verdict is PortfolioVerdict.DIVERSIFIED


def test_a_concealed_member_downgrades_a_good_looking_verdict() -> None:
    """Ẩn một thành viên khỏi phép đo không được phép làm rổ trông TỐT hơn.

    Hai bot còn lại thật sự đối nghịch nhau -- DIVERSIFIED là đúng cho HAI bot
    đó. Nhưng một bot thứ ba đã NỘP vào rổ mà không đo được (giấu sổ lệnh)
    nghĩa là con số này chỉ đúng cho một phần của rổ thật, nên verdict phải
    lùi về INSUFFICIENT_EVIDENCE thay vì khẳng định nhầm cả rổ đã phân tán.
    """
    without = _assess([
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades([-v for v in _SERIES])),
    ])
    assert without.verdict is PortfolioVerdict.DIVERSIFIED

    with_concealed = _assess(
        [
            make_bot("AAA", make_trades(_SERIES)),
            make_bot("BBB", make_trades([-v for v in _SERIES])),
        ],
        concealed_members=["ZZZ"],
    )
    assert with_concealed.verdict is PortfolioVerdict.INSUFFICIENT_EVIDENCE
    assert "ZZZ" in with_concealed.verdict_reason
    assert "cannot be called diversification" in with_concealed.verdict_reason
    assert any("ZZZ" in line for line in with_concealed.limitations)


def test_submitted_member_count_includes_concealed_and_error_codes_not_counted_in_members() -> None:
    """Phát hiện thật (2026-09-24): `/api/portfolios` từng đọc `member_count`
    (chỉ đếm bot ĐO ĐƯỢC) làm số bot đã nộp -- một request 4 mã, 1 bị giấu
    sổ, lưu vào lịch sử thành "3 bot" không để lại dấu vết. `member_codes`/
    `members` không bao giờ chứa mã bị loại (concealed hay error), vì mã đó
    không hề trở thành `PortfolioCandidate`; `submitted_member_count` phải
    cộng lại đúng cả ba nhóm."""
    result = _assess(
        [
            make_bot("AAA", make_trades(_SERIES)),
            make_bot("BBB", make_trades([-v for v in _SERIES])),
        ],
        concealed_members=["ZZZ"],
        error_members=["YYY", "XXX"],
    )
    assert len(result.member_codes) == 2  # chi 2 bot do duoc
    assert result.submitted_member_count == 5  # 2 do duoc + 1 giau so + 2 loi doc
    assert result.concealed_member_codes == ["ZZZ"]


def test_submitted_member_count_matches_measured_count_with_no_exclusions() -> None:
    result = _assess([
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades([-v for v in _SERIES])),
    ])
    assert result.submitted_member_count == len(result.member_codes) == 2
    assert result.concealed_member_codes == []


def test_a_concealed_member_gives_the_run_a_different_assessment_id() -> None:
    """Phát hiện thật, trực tiếp trên container đang chạy (2026-09-24): hai
    request khác nhau -- cùng 2 bot đo được, một request có thêm một bot thứ
    ba bị giấu sổ, request kia không -- từng ra CÙNG một `assessment_id` vì
    digest chỉ băm các bot ĐO ĐƯỢC. `PortfolioHistoryStore.append` coi hai id
    giống nhau là "không đổi gì", nên bản ghi có `submitted_member_count`
    đúng bị bản ghi cũ (thiếu trường đó) âm thầm đè mất -- không phải do lỗi
    ghi, mà do hai request LẼ RA khác nhau lại chung một chữ ký.
    """
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades([-v for v in _SERIES])),
    ]
    without_concealed = _assess(bots)
    with_concealed = _assess(bots, concealed_members=["ZZZ"])
    assert without_concealed.assessment_id != with_concealed.assessment_id

    with_a_different_concealed_bot = _assess(bots, concealed_members=["YYY"])
    assert with_concealed.assessment_id != with_a_different_concealed_bot.assessment_id

    with_an_error_instead = _assess(bots, error_members=["ZZZ"])
    assert with_concealed.assessment_id != with_an_error_instead.assessment_id


def test_a_concealed_member_does_not_soften_an_already_bad_verdict() -> None:
    """HIGH_CORRELATION_CLUSTER là một cảnh báo, không phải tin tốt -- một bot
    vô hình không thể làm cảnh báo đó trông NHẸ hơn, nên không cần hạ xuống."""
    result = _assess(
        [
            make_bot("AAA", make_trades(_SERIES)),
            make_bot("BBB", make_trades(_SERIES)),
        ],
        concealed_members=["ZZZ"],
    )
    assert result.verdict is PortfolioVerdict.HIGH_CORRELATION_CLUSTER


# --------------------------------------------------------------------------- #
# Confidence phải giảm theo tỉ lệ, không chỉ nhị phân "có/không concealed".
# Sếp (2026-09-23): "Giảm confidence của portfolio theo tỉ lệ vốn hoặc số bot
# bị concealed. Nếu tỉ lệ này vượt ngưỡng thì hạ verdict."
# --------------------------------------------------------------------------- #


def test_measurement_coverage_is_full_with_no_concealed_member() -> None:
    result = _assess([
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades([-v for v in _SERIES])),
    ])
    assert result.measurement_coverage_pct == pytest.approx(100.0)


def test_measurement_coverage_falls_back_to_headcount_without_capital_data() -> None:
    """Không biết vốn của bot giấu sổ -> không được đoán, dùng đếm đầu bot."""
    result = _assess(
        [
            make_bot("AAA", make_trades(_SERIES)),
            make_bot("BBB", make_trades([-v for v in _SERIES])),
        ],
        concealed_members=["ZZZ"],
    )
    # 2 do duoc / (2 do duoc + 1 giau) = 66.7%
    assert result.measurement_coverage_pct == pytest.approx(200.0 / 3.0, abs=0.1)


def test_measurement_coverage_is_capital_weighted_when_known() -> None:
    """Vốn của bot giấu sổ nhỏ so với 2 bot đo được (10k mỗi bot) -> độ phủ
    theo vốn phải cao hơn hẳn con số đếm đầu bot (66.7%), và đủ cao để KHÔNG
    hạ verdict -- một bot giấu sổ nhưng vốn không đáng kể không được phép
    làm một verdict tốt-thật trở thành INSUFFICIENT_EVIDENCE."""
    result = _assess(
        [
            make_bot("AAA", make_trades(_SERIES)),
            make_bot("BBB", make_trades([-v for v in _SERIES])),
        ],
        concealed_members=["ZZZ"],
        concealed_capital_usdt={"ZZZ": 100.0},
    )
    # 20,000 do duoc / (20,000 + 100 giau) ~ 99.5%
    assert result.measurement_coverage_pct == pytest.approx(20000.0 / 20100.0 * 100.0, abs=0.1)
    assert result.measurement_coverage_pct > PortfolioQCService.MIN_MEASUREMENT_COVERAGE_PCT
    assert result.verdict is PortfolioVerdict.DIVERSIFIED


def test_a_large_concealed_capital_share_downgrades_even_though_headcount_looks_fine() -> None:
    """Ngược lại: vốn của bot giấu sổ LỚN hơn hẳn 2 bot đo được -- độ phủ
    theo vốn thấp, dưới ngưỡng, nên verdict phải hạ dù chỉ có 1/3 bot bị
    giấu (đếm đầu bot một mình sẽ nói 66.7%, KHÔNG dưới ngưỡng 75% -- vốn là
    tín hiệu đúng phải thắng ở đây, không phải đầu bot)."""
    result = _assess(
        [
            make_bot("AAA", make_trades(_SERIES)),
            make_bot("BBB", make_trades([-v for v in _SERIES])),
        ],
        concealed_members=["ZZZ"],
        concealed_capital_usdt={"ZZZ": 100_000.0},
    )
    assert result.measurement_coverage_pct < PortfolioQCService.MIN_MEASUREMENT_COVERAGE_PCT
    assert result.verdict is PortfolioVerdict.INSUFFICIENT_EVIDENCE
    assert "only" in result.verdict_reason and "measured" in result.verdict_reason


def test_a_minority_of_significant_pairs_is_insufficient_evidence_even_with_one_extreme_pair() -> None:
    """Sếp's explicit rule (2026-09-23, M1): dưới 50% số cặp có ý nghĩa thì
    verdict phải là INSUFFICIENT_EVIDENCE -- kể cả khi một cặp trong đó cực
    đoan và có thật (AAA-BBB, r=1.0). 1 trên 3 cặp có ý nghĩa (33%) là dưới
    ngưỡng, nên verdict không được phép nói gì chắc chắn về CẢ RỔ, dù nó có
    một cặp đáng ngại thật sự. Đây LÀ hành vi mong muốn, không phải hồi quy:
    trước bản vá này chính cặp AAA-BBB một mình đã đủ kéo verdict thành
    HIGH_CORRELATION_CLUSTER (xem test kế bên cho đúng trường hợp đó với chỉ
    2 bot, nơi 1 cặp = 100% số cặp)."""
    import numpy as np

    rng = np.random.default_rng(5)
    result = _assess([
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(_SERIES)),
        make_bot("CCC", make_trades(list(rng.normal(0, 3, 60)))),
    ])
    assert result.correlation.max_pearson == pytest.approx(1.0)
    assert result.verdict is PortfolioVerdict.INSUFFICIENT_EVIDENCE
    assert "Only 1 of 3 pair(s)" in result.verdict_reason


def test_an_extreme_pair_alone_still_reads_as_high_correlation_cluster() -> None:
    """Cùng cặp AAA-BBB (r=1.0) như trên, nhưng KHÔNG có CCC pha loãng tỉ lệ
    -- 2 bot nghĩa là chỉ có 1 cặp, và cặp đó chiếm 100% số cặp đo được, nên
    verdict vẫn phải bắt được nó."""
    result = _assess([
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(_SERIES)),
    ])
    assert result.correlation.max_pearson == pytest.approx(1.0)
    assert result.verdict is PortfolioVerdict.HIGH_CORRELATION_CLUSTER
    assert "move as one" in result.verdict_reason


def test_no_shared_window_is_insufficient_evidence_not_diversified() -> None:
    result = _assess([
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(_SERIES, start_ms=BASE_MS + 400 * DAY_MS)),
    ])
    assert result.verdict is PortfolioVerdict.INSUFFICIENT_EVIDENCE
    assert result.joint_simulation is None


def test_there_is_no_second_risk_score_beside_the_combined_one() -> None:
    """Một danh mục có đúng MỘT điểm rủi ro, do mười lens sinh ra."""
    result = _assess([make_bot(c, make_trades(_SERIES)) for c in ("AAA", "BBB")])
    fields = type(result).model_fields
    assert "portfolio_risk_score" not in fields
    assert "member_weighted_risk_score" not in fields
    assert "score_adjustments" not in fields
    assert result.combined_risk_score is None  # chưa truyền `combined`


# --------------------------------------------------------------------------- #
# Mục đa dạng hoá: cách chơi
# --------------------------------------------------------------------------- #


def test_same_behaviour_with_uncorrelated_results_is_flagged_as_a_trap() -> None:
    """Đây là ca tính năng này sinh ra để bắt.

    Hai bot có CÙNG phân bố lệnh thoát (cùng luật chơi) nhưng thứ tự xảy ra
    khác nhau nên PnL không tương quan. Nhìn vào ma trận PnL sẽ kết luận đã
    phân tán; thực tế chúng là một chiến lược, và khi chế độ thị trường đổi
    thì cùng hỏng.
    """
    # Hoán vị, KHÔNG phải xoay vòng: `_SERIES` có chu kỳ 10 nên xoay 30 phần
    # tử trả lại đúng chính nó và hai bot sẽ tương quan hoàn hảo.
    import numpy as np

    shuffled = list(np.random.default_rng(0).permutation(np.array(_SERIES)))
    assert sorted(shuffled) == sorted(_SERIES)
    result = _assess([
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(shuffled)),
    ])
    pair = result.correlation.pairs[0]
    assert abs(pair.pearson) <= PortfolioQCService.CONFLICT_PEARSON_MAX
    assert pair.style is not None
    assert pair.style.exit_distance == pytest.approx(0.0, abs=0.02)
    assert pair.style.style_vs_pnl_conflict is True
    assert result.style_vs_pnl_conflict is True
    assert result.style_verdict is StyleVerdict.SAME_PLAYBOOK
    assert "timing, not design" in result.style_verdict_reason
    assert "The offsetting PnL is not diversification" in (
        result.recommended_action
    )


def test_genuinely_different_exits_are_called_distinct() -> None:
    disciplined = make_trades([0.4, 1.0, 1.8, 0.6, 2.4, 1.2] * 10)
    bagholder = make_trades(
        [0.4, 1.0, 1.8, 0.6, 2.4, -9.0] * 10, hold_minutes=20_000.0
    )
    result = _assess([
        make_bot("AAA", disciplined),
        make_bot("BBB", bagholder),
    ])
    pair = result.correlation.pairs[0]
    assert pair.style is not None
    assert pair.style.exit_distance > PortfolioQCService.SAME_PLAYBOOK_DISTANCE
    assert pair.style.style_vs_pnl_conflict is False


def test_style_is_absent_not_guessed_when_a_ledger_is_too_thin() -> None:
    result = _assess([
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(_SERIES)),
        make_bot("CCC", make_trades([1.0, 2.0])),
    ])
    thin_pairs = [
        pair for pair in result.correlation.pairs if "CCC" in (pair.code_a, pair.code_b)
    ]
    assert thin_pairs == [] or all(pair.style is None for pair in thin_pairs)


# --------------------------------------------------------------------------- #
# Thành viên và tập trung vốn
# --------------------------------------------------------------------------- #


def test_an_unmeasurable_member_stays_in_the_report_with_its_reason() -> None:
    result = _assess([
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(_SERIES)),
        make_bot("CCC", make_trades([1.0, 2.0])),
    ])
    assert len(result.members) == 3
    assert result.measurable_member_count == 2
    excluded = [m for m in result.members if m.excluded_reason]
    assert [m.unique_code for m in excluded] == ["CCC"]


def test_concentration_sees_through_a_multi_bot_split() -> None:
    result = _assess([
        make_bot(c, make_trades(_SERIES), symbol="BTC", current_notional=5_000.0,
                 side=PositionSide.LONG)
        for c in ("AAA", "BBB", "CCC")
    ])
    assert result.concentration.largest_symbol == "BTC"
    assert result.concentration.largest_symbol_share_pct == pytest.approx(100.0)
    assert result.concentration.directional_alignment == pytest.approx(1.0)


def test_the_same_bot_twice_is_rejected() -> None:
    bot = make_bot("AAA", make_trades(_SERIES))
    with pytest.raises(ValueError, match="more than once"):
        _assess([bot, bot])


# --------------------------------------------------------------------------- #
# Lưu trữ
# --------------------------------------------------------------------------- #


def test_store_round_trips_and_deduplicates(tmp_path) -> None:
    store = PortfolioHistoryStore(root=tmp_path)
    result = _assess([make_bot(c, make_trades(_SERIES)) for c in ("AAA", "BBB")])
    assert store.append(result) is True
    assert store.append(result) is False
    history = store.history(result.portfolio_id)
    assert len(history) == 1
    assert history[0].correlation.average_pearson == pytest.approx(1.0)
    assert [e.portfolio_id for e in store.list_latest()] == [result.portfolio_id]


def test_missing_store_directory_lists_empty(tmp_path) -> None:
    assert PortfolioHistoryStore(root=tmp_path / "nope").list_latest() == []


# --------------------------------------------------------------------------- #
# Pipeline, trên fixture thật
# --------------------------------------------------------------------------- #


def _pipeline() -> PortfolioSupervisionPipeline:
    return PortfolioSupervisionPipeline(persist_history=False, max_workers=3)


def _run(members=_MEMBERS):
    return _pipeline().run(
        members,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=300,
        simulation_horizon=100,
        portfolio_iterations=500,
    )


def test_three_bots_produce_one_report_shaped_like_a_single_bot_report() -> None:
    """Điều kiện nghiệm thu chính: ra ĐÚNG MỘT báo cáo, đủ mọi mục."""
    result = _run()
    assert result.failures == []
    assert result.unavailable_reason is None

    combined = result.combined
    assert combined is not None
    # Cùng kiểu dữ liệu mà đường đơn lẻ trả về, nên renderer 3 tab dùng lại
    # được nguyên vẹn.
    assert combined.risk_assessment.risk_score is not None
    assert combined.risk_assessment.quality_score is not None
    assert combined.risk_assessment.verdict
    assert combined.risk_assessment.recommended_action
    assert combined.control_decision is not None

    # Cả mười chiều đều được chấm, không phải một tập rút gọn.
    dimensions = combined.risk_assessment.dimensions
    assert len(type(dimensions).model_fields) == 10
    assert combined.risk_assessment.score_breakdown.contributions

    # Tab "Lệnh & vị thế" và tab "Thị trường" có dữ liệu để dựng.
    bot = combined.bot_result
    assert len(bot.trade_ledger_summary) == sum(
        1 for _ in bot.trade_ledger_summary
    ) > 800
    assert bot.simulation_results.is_valid
    assert bot.exit_rule is not None and bot.exit_rule.is_valid
    assert bot.strategy_observations.phase_breakdown
    assert combined.market_available is True


def test_the_report_is_the_merged_book_not_one_member() -> None:
    result = _run()
    combined = result.combined.bot_result
    members, _ = _pipeline().fetch_members(_MEMBERS, as_of_ms=FIXED_AS_OF_MS)
    assert combined.performance.trade_count == sum(
        m.performance.trade_count for m in members
    )
    assert combined.capital.capital_at_risk == pytest.approx(
        sum(m.capital.capital_at_risk for m in members)
    )
    assert combined.identity.unique_code == PortfolioAggregator.portfolio_id(
        [m.identity.unique_code for m in members]
    )


def test_the_diversification_section_is_attached_and_scoreless() -> None:
    result = _run()
    portfolio = result.portfolio
    assert portfolio is not None
    assert portfolio.measurable_member_count == 3
    assert portfolio.correlation.is_valid
    assert len(portfolio.correlation.pairs) == 3
    assert portfolio.correlation.alignment.overlap_days > 60
    assert portfolio.joint_simulation is not None
    assert portfolio.joint_simulation.is_valid
    # Điểm rủi ro chỉ có một, và nó là của bản đánh giá gộp.
    assert portfolio.combined_assessment_id == result.combined.risk_assessment.assessment_id
    assert portfolio.combined_risk_score == result.combined.risk_assessment.risk_score
    assert portfolio.style_verdict is not StyleVerdict.INSUFFICIENT_EVIDENCE


def test_an_unreadable_member_is_reported_not_swallowed() -> None:
    result = _run(
        (*_MEMBERS[:2], PortfolioBotRequest(asset="BTC", bot_folder_name="bot_NOPE"))
    )
    assert [f.bot_folder_name for f in result.failures] == ["bot_NOPE"]
    assert result.combined is not None
    assert any("bot_NOPE" in w for w in result.portfolio.warnings)


def test_a_single_bot_is_not_a_portfolio() -> None:
    with pytest.raises(ValueError, match="at least two"):
        _pipeline().run(_MEMBERS[:1])


def test_member_notes_are_counted_not_pasted_into_the_merged_book() -> None:
    """`data_quality.warnings` của bot gộp trở thành BODY COPY trên trang.

    `RiskFusionEngine.fuse` chép thẳng nó vào `BotRiskAssessment.limitations`,
    và trang nối lại thành một câu "Data limitation: ...". Nối nguyên văn ghi
    chú của từng thành viên vào đó biến dòng ấy thành 2.390 ký tự văn xuôi
    cho một danh mục HAI bot -- và nó tăng tuyến tính theo số thành viên.
    Mỗi thành viên phải gọn trong một dòng có số đếm.
    """
    noisy = make_bot("AAA", make_trades(_SERIES))
    noisy.data_quality.warnings = [f"ghi chu rat dai so {i} " * 6 for i in range(9)]
    quiet = make_bot("BBB", make_trades(_SERIES))
    quiet.data_quality.warnings = ["mot ghi chu"]

    combined = PortfolioAggregator.combine([noisy, quiet], simulation_iterations=50)
    warnings = combined.data_quality.warnings

    # Không một ghi chú gốc nào được chép nguyên văn vào đây.
    for original in noisy.data_quality.warnings:
        assert original not in " ".join(warnings)
    # Nhưng phải nói rõ là có bao nhiêu, của ai.
    assert any("9 data notes" in line for line in warnings)
    assert any("1 data note" in line and "notes" not in line for line in warnings)
    # Và tổng độ dài phải ở mức một dòng, không phải một đoạn.
    assert sum(len(line) for line in warnings) < 500


def test_the_full_member_notes_are_still_available_on_the_portfolio() -> None:
    """Gọn KHÔNG được phép nghĩa là mất: chi tiết chuyển sang chỗ người đọc
    mở có chủ đích, không nằm trong thân trang."""
    noisy = make_bot("AAA", make_trades(_SERIES))
    noisy.data_quality.warnings = ["chi tiet quan trong ve so lenh bi loai"]
    quiet = make_bot("BBB", make_trades(_SERIES))

    result = PortfolioQCService.assess_portfolio(
        [PortfolioCandidate(bot=noisy), PortfolioCandidate(bot=quiet)],
        iterations=200,
    )
    joined = " ".join(result.limitations)
    assert "chi tiet quan trong ve so lenh bi loai" in joined
    assert "[Bot AAA]" in joined


# --------------------------------------------------------------------------- #
# Phân loại thành viên hỏng: GIẤU SỔ LỆNH vs ĐỌC HỎNG
#
# `fetch_members` là nơi DUY NHẤT còn giữ KIỂU của ngoại lệ; xuống dưới chỉ còn
# chuỗi, mà chuỗi thì không hỏi được là "bot này giấu sổ" hay "mạng rớt". Đây
# đúng là ranh giới mà đường single đã phân biệt: sổ lệnh bị giấu làm rủi ro
# TĂNG (Agent/backend/bot/analysis/limited.py), còn đọc hỏng thì không nói gì
# về bot cả.
# --------------------------------------------------------------------------- #


class _Boom:
    """Bot service chỉ biết ném -- không chạm đĩa, không chạm mạng."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    def get_bot_result(self, *args, **kwargs):
        raise self._error


class _BoomPipeline:
    """Đủ để `PortfolioSupervisionPipeline.bot_service` đọc được.

    `bot_service` là property chỉ đọc, đọc xuyên qua pipeline đơn bên trong,
    nên chỗ tiêm đúng là pipeline đó chứ không phải gán đè thuộc tính.
    """

    persist_history = False
    history = None

    def __init__(self, error: Exception) -> None:
        self.bot_service = _Boom(error)


def _fetch_one_failing(error: Exception):
    from Agent.backend.pipeline_portfolio import PortfolioBotRequest

    pipeline = PortfolioSupervisionPipeline(
        pipeline=_BoomPipeline(error), persist_history=False, max_workers=1
    )
    members, failures = pipeline.fetch_members(
        (PortfolioBotRequest(asset="BTC", bot_folder_name="bot_ZZZ"),),
        as_of_ms=FIXED_AS_OF_MS,
    )
    assert members == []
    assert len(failures) == 1
    return failures[0]


def test_a_bot_that_hides_its_ledger_is_marked_concealed() -> None:
    from Agent.backend.external.sources.bot_source import (
        STATUS_LIMITED,
        LedgerUnavailableError,
    )

    failure = _fetch_one_failing(
        LedgerUnavailableError(status=STATUS_LIMITED, code="ZZZ", reason="hidden")
    )
    assert failure.kind == "concealed"


def test_an_ordinary_failure_is_not_marked_concealed() -> None:
    assert _fetch_one_failing(RuntimeError("OKX unreachable")).kind == "error"


def test_kind_defaults_to_error_so_an_unclassified_failure_never_accuses_a_bot() -> None:
    """Mặc định phải là phía AN TOÀN CHO BOT.

    Ghi nhầm "giấu sổ lệnh" cho một bot chỉ vì lượt chạy gặp sự cố là bịa ra
    một phát hiện về bot đó, nên giá trị mặc định là `error`.
    """
    from Agent.backend.pipeline_portfolio import PortfolioMemberFailure

    assert (
        PortfolioMemberFailure(asset="BTC", bot_folder_name="bot_A", error="x").kind
        == "error"
    )


# --------------------------------------------------------------------------- #
# Kiểm chứng THẬT của M4 (sếp, 2026-09-23): "6 bot có symbol chồng nhau chạy
# không treo." Không phải test đơn vị mô phỏng -- đây là `fetch_members`
# THẬT, đọc dữ liệu THẬT trên đĩa, qua đúng `ThreadPoolExecutor` mà
# `PortfolioSupervisionPipeline` dùng trong sản xuất, với 6 bot cố ý chọn để
# CHỒNG symbol (3 ETH, 2 BTC, 1 WBTC) -- đúng điều kiện AB-BA nêu trong phát
# hiện gốc. Bọc timeout thủ công vì suite không có pytest-timeout: nếu khoá
# lấy sai thứ tự, test này TREO CÓ KIỂM SOÁT (fail rõ ràng) thay vì treo cả
# suite mãi mãi.
# --------------------------------------------------------------------------- #


def test_six_overlapping_symbol_bots_fetch_concurrently_without_hanging() -> None:
    import concurrent.futures

    from Agent.backend.bot.mcp.service import BotObservationService
    from Agent.backend.infra.config import config as _config
    from Agent.backend.infra.quality import EvaluationMode
    from Agent.backend.market.service import MarketService
    from Agent.backend.pipeline import RiskSupervisionPipeline
    from pathlib import Path

    data_dir = Path(_config.DATA_DIR)
    # 3 ETH + 2 BTC + 1 WBTC -- symbol thật sự lặp lại giữa các bot, đúng
    # điều kiện gây khoá chéo nếu thứ tự lấy lock không cố định.
    names = [
        ("BTC", "bot_35F888C7BB441B2B"),
        ("ETH", "bot_6F262ADB3B44266C"),
        ("WBTC", "bot_58D7D205FB591484"),
        ("ETH", "bot_9A073DDF49603886"),
        ("ETH", "bot_0EAF7292CE2FAAC2"),
        ("BTC", "bot_819848249304757406"),
    ]
    for _, folder in names:
        if not (data_dir / "trade" / folder).exists():
            pytest.skip(f"fixture {folder} không có trên đĩa")

    # MỘT service, chia sẻ giữa tất cả các luồng -- đúng cách
    # `PortfolioSupervisionPipeline` dùng trong sản xuất, và điều kiện DUY
    # NHẤT khiến `_timeline_locks` của các luồng thật sự đụng nhau (mỗi
    # luồng một service riêng sẽ không bao giờ tranh chấp khoá).
    svc = BotObservationService(data_dir, EvaluationMode.SNAPSHOT)
    inner = RiskSupervisionPipeline(
        data_dir=data_dir,
        bot_service=svc,
        market_service=MarketService(data_dir, EvaluationMode.SNAPSHOT),
        persist_history=False,
    )
    pipe = PortfolioSupervisionPipeline(
        data_dir=data_dir, pipeline=inner, persist_history=False, max_workers=6
    )
    reqs = tuple(
        PortfolioBotRequest(asset=asset, bot_folder_name=folder)
        for asset, folder in names
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as runner:
        future = runner.submit(pipe.fetch_members, reqs, as_of_ms=FIXED_AS_OF_MS)
        try:
            members, failures = future.result(timeout=90)
        except concurrent.futures.TimeoutError:
            pytest.fail(
                "fetch_members treo quá 90s trên 6 bot symbol chồng nhau -- "
                "đúng dấu hiệu khoá chéo AB-BA mà M4 phải chặn"
            )
    assert len(members) + len(failures) == len(names)
