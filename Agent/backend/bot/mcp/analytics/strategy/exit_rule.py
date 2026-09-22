"""Reconstruct a bot's exit discipline, and compare two of them.

WHY THIS EXISTS. Two bots can be told apart by their results -- that is what
PnL correlation measures -- but results are an accident of the window they ran
in. What does not change with the window is HOW a bot decides a trade is over,
and that is recoverable from a public ledger with no market data at all: the
distance between entry and exit price, the shape of each tail, and how long
winners are held against losers. A portfolio of bots whose PnL happens to
offset while their exit rules are identical is not diversified; it is one
strategy that got lucky with timing, and the next regime will show that.

WHY PRICE AND NOT PnL. Every measurement below uses the direction-adjusted
price move, never realized PnL. PnL folds the exit decision together with
leverage and position size, so the same rule run at 5x and 50x would look like
two different strategies. Stripping those out is what makes the comparison a
comparison of BEHAVIOUR.

WHAT IS DELIBERATELY NOT INFERRED. A closed-trade ledger contains no cancelled
orders, no still-open positions and nothing hedged elsewhere, so this describes
the exits that happened -- never the rule that was configured. Where the
evidence runs out (too few trades, missing prices) the field stays None and
`is_valid` goes False, rather than a number being produced from a handful of
observations.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from Agent.backend.bot.mcp.schemas.bot_result import (
    ExitRuleFingerprint,
    ExitStyle,
    PositionSide,
    TradeLedgerItem,
)

# Fixed duration bands, coarse on purpose: the question is which ORDER OF
# MAGNITUDE a bot holds for (minutes / hours / days / weeks), and a finer grid
# would split one behaviour across neighbouring bins and invent modes.
HOLD_BUCKET_BOUNDS_MINUTES: Tuple[float, ...] = (
    60.0, 240.0, 720.0, 1440.0, 2880.0, 5760.0, 11520.0,
)
HOLD_BUCKET_LABELS: Tuple[str, ...] = (
    "<1h", "1-4h", "4-12h", "12-24h", "1-2d", "2-4d", "4-8d", ">8d",
)

# Names for `ExitRuleFingerprint.rule_vector`, in the order it is built. Kept
# beside the vector so a gap between two bots can be reported as "they differ
# most on how long losers are held" instead of "component 6".
RULE_COMPONENT_LABELS: Tuple[str, ...] = (
    "loss-to-win size",
    "win dispersion",
    "loss dispersion",
    "take-profit clustering",
    "stop-loss clustering",
    "hold asymmetry",
    "win tail",
    "loss tail",
)


def _ratio_component(value: Optional[float]) -> float:
    """Map a positive ratio onto [0, 1], symmetric about 1.0.

    Ratios like loss/win or p90/median live on (0, inf) with 1.0 as the
    neutral point, so a plain min-max would treat 0.5 and 2.0 -- mirror images
    of each other -- as wildly different distances from neutral. Squashing the
    LOG through arctan keeps that symmetry: 1.0 lands on 0.5, and x and 1/x
    land equally far either side of it.
    """
    if value is None or value <= 0.0 or not math.isfinite(value):
        return 0.5
    return max(0.0, min(1.0, 0.5 + math.atan(math.log(value)) / math.pi))


class ExitRuleAnalyzer:
    # Same floor as MonteCarloSimulationEngine.MIN_SAMPLE_SIZE: a ledger too
    # thin to bootstrap is too thin to characterise.
    MIN_TRADES = 10
    # Tails are measured per side, so each side needs its own sample. Below
    # this the median of that side is one or two trades wearing a statistic.
    MIN_PER_SIDE = 5
    # A rule firing at a fixed level lands its exits in a narrow band around
    # that level; slippage and fees widen it, so the band is relative rather
    # than absolute.
    CLUSTER_BAND = 0.15
    # Above this share inside the band, scattered discretionary exits stop
    # being a plausible explanation.
    CLUSTER_THRESHOLD = 0.5
    # Losers held this many times longer than winners is the cut-winners /
    # sit-on-losers pattern rather than ordinary variation.
    HOLD_ASYMMETRY_THRESHOLD = 1.5
    # A tail running this far past the typical win is letting winners run.
    RUN_WINNERS_TAIL_RATIO = 2.5
    # One duration band holding this much of the book is a time-based exit.
    TIME_EXIT_CONCENTRATION = 0.6
    # A second mode has to carry real weight before it counts as a second
    # behaviour rather than a bump.
    MODE_MIN_SHARE = 0.15

    # ------------------------------------------------------------------ #

    @staticmethod
    def _move_pct(trade: TradeLedgerItem) -> Optional[float]:
        """Direction-adjusted price move, in percent of the entry price."""
        entry, exit_price = trade.entry_price, trade.exit_price
        if not entry or not exit_price or entry <= 0.0:
            return None
        raw = (exit_price - entry) / entry * 100.0
        return -raw if trade.side == PositionSide.SHORT else raw

    @classmethod
    def _clustering(cls, values: np.ndarray) -> Tuple[Optional[float], float]:
        """Share of exits within +-CLUSTER_BAND of the median, and the median."""
        if values.size < cls.MIN_PER_SIDE:
            return None, float("nan")
        median = float(np.median(values))
        if median == 0.0:
            return None, median
        inside = np.abs(values - median) <= abs(median) * cls.CLUSTER_BAND
        return float(np.mean(inside)), median

    @classmethod
    def _hold_histogram(cls, minutes: np.ndarray) -> Tuple[Dict[str, int], List[float]]:
        counts = np.zeros(len(HOLD_BUCKET_LABELS), dtype=np.int64)
        indices = np.searchsorted(HOLD_BUCKET_BOUNDS_MINUTES, minutes, side="right")
        for index in indices:
            counts[int(index)] += 1
        total = float(counts.sum()) or 1.0
        return (
            {label: int(count) for label, count in zip(HOLD_BUCKET_LABELS, counts)},
            [round(float(count) / total, 6) for count in counts],
        )

    @classmethod
    def _modes(cls, shape: Sequence[float]) -> List[str]:
        """Duration bands that are local peaks carrying real weight.

        A local maximum alone is not a mode: a single stray trade in an
        otherwise empty band would qualify. Requiring MODE_MIN_SHARE of the
        book as well is what separates "the bot also does this" from noise.
        """
        modes: List[str] = []
        for index, share in enumerate(shape):
            if share < cls.MODE_MIN_SHARE:
                continue
            left = shape[index - 1] if index > 0 else -1.0
            right = shape[index + 1] if index + 1 < len(shape) else -1.0
            if share >= left and share >= right:
                modes.append(HOLD_BUCKET_LABELS[index])
        return modes

    # ------------------------------------------------------------------ #

    @classmethod
    def analyze(cls, trades: Sequence[TradeLedgerItem]) -> ExitRuleFingerprint:
        sample = len(trades)
        priced: List[Tuple[float, float]] = []
        for trade in trades:
            move = cls._move_pct(trade)
            if move is None:
                continue
            priced.append((move, float(trade.holding_time_minutes)))

        coverage = (len(priced) / sample) if sample else 0.0
        base = ExitRuleFingerprint(
            sample_size=sample,
            priced_trades=len(priced),
            price_coverage=round(coverage, 4),
        )
        if len(priced) < cls.MIN_TRADES:
            base.warnings.append(
                f"Only {len(priced)} closed trades carry both an entry and an exit "
                f"price (needs {cls.MIN_TRADES}); exit discipline is not characterised"
            )
            return base

        moves = np.array([item[0] for item in priced], dtype=np.float64)
        holds = np.array([item[1] for item in priced], dtype=np.float64)
        wins, losses = moves[moves > 0.0], moves[moves < 0.0]
        win_holds, loss_holds = holds[moves > 0.0], holds[moves < 0.0]
        base.win_count, base.loss_count = int(wins.size), int(losses.size)

        warnings: List[str] = []
        if coverage < 0.9:
            warnings.append(
                f"{1 - coverage:.0%} of closed trades are missing an entry or exit "
                "price and sit outside every figure here"
            )

        # --- tails -------------------------------------------------------
        if wins.size >= cls.MIN_PER_SIDE:
            base.win_move_median = round(float(np.median(wins)), 4)
            base.win_move_p90 = round(float(np.percentile(wins, 90)), 4)
            base.win_move_max = round(float(wins.max()), 4)
            mean_win = float(np.mean(wins))
            if mean_win > 0:
                base.win_dispersion = round(float(np.std(wins)) / mean_win, 4)
            if base.win_move_median:
                base.win_tail_ratio = round(
                    base.win_move_p90 / base.win_move_median, 4
                )
        else:
            warnings.append(
                f"Only {wins.size} winning trades; the profit-side exit is not "
                "characterised"
            )
        if losses.size >= cls.MIN_PER_SIDE:
            base.loss_move_median = round(float(np.median(losses)), 4)
            base.loss_move_p10 = round(float(np.percentile(losses, 10)), 4)
            base.loss_move_worst = round(float(losses.min()), 4)
            mean_loss = abs(float(np.mean(losses)))
            if mean_loss > 0:
                base.loss_dispersion = round(float(np.std(losses)) / mean_loss, 4)
            if base.loss_move_median:
                base.loss_tail_ratio = round(
                    base.loss_move_p10 / base.loss_move_median, 4
                )
        else:
            warnings.append(
                f"Only {losses.size} losing trades; the loss-side exit is not "
                "characterised"
            )
        if base.win_move_median and base.loss_move_median:
            base.loss_to_win_ratio = round(
                abs(base.loss_move_median) / base.win_move_median, 4
            )

        # --- hard TP / SL ------------------------------------------------
        tp_cluster, tp_level = cls._clustering(wins)
        sl_cluster, sl_level = cls._clustering(losses)
        base.take_profit_clustering = (
            round(tp_cluster, 4) if tp_cluster is not None else None
        )
        base.stop_loss_clustering = (
            round(sl_cluster, 4) if sl_cluster is not None else None
        )
        base.has_hard_take_profit = bool(
            tp_cluster is not None and tp_cluster >= cls.CLUSTER_THRESHOLD
        )
        base.has_hard_stop_loss = bool(
            sl_cluster is not None and sl_cluster >= cls.CLUSTER_THRESHOLD
        )
        if base.has_hard_take_profit:
            base.take_profit_level_pct = round(tp_level, 4)
        if base.has_hard_stop_loss:
            base.stop_loss_level_pct = round(sl_level, 4)

        # --- holding behaviour -------------------------------------------
        base.hold_median_minutes = round(float(np.median(holds)), 2)
        if win_holds.size:
            base.win_hold_median_minutes = round(float(np.median(win_holds)), 2)
        if loss_holds.size:
            base.loss_hold_median_minutes = round(float(np.median(loss_holds)), 2)
        if base.win_hold_median_minutes and base.loss_hold_median_minutes:
            base.hold_asymmetry = round(
                base.loss_hold_median_minutes / base.win_hold_median_minutes, 4
            )
        base.hold_buckets, base.hold_shape = cls._hold_histogram(holds)
        base.hold_modes = cls._modes(base.hold_shape)
        base.is_multi_modal = len(base.hold_modes) > 1

        # --- label --------------------------------------------------------
        patterns: List[str] = []
        evidence: List[str] = []
        if base.has_hard_take_profit:
            patterns.append("FIXED_TARGET")
            evidence.append(
                f"{base.take_profit_clustering:.0%} of winning exits land within 15% "
                f"of {base.take_profit_level_pct:+.2f}% -- a fixed profit target"
            )
        if base.has_hard_stop_loss:
            patterns.append("PROTECTIVE_STOP")
            evidence.append(
                f"{base.stop_loss_clustering:.0%} of losing exits land within 15% of "
                f"{base.stop_loss_level_pct:+.2f}% -- a fixed stop"
            )
        if (
            base.loss_to_win_ratio is not None
            and base.loss_to_win_ratio > 1.0
            and base.hold_asymmetry is not None
            and base.hold_asymmetry >= cls.HOLD_ASYMMETRY_THRESHOLD
        ):
            patterns.append("HOLD_LOSERS")
            evidence.append(
                f"Losses run {base.loss_to_win_ratio:.2f}x the size of wins and are "
                f"held {base.hold_asymmetry:.2f}x as long -- winners are cut, losers "
                "are sat on"
            )
        if (
            base.win_tail_ratio is not None
            and base.win_tail_ratio >= cls.RUN_WINNERS_TAIL_RATIO
            and base.loss_to_win_ratio is not None
            and base.loss_to_win_ratio <= 1.0
        ):
            patterns.append("RUN_WINNERS_CUT_LOSSES")
            evidence.append(
                f"Best winners run {base.win_tail_ratio:.1f}x the typical win while "
                f"losses stay at {base.loss_to_win_ratio:.2f}x of it"
            )
        top_share = max(base.hold_shape) if base.hold_shape else 0.0
        if (
            top_share >= cls.TIME_EXIT_CONCENTRATION
            and not base.has_hard_take_profit
            and not base.has_hard_stop_loss
        ):
            patterns.append("TIME_EXIT")
            evidence.append(
                f"{top_share:.0%} of trades close inside the "
                f"{HOLD_BUCKET_LABELS[int(np.argmax(base.hold_shape))]} band with no "
                "price-level rule visible -- exits look driven by elapsed time"
            )
        if base.is_multi_modal:
            patterns.append("MULTI_MODAL_HOLDING")
            evidence.append(
                "Two or more distinct holding regimes ("
                + ", ".join(base.hold_modes)
                + ") -- more than one behaviour running under one bot"
            )

        # Priority. HOLD_LOSERS leads because it is the finding that costs
        # money, and it routinely co-occurs with FIXED_TARGET: a small fixed
        # take-profit with no stop and losers held indefinitely is the grid /
        # martingale shape, and labelling that bot FIXED_TARGET would put the
        # harmless half of its behaviour in the headline. Below that, a
        # DETECTED level (a clustering measurement) outranks an INFERRED habit
        # (a tail-shape reading), because the former is evidence and the
        # latter is a characterisation. `patterns` keeps everything the single
        # label drops, so nothing is lost to this ordering.
        for candidate in (
            "HOLD_LOSERS",
            "FIXED_TARGET",
            "PROTECTIVE_STOP",
            "RUN_WINNERS_CUT_LOSSES",
            "TIME_EXIT",
        ):
            if candidate in patterns:
                base.exit_style = ExitStyle(candidate)
                break
        else:
            base.exit_style = ExitStyle.DISCRETIONARY
            evidence.append(
                "No fixed level and no consistent duration: exits are decided "
                "trade by trade"
            )

        base.rule_vector = [
            _ratio_component(base.loss_to_win_ratio),
            _ratio_component(base.win_dispersion),
            _ratio_component(base.loss_dispersion),
            base.take_profit_clustering if base.take_profit_clustering is not None else 0.5,
            base.stop_loss_clustering if base.stop_loss_clustering is not None else 0.5,
            _ratio_component(base.hold_asymmetry),
            _ratio_component(base.win_tail_ratio),
            _ratio_component(base.loss_tail_ratio),
        ]
        base.patterns = patterns
        base.evidence = evidence
        base.warnings = warnings
        base.is_valid = True
        return base

    # ------------------------------------------------------------------ #

    @classmethod
    def compare(
        cls, left: ExitRuleFingerprint, right: ExitRuleFingerprint
    ) -> Optional[Dict[str, object]]:
        """How alike two bots' exit discipline is, on [0, 1].

        TWO AXES, KEPT APART. `rule_distance` covers the eight dimensionless
        rule components; `hold_distance` covers how long positions are held.
        They answer different questions and are reported separately, because
        folding them into one number lets agreement on one mask disagreement
        on the other.

        WHY THE HEADLINE IS A MAX, NOT A MEAN. The question this metric exists
        to answer is "are these two running the same playbook", and that is a
        conjunction: same rules AND same cadence. Averaging lets two bots with
        identical holding periods but opposite loss discipline come back as
        half-similar, which is not a useful half of anything. Taking the worse
        of the two axes means a strong disagreement anywhere is enough to
        separate them, which is the behaviour a portfolio reader needs.

        WHY THE CADENCE HALF IS WASSERSTEIN, NOT HISTOGRAM INTERSECTION. The
        duration bands are ORDERED, and intersection throws that away: a bot
        holding 2-4 days and one holding 4-8 days share no bucket, so
        intersection calls them as different as a scalper and a bag-holder.
        The 1-D Wasserstein distance (here, the mean absolute gap between the
        two cumulative distributions, normalised by the number of steps)
        measures how far mass has to move along the band axis, so adjacent
        bands come out close and distant ones far -- which is what "similar
        holding behaviour" actually means.
        """
        if not left.is_valid or not right.is_valid:
            return None
        if len(left.rule_vector) != len(right.rule_vector) or not left.rule_vector:
            return None

        a = np.array(left.rule_vector, dtype=np.float64)
        b = np.array(right.rule_vector, dtype=np.float64)
        gaps = np.abs(a - b)
        # RMS over components, each already on [0, 1], so the result is too.
        rule_distance = float(np.linalg.norm(gaps) / math.sqrt(a.size))
        worst = int(np.argmax(gaps))

        hold_distance: Optional[float] = None
        if left.hold_shape and len(left.hold_shape) == len(right.hold_shape) > 1:
            left_cdf = np.cumsum(left.hold_shape)
            right_cdf = np.cumsum(right.hold_shape)
            steps = len(left.hold_shape) - 1
            hold_distance = float(
                np.sum(np.abs(left_cdf - right_cdf)) / steps
            )
            hold_distance = max(0.0, min(1.0, hold_distance))

        if hold_distance is None:
            distance = rule_distance
            driver = "RULE"
        elif hold_distance >= rule_distance:
            distance = hold_distance
            driver = "HOLDING_PERIOD"
        else:
            distance = rule_distance
            driver = "RULE"

        same_style = (
            left.exit_style is right.exit_style
            and left.exit_style is not ExitStyle.DISCRETIONARY
        )
        shared = sorted(set(left.patterns) & set(right.patterns))
        return {
            "rule_distance": round(rule_distance, 4),
            "hold_distance": round(hold_distance, 4) if hold_distance is not None else None,
            "distance": round(distance, 4),
            "similarity": round(1.0 - distance, 4),
            "driver": driver,
            "top_rule_component": RULE_COMPONENT_LABELS[worst],
            "top_rule_gap": round(float(gaps[worst]), 4),
            "same_exit_style": same_style,
            "shared_patterns": shared,
        }
