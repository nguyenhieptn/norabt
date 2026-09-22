"""Tests for `Agent/backend/web/score_basis.py`.

The one test that matters most here is the "khoá chống trôi" the module's
own docstring promises: `limited_confidence_breakdown`/`limited_fusion_summary`
duplicate a few small formulas out of `Agent/backend/analysis/limited.py`
(noisy-OR combine, coverage, the per-stream confidence ceiling) so the report
page can show a bot-specific breakdown without importing private names --
if `limited.py`'s own constants or formula ever change without this module
being updated to match, this test must fail loudly rather than let the two
silently disagree on what a bot's own confidence number means.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from Agent.backend.bot.analysis.limited import STATUS_LIMITED, assess_limited_bot
from Agent.backend.web import score_basis


def _weekly_points(n: int = 12) -> List[Dict[str, Any]]:
    start_ts = 1_788_710_400_000
    return [
        {
            "beginTs": str(start_ts - i * 604_800_000),
            "pnl": str(500.0 + i * 15.0),
            "pnlRatio": str(0.05 + i * 0.002),
        }
        for i in range(n)
    ]


def _profile() -> Dict[str, Any]:
    return {
        "uniqueCode": "CODE1",
        "nickName": "Test Lead Trader",
        "aum": "20000.0",
        "pnl": "9000.0",
        "pnlRatio": "0.45",
        "leadDays": "400",
        "rank": 3,
        "pnlRatios": [
            {
                "beginTs": str(1_788_710_400_000 - i * 5 * 86_400_000),
                "pnlRatio": str(0.4 + i * 0.03),
            }
            for i in range(19)
        ],
    }


def _stats() -> Dict[str, Any]:
    return {
        "winRatio": "0.62",
        "investAmt": "15000.0",
        "profitDays": "220",
        "lossDays": "135",
    }


def _real_limited_result() -> Dict[str, Any]:
    return assess_limited_bot(
        code="CODE1",
        status=STATUS_LIMITED,
        reason="OKX trả lỗi 60004 ở endpoint sổ lệnh",
        profile=_profile(),
        stats=_stats(),
        weekly=_weekly_points(),
    )


def test_limited_confidence_breakdown_matches_assess_limited_bot() -> None:
    """The recomputed `implied_confidence_pct` must land on the SAME number
    `assess_limited_bot` itself reports (within its own 1-decimal rounding)
    -- this is the drift guard the module docstring promises. A real
    divergence here means the duplicated constants/formula have gone out of
    sync with `limited.py` and the report page would be showing a made-up
    breakdown for a real number.
    """
    result = _real_limited_result()
    breakdown = score_basis.limited_confidence_breakdown(result["evidence"])
    assert breakdown is not None
    assert breakdown["implied_confidence_pct"] == pytest.approx(
        result["confidence"], abs=0.15
    )


def test_limited_fusion_summary_matches_reported_risk() -> None:
    """LIMITED has no veto/emergency override -- the weighted average this
    module recomputes from `evidence.components` must equal `result["risk"]`
    exactly (both are the same weighted-average formula over the same
    components, see `Agent/backend/analysis/limited.py::assess_limited_bot`).
    """
    result = _real_limited_result()
    components = score_basis.limited_risk_components(result["evidence"])
    fusion = score_basis.limited_fusion_summary(components)
    assert fusion["weighted_average"] == pytest.approx(result["risk"], abs=0.15)


def test_limited_confidence_breakdown_streams_and_ceiling_are_consistent() -> None:
    result = _real_limited_result()
    breakdown = score_basis.limited_confidence_breakdown(result["evidence"])
    assert breakdown is not None
    assert 0 <= breakdown["streams"] <= 4
    assert breakdown["ceiling_pct"] == min(45.0, 15.0 + 7.5 * breakdown["streams"])
    assert breakdown["implied_confidence_pct"] <= breakdown["ceiling_pct"] + 1e-9


def test_full_risk_dimensions_empty_for_missing_evidence() -> None:
    assert score_basis.full_risk_dimensions({}) == []
    assert score_basis.full_risk_dimensions(None) == []


def test_full_fusion_summary_degrades_gracefully_on_sparse_disk_shape() -> None:
    """The disk-read `assessment_to_analyze_result` shape only carries
    decided_by/veto_reasons/weighted_average/hidden_risk_flags on
    `score_breakdown` -- `total_weight`/`contributions` are absent. This
    must come back as `has_rich_breakdown=False`, not raise or fabricate a
    total weight.
    """
    evidence = {
        "score_breakdown": {
            "decided_by": "WEIGHTED_AVERAGE",
            "veto_reasons": [],
            "weighted_average": 42.0,
            "hidden_risk_flags": [],
        }
    }
    summary = score_basis.full_fusion_summary(evidence)
    assert summary["has_rich_breakdown"] is False
    assert summary["total_weight"] is None
    assert summary["weighted_average"] == 42.0


def test_quality_basis_limited_reads_real_inputs() -> None:
    result = _real_limited_result()
    basis = score_basis.quality_basis_limited(result["evidence"])
    assert basis is not None
    assert basis["lead_days"] == 400
    assert basis["pnl"] == 9000.0
    assert basis["win_ratio_pct"] == pytest.approx(62.0)
    assert basis["wiped_out"] is False
    assert basis["cap"] == 75.0


def test_quality_basis_limited_none_when_no_public_data() -> None:
    assert score_basis.quality_basis_limited({"profile": None, "stats": None}) is None
