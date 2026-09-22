from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, Sequence

from Agent.backend.report.qc.reporting.cohort import BotEvaluationRow, CohortReport
from Agent.backend.report.qc.reporting.market_report import MarketRegimeReport
from Agent.backend.report.qc.reporting.reasons import (
    TIER_VI,
    computed_summary_vi,
    phase_vi,
    recommendation_vi,
    explain_vi,
    score_story_vi,
)


def _stamp(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime(
        "%d/%m/%Y %H:%M UTC"
    )


def display_width(text: str) -> int:
    """Vietnamese and CJK glyphs take two cells in most terminals."""
    return sum(2 if ord(c) > 0x2E80 else 1 for c in str(text))


def _cell(value: Optional[object], width: int, decimals: Optional[int] = None) -> str:
    if value is None:
        text = "—"
    elif decimals is not None and isinstance(value, (int, float)):
        text = f"{value:,.{decimals}f}"
    else:
        text = str(value)
    # Vietnamese and CJK glyphs are wider than one cell in most terminals.
    pad = width - display_width(text)
    if pad < 0:
        while text and pad < 0:
            dropped = text[-1]
            text = text[:-1]
            pad += 2 if ord(dropped) > 0x2E80 else 1
        text += "…"
        pad -= 1
    return text + " " * max(pad, 0)


def _header(columns: Sequence[tuple], title: str, subtitle: str) -> List[str]:
    line = " ".join(_cell(name, width) for name, width in columns)
    rule = "=" * len(line)
    return [rule, title, subtitle, rule, line, "-" * len(line)]


# ---------------------------------------------------------------- REPORT 1
MARKET_COLUMNS = (
    ("ASSET", 12),
    ("POSTURE", 16),
    ("MARKET REGIME", 30),
    ("LIQUIDITY", 13),
    ("FLOW", 14),
    ("ATR%", 7),
    ("RANGE POS", 12),
    ("QUALITY", 11),
    ("BOT", 4),
    ("ELIGIBLE", 8),
)


def render_market_report(report: MarketRegimeReport, detail: bool = True) -> str:
    lines = _header(
        MARKET_COLUMNS,
        "STEP 2.1 — MARKET ANALYSIS (REGIME AND POSTURE)",
        f"{_stamp(report.generated_at_ms)} | Observed {report.markets_observed} markets | "
        f"Eligible for monitoring {report.markets_eligible}",
    )
    for row in report.rows:
        lines.append(
            " ".join(
                [
                    _cell(f"{row.symbol}/{row.venue_type}", 12),
                    _cell(row.posture, 16),
                    _cell(row.regime, 30),
                    _cell(row.liquidity_tier, 13),
                    _cell(row.flow_bias, 14),
                    _cell(row.atr_pct, 7, 2),
                    _cell(row.range_position_pct, 12, 0),
                    _cell(row.data_quality * 100, 11, 0),
                    _cell(row.bots_trading, 4),
                    _cell("YES" if row.eligible else "NO", 8),
                ]
            )
        )
    lines.append("-" * len(lines[4]))
    lines.append(
        "Posture distribution: "
        + " | ".join(
            f"{k}: {v}"
            for k, v in sorted(report.posture_summary.items(), key=lambda kv: -kv[1])
        )
    )
    lines.append(
        "Regime distribution: "
        + " | ".join(
            f"{k}: {v}"
            for k, v in sorted(report.regime_summary.items(), key=lambda kv: -kv[1])
        )
    )
    if detail:
        lines.append("")
        lines.append("PER-MARKET EXPLANATION")
        lines.append("=" * len(lines[4]))
        for row in report.rows:
            lines.append(f"[{row.symbol}/{row.venue_type}] {row.note}")
            if row.posture_evidence:
                lines.append(f"    {row.posture} because: {'; '.join(row.posture_evidence)}")
            if row.missing_sources:
                lines.append(f"    Missing sources: {', '.join(row.missing_sources)}")
    return "\n".join(lines)


# ---------------------------------------------------------------- REPORT 2
BOT_COLUMNS = (
    ("BOT", 22),
    ("ASSET", 11),
    ("TRADES", 6),
    ("WIN%", 6),
    ("PF BOOK", 7),
    ("PF CLOSE", 8),
    ("DRAWDOWN", 9),
    ("POSITION", 8),
    ("EXPOSURE", 11),
    ("OPEN LOSS", 14),
)


def render_bot_report(report: CohortReport, detail: bool = True) -> str:
    rows = sorted(report.rows, key=lambda r: (r.traded_symbol, r.nick_name))
    lines = _header(
        BOT_COLUMNS,
        "STEP 2 — PER-BOT ANALYSIS BY TRADED ASSET",
        f"{_stamp(report.generated_at_ms)} | {report.distinct_bots} bots | "
        f"Raw observed data, not yet a risk verdict",
    )
    current = None
    for row in rows:
        if row.traded_symbol != current:
            current = row.traded_symbol
        lines.append(
            " ".join(
                [
                    _cell(row.nick_name, 22),
                    _cell(f"{row.traded_symbol}/{row.venue_type}", 11),
                    _cell(row.trade_count, 6),
                    _cell(row.win_rate, 6, 0),
                    _cell(row.profit_factor, 7, 2),
                    _cell(row.marked_profit_factor, 8, 2),
                    _cell(
                        f"{row.max_drawdown_pct:.1f}%"
                        if row.max_drawdown_pct is not None
                        else (
                            f"{row.max_drawdown_abs / 1000:,.0f}k$"
                            if row.max_drawdown_abs
                            else None
                        ),
                        9,
                    ),
                    _cell(row.open_positions, 8),
                    _cell(
                        f"{row.gross_exposure / 1000:,.0f}k$"
                        if row.gross_exposure
                        else None,
                        11,
                    ),
                    _cell(
                        f"{row.open_loss / 1000:,.0f}k$"
                        if row.open_loss
                        else ("0" if row.open_loss == 0 else None),
                        14,
                    ),
                ]
            )
        )
    lines.append("-" * len(lines[4]))
    if detail:
        lines.append("")
        lines.append("OBSERVATION DETAIL")
        lines.append("=" * len(lines[4]))
        for row in rows:
            lines.append(f"[{row.nick_name}] trading {row.traded_symbol}")
            lines.append(
                f"    Ledger: {row.trade_count} trades, reconciliation {row.reconciliation_status}, "
                f"measurement {row.measurement_mode}"
            )
            lines.append(
                f"    Capital basis: {row.capital_basis}"
                + (f" ({row.capital_at_risk:,.0f} USDT)" if row.capital_at_risk else "")
            )
            if row.open_positions:
                lines.append(
                    f"    Positions: {row.open_positions} open, "
                    f"{row.observed_positions_count} with instId, "
                    f"{row.inferred_positions_count} inferred, "
                    f"{row.positions_outside_ledger_universe} outside the ledger universe"
                )
            if row.loss_representativeness in ("PARTIAL", "UNREPRESENTATIVE"):
                lines.append(
                    f"    Deferred loss: {row.loss_representativeness}, "
                    f"{row.open_loss:,.0f} USDT unrealised"
                )
            lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------- REPORT 3
QC_COLUMNS = (
    ("#", 3),
    ("BOT NAME", 21),
    ("ASSET", 10),
    ("TRADE", 6),
    ("WIN%", 5),
    ("PF BOOK", 7),
    ("PF CLOSE", 8),
    ("DRAWDOWN", 8),
    ("P95 TAIL", 9),
    ("RISK", 7),
    ("QUALITY", 8),
    # Widened from 14: the two-axis labels ("DRAWDOWN: HIGH · QUALITY: GOOD",
    # 31 chars) are longer than the old 4 single-word buckets ever were.
    ("VERDICT", 32),
    ("NOTES", 46),
)

# Ordered worst first, which is the order the table is read in. "Worst" here
# means "needs a human look the soonest": hidden risk first (neither axis's
# number can be trusted), then the high-drawdown states (the axis the
# out-of-sample validation actually supports), then the low-drawdown states.
# Anything not listed (INSUFFICIENT EVIDENCE, or a stray/legacy value) sorts last
# via the `.get(..., 9)` default at each call site below.
VERDICT_ORDER = {
    "HIDDEN RISK": 0,
    "DRAWDOWN: HIGH · QUALITY: WEAK": 1,
    "DRAWDOWN: HIGH · QUALITY: GOOD": 2,
    "DRAWDOWN: LOW · QUALITY: WEAK": 3,
    "DRAWDOWN: LOW · QUALITY: GOOD": 4,
}


def _wrap(text: str, width: int, indent: str) -> List[str]:
    """Wrap on word boundaries; the cause text must never be cut mid-sentence."""
    out: List[str] = []
    line = ""
    for word in str(text).split():
        candidate = f"{line} {word}".strip()
        if display_width(candidate) > width and line:
            out.append(indent + line)
            line = word
        else:
            line = candidate
    if line:
        out.append(indent + line)
    return out


def render_qc_ranking(report: CohortReport) -> str:
    lines = _header(
        QC_COLUMNS,
        "STEP 3 — BOT SCORING AND VERDICT (QC CORE)",
        f"{_stamp(report.generated_at_ms)} | {report.distinct_bots} bots | "
        f"RISK: lower is safer · QUALITY: higher is better",
    )
    ordered = sorted(
        report.rows,
        key=lambda r: (
            VERDICT_ORDER.get(r.verdict or "", 9),
            -(r.risk_score or 0.0),
            r.nick_name,
        ),
    )
    width = len(lines[4])
    for index, row in enumerate(ordered, 1):
        drawdown = (
            f"{row.max_drawdown_pct:.1f}%" if row.max_drawdown_pct is not None else "—"
        )
        tail = (
            f"{row.p95_max_drawdown:.0f}%"
            if getattr(row, "p95_max_drawdown", None) is not None
            else "—"
        )
        lines.append(
            " ".join(
                [
                    _cell(index, 3),
                    _cell(row.nick_name, 21),
                    _cell(f"{row.traded_symbol}/{row.venue_type}", 10),
                    _cell(row.trade_count, 6),
                    _cell(row.win_rate, 5, 0),
                    _cell(row.profit_factor, 7, 2),
                    _cell(row.marked_profit_factor, 8, 2),
                    _cell(drawdown, 8),
                    _cell(tail, 9),
                    _cell(row.risk_score, 7, 1),
                    _cell(row.quality_score, 8, 1),
                    _cell(row.verdict, 32),
                    _cell(row.verdict_reason, 46),
                ]
            )
        )
        # The reasons are the point of the row, so they wrap rather than truncate.
        computed = computed_summary_vi(row)
        if computed:
            lines.extend(_wrap(f"↳ computed: {computed}", width - 6, "     "))
        cause = explain_vi(row)
        if cause:
            lines.extend(_wrap(f"↳ cause: {cause}", width - 6, "     "))
        if row.hidden_risk_flags:
            lines.extend(
                _wrap(
                    "↳ hidden risk: " + "; ".join(row.hidden_risk_flags),
                    width - 6,
                    "     ",
                )
            )
        if row.recommended_action:
            lines.append(f"     ↳ recommendation: {row.recommended_action}")
    lines.append("-" * width)
    verdicts: dict = {}
    for row in report.rows:
        verdicts[row.verdict or "?"] = verdicts.get(row.verdict or "?", 0) + 1
    lines.append(
        "Verdicts: "
        + " | ".join(
            f"{k}: {v}"
            for k, v in sorted(
                verdicts.items(), key=lambda kv: VERDICT_ORDER.get(kv[0], 9)
            )
        )
    )
    lines.append(
        "Risk tier distribution: "
        + " | ".join(
            f"{TIER_VI.get(k, k)}: {v}"
            for k, v in sorted(report.tier_summary.items(), key=lambda kv: -kv[1])
        )
    )
    lines.append("")
    lines.append("PER-BOT SCORECARD")
    lines.append("=" * width)
    for index, row in enumerate(ordered, 1):
        lines.extend(_bot_card(index, row, width))
    return "\n".join(lines)


def _bot_card(index: int, row, width: int) -> List[str]:
    """One bot, told as a verdict a person can act on.

    The table above gives the numbers; this says what they mean. Written for a
    reader who wants to know whether to copy this bot, not for someone auditing
    the maths -- so every figure quoted is one that changed the conclusion.
    """
    num = lambda v, d=2: "—" if v is None else f"{v:,.{d}f}"  # noqa: E731
    pct = lambda v: "—" if v is None else f"{v:+.1f}%"  # noqa: E731
    prob = lambda v: "—" if v is None else f"{v:.0f}%"  # noqa: E731

    lines = [
        f"[{index}] {row.nick_name} — {row.traded_symbol}/{row.venue_type}",
        f"     VERDICT: {row.verdict}"
        f"   ·   QUALITY SCORE: {num(row.quality_score, 1)}/100"
        f"   ·   RISK SCORE: {num(row.risk_score, 1)}/100 (lower is safer)"
        f"   ·   RECOMMENDATION: {row.recommended_action}",
        f"     Assessment confidence: {num(row.confidence, 0)}%"
        f" · ledger reconciliation {row.reconciliation_status}"
        f" · measurement mode {row.measurement_mode}",
        "",
    ]

    # 1. What the bot actually is.
    book = []
    if row.trade_count is not None:
        book.append(f"{row.trade_count} closed trades")
    if row.win_rate is not None:
        book.append(f"win rate {row.win_rate:.0f}%")
    if row.profit_factor is not None:
        book.append(f"profit factor {row.profit_factor:.2f}")
    if row.total_pnl is not None:
        book.append(f"total PnL {row.total_pnl:,.0f} USDT")
    if row.sharpe_ratio is not None:
        book.append(f"Sharpe {row.sharpe_ratio:.2f}")
    if row.max_drawdown_pct is not None:
        book.append(f"max drawdown {row.max_drawdown_pct:.1f}%")
    lines.extend(_wrap("BOT STATS: " + " · ".join(book), width - 6, "     "))

    holding = []
    if row.open_positions:
        holding.append(f"{row.open_positions} open positions")
    if row.gross_exposure:
        holding.append(f"exposure {row.gross_exposure:,.0f} USDT")
    if row.leverage:
        holding.append(f"leverage {row.leverage:.0f}x")
    if row.open_loss:
        holding.append(f"unrealised loss {row.open_loss:,.0f} USDT")
    if row.capital_at_risk:
        holding.append(f"reference capital {row.capital_at_risk:,.0f} USDT")
    if holding:
        lines.extend(_wrap("CURRENTLY HOLDING: " + " · ".join(holding), width - 6, "     "))

    # 2. What the simulation says could happen next.
    if row.mc_iterations and row.mc_horizon:
        sim = (
            f"RAN {row.mc_iterations:,} SIMULATIONS × {row.mc_horizon} trades "
            f"(bootstrapped from the bot's own closed book): "
            f"median profit {pct(row.profit_pct_p50)} on capital, "
            f"good scenario (p95) {pct(row.profit_pct_p95)}, "
            f"bad scenario (p05) {pct(row.profit_pct_p05)}, "
            f"WORST CASE {pct(row.profit_pct_worst)}. "
            f"P95 drawdown {prob(row.p95_max_drawdown)}, worst "
            f"{prob(row.worst_drawdown)}. "
            f"Probability of loss {prob(row.p_loss_after_horizon)}, "
            f"probability of ruin {prob(row.p_ruin)}."
        )
        lines.extend(_wrap(sim, width - 6, "     "))

    # 3. Whether the edge behind those numbers is real.
    if row.psr is not None:
        parts = [
            f"STATISTICAL TEST: probability the true Sharpe is above 0 is "
            f"{row.psr * 100:.1f}%"
        ]
        if not row.inference_reliable:
            parts.append(
                " (this figure is not reliable because a few individual trades "
                "dominate the skew and tail of the distribution)"
            )
        if row.deflated_sharpe is not None and row.selection_trials:
            parts.append(
                f"; after accounting for this bot being chosen as the best of "
                f"{row.selection_trials} candidates for the same asset, the probability "
                f"drops to {row.deflated_sharpe * 100:.1f}%"
            )
        if row.min_track_record_trades and row.trade_count:
            need = row.min_track_record_trades
            have = row.trade_count
            parts.append(
                f". Needs at least {need:,.0f} trades for this track record to be "
                f"trustworthy, the bot currently has {have}"
                + (" — enough" if have >= need else f" — {need - have:,.0f} short")
            )
        lines.extend(_wrap("".join(parts), width - 6, "     "))

    # 4. The recommendation in prose. This is what a trading agent reads; the
    # numbers above are the attachment, not the message.
    lines.append("")
    lines.append("     ASSESSMENT AND RECOMMENDATION:")
    previous_was_bullet = False
    for paragraph in recommendation_vi(row):
        if paragraph.startswith("• "):
            # A bullet that wraps flush with its own marker stops looking like
            # a list, so continuation lines hang under the text.
            wrapped = _wrap(paragraph[2:], width - 12, "")
            lines.append("       • " + wrapped[0])
            lines.extend("         " + line for line in wrapped[1:])
            previous_was_bullet = True
            continue
        if previous_was_bullet:
            lines.append("")
        lines.extend(_wrap(paragraph, width - 8, "       "))
        # The list header belongs against its list, not floating above a gap.
        if not paragraph.endswith(":"):
            lines.append("")
        previous_was_bullet = False

    lines.extend(
        _wrap(f"WHY THIS VERDICT: {row.verdict_reason}", width - 6, "     ")
    )
    cause = explain_vi(row)
    if cause:
        lines.extend(_wrap(f"WHY THIS RISK: {cause}", width - 6, "     "))
    if row.hidden_risk_flags:
        lines.extend(
            _wrap(
                "HIDDEN RISK BEHIND THE GOOD NUMBERS: " + "; ".join(row.hidden_risk_flags),
                width - 6,
                "     ",
            )
        )
    lines.extend(_wrap(score_story_vi(row), width - 6, "     "))
    for item in row.raised_the_score[:4]:
        lines.append(f"       + {item}")
    for item in row.held_the_score_down[:4]:
        lines.append(f"       − {item}")
    lines.append("")
    return lines


def render_text(report: CohortReport, detail: bool = True) -> str:
    """Giữ tương thích: mặc định trả báo cáo xếp hạng."""
    return render_qc_ranking(report)


def render_gaps(report: CohortReport) -> str:
    if not report.gaps:
        return ""
    lines = ["MISSING DATA — WORK TO COLLECT", "=" * 100]
    for gap in report.gaps:
        who = (
            f" | Affects: {', '.join(gap.affected_bots)}" if gap.affected_bots else ""
        )
        lines.append(f"[{gap.priority:6s}] {gap.scope} — {gap.evidence}")
        lines.append(f"    {gap.detail}")
        lines.append(f"    Unlocks: {', '.join(gap.unlocks) or '—'}{who}")
    return "\n".join(lines)


__all__ = [
    "render_market_report",
    "render_bot_report",
    "render_qc_ranking",
    "render_gaps",
    "render_text",
    "BotEvaluationRow",
]


BIAS_VI = {
    "LONG_ONLY": "long only",
    "SHORT_ONLY": "short only",
    "LONG_TILTED": "long tilted",
    "SHORT_TILTED": "short tilted",
    "TWO_WAY": "two-way",
    "UNKNOWN": "unclear",
}
STYLE_VI = {
    "TREND_FOLLOWING": "trend following",
    "MEAN_REVERSION": "mean reversion",
    "MIXED": "mixed",
    "UNKNOWN": "insufficient data",
}


def render_pair_report(report, detail: bool = True) -> str:
    """Step 2, one block per asset: the market, then the pair that trades it."""
    lines = [
        "=" * 118,
        "STEP 2.2 — PER-BOT ANALYSIS AND SIMULATION",
        f"{_stamp(report.generated_at_ms)} | {report.slots} assets | "
        f"{report.bots_evaluated} bots analyzed"
        + (f", {report.bots_failed} bots failed" if report.bots_failed else "")
        + " | Observed data, not yet a risk verdict",
        "=" * 118,
    ]

    # Two tables, because they answer different questions: what the bot did,
    # and what could happen next. One combined row carried twenty columns and
    # stopped being readable.
    perf_width = 140
    lines += [
        "",
        f"TABLE A — REALIZED PERFORMANCE ({report.slots} ASSETS · "
        f"{report.bots_evaluated} BOTS)",
        "-" * perf_width,
        _cell("ASSET", 10)
        + _cell("ROLE", 10)
        + _cell("BOT", 20)
        + _cell("TRADE", 6)
        + _cell("WIN%", 5)
        + _cell("PROFIT", 12)
        + _cell("PF BOOK", 8)
        + _cell("PF CLOSE", 9)
        + _cell("MDD", 8)
        + _cell("SHARPE", 7)
        + _cell("OPEN LOSS", 10)
        + _cell("DIRECTION", 14)
        + "ENTRY STYLE",
        "-" * perf_width,
    ]
    for block in report.blocks:
        for position, bot in enumerate(block.bots):
            asset_cell = f"{block.venue_type}/{block.symbol}" if not position else ""
            if bot.error:
                lines.append(
                    _cell(asset_cell, 10)
                    + _cell(bot.role, 10)
                    + _cell(bot.nick_name, 20)
                    + f"ERROR: {bot.error}"
                )
                continue
            dd = (
                f"{bot.max_drawdown_pct:.1f}%"
                + ("*" if bot.max_drawdown_capped else "")
                if bot.max_drawdown_pct is not None
                else "—"
            )
            lines.append(
                _cell(asset_cell, 10)
                + _cell(bot.role, 10)
                + _cell(bot.nick_name, 20)
                + _cell(bot.trade_count, 6)
                + _cell(bot.win_rate, 5, 0)
                + _cell(
                    f"{bot.ledger_pnl:,.0f}" if bot.ledger_pnl is not None else "—", 12
                )
                + _cell(bot.profit_factor, 8, 2)
                + _cell(bot.marked_profit_factor, 9, 2)
                + _cell(dd, 8)
                + _cell(bot.sharpe_ratio, 7, 2)
                + _cell(f"{bot.open_loss / 1000:,.0f}k$" if bot.open_loss else "0", 10)
                + _cell(BIAS_VI.get(bot.directional_bias, bot.directional_bias), 14)
                + STYLE_VI.get(bot.entry_style, bot.entry_style)
            )
    lines += [
        "-" * perf_width,
        "PROFIT = closed-book PnL · PF CLOSE = profit factor if all open positions "
        "were closed now · MDD marked with * exceeds the recorded capital, so it is a floor",
    ]

    mc_width = 160
    lines += [
        "",
        "TABLE B — MONTE CARLO SIMULATION AND RISK ASSESSMENT",
        "10,000 scenarios/bot · stationary bootstrap (Politis-Romano 1994) · each "
        "scenario replays the bot's own exact trade count "
        "· CLOSED trades only",
        "-" * mc_width,
        _cell("ASSET", 10)
        + _cell("BOT", 20)
        + _cell("PROFIT WORST", 13)
        + _cell("PFT MED", 9)
        + _cell("PFT P95", 9)
        + _cell("CVaR95", 9)
        + _cell("DD MEDIAN", 10)
        + _cell("DD P95", 8)
        + _cell("MAR", 7)
        + _cell("P(WIN)", 7)
        + _cell("P(RUIN)", 8)
        + _cell("PSR", 7)
        + _cell("DSR", 7)
        + "MinTRL",
        "-" * mc_width,
    ]
    for block in report.blocks:
        for position, bot in enumerate(block.bots):
            if bot.error or not bot.mc_iterations:
                continue
            pct = lambda v: "—" if v is None else f"{v:+.1f}%"  # noqa: E731
            prob = lambda v: "—" if v is None else f"{v:.0f}%"  # noqa: E731
            prb = lambda v: "—" if v is None else f"{v:.3f}"  # noqa: E731
            trl = (
                f"{bot.min_track_record_trades:,.0f} (of {bot.mc_sample_size})"
                if bot.min_track_record_trades
                else "—"
            )
            lines.append(
                _cell(f"{block.venue_type}/{block.symbol}" if not position else "", 10)
                + _cell(bot.nick_name, 20)
                + _cell(pct(bot.mc_profit_worst_pct), 13)
                + _cell(pct(bot.mc_profit_p50_pct), 9)
                + _cell(pct(bot.mc_profit_p95_pct), 9)
                + _cell(
                    pct(-bot.cvar_95_pct) if bot.cvar_95_pct is not None else "—", 9
                )
                + _cell(prob(bot.mc_median_drawdown), 10)
                + _cell(prob(bot.mc_p95_drawdown), 8)
                + _cell(
                    f"{bot.mar_ratio_median:.1f}"
                    if bot.mar_ratio_median is not None
                    else "—",
                    7,
                )
                + _cell(prob(bot.probability_of_profit), 7)
                + _cell(prob(bot.mc_p_ruin), 8)
                + _cell(prb(bot.psr) + ("" if bot.inference_reliable else "?"), 7)
                + _cell(prb(bot.deflated_sharpe), 7)
                + trl
            )
    lines += [
        "-" * mc_width,
        f"Total: {report.slots} assets · {report.bots_evaluated} bots"
        + (f" · {report.bots_failed} bots failed" if report.bots_failed else ""),
        "PROFIT = profit on capital · CVaR95 = average loss in the worst 5% of scenarios "
        "· MAR = profit divided by drawdown",
        "PSR = probability the true Sharpe is > 0 after accounting for sample length, skew "
        "and fat tails; a ? mark means the moments are dominated by a few individual trades "
        "and are not reliable",
        "DSR = PSR after accounting for this bot being chosen as the best of a candidate pool "
        "· MinTRL = minimum trades needed for the Sharpe to be trustworthy at 95% confidence",
        "(Bailey & López de Prado 2012, 2014)",
        "",
        "PER-ASSET DETAIL",
    ]

    for block in report.blocks:
        lines.append("")
        market = (
            f"{block.market_posture} · {block.market_trend}/{block.market_volatility}"
            f" · liquidity {block.market_liquidity}"
            f" · data quality {block.market_quality:.2f}"
            if block.market_available
            else f"COULD NOT BUILD MARKET: {block.market_error}"
        )
        lines.append(f"── {block.venue_type}/{block.symbol} ── {market}")
        if block.market_evidence:
            lines.append(f"   Because: {'; '.join(block.market_evidence)}")

        lines.append(
            "   "
            + _cell("role", 10)
            + _cell("bot", 21)
            + _cell("trades", 7)
            + _cell("/asset", 7)
            + _cell("win%", 6)
            + _cell("pf book", 8)
            + _cell("pf close", 9)
            + _cell("drawdown", 9)
            + _cell("position", 9)
            + _cell("open loss", 10)
            + "STRATEGY"
        )
        for bot in block.bots:
            if bot.error:
                lines.append(
                    "   "
                    + _cell(bot.role, 10)
                    + _cell(bot.nick_name, 21)
                    + f"ERROR: {bot.error}"
                )
                continue
            dd = (
                f"{bot.max_drawdown_pct:.1f}%"
                + ("*" if bot.max_drawdown_capped else "")
                if bot.max_drawdown_pct is not None
                else "—"
            )
            strategy = (
                f"{BIAS_VI.get(bot.directional_bias, bot.directional_bias)}, "
                f"{STYLE_VI.get(bot.entry_style, bot.entry_style)}"
                f" · phase coverage {bot.phase_coverage_pct:.0f}%"
                if bot.phase_coverage_pct is not None
                else BIAS_VI.get(bot.directional_bias, bot.directional_bias)
            )
            lines.append(
                "   "
                + _cell(bot.role, 10)
                + _cell(bot.nick_name, 21)
                + _cell(bot.trade_count, 7)
                + _cell(bot.trades_on_asset, 7)
                + _cell(bot.win_rate, 6, 0)
                + _cell(bot.profit_factor, 8, 2)
                + _cell(bot.marked_profit_factor, 9, 2)
                + _cell(dd, 9)
                + _cell(bot.open_positions, 9)
                + _cell(f"{bot.open_loss / 1000:,.0f}k$" if bot.open_loss else "0", 10)
                + strategy
            )

        if detail:
            for bot in block.bots:
                if bot.error or not bot.phase_rows:
                    continue
                num = lambda v, d=2: "—" if v is None else f"{v:,.{d}f}"  # noqa: E731
                lines.append(f"   · {bot.nick_name} — full stats:")
                lines.append(
                    "       PERFORMANCE:      "
                    f"expectancy {num(bot.expectancy)}/trade"
                    f" · payoff {num(bot.payoff_ratio)}"
                    f" · avg win {num(bot.average_win)} / avg loss {num(bot.average_loss)}"
                    f" · total PnL {num(bot.ledger_pnl, 0)}"
                )
                lines.append(
                    "       RISK-ADJUSTED:    "
                    f"Sharpe {num(bot.sharpe_ratio)}"
                    f" · Sortino {num(bot.sortino_ratio)}"
                    f" · Calmar {num(bot.calmar_ratio)}"
                    f" · recovery {num(bot.recovery_factor)}"
                )
                lines.append(
                    "       CADENCE:          "
                    f"{num(bot.trades_per_day)} trades/day"
                    f" · median hold time {num(bot.median_hold_minutes, 0)} min"
                    f" · longest win streak {bot.max_win_streak}"
                    f" · longest loss streak {bot.max_loss_streak}"
                )
                ci = (
                    f"[{bot.mean_pnl_ci[0]:,.0f}; {bot.mean_pnl_ci[1]:,.0f}]"
                    if bot.mean_pnl_ci and len(bot.mean_pnl_ci) == 2
                    else "—"
                )
                lines.append(
                    "       DISTRIBUTION:     "
                    f"median {num(bot.pnl_median, 0)}"
                    f" · std dev {num(bot.pnl_std, 0)}"
                    f" · skew {num(bot.pnl_skew)}"
                    f" · kurtosis {num(bot.pnl_kurtosis)}"
                    f" · p05 {num(bot.pnl_p05, 0)} / p95 {num(bot.pnl_p95, 0)}"
                    f" · mean 95% CI {ci}"
                )
                lines.append(
                    "       CAPITAL & LEDGER: "
                    f"reference capital {num(bot.capital_at_risk, 0)}"
                    f" ({bot.capital_basis})"
                    f" · ledger covers {num(bot.ledger_coverage_days, 0)}/"
                    f"{bot.declared_lead_days or '—'} lead days"
                    f" · reconciliation {bot.reconciliation}"
                    f" · measurement mode {bot.measurement_mode}"
                )
                if bot.stress_verdict:
                    lines.append(
                        "       STRESS TEST:     "
                        f" volatility ×2 {num(bot.stress_volatility_2x, 0)}"
                        f" · spread ×3 {num(bot.stress_spread_3x, 0)}"
                        f" · liquidity ½ {num(bot.stress_liquidity_half, 0)}"
                        f" → {bot.stress_verdict}"
                    )
                lines.append("     by market phase:")
                for row in bot.phase_rows:
                    win = row.get("win_rate")
                    share = row.get("profit_share_pct")
                    lines.append(
                        "       "
                        + _cell(phase_vi(row["phase"]), 16)
                        + _cell(f"{row['trades']} trades", 10)
                        + _cell(f"win {win:.0f}%" if win is not None else "win —", 9)
                        + _cell(f"PnL {row['total_pnl']:,.0f}", 18)
                        + (
                            # Share of GROSS wins, which a net-losing phase can
                            # still hold a lot of; saying "chiếm x% lợi nhuận"
                            # there would read as if the phase made money.
                            (
                                f"{share:.0f}% of gross profit"
                                + (" but net losing" if row["total_pnl"] < 0 else "")
                            )
                            if share is not None
                            else "no gross profit"
                        )
                    )
                if bot.mc_iterations:
                    draws = bot.mc_iterations * (bot.mc_horizon or 0)
                    lines.append(
                        f"       Monte Carlo: {bot.mc_iterations:,} scenarios × "
                        f"{bot.mc_horizon} trades = {draws:,} draws"
                        + "  · scope: CLOSED trades only"
                        + (
                            f", the bot is holding {bot.open_loss / 1000:,.0f}k$ of "
                            "unrealised loss outside the simulation"
                            if bot.mc_deferred_loss_bias and bot.open_loss
                            else ""
                        )
                    )
                    fmt = lambda v: "—" if v is None else f"{v:+.1f}%"  # noqa: E731
                    lines.append(
                        "       PROFIT/CAPITAL:   "
                        + f"worst {fmt(bot.mc_profit_worst_pct)}"
                        + f" · p05 {fmt(bot.mc_profit_p05_pct)}"
                        + f" · median {fmt(bot.mc_profit_p50_pct)}"
                        + f" · p95 {fmt(bot.mc_profit_p95_pct)}"
                        + f" · best {fmt(bot.mc_profit_best_pct)}"
                    )
                    lines.append(
                        "       DRAWDOWN:         " + f"P95 {bot.mc_p95_drawdown:.1f}%"
                        if bot.mc_p95_drawdown is not None
                        else "       DRAWDOWN:         —"
                    )
                    lines[-1] += (
                        f" · worst {bot.mc_worst_drawdown:.1f}%"
                        if bot.mc_worst_drawdown is not None
                        else ""
                    )
                    lines[-1] += (
                        f" · probability of ruin {bot.mc_p_ruin:.1f}%"
                        if bot.mc_p_ruin is not None
                        else ""
                    )
                    lines[-1] += (
                        f" · probability of loss {bot.mc_p_loss:.1f}%"
                        if bot.mc_p_loss is not None
                        else ""
                    )
                if bot.entry_style_evidence:
                    lines.append(
                        f"       entry style basis: {bot.entry_style_evidence}"
                    )
                if bot.untested_phases:
                    lines.append(
                        "       market phases that exist but this bot has never traded through: "
                        + ", ".join(phase_vi(p) for p in bot.untested_phases)
                    )

        for note in block.comparison:
            lines.append(f"   → {note}")

    lines.append("")
    lines.append("-" * 118)
    lines.append("* = drawdown exceeds the capital recorded at that time, so the figure is a floor.")
    for note in report.notes:
        lines.append(f"· {note}")
    return "\n".join(lines)


def render_data_report(report) -> str:
    """Step 1: two inventories — the markets, then the bots."""
    lines = [
        "=" * 140,
        "STEP 1 — DATA (INPUT INVENTORY FOR MARKET AND BOT)",
        f"{_stamp(report.generated_at_ms)} | "
        f"{report.markets_complete}/{len(report.markets)} markets with complete sources | "
        f"{report.bots_complete}/{len(report.bots)} bots with complete data",
        "=" * 140,
        "",
        f"TABLE 1.1 — MARKET DATA ({len(report.markets)} ASSETS)",
        "-" * 140,
        _cell("MARKET", 13)
        + _cell("1H CANDLE", 10)
        + _cell("SOURCES OK", 11)
        + _cell("QUALITY", 12)
        + "MISSING / STALE",
        "-" * 140,
    ]
    for row in report.markets:
        if not row.available:
            lines.append(
                _cell(f"{row.venue_type}/{row.symbol}", 13)
                + f"COULD NOT BUILD: {row.error}"
            )
            continue
        gaps = [f"missing {s}" for s in row.missing] + [f"stale {s}" for s in row.stale]
        lines.append(
            _cell(f"{row.venue_type}/{row.symbol}", 13)
            + _cell(f"{row.candles:,}", 10)
            + _cell(f"{row.sources_ok}/{row.sources_total}", 11)
            + _cell(f"{row.quality:.2f}" if row.quality is not None else "—", 12)
            + ("; ".join(gaps) if gaps else "✓ OK")
        )

    lines += [
        "-" * 140,
        "",
        f"TABLE 1.2 — BOT DATA ({len(report.bots)} BOTS)",
        "-" * 140,
        _cell("SLOT", 11)
        + _cell("ROLE", 10)
        + _cell("BOT", 21)
        + _cell("TRADES", 7)
        + _cell("/ASSET", 7)
        + _cell("POSITION", 9)
        + _cell("MISSING ID", 11)
        + _cell("WEEKLY", 7)
        + _cell("PROFILE", 8)
        + _cell("ACTIVITY", 11)
        + "BLOCKING / NOTES",
        "-" * 140,
    ]
    for row in report.bots:
        if row.blocking and row.folder is None:
            lines.append(
                _cell(row.slot, 11)
                + _cell(row.role, 10)
                + _cell(row.nick_name, 21)
                + "NOT CRAWLED"
            )
            continue
        status = "; ".join(f"BLOCKED: {b}" for b in row.blocking)
        if row.notes:
            status = (status + " · " if status else "") + "; ".join(row.notes)
        lines.append(
            _cell(row.slot, 11)
            + _cell(row.role, 10)
            + _cell(row.nick_name, 21)
            + _cell(row.trades, 7)
            + _cell(row.trades_on_asset, 7)
            + _cell(row.open_positions, 9)
            + _cell(row.positions_without_instrument, 11)
            + _cell(row.weekly_points, 7)
            + _cell("yes" if row.has_profile else "no", 8)
            + _cell(
                f"{row.last_close_days:.1f}d"
                if row.last_close_days is not None
                else "—",
                11,
            )
            + (status or "✓ OK")
        )

    lines.append("-" * 140)
    for note in report.notes:
        lines.append(f"· {note}")
    return "\n".join(lines)
