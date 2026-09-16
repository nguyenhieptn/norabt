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

from Agent.backend.analysis.limited import (
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
from Agent.backend.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.qc.service import QCCoreService
from Agent.backend.sources.bot_source import LedgerUnavailableError

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
    assert "ĐÁNH GIÁ HẠN CHẾ" in first
    assert "CODE1" in first


def test_unavailable_lists_exactly_the_five_uncomputable_dimensions():
    """With clean profile/stats/weekly and only 12 weekly points (Monte Carlo
    necessarily invalid), `unavailable` must be exactly the five dimensions
    the task specifies -- no more (a spurious extra would mislead a reader
    into thinking something else is also missing), no less."""
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=_weekly_points(n=12),
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
        weekly=_weekly_points(),
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
        weekly=_weekly_points(),
    )
    assert "profile" in result["unavailable"]
    assert result["name"] == "CODE1"


# ---------------------------------------------------------------------------
# NOT_FOUND
# ---------------------------------------------------------------------------


def test_not_found_contract_and_vietnamese_message():
    result = assess_limited_bot(
        code="GARBAGE999",
        status=STATUS_NOT_FOUND,
        reason=(
            "Không tìm thấy mã GARBAGE999 ở bất kỳ endpoint nào của OKX -- "
            "nhiều khả năng đây là uniqueCode sai hoặc không tồn tại"
        ),
    )
    assert result["status"] == STATUS_NOT_FOUND
    assert result["risk"] is None
    assert result["quality"] is None
    assert result["confidence"] == NOT_FOUND_CONFIDENCE
    assert result["mc"] is None
    assert result["verdict"] == "KHÔNG TÌM THẤY"
    assert set(result["unavailable"]) == CANONICAL_UNAVAILABLE | {PSR_DSR_KEY}
    joined = " ".join(result["text"])
    assert "không tồn tại" in joined or "mã sai" in joined or "uniqueCode sai" in joined


def test_not_found_confidence_is_lower_than_any_limited_confidence():
    not_found = assess_limited_bot(
        code="GARBAGE999",
        status=STATUS_NOT_FOUND,
        reason="Không tìm thấy mã GARBAGE999",
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
# Monte Carlo: must respect MIN_SAMPLE_SIZE, never fabricate from 12 points.
# ---------------------------------------------------------------------------


def test_monte_carlo_with_twelve_weekly_points_is_invalid_and_reported_honestly():
    assert 12 < MonteCarloSimulationEngine.MIN_SAMPLE_SIZE, (
        "this test's premise (12 weekly points is below the engine's real "
        "threshold) must hold for MIN_SAMPLE_SIZE's current value"
    )
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=_weekly_points(n=12),
    )
    assert result["mc"] is None
    assert MONTE_CARLO_KEY in result["unavailable"]
    joined = " ".join(result["text"])
    assert "Không đủ mẫu" in joined
    assert str(MonteCarloSimulationEngine.MIN_SAMPLE_SIZE) in joined
    assert "12" in joined
    mc_component = next(
        c for c in result["evidence"]["components"] if c["name"] == MONTE_CARLO_KEY
    )
    assert mc_component["status"] != "AVAILABLE"
    assert mc_component["confidence"] == 0.0


def test_monte_carlo_never_fabricates_percentiles_from_too_few_points():
    """Belt-and-braces on the module's most dangerous failure mode: even
    inside the raw evidence blob, no simulated percentile/probability field
    from an invalid run should leak through as if it were real."""
    result = assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="Bot không công khai sổ lệnh (OKX trả 60004)",
        profile=_clean_profile(),
        stats=_clean_stats(),
        weekly=_weekly_points(n=12),
    )
    assert result["mc"] is None
    dumped = json.dumps(result["evidence"], ensure_ascii=False)
    # is_valid=False leaves every percentile/probability field None on the
    # engine's own SimulationResults -- nothing here should serialize one.
    assert "p_mdd_gt_25" not in dumped


def test_monte_carlo_with_enough_weekly_points_uses_the_real_engine_result():
    """If a bot somehow has >= MIN_SAMPLE_SIZE weekly points, the engine
    legitimately validates -- this must surface as real (not fabricated)
    engine output, not be forced to null just because this is a LIMITED
    assessment."""
    n = MonteCarloSimulationEngine.MIN_SAMPLE_SIZE + 5
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
        DATA_DIR / "cex" / "MU" / "bot" / "bot_BB3398A957270A39" / "overview.json"
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
        reason="Không tìm thấy mã GARBAGE999 ở bất kỳ endpoint nào của OKX",
    )
    result = assess_from_error(exc)
    assert result["status"] == STATUS_NOT_FOUND
    assert result["code"] == "GARBAGE999"


def test_invalid_status_raises():
    with pytest.raises(ValueError):
        assess_limited_bot(code="CODE1", status="FULL", reason="n/a")
