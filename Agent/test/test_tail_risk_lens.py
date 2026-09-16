"""TailRiskLens: score the loss-streak *excess*, not the raw sample-size artifact.

See Agent/test/test_loss_streak_baseline.py for the math this lens now reads
(`p_5_loss_streak_excess` / `p_10_loss_streak_excess` on `SimulationResults`).
This file only checks the lens's wiring: which threshold it applies, on which
field, and the legacy fallback for assessments stored before the baseline
fields existed.
"""

from __future__ import annotations

from Agent.backend.mcp.schemas.bot_result import BotResult, SimulationResults
from Agent.backend.qc.evaluator.lenses.tail_risk import TailRiskLens
from Agent.backend.qc.schemas.risk_assessment import EvidenceStatus


def _sim(**overrides) -> SimulationResults:
    fields = dict(
        simulation_method="STATIONARY_BOOTSTRAP",
        iterations=10_000,
        sample_size=100,
        horizon_trades=500,
        return_basis="ABSOLUTE_PNL_RELATIVE_TO_EQUITY",
        capital_basis="CURRENT_AUM",
        is_valid=True,
        p_mdd_gt_15=1.0,
    )
    fields.update(overrides)
    return SimulationResults(**fields)


def _bot(sim: SimulationResults, stress_results=None) -> BotResult:
    return BotResult.model_construct(
        simulation_results=sim, stress_results=stress_results
    )


def _evaluate(sim: SimulationResults):
    return TailRiskLens.evaluate(_bot(sim))


def test_legacy_data_without_a_baseline_falls_back_to_the_old_raw_threshold():
    """An assessment produced before this field existed (or any caller that
    never ran the updated engine) has baseline=None. The +15 penalty must
    still apply at the exact old raw threshold (>40) rather than silently
    disappearing -- that would be a quiet loosening of the veto for old data.
    """
    penalized = _evaluate(_sim(p_5_loss_streak=65.0, p_5_loss_streak_baseline=None))
    not_penalized = _evaluate(_sim(p_5_loss_streak=35.0, p_5_loss_streak_baseline=None))

    assert penalized.score == 30.0  # 15 base + 15
    assert not_penalized.score == 15.0  # base only, 35 <= 40


def test_legacy_data_without_a_baseline_falls_back_for_the_ten_streak_too():
    penalized = _evaluate(_sim(p_10_loss_streak=15.0, p_10_loss_streak_baseline=None))
    not_penalized = _evaluate(
        _sim(p_10_loss_streak=8.0, p_10_loss_streak_baseline=None)
    )

    assert penalized.score == 35.0  # 15 base + 20
    assert not_penalized.score == 15.0


def test_a_high_win_rate_bot_with_small_excess_is_not_penalized():
    """This is the case a raw-number threshold gets wrong: a bot that has
    simply traded a lot shows a high raw p_5_loss_streak, but almost all of
    it is explained by the baseline for its own win rate -- the excess is
    small, so it must not eat the +15 penalty.
    """
    result = _evaluate(
        _sim(
            p_5_loss_streak=65.01,
            p_5_loss_streak_baseline=63.0,
            p_5_loss_streak_excess=2.01,
        )
    )
    assert result.score == 15.0
    assert not any("phần vượt thật" in f for f in result.key_findings)


def test_a_bot_with_real_excess_streak_risk_is_still_penalized():
    """Required negative control: when the excess over baseline is large --
    meaning the raw streak probability is not explained by sample size alone
    -- the penalty must still fire.
    """
    result = _evaluate(
        _sim(
            p_5_loss_streak=65.0,
            p_5_loss_streak_baseline=5.0,
            p_5_loss_streak_excess=60.0,
        )
    )
    assert result.score == 30.0
    finding = next(f for f in result.key_findings if "phần vượt thật" in f)
    assert "65.0" in finding and "5.0" in finding and "60.0" in finding


def test_the_ten_streak_excess_threshold_uses_ten_not_fifteen():
    just_under = _evaluate(
        _sim(
            p_10_loss_streak=50.0,
            p_10_loss_streak_baseline=41.0,
            p_10_loss_streak_excess=9.0,
        )
    )
    just_over = _evaluate(
        _sim(
            p_10_loss_streak=50.0,
            p_10_loss_streak_baseline=39.0,
            p_10_loss_streak_excess=11.0,
        )
    )
    assert just_under.score == 15.0
    assert just_over.score == 35.0  # 15 base + 20


def test_other_tail_risk_criteria_are_unchanged_by_the_horizon_fix():
    """p_ruin and the drawdown criteria do not depend on horizon length the
    way streak probabilities do, and must not have moved."""
    result = _evaluate(_sim(p_ruin=25.0))
    assert result.score == 15.0 + 55  # p_ruin >= 20 branch, unchanged


def test_findings_report_the_horizon_in_calendar_days_when_available():
    result = _evaluate(
        _sim(trades_per_day=50.0, horizon_calendar_days=10.0, horizon_trades=500)
    )
    assert any("ngày lịch" in f for f in result.key_findings)


def test_findings_warn_when_the_horizon_extrapolates_past_observed_data():
    result = _evaluate(
        _sim(
            horizon_exceeds_observed=True,
            observed_span_days=30.0,
            horizon_calendar_days=90.0,
        )
    )
    assert any("ngoại suy" in f for f in result.key_findings)


def test_findings_say_nothing_about_horizon_when_not_computable():
    result = _evaluate(_sim())
    assert not any("ngày lịch" in f for f in result.key_findings)
    assert not any("ngoại suy" in f for f in result.key_findings)


def test_evaluate_still_reports_unknown_when_simulation_is_unavailable():
    result = TailRiskLens.evaluate(
        _bot(_sim(is_valid=False, p_mdd_gt_15=None, warnings=["not enough trades"]))
    )
    assert result.status == EvidenceStatus.UNKNOWN
