"""Việc 4 -- narrative generated in the persisted-assessment write path,
not just the live `/api/analyze` one.

`Agent/backend/run_report.py`'s `build_assessment_extras` re-fetches each
scored row's own `BotResult` (read-only, never a second scoring pass -- see
that function's own module-level comment for why) to fill in the strategy/
behavioural fields `BotEvaluationRow` cannot carry, and -- unless
`--no-narrative` was passed -- generates a narrative from THIS row's own
already-scored numbers.

Every test here fakes `narrative.generate_narrative_sync` (never spawns the
real `claude` CLI, same discipline `test_narrative.py` itself follows) so
these tests are fast, deterministic, and spend no real Claude usage.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from types import SimpleNamespace

import pytest

import Agent.backend.run_report as run_report
from Agent.backend.mcp.schemas.bot_result import (
    BehavioralObservations,
    HorizonOutcome,
    PhasePerformance,
    StrategyObservations,
)
from Agent.backend.qc.reporting.assessment_store import build_assessments
from Agent.backend.qc.reporting.cohort import BotEvaluationRow


def _row(**overrides: Any) -> BotEvaluationRow:
    base: Dict[str, Any] = dict(
        rank=1,
        status="EVALUATED",
        bot_id="bot_TESTCODE1",
        unique_code="TESTCODE1",
        nick_name="Test Bot",
        traded_symbol="ETH",
        asset_context="ETH",
        venue_type="CEX",
        snapshot_venue="CEX",
        bot_folder="bot_TESTCODE1",
        trade_count=50,
        win_rate=70.0,
        profit_factor=2.5,
        max_drawdown_pct=8.0,
        sharpe_ratio=1.8,
        payoff_ratio=1.4,
        max_loss_streak=3,
        risk_score=42.0,
        quality_score=65.0,
        confidence=60.0,
        verdict="SỤT VỐN: TRUNG BÌNH · CHẤT LƯỢNG: KHÁ",
        directional_bias="TWO_WAY",
        entry_style="MEAN_REVERSION",
        phase_coverage_pct=55.0,
        score_decided_by="WEIGHTED_AVERAGE",
        conclusion="OK",
    )
    base.update(overrides)
    return BotEvaluationRow(**base)


def _cohort(*rows: BotEvaluationRow, generated_at_ms: int = 1_800_000_000_000):
    return SimpleNamespace(generated_at_ms=generated_at_ms, rows=list(rows))


def _fake_bot_result(**overrides: Any):
    strategy = StrategyObservations(
        observed_profile="DayTrading",
        directional_bias="TWO_WAY",
        long_share_pct=47.2,
        entry_style="MEAN_REVERSION",
        entry_style_evidence="7/28 lệnh mở thuận chiều biến động 24h trước đó",
        phase_coverage_pct=40.3,
        best_phase="UPTREND_VOLATILE",
        worst_phase="UPTREND_CALM",
        untested_phases=["RANGE_CALM"],
        tested_in_downtrend=False,
        tested_in_trend=True,
        phase_breakdown=[
            PhasePerformance(
                phase="UPTREND_VOLATILE",
                trades=15,
                win_rate=86.7,
                total_pnl=9857.0,
                long_share_pct=7.0,
                average_leverage=2.3,
                median_hold_minutes=939.0,
                profit_share_pct=18.7,
            )
        ],
    )
    behavioral = BehavioralObservations(
        behavioral_risk_tier="MEDIUM",
        martingale_escalation_detected=False,
        averaging_down_detected=False,
    )
    bot = SimpleNamespace(
        strategy_observations=strategy, behavioral_observations=behavioral
    )
    for key, value in overrides.items():
        setattr(bot, key, value)
    return bot


class _FakeBotService:
    """Records every `get_bot_result` call and returns a canned `BotResult`
    (or raises, to exercise the degrade-gracefully path)."""

    def __init__(self, bot: Any = None, error: Optional[Exception] = None) -> None:
        self._bot = bot
        self._error = error
        self.calls: List[Dict[str, Any]] = []

    def get_bot_result(self, asset: str, bot_folder_name: str, **kwargs: Any) -> Any:
        self.calls.append(
            {"asset": asset, "bot_folder_name": bot_folder_name, **kwargs}
        )
        if self._error is not None:
            raise self._error
        return self._bot


def _fake_generate_narrative_sync(
    monkeypatch: pytest.MonkeyPatch, text: str = "Bot này chơi kiểu day-trading."
) -> Dict[str, Any]:
    captured: Dict[str, Any] = {}

    def _fake(numbers, context, *, backend=None):  # noqa: ANN001
        captured["numbers"] = list(numbers)
        captured["context"] = context
        return text

    monkeypatch.setattr(run_report.narrative, "generate_narrative_sync", _fake)
    return captured


# --------------------------------------------------------------------------- #
# build_assessment_extras
# --------------------------------------------------------------------------- #


def test_extras_include_strategy_behavioral_and_narrative_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _fake_generate_narrative_sync(monkeypatch)
    row = _row()
    cohort = _cohort(row)
    bot_service = _FakeBotService(bot=_fake_bot_result())

    extras = run_report.build_assessment_extras(
        cohort, bot_service, generate_narrative_flag=True
    )

    assert set(extras.keys()) == {"TESTCODE1"}
    extra = extras["TESTCODE1"]
    assert extra["strategy"]["observed_profile"] == "DayTrading"
    assert extra["strategy"]["entry_style"] == "MEAN_REVERSION"
    assert extra["behavioral"]["behavioral_risk_tier"] == "MEDIUM"
    assert extra["narrative"] == "Bot này chơi kiểu day-trading."

    # The re-fetch used the SAME snapshot coordinates + as_of_ms the row was
    # scored from -- never a different bot/venue/timestamp.
    call = bot_service.calls[0]
    assert call["asset"] == row.asset_context
    assert call["bot_folder_name"] == row.bot_folder
    assert call["venue_type"] == row.snapshot_venue
    assert call["as_of_ms"] == cohort.generated_at_ms

    # And the narrative's own numbers/context are THIS row's own numbers,
    # never a recomputed/second-guessed score.
    values = {spec.value for spec in captured["numbers"]}
    assert row.risk_score in values
    assert row.quality_score in values
    assert captured["context"].verdict == row.verdict


def test_no_narrative_flag_skips_generation_entirely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _must_not_be_called(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("generate_narrative_sync must not be called")

    monkeypatch.setattr(
        run_report.narrative, "generate_narrative_sync", _must_not_be_called
    )
    row = _row()
    cohort = _cohort(row)
    bot_service = _FakeBotService(bot=_fake_bot_result())

    extras = run_report.build_assessment_extras(
        cohort, bot_service, generate_narrative_flag=False
    )

    assert extras["TESTCODE1"]["narrative"] is None
    # Strategy/behavioural evidence is still built -- only the narrative is
    # skipped, so --no-narrative is a speed-up, not a feature downgrade of
    # Việc 1's own evidence fix.
    assert extras["TESTCODE1"]["strategy"]["observed_profile"] == "DayTrading"


def test_failed_refetch_degrades_extras_to_none_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from Agent.backend.mcp.service import BotDataUnavailableError

    def _must_not_be_called(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("generate_narrative_sync must not be called")

    monkeypatch.setattr(
        run_report.narrative, "generate_narrative_sync", _must_not_be_called
    )
    row = _row()
    cohort = _cohort(row)
    bot_service = _FakeBotService(
        error=BotDataUnavailableError("missing overview.json")
    )

    extras = run_report.build_assessment_extras(
        cohort, bot_service, generate_narrative_flag=True
    )

    extra = extras["TESTCODE1"]
    assert extra["strategy"] is None
    assert extra["behavioral"] is None
    assert extra["narrative"] is None


def test_rows_with_errors_or_no_verdict_are_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_generate_narrative_sync(monkeypatch)
    ok_row = _row()
    broken_row = _row(
        unique_code="BROKEN1", bot_id="bot_BROKEN1", verdict=None, error="NO_LEDGER"
    )
    cohort = _cohort(ok_row, broken_row)
    bot_service = _FakeBotService(bot=_fake_bot_result())

    extras = run_report.build_assessment_extras(
        cohort, bot_service, generate_narrative_flag=True
    )

    assert set(extras.keys()) == {"TESTCODE1"}
    assert len(bot_service.calls) == 1


# --------------------------------------------------------------------------- #
# closed_trade_series / horizon_scenarios / assets -- the fix that restores
# `GET /bot/<code>`'s 2 missing charts + 1 missing table when it has to read
# assessment.json instead of running live (measured: file-sourced was 5
# `<svg>`/8 `<details>`, live is 7/12). Ride the SAME re-fetch as the
# strategy/behavioural evidence above, but need EXTRA attributes
# `_fake_bot_result()` above never sets (`trade_ledger_summary`,
# `current_state`, `simulation_results`) -- degrade to `None` (proven
# already, implicitly, by every test above that uses the plain
# `_fake_bot_result()`) when the re-fetched bot lacks them.
# --------------------------------------------------------------------------- #


def _fake_trade(symbol: str, close_time: int, realized_pnl: float) -> SimpleNamespace:
    return SimpleNamespace(
        symbol=symbol, close_time=close_time, realized_pnl=realized_pnl
    )


def _fake_bot_result_with_full_evidence(**overrides: Any) -> SimpleNamespace:
    """`_fake_bot_result()` above, plus the three extra attributes
    `_closed_trade_series_evidence`/`_horizon_scenarios_evidence`/
    `_assets_evidence` (run_report.py) read: `trade_ledger_summary`
    (closed trades), `current_state.open_positions` (open symbols), and
    `simulation_results.horizon_scenarios` (real `HorizonOutcome` pydantic
    rows, so `.model_dump(mode="json")` behaves exactly like the live
    `BotResult` it stands in for).
    """
    bot = _fake_bot_result()
    bot.trade_ledger_summary = [
        _fake_trade("ETH-USDT-SWAP", 1_700_000_000_000, 12.5),
        _fake_trade("ETH-USDT-SWAP", 1_700_003_600_000, -4.0),
    ]
    bot.current_state = SimpleNamespace(open_positions=[])
    bot.simulation_results = SimpleNamespace(
        horizon_scenarios=[
            HorizonOutcome(
                label="SHORT",
                horizon_trades=5,
                iterations=100,
                is_valid=True,
                probability_of_profit=90.0,
                p_loss_after_horizon=10.0,
            ),
            HorizonOutcome(
                label="MEDIUM",
                horizon_trades=50,
                iterations=10_000,
                is_valid=True,
                probability_of_profit=85.0,
                p_loss_after_horizon=15.0,
            ),
        ]
    )
    for key, value in overrides.items():
        setattr(bot, key, value)
    return bot


def test_extras_include_closed_trade_series_horizon_scenarios_and_assets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_generate_narrative_sync(monkeypatch)
    row = _row()
    cohort = _cohort(row)
    bot_service = _FakeBotService(bot=_fake_bot_result_with_full_evidence())

    extras = run_report.build_assessment_extras(
        cohort,
        bot_service,
        generate_narrative_flag=True,
        simulation_iterations=10_000,
        simulation_horizon=None,
        seed=7,
    )

    extra = extras["TESTCODE1"]
    assert extra["closed_trade_series"] == [
        {"close_time": 1_700_000_000_000, "realized_pnl": 12.5},
        {"close_time": 1_700_003_600_000, "realized_pnl": -4.0},
    ]
    assert [s["label"] for s in extra["horizon_scenarios"]] == ["SHORT", "MEDIUM"]
    assert extra["horizon_scenarios"][1]["probability_of_profit"] == 85.0
    # Both closed trades share one symbol, never seen open -> one "ĐANG
    # GIAO DỊCH" (or "ĐÃ RỜI", depending on last_close_days) row, not zero.
    assert len(extra["assets"]) == 1
    assert extra["assets"][0]["asset"] == "ETH"
    assert extra["assets"][0]["closed_seen"] == 2

    # The real iterations/horizon/seed this run used -- not the historical
    # cheap 100/1/42 defaults -- reached the re-fetch call.
    call = bot_service.calls[0]
    assert call["simulation_iterations"] == 10_000
    assert call["simulation_horizon"] is None
    assert call["seed"] == 7


def test_extras_default_simulation_params_stay_the_historical_cheap_ones(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Backward-compatibility check: a caller that never passes
    `simulation_iterations`/`simulation_horizon`/`seed` (every pre-existing
    test above, and any future caller that genuinely only wants the
    strategy/behavioural evidence) must still get the ORIGINAL cheap
    100/1/42 re-fetch -- unaffected by this task's addition.
    """
    _fake_generate_narrative_sync(monkeypatch)
    row = _row()
    cohort = _cohort(row)
    bot_service = _FakeBotService(bot=_fake_bot_result())

    run_report.build_assessment_extras(
        cohort, bot_service, generate_narrative_flag=True
    )

    call = bot_service.calls[0]
    assert call["simulation_iterations"] == 100
    assert call["simulation_horizon"] == 1
    assert call["seed"] == 42


def test_extras_new_evidence_fields_degrade_to_none_without_the_extra_attrs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The plain `_fake_bot_result()` (no `trade_ledger_summary`/
    `current_state`/`simulation_results`) stands in for a real `BotResult`
    missing none of its required fields -- this guard only ever fires for a
    test double, but must still degrade cleanly rather than raise
    `AttributeError`.
    """
    _fake_generate_narrative_sync(monkeypatch)
    row = _row()
    cohort = _cohort(row)
    bot_service = _FakeBotService(bot=_fake_bot_result())

    extras = run_report.build_assessment_extras(
        cohort, bot_service, generate_narrative_flag=True
    )

    extra = extras["TESTCODE1"]
    assert extra["closed_trade_series"] is None
    assert extra["horizon_scenarios"] is None
    assert extra["assets"] is None
    # Strategy/behavioural evidence (already covered above) is unaffected.
    assert extra["strategy"]["observed_profile"] == "DayTrading"


# --------------------------------------------------------------------------- #
# End to end with assessment_store: the narrative that lands in the file
# matches the SAME row's own numbers -- Việc 4's hard constraint.
# --------------------------------------------------------------------------- #


def test_narrative_in_persisted_assessment_matches_this_assessments_own_numbers(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _fake_generate_narrative_sync(monkeypatch, text="Bot này đánh ngược đà thị trường.")
    row = _row(risk_score=42.0, quality_score=65.0)
    cohort = _cohort(row)
    bot_service = _FakeBotService(bot=_fake_bot_result())

    extras = run_report.build_assessment_extras(
        cohort, bot_service, generate_narrative_flag=True
    )
    built = build_assessments(cohort, tmp_path, extra_by_code=extras)
    assert len(built) == 1
    _, payload = built[0]

    assert payload["expert_assessment"] == "Bot này đánh ngược đà thị trường."
    # Same file's own scored numbers, untouched by the narrative wiring.
    assert payload["recommendation"]["risk_score"] == 42.0
    assert payload["recommendation"]["quality_score"] == 65.0
    assert payload["evidence"]["observed_profile"] == "DayTrading"


def test_a_second_run_with_different_numbers_gets_its_own_narrative_not_the_old_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """Regression guard for the exact drift Việc 4 forbids: a narrative
    generated for one set of scored numbers must never be the one attached
    to a DIFFERENT set for the same bot (e.g. a later re-run after the
    ledger moved on).
    """
    texts = iter(
        [
            "Đợt chấm đầu: rủi ro ở mức trung bình.",
            "Đợt chấm sau: rủi ro đã tăng rõ rệt.",
        ]
    )

    def _fake(numbers, context, *, backend=None):  # noqa: ANN001
        return next(texts)

    monkeypatch.setattr(run_report.narrative, "generate_narrative_sync", _fake)

    bot_service = _FakeBotService(bot=_fake_bot_result())
    first_row = _row(risk_score=42.0)
    first_cohort = _cohort(first_row, generated_at_ms=1_000)
    first_extras = run_report.build_assessment_extras(
        first_cohort, bot_service, generate_narrative_flag=True
    )
    first_payload = build_assessments(
        first_cohort, tmp_path, extra_by_code=first_extras
    )[0][1]

    second_row = _row(risk_score=70.0)
    second_cohort = _cohort(second_row, generated_at_ms=2_000)
    second_extras = run_report.build_assessment_extras(
        second_cohort, bot_service, generate_narrative_flag=True
    )
    second_payload = build_assessments(
        second_cohort, tmp_path, extra_by_code=second_extras
    )[0][1]

    assert (
        first_payload["expert_assessment"]
        == "Đợt chấm đầu: rủi ro ở mức trung bình."
    )
    assert first_payload["recommendation"]["risk_score"] == 42.0
    assert (
        second_payload["expert_assessment"] == "Đợt chấm sau: rủi ro đã tăng rõ rệt."
    )
    assert second_payload["recommendation"]["risk_score"] == 70.0
