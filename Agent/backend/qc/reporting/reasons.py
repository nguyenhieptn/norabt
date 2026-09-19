from __future__ import annotations

from typing import List, Optional

from Agent.backend.qc.scoring.verdict import (
    VERDICT_LOW_DD_GOOD_Q,
    VERDICT_LOW_DD_WEAK_Q,
)

DIMENSION_VI = {
    "market_alignment": "against the market trend",
    "performance_quality": "weak performance quality",
    "return_r_quality": "poor return distribution",
    "drawdown_risk": "deep drawdown",
    "tail_risk": "high tail risk",
    "leverage_exposure": "large leverage and exposure",
    "behavioral_risk": "dangerous trading behaviour",
    "strategy_drift": "strategy not durable across market phases",
    "liquidity_execution": "position large relative to liquidity",
    "portfolio_risk": "concentrated portfolio",
}

TREND_VI = {
    "BULLISH": "up",
    "BEARISH": "down",
    "SIDEWAYS": "sideways",
    "BREAKOUT_BULL": "breakout up",
    "BREAKOUT_BEAR": "breakout down",
    "UNKNOWN": "unclear",
}
VOL_VI = {
    "COMPRESSED": "compressed volatility",
    "NORMAL": "normal volatility",
    "EXPANDING": "expanding volatility",
    "EXTREME": "extreme volatility",
    "UNKNOWN": "volatility unclear",
}
LIQ_VI = {
    "DEEP": "deep liquidity",
    "ADEQUATE": "adequate liquidity",
    "THIN": "thin liquidity",
    "ILLIQUID": "near-illiquid",
    "UNKNOWN": "liquidity unclear",
}
FLOW_VI = {
    "BUY_PRESSURE": "buy pressure",
    "SELL_PRESSURE": "sell pressure",
    "NEUTRAL": "balanced flow",
    "UNKNOWN": "flow unclear",
}
TIER_VI = {
    "EMERGENCY": "EMERGENCY",
    "CRITICAL": "CRITICAL",
    "HIGH": "HIGH",
    "ELEVATED": "ELEVATED",
    "WATCH": "WATCH",
    # "HEALTHY" (RiskTier.HEALTHY), not "SAFE" -- that exact string is now
    # reserved for the (removed) old 4-bucket verdict label, and a per-
    # dimension risk tier is a different, more granular axis than the
    # two-axis bot-level verdict (see scoring/verdict.py's module docstring).
    "HEALTHY": "HEALTHY",
    "UNKNOWN": "UNMEASURED",
}


def regime_label_vi(trend: Optional[str], volatility: Optional[str]) -> str:
    if not trend or trend == "UNKNOWN":
        return "Market regime not yet determined"
    return f"{TREND_VI.get(trend, trend).capitalize()}, {VOL_VI.get(volatility or 'UNKNOWN', '')}"


def explain_vi(row) -> str:
    """State plainly why this bot got this ranking, with concrete numbers."""
    causes: List[str] = []

    if row.status != "EVALUATED":
        return "Could not be assessed because the input data is invalid."

    if row.wiped_out:
        causes.append(
            "the weekly equity curve touched zero, meaning the account was wiped out at least once"
        )

    if row.loss_representativeness == "UNREPRESENTATIVE" and row.open_loss:
        shift = ""
        if (
            row.booked_profit_factor is not None
            and row.marked_profit_factor is not None
        ):
            shift = (
                f", closing everything would drop the profit factor from {row.booked_profit_factor:.2f} "
                f"to {row.marked_profit_factor:.2f}"
            )
        elif row.marked_profit_factor is not None:
            shift = (
                f", it has never closed a loss so the profit factor is meaningless; "
                f"closing everything now would leave the profit factor at only "
                f"{row.marked_profit_factor:.2f}"
            )
        pct = (
            f" ({row.open_loss_to_capital_pct:.0f}% of capital)"
            if row.open_loss_to_capital_pct
            else ""
        )
        causes.append(f"holding {row.open_loss:,.0f} USDT of unrealised loss{pct}{shift}")

    if row.p_ruin and row.p_ruin >= 5.0:
        causes.append(f"probability of ruin {row.p_ruin:.0f}% over the next 500 trades")

    scores = row.dimension_scores or {}
    for name, score in sorted(scores.items(), key=lambda kv: -kv[1]):
        if score < 60 or len(causes) >= 4:
            continue
        label = DIMENSION_VI.get(name, name)
        if name == "behavioral_risk":
            causes.append(f"{label} (score {score:.0f})")
        elif name == "drawdown_risk" and row.max_drawdown_pct is not None:
            causes.append(f"{label}: max {row.max_drawdown_pct:.1f}%")
        elif name == "leverage_exposure" and row.leverage:
            causes.append(f"{label}: leverage {row.leverage:.0f}x")
        elif name == "market_alignment" and row.market:
            causes.append(
                f"{label} ({TREND_VI.get(row.market.trend, row.market.trend)})"
            )
        elif name == "tail_risk" and row.p95_max_drawdown is not None:
            causes.append(f"{label}: P95 drawdown {row.p95_max_drawdown:.0f}%")
        else:
            causes.append(f"{label} (score {score:.0f})")

    if not causes:
        if row.risk_tier == "UNKNOWN":
            missing = len(row.unknown_dimensions or [])
            return f"Not enough evidence to conclude: {missing}/10 assessed dimensions are missing data."
        return "No risk dimension crossed the warning threshold."

    text = "; ".join(causes)
    if row.confidence is not None and row.confidence < 50:
        text += f". Confidence is only {row.confidence:.0f}%, so more evidence is needed before acting on this"
    return text[0].upper() + text[1:] + "."


def computed_summary_vi(row) -> str:
    """Condensed computed result: what was measured and what number it came to."""
    if row.status != "EVALUATED":
        return "—"
    parts: List[str] = []
    if row.profit_factor is not None:
        if (
            row.marked_profit_factor is not None
            and row.loss_representativeness == "UNREPRESENTATIVE"
        ):
            parts.append(f"PF {row.profit_factor:.2f}→{row.marked_profit_factor:.2f}")
        else:
            parts.append(f"PF {row.profit_factor:.2f}")
    elif row.marked_profit_factor is not None:
        parts.append(f"PF —→{row.marked_profit_factor:.2f}")

    if row.max_drawdown_pct is not None:
        parts.append(f"DD {row.max_drawdown_pct:.1f}%")
    elif row.max_drawdown_abs:
        parts.append(f"DD {row.max_drawdown_abs / 1000:,.0f}k$")

    if row.p95_max_drawdown is not None:
        parts.append(f"P95 {row.p95_max_drawdown:.0f}%")
    # Only state numbers that carry signal; a zero would only dilute the table.
    if row.p_ruin:
        parts.append(f"ruin {row.p_ruin:.0f}%")
    if row.open_loss:
        parts.append(f"open loss {row.open_loss / 1000:,.0f}k$")
    if row.gross_exposure:
        parts.append(f"exp {row.gross_exposure / 1000:,.0f}k$")
    return " · ".join(parts) if parts else "not yet computed"


def score_story_vi(row) -> str:
    """Explain the number: how it was produced and what capped it."""
    if row.risk_score is None:
        return "The score could not be computed."
    avg = row.weighted_average
    floor = row.veto_floor
    decided = row.score_decided_by or "WEIGHTED_AVERAGE"

    if decided == "EMERGENCY_OVERRIDE":
        head = (
            f"The score {row.risk_score:.1f} is the maximum, set by the emergency rule, "
            f"overriding the weighted average of {avg:.1f}"
        )
    elif decided == "VETO_FLOOR" and floor is not None:
        head = (
            f"The score {row.risk_score:.1f} comes from the veto floor {floor:.0f}, not the average: "
            f"the weighted average across the 10 dimensions is only {avg:.1f}"
        )
    else:
        head = (
            f"The score {row.risk_score:.1f} is exactly the weighted average across the assessed "
            f"dimensions; no veto was triggered"
        )
    if row.veto_reasons:
        head += f". Veto triggered by: {'; '.join(row.veto_reasons)}"
    return head + "."


PHASE_VI = {
    "UPTREND_CALM": "Uptrend, calm",
    "UPTREND_VOLATILE": "Uptrend, volatile",
    "DOWNTREND_CALM": "Downtrend, calm",
    "DOWNTREND_VOLATILE": "Downtrend, volatile",
    "RANGE_CALM": "Sideways, calm",
    "RANGE_VOLATILE": "Sideways, volatile",
}


def phase_vi(name: Optional[str]) -> str:
    """Market-phase label in Vietnamese; unknown names pass through unchanged."""
    return PHASE_VI.get(name or "", name or "—")


def _pct0(value: Optional[float]) -> str:
    return "—" if value is None else f"{value:.0f}%"


def _num0(value: Optional[float]) -> str:
    return "—" if value is None else f"{value:.0f}"


def _action_emergency_stop(row) -> str:
    """Worst tier: state the stress/ruin evidence, not an order.

    Out-of-sample validation measured the risk score against forward
    drawdown -- it never measured whether stopping a copy changes the
    outcome, so this cannot read as a command backed by that evidence. Kept
    short and does not repeat the risk score (`recommendation_vi`'s closing
    line already states it immediately before this text): see
    `recommendation_vi`'s own design note that the reasoning paragraph above
    is meant to be the longest part of the message, not this closing line.
    """
    text = (
        "The stress scenario ends in liquidation"
        if row.stress_verdict == "LIQUIDATED"
        else ("The current measurement sits in the emergency zone")
    )
    if row.p_ruin:
        text += f", {_pct0(row.p_ruin)} of simulations wipe out capital entirely"
    text += (
        " -- total loss of capital, not a temporary drawdown. Whether to keep copying is your call."
    )
    return text


def _action_pause(row) -> str:
    if row.p95_max_drawdown is not None:
        metric = f"Simulated P95 drawdown {_pct0(row.p95_max_drawdown)}"
    elif row.p_ruin:
        metric = f"Simulated probability of ruin {_pct0(row.p_ruin)}"
    else:
        metric = "The bot is in a risk zone that needs to be resolved on its own"
    return f"{metric}. Whether to wait until that is resolved is your call."


def _action_reduce(row) -> str:
    if row.p95_max_drawdown is not None:
        return (
            f"Simulated P95 drawdown {_pct0(row.p95_max_drawdown)} -- high, "
            "though not yet in the emergency zone."
        )
    return "The current measurement is high, though not yet in the emergency zone."


def _action_block_new_trades(row) -> str:
    if row.capital_at_risk:
        return (
            f"{_money(row.capital_at_risk)} is currently open, in an elevated risk zone. "
            "Whether to add more is your call."
        )
    return "The open position is in an elevated risk zone. Whether to add more is your call."


def _action_warn(row) -> str:
    if row.p95_max_drawdown is not None:
        return (
            f"Simulated P95 drawdown {_pct0(row.p95_max_drawdown)}, a watch "
            "zone. Whether to withdraw or hold is your call."
        )
    return "The current measurement sits in a watch zone, no action needed yet. Whether to withdraw or hold is your call."


def _action_monitor(row) -> str:
    return (
        f"Risk score {_num0(row.risk_score)}/100, no sign of anything abnormal. "
        "Whether to keep copying is still your call."
    )


# The old imperative-mood strings here (stop-now / pause / cut-size wording)
# overran the scope agreed with the project owner: this system only analyzes
# and suggests, it never substitutes its own decision for the user's. They
# also had no evidence behind them specifically -- the out-of-sample
# validation (Agent/docs/out_of_sample_validation.md) measured the risk
# score's correlation with forward drawdown, never whether stopping a copy
# changes the outcome. Each function below instead states this bot's own
# measured numbers and hands the decision back to the reader. Dict keys stay
# the internal action codes fusion.py already emits -- only the VALUES moved
# from a static string to a per-bot text generator.
ACTION_VI = {
    "EMERGENCY_STOP": _action_emergency_stop,
    "PAUSE": _action_pause,
    "REDUCE": _action_reduce,
    "BLOCK_NEW_TRADES": _action_block_new_trades,
    "WARN": _action_warn,
    "MONITOR": _action_monitor,
}


def action_vi(row) -> str:
    """The measured consequence behind `row.recommended_action`, argued from
    this bot's own numbers, ending on the reader's own call -- see the
    module comment above `ACTION_VI` for why this replaced a fixed
    imperative-mood string per action.
    """
    fn = ACTION_VI.get(row.recommended_action or "")
    if fn is None:
        return row.recommended_action or "—"
    return fn(row)


def _money(value: Optional[float]) -> str:
    return "—" if value is None else f"{value:,.0f} USDT"


BIAS_TEXT_VI = {
    "LONG_ONLY": "long only",
    "SHORT_ONLY": "short only",
    "LONG_TILTED": "both directions, leaning long",
    "SHORT_TILTED": "both directions, leaning short",
    "TWO_WAY": "both directions",
    "UNKNOWN": "direction not yet determined",
}
STYLE_TEXT_VI = {
    "TREND_FOLLOWING": "follows the move that just happened",
    "MEAN_REVERSION": "trades against the move that just happened",
    "MIXED": "sometimes follows, sometimes fades",
    "UNKNOWN": "not enough data to say what style it enters with",
}


def _what_would_change_it(row) -> str:
    """Name the single condition that would move this bot out of its bucket.

    A verdict without an exit condition reads as permanent, and the agent
    reading it has no way to know when to look again.
    """
    if (
        row.marked_profit_factor is not None
        and row.profit_factor is not None
        and row.profit_factor >= 1.0 > row.marked_profit_factor
    ):
        return (
            "Revisit when: the bot closes or cuts the pending open loss and the "
            "profit factor after closing returns above break-even."
        )
    if (row.trade_count or 0) >= 20 and not row.tested_in_downtrend:
        return (
            "Condition to revisit: the bot runs through a downtrend phase and "
            "holds its result."
        )
    if (
        row.min_track_record_trades
        and row.trade_count
        and row.trade_count < row.min_track_record_trades
    ):
        need = row.min_track_record_trades - row.trade_count
        return (
            f"Condition to revisit: roughly {need:,.0f} more trades are needed for a "
            "sound statistical basis."
        )
    if row.regime_dependence_pct is not None and row.regime_dependence_pct >= 70:
        return (
            "Condition to revisit: the bot earns profit in a market phase other "
            "than the one it currently depends on."
        )
    if row.p_ruin and row.p_ruin >= 5:
        return (
            "Condition to revisit: the simulated probability of ruin drops "
            "below 5%."
        )
    return ""


QUALITY_COMPONENT_VI = {
    "profitability": "profitability",
    "consistency": "consistency",
    "drawdown_control": "drawdown control",
    "honesty": "book honesty",
    "robustness": "robustness across regimes",
}


def _surface(row) -> str:
    """What the bot looks like to someone who only reads the leaderboard."""
    bits = []
    if row.win_rate is not None:
        bits.append(f"win rate {row.win_rate:.0f}%")
    if row.profit_factor is not None:
        bits.append(f"profit factor {row.profit_factor:.2f}")
    if row.max_drawdown_pct is not None:
        bits.append(f"max drawdown {row.max_drawdown_pct:.1f}%")
    return ", ".join(bits)


def _cause_story(row) -> str:
    """Why this bot got this verdict, argued in two or three sentences.

    A reader will only ever look at one bot for a few seconds, so the
    argument has to land in one breath: cơ chế (what the bot actually does)
    then hệ quả (what that does to a copier). Longer branches used to spell
    out the same point three times over; every branch here now makes it once
    and stops, trusting the bullets below to carry the supporting numbers.
    """
    name = row.nick_name
    surface = _surface(row)

    # The book is filtered: wins are closed, losses are left open.
    if (
        row.marked_profit_factor is not None
        and row.profit_factor is not None
        and row.profit_factor >= 1.0 > row.marked_profit_factor
    ):
        # NGÂN SÁCH 350 KÝ TỰ, xem `test_assessment_leads_with_the_text_and_
        # keeps_the_numbers`. Bản tiếng Anh đầu tiên dài 475 ký tự vì dịch sát
        # từng ý của bản tiếng Việt mà không cắt lại cho vừa -- đoạn này là
        # phần người đọc liếc mắt đầu tiên, dài quá thì mất tác dụng.
        text = (
            f"{name} looks strong ({surface}) — but only on closed trades: "
            f"{_money(row.open_loss)} of loss sits unrealised"
        )
        if row.open_loss_to_capital_pct:
            text += f" ({row.open_loss_to_capital_pct:.0f}% of capital)"
        text += (
            f". Closing it all turns profit factor into {row.marked_profit_factor:.2f}: "
            "wins taken early, losses held, copiers absorb them."
        )
        return text

    if row.open_loss_to_capital_pct and row.open_loss_to_capital_pct >= 20:
        return (
            f"{name} is holding {_money(row.open_loss)} of unrealised loss, equal to "
            f"{row.open_loss_to_capital_pct:.0f}% of reference capital — money already lost "
            "but not yet booked because the position is still open, so it does not show up "
            f"in any headline metric ({surface}). The numbers make the bot look fine; the real "
            "account has already lost part of its capital that whoever copies it does not know about."
        )

    if row.never_realized_a_loss and (row.trade_count or 0) >= 30:
        return (
            f"{name} has run {row.trade_count} trades without ever booking a single loss — "
            "at this trade count, the odds of a genuine strategy never losing once are close "
            "to zero. The only reasonable explanation is that the loss has not been closed "
            f"out yet, not that it doesn't exist, so every figure on the book ({surface}) "
            "is only the flattering half of the truth."
        )

    if row.regime_dependence_pct and row.regime_dependence_pct >= 70:
        text = (
            f"{name} shows a good result on the book ({surface}), but "
            f"{row.regime_dependence_pct:.0f}% of gross profit comes from a single market "
            f"phase, {phase_vi(row.best_phase)}. This is a strategy that fits one kind of "
            "market rather than a stable edge — when the phase changes, the edge disappears "
            "with no warning."
        )
        if row.losing_phases:
            text += f" The bot has been net losing in {len(row.losing_phases)}/6 phases."
        return text

    if not row.tested_in_downtrend and (row.trade_count or 0) >= 20:
        return (
            f"{name} currently has a good track record ({surface}), but the whole thing "
            "was built without a single trade during a downtrend phase. This does not mean "
            "the bot will lose on the way down — nobody knows yet — only that there is no "
            "basis for saying it can handle exactly the regime it has never faced."
        )

    if row.expectancy is not None and row.expectancy < 0:
        text = (
            f"{name} is losing money, not making it: across {row.trade_count or 0} "
            f"closed trades, the expectancy per trade is {row.expectancy:,.0f} USDT"
        )
        if row.total_pnl is not None and row.total_pnl < 0:
            text += f", for a cumulative loss of {_money(abs(row.total_pnl))}"
        text += ". "
        if row.win_rate is not None and row.win_rate >= 60 and row.payoff_ratio:
            text += (
                f"A win rate of {row.win_rate:.0f}% sounds fine, but each winning trade is "
                f"only {row.payoff_ratio:.2f} times a losing one, so it looks good on the win "
                "rate column while still losing money steadily overall. "
            )
        text += "The strategy has enough trades to draw a conclusion, and it is saying it loses money."
        return text

    if (
        row.deflated_sharpe is not None
        and row.deflated_sharpe < 0.6
        and row.selection_trials
    ):
        return (
            f"{name} looks promising ({surface}), but it was picked for being the best of "
            f"{row.selection_trials} candidates on the same asset — picking the best out of many "
            "candidates always carries an element of luck. Once that is discounted with the "
            f"Deflated Sharpe Ratio, the probability the bot has a genuine edge is only "
            f"{row.deflated_sharpe * 100:.1f}%, close to a coin flip."
        )

    if row.veto_reasons:
        return (
            f"{name} is blocked by a veto rule, not by the weighted average score: "
            + "; ".join(row.veto_reasons)
            + f". A veto exists so that one severe-enough fault cannot be hidden behind a "
            f"good-looking average — the weighted average across the 10 dimensions is still "
            f"{row.weighted_average:.1f}, but as long as this fault stands the bot should not be copied."
        )

    if (
        row.marked_profit_factor is not None
        and row.profit_factor is not None
        and abs(row.profit_factor - row.marked_profit_factor) < 0.3
    ):
        text = (
            f"{name} keeps an honest book — the most important point: profit factor "
            f"{row.profit_factor:.2f} on closed trades, and {row.marked_profit_factor:.2f} if every "
            "open position were closed right now. The two numbers being close means the bot "
            "actually cuts losses instead of holding them hoping for a bounce, so the track "
            "record shown is a real one."
        )
        if row.max_drawdown_pct is not None:
            text += f" The real drawdown recorded so far is {row.max_drawdown_pct:.1f}%."
        return text

    return (
        f"{name} has no single anomaly severe enough to decide the result on its own "
        f"({surface}). The score comes from the average across risk dimensions rather than "
        "one specific fault, so this is an overall risk level rather than one identifiable "
        "broken spot."
    )


def _proof_points(row) -> List[str]:
    """The handful of numbers that carry the argument, one line each.

    Every bullet pairs the number with what it means, because a number alone
    proves nothing to a reader who does not already know the threshold. A bot
    can qualify for a dozen of these at once, which is what made the old list
    a wall of text; candidates are built in priority order below and the
    return is cut to 6 so the strongest evidence survives and the rest is
    left to the paragraph above.
    """
    points: List[str] = []

    # 1. Profit factor, closed book vs. marked-to-market -- the number the
    # paragraph above is usually arguing from, so it leads here too.
    if row.profit_factor is not None and row.marked_profit_factor is not None:
        # "Close" has to mean close: 1.68 → 1.31 is a fifth of the edge
        # gone, and calling that an honest book contradicts the paragraph above.
        gap = row.profit_factor - row.marked_profit_factor
        relative = gap / row.profit_factor if row.profit_factor else 0.0
        if row.profit_factor >= 1.0 > row.marked_profit_factor:
            verdict = " — this gap is the whole problem"
        elif relative >= 0.15:
            verdict = f" — closing the open book would cost {relative * 100:.0f}% of the edge"
        else:
            verdict = " — the two figures are close, the book is not hiding a loss"
        points.append(
            f"Profit factor {row.profit_factor:.2f} (closed book) → "
            f"{row.marked_profit_factor:.2f} (open book closed too)" + verdict
        )
    elif row.profit_factor is not None:
        points.append(f"Profit factor {row.profit_factor:.2f}")

    # 2. The open loss in money and in percent of capital -- the single fact
    # a headline win rate is most likely to be hiding.
    if row.open_loss and row.open_loss_to_capital_pct:
        points.append(
            f"Unrealised loss {_money(row.open_loss)} = "
            f"{row.open_loss_to_capital_pct:.0f}% of capital, across "
            f"{row.open_positions or 0} open positions"
        )

    # 3. The stress test only earns a line when the bot did not simply
    # survive it -- a pass is the expected case, not evidence.
    if row.stress_verdict and row.stress_verdict != "SURVIVED":
        points.append(
            "Stress scenario (volatility 2x, spread 3x, liquidity 1/2): "
            + ("liquidated" if row.stress_verdict == "LIQUIDATED" else "vulnerable")
        )

    # 4. Where the risk score actually came from: a veto floor overrides the
    # weighted average, so the average alone would be misleading here.
    if row.veto_reasons:
        points.append(
            f"Risk score {row.risk_score:.0f} comes from the veto floor (weighted average "
            f"across 10 dimensions is only {row.weighted_average:.1f}): " + "; ".join(row.veto_reasons)
        )
    elif row.top_risk_drivers:
        points.append(
            f"Risk score {row.risk_score:.0f} is the weighted average across 10 dimensions; heaviest: "
            + ", ".join(row.top_risk_drivers[:2])
        )

    # 5. Monte Carlo over the bot's own trade count.
    if row.mc_iterations and row.profit_pct_p50 is not None:
        line = (
            f"Monte Carlo {row.mc_iterations:,} scenarios × {row.mc_horizon} trades: "
            f"median {row.profit_pct_p50:+.1f}% of capital"
        )
        if row.profit_pct_p05 is not None:
            line += f", p05 {row.profit_pct_p05:+.1f}%"
        if row.profit_pct_worst is not None:
            line += f", worst {row.profit_pct_worst:+.1f}%"
        points.append(line)

    # 6. The tail of that same simulation: what the worst 5% of paths look like.
    tail = []
    if row.cvar_95_pct is not None:
        value = -row.cvar_95_pct
        tail.append(
            f"worst 5% tail {'loss' if value < 0 else 'still profit'} {abs(value):.1f}%"
        )
    if row.p_loss_after_horizon is not None:
        tail.append(f"probability of loss {row.p_loss_after_horizon:.0f}%")
    if row.p_ruin:
        tail.append(f"probability of ruin {row.p_ruin:.0f}%")
    if tail:
        points.append("Simulated tail risk: " + ", ".join(tail))

    # 7. Its own bullet, not a tail clause: a strategy that has never met a
    # falling market is the single fact most likely to be missed, and it must
    # not disappear just because the phase breakdown could not be built.
    if not row.tested_in_downtrend and (row.trade_count or 0) >= 20:
        points.append(
            "Never tested on the way down — no trades during a downtrend phase"
        )

    # 8. The trade-count / win-rate / payoff triangle, which is where a "high
    # win rate" story usually falls apart.
    if row.trade_count and row.win_rate is not None and row.payoff_ratio:
        line = (
            f"{row.trade_count} trades, win rate {row.win_rate:.0f}%, payoff "
            f"{row.payoff_ratio:.2f}"
        )
        # "one loss erases 1.0 wins" is arithmetic, not evidence; the ratio
        # only says something once the two sides stop being equal.
        if row.payoff_ratio < 0.9:
            line += f" → one losing trade erases {1 / row.payoff_ratio:.1f} winning trades"
        elif row.payoff_ratio >= 1.5:
            line += " → winning trades are well ahead of losing trades"
        points.append(line)

    # 9. Drawdown and Sharpe together, since either alone is easy to misread.
    if row.max_drawdown_pct is not None and row.sharpe_ratio is not None:
        points.append(
            f"Actual drawdown {row.max_drawdown_pct:.1f}%, Sharpe "
            f"{row.sharpe_ratio:.2f}"
            + (
                f", longest losing streak {row.max_loss_streak} trades"
                if row.max_loss_streak
                else ""
            )
        )

    # 10. Deflated Sharpe: how much of the edge survives after accounting for
    # how many candidates it was picked from.
    if row.deflated_sharpe is not None and row.selection_trials:
        points.append(
            f"Probability of a genuine edge {row.deflated_sharpe * 100:.1f}% after "
            f"discounting selection from {row.selection_trials} candidates"
            + ("" if row.inference_reliable else " (low reliability, tail too thick)")
        )

    # 11. What the bot does and where it is strongest -- context rather than
    # a red flag on its own.
    if row.phase_coverage_pct is not None and row.best_phase:
        line = (
            f"Strategy: {BIAS_TEXT_VI.get(row.directional_bias or '', '')}, "
            f"{STYLE_TEXT_VI.get(row.entry_style or '', '')}; strongest in phase "
            f"{phase_vi(row.best_phase)}"
        )
        if row.regime_dependence_pct:
            line += f" ({row.regime_dependence_pct:.0f}% of gross profit)"
        if row.losing_phases:
            line += f", net losing in {len(row.losing_phases)}/6 phases"
        points.append(line)

    # 12. Which quality components dragged the composite score down.
    if row.quality_components:
        weak = [
            f"{QUALITY_COMPONENT_VI.get(key, key)} {value:.0f}"
            for key, value in row.quality_components.items()
            if value < 50
        ]
        if weak:
            points.append(
                f"Quality {row.quality_score:.0f}/100 dragged down by: "
                + ", ".join(weak)
            )

    # 13. Data limitations last: they qualify the evidence above rather than
    # adding a new fact of their own.
    limits = []
    if row.ledger_coverage_days and row.declared_lead_days:
        if row.ledger_coverage_days / row.declared_lead_days < 0.5:
            limits.append(
                f"the public ledger only covers {row.ledger_coverage_days:,.0f}/"
                f"{row.declared_lead_days} days of activity"
            )
    if (
        row.min_track_record_trades
        and row.trade_count
        and row.trade_count < row.min_track_record_trades
    ):
        limits.append(
            f"needs {row.min_track_record_trades:,.0f} trades for statistical "
            f"significance, currently has {row.trade_count}"
        )
    if row.measurement_mode and row.measurement_mode != "FULL":
        limits.append(f"measurement mode {row.measurement_mode}")
    if limits:
        points.append("Data limitations: " + "; ".join(limits))

    # Every branch above can fire at once; only the highest-priority handful
    # reach the reader, in the order they were appended.
    return points[:6]


def recommendation_vi(row) -> List[str]:
    """The assessment as an argument: why, then the proof, then the call.

    Shaped for a person to read top to bottom -- the reasoning is the long part
    because that is what has to convince, and the numbers are bullets under it
    because that is how evidence gets checked.
    """
    out: List[str] = []

    intro = f"{row.nick_name} — {row.traded_symbol}/{row.venue_type}"
    if row.trade_count:
        intro += f", {row.trade_count} closed trades"
    if row.capital_at_risk:
        intro += f", reference capital {row.capital_at_risk:,.0f} USDT"
    if row.trades_per_day:
        intro += f", {row.trades_per_day:.1f} trades/day"
    out.append(intro + ".")

    out.append("WHY THIS HAPPENED: " + _cause_story(row))

    proof = _proof_points(row)
    if proof:
        out.append("EVIDENCE:")
        out.extend(f"• {point}" for point in proof)

    action = action_vi(row)
    closing = (
        f"CONCLUSION: {row.verdict} — quality {row.quality_score:.0f}/100, risk "
        f"{row.risk_score:.0f}/100. {action}"
    )
    if row.verdict in (VERDICT_LOW_DD_GOOD_Q, VERDICT_LOW_DD_WEAK_Q) and (
        (row.total_pnl is not None and row.total_pnl < 0)
        or (row.expectancy is not None and row.expectancy < 0)
    ):
        closing += (
            " This verdict is about risk, not about profit: the bot is losing money, so "
            "this is not a recommendation to copy it, only that the potential damage is limited."
        )
    change = _what_would_change_it(row)
    if change:
        closing += f" {change}"
    if row.confidence is not None and row.confidence < 70:
        closing += f" Confidence in this assessment itself is only {row.confidence:.0f}%."
    out.append(closing)
    return out
