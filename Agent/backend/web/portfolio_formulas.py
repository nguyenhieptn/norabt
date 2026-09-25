"""Formula descriptions for a PORTFOLIO page -- N PnL series, not one bot.

The single-bot report explains every number with `report_page.
METRIC_FORMULA_INFO`, written for ONE bot's trades. A portfolio page shows the
same kinds of numbers, but each one is computed from N members together, so
its explanation has to say how -- a reader clicking "Max drawdown" on a
four-bot book must be told it is the combined account's drawdown, not one
bot's, and not an average of four.

Two kinds of entries:

* `pf_*` keys: the portfolio's own numbers (the book as one account, the
  joint simulation, the correlation matrix, risk contribution), each with the
  formula actually used.
* every single-bot key, re-scoped: numbers that are still computed by the
  single-bot engine over the MERGED order book of the members whose ledger is
  visible. Their formula is unchanged -- what changes is WHAT it runs over,
  and which members are not in it, which the description now states.
"""

from __future__ import annotations

from typing import Dict, Optional

# The book as one account -- see `report.qc.portfolio.book_metrics`.
_BOOK: Dict[str, Dict[str, str]] = {
    "pf_capital": {
        "title": "Portfolio capital",
        "formula": "C = Σᵢ cᵢ over all N members",
        "desc": (
            "The capital the whole book trades with. On the mark-to-market basis, when every "
            "member publishes it, cᵢ is OKX's public investAmt -- one source for all members, "
            "the same figure OKX's own daily pnlRatio divides by -- so a member with a hidden "
            "order book is weighted on the same scale as the others. If any member lacks it, "
            "every member falls back to the equity-curve capital model instead: one ruler, "
            "never a mix."
        ),
    },
    "pf_return": {
        "title": "Portfolio return",
        "formula": "Return = Σₜ Σᵢ pᵢ,ₜ / C",
        "desc": "Everything the N members made or lost over the shared window, on the book's capital.",
    },
    "pf_max_drawdown": {
        "title": "Portfolio max drawdown",
        "formula": "MDD = maxₜ (peakₜ − Eₜ) / peakₜ,  Eₜ = C + Σ_{s≤t} Σᵢ pᵢ,ₛ",
        "desc": (
            "The deepest fall the COMBINED account went through, with every member's PnL "
            "summed period by period. Not the average of each bot's own drawdown -- the "
            "members did not bottom out on the same day, and offsetting is what a "
            "portfolio is for."
        ),
    },
    "pf_current_drawdown": {
        "title": "Portfolio drawdown now",
        "formula": "DDₙₒw = (peak − E_T) / peak at the last period",
        "desc": "How far the combined account sits below its own high at the end of the window.",
    },
    "pf_profitable_periods": {
        "title": "Profitable days",
        "formula": "#{t : Σᵢ pᵢ,ₜ > 0} / T",
        "desc": (
            "Share of periods in which the WHOLE book made money. Replaces the single-bot "
            "'winning trades': pooling N bots' trades counts a 10-USDT win and a 10,000-"
            "USDT loss as one each, which describes the trades, not the account."
        ),
    },
    "pf_profit_factor": {
        "title": "Portfolio profit factor",
        "formula": "PF = Σ gains of Pₜ / |Σ losses of Pₜ|,  Pₜ = Σᵢ pᵢ,ₜ",
        "desc": "Money made on up-periods of the book per unit lost on down-periods. Above 1 the book makes money.",
    },
    "pf_sharpe": {
        "title": "Portfolio Sharpe (annualised)",
        "formula": "Sharpe = mean(rₜ) / sd(rₜ) × √(periods per year),  rₜ = Σᵢ pᵢ,ₜ / C",
        "desc": (
            "Return per unit of the BOOK's volatility, over periods of the combined account "
            "(idle periods count as zero return). A pooled per-trade Sharpe is a different "
            "number, usually far higher: it measures the average trade, not the account."
        ),
    },
    "pf_sortino": {
        "title": "Portfolio Sortino (annualised)",
        "formula": "Sortino = mean(rₜ) / sqrt(mean(min(rₜ, 0)²)) × √(periods per year)",
        "desc": "Like Sharpe, but only the book's DOWN-periods count as risk.",
    },
    "pf_volatility": {
        "title": "Portfolio volatility (annualised)",
        "formula": "σₚ = sqrt(wᵀ Σ w) × √(periods per year),  wᵢ = cᵢ / C",
        "desc": (
            "Σ is the covariance of the members' own returns (pᵢ,ₜ / cᵢ). The correlations "
            "in the matrix below enter here: the same members with lower correlation give "
            "a lower σₚ."
        ),
    },
    "pf_vol_diversification": {
        "title": "Volatility cancelled inside the book",
        "formula": "1 − σₚ / Σᵢ wᵢ σᵢ",
        "desc": "How much of the members' own volatility offsets once they are held together. 0% = none, higher = more.",
    },
    "pf_periods": {
        "title": "Periods measured",
        "formula": "T = periods from the first to the last shared period",
        "desc": (
            "The window in which all N members were running. Periods in which no member's PnL "
            "moved are left out of the correlation matrix but kept here as zero return for the "
            "account."
        ),
    },
    "pf_risk_contribution": {
        "title": "Risk contribution",
        "formula": "RCᵢ = wᵢ (Σ w)ᵢ / (wᵀ Σ w),  Σᵢ RCᵢ = 100%",
        "desc": (
            "Each member's share of the book's variance (Euler decomposition). Compare it "
            "with the member's share of capital: a member carrying far more risk than "
            "capital is where the book's risk actually sits (tagged risk-heavy above 1.5× its "
            "capital share and at least 5 points more). Negative = it hedges the rest."
        ),
    },
    "pf_weight": {
        "title": "Capital weight",
        "formula": "wᵢ = cᵢ / C",
        "desc": "The member's share of the book's capital.",
    },
    "pf_standalone_vol": {
        "title": "Member volatility (annualised)",
        "formula": "σᵢ = sd(pᵢ,ₜ / cᵢ) × √(periods per year)",
        "desc": "The member's own volatility on its own capital, before any offsetting.",
    },
}

# The joint simulation -- see `report.qc.portfolio.joint_monte_carlo`.
_JOINT: Dict[str, Dict[str, str]] = {
    "pf_sim_max_dd": {
        "title": "Simulated max drawdown (P95, joint)",
        "formula": "95th percentile over joint paths of maxₜ (peakₜ − Eₜ)/peakₜ;  each path = H resampled periods, every member's PnL from the SAME period",
        "desc": (
            "Stationary bootstrap (Politis & Romano, 1994) over the aligned matrix: a "
            "resampled period carries every member's PnL from that SAME period, so the "
            "co-movement between bots is kept. The horizon H is as long as the shared "
            "history. The bad case: 1 joint path in 20 falls deeper than this. A per-bot or "
            "pooled-trade simulation would treat the members as independent."
        ),
    },
    "pf_sim_max_dd_median": {
        "title": "Simulated max drawdown (median, joint)",
        "formula": "median over joint paths of maxₜ (peakₜ − Eₜ)/peakₜ over the horizon H",
        "desc": "The typical path's deepest fall for the whole book, co-movement kept.",
    },
    "pf_ruin": {
        "title": "Probability of ruin (joint)",
        "formula": "#{paths : C + Σ_{s≤t} Σᵢ pᵢ,ₛ ≤ 0 for some t ≤ H} / all joint paths × 100",
        "desc": "Share of joint paths that wipe out the book's capital, co-movement included.",
    },
    "pf_joint_var": {
        "title": "Joint VaR 95%",
        "formula": "VaR₉₅ = −P₅( Σₜ≤H Σᵢ pᵢ,ₜ / C ) over joint paths",
        "desc": (
            "The book's result at the end of the horizon H (as long as the shared history), "
            "resampled with the members' co-movement kept. In 95% of joint paths the book "
            "loses less than this share of its capital. Positive = loss; negative = even the "
            "worst 5% of paths end in profit."
        ),
    },
    "pf_undiversified": {
        "title": "Undiversified VaR 95%",
        "formula": "Σᵢ wᵢ · VaR₉₅,ᵢ,  VaR₉₅,ᵢ = −P₅(member i's own paths / cᵢ),  wᵢ = cᵢ / C",
        "desc": (
            "The book's tail if every member hit its own worst 5% at the same time -- the "
            "no-diversification benchmark. Each member is simulated alone on its own capital "
            "over the same horizon H, then weighted by its capital share."
        ),
    },
    "pf_tail_removed": {
        "title": "Tail removed by combining",
        "formula": "1 − Joint VaR₉₅ / Undiversified VaR₉₅",
        "desc": (
            "How much of the loss tail disappears because the members do not all lose "
            "together. 0% = none; negative = combining made the tail worse; not shown when "
            "the undiversified benchmark is not a loss."
        ),
    },
    "pf_independent_var": {
        "title": "Independent VaR 95%",
        "formula": "VaR₉₅ with each member resampled on its OWN period indices, then summed / C",
        "desc": (
            "The counterfactual: the same members with their co-movement removed. The gap "
            "between this and the joint VaR is what the members' correlation costs the book."
        ),
    },
    "pf_cvar": {
        "title": "Joint CVaR 95% (expected shortfall)",
        "formula": "CVaR₉₅ = −mean( book return at H | return ≤ P₅ ) over joint paths",
        "desc": "The AVERAGE loss of the worst 5% of joint paths -- how bad the bad case is, not just where it starts.",
    },
    "pf_outcome": {
        "title": "Simulated book return at the horizon",
        "formula": "P₅ · P₅₀ · P₉₅ of Σₜ≤H Σᵢ pᵢ,ₜ / C over joint paths",
        "desc": (
            "Where the book ends after H periods (as long as the shared history), co-movement "
            "kept. The band runs from the 5th to the 95th percentile, the dot is the median, "
            "the dashed line is break-even."
        ),
    },
    "pf_prob_profit": {
        "title": "Probability of profit (joint)",
        "formula": "#{joint paths with book return at H > 0} / all paths × 100",
        "desc": "Share of joint paths in which the whole book ends the horizon in profit.",
    },
}

# The correlation matrix -- see `report.qc.portfolio.correlation`.
_CORRELATION: Dict[str, Dict[str, str]] = {
    "pf_avg_r": {
        "title": "Average pairwise correlation",
        "formula": "mean over all N(N−1)/2 pairs of Pearson r(pᵢ,ₜ, pⱼ,ₜ)",
        "desc": (
            "How much the members' PnL moves together, over EVERY pair, significant or not. "
            "The verdict uses a stricter number: the average of the pairs significant at 5% "
            "only, and only when at least half of the pairs are."
        ),
    },
    "pf_sig_avg_r": {
        "title": "Verdict correlation (significant pairs)",
        "formula": "r̄ₛᵢg = mean of r over pairs with p < 0.05  (needs ≥ 50% of pairs significant)",
        "desc": (
            "What the Results verdict is decided on: ≥ 0.60 (or any significant pair ≥ 0.80) "
            "= move together, 0.30-0.60 = partly, below 0.30 = diversified. Fewer than half "
            "the pairs significant = not enough evidence either way."
        ),
    },
    "pf_max_r": {
        "title": "Strongest pair",
        "formula": "max over pairs of Pearson r(pᵢ,ₜ, pⱼ,ₜ)",
        "desc": "One pair near +1 is one position held twice, however comfortable the average looks.",
    },
    "pf_shared_history": {
        "title": "Shared history",
        "formula": "end of the last shared period − start of the first shared period",
        "desc": "The calendar window in which every member was running; every number in this section is measured inside it.",
    },
    "pf_pair_r": {
        "title": "Pair correlation r",
        "formula": "r = cov(pᵢ, pⱼ) / (σ(pᵢ) σ(pⱼ)) over the shared periods",
        "desc": (
            "+1 the two lose and win together, 0 unrelated, −1 they offset. Bands (the "
            "matrix tint): ≥ 0.60 high, 0.30-0.60 moderate, ≤ −0.20 offsetting."
        ),
    },
    "pf_pair_d": {
        "title": "Exit-rule distance d",
        "formula": "d = max( RMS gap of the 8 exit-rule components,  1-D Wasserstein distance of the holding-period bands )",
        "desc": (
            "How alike the two TRADE, from their order books. ≤ 0.15 same playbook, "
            "0.15-0.30 partly overlapping, ≥ 0.30 genuinely different. The worse of the two "
            "axes, so a strong difference in either separates them. n/a when OKX hides "
            "either order book."
        ),
    },
    "pf_rho": {
        "title": "Rank correlation ρ",
        "formula": "Spearman ρ = Pearson r of the ranks",
        "desc": "Like r but insensitive to a few extreme days.",
    },
    "pf_co": {
        "title": "Co-active periods",
        "formula": "#{t : pᵢ,ₜ ≠ 0 and pⱼ,ₜ ≠ 0}",
        "desc": "Periods in which BOTH members' PnL moved; r over mostly-idle periods partly measures idleness.",
    },
    "pf_p": {
        "title": "p-value of r",
        "formula": "p = erfc(|atanh r| · sqrt(n − 3) / √2)  (Fisher z, n = shared periods)",
        "desc": "Below 0.05 the pair's r is distinguishable from zero at this sample size.",
    },
    "pf_ov": {
        "title": "Exposure overlap",
        "formula": "cosine similarity of the two members' symbol-share vectors",
        "desc": "Do they hold the same things (1) or different things (0) -- independent of whether their PnL co-moves.",
    },
}


def _scoped(info: Dict[str, str], scope: str) -> Dict[str, str]:
    return {
        "title": info.get("title", ""),
        "formula": info.get("formula", ""),
        "desc": f"{scope} {info.get('desc', '')}".strip(),
    }


def portfolio_formula_overrides(
    base: Dict[str, Dict[str, str]],
    *,
    measured: int,
    ledger_visible: int,
    ledger_hidden: int,
    hidden_capital_pct: Optional[float] = None,
) -> Dict[str, Dict[str, str]]:
    """Every formula entry a portfolio page needs, portfolio-worded.

    `base` is the single-bot `METRIC_FORMULA_INFO`; each of its keys comes back
    re-scoped to the merged order book, with the members NOT in that book
    named by count (and capital share when known). The `pf_*` keys are added
    as they are.
    """
    hidden_note = ""
    if ledger_hidden:
        share = (
            f" ({hidden_capital_pct:.0f}% of the book's capital)"
            if hidden_capital_pct is not None
            else ""
        )
        hidden_note = (
            f" {ledger_hidden} member{'s' if ledger_hidden != 1 else ''} whose order book OKX "
            f"hides{share} {'are' if ledger_hidden != 1 else 'is'} NOT in it -- see "
            "Diversification for the numbers that include every member."
        )
    ledger_scope = (
        f"Portfolio: computed by the single-bot engine over the MERGED order book of the "
        f"{ledger_visible} member{'s' if ledger_visible != 1 else ''} whose ledger is visible "
        f"(all their trades in one time-ordered book).{hidden_note}"
    )
    overrides: Dict[str, Dict[str, str]] = {
        key: _scoped(info, ledger_scope) for key, info in base.items()
    }
    # The three hero scores get a sharper statement than the generic scope:
    # they are the ones a reader acts on.
    for key, what in (
        ("risk_score", "Risk score"),
        ("quality_score", "Quality score"),
        ("confidence", "Confidence"),
    ):
        if key in base:
            overrides[key] = {
                "title": f"{what} (merged order book)",
                "formula": base[key].get("formula", ""),
                "desc": (
                    f"The ten-lens engine run over the merged order book of the "
                    f"{ledger_visible} ledger-visible members, as if they were one bot.{hidden_note} "
                    + base[key].get("desc", "")
                ).strip(),
            }
    overrides.update(_BOOK)
    overrides.update(_JOINT)
    overrides.update(_CORRELATION)
    overrides.update(_EXPOSURE)
    return overrides


# The open book -- see `PortfolioQCService._concentration`. Built from open
# POSITIONS, which only a visible order book has.
_EXPOSURE: Dict[str, Dict[str, str]] = {
    "pf_largest_symbol": {
        "title": "Largest symbol",
        "formula": "maxₛ  Σᵢ notionalᵢ,ₛ / Σᵢ Σₛ notionalᵢ,ₛ",
        "desc": (
            "The share of all members' open notional sitting in one instrument. Only "
            "members whose positions are visible count: OKX hides a concealed bot's "
            "positions along with its order book."
        ),
    },
    "pf_hhi": {
        "title": "Normalised HHI",
        "formula": "(Σₛ sₛ² − 1/k) / (1 − 1/k),  sₛ = symbol share of open notional, k = symbols held",
        "desc": "0 = the open book is spread evenly across the symbols held, 1 = all of it in one.",
    },
    "pf_direction": {
        "title": "Same direction",
        "formula": "|Σ long notional − Σ short notional| / Σ gross notional",
        "desc": "100% = every open position points the same way -- one directional bet, however many bots placed it.",
    },
    "pf_gross": {
        "title": "Gross open notional",
        "formula": "Σᵢ |open notionalᵢ| over the members with visible positions",
        "desc": "The size of the open book right now, long and short added together.",
    },
}


# Every `pf_*` entry in one map, for renderers that label portfolio numbers.
PF_FORMULAS: Dict[str, Dict[str, str]] = {**_BOOK, **_JOINT, **_CORRELATION, **_EXPOSURE}
