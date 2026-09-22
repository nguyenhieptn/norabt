"""Exact loss-streak baseline: the artifact this fixes and the fix itself.

Context: 15/15 bots QC labeled NGUY HIỂM were vetoed on tail risk, and 9/15 of
those vetoes cited "extreme simulated tail risk" driven by `p_5_loss_streak`
and `p_10_loss_streak`. The probability that a sequence of trades contains a
run of k consecutive losses rises monotonically with the number of trades --
so a bot that has simply traded a lot is near-guaranteed to show a long
losing streak somewhere in its history even when every trade is an
independent draw from its own (possibly excellent) win rate. The raw number
conflates "traded a lot" with "loses in a risky, clustered way".

`MonteCarloSimulationEngine.loss_streak_baseline_probability` is the "how
often would this happen anyway, from sample size alone" baseline: the exact
probability an *independent* Bernoulli sequence at this bot's own per-trade
loss rate would show the same streak over the same horizon. What is left
after subtracting it (`p_5_loss_streak_excess` / `p_10_loss_streak_excess`)
is what should actually count as a risk signal.
"""

from __future__ import annotations

import numpy as np
import pytest

from Agent.backend.bot.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.bot.mcp.schemas.bot_result import PositionSide, TradeLedgerItem

HOUR_MS = 3_600_000


def trade(index: int, pnl: float) -> TradeLedgerItem:
    return TradeLedgerItem(
        trade_id=f"t{index}",
        symbol="BTC-USDT-SWAP",
        side=PositionSide.LONG,
        open_time=index * HOUR_MS,
        close_time=(index + 1) * HOUR_MS,
        realized_pnl=pnl,
        holding_time_minutes=60.0,
    )


def _direct_bernoulli_streak_probability(
    q: float, horizon: int, streak_length: int, trials: int = 60_000, seed: int = 0
) -> float:
    """Ground truth via literal simulation, to check the DP against something
    that does not share any code with it.
    """
    rng = np.random.default_rng(seed)
    is_loss = rng.random((trials, horizon)) < q
    run = np.zeros(trials, dtype=np.int32)
    hit = np.zeros(trials, dtype=bool)
    for column in range(horizon):
        run = np.where(is_loss[:, column], run + 1, 0)
        hit |= run >= streak_length
    return float(np.mean(hit))


@pytest.mark.parametrize(
    "q, horizon, streak_length",
    [
        (0.3, 50, 5),
        (0.1, 100, 3),
        (0.5, 30, 4),
        (0.091, 500, 5),
        (0.2, 200, 10),
    ],
)
def test_exact_baseline_matches_direct_monte_carlo_simulation(
    q, horizon, streak_length
):
    exact = MonteCarloSimulationEngine.loss_streak_baseline_probability(
        q, horizon, streak_length
    )
    simulated = _direct_bernoulli_streak_probability(q, horizon, streak_length)

    # Binomial sampling error on 60k independent draws; a generous multiple
    # of it plus a small floor keeps this from flaking on a tiny probability.
    stderr = (simulated * (1 - simulated) / 60_000) ** 0.5
    tolerance = max(5 * stderr, 0.003)
    assert exact == pytest.approx(simulated, abs=tolerance)


def test_zero_loss_probability_gives_zero_baseline():
    assert (
        MonteCarloSimulationEngine.loss_streak_baseline_probability(0.0, 500, 5) == 0.0
    )
    assert (
        MonteCarloSimulationEngine.loss_streak_baseline_probability(0.0, 10, 1) == 0.0
    )


def test_certain_loss_gives_baseline_one_once_horizon_reaches_streak_length():
    assert MonteCarloSimulationEngine.loss_streak_baseline_probability(1.0, 5, 5) == 1.0
    assert (
        MonteCarloSimulationEngine.loss_streak_baseline_probability(1.0, 500, 5) == 1.0
    )
    # Horizon shorter than the streak length: the streak cannot occur at all,
    # even with a certain loss on every trade.
    assert MonteCarloSimulationEngine.loss_streak_baseline_probability(1.0, 4, 5) == 0.0


def test_horizon_shorter_than_streak_length_is_always_zero():
    for q in (0.0, 0.3, 0.7, 1.0):
        assert (
            MonteCarloSimulationEngine.loss_streak_baseline_probability(q, 3, 5) == 0.0
        )


def test_baseline_rises_monotonically_with_loss_probability():
    values = [
        MonteCarloSimulationEngine.loss_streak_baseline_probability(q, 500, 5)
        for q in (0.05, 0.1, 0.2, 0.3, 0.4, 0.5)
    ]
    assert values == sorted(values)


def test_baseline_rises_monotonically_with_horizon():
    values = [
        MonteCarloSimulationEngine.loss_streak_baseline_probability(0.2, horizon, 5)
        for horizon in (10, 50, 100, 300, 500)
    ]
    assert values == sorted(values)


# --- Engine-level: does the excess field actually separate the two cases? ---


def _evenly_spaced_losses(n: int, loss_every: int) -> list[TradeLedgerItem]:
    """A high-win-rate ledger with no real streak dependence: losses are
    spread out by construction, never adjacent in the original order.
    """
    return [
        trade(i, -100.0 if i % loss_every == loss_every - 1 else 10.0) for i in range(n)
    ]


def test_high_win_rate_bot_with_no_real_clustering_has_small_excess_at_horizon_500():
    """The motivating case: a bot with ~90% win rate and enough real history
    to genuinely support a 500-trade horizon, with no real streak dependence.
    Its raw p_5_loss_streak should already track the baseline closely, so the
    excess -- the only thing the new threshold checks -- stays small and this
    bot must not eat the +15 penalty that a raw-number threshold would apply
    to any bot that simply trades a lot.
    """
    trades = _evenly_spaced_losses(n=550, loss_every=10)
    result = MonteCarloSimulationEngine.run_simulation(
        trades,
        1_000.0,
        iterations=8_000,
        horizon_trades=500,
        seed=42,
        block_bootstrap=True,
    )
    assert result.is_valid
    assert result.p_5_loss_streak_baseline is not None
    assert (result.p_5_loss_streak_excess or 0.0) <= 15.0
    assert (result.p_10_loss_streak_excess or 0.0) <= 10.0


def test_genuine_loss_clustering_still_produces_a_large_excess():
    """Required negative control: a bot whose losses are genuinely dumped
    together (a real drawdown episode, not just sample-size noise) must still
    show up as risky under the new excess-based scoring. If this test did not
    hold, the fix would just be a blanket loosening in disguise.
    """
    n = 500
    trades = [trade(i, 10.0) for i in range(n)]
    # One real cluster of 8 consecutive losses -- an actual clustered episode,
    # not scattered single losses -- plus routine scattered single losses so
    # the overall win rate still reads as high (~90%).
    for i in range(200, 208):
        trades[i] = trade(i, -50.0)
    for i in range(0, n, 13):
        trades[i] = trade(i, -20.0)

    result = MonteCarloSimulationEngine.run_simulation(
        trades,
        1_000.0,
        iterations=8_000,
        horizon_trades=500,
        seed=42,
        block_bootstrap=True,
    )
    assert result.is_valid
    win_rate = sum(1 for t in trades if t.realized_pnl > 0) / n
    assert win_rate > 0.85  # still a high win-rate bot on paper
    assert result.p_5_loss_streak_baseline is not None
    assert result.p_5_loss_streak_baseline < 5.0  # baseline stays low: high win rate
    assert (result.p_5_loss_streak_excess or 0.0) > 15.0  # but excess is not


def test_baseline_and_excess_are_consistent_with_the_raw_field():
    trades = _evenly_spaced_losses(n=120, loss_every=8)
    result = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000.0, iterations=2_000, seed=5, block_bootstrap=True
    )
    assert result.is_valid
    expected_excess5 = max(
        0.0, result.p_5_loss_streak - result.p_5_loss_streak_baseline
    )
    expected_excess10 = max(
        0.0, result.p_10_loss_streak - result.p_10_loss_streak_baseline
    )
    assert result.p_5_loss_streak_excess == pytest.approx(expected_excess5)
    assert result.p_10_loss_streak_excess == pytest.approx(expected_excess10)
