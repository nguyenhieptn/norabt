"""Tests for `Agent/backend/web/admin_page.py` -- the pure renderer behind
`GET /admin` (see that module's own docstring for the contract: a list of
`assessment.json`-shaped documents plus a list of bare `RecentCodeRegistry`
codes in, one self-contained HTML string out, no I/O of its own).

Route-level access control (404 vs 200, the disk-read cache) is
`Agent/backend/web/app.py`'s job and is tested in `test_web_app.py`
alongside every other route; this file only tests what `admin_page.py` does
with data it is handed directly.

Mirrors `test_report_page.py`'s own three concerns for the same reasons:
XSS (a bot's `nick_name`/venue/veto reasons are OKX-sourced, fully
attacker-controlled), never crashing on missing/partial/empty data, and
every emitted `<svg>` being well-formed XML with no non-finite attribute
value.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List
from xml.etree import ElementTree

import pytest

from Agent.backend.web.admin_page import (
    DEFAULT_SORT,
    merge_bot_rows,
    render_admin_page_html,
    sort_rows,
)

# --------------------------------------------------------------------------- #
# SVG-validity helpers -- same approach as test_report_page.py's own.
# --------------------------------------------------------------------------- #

_BAD_TOKENS = ("nan", "inf", "-inf", "none", "undefined")
_ATTR_VALUE_RE = re.compile(r'="([^"]*)"')


def _assert_no_bad_numeric_attrs(svg_fragment: str) -> None:
    for match in _ATTR_VALUE_RE.finditer(svg_fragment):
        value = match.group(1).strip().lower()
        assert value not in _BAD_TOKENS, f"bad SVG attribute value: {match.group(0)!r}"


def _extract_svgs(html_doc: str) -> List[str]:
    return re.findall(r"<svg[^>]*>.*?</svg>", html_doc, flags=re.DOTALL)


def _assert_valid_xml_fragment(fragment: str) -> None:
    ElementTree.fromstring(fragment)


def _assert_all_svgs_valid(html_doc: str) -> List[str]:
    svgs = _extract_svgs(html_doc)
    for svg in svgs:
        _assert_valid_xml_fragment(svg)
        _assert_no_bad_numeric_attrs(svg)
    return svgs


# --------------------------------------------------------------------------- #
# Fixture builders
# --------------------------------------------------------------------------- #


def _assessment(
    *,
    code: str,
    name: str = "Bot",
    venue_type: str = "CEX",
    traded_symbol: str = "ETH",
    verdict: str = "TIỀM ẨN",
    risk: float = 50.0,
    quality: float = 50.0,
    confidence: float = 50.0,
    trade_count: int = 100,
    total_pnl: float = 1000.0,
    decided_by: str = "WEIGHTED_AVERAGE",
    veto_reasons: Any = None,
    generated_at_ms: int = 1_700_000_000_000,
) -> Dict[str, Any]:
    """One `assessment.json`-shaped document (see admin_page.py's own
    docstring for the real on-disk shape this mirrors: `bot`, `khuyen_nghi`,
    `cham_diem`, `bang_chung`, `mo_phong`).
    """
    return {
        "step": "3_QC_DANH_GIA",
        "schema_version": "bot_assessment.v1",
        "generated_at_ms": generated_at_ms,
        "bot": {
            "nick_name": name,
            "unique_code": code,
            "venue_type": venue_type,
            "traded_symbol": traded_symbol,
        },
        "khuyen_nghi": {
            "ket_luan": verdict,
            "diem_rui_ro": risk,
            "diem_chat_luong": quality,
            "do_tin_cay": confidence,
        },
        "cham_diem": {
            "risk_score": risk,
            "quality_score": quality,
            "score_decided_by": decided_by,
            "veto_reasons": veto_reasons or [],
        },
        "bang_chung": {
            "trade_count": trade_count,
            "total_pnl": total_pnl,
        },
        "mo_phong": {},
    }


# --------------------------------------------------------------------------- #
# merge_bot_rows -- dedup across the two sources
# --------------------------------------------------------------------------- #


def test_merge_disk_only() -> None:
    rows = merge_bot_rows([_assessment(code="AAA")], [])
    assert len(rows) == 1
    assert rows[0]["code"] == "AAA"
    assert rows[0]["registry_only"] is False


def test_merge_registry_only_code_becomes_a_placeholder_row() -> None:
    rows = merge_bot_rows([], ["BBB"])
    assert len(rows) == 1
    row = rows[0]
    assert row["code"] == "BBB"
    assert row["registry_only"] is True
    assert row["name"] is None
    assert row["risk"] is None
    assert row["verdict"] == "THIẾU BẰNG CHỨNG"


def test_merge_dedupes_by_code_disk_wins_over_registry() -> None:
    """The SAME code on disk AND in the registry must appear exactly once,
    keeping the real scored data rather than the bare placeholder."""
    rows = merge_bot_rows([_assessment(code="AAA", risk=77.0)], ["AAA"])
    assert len(rows) == 1
    assert rows[0]["risk"] == 77.0
    assert rows[0]["registry_only"] is False


def test_merge_dedupes_within_each_source_too() -> None:
    rows = merge_bot_rows(
        [_assessment(code="AAA"), _assessment(code="AAA")], ["BBB", "BBB"]
    )
    codes = [r["code"] for r in rows]
    assert codes.count("AAA") == 1
    assert codes.count("BBB") == 1


def test_merge_skips_malformed_documents_without_crashing() -> None:
    malformed: List[Any] = [
        None,
        "not-a-dict",
        {},
        {"bot": {}},  # no unique_code
        {"bot": {"unique_code": ""}},  # blank code
        {"bot": {"unique_code": 12345}},  # code not a string
    ]
    rows = merge_bot_rows(malformed, [None, "", "  ", 123])  # type: ignore[list-item]
    assert rows == []


# --------------------------------------------------------------------------- #
# sort_rows -- "nguy hiểm trước" default, unknown always last
# --------------------------------------------------------------------------- #


def test_default_sort_is_risk_descending() -> None:
    rows = merge_bot_rows(
        [
            _assessment(code="LOW", risk=10.0),
            _assessment(code="HIGH", risk=90.0),
            _assessment(code="MID", risk=50.0),
        ],
        [],
    )
    ordered = [r["code"] for r in sort_rows(rows, DEFAULT_SORT)]
    assert ordered == ["HIGH", "MID", "LOW"]


def test_unknown_risk_rows_always_sort_last_regardless_of_direction() -> None:
    rows = merge_bot_rows([_assessment(code="KNOWN", risk=10.0)], ["UNKNOWN_CODE"])
    for sort in ("risk_desc", "risk_asc"):
        ordered = [r["code"] for r in sort_rows(rows, sort)]
        assert ordered[-1] == "UNKNOWN_CODE"


def test_sort_quality_and_confidence_and_name() -> None:
    rows = merge_bot_rows(
        [
            _assessment(code="A", name="Zeta", quality=10.0, confidence=90.0),
            _assessment(code="B", name="Alpha", quality=90.0, confidence=10.0),
        ],
        [],
    )
    assert [r["code"] for r in sort_rows(rows, "quality_desc")] == ["B", "A"]
    assert [r["code"] for r in sort_rows(rows, "confidence_desc")] == ["A", "B"]
    assert [r["code"] for r in sort_rows(rows, "name_asc")] == ["B", "A"]


# --------------------------------------------------------------------------- #
# render_admin_page_html -- empty state, XSS, SVG validity, sort links
# --------------------------------------------------------------------------- #


def test_empty_inputs_render_a_valid_page_with_a_friendly_message() -> None:
    out = render_admin_page_html([], [])
    assert out.startswith("<!doctype html>")
    assert "<html" in out and "</html>" in out
    assert out.count("<svg") == out.count("</svg>")
    assert "Chưa có bot nào" in out
    svgs = _assert_all_svgs_valid(out)
    # The tier pie must still render -- as its own "no data" placeholder,
    # never an empty/broken fragment.
    assert any("Không có dữ liệu" in svg for svg in svgs)


def test_xss_payload_in_name_venue_and_veto_reason_is_escaped() -> None:
    xss = "<script>alert(1)</script>"
    doc = _assessment(
        code="XSSCODE",
        name=xss,
        venue_type=xss,
        traded_symbol="\"'&",
        decided_by="VETO_FLOOR",
        veto_reasons=[xss],
    )
    out = render_admin_page_html([doc], [])
    assert xss not in out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out


def test_xss_payload_in_registry_only_code_is_escaped() -> None:
    xss_code = "<img src=x onerror=alert(1)>"
    out = render_admin_page_html([], [xss_code])
    assert xss_code not in out
    assert "&lt;img" in out


def test_real_data_renders_table_and_every_svg_is_well_formed() -> None:
    docs = [
        _assessment(
            code="D1",
            risk=90.0,
            verdict="NGUY HIỂM",
            decided_by="VETO_FLOOR",
            veto_reasons=["rủi ro đuôi mô phỏng cực đoan"],
            total_pnl=-500.0,
        ),
        _assessment(code="D2", risk=60.0, verdict="TIỀM ẨN", total_pnl=200.0),
        _assessment(code="D3", risk=20.0, verdict="TIỀM NĂNG", total_pnl=300.0),
        _assessment(code="D4", risk=5.0, verdict="AN TOÀN", total_pnl=50.0),
    ]
    out = render_admin_page_html(docs, ["REGISTRY_ONLY_CODE"])
    assert "D1" in out and "D2" in out and "D3" in out and "D4" in out
    assert "REGISTRY_ONLY_CODE" in out
    assert "phiên gần đây" in out
    svgs = _assert_all_svgs_valid(out)
    assert len(svgs) >= 3  # tier pie + risk-bucket bars + veto-reason bars


def test_danger_first_default_ordering_reflected_in_rendered_table() -> None:
    docs = [
        _assessment(code="SAFE", risk=5.0),
        _assessment(code="DANGEROUS", risk=95.0),
    ]
    out = render_admin_page_html(docs, [])
    assert out.index("DANGEROUS") < out.index("SAFE")


def test_unknown_sort_query_value_falls_back_to_default() -> None:
    docs = [
        _assessment(code="SAFE", risk=5.0),
        _assessment(code="DANGEROUS", risk=95.0),
    ]
    out = render_admin_page_html(docs, [], sort="not-a-real-sort-mode")
    assert out.index("DANGEROUS") < out.index("SAFE")


def test_sort_links_preserve_other_query_parameters() -> None:
    out = render_admin_page_html(
        [_assessment(code="A")], [], current_query={"token": "sekret"}
    )
    assert "token=sekret" in out
    assert "sort=risk_asc" in out


def test_row_links_to_bot_detail_page() -> None:
    out = render_admin_page_html([_assessment(code="LINKME")], [])
    assert 'href="/bot/LINKME"' in out


# --------------------------------------------------------------------------- #
# Regression: a document missing whole sub-objects (`khuyen_nghi`,
# `cham_diem`, `bang_chung`) must degrade to placeholder values, never raise.
# --------------------------------------------------------------------------- #


def test_document_missing_subsections_does_not_crash() -> None:
    doc = {"bot": {"unique_code": "BARE", "nick_name": "Bare"}}
    out = render_admin_page_html([doc], [])
    assert "BARE" in out
    _assert_all_svgs_valid(out)


@pytest.mark.parametrize(
    "scored_bots,recent_codes",
    [
        (None, None),
        ([], None),
        (None, []),
        ([{"totally": "unrelated"}], ["x", None, 123, ""]),  # type: ignore[list-item]
    ],
)
def test_render_never_raises_on_ragged_input(
    scored_bots: Any, recent_codes: Any
) -> None:
    out = render_admin_page_html(scored_bots, recent_codes)
    assert out.startswith("<!doctype html>")
