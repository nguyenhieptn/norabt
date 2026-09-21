"""Tests for `Agent/backend/web/data.py`'s bot-listing normalization
(`bot_listing_row`/`list_bot_listing_rows`) -- the single function `GET
/api/bots` (app.py's `api_bots`, via `WebDataService.list_bot_rows`) uses to
turn a raw `assessment.json` document into a screen-ready row.

This used to be `Agent/backend/web/admin_page.py`'s own `_row_from_assessment`
/ `merge_bot_rows`, tested in the now-deleted `test_admin_page.py`. Việc 3
retired that module (a second, independent implementation of the same
listing, which is exactly how Việc 1's bug happened: one surface read a
retired label field the other did not) -- the HTML-rendering and
`RecentCodeRegistry`-merge concerns that file also tested went with it
(`GET /admin` is now a plain redirect, see test_web_app.py's own admin-route
tests); what remains here is the normalization itself, now living in
data.py and shared by every consumer of `GET /api/bots`.
"""

from __future__ import annotations

from typing import Any, Dict, List

from Agent.backend.web.data import bot_listing_row, list_bot_listing_rows

# --------------------------------------------------------------------------- #
# Fixture builder
# --------------------------------------------------------------------------- #


def _assessment(
    *,
    code: str,
    name: str = "Bot",
    venue_type: str = "CEX",
    traded_symbol: str = "ETH",
    old_verdict: str = "TIỀM ẨN",
    risk: float = 50.0,
    quality: float = 50.0,
    confidence: float = 50.0,
    trade_count: int = 100,
    total_pnl: float = 1000.0,
    decided_by: str = "WEIGHTED_AVERAGE",
    veto_reasons: Any = None,
    hidden_risk_flags: Any = None,
    generated_at_ms: int = 1_700_000_000_000,
) -> Dict[str, Any]:
    """One `assessment.json`-shaped document (real on-disk shape: `bot`,
    `khuyen_nghi`, `cham_diem`, `bang_chung`, `mo_phong`). `old_verdict`
    only ever lands in `khuyen_nghi.ket_luan` -- the retired field
    `bot_listing_row` must NEVER read, per Việc 1's own bug report.
    """
    return {
        "step": "3_QC_ASSESSMENT",
        "schema_version": "bot_assessment.v1",
        "generated_at_ms": generated_at_ms,
        "bot": {
            "nick_name": name,
            "unique_code": code,
            "venue_type": venue_type,
            "traded_symbol": traded_symbol,
        },
        "recommendation": {
            "verdict": old_verdict,
            "risk_score": risk,
            "quality_score": quality,
            "confidence": confidence,
        },
        "scoring": {
            "risk_score": risk,
            "quality_score": quality,
            "score_decided_by": decided_by,
            "veto_reasons": veto_reasons or [],
            "hidden_risk_flags": hidden_risk_flags or [],
        },
        "evidence": {
            "trade_count": trade_count,
            "total_pnl": total_pnl,
        },
        "simulation": {},
    }


# --------------------------------------------------------------------------- #
# bot_listing_row -- Việc 1's own regression guard: the verdict is ALWAYS
# recomputed from scores, never read verbatim off `khuyen_nghi.ket_luan`.
# --------------------------------------------------------------------------- #


def test_verdict_is_recomputed_never_read_from_the_retired_field() -> None:
    doc = _assessment(code="AAA", old_verdict="NGUY HIỂM", risk=10.0, quality=90.0)
    row = bot_listing_row(doc)
    assert row is not None
    assert row["verdict"] != "NGUY HIỂM"
    assert row["verdict"] == "DRAWDOWN: LOW · QUALITY: GOOD"


def test_hidden_risk_flags_override_low_risk_and_good_quality() -> None:
    doc = _assessment(
        code="AAA",
        risk=10.0,
        quality=95.0,
        hidden_risk_flags=["lỗ chưa chốt bằng 65% vốn"],
    )
    row = bot_listing_row(doc)
    assert row is not None
    assert row["verdict"] == "HIDDEN RISK"


def test_basic_row_shape() -> None:
    row = bot_listing_row(_assessment(code="AAA"))
    assert row is not None
    assert row["code"] == "AAA"
    assert row["name"] == "Bot"
    assert row["venue_asset"] == "CEX · ETH"
    assert row["risk"] == 50.0
    assert row["quality"] == 50.0
    assert row["confidence"] == 50.0
    assert row["trade_count"] == 100
    assert row["total_pnl"] == 1000.0
    assert row["is_veto"] is False
    assert row["veto_reasons"] == []
    assert row["generated_at_ms"] == 1_700_000_000_000


def test_veto_decided_by_sets_is_veto_true() -> None:
    row = bot_listing_row(
        _assessment(
            code="AAA", decided_by="VETO_FLOOR", veto_reasons=["rủi ro đuôi cực đoan"]
        )
    )
    assert row is not None
    assert row["is_veto"] is True
    assert row["veto_reasons"] == ["rủi ro đuôi cực đoan"]


def test_malformed_documents_return_none_without_crashing() -> None:
    malformed: List[Any] = [
        None,
        "not-a-dict",
        {},
        {"bot": {}},  # no unique_code
        {"bot": {"unique_code": ""}},  # blank code
        {"bot": {"unique_code": 12345}},  # code not a string
    ]
    for doc in malformed:
        assert bot_listing_row(doc) is None


def test_document_missing_subsections_degrades_to_placeholders() -> None:
    doc = {"bot": {"unique_code": "BARE", "nick_name": "Bare"}}
    row = bot_listing_row(doc)
    assert row is not None
    assert row["code"] == "BARE"
    assert row["risk"] is None
    assert row["quality"] is None
    assert row["verdict"] == "INSUFFICIENT EVIDENCE"


def test_falls_back_to_khuyen_nghi_scores_when_cham_diem_missing() -> None:
    """An even older assessment.json shape with no `cham_diem` block at all
    -- backward compatibility with `khuyen_nghi.diem_rui_ro`/
    `diem_chat_luong` (see `bot_listing_row`'s own field-precedence rule).
    """
    doc = {
        "bot": {"unique_code": "OLD", "nick_name": "Old"},
        "recommendation": {
            "verdict": "AN TOÀN",
            "risk_score": 15.0,
            "quality_score": 70.0,
        },
    }
    row = bot_listing_row(doc)
    assert row is not None
    assert row["risk"] == 15.0
    assert row["quality"] == 70.0
    assert row["verdict"] == "DRAWDOWN: LOW · QUALITY: GOOD"


# --------------------------------------------------------------------------- #
# list_bot_listing_rows -- dedup by code, first occurrence wins
# --------------------------------------------------------------------------- #


def test_list_bot_listing_rows_reads_real_committed_dataset() -> None:
    from Agent.backend.infra.config import config
    from pathlib import Path

    rows = list_bot_listing_rows(Path(config.DATA_DIR))
    assert len(rows) >= 30
    codes = {r["code"] for r in rows}
    assert "811997770117827919" in codes


def test_list_bot_listing_rows_dedupes_by_code(monkeypatch, tmp_path) -> None:
    from Agent.backend.web import data as data_module

    monkeypatch.setattr(
        data_module,
        "list_scored_bots",
        lambda data_dir: [
            _assessment(code="AAA", risk=10.0),
            _assessment(code="AAA", risk=90.0),
        ],
    )
    rows = list_bot_listing_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["risk"] == 10.0
