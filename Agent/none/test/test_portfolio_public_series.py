"""A bot that hides its order book is still measurable -- on OKX's public daily PnL.

OKX answers 60004 on exactly two endpoints for such a bot (history, current
positions). Its daily PnL, currency preference and stats stay public. These
tests pin the three steps that turn that into a member of the correlation
matrix instead of an absence (2026-09-24):

1. parsing OKX's cumulative, newest-first series into daily PnL;
2. aligning daily series on one shared clock (one ruler for every member);
3. `assess_portfolio` moving the WHOLE matrix to that ruler only when every
   ledger member has it, and never mixing the two bases.
"""

from __future__ import annotations

import numpy as np
import pytest

from Agent.backend.report.qc.portfolio.public_series import (
    PublicPnlProfile,
    parse_public_profile,
)
from Agent.backend.report.qc.portfolio.schemas import PortfolioVerdict
from Agent.backend.report.qc.portfolio.service import (
    PortfolioCandidate,
    PortfolioQCService,
)
from Agent.backend.report.qc.portfolio.timeseries import TimeSeriesMerger
from Agent.none.test.portfolio_factory import make_bot, make_trades

DAY = 86_400_000
# A Hong Kong day start (16:00 UTC), as OKX stamps them.
T0 = 1_790_006_400_000
_SERIES = [1.0, -2.0, 3.0, -1.0, 0.5, -0.5, 2.0, -3.0, 1.5, -1.5] * 6


def _profile(code, values, *, capital=10_000.0, name=None, exposure=None):
    return PublicPnlProfile(
        unique_code=code,
        daily=tuple((T0 + index * DAY, float(v)) for index, v in enumerate(values)),
        nick_name=name,
        capital=capital,
        exposure=exposure or {"BTC": 1.0},
    )


# --------------------------------------------------------------------------- #
# 1. Parsing
# --------------------------------------------------------------------------- #


def test_cumulative_newest_first_rows_become_ascending_daily_pnl() -> None:
    raw = {
        "pnl": [
            {"beginTs": str(T0 + 2 * DAY), "pnl": "30"},
            {"beginTs": str(T0 + DAY), "pnl": "10"},
            {"beginTs": str(T0), "pnl": "0"},
        ],
        "preference": [{"ccy": "eth", "ratio": "0.6"}, {"ccy": "BTC", "ratio": "0.4"}],
        "stats": {"investAmt": "5000"},
        "nickName": "Hidden Whale",
    }
    profile = parse_public_profile("CODE1", raw)
    assert profile is not None
    assert profile.daily == ((T0 + DAY, 10.0), (T0 + 2 * DAY, 20.0))
    assert profile.capital == 5000.0
    assert profile.exposure == {"ETH": 0.6, "BTC": 0.4}
    assert profile.nick_name == "Hidden Whale"


@pytest.mark.parametrize(
    "raw",
    [None, {}, {"pnl": []}, {"pnl": [{"beginTs": str(T0), "pnl": "0"}]}],
)
def test_no_usable_daily_series_is_none_not_an_empty_profile(raw) -> None:
    assert parse_public_profile("CODE1", raw) is None


def test_non_positive_capital_is_unknown_not_zero() -> None:
    raw = {
        "pnl": [{"beginTs": str(T0 + DAY), "pnl": "1"}, {"beginTs": str(T0), "pnl": "0"}],
        "stats": {"investAmt": "0"},
    }
    assert parse_public_profile("CODE1", raw).capital is None


# --------------------------------------------------------------------------- #
# 2. Daily alignment
# --------------------------------------------------------------------------- #


def test_daily_series_share_one_window_and_drop_days_nobody_moved() -> None:
    a = [(T0 + i * DAY, float(i + 1)) for i in range(30)]
    # B starts five days later and is flat on its last day.
    b = [(T0 + i * DAY, 2.0) for i in range(5, 30)] + [(T0 + 30 * DAY, 0.0)]
    series = TimeSeriesMerger.merge_daily([("A", "a", a), ("B", "b", b)])
    assert series.diagnostics.pnl_basis == "MARK_TO_MARKET_DAILY"
    assert series.diagnostics.overlap_start_ms == T0 + 5 * DAY
    assert series.diagnostics.overlap_end_ms == T0 + 29 * DAY
    assert series.matrix.shape == (2, 25)
    assert series.is_valid


def test_a_short_daily_series_is_excluded_by_name() -> None:
    long = [(T0 + i * DAY, 1.0 + i) for i in range(40)]
    short = [(T0 + i * DAY, 1.0) for i in range(5)]
    series = TimeSeriesMerger.merge_daily(
        [("A", "a", long), ("B", "b", long), ("S", "s", short)]
    )
    assert "S" in series.diagnostics.excluded
    assert series.labels == ["A", "B"]


def test_a_failed_daily_alignment_still_names_its_ruler() -> None:
    series = TimeSeriesMerger.merge_daily([("A", "a", [(T0, 1.0)])])
    assert not series.is_valid
    assert series.diagnostics.pnl_basis == "MARK_TO_MARKET_DAILY"


# --------------------------------------------------------------------------- #
# 3. assess_portfolio on one ruler
# --------------------------------------------------------------------------- #


def _two_ledger_bots_and_a_hidden_twin():
    rng = np.random.default_rng(7)
    base = rng.normal(0, 100, 150)
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades([-v for v in _SERIES])),
    ]
    profiles = {
        "AAA": _profile("AAA", base + rng.normal(0, 25, 150)),
        "BBB": _profile("BBB", -base + rng.normal(0, 25, 150)),
        # Concealed on OKX, and secretly the same position as AAA.
        "ZZZ": _profile(
            "ZZZ",
            base + rng.normal(0, 25, 150),
            capital=5_000.0,
            name="Hidden Whale",
            exposure={"ETH": 0.6, "BTC": 0.4},
        ),
    }
    return bots, profiles


def _assess(bots, **kwargs):
    return PortfolioQCService.assess_portfolio(
        [PortfolioCandidate(bot=bot) for bot in bots], iterations=400, **kwargs
    )


def test_a_concealed_bot_with_public_pnl_joins_the_matrix() -> None:
    bots, profiles = _two_ledger_bots_and_a_hidden_twin()
    result = _assess(bots, concealed_members=["ZZZ"], public_profiles=profiles)

    correlation = result.correlation
    assert correlation.alignment.pnl_basis == "MARK_TO_MARKET_DAILY"
    assert len(correlation.labels) == 3
    hidden = [m for m in result.members if m.ledger_hidden]
    assert [m.label for m in hidden] == ["Hidden Whale"]
    assert hidden[0].capital_at_risk == 5_000.0
    assert hidden[0].symbol == "ETH"
    assert sum(m.capital_weight for m in result.members) == pytest.approx(1.0, abs=1e-5)
    assert result.submitted_member_count == 3
    assert result.concealed_member_codes == ["ZZZ"]
    # It is measured now, so the "absent" coverage guard does not fire.
    assert result.measurement_coverage_pct == pytest.approx(100.0)


def test_what_the_hidden_bot_is_doing_is_found_not_assumed() -> None:
    """The case dropping it used to hide: the concealed bot is the same
    position as a member, and the verdict has to say so."""
    bots, profiles = _two_ledger_bots_and_a_hidden_twin()
    result = _assess(bots, concealed_members=["ZZZ"], public_profiles=profiles)
    pair = next(
        p for p in result.correlation.pairs
        if {p.label_a, p.label_b} == {"Bot AAA", "Hidden Whale"}
    )
    assert pair.pearson > 0.8 and pair.is_significant
    assert result.verdict is PortfolioVerdict.HIGH_CORRELATION_CLUSTER


def test_pairs_with_a_hidden_bot_have_no_behaviour_distance() -> None:
    bots, profiles = _two_ledger_bots_and_a_hidden_twin()
    result = _assess(bots, concealed_members=["ZZZ"], public_profiles=profiles)
    for pair in result.correlation.pairs:
        if "Hidden Whale" in (pair.label_a, pair.label_b):
            assert pair.style is None


def test_one_ledger_member_without_public_pnl_keeps_everyone_on_the_ledger() -> None:
    """Never two rulers in one matrix."""
    bots, profiles = _two_ledger_bots_and_a_hidden_twin()
    del profiles["BBB"]
    result = _assess(bots, concealed_members=["ZZZ"], public_profiles=profiles)
    assert result.correlation.alignment.pnl_basis == "REALIZED_LEDGER"
    assert len(result.correlation.labels) == 2
    assert not any(m.ledger_hidden for m in result.members)
    assert result.submitted_member_count == 3


def test_no_public_profiles_is_exactly_the_old_behaviour() -> None:
    bots, _ = _two_ledger_bots_and_a_hidden_twin()
    result = _assess(bots, concealed_members=["ZZZ"])
    assert result.correlation.alignment.pnl_basis == "REALIZED_LEDGER"
    assert result.verdict is PortfolioVerdict.INSUFFICIENT_EVIDENCE


def test_a_recovered_member_gives_the_portfolio_its_own_id() -> None:
    """Booking the hidden bot is a different portfolio from not booking it."""
    bots, profiles = _two_ledger_bots_and_a_hidden_twin()
    with_hidden = _assess(bots, concealed_members=["ZZZ"], public_profiles=profiles)
    without = _assess(bots, public_profiles={k: profiles[k] for k in ("AAA", "BBB")})
    assert with_hidden.portfolio_id != without.portfolio_id
    assert "ZZZ" in with_hidden.member_codes


# --------------------------------------------------------------------------- #
# 4. The pipeline asks for every code, and never fails on it
# --------------------------------------------------------------------------- #


class _Service:
    def __init__(self, raw_by_code):
        self.raw_by_code = raw_by_code
        self.calls = []

    def public_profile(self, code, folder=None, include_name=False):
        self.calls.append((code, include_name))
        return self.raw_by_code.get(code)


class _Inner:
    persist_history = False
    history = None

    def __init__(self, service):
        self.bot_service = service


def test_pipeline_fetches_public_series_for_members_and_concealed_codes() -> None:
    from Agent.backend.pipeline_portfolio import PortfolioSupervisionPipeline

    raw = {
        "pnl": [
            {"beginTs": str(T0 + DAY), "pnl": "5"},
            {"beginTs": str(T0), "pnl": "0"},
        ]
    }
    service = _Service({"AAA": raw, "ZZZ": raw})
    pipeline = PortfolioSupervisionPipeline(
        pipeline=_Inner(service), persist_history=False, max_workers=2
    )
    profiles = pipeline.fetch_public_profiles(["AAA", "BBB"], ["ZZZ"])
    assert set(profiles) == {"AAA", "ZZZ"}
    # Only the concealed code pays for the name lookup.
    assert ("ZZZ", True) in service.calls and ("AAA", False) in service.calls


# --------------------------------------------------------------------------- #
# 5. The page: a recovered bot is a member, not an absence
# --------------------------------------------------------------------------- #


def test_the_page_shows_a_recovered_bot_as_a_member_with_its_limits() -> None:
    from Agent.backend.web.portfolio_section import render_portfolio_section

    bots, profiles = _two_ledger_bots_and_a_hidden_twin()
    result = _assess(bots, concealed_members=["ZZZ"], public_profiles=profiles)
    failures = [
        {"asset": "ETH", "bot_folder_name": "bot_ZZZ", "error": "60004", "kind": "concealed"}
    ]
    html = render_portfolio_section(result.model_dump(mode="json"), [], [], failures)

    assert "Submitted but not measured" not in html
    # Recovered into the matrix, the book metrics and the joint simulation;
    # only the scores and the trade tables need an order book and still
    # leave it out -- the header says how much of the book those cover, and
    # which figures DO include every member.
    assert "SCORE PARTIAL" in html and "covers" in html
    assert "Every member is in" in html
    assert "RISK UNDERSTATED" not in html
    assert "3 measured (1 public PnL only)" in html
    assert ">Public PnL<" in html
    assert "mark-to-market daily PnL" in html
    assert "order book hidden on OKX, no exits to compare" in html


def test_an_unrecovered_concealed_bot_is_still_reported_absent() -> None:
    from Agent.backend.web.portfolio_section import render_portfolio_section

    bots, _ = _two_ledger_bots_and_a_hidden_twin()
    result = _assess(bots, concealed_members=["ZZZ"])
    failures = [
        {"asset": "ETH", "bot_folder_name": "bot_ZZZ", "error": "60004", "kind": "concealed"}
    ]
    html = render_portfolio_section(result.model_dump(mode="json"), [], [], failures)
    assert "Submitted but not measured" in html
    assert "RISK UNDERSTATED" in html
    assert "ORDER BOOK HIDDEN" not in html


def test_capital_is_on_one_ruler_too_when_every_member_publishes_it() -> None:
    """A ledger member's modelled capital and a hidden member's public
    `investAmt` are not on one scale (measured 0.75x-5.27x apart); on the
    mark-to-market basis every member's weight comes from `investAmt`."""
    bots, profiles = _two_ledger_bots_and_a_hidden_twin()
    result = _assess(bots, concealed_members=["ZZZ"], public_profiles=profiles)
    by_code = {m.unique_code: m for m in result.members}
    assert by_code["AAA"].capital_at_risk == profiles["AAA"].capital
    assert by_code["ZZZ"].capital_at_risk == profiles["ZZZ"].capital
    # 10k + 10k + 5k
    assert by_code["ZZZ"].capital_weight == pytest.approx(0.2)


def test_one_missing_public_capital_keeps_the_modelled_capitals() -> None:
    bots, profiles = _two_ledger_bots_and_a_hidden_twin()
    profiles["BBB"] = PublicPnlProfile(
        unique_code="BBB", daily=profiles["BBB"].daily, capital=None
    )
    result = _assess(bots, concealed_members=["ZZZ"], public_profiles=profiles)
    by_code = {m.unique_code: m for m in result.members}
    assert by_code["BBB"].capital_at_risk == bots[1].capital.capital_at_risk
