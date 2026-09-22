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
    assert any("Synthetic portfolio" in w for w in combined.data_quality.warnings)
    assert any("merged ledger" in w for w in combined.data_quality.warnings)


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


def test_one_extreme_pair_is_not_hidden_by_a_comfortable_average() -> None:
    import numpy as np

    rng = np.random.default_rng(5)
    result = _assess([
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(_SERIES)),
        make_bot("CCC", make_trades(list(rng.normal(0, 3, 60)))),
    ])
    assert result.correlation.average_pearson < PortfolioQCService.HIGH_AVG_PEARSON
    assert result.correlation.max_pearson == pytest.approx(1.0)
    assert result.verdict is PortfolioVerdict.HIGH_CORRELATION_CLUSTER
    assert "held twice" in result.verdict_reason


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
    assert "Do not treat the offsetting PnL as diversification" in (
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
