from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from Agent.backend.mcp.schemas.bot_result import (
    HorizonOutcome,
    SimulationResults,
    TradeLedgerItem,
)


class MonteCarloSimulationEngine:
    """Bounded IID/block bootstrap over realized trade PnL, owned by Logic 2."""

    # Số quan sát TỐI THIỂU để chạy bootstrap. Hạ từ 20 xuống 10 (18/09) --
    # con số 20 cũ là số tròn duy nhất trong cả class này không kèm một dòng
    # giải thích nào, trong khi chính dự án đã có sẵn một ngưỡng "đủ mẫu"
    # được định nghĩa và dùng ở chỗ khác: `PHASE_CONFIDENCE_ENOUGH_TRADES =
    # 10` ("N >= 10 -> đủ mẫu, được rút ra quy luật", xem
    # Agent/backend/web/report_page.py). Để hai ngưỡng lệch nhau nghĩa là
    # cùng một cỡ mẫu vừa "đủ để rút ra quy luật" ở mục phân tích pha, vừa
    # "không đủ để mô phỏng" ở Monte Carlo -- không có cơ sở nào biện minh
    # cho sự vênh đó.
    #
    # PHẠM VI ẢNH HƯỞNG đã ĐO trước khi đổi, không ước lượng: toàn bộ 31 bot
    # trong kho đã chấm đều có >= 33 lệnh (nhỏ nhất 33), nên KHÔNG một điểm
    # số hay phán quyết nào đang tồn tại bị thay đổi. Việc hạ ngưỡng chỉ mở
    # khoá cho những bot trước đây KHÔNG nhận được gì cả -- điển hình là bot
    # giấu sổ lệnh (OKX 60004) mà thứ duy nhất đo được là ~12 điểm vốn tuần.
    MIN_SAMPLE_SIZE = 10
    # 10 <= n < 20: chạy được, nhưng phải NÓI RÕ là mẫu mỏng (xem
    # `sample_is_thin` + `_THIN_SAMPLE_WARNING_VI` bên dưới). Lý do thống kê
    # thật, không phải sự thận trọng chung chung: một phân vị bootstrap chỉ
    # phân giải được tới cỡ 1/n, nên ở n=12 con số gọi là "phân vị 5" thực
    # chất đang được đọc ra từ 12 giá trị rời rạc -- ước lượng vẫn tính được
    # nhưng sai số chuẩn của nó rất lớn, đặc biệt ở hai đuôi.
    THIN_SAMPLE_SIZE = 20
    # Câu cảnh báo DUY NHẤT cho trạng thái mẫu mỏng -- tầng trình bày đọc
    # `sample_is_thin` rồi hiện đúng câu này, không tự viết lại.
    THIN_SAMPLE_WARNING_VI = (
        "Thin sample ({n} observations, below {thin}): the simulation still "
        "runs, but read it as an INDICATIVE RANGE rather than a firm estimate. "
        "A bootstrap percentile can only resolve to about 1/n, so at this "
        "sample size the figures in both tails (bad-case return, probability "
        "of ruin, bad-case drawdown) carry a large standard error."
    )
    MAX_ITERATIONS = 50_000
    MAX_HORIZON = 500
    BATCH_SIZE = 2_000

    # Extra horizons (SHORT/LONG) exist to show *how* an outcome moves with
    # horizon, not to re-measure it at full precision -- the MEDIUM horizon
    # already carries the precise, backward-compatible numbers everything
    # else in this codebase reads. Capping their iteration count keeps a
    # three-horizon run from costing three times as much wall clock time.
    SCENARIO_ITERATIONS_CAP = 3_000
    # Midpoint of the requested "~10-25% of the bot's own trades" band.
    SHORT_HORIZON_FRACTION = 0.15
    # Midpoint of the requested "2-5x the bot's own trades" band.
    LONG_HORIZON_MULTIPLIER = 3
    # A horizon is judged "healthy" at better-than-coin-flip odds of ending
    # ahead. This is only used to describe how sensitive the record is to
    # horizon -- it never feeds the QC verdict.
    HORIZON_OK_THRESHOLD_PCT = 50.0

    # `horizon_exceeds_observed` must only fire on a *meaningful*
    # extrapolation, never on floating-point noise. With the default
    # (caller leaves `--horizon` blank), `horizon_calendar_days` is derived
    # from `horizon / trades_per_day` where `horizon == len(trades)` and
    # `trades_per_day == len(trades) / observed_span_days` -- i.e.
    # `horizon_calendar_days` and `observed_span_days` are the SAME
    # quantity computed via two different float expressions. They are
    # mathematically equal but can differ in the last bit (observed on a
    # real bot: a 1e-14 day gap), so a bare `>` comparison flags every bot
    # that uses the default horizon, not just genuine overruns. Requiring
    # the gap to clear both a relative floor (percent of the observed span)
    # and an absolute floor (whole days) keeps rounding noise silent while
    # still catching real extrapolation, e.g. a 500-trade horizon requested
    # against a 72-trade/57-day history (~7x, far past both floors).
    HORIZON_EXCEEDS_OBSERVED_REL_THRESHOLD = 0.02
    HORIZON_EXCEEDS_OBSERVED_ABS_THRESHOLD_DAYS = 1.0

    STABLE_LABEL = "STABLE ACROSS HORIZONS"
    SHORT_ONLY_LABEL = "HOLDS ONLY AT SHORT HORIZON"
    NEEDS_TIME_LABEL = "NEEDS MORE TIME"

    @staticmethod
    def loss_streak_baseline_probability(
        q: float, horizon_trades: int, streak_length: int
    ) -> float:
        """Exact P(>= 1 run of `streak_length` consecutive losses) over
        `horizon_trades` *independent* Bernoulli trials with per-trade loss
        probability `q`.

        Why this exists: the probability that a run of independent trades
        contains a losing streak of length k rises monotonically with the
        number of trades. A bot that has simply traded a lot is therefore
        near-certain to show a long loss streak somewhere in its history even
        when every trade is an independent draw from its own win rate -- a
        90%-win-rate bot with 500 trades can easily show a 65% chance of a
        5-in-a-row losing streak, and that number is telling you about the
        length of the ledger, not about risk. This is the "how often would
        this happen anyway, from sample size alone" baseline: the simulated
        raw probability minus this number is what is left over to actually
        indicate streak-dependence (herding / martingale-like clustering) in
        this specific bot's trades.

        Computed by exact dynamic programming (no sampling, so no noise to
        argue with) over the length of the current loss run: states
        0..streak_length-1 are "not hit yet, current run has this length",
        plus one absorbing state for "already hit at least once". With
        horizon_trades <= 500 and streak_length <= 10 this is O(horizon *
        streak_length), trivially cheap.
        """
        if streak_length <= 0:
            return 1.0
        if horizon_trades < streak_length:
            return 0.0
        q = max(0.0, min(1.0, q))
        if q <= 0.0:
            return 0.0
        win = 1.0 - q
        # dist[i]: probability mass currently sitting at "run length i, not
        # yet hit". `hit` is the absorbing probability of having reached
        # `streak_length` at some point so far.
        dist = [0.0] * streak_length
        dist[0] = 1.0
        hit = 0.0
        for _ in range(horizon_trades):
            new_dist = [0.0] * streak_length
            for length, mass in enumerate(dist):
                if mass <= 0.0:
                    continue
                # A win resets the run to zero length, from any state.
                new_dist[0] += mass * win
                # A loss extends the run; once it reaches streak_length the
                # mass leaves the tracked states for good (absorbed into hit).
                extended = length + 1
                if extended >= streak_length:
                    hit += mass * q
                else:
                    new_dist[extended] += mass * q
            dist = new_dist
        return min(1.0, hit)

    @staticmethod
    def _trade_cadence(
        trades: List[TradeLedgerItem],
    ) -> Tuple[Optional[float], Optional[float]]:
        """(trades_per_day, observed_span_days) from the ledger's own
        open/close timestamps.

        Returns (None, None) rather than guessing whenever the ledger cannot
        support the estimate: fewer than two trades give no elapsed time to
        measure a rate over, and a zero observed span (every trade closes at
        the same instant) would otherwise imply an undefined/infinite rate.
        """
        if len(trades) < 2:
            return None, None
        span_ms = max(t.close_time for t in trades) - min(t.open_time for t in trades)
        if span_ms <= 0:
            return None, 0.0
        observed_span_days = span_ms / 86_400_000.0
        return len(trades) / observed_span_days, observed_span_days

    @classmethod
    def _horizon_exceeds_observed(
        cls,
        horizon_calendar_days: Optional[float],
        observed_span_days: Optional[float],
    ) -> Optional[bool]:
        """True only when the simulated horizon runs meaningfully past the
        calendar span actually observed -- see
        `HORIZON_EXCEEDS_OBSERVED_REL_THRESHOLD`'s own comment for why a
        bare `>` on these two numbers is unsafe (they are the same quantity
        under the default horizon and can differ only by float noise).

        Both a relative floor (percent of the observed span) and an
        absolute floor (whole days) must be cleared, so a long-lived bot's
        genuinely small overrun does not fire on relative percent alone,
        and a short-lived bot's tiny absolute gap does not fire on absolute
        days alone.
        """
        if horizon_calendar_days is None or observed_span_days is None:
            return None
        gap_days = horizon_calendar_days - observed_span_days
        rel_threshold_days = (
            observed_span_days * cls.HORIZON_EXCEEDS_OBSERVED_REL_THRESHOLD
        )
        return (
            gap_days > rel_threshold_days
            and gap_days > cls.HORIZON_EXCEEDS_OBSERVED_ABS_THRESHOLD_DAYS
        )

    @classmethod
    def run_simulation(
        cls,
        trades: List[TradeLedgerItem],
        initial_equity: Optional[float],
        iterations: int = 10_000,
        horizon_trades: Optional[int] = None,
        block_bootstrap: bool = True,
        seed: Optional[int] = None,
        capital_basis: str = "CURRENT_AUM",
        current_drawdown_pct: Optional[float] = None,
        trade_frequency_per_day: Optional[float] = None,
    ) -> SimulationResults:
        iterations = min(max(int(iterations), 1), cls.MAX_ITERATIONS)
        # Replay the bot's own history length by default: asking "what could the
        # next 500 trades look like" for a bot with 33 fills invents a future far
        # longer than anything observed. A caller can still pin a horizon.
        horizon_basis = "OWN_TRADE_COUNT" if horizon_trades is None else "CALLER_SET"
        requested = horizon_trades if horizon_trades is not None else len(trades)
        horizon = min(max(int(requested), 1), cls.MAX_HORIZON)
        method = "STATIONARY_BOOTSTRAP" if block_bootstrap else "IID_BOOTSTRAP"
        warnings: List[str] = []
        if (
            len(trades) < cls.MIN_SAMPLE_SIZE
            or initial_equity is None
            or initial_equity <= 0
        ):
            if len(trades) < cls.MIN_SAMPLE_SIZE:
                warnings.append(
                    f"At least {cls.MIN_SAMPLE_SIZE} valid trades are required; got {len(trades)}"
                )
            if initial_equity is None or initial_equity <= 0:
                warnings.append(
                    "Positive reference equity is required for drawdown probabilities"
                )
            return SimulationResults(
                simulation_method=method,
                iterations=0,
                sample_size=len(trades),
                horizon_trades=horizon,
                return_basis="ABSOLUTE_PNL_RELATIVE_TO_EQUITY",
                capital_basis=capital_basis,
                is_valid=False,
                warnings=warnings,
            )

        sample_is_thin = len(trades) < cls.THIN_SAMPLE_SIZE
        if sample_is_thin:
            warnings.append(
                cls.THIN_SAMPLE_WARNING_VI.format(
                    n=len(trades), thin=cls.THIN_SAMPLE_SIZE
                )
            )

        pnls = np.asarray([trade.realized_pnl for trade in trades], dtype=np.float64)

        # Translate the trade-count horizon into calendar time using this
        # bot's own cadence, so a reader can tell "500 trades" apart for a
        # scalper (days) versus a swing trader (years), and can tell when a
        # conclusion at this horizon runs past the data actually observed.
        trades_per_day, observed_span_days = cls._trade_cadence(trades)
        horizon_calendar_days = (
            horizon / trades_per_day
            if trades_per_day is not None and trades_per_day > 0
            else None
        )
        horizon_exceeds_observed = cls._horizon_exceeds_observed(
            horizon_calendar_days, observed_span_days
        )

        # MEDIUM is computed first and exactly as this method always has --
        # same seed, same iterations, same horizon -- so every existing
        # top-level field on SimulationResults is bit-identical to before
        # multi-horizon support existed. SHORT and LONG are additional,
        # independent runs (each reseeds its own RNG from `seed`) layered on
        # top; they cannot perturb MEDIUM's numbers because they never share
        # its RNG instance or its call to `_simulate_horizon`.
        stats = cls._simulate_horizon(
            pnls=pnls,
            initial_equity=initial_equity,
            horizon=horizon,
            iterations=iterations,
            seed=seed,
            block_bootstrap=block_bootstrap,
            current_drawdown_pct=current_drawdown_pct,
            trade_frequency_per_day=trade_frequency_per_day,
        )

        horizon_scenarios = cls._run_horizon_scenarios(
            pnls=pnls,
            initial_equity=initial_equity,
            iterations=iterations,
            seed=seed,
            block_bootstrap=block_bootstrap,
            current_drawdown_pct=current_drawdown_pct,
            trade_frequency_per_day=trade_frequency_per_day,
            medium_horizon=horizon,
            medium_stats=stats,
        )
        sensitivity, stability_label = cls._classify_horizon_stability(
            horizon_scenarios
        )

        return SimulationResults(
            simulation_method=method,
            iterations=iterations,
            sample_size=len(trades),
            horizon_trades=horizon,
            return_basis="ABSOLUTE_PNL_RELATIVE_TO_EQUITY",
            capital_basis=capital_basis,
            capital_at_risk=initial_equity,
            is_valid=True,
            sample_is_thin=sample_is_thin,
            horizon_basis=horizon_basis,
            warnings=warnings,
            horizon_scenarios=horizon_scenarios,
            horizon_sensitivity=sensitivity,
            horizon_stability_label=stability_label,
            trades_per_day=trades_per_day,
            horizon_calendar_days=horizon_calendar_days,
            observed_span_days=observed_span_days,
            horizon_exceeds_observed=horizon_exceeds_observed,
            **stats,
        )

    @classmethod
    def _run_horizon_scenarios(
        cls,
        pnls: np.ndarray,
        initial_equity: float,
        iterations: int,
        seed: Optional[int],
        block_bootstrap: bool,
        current_drawdown_pct: Optional[float],
        trade_frequency_per_day: Optional[float],
        medium_horizon: int,
        medium_stats: Dict[str, object],
    ) -> List[HorizonOutcome]:
        """Build the SHORT / MEDIUM / LONG comparison for one bot.

        All three horizons are sized off the bot's own trade count (`len(pnls)`),
        not off a caller-supplied `horizon_trades` override, because the point
        of this comparison is "how does this specific bot's own cadence behave
        at different horizons" -- a caller pinning an unrelated horizon for the
        legacy fields should not change what this comparison means.
        """
        n = len(pnls)
        medium = min(max(n, 1), cls.MAX_HORIZON)
        short = max(
            1,
            min(medium - 1 if medium > 1 else 1, round(n * cls.SHORT_HORIZON_FRACTION)),
        )
        short = max(1, short)
        long_ = min(
            cls.MAX_HORIZON, max(medium, round(n * cls.LONG_HORIZON_MULTIPLIER))
        )
        if long_ <= medium and medium < cls.MAX_HORIZON:
            long_ = min(cls.MAX_HORIZON, medium + 1)

        scenario_iterations = min(iterations, cls.SCENARIO_ITERATIONS_CAP)

        outcomes: List[HorizonOutcome] = []
        for label, target_horizon in (
            ("SHORT", short),
            ("MEDIUM", medium),
            ("LONG", long_),
        ):
            if label == "MEDIUM" and target_horizon == medium_horizon:
                # Reuse the exact run already performed above instead of paying
                # for a second full-precision pass over the same horizon.
                stats = medium_stats
                run_iterations = iterations
            else:
                stats = cls._simulate_horizon(
                    pnls=pnls,
                    initial_equity=initial_equity,
                    horizon=target_horizon,
                    iterations=scenario_iterations,
                    seed=seed,
                    block_bootstrap=block_bootstrap,
                    current_drawdown_pct=current_drawdown_pct,
                    trade_frequency_per_day=trade_frequency_per_day,
                )
                run_iterations = scenario_iterations
            loss_prob = stats["p_loss_after_horizon"]
            outcomes.append(
                HorizonOutcome(
                    label=label,
                    horizon_trades=target_horizon,
                    iterations=run_iterations,
                    is_valid=True,
                    profit_pct_p05=stats["profit_pct_p05"],
                    profit_pct_p50=stats["profit_pct_p50"],
                    profit_pct_p95=stats["profit_pct_p95"],
                    median_max_drawdown=stats["median_max_drawdown"],
                    p_loss_after_horizon=loss_prob,
                    p_ruin=stats["p_ruin"],
                    mar_ratio_median=stats["mar_ratio_median"],
                    probability_of_profit=(
                        100.0 - loss_prob if loss_prob is not None else None
                    ),
                )
            )
        return outcomes

    @classmethod
    def _classify_horizon_stability(
        cls, scenarios: List[HorizonOutcome]
    ) -> tuple[Optional[float], Optional[str]]:
        """Summarize how much the SHORT vs LONG horizons disagree.

        This is deliberately about *description*, not *verdict*: a bot that
        wins fast and burns slow is not lying about either number, it is a
        strategy meant to be run short. Forcing one label onto both readings
        would hide exactly the fact the user needs to see -- that the same
        bot can be safe under one usage pattern and dangerous under another.
        Step 3 (the QC verdict) intentionally does not consume this yet.
        """
        by_label = {s.label: s for s in scenarios}
        short = by_label.get("SHORT")
        long_ = by_label.get("LONG")
        if (
            short is None
            or long_ is None
            or short.probability_of_profit is None
            or long_.probability_of_profit is None
        ):
            return None, None

        sensitivity = (
            abs(long_.probability_of_profit - short.probability_of_profit) / 100.0
        )
        short_ok = short.probability_of_profit >= cls.HORIZON_OK_THRESHOLD_PCT
        long_ok = long_.probability_of_profit >= cls.HORIZON_OK_THRESHOLD_PCT

        if short_ok and not long_ok:
            label = cls.SHORT_ONLY_LABEL
        elif not short_ok and long_ok:
            label = cls.NEEDS_TIME_LABEL
        else:
            # Either healthy at every horizon or unhealthy at every horizon --
            # in both cases the horizon choice does not change the picture,
            # so the conclusion (whatever it is) is not an artifact of
            # measuring at one arbitrary length.
            label = cls.STABLE_LABEL
        return sensitivity, label

    @classmethod
    def _simulate_horizon(
        cls,
        pnls: np.ndarray,
        initial_equity: float,
        horizon: int,
        iterations: int,
        seed: Optional[int],
        block_bootstrap: bool,
        current_drawdown_pct: Optional[float],
        trade_frequency_per_day: Optional[float],
    ) -> Dict[str, object]:
        """Run the bootstrap for exactly one horizon and return its statistics.

        This is the original single-horizon body of `run_simulation`, moved
        here unchanged so it can be called once per horizon. Nothing about the
        math changed -- only that it is now a function instead of being
        inlined -- which is what keeps the MEDIUM horizon's numbers identical
        to what this engine produced before multi-horizon support existed.
        """
        rng = np.random.default_rng(seed)
        # Politis & Romano (1994) stationary bootstrap. A fixed block length has
        # to be guessed, and the guess shows up in the answer; here each block
        # ends with probability 1/L, so lengths are geometric with mean L and no
        # single choice of L is baked in. L = n^(1/3) is the standard rate.
        expected_block = max(2, min(int(round(len(pnls) ** (1 / 3))), len(pnls) // 2))
        restart_probability = 1.0 / expected_block
        all_terminal: List[np.ndarray] = []
        all_gross_profit: List[np.ndarray] = []
        all_gross_loss: List[np.ndarray] = []
        all_max_dd: List[np.ndarray] = []
        counts = {
            "mdd10": 0,
            "mdd15": 0,
            "mdd25": 0,
            "loss": 0,
            "streak5": 0,
            "streak10": 0,
            "recovery30d": 0,
            "current_dd": 0,
            "ruin": 0,
        }

        remaining = iterations
        while remaining:
            batch = min(cls.BATCH_SIZE, remaining)
            if block_bootstrap and len(pnls) >= 4:
                # Walk forward inside the ledger, restarting at a random trade
                # with probability 1/L. Wrapping keeps every trade equally
                # likely to appear, which a truncated walk would not.
                restarts = rng.random((batch, horizon)) < restart_probability
                restarts[:, 0] = True
                fresh = rng.integers(0, len(pnls), size=(batch, horizon))
                # Position of the most recent restart, per path: a running max
                # over restart positions replaces a column-by-column walk, which
                # cost twelve seconds a bot.
                positions = np.arange(horizon)
                block_start = np.maximum.accumulate(
                    np.where(restarts, positions, 0), axis=1
                )
                offsets = positions - block_start
                origins = np.take_along_axis(fresh, block_start, axis=1)
                indices = (origins + offsets) % len(pnls)
            else:
                indices = rng.integers(0, len(pnls), size=(batch, horizon))
            sim_pnls = pnls[indices]
            equity = initial_equity + np.cumsum(sim_pnls, axis=1)
            equity = np.concatenate(
                (np.full((batch, 1), initial_equity), equity), axis=1
            )
            peaks = np.maximum.accumulate(equity, axis=1)
            drawdown = np.clip((peaks - equity) / np.maximum(peaks, 1e-12), 0.0, 1.0)
            max_dd = np.max(drawdown, axis=1) * 100.0
            ruined = np.any(equity <= 0.0, axis=1)
            terminal = equity[:, -1]

            loss_run = np.zeros(batch, dtype=np.int16)
            max_loss_run = np.zeros(batch, dtype=np.int16)
            underwater_run = np.zeros(batch, dtype=np.int16)
            max_underwater_run = np.zeros(batch, dtype=np.int16)
            for column in range(horizon):
                is_loss = sim_pnls[:, column] < 0
                loss_run = np.where(is_loss, loss_run + 1, 0)
                max_loss_run = np.maximum(max_loss_run, loss_run)
                underwater = drawdown[:, column + 1] > 0
                underwater_run = np.where(underwater, underwater_run + 1, 0)
                max_underwater_run = np.maximum(max_underwater_run, underwater_run)

            counts["ruin"] += int(np.sum(ruined))
            counts["mdd10"] += int(np.sum(max_dd > 10.0))
            counts["mdd15"] += int(np.sum(max_dd > 15.0))
            counts["mdd25"] += int(np.sum(max_dd > 25.0))
            counts["loss"] += int(np.sum(terminal < initial_equity))
            counts["streak5"] += int(np.sum(max_loss_run >= 5))
            counts["streak10"] += int(np.sum(max_loss_run >= 10))
            if trade_frequency_per_day and trade_frequency_per_day > 0:
                counts["recovery30d"] += int(
                    np.sum(max_underwater_run / trade_frequency_per_day > 30.0)
                )
            if current_drawdown_pct is not None:
                counts["current_dd"] += int(np.sum(max_dd > current_drawdown_pct))
            all_terminal.append(terminal)
            all_max_dd.append(max_dd)
            gains = np.where(sim_pnls > 0, sim_pnls, 0.0).sum(axis=1)
            losses = np.where(sim_pnls < 0, -sim_pnls, 0.0).sum(axis=1)
            all_gross_profit.append(gains)
            all_gross_loss.append(losses)
            remaining -= batch

        terminal_values = np.concatenate(all_terminal)
        max_drawdowns = np.concatenate(all_max_dd)
        gross_profits = np.concatenate(all_gross_profit)
        gross_losses = np.concatenate(all_gross_loss)

        def probability(name: str) -> float:
            return counts[name] / iterations * 100.0

        recovery_probability = (
            probability("recovery30d")
            if trade_frequency_per_day and trade_frequency_per_day > 0
            else None
        )
        current_dd_probability = (
            probability("current_dd") if current_drawdown_pct is not None else None
        )
        loss_probability = probability("loss")

        # Raw simulated streak probabilities, and the exact independent-trial
        # baseline for this bot's own per-trade loss rate, at this horizon.
        # See `loss_streak_baseline_probability` for why the baseline matters:
        # a bot that has simply traded a lot is near-certain to show a loss
        # streak somewhere in its history even with no real dependence
        # between losses, so the raw number alone conflates "traded a lot"
        # with "loses in a risky, clustered way". Estimated from this same
        # bot's own realized trades (not a caller-supplied win rate) so the
        # baseline always matches the exact sequence being resampled.
        streak5_probability = probability("streak5")
        streak10_probability = probability("streak10")
        per_trade_loss_probability = float(np.mean(pnls < 0)) if len(pnls) else 0.0
        streak5_baseline = (
            cls.loss_streak_baseline_probability(per_trade_loss_probability, horizon, 5)
            * 100.0
        )
        streak10_baseline = (
            cls.loss_streak_baseline_probability(
                per_trade_loss_probability, horizon, 10
            )
            * 100.0
        )
        streak5_excess = max(0.0, streak5_probability - streak5_baseline)
        streak10_excess = max(0.0, streak10_probability - streak10_baseline)

        # Profit of each run as a percent of the capital it started with.
        profits = (terminal_values - initial_equity) / initial_equity * 100.0
        profit_pct = [
            float(np.min(profits)),
            *(float(np.percentile(profits, q)) for q in (5, 10, 25, 50, 75, 90, 95)),
            float(np.max(profits)),
        ]

        # VaR is the loss the worst 5 % (1 %) of runs exceed; CVaR is the average
        # loss inside that tail. Reported as losses, so a positive number means
        # money lost.
        var95 = -float(np.percentile(profits, 5))
        var99 = -float(np.percentile(profits, 1))
        tail95 = profits[profits <= np.percentile(profits, 5)]
        tail99 = profits[profits <= np.percentile(profits, 1)]
        cvar95 = -float(np.mean(tail95)) if len(tail95) else None
        cvar99 = -float(np.mean(tail99)) if len(tail99) else None

        # Return per unit of drawdown, the ratio a capital allocator actually
        # sizes on. Undefined where a run had no drawdown at all.
        usable = max_drawdowns > 1e-9
        mar_median = mar_p05 = None
        if usable.any():
            mar = profits[usable] / max_drawdowns[usable]
            mar_median = float(np.median(mar))
            mar_p05 = float(np.percentile(mar, 5))

        pf_median = pf_p05 = None
        payable = gross_losses > 1e-9
        if payable.any():
            factors = gross_profits[payable] / gross_losses[payable]
            pf_median = float(np.median(factors))
            pf_p05 = float(np.percentile(factors, 5))

        return {
            "p_ruin": probability("ruin"),
            "p_mdd_gt_10": probability("mdd10"),
            "p_mdd_gt_15": probability("mdd15"),
            "p_mdd_gt_25": probability("mdd25"),
            "p_loss_after_horizon": loss_probability,
            "p_loss_after_500_trades": loss_probability if horizon == 500 else None,
            "p_recovery_gt_30d": recovery_probability,
            "p_5_loss_streak": streak5_probability,
            "p_10_loss_streak": streak10_probability,
            "p_5_loss_streak_baseline": streak5_baseline,
            "p_10_loss_streak_baseline": streak10_baseline,
            "p_5_loss_streak_excess": streak5_excess,
            "p_10_loss_streak_excess": streak10_excess,
            "p_capital_loss_gt_current_dd": current_dd_probability,
            "profit_pct_worst": profit_pct[0],
            "profit_pct_p05": profit_pct[1],
            "profit_pct_p10": profit_pct[2],
            "profit_pct_p25": profit_pct[3],
            "profit_pct_p50": profit_pct[4],
            "profit_pct_p75": profit_pct[5],
            "profit_pct_p90": profit_pct[6],
            "profit_pct_p95": profit_pct[7],
            "profit_pct_best": profit_pct[8],
            "worst_terminal_equity": float(np.min(terminal_values)),
            "var_95_pct": var95,
            "var_99_pct": var99,
            "cvar_95_pct": cvar95,
            "cvar_99_pct": cvar99,
            "median_max_drawdown": float(np.median(max_drawdowns)),
            "p90_max_drawdown": float(np.percentile(max_drawdowns, 90)),
            "mar_ratio_median": mar_median,
            "mar_ratio_p05": mar_p05,
            "profit_factor_median": pf_median,
            "profit_factor_p05": pf_p05,
            "probability_of_profit": 100.0 - loss_probability,
            "expected_terminal_equity": float(np.mean(terminal_values)),
            "median_terminal_equity": float(np.median(terminal_values)),
            "p10_outcome": float(np.percentile(terminal_values, 10)),
            "p50_outcome": float(np.percentile(terminal_values, 50)),
            "p90_outcome": float(np.percentile(terminal_values, 90)),
            "p95_max_drawdown": float(np.percentile(max_drawdowns, 95)),
            "p99_max_drawdown": float(np.percentile(max_drawdowns, 99)),
            "worst_percentile_drawdown": float(np.max(max_drawdowns)),
        }
