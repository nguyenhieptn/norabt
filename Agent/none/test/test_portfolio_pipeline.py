"""Portfolio verdict, storage and the multi-bot pipeline end to end.

The integration cases run against the same committed on-disk fixtures the
rest of this suite uses (`Agent/data/trade/...`, read through
`EvaluationMode.SNAPSHOT` with a fixed `as_of_ms`), so they need no network
and no OKX credentials.
"""

from __future__ import annotations

import pytest

from Agent.backend.pipeline import RiskSupervisionPipeline
from Agent.backend.pipeline_portfolio import (
    PortfolioBotRequest,
    PortfolioSupervisionPipeline,
)
from Agent.backend.report.qc.history.portfolio_store import PortfolioHistoryStore
from Agent.backend.report.qc.portfolio.schemas import PortfolioVerdict
from Agent.backend.report.qc.portfolio.service import (
    PortfolioCandidate,
    PortfolioQCService,
)
from Agent.backend.bot.mcp.schemas.bot_result import PositionSide
from Agent.none.test.conftest import FIXED_AS_OF_MS
from Agent.none.test.portfolio_factory import BASE_MS, DAY_MS, make_bot, make_trades

_SERIES = [1.0, -2.0, 3.0, -1.0, 0.5, -0.5, 2.0, -3.0, 1.5, -1.5] * 6

# Three committed fixtures with ~86 days of shared trading history across
# three different instruments -- the exact shape the feature exists for: a
# book that looks diversified by instrument and may not be by behaviour.
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
# Verdict
# --------------------------------------------------------------------------- #


def test_identical_bots_are_called_a_correlation_cluster() -> None:
    result = _assess(
        [
            make_bot("AAA", make_trades(_SERIES)),
            make_bot("BBB", make_trades(_SERIES)),
        ]
    )
    assert result.verdict is PortfolioVerdict.HIGH_CORRELATION_CLUSTER
    assert "move as one" in result.verdict_reason
    assert result.score_adjustments["correlation"] > 20.0


def test_offsetting_bots_are_called_diversified() -> None:
    result = _assess(
        [
            make_bot("AAA", make_trades(_SERIES)),
            make_bot("BBB", make_trades([-value for value in _SERIES])),
        ]
    )
    assert result.verdict is PortfolioVerdict.DIVERSIFIED
    assert result.score_adjustments.get("correlation", 0.0) == 0.0


def test_one_extreme_pair_is_not_hidden_by_a_comfortable_average() -> None:
    """Two clones plus one independent bot average out to something moderate.

    An average-only rule would call that portfolio partly diversified while
    two thirds of it is a single position held twice, so the worst pair has
    to be able to decide the verdict on its own.
    """
    import numpy as np

    rng = np.random.default_rng(5)
    independent = list(rng.normal(0, 3, 60))
    result = _assess(
        [
            make_bot("AAA", make_trades(_SERIES)),
            make_bot("BBB", make_trades(_SERIES)),
            make_bot("CCC", make_trades(independent)),
        ]
    )
    assert result.correlation.average_pearson < PortfolioQCService.HIGH_AVG_PEARSON
    assert result.correlation.max_pearson == pytest.approx(1.0)
    assert result.verdict is PortfolioVerdict.HIGH_CORRELATION_CLUSTER
    assert "held twice" in result.verdict_reason


def test_no_shared_window_is_insufficient_evidence_not_diversified() -> None:
    """Unmeasurable must never be reported as a clean bill of health."""
    result = _assess(
        [
            make_bot("AAA", make_trades(_SERIES)),
            make_bot(
                "BBB", make_trades(_SERIES, start_ms=BASE_MS + 400 * DAY_MS)
            ),
        ]
    )
    assert result.verdict is PortfolioVerdict.INSUFFICIENT_EVIDENCE
    assert result.joint_simulation is None


# --------------------------------------------------------------------------- #
# Membership and concentration
# --------------------------------------------------------------------------- #


def test_an_unmeasurable_member_stays_in_the_report_with_its_reason() -> None:
    """Dropping it silently would answer a question the user did not ask."""
    result = _assess(
        [
            make_bot("AAA", make_trades(_SERIES)),
            make_bot("BBB", make_trades(_SERIES)),
            make_bot("CCC", make_trades([1.0, 2.0])),
        ]
    )
    assert len(result.members) == 3
    assert result.measurable_member_count == 2
    excluded = [member for member in result.members if member.excluded_reason]
    assert [member.unique_code for member in excluded] == ["CCC"]
    assert any("not part of the correlation" in w for w in result.warnings)


def test_the_same_bot_twice_is_rejected() -> None:
    bot = make_bot("AAA", make_trades(_SERIES))
    with pytest.raises(ValueError, match="more than once"):
        _assess([bot, bot])


def test_concentration_sees_through_a_multi_bot_split() -> None:
    """Three bots, one instrument, all long: a single bet in three costumes."""
    result = _assess(
        [
            make_bot(
                code,
                make_trades(_SERIES),
                symbol="BTC",
                current_notional=5_000.0,
                side=PositionSide.LONG,
            )
            for code in ("AAA", "BBB", "CCC")
        ]
    )
    assert result.concentration.largest_symbol == "BTC"
    assert result.concentration.largest_symbol_share_pct == pytest.approx(100.0)
    assert result.concentration.directional_alignment == pytest.approx(1.0)
    assert result.score_adjustments["directional_alignment"] == pytest.approx(
        PortfolioQCService.DIRECTIONAL_PENALTY_MAX
    )


def test_opposing_positions_are_not_read_as_directional() -> None:
    result = _assess(
        [
            make_bot("AAA", make_trades(_SERIES), side=PositionSide.LONG),
            make_bot(
                "BBB",
                make_trades([-value for value in _SERIES]),
                side=PositionSide.SHORT,
            ),
        ]
    )
    assert result.concentration.directional_alignment == pytest.approx(0.0)
    assert result.concentration.net_notional == pytest.approx(0.0)


def test_capital_weights_are_withheld_when_one_member_has_no_capital() -> None:
    """An invented weight would silently change every weighted number."""
    result = _assess(
        [
            make_bot("AAA", make_trades(_SERIES), capital_at_risk=10_000.0),
            make_bot("BBB", make_trades(_SERIES), capital_at_risk=None),
        ]
    )
    assert all(member.capital_weight is None for member in result.members)
    assert result.joint_simulation is not None
    assert result.joint_simulation.is_valid is False


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #


def test_store_round_trips_and_deduplicates(tmp_path) -> None:
    store = PortfolioHistoryStore(root=tmp_path)
    result = _assess(
        [
            make_bot("AAA", make_trades(_SERIES)),
            make_bot("BBB", make_trades(_SERIES)),
        ]
    )
    assert store.append(result) is True
    # Same snapshot, same id: re-running must not grow the history.
    assert store.append(result) is False
    history = store.history(result.portfolio_id)
    assert len(history) == 1
    assert history[0].assessment_id == result.assessment_id
    assert history[0].correlation.average_pearson == pytest.approx(1.0)
    latest = store.list_latest()
    assert [entry.portfolio_id for entry in latest] == [result.portfolio_id]


def test_portfolio_id_is_the_member_set_not_the_order(tmp_path) -> None:
    """Re-analysing the same bots must land in the same file, so a portfolio
    has a history of its own to read drift from."""
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(list(reversed(_SERIES)))),
    ]
    first = _assess(bots)
    second = _assess(list(reversed(bots)))
    assert first.portfolio_id == second.portfolio_id


def test_missing_store_directory_lists_empty(tmp_path) -> None:
    assert PortfolioHistoryStore(root=tmp_path / "nope").list_latest() == []


# --------------------------------------------------------------------------- #
# Pipeline, on real fixtures
# --------------------------------------------------------------------------- #


def _pipeline() -> PortfolioSupervisionPipeline:
    return PortfolioSupervisionPipeline(persist_history=False, max_workers=2)


def test_pipeline_runs_three_real_bots_and_measures_them() -> None:
    result = _pipeline().run(
        _MEMBERS,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=200,
        simulation_horizon=100,
        portfolio_iterations=500,
    )
    assert result.failures == []
    assert len(result.members) == 3
    portfolio = result.portfolio_assessment
    assert portfolio is not None
    assert portfolio.measurable_member_count == 3
    assert portfolio.correlation.is_valid
    assert len(portfolio.correlation.pairs) == 3
    assert portfolio.correlation.alignment.overlap_days > 60
    assert portfolio.joint_simulation is not None
    assert portfolio.joint_simulation.is_valid
    assert portfolio.portfolio_risk_score is not None
    assert portfolio.verdict is not PortfolioVerdict.INSUFFICIENT_EVIDENCE
    assert portfolio.recommended_action


def test_the_portfolio_pass_changes_only_the_portfolio_risk_lens() -> None:
    """The nine single-bot lenses must be untouched by running in a group.

    This is the guarantee the whole feature rests on: adding a bot to a
    portfolio view may not quietly move another bot's own score.
    """
    solo = RiskSupervisionPipeline(persist_history=False).run(
        _MEMBERS[0].asset,
        _MEMBERS[0].bot_folder_name,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=200,
        simulation_horizon=100,
    )
    grouped = _pipeline().run(
        _MEMBERS,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=200,
        simulation_horizon=100,
        portfolio_iterations=500,
    )
    member = next(
        item
        for item in grouped.members
        if item.bot_result.identity.bot_id == solo.bot_result.identity.bot_id
    )
    solo_dims = solo.risk_assessment.dimensions
    group_dims = member.risk_assessment.dimensions
    for name in type(solo_dims).model_fields:
        if name == "portfolio_risk":
            continue
        assert getattr(solo_dims, name) == getattr(group_dims, name), name
    # And the one lens that does take portfolio context actually used it.
    assert solo_dims.portfolio_risk.status.value == "UNKNOWN"
    assert group_dims.portfolio_risk.status.value == "AVAILABLE"


def test_a_single_bot_is_not_a_portfolio() -> None:
    with pytest.raises(ValueError, match="at least two"):
        _pipeline().run(_MEMBERS[:1])


def test_an_unreachable_member_is_reported_not_swallowed() -> None:
    result = _pipeline().run(
        (*_MEMBERS[:2], PortfolioBotRequest(asset="BTC", bot_folder_name="bot_NOPE")),
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=200,
        simulation_horizon=100,
        portfolio_iterations=500,
    )
    assert [failure.bot_folder_name for failure in result.failures] == ["bot_NOPE"]
    assert len(result.members) == 2
    assert result.portfolio_assessment is not None
    assert any(
        "bot_NOPE" in warning
        for warning in result.portfolio_assessment.warnings
    )
