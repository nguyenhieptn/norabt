"""Tests for the limited assessment (Agent/backend/analysis/limited.py).

This is the reduced assessment built when OKX answers 60004 ("Trader doesn't
exist") on a bot's ledger endpoints but still serves its profile/weekly-pnl/
public-stats -- see Agent/backend/sources/bot_source.py's
LedgerUnavailableError and TRADER_NOT_EXIST_CODE for the measured 19%-of-
lead-traders rate this happens at (7/36 in a real sample).

No test here calls OKX -- every input is a hand-built dict/list shaped like a
real OKX response, following the same fixtures test_bot_source.py already
uses (make_weekly/make_leaderboard_row/make_stats). The one exception is the
"never scores better than a transparent bot" test, which deliberately runs
the REAL full QC pipeline (QCCoreService) against the project's own bot_top
fixture to get a real, non-cherry-picked FULL risk/confidence number to
compare against.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from Agent.backend.bot.analysis.limited import (
    LIMITED_CONFIDENCE_CEILING,
    MONTE_CARLO_KEY,
    NOT_FOUND_CONFIDENCE,
    PSR_DSR_KEY,
    STATUS_LIMITED,
    STATUS_NOT_FOUND,
    assess_from_error,
    assess_limited_bot,
)
from Agent.backend.infra.config import config
from Agent.backend.bot.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.report.qc.service import QCCoreService
from Agent.backend.external.sources.bot_source import LedgerUnavailableError

DATA_DIR = Path(config.DATA_DIR)

CANONICAL_UNAVAILABLE = {
    "profit_factor",
    "deferred_loss",
    "phase_analysis",
    "monte_carlo",
    "psr_dsr",
}


def _weekly_points(
    n: int = 12,
    start_ts: int = 1_788_710_400_000,
    base_pnl: float = 500.0,
    base_ratio: float = 0.05,
) -> List[Dict[str, Any]]:
    """~n weeks of weekly PnL, ratios well above the equity-curve builder's
    precision floor so the drawdown/equity math itself is exercised (not
    just skipped as unusable)."""
    return [
        {
            "beginTs": str(start_ts - i * 604_800_000),
            "pnl": str(base_pnl + i * 15.0),
            "pnlRatio": str(base_ratio + i * 0.002),
        }
        for i in range(n)
    ]


def _clean_profile(code: str = "CODE1") -> Dict[str, Any]:
    return {
        "uniqueCode": code,
        "nickName": "Test Lead Trader",
        "aum": "20000.0",
        "pnl": "9000.0",
        "pnlRatio": "0.45",
        "leadDays": "400",
        "rank": 3,
    }


def _clean_stats() -> Dict[str, Any]:
    return {
        "winRatio": "0.62",
        "investAmt": "15000.0",
        "profitDays": "220",
        "lossDays": "135",
    }


# ---------------------------------------------------------------------------
# Contract shape
# ---------------------------------------------------------------------------


def test_limited_contract_has_every_required_key():
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=_weekly_points(),
    )
    for key in (
        "status",
        "code",
        "name",
        "limited_reason",
        "unavailable",
        "verdict",
        "risk",
        "quality",
        "confidence",
        "evidence",
        "mc",
        "text",
    ):
        assert key in result, f"missing key {key}"
    assert result["status"] == STATUS_LIMITED
    assert result["code"] == "CODE1"
    assert isinstance(result["text"], list) and result["text"]


def test_limited_text_states_it_is_a_limited_assessment_up_front():
    """Task requirement: the first text line must say plainly this is a
    limited assessment because the bot hides its ledger -- not buried later."""
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=_weekly_points(),
    )
    first = result["text"][0]
    assert "LIMITED ASSESSMENT" in first
    assert "CODE1" in first


def test_unavailable_lists_exactly_the_five_uncomputable_dimensions():
    """With clean profile/stats/weekly and fewer weekly points than the
    engine's own MIN_SAMPLE_SIZE (Monte Carlo necessarily invalid --
    MIN_SAMPLE_SIZE moved from 20 to 10 after this test was first written,
    see monte_carlo.py's own comment on why; the point of this test is
    "too few points to run at all", which still needs a count strictly
    below whatever that threshold currently is, not the literal number 12),
    `unavailable` must be exactly the five dimensions the task specifies --
    no more (a spurious extra would mislead a reader into thinking
    something else is also missing), no less."""
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=_weekly_points(n=MonteCarloSimulationEngine.MIN_SAMPLE_SIZE - 1),
    )
    assert set(result["unavailable"]) == CANONICAL_UNAVAILABLE
    # Order matches the task's own contract example.
    assert result["unavailable"] == [
        "profit_factor",
        "deferred_loss",
        "phase_analysis",
        "monte_carlo",
        "psr_dsr",
    ]


def test_missing_stats_adds_win_ratio_to_unavailable():
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=None,
        # Below MIN_SAMPLE_SIZE on purpose (not the helper's default n=12,
        # which clears the engine's current threshold and would make
        # "monte_carlo" wrongly absent from `unavailable`, breaking the
        # `CANONICAL_UNAVAILABLE.issubset(...)` check below) -- this test is
        # about `stats=None`, not about Monte Carlo, so it keeps MC on the
        # "genuinely too few points" side deliberately.
        weekly=_weekly_points(n=MonteCarloSimulationEngine.MIN_SAMPLE_SIZE - 1),
    )
    assert "win_ratio" in result["unavailable"]
    assert CANONICAL_UNAVAILABLE.issubset(set(result["unavailable"]))


def test_missing_profile_adds_profile_to_unavailable_and_falls_back_name():
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=None,
        stats=_clean_stats(),
        # Same reasoning as test_missing_stats_adds_win_ratio_to_unavailable
        # above: below MIN_SAMPLE_SIZE so Monte Carlo stays uncomputable and
        # CANONICAL_UNAVAILABLE.issubset(...) still holds.
        weekly=_weekly_points(n=MonteCarloSimulationEngine.MIN_SAMPLE_SIZE - 1),
    )
    assert "profile" in result["unavailable"]
    assert result["name"] == "CODE1"


# ---------------------------------------------------------------------------
# NOT_FOUND
# ---------------------------------------------------------------------------


def test_not_found_contract_and_message():
    result = assess_limited_bot(
        code="GARBAGE999",
        status=STATUS_NOT_FOUND,
        # Đúng hình dạng `bot_source` sinh ra trong sản phẩm thật (tiếng
        # Anh -- agent phục vụ marketplace toàn cầu). Trước đây test này
        # truyền một chuỗi tiếng Việt mà sản phẩm không còn sinh ra nữa.
        reason=(
            "Bot with code 'GARBAGE999' was not found on OKX, or OKX "
            "temporarily failed to respond for this code"
        ),
    )
    assert result["status"] == STATUS_NOT_FOUND
    assert result["risk"] is None
    assert result["quality"] is None
    assert result["confidence"] == NOT_FOUND_CONFIDENCE
    assert result["mc"] is None
    assert result["verdict"] == "NOT FOUND"
    assert set(result["unavailable"]) == CANONICAL_UNAVAILABLE | {PSR_DSR_KEY}
    joined = " ".join(result["text"])
    # Khẳng định trên câu CHÍNH SẢN PHẨM viết ra, không phải trên `reason`
    # test vừa truyền vào. Bản trước kiểm ba cụm tiếng Việt và chỉ xanh vì
    # test tự nạp đúng chuỗi tiếng Việt đó ở trên rồi tìm lại nó ở đầu ra --
    # một khẳng định tự thoả mãn, không kiểm được gì.
    assert "wrong or nonexistent uniqueCode" in joined
    assert "not a bot hiding its ledger" in joined


def test_not_found_confidence_is_lower_than_any_limited_confidence():
    not_found = assess_limited_bot(
        code="GARBAGE999",
        status=STATUS_NOT_FOUND,
        reason="Bot with code 'GARBAGE999' was not found on OKX",
    )
    limited = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=_weekly_points(),
    )
    assert not_found["confidence"] < limited["confidence"]


# ---------------------------------------------------------------------------
# Monte Carlo: must respect MIN_SAMPLE_SIZE, never fabricate from too few
# points, and never stay silent about a thin-but-valid sample.
#
# History: this block originally pinned MIN_SAMPLE_SIZE=20, under which a
# typical 60004 bot's ~12 published weekly points always refused to run --
# `test_monte_carlo_with_twelve_weekly_points_is_invalid_and_reported_honestly`
# below used to assert exactly that. MIN_SAMPLE_SIZE has since moved to 10
# (see Agent/backend/mcp/analytics/simulation/monte_carlo.py's own comment:
# the old threshold had no measured justification and was refusing the
# EXACT bot this module exists for; the project's own phase-confidence
# convention already treats n>=10 as "enough to draw a pattern from"). 12
# now clears MIN_SAMPLE_SIZE, so it runs -- but the ORIGINAL intent behind
# these tests ("never let a thin sample look like a solid one") still
# holds, just expressed differently: instead of refusing to run, the engine
# now runs AND is required to flag the result thin (`sample_is_thin=True`,
# with its own warning) rather than staying silent about it. Nothing here
# should ever hardcode 12 or 20 as literals -- always read
# MonteCarloSimulationEngine.MIN_SAMPLE_SIZE/THIN_SAMPLE_SIZE so a future
# threshold change doesn't silently invalidate the premise again.
# ---------------------------------------------------------------------------


def test_monte_carlo_with_twelve_weekly_points_runs_but_flags_thin_sample():
    """12 weekly points -- the real-world count a 60004 bot like
    ED2DE1A47EEF62EC actually publishes -- clears MIN_SAMPLE_SIZE (10) but
    stays below THIN_SAMPLE_SIZE (20), so the engine must run for real AND
    say plainly that this is a thin sample: never a numeric result that
    looks as solid as a >=20-point one, and never a silent `mc=None` either
    (that would hide a bot lucky enough to reach 12 points behind the same
    "not computable" wall as one with only 2)."""
    assert (
        MonteCarloSimulationEngine.MIN_SAMPLE_SIZE
        <= 12
        < MonteCarloSimulationEngine.THIN_SAMPLE_SIZE
    ), (
        "this test's premise (12 weekly points clears MIN_SAMPLE_SIZE but "
        "stays below THIN_SAMPLE_SIZE) must hold for the engine's current "
        "thresholds"
    )
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=_weekly_points(n=12),
    )
    assert result["mc"] is not None
    assert result["mc"]["is_valid"] is True
    assert result["mc"]["sample_size"] == 12
    assert result["mc"]["sample_is_thin"] is True
    assert MONTE_CARLO_KEY not in result["unavailable"]
    mc_component = next(
        c for c in result["evidence"]["components"] if c["name"] == MONTE_CARLO_KEY
    )
    assert mc_component["status"] == "AVAILABLE"
    joined = " ".join(result["text"])
    assert "THIN SAMPLE" in joined or "thin sample" in joined.lower()


def test_monte_carlo_below_min_sample_size_is_invalid_and_reported_honestly():
    """Below MIN_SAMPLE_SIZE (not merely thin), the engine must still
    refuse outright -- this is the "genuinely too few points" case the
    original 12-point test was written to cover, kept alive here with a
    count that is guaranteed to stay below the threshold regardless of its
    current value."""
    n = MonteCarloSimulationEngine.MIN_SAMPLE_SIZE - 1
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=_weekly_points(n=n),
    )
    assert result["mc"] is None
    assert MONTE_CARLO_KEY in result["unavailable"]
    joined = " ".join(result["text"])
    assert "Not enough samples" in joined
    assert str(MonteCarloSimulationEngine.MIN_SAMPLE_SIZE) in joined
    assert str(n) in joined
    mc_component = next(
        c for c in result["evidence"]["components"] if c["name"] == MONTE_CARLO_KEY
    )
    assert mc_component["status"] != "AVAILABLE"
    assert mc_component["confidence"] == 0.0


def test_monte_carlo_never_fabricates_percentiles_from_too_few_points():
    """Belt-and-braces on the module's most dangerous failure mode: even
    inside the raw evidence blob, no simulated percentile/probability field
    from an invalid run should leak through as if it were real. Uses a
    count below MIN_SAMPLE_SIZE (not the module's old 12-point example,
    which now legitimately runs) so the premise "too few points to run at
    all" stays true regardless of the exact threshold value."""
    n = MonteCarloSimulationEngine.MIN_SAMPLE_SIZE - 1
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=_weekly_points(n=n),
    )
    assert result["mc"] is None
    dumped = json.dumps(result["evidence"], ensure_ascii=False)
    # is_valid=False leaves every percentile/probability field None on the
    # engine's own SimulationResults -- nothing here should serialize one.
    assert "p_mdd_gt_25" not in dumped


def test_monte_carlo_with_enough_weekly_points_uses_the_real_engine_result():
    """At/above THIN_SAMPLE_SIZE the engine validates AND does not flag the
    result thin -- this must surface as real (not fabricated) engine
    output, not be forced to null just because this is a LIMITED
    assessment, and not carry a thin-sample warning it does not need."""
    n = MonteCarloSimulationEngine.THIN_SAMPLE_SIZE + 5
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=_weekly_points(n=n, base_pnl=200.0, base_ratio=0.03),
    )
    assert result["mc"] is not None
    assert result["mc"]["is_valid"] is True
    assert result["mc"]["sample_size"] == n
    assert result["mc"]["sample_is_thin"] is False
    assert MONTE_CARLO_KEY not in result["unavailable"]


# ---------------------------------------------------------------------------
# The task's most important invariant: concealment must never score better
# than transparency for the same surface numbers.
# ---------------------------------------------------------------------------


def test_limited_bot_never_scores_better_than_an_equivalent_transparent_bot(bot_top):
    """bot_top (Modern-dAPI-Manatee) is a real, clean, reconciled FULL bot
    (see conftest.py). Its own real overview.json is used to build a LIMITED
    payload with IDENTICAL surface numbers (same weekly PnL history, same
    aum/pnl/leadDays/winRatio) -- the only difference is that this version
    "hides its ledger". A real QCCoreService.assess_bot run on the actual
    bot_top fixture supplies the FULL-side numbers, so this is not a
    self-referential check against this module's own internals.

    Must hold: risk(LIMITED) >= risk(FULL) and confidence(LIMITED) <
    confidence(FULL) -- a transparent bot must never come out looking riskier
    or less trustworthy than an opaque one with the same visible numbers.
    """
    full = QCCoreService.assess_bot(None, bot_top)

    overview_path = (
        DATA_DIR / "trade" / "bot_BB3398A957270A39" / "overview.json"
    )
    overview = json.loads(overview_path.read_text(encoding="utf-8"))
    win_ratio = float(overview["winRatio"])
    profit_days = round(win_ratio * 365)
    loss_days = 365 - profit_days

    profile = {
        "uniqueCode": overview["uniqueCode"],
        "nickName": overview["nickName"],
        "aum": overview["aum"],
        "pnl": overview["pnl"],
        "pnlRatio": overview["pnlRatio"],
        "leadDays": overview["leadDays"],
        "rank": 1,
    }
    stats = {
        "winRatio": overview["winRatio"],
        "investAmt": "10000",
        "profitDays": str(profit_days),
        "lossDays": str(loss_days),
    }

    limited = assess_limited_bot(
        code=overview["uniqueCode"],
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=profile,
        stats=stats,
        weekly=overview["weekly_pnl_history"],
    )

    assert limited["risk"] >= full.risk_score, (
        f"LIMITED risk {limited['risk']} must not be lower than FULL risk "
        f"{full.risk_score} for the same surface numbers"
    )
    assert limited["confidence"] < full.confidence, (
        f"LIMITED confidence {limited['confidence']} must be lower than FULL "
        f"confidence {full.confidence}"
    )
    # And a structural sanity check independent of bot_top's specific numbers:
    # LIMITED confidence can never reach the ceiling this module enforces.
    assert limited["confidence"] <= LIMITED_CONFIDENCE_CEILING


def test_limited_confidence_ceiling_holds_even_for_maximally_clean_surface_data():
    """However good the surface numbers look (perfect win ratio, no
    drawdown, long track record), LIMITED confidence must never cross the
    ceiling -- it has zero trade-level evidence by construction."""
    pristine_profile = {
        "uniqueCode": "CODE1",
        "nickName": "Pristine",
        "aum": "100000",
        "pnl": "50000",
        "pnlRatio": "0.5",
        "leadDays": "2000",
        "rank": 1,
    }
    pristine_stats = {
        "winRatio": "0.95",
        "investAmt": "50000",
        "profitDays": "350",
        "lossDays": "15",
    }
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=pristine_profile,
        stats=pristine_stats,
        weekly=_weekly_points(n=12, base_pnl=1000.0, base_ratio=0.08),
    )
    assert result["confidence"] <= LIMITED_CONFIDENCE_CEILING


# ---------------------------------------------------------------------------
# evidence.weekly_series / pnl_ratio_series / drawdown_summary -- structured
# fields added on top of the original contract so the report page can draw
# real charts/tables instead of the bare point COUNT `weekly_points` alone
# gave it. Every one of these must (a) contain real content shaped exactly
# like the builder that reads them expects, (b) be sorted ascending by
# time, (c) fall back to an absent/empty value -- never a fabricated one --
# when the underlying data cannot support it, and (d) never move
# risk/quality/confidence/verdict by even one unit, since they are pure
# additions to `evidence`, not new inputs to the scoring formulas above.
# ---------------------------------------------------------------------------


def test_weekly_series_matches_equity_curve_points_in_time_order():
    weekly = _weekly_points(n=6)
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=weekly,
    )
    series = result["evidence"]["weekly_series"]
    assert isinstance(series, list) and len(series) == 6
    for row in series:
        assert set(row.keys()) == {"begin_ts", "equity", "pnl", "pnl_ratio"}
        # _weekly_points() uses ratios well above the equity-curve builder's
        # precision floor, so every week here is usable -- equity/pnl/ratio
        # must all be real numbers, never fabricated placeholders.
        assert isinstance(row["equity"], float) and row["equity"] > 0
        assert isinstance(row["pnl"], float)
        assert isinstance(row["pnl_ratio"], float)
    # Ascending by begin_ts -- _weekly_points() itself emits DESCENDING
    # timestamps (index 0 is the most recent week), so this only holds if
    # the builder's own sort actually ran.
    timestamps = [row["begin_ts"] for row in series]
    assert timestamps == sorted(timestamps)


def test_weekly_series_marks_unusable_weeks_with_none_equity_not_zero():
    """A week whose pnlRatio is below the equity-curve builder's precision
    floor must come back with `equity=None`, never `0.0` -- 0 would read as
    "equity crashed to zero", a very different (and false) claim from "we
    could not derive equity this week"."""
    weekly = [
        {"beginTs": "1700000000000", "pnl": "10.0", "pnlRatio": "0.0001"},
        {"beginTs": "1700604800000", "pnl": "500.0", "pnlRatio": "0.05"},
    ]
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=weekly,
    )
    series = result["evidence"]["weekly_series"]
    assert series[0]["equity"] is None
    assert series[1]["equity"] is not None


def test_weekly_series_is_empty_list_never_none_when_no_weekly_data():
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=None,
    )
    assert result["evidence"]["weekly_series"] == []


def test_pnl_ratio_series_normalizes_and_sorts_profile_pnl_ratios():
    profile = _clean_profile()
    # Deliberately out of time order and mixed str/number types, like a raw
    # OKX payload could plausibly be -- the function must sort by beginTs
    # regardless of input order and accept either type.
    profile["pnlRatios"] = [
        {"beginTs": "1700604800000", "pnlRatio": "0.10"},
        {"beginTs": 1700000000000, "pnlRatio": 0.02},
        {"beginTs": "1701209600000", "pnlRatio": "not-a-number"},  # dropped
        {"pnlRatio": "0.30"},  # missing beginTs, dropped
    ]
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=profile,
        stats=_clean_stats(),
        weekly=_weekly_points(),
    )
    series = result["evidence"]["pnl_ratio_series"]
    assert series == [
        {"ts_ms": 1700000000000, "pnl_ratio_pct": 2.0},
        {"ts_ms": 1700604800000, "pnl_ratio_pct": 10.0},
    ]


def test_pnl_ratio_series_is_none_when_profile_has_no_ratios_history():
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),  # no "pnlRatios" key
        stats=_clean_stats(),
        weekly=_weekly_points(),
    )
    assert result["evidence"]["pnl_ratio_series"] is None


def test_drawdown_summary_matches_the_component_it_was_scored_from():
    weekly = _weekly_points(n=8)
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=weekly,
    )
    summary = result["evidence"]["drawdown_summary"]
    drawdown_component = next(
        c for c in result["evidence"]["components"] if c["name"] == "drawdown"
    )
    assert summary is not None
    assert set(summary.keys()) == {
        "max_dd_pct",
        "usable_weeks",
        "total_weeks",
        "wiped_out",
    }
    # The findings string is prose built from these exact numbers -- if the
    # summary ever drifted from what was actually scored, the percentage in
    # that sentence and `summary["max_dd_pct"]` would disagree.
    assert f"{summary['max_dd_pct']:.1f}%" in drawdown_component["findings"][0]
    assert (
        f"{summary['usable_weeks']}/{summary['total_weeks']}"
        in (drawdown_component["findings"][0])
    )


def test_drawdown_summary_is_none_when_equity_curve_is_unusable():
    """No weekly data at all -> the curve basis is UNAVAILABLE -> there is
    no max_drawdown_pct to report -- `drawdown_summary` must be `None`, not
    a dict of zeros (a bot with unmeasured drawdown must never look
    identical to a bot measured at exactly 0% drawdown)."""
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=None,
    )
    assert result["evidence"]["drawdown_summary"] is None


def test_new_evidence_fields_never_move_the_score():
    """The three fields above are pure additions to `evidence` -- this pins
    risk/quality/confidence/verdict to the exact values a comparable call
    without them would have produced, by checking they equal what the
    dimension components (the actual scoring inputs) alone would imply.
    Concretely: two calls with IDENTICAL inputs must produce identical
    risk/quality/confidence/verdict regardless of what `weekly_series`/
    `pnl_ratio_series`/`drawdown_summary` happen to contain -- i.e. those
    keys are write-only outputs, never read back into the formulas above.
    """
    kwargs = dict(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=_weekly_points(n=12),
    )
    first = assess_limited_bot(**kwargs)
    second = assess_limited_bot(**kwargs)
    for key in ("risk", "quality", "confidence", "verdict"):
        assert first[key] == second[key]
    # Cross-check against the actual scoring inputs (the component list),
    # rounded the same way `assess_limited_bot` itself rounds `risk` -- a
    # real regression lock tying the score to its components, not just
    # "equal to itself".
    components = first["evidence"]["components"]
    total_weight = sum(c["weight"] for c in components)
    expected_risk = sum(c["score"] * c["weight"] for c in components) / total_weight
    assert first["risk"] == round(expected_risk, 1)


# ---------------------------------------------------------------------------
# assess_from_error wiring
# ---------------------------------------------------------------------------


def test_assess_from_error_matches_direct_call_with_the_same_fields():
    exc = LedgerUnavailableError(
        status=STATUS_LIMITED,
        code="CODE1",
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=_weekly_points(),
    )
    via_error = assess_from_error(exc)
    direct = assess_limited_bot(
        code=exc.code,
        status=exc.status,
        reason=str(exc),
        profile=exc.profile,
        stats=exc.stats,
        weekly=exc.weekly,
    )
    assert via_error == direct


def test_assess_from_error_not_found():
    exc = LedgerUnavailableError(
        status=STATUS_NOT_FOUND,
        code="GARBAGE999",
        reason="Bot with code 'GARBAGE999' was not found on any OKX endpoint",
    )
    result = assess_from_error(exc)
    assert result["status"] == STATUS_NOT_FOUND
    assert result["code"] == "GARBAGE999"


def test_invalid_status_raises():
    with pytest.raises(ValueError):
        assess_limited_bot(code="CODE1", status="FULL", reason="n/a")
