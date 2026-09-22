"""Risk says how much it can hurt; quality says whether it is any good."""

from __future__ import annotations

from types import SimpleNamespace

from Agent.backend.report.qc.reporting.cohort import BotEvaluationRow

import pytest

from Agent.backend.report.qc.scoring.quality import assess as assess_quality
from Agent.backend.report.qc.scoring.verdict import (
    DANGEROUS_RISK,
    PROMISING_QUALITY,
    VERDICT_HIDDEN_RISK,
    VERDICT_HIGH_DD_GOOD_Q,
    VERDICT_HIGH_DD_WEAK_Q,
    VERDICT_LOW_DD_GOOD_Q,
    VERDICT_LOW_DD_WEAK_Q,
    VERDICT_UNKNOWN,
    decide,
    label_from_scores,
)


def _bot(
    *,
    trade_count=100,
    profit_factor=2.0,
    booked_pf=2.0,
    marked_pf=2.0,
    expectancy=50.0,
    sharpe=1.0,
    max_dd=8.0,
    dd_capped=False,
    never_lost=False,
    open_loss_pct=1.0,
    coverage=90.0,
    dependence=30.0,
    losing_phases=(),
    tested_down=True,
):
    return SimpleNamespace(
        performance=SimpleNamespace(
            trade_count=trade_count,
            profit_factor=profit_factor,
            expectancy=expectancy,
            sharpe_ratio=sharpe,
        ),
        deferred_loss=SimpleNamespace(
            booked_profit_factor=booked_pf,
            marked_profit_factor=marked_pf,
            never_realized_a_loss=never_lost,
            open_loss_to_capital_pct=open_loss_pct,
        ),
        drawdown_analysis=SimpleNamespace(
            max_dd_pct=max_dd, max_dd_pct_capped=dd_capped
        ),
        strategy_observations=SimpleNamespace(
            phase_coverage_pct=coverage,
            regime_dependence_pct=dependence,
            losing_phases=list(losing_phases),
            tested_in_downtrend=tested_down,
        ),
    )


def test_a_record_that_only_holds_while_losers_stay_open_scores_badly():
    """PF 11 on the closed book and 0.16 once marked is not a good bot."""
    honest = assess_quality(_bot(profit_factor=3.0, booked_pf=3.0, marked_pf=2.9))
    curated = assess_quality(_bot(profit_factor=11.0, booked_pf=11.0, marked_pf=0.16))

    assert curated.score < honest.score
    assert curated.components["profitability"] == 0.0
    assert curated.components["honesty"] == 0.0


def test_a_capped_drawdown_is_not_read_as_shallow():
    capped = assess_quality(_bot(max_dd=100.0, dd_capped=True))

    assert "drawdown_control" not in capped.components
    assert any("cannot be scored" in note for note in capped.notes)


def test_quality_is_none_when_nothing_can_be_measured():
    bare = assess_quality(
        _bot(
            trade_count=2,
            profit_factor=None,
            booked_pf=None,
            marked_pf=None,
            expectancy=None,
            max_dd=None,
            coverage=None,
        )
    )

    assert bare.score is None


def test_a_high_risk_high_quality_bot_gets_its_own_state_not_a_single_danger_bucket():
    """The whole point of the two-axis redesign: out-of-sample validation found
    the risk score predicts drawdown, not PnL, so a high-risk bot with good
    quality must not collapse into the same label as one with weak quality.
    """
    verdict = decide(_bot(), risk_score=85.0, quality_score=95.0)

    assert verdict.verdict == VERDICT_HIGH_DD_GOOD_Q


def test_a_high_risk_low_quality_bot_is_the_worst_two_axis_state():
    verdict = decide(_bot(), risk_score=85.0, quality_score=30.0)

    assert verdict.verdict == VERDICT_HIGH_DD_WEAK_Q


def test_good_surface_numbers_hiding_an_open_loss_are_hidden_risk():
    """This is the case a plain risk ladder puts two rungs too low -- and
    hidden risk now overrides BOTH axes, not just a middle risk tier.
    """
    bot = _bot(booked_pf=11.0, marked_pf=0.16, open_loss_pct=65.0)

    verdict = decide(bot, risk_score=30.0, quality_score=80.0)

    assert verdict.verdict == VERDICT_HIDDEN_RISK
    assert any("drops the PF" in flag for flag in verdict.hidden_flags)


def test_profit_from_a_single_regime_is_hidden_risk_not_low_drawdown():
    bot = _bot(dependence=95.0)

    assert decide(bot, 25.0, 85.0).verdict == VERDICT_HIDDEN_RISK


def test_never_having_traded_a_downtrend_is_hidden_risk():
    bot = _bot(tested_down=False)

    assert decide(bot, 20.0, 85.0).verdict == VERDICT_HIDDEN_RISK


def test_hidden_risk_overrides_low_drawdown_and_good_quality_together():
    """A bot that would otherwise land in the best two-axis state (low risk
    score AND good quality) must still be flagged when the surface numbers
    are shown to be hiding something -- neither axis's number can be
    trusted once that is true.
    """
    bot = _bot(booked_pf=11.0, marked_pf=0.16, open_loss_pct=65.0)

    verdict = decide(bot, risk_score=10.0, quality_score=95.0)

    assert verdict.verdict == VERDICT_HIDDEN_RISK


def test_low_risk_and_strong_quality_is_the_best_two_axis_state():
    verdict = decide(_bot(), risk_score=25.0, quality_score=80.0)

    assert verdict.verdict == VERDICT_LOW_DD_GOOD_Q


def test_low_risk_but_weak_quality_is_the_low_drawdown_weak_quality_state():
    verdict = decide(_bot(), risk_score=20.0, quality_score=30.0)

    assert verdict.verdict == VERDICT_LOW_DD_WEAK_Q


def test_risk_score_none_is_unknown_regardless_of_quality():
    verdict = decide(_bot(), risk_score=None, quality_score=90.0)

    assert verdict.verdict == VERDICT_UNKNOWN


def test_quality_score_none_lands_on_the_weak_quality_side():
    """`quality_score is None` must read as YẾU (with a note in the reason),
    never silently promoted to TỐT for lack of a number."""
    verdict = decide(_bot(), risk_score=20.0, quality_score=None)

    assert verdict.verdict == VERDICT_LOW_DD_WEAK_Q
    assert "quality could not be scored" in verdict.reason


def test_the_six_states_are_the_only_outcomes():
    seen = {
        decide(_bot(), risk, quality).verdict
        for risk in (10.0, 40.0, 60.0, 90.0)
        for quality in (20.0, 50.0, 90.0)
    }

    assert seen <= {
        VERDICT_LOW_DD_WEAK_Q,
        VERDICT_LOW_DD_GOOD_Q,
        VERDICT_HIGH_DD_WEAK_Q,
        VERDICT_HIGH_DD_GOOD_Q,
    }


# --------------------------------------------------------------------------- #
# Threshold boundaries -- DANGEROUS_RISK (70.0) and PROMISING_QUALITY (65.0)
# are reused verbatim from the pre-existing single-ladder thresholds (task's
# own explicit "dùng lại đúng các hằng số ngưỡng đã có, không phát minh số
# mới"); these tests pin exactly which side of each boundary lands where.
# --------------------------------------------------------------------------- #


def test_risk_score_exactly_at_the_dangerous_threshold_is_high_drawdown():
    assert DANGEROUS_RISK == 70.0
    verdict = decide(_bot(), risk_score=70.0, quality_score=90.0)
    assert verdict.verdict == VERDICT_HIGH_DD_GOOD_Q


def test_risk_score_just_under_the_dangerous_threshold_is_low_drawdown():
    verdict = decide(_bot(), risk_score=69.999, quality_score=90.0)
    assert verdict.verdict == VERDICT_LOW_DD_GOOD_Q


def test_quality_score_exactly_at_the_promising_threshold_is_good_quality():
    assert PROMISING_QUALITY == 65.0
    verdict = decide(_bot(), risk_score=10.0, quality_score=65.0)
    assert verdict.verdict == VERDICT_LOW_DD_GOOD_Q


def test_quality_score_just_under_the_promising_threshold_is_weak_quality():
    verdict = decide(_bot(), risk_score=10.0, quality_score=64.999)
    assert verdict.verdict == VERDICT_LOW_DD_WEAK_Q


# --------------------------------------------------------------------------- #
# label_from_scores -- the pure function backward-compatibility relies on
# (Agent/backend/web/admin_page.py, agent_server.py) to recompute a label
# from an OLD assessment.json's stored scores, without needing a BotResult.
# --------------------------------------------------------------------------- #


def test_label_from_scores_matches_decide_on_the_boundary():
    for risk in (0.0, 69.9, 70.0, 100.0):
        for quality in (0.0, 64.9, 65.0, 100.0):
            verdict = decide(_bot(), risk, quality)
            assert label_from_scores(risk, quality, []) == verdict.verdict


def test_label_from_scores_is_unknown_for_no_risk_score():
    assert label_from_scores(None, 90.0, []) == VERDICT_UNKNOWN
    assert label_from_scores(None, None, []) == VERDICT_UNKNOWN


def test_label_from_scores_hidden_flags_override_both_axes():
    assert (
        label_from_scores(10.0, 95.0, ["lỗ chưa chốt bằng 65% vốn"])
        == VERDICT_HIDDEN_RISK
    )


def test_quality_weights_every_measured_component():
    strong = assess_quality(_bot(profit_factor=4.0, booked_pf=4.0, marked_pf=4.0))
    weak = assess_quality(
        _bot(
            profit_factor=1.05,
            booked_pf=1.05,
            marked_pf=1.05,
            expectancy=-5.0,
            max_dd=55.0,
            losing_phases=("A", "B", "C"),
        )
    )

    assert strong.score > weak.score
    assert set(strong.measured_on) == set(strong.components)
    assert strong.score == pytest.approx(strong.score)


def _row(**kwargs):
    base = dict(
        rank=1,
        status="OK",
        bot_id="bot_TEST",
        unique_code="TEST",
        asset_context="XRP",
        snapshot_venue="OKX",
        bot_folder="bot_TEST",
        conclusion="NGUY HIỂM",
        nick_name="Bot",
        traded_symbol="XRP",
        venue_type="CEX",
        trade_count=143,
        win_rate=92.0,
        total_pnl=9583.0,
        profit_factor=11.12,
        marked_profit_factor=0.16,
        open_loss=86132.0,
        open_positions=95,
        capital_at_risk=131958.0,
        directional_bias="TWO_WAY",
        entry_style="MEAN_REVERSION",
        phase_coverage_pct=83.0,
        regime_dependence_pct=39.0,
        best_phase="UPTREND_VOLATILE",
        losing_phases=[],
        untested_phases=[],
        tested_in_downtrend=True,
        mc_iterations=10_000,
        mc_horizon=143,
        profit_pct_p50=7.3,
        profit_pct_worst=3.9,
        p_loss_after_horizon=0.0,
        p_ruin=0.0,
        p95_max_drawdown=0.0,
        worst_drawdown=1.0,
        psr=1.0,
        deflated_sharpe=0.998,
        selection_trials=9,
        inference_reliable=False,
        min_track_record_trades=20.0,
        hidden_risk_flags=["lỗ chưa chốt bằng 65% vốn"],
        verdict="NGUY HIỂM",
        quality_score=54.5,
        risk_score=70.0,
        recommended_action="REDUCE",
        confidence=80.0,
    )
    base.update(kwargs)
    # The real model, not a stub: a namespace silently lacks whatever field the
    # narrative starts reading next, and the test then fails for the wrong reason.
    return BotEvaluationRow(**base)


def test_the_recommendation_names_the_gap_between_closed_and_open_books():
    from Agent.backend.report.qc.reporting.reasons import recommendation_vi

    text = " ".join(recommendation_vi(_row()))

    assert "86,132" in text and "0.16" in text
    # Wording was condensed for length; the mechanism it names must survive.
    # Cơ chế phải được NÊU TÊN, không chỉ nêu số. Câu chữ đổi khi cắt gọn
    # cho vừa ngân sách 1200 ký tự; yêu cầu thì không đổi.
    assert "wins taken early" in text


def test_the_recommendation_describes_how_the_bot_trades():
    from Agent.backend.report.qc.reporting.reasons import recommendation_vi

    text = " ".join(recommendation_vi(_row()))

    assert "Strategy:" in text
    assert "both directions" in text
    assert "Uptrend, volatile" in text


def test_an_untested_downtrend_is_stated_plainly():
    from Agent.backend.report.qc.reporting.reasons import recommendation_vi

    text = " ".join(recommendation_vi(_row(tested_in_downtrend=False)))

    assert "Never tested on the way down" in text


def test_every_verdict_ends_with_a_condition_that_would_change_it():
    """A verdict with no exit condition reads as permanent."""
    from Agent.backend.report.qc.reporting.reasons import recommendation_vi

    deferred = " ".join(recommendation_vi(_row()))
    untested = " ".join(
        recommendation_vi(
            _row(
                marked_profit_factor=2.0,
                hidden_risk_flags=[],
                tested_in_downtrend=False,
            )
        )
    )
    thin = " ".join(
        recommendation_vi(
            _row(
                marked_profit_factor=2.0,
                hidden_risk_flags=[],
                trade_count=30,
                min_track_record_trades=400.0,
            )
        )
    )

    assert "Revisit when" in deferred
    assert "downtrend phase" in untested
    assert "370" in thin


def test_a_dangerous_verdict_names_the_driver_not_the_threshold():
    from Agent.backend.report.qc.scoring.verdict import decide

    with_driver = decide(
        _bot(), 88.0, 40.0, risk_drivers=["hành vi giao dịch hủy hoại"]
    )

    assert "hành vi giao dịch hủy hoại" in with_driver.reason
    assert "ngưỡng" not in with_driver.reason
