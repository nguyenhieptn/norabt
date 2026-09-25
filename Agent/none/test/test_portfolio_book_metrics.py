"""The portfolio's headline numbers are PORTFOLIO numbers, not single-bot ones.

N bots are N PnL series; the book's max drawdown, Sharpe, profitable days and
capital come from those series summed on the shared clock, and every formula
the page opens says so. Pinned against hand-computed values, not against the
implementation's own output (2026-09-25).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from Agent.backend.report.qc.portfolio.book_metrics import compute_book_metrics
from Agent.backend.report.qc.portfolio.schemas import PortfolioMember
from Agent.backend.report.qc.portfolio.timeseries import TimeSeriesMerger

DAY = 86_400_000
T0 = 1_790_006_400_000


def _members(capitals):
    return [
        PortfolioMember(
            bot_id=label, unique_code=label, nick_name=label, symbol="BTC",
            label=label, capital_at_risk=capital,
        )
        for label, capital in capitals.items()
    ]


def _series(values_by_label):
    return TimeSeriesMerger.merge_daily(
        [
            (label, label, [(T0 + i * DAY, float(v)) for i, v in enumerate(values)])
            for label, values in values_by_label.items()
        ]
    )


def test_drawdown_is_the_combined_accounts_not_an_average() -> None:
    """A loses 100 on day 1, B loses 100 on day 2: each bot alone has one
    100-deep fall, the account has a 200-deep one."""
    a = [0, -100, 0, 50] + [1] * 30
    b = [0, 0, -100, 50] + [1] * 30
    book = compute_book_metrics(_series({"A": a, "B": b}), _members({"A": 1000, "B": 1000}))
    # Peak 2000 at start, trough 1800 after day 2.
    assert book.max_drawdown_pct == pytest.approx(10.0)
    assert book.max_drawdown_abs == pytest.approx(200.0)
    assert book.capital == 2000


def test_sharpe_and_profitable_days_are_over_the_books_periods() -> None:
    rng = np.random.default_rng(3)
    a = rng.normal(5, 20, 60)
    b = rng.normal(-2, 30, 60)
    book = compute_book_metrics(_series({"A": a, "B": b}), _members({"A": 1000, "B": 3000}))
    returns = (a + b) / 4000.0
    expected = returns.mean() / returns.std(ddof=1) * math.sqrt(365)
    assert book.sharpe_annual == pytest.approx(expected, rel=1e-3)
    assert book.profitable_period_pct == pytest.approx((a + b > 0).mean() * 100, abs=0.01)


def test_idle_days_count_as_zero_return_for_the_account() -> None:
    """Dropped from the matrix (they say nothing about co-movement), but
    restored as zeros for the account -- or every average is overstated."""
    a = [10, 0, 0, 10] * 10
    b = [5, 0, 0, 5] * 10
    book = compute_book_metrics(_series({"A": a, "B": b}), _members({"A": 1000, "B": 1000}))
    assert book.periods == 40
    assert book.profitable_period_pct == pytest.approx(50.0)


def test_risk_contributions_sum_to_100_and_expose_the_risk_heavy_member() -> None:
    rng = np.random.default_rng(11)
    calm = rng.normal(0, 1, 90)
    wild = rng.normal(0, 40, 90)
    book = compute_book_metrics(
        _series({"calm": calm, "wild": wild}), _members({"calm": 9000, "wild": 1000})
    )
    shares = {m.label: m for m in book.members}
    assert sum(m.risk_contribution_pct for m in book.members) == pytest.approx(100.0, abs=0.01)
    # 10% of the capital, most of the risk.
    assert shares["wild"].capital_weight_pct == pytest.approx(10.0)
    assert shares["wild"].risk_contribution_pct > 80.0


def test_a_hedge_has_negative_risk_contribution() -> None:
    rng = np.random.default_rng(5)
    base = rng.normal(0, 10, 90)
    book = compute_book_metrics(
        _series({"long": base, "hedge": -0.5 * base + rng.normal(0, 1, 90)}),
        _members({"long": 1000, "hedge": 1000}),
    )
    hedge = next(m for m in book.members if m.label == "hedge")
    assert hedge.risk_contribution_pct < 0


def test_missing_capital_withholds_percentages_rather_than_guessing() -> None:
    book = compute_book_metrics(
        _series({"A": [1.0] * 30, "B": [2.0, -1.0] * 15}),
        _members({"A": 1000, "B": None}),
    )
    assert book.capital is None
    assert book.max_drawdown_pct is None and book.sharpe_annual is None
    assert book.total_pnl == pytest.approx(30 + 15)


# --------------------------------------------------------------------------- #
# Formula descriptions for a portfolio page
# --------------------------------------------------------------------------- #


def test_every_single_bot_formula_is_rescoped_for_a_portfolio() -> None:
    from Agent.backend.web.portfolio_formulas import portfolio_formula_overrides
    from Agent.backend.web.report_page import METRIC_FORMULA_INFO

    overrides = portfolio_formula_overrides(
        METRIC_FORMULA_INFO, measured=4, ledger_visible=3, ledger_hidden=1,
        hidden_capital_pct=84.9,
    )
    assert set(METRIC_FORMULA_INFO) <= set(overrides)
    for key in METRIC_FORMULA_INFO:
        desc = overrides[key]["desc"]
        assert "merged order book" in desc.lower(), key
        assert "85%" in desc, key  # names what is NOT in it
    assert "Σᵢ pᵢ,ₛ" in overrides["pf_max_drawdown"]["formula"]
    assert "RCᵢ" in overrides["pf_risk_contribution"]["formula"]


def test_no_hidden_member_means_no_hidden_member_note() -> None:
    from Agent.backend.web.portfolio_formulas import portfolio_formula_overrides
    from Agent.backend.web.report_page import METRIC_FORMULA_INFO

    overrides = portfolio_formula_overrides(
        METRIC_FORMULA_INFO, measured=3, ledger_visible=3, ledger_hidden=0,
    )
    assert "hides" not in overrides["risk_score"]["desc"]


def test_the_page_payload_carries_portfolio_headline_numbers() -> None:
    from Agent.backend.report.qc.portfolio.public_series import PublicPnlProfile
    from Agent.backend.report.qc.portfolio.service import (
        PortfolioCandidate,
        PortfolioQCService,
    )
    from Agent.backend.web.data import _portfolio_page_overrides
    from Agent.none.test.portfolio_factory import make_bot, make_trades

    rng = np.random.default_rng(7)
    base = rng.normal(0, 100, 120)
    series = [1.0, -2.0, 3.0, -1.0, 0.5, -0.5, 2.0, -3.0, 1.5, -1.5] * 6

    def prof(code, values, capital):
        return PublicPnlProfile(
            unique_code=code,
            daily=tuple((T0 + i * DAY, float(v)) for i, v in enumerate(values)),
            capital=capital,
        )

    assessment = PortfolioQCService.assess_portfolio(
        [
            PortfolioCandidate(bot=make_bot("AAA", make_trades(series))),
            PortfolioCandidate(bot=make_bot("BBB", make_trades([-v for v in series]))),
        ],
        iterations=300,
        concealed_members=["ZZZ"],
        public_profiles={
            "AAA": prof("AAA", base + rng.normal(0, 20, 120), 1000),
            "BBB": prof("BBB", -base + rng.normal(0, 20, 120), 1000),
            "ZZZ": prof("ZZZ", base + rng.normal(0, 20, 120), 8000),
        },
    )
    out = _portfolio_page_overrides(assessment)
    keys = [item["key"] for item in out["headline"]]
    assert keys == ["pf_capital", "pf_max_drawdown", "pf_profitable_periods", "pf_sharpe", "pf_periods"]
    assert out["headline"][0]["value"] == "10,000 USDT"
    assert out["headline"][4]["value"].startswith("3 bots")
    assert out["headline_sim"]["dd_key"] == "pf_sim_max_dd"
    assert out["headline_sim"]["dd_label"].endswith("P95")
    # 80% of the capital is the hidden member, and the scores say so.
    assert "80%" in out["formula_overrides"]["risk_score"]["desc"]


def test_the_page_header_figures_describe_the_whole_book() -> None:
    """Net PnL and the Monte Carlo line at the top of a portfolio page come
    from the book (all members) and the joint simulation -- not from the
    merged order book of the ledger-visible members."""
    from Agent.backend.web.report_page import _render_short_answer

    base = {
        "status": "FULL", "verdict": "DRAWDOWN: LOW · QUALITY: GOOD",
        "text": ["CONCLUSION: DRAWDOWN: LOW · QUALITY: GOOD — fine."],
        "evidence": {"performance": {"trade_count": 1201, "total_pnl": 342460.0}},
        "mc": {"p_ruin": 0.0, "p_loss_after_horizon": 12.5},
    }
    single = _render_short_answer(base)
    assert "+342,460 USDT" in single and "1 in 8 runs end in a loss" in single

    portfolio = {
        **base,
        "portfolio": {
            "book": {"total_pnl": 786998.0},
            "joint_simulation": {"is_valid": True, "p_ruin": 0.0, "probability_of_profit": 83.0},
            "members": [],
        },
    }
    html = _render_short_answer(portfolio)
    assert "+786,998 USDT" in html
    assert "Monte Carlo (joint)" in html
    assert "+342,460" not in html


# --------------------------------------------------------------------------- #
# What the correlation section draws must say what the engine measured
# --------------------------------------------------------------------------- #


def test_matrix_colours_use_the_engines_bands() -> None:
    """A pair the engine calls HIGH (r >= 0.6, "effectively one position")
    is red in the matrix, not amber: one r, one reading (2026-09-25)."""
    from Agent.backend.report.qc.portfolio.correlation import CorrelationAnalyzer
    from Agent.backend.web.portfolio_section import _distance_tint, _pearson_tint

    high = CorrelationAnalyzer.MODERATE_THRESHOLD
    assert CorrelationAnalyzer._relationship(0.62).value == "HIGH"
    assert "pf-tint-bad" in _pearson_tint(0.62)
    assert "pf-tint-warn" in _pearson_tint(high - 0.01)
    assert "pf-tint-warn" in _pearson_tint(0.40)
    assert "pf-tint-ok" in _pearson_tint(-0.25)
    # d = 0.30 is "genuinely different" in the engine, so green here.
    assert "pf-tint-ok" in _distance_tint(0.30)
    assert "pf-tint-bad" in _distance_tint(0.15)


def test_tail_tag_is_signed_and_toned() -> None:
    from Agent.backend.web.portfolio_section import _tail_tag

    assert "pf-tag-ok" in _tail_tag(0.45) and "&minus;45%" in _tail_tag(0.45)
    assert "pf-tag-warn" in _tail_tag(0.10)
    worse = _tail_tag(-0.2)
    assert "pf-tag-bad" in worse and "+20% worse" in worse and "&minus;-" not in worse
    assert _tail_tag(None) == ""


def test_joint_charts_state_horizon_and_link_formulas() -> None:
    from Agent.backend.web.portfolio_section import _outcome_chart, _var_chart

    joint = {
        "var_95_pct": 12.1, "sum_individual_var_95_pct": 22.1,
        "independent_var_95_pct": 7.0, "diversification_ratio": 0.45,
        "profit_pct_p05": -12.1, "profit_pct_p50": 21.1, "profit_pct_p95": 68.3,
        "probability_of_profit": 55.0, "p95_max_drawdown": 21.7, "cvar_95_pct": 18.1,
        "p_ruin": 0.0, "iterations": 10000, "horizon_buckets": 130,
        "horizon_calendar_days": 130.0,
    }
    var_html, outcome_html = _var_chart(joint), _outcome_chart(joint)
    assert "130 days" in var_html and "130 days" in outcome_html
    for key in ("pf_undiversified", "pf_joint_var", "pf_independent_var"):
        assert f"openFormulaModal('{key}')" in var_html
    for key in ("pf_outcome", "pf_prob_profit", "pf_sim_max_dd", "pf_cvar", "pf_ruin"):
        assert f"openFormulaModal('{key}')" in outcome_html
    # 45% of runs losing is not a green badge.
    assert "pf-tag-bad" in outcome_html


def test_results_card_shows_the_number_the_verdict_used() -> None:
    from Agent.backend.web.portfolio_section import render_portfolio_section

    pairs = [
        {"label_a": "A", "label_b": "B", "pearson": 0.7, "p_value": 0.0001, "is_significant": True},
        {"label_a": "A", "label_b": "C", "pearson": 0.5, "p_value": 0.001, "is_significant": True},
        {"label_a": "B", "label_b": "C", "pearson": -0.3, "p_value": 0.4, "is_significant": False},
    ]
    html = render_portfolio_section({
        "verdict": "MODERATE_CO_MOVEMENT",
        "correlation": {
            "labels": ["A", "B", "C"], "pairs": pairs, "average_pearson": 0.3,
            "pearson": [[1, 0.7, 0.5], [0.7, 1, -0.3], [0.5, -0.3, 1]],
        },
        "members": [],
    })
    assert "+0.60 &middot; 2/3 pairs" in html
    assert "&lt;0.001" in html
    assert "not significant: left out of the verdict" in html


def test_daily_window_counts_whole_days() -> None:
    series = _series({"A": [1.0, -1.0] * 65, "B": [-1.0, 2.0] * 65})
    assert series.diagnostics.span_buckets == 130
    assert series.diagnostics.overlap_days == pytest.approx(130.0)
