"""Monte Carlo over the whole book, with the bots' co-movement left intact.

WHAT MAKES THIS DIFFERENT FROM RUNNING THE PER-BOT ENGINE N TIMES. Logic 2's
`MonteCarloSimulationEngine` resamples one bot's trades in isolation. Summing
N of those runs would produce a portfolio in which every bot draws its
outcome independently -- which is exactly the assumption a correlated
portfolio violates, and it is the assumption that makes a cluster of
same-direction bots look safe. The fix is that a single draw here picks a TIME
BUCKET and takes what EVERY bot did in that bucket, as one column. Whatever
co-movement the ledgers contain is carried along by construction; nothing is
modelled, fitted or assumed about it.

THE THREE NUMBERS, AND WHY ALL THREE ARE NEEDED. One VaR on its own cannot
answer whether combining these bots helped, because there is nothing to
compare it against:

  sum_individual_var_95_pct   capital-weighted sum of each bot's standalone
                              VaR -- the undiversified benchmark, what you
                              risk if the bots are one and the same bet.
  independent_var_95_pct      the same bots resampled with their co-movement
                              deliberately destroyed -- the best case, the
                              diversification the combination COULD deliver.
  var_95_pct                  the real one, co-movement intact.

`var_95_pct` sitting near the first means the portfolio is one position in
three costumes. Sitting near the second means the bots genuinely offset. The
gap between the two counterfactuals is the price of the correlation, and it
is reported as `correlation_cost_pct` rather than left for a reader to derive.

The resampler is the same Politis & Romano (1994) stationary bootstrap Logic
2 uses, for the same reason: a fixed block length is a guess that shows up in
the answer, whereas restarting with probability 1/L makes block lengths
geometric with mean L and bakes in no single choice. L = n^(1/3) is the
standard rate. Keeping the two engines on the same resampler is what lets a
per-bot VaR and this portfolio VaR be put in the same table at all.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

import numpy as np

from Agent.backend.report.qc.portfolio.schemas import JointSimulationResult
from Agent.backend.report.qc.portfolio.timeseries import AlignedSeries

_DAY_MS = 24 * 60 * 60 * 1000


class JointMonteCarloEngine:
    DEFAULT_ITERATIONS = 10_000
    MAX_ITERATIONS = 50_000
    MAX_HORIZON = 500
    BATCH_SIZE = 2_000
    # Matches TimeSeriesMerger.MIN_BUCKETS: a window too short to correlate
    # over is too short to resample from.
    MIN_BUCKETS = 20
    THIN_BUCKETS = 40

    @classmethod
    def _indices(
        cls,
        rng: np.random.Generator,
        sample_length: int,
        batch: int,
        horizon: int,
    ) -> np.ndarray:
        """One stationary-bootstrap index matrix of shape (batch, horizon)."""
        if sample_length < 4:
            return rng.integers(0, sample_length, size=(batch, horizon))
        expected_block = max(
            2, min(int(round(sample_length ** (1 / 3))), sample_length // 2)
        )
        restarts = rng.random((batch, horizon)) < (1.0 / expected_block)
        restarts[:, 0] = True
        fresh = rng.integers(0, sample_length, size=(batch, horizon))
        positions = np.arange(horizon)
        block_start = np.maximum.accumulate(
            np.where(restarts, positions, 0), axis=1
        )
        offsets = positions - block_start
        origins = np.take_along_axis(fresh, block_start, axis=1)
        # Wrapping keeps every bucket equally likely to appear; a truncated
        # walk would under-sample the end of the window.
        return (origins + offsets) % sample_length

    @staticmethod
    def _summarise(
        path_pnl: np.ndarray, capital: float
    ) -> Dict[str, float]:
        """Loss statistics for a set of simulated paths, as % of capital.

        Sign convention is deliberately the same as `SimulationResults`: VaR
        and CVaR are POSITIVE when they describe a loss. Two risk numbers in
        one report with opposite signs is a reading error waiting to happen.
        """
        equity = capital + np.cumsum(path_pnl, axis=1)
        equity = np.concatenate(
            (np.full((equity.shape[0], 1), capital), equity), axis=1
        )
        peaks = np.maximum.accumulate(equity, axis=1)
        drawdown = np.clip((peaks - equity) / np.maximum(peaks, 1e-12), 0.0, 1.0)
        terminal = equity[:, -1]
        profits = (terminal - capital) / capital * 100.0
        tail95 = profits[profits <= np.percentile(profits, 5)]
        tail99 = profits[profits <= np.percentile(profits, 1)]
        return {
            "var_95_pct": -float(np.percentile(profits, 5)),
            "var_99_pct": -float(np.percentile(profits, 1)),
            "cvar_95_pct": -float(np.mean(tail95)) if tail95.size else float("nan"),
            "cvar_99_pct": -float(np.mean(tail99)) if tail99.size else float("nan"),
            "profit_pct_p05": float(np.percentile(profits, 5)),
            "profit_pct_p50": float(np.percentile(profits, 50)),
            "profit_pct_p95": float(np.percentile(profits, 95)),
            "probability_of_profit": float(np.mean(profits > 0.0) * 100.0),
            "median_max_drawdown": float(np.percentile(np.max(drawdown, axis=1), 50))
            * 100.0,
            "p95_max_drawdown": float(np.percentile(np.max(drawdown, axis=1), 95))
            * 100.0,
            "p_ruin": float(np.mean(np.any(equity <= 0.0, axis=1)) * 100.0),
        }

    @classmethod
    def run(
        cls,
        series: AlignedSeries,
        capital_at_risk: Sequence[Optional[float]],
        iterations: int = DEFAULT_ITERATIONS,
        horizon_buckets: Optional[int] = None,
        seed: Optional[int] = 42,
    ) -> JointSimulationResult:
        labels = list(series.labels)
        warnings: List[str] = []

        if not series.is_valid or series.matrix.size == 0:
            return JointSimulationResult(
                is_valid=False,
                warnings=["No aligned series to simulate over"],
            )
        if len(capital_at_risk) != len(labels):
            raise ValueError("capital_at_risk must be the same length as the series")

        missing = [
            labels[index]
            for index, value in enumerate(capital_at_risk)
            if value is None or value <= 0.0
        ]
        if missing:
            # Fail closed. Substituting an equal weight, or an average of the
            # members that do have capital, would put a number on the report
            # that no bot actually reported -- and every VaR below is a
            # percentage OF that number.
            return JointSimulationResult(
                is_valid=False,
                warnings=[
                    "Cannot size the portfolio: no capital at risk resolved for "
                    + ", ".join(f"[{name}]" for name in missing)
                    + ". A substituted figure would change every percentage below, "
                    "so the joint simulation is withheld rather than guessed."
                ],
            )

        matrix = series.matrix
        member_capital = np.array([float(value) for value in capital_at_risk])
        total_capital = float(member_capital.sum())
        sample_length = int(matrix.shape[1])
        if sample_length < cls.MIN_BUCKETS:
            return JointSimulationResult(
                is_valid=False,
                sample_buckets=sample_length,
                warnings=[
                    f"Only {sample_length} shared buckets to resample from "
                    f"(needs {cls.MIN_BUCKETS})"
                ],
            )

        iterations = max(1, min(int(iterations), cls.MAX_ITERATIONS))
        horizon = int(horizon_buckets or sample_length)
        horizon = max(1, min(horizon, cls.MAX_HORIZON))
        thin = sample_length < cls.THIN_BUCKETS
        if thin:
            warnings.append(
                f"Thin sample: {sample_length} shared buckets. A bootstrap "
                "percentile resolves only to about 1/n, so both tails carry a "
                "large standard error -- read the figures as an indicative range"
            )

        rng = np.random.default_rng(seed)
        joint_paths: List[np.ndarray] = []
        independent_paths: List[np.ndarray] = []
        remaining = iterations
        while remaining:
            batch = min(cls.BATCH_SIZE, remaining)
            # One index vector per path, applied to EVERY bot: the column is
            # taken whole, so the bots' co-movement survives the resampling.
            shared = cls._indices(rng, sample_length, batch, horizon)
            joint_paths.append(matrix[:, shared].sum(axis=0))
            # The counterfactual: each bot drawn from its own independent
            # index vector, which destroys the co-movement while leaving every
            # marginal distribution untouched.
            independent = np.zeros((batch, horizon), dtype=np.float64)
            for row in range(matrix.shape[0]):
                own = cls._indices(rng, sample_length, batch, horizon)
                independent += matrix[row][own]
            independent_paths.append(independent)
            remaining -= batch

        joint_stats = cls._summarise(np.concatenate(joint_paths), total_capital)
        independent_stats = cls._summarise(
            np.concatenate(independent_paths), total_capital
        )

        # Each bot alone, on its own capital, so the per-member VaR is
        # comparable with what that bot's own report already shows.
        per_member: Dict[str, float] = {}
        undiversified = 0.0
        for row, label in enumerate(labels):
            member_rng = np.random.default_rng(
                None if seed is None else seed + row + 1
            )
            paths: List[np.ndarray] = []
            remaining = iterations
            while remaining:
                batch = min(cls.BATCH_SIZE, remaining)
                own = cls._indices(member_rng, sample_length, batch, horizon)
                paths.append(matrix[row][own])
                remaining -= batch
            stats = cls._summarise(
                np.concatenate(paths), float(member_capital[row])
            )
            per_member[label] = round(stats["var_95_pct"], 4)
            # Weighted into portfolio terms: a bot holding 10% of the capital
            # contributes 10% of its own percentage loss to the whole.
            undiversified += stats["var_95_pct"] * (
                float(member_capital[row]) / total_capital
            )

        joint_var = joint_stats["var_95_pct"]
        independent_var = independent_stats["var_95_pct"]
        if undiversified > 0.0:
            diversification_ratio = 1.0 - joint_var / undiversified
            potential_ratio = 1.0 - independent_var / undiversified
            correlation_cost = joint_var - independent_var
        else:
            # The benchmark is not a loss, so "how much of the loss did
            # diversification remove" has no meaning. None, not zero.
            diversification_ratio = None
            potential_ratio = None
            correlation_cost = None
            warnings.append(
                "The undiversified benchmark VaR is not positive, so no "
                "diversification ratio can be formed from it"
            )

        if diversification_ratio is not None and diversification_ratio < 0.05:
            warnings.append(
                "Combining these bots removed essentially none of the loss tail: "
                f"the portfolio's 95% VaR ({joint_var:.1f}% of capital) is within "
                f"5% of what the same bots risk undiversified ({undiversified:.1f}%)"
            )

        def _clean(value: float) -> Optional[float]:
            return round(value, 4) if np.isfinite(value) else None

        return JointSimulationResult(
            iterations=iterations,
            horizon_buckets=horizon,
            horizon_calendar_days=round(horizon * series.bucket_ms / _DAY_MS, 3),
            sample_buckets=sample_length,
            sample_is_thin=thin,
            capital_at_risk=total_capital,
            var_95_pct=_clean(joint_var),
            var_99_pct=_clean(joint_stats["var_99_pct"]),
            cvar_95_pct=_clean(joint_stats["cvar_95_pct"]),
            cvar_99_pct=_clean(joint_stats["cvar_99_pct"]),
            profit_pct_p05=_clean(joint_stats["profit_pct_p05"]),
            profit_pct_p50=_clean(joint_stats["profit_pct_p50"]),
            profit_pct_p95=_clean(joint_stats["profit_pct_p95"]),
            probability_of_profit=_clean(joint_stats["probability_of_profit"]),
            median_max_drawdown=_clean(joint_stats["median_max_drawdown"]),
            p95_max_drawdown=_clean(joint_stats["p95_max_drawdown"]),
            p_ruin=_clean(joint_stats["p_ruin"]),
            sum_individual_var_95_pct=_clean(undiversified),
            independent_var_95_pct=_clean(independent_var),
            diversification_ratio=(
                round(diversification_ratio, 4)
                if diversification_ratio is not None
                else None
            ),
            potential_diversification_ratio=(
                round(potential_ratio, 4) if potential_ratio is not None else None
            ),
            correlation_cost_pct=(
                round(correlation_cost, 4) if correlation_cost is not None else None
            ),
            per_member_var_95_pct=per_member,
            is_valid=True,
            warnings=warnings,
        )
