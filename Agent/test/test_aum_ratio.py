"""Việc 4 -- `Agent/backend/web/data.py`'s `_narrative_numbers` used to
divide `reported_aum / capital_at_risk` unconditionally, silently assuming
the self-reported AUM was always the bigger of the two figures. For a real
bot where the ledger-derived reference capital is the BIGGER one (AUM 8,998
vs reference capital 1,436,724 -- the reported bug), that produced ~0.0063,
which rounds to "0.0x" and collapses to the bare digit "0" once
`narrative.make_number`'s own text cleanup strips trailing zeros -- a
narrative then dutifully repeated "bội số 0x", a meaningless claim.

Fixed to always divide the BIGGER figure by the SMALLER one (a ratio that
can never round to 0) and to give each direction its own, unambiguous
label naming which figure is the multiple of which.

These tests build a minimal duck-typed fake of the `RiskSupervisionResult`
shape `_narrative_numbers` reads (`result.risk_assessment`/
`result.bot_result`) via `types.SimpleNamespace` -- the function only ever
reads plain attributes off these objects (no method calls, no isinstance
checks beyond `narrative.make_number`'s own `None`/non-finite guards), so a
duck-typed stand-in exercises the exact same code path a real
`BotRiskAssessment`/`BotResult` pair would, without needing to satisfy
every unrelated required field those real pydantic models carry.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

from Agent.backend.web.data import _narrative_numbers


def _fake_result(
    *, capital_at_risk: Optional[float], reported_aum: Optional[float]
) -> SimpleNamespace:
    performance = SimpleNamespace(
        trade_count=None,
        win_rate=None,
        loss_rate=None,
        profit_factor=None,
        max_drawdown_pct=None,
        sharpe_ratio=None,
        payoff_ratio=None,
        max_loss_streak=None,
    )
    simulation_results = SimpleNamespace(
        p_ruin=None,
        p95_max_drawdown=None,
        p_loss_after_horizon=None,
        probability_of_profit=None,
        deflated_sharpe=None,
        selection_trials=None,
        iterations=None,
        horizon_trades=None,
        trades_per_day=None,
    )
    deferred_loss = SimpleNamespace(
        marked_profit_factor=None,
        open_loss_to_capital_pct=None,
    )
    capital = SimpleNamespace(
        capital_at_risk=capital_at_risk,
        reported_aum=reported_aum,
    )
    current_state = SimpleNamespace(gross_exposure=None, current_leverage=None)
    # Empty `phase_breakdown`/`None` percentages: `_phase_breakdown_numbers`
    # (Việc bổ sung -- per-phase cross-tab numbers) must degrade to "nothing
    # to add" rather than raise on a bot with no phase observations at all,
    # exactly like every other optional figure in this fixture.
    strategy_observations = SimpleNamespace(
        phase_breakdown=[],
        phase_coverage_pct=None,
        regime_dependence_pct=None,
    )
    bot_result = SimpleNamespace(
        performance=performance,
        simulation_results=simulation_results,
        deferred_loss=deferred_loss,
        capital=capital,
        current_state=current_state,
        strategy_observations=strategy_observations,
    )
    score_breakdown = SimpleNamespace(
        decided_by="WEIGHTED_AVERAGE", weighted_average=None, veto_floor=None
    )
    risk_assessment = SimpleNamespace(
        risk_score=None,
        quality_score=None,
        confidence=None,
        score_breakdown=score_breakdown,
    )
    return SimpleNamespace(risk_assessment=risk_assessment, bot_result=bot_result)


def _labels_and_values(result: SimpleNamespace) -> dict:
    return {spec.label: spec.value for spec in _narrative_numbers(result)}


_REF_CAPITAL_BIGGER_LABEL = "How many times the inferred reference capital is larger than the self-reported AUM"
_AUM_BIGGER_LABEL = "How many times the self-reported AUM is larger than the inferred reference capital"


def test_reference_capital_much_bigger_than_aum_reports_gap_160_lan() -> None:
    """The exact reported bug: AUM 8,998, reference capital 1,436,724 ->
    ~159.68, rounds to "gấp ~160 lần" the RIGHT way round, never "0"."""
    result = _fake_result(capital_at_risk=1_436_724.0, reported_aum=8_998.0)
    values = _labels_and_values(result)
    assert _AUM_BIGGER_LABEL not in values
    assert _REF_CAPITAL_BIGGER_LABEL in values
    ratio = values[_REF_CAPITAL_BIGGER_LABEL]
    assert ratio != 0
    assert 159.0 <= ratio <= 160.0


def test_aum_much_bigger_than_reference_capital_reports_the_other_direction() -> None:
    """The reverse case: a bot whose self-reported AUM dwarfs the
    ledger-derived reference capital -- the ORIGINAL (pre-fix) direction --
    must still be reported, just under its own explicit label."""
    result = _fake_result(capital_at_risk=1_000.0, reported_aum=50_000.0)
    values = _labels_and_values(result)
    assert _REF_CAPITAL_BIGGER_LABEL not in values
    assert _AUM_BIGGER_LABEL in values
    assert values[_AUM_BIGGER_LABEL] == 50.0


def test_ratio_never_rounds_to_zero_even_when_the_gap_is_extreme() -> None:
    result = _fake_result(capital_at_risk=10_000_000.0, reported_aum=1.0)
    values = _labels_and_values(result)
    assert values[_REF_CAPITAL_BIGGER_LABEL] != 0


def test_equal_figures_report_a_ratio_of_one_never_zero() -> None:
    result = _fake_result(capital_at_risk=5_000.0, reported_aum=5_000.0)
    values = _labels_and_values(result)
    # capital_at_risk >= reported_aum (equal case) -> the reference-capital
    # direction, ratio exactly 1.0.
    assert values[_REF_CAPITAL_BIGGER_LABEL] == 1.0


def test_aum_exactly_zero_never_produces_a_ratio_number() -> None:
    result = _fake_result(capital_at_risk=1_436_724.0, reported_aum=0.0)
    values = _labels_and_values(result)
    assert _REF_CAPITAL_BIGGER_LABEL not in values
    assert _AUM_BIGGER_LABEL not in values


def test_aum_missing_never_produces_a_ratio_number() -> None:
    result = _fake_result(capital_at_risk=1_436_724.0, reported_aum=None)
    values = _labels_and_values(result)
    assert _REF_CAPITAL_BIGGER_LABEL not in values
    assert _AUM_BIGGER_LABEL not in values


def test_reference_capital_missing_never_produces_a_ratio_number() -> None:
    result = _fake_result(capital_at_risk=None, reported_aum=8_998.0)
    values = _labels_and_values(result)
    assert _REF_CAPITAL_BIGGER_LABEL not in values
    assert _AUM_BIGGER_LABEL not in values


def test_reference_capital_zero_never_produces_a_ratio_number() -> None:
    result = _fake_result(capital_at_risk=0.0, reported_aum=8_998.0)
    values = _labels_and_values(result)
    assert _REF_CAPITAL_BIGGER_LABEL not in values
    assert _AUM_BIGGER_LABEL not in values


def test_ratio_labels_never_embed_a_stray_digit() -> None:
    """Same discipline every other `_narrative_numbers` label follows (see
    test_web_app.py's own
    test_narrative_number_labels_never_embed_a_stray_digit) -- a label must
    never carry a bare number the model could echo back as if it were a
    measured figure.
    """
    import re

    assert not re.search(r"\d", _REF_CAPITAL_BIGGER_LABEL)
    assert not re.search(r"\d", _AUM_BIGGER_LABEL)
