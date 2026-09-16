"""Risk says how much it can hurt; quality says whether it is any good."""

from __future__ import annotations

from types import SimpleNamespace

from Agent.backend.qc.reporting.cohort import BotEvaluationRow

import pytest

from Agent.backend.qc.scoring.quality import assess as assess_quality
from Agent.backend.qc.scoring.verdict import (
    VERDICT_DANGEROUS,
    VERDICT_LATENT,
    VERDICT_PROMISING,
    VERDICT_SAFE,
    decide,
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
    assert any("không chấm được" in note for note in capped.notes)


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


def test_a_high_risk_bot_is_dangerous_whatever_its_quality():
    verdict = decide(_bot(), risk_score=85.0, quality_score=95.0)

    assert verdict.verdict == VERDICT_DANGEROUS


def test_good_surface_numbers_hiding_an_open_loss_land_in_latent():
    """This is the case a plain risk ladder puts two rungs too low."""
    bot = _bot(booked_pf=11.0, marked_pf=0.16, open_loss_pct=65.0)

    verdict = decide(bot, risk_score=30.0, quality_score=80.0)

    assert verdict.verdict == VERDICT_LATENT
    assert any("PF rơi" in flag for flag in verdict.hidden_flags)


def test_profit_from_a_single_regime_is_latent_not_safe():
    bot = _bot(dependence=95.0)

    assert decide(bot, 25.0, 85.0).verdict == VERDICT_LATENT


def test_never_having_traded_a_downtrend_is_latent():
    bot = _bot(tested_down=False)

    assert decide(bot, 20.0, 85.0).verdict == VERDICT_LATENT


def test_low_risk_and_strong_quality_is_promising():
    verdict = decide(_bot(), risk_score=25.0, quality_score=80.0)

    assert verdict.verdict == VERDICT_PROMISING


def test_low_risk_but_weak_quality_is_safe_not_promising():
    verdict = decide(_bot(), risk_score=20.0, quality_score=30.0)

    assert verdict.verdict == VERDICT_SAFE
    assert "gần như không kiếm được gì" in verdict.reason


def test_the_four_buckets_are_the_only_outcomes():
    seen = {
        decide(_bot(), risk, quality).verdict
        for risk in (10.0, 40.0, 60.0, 90.0)
        for quality in (20.0, 50.0, 90.0)
    }

    assert seen <= {VERDICT_SAFE, VERDICT_PROMISING, VERDICT_LATENT, VERDICT_DANGEROUS}


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
    from Agent.backend.qc.reporting.reasons import recommendation_vi

    text = " ".join(recommendation_vi(_row()))

    assert "86,132" in text and "0.16" in text
    # Wording was condensed for length; the mechanism it names must survive.
    assert "chốt lời sớm" in text


def test_the_recommendation_describes_how_the_bot_trades():
    from Agent.backend.qc.reporting.reasons import recommendation_vi

    text = " ".join(recommendation_vi(_row()))

    assert "Chiến lược:" in text
    assert "cả hai chiều" in text
    assert "Tăng, động" in text


def test_an_untested_downtrend_is_stated_plainly():
    from Agent.backend.qc.reporting.reasons import recommendation_vi

    text = " ".join(recommendation_vi(_row(tested_in_downtrend=False)))

    assert "Chưa từng bị thử ở chiều xuống" in text


def test_every_verdict_ends_with_a_condition_that_would_change_it():
    """A verdict with no exit condition reads as permanent."""
    from Agent.backend.qc.reporting.reasons import recommendation_vi

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

    assert "Điều kiện xem xét lại" in deferred
    assert "pha thị trường giảm" in untested
    assert "370" in thin


def test_a_dangerous_verdict_names_the_driver_not_the_threshold():
    from Agent.backend.qc.scoring.verdict import decide

    with_driver = decide(
        _bot(), 88.0, 40.0, risk_drivers=["hành vi giao dịch hủy hoại"]
    )

    assert "hành vi giao dịch hủy hoại" in with_driver.reason
    assert "ngưỡng" not in with_driver.reason
