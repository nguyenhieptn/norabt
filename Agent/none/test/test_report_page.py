"""Tests for `Agent/backend/web/report_page.py` -- the self-contained HTML
`GET /bot/<code>` renders (see that module's own docstring for the contract
it consumes: exactly the dict `WebDataService.analyze()` returns).

Three things this file exists to nail down, because they are the ways this
kind of hand-rolled HTML/SVG generator actually breaks in practice:

  1. XSS: a bot's `nick_name` comes straight from OKX and is fully
     attacker-controlled (whoever registered that copy-trading account picks
     it) -- a `<script>` or a stray `"`/`'`/`&` in it must come out as inert
     text, never as a live tag or a broken attribute.
  2. Partial/missing data must never raise. `mc` is `None` for a lot of real
     bots (LIMITED, or a FULL bot whose simulation never became valid), and
     even a populated `mc` is a pydantic model full of `Optional[float]`
     fields that are frequently `None` -- every section must degrade to
     "not shown" instead of `KeyError`/`TypeError`.
  3. SVG validity: every numeric value that lands in an SVG attribute must
     be a finite, parseable number -- never the literal text "None", "nan",
     "inf" or "-inf", which would be a malformed attribute even though the
     surrounding HTML still parses.

A real FULL fixture is built the same way `Agent/none/test/test_web_app.py` does
(`WebDataService` wired to a fake `BotDataSource`/`MarketDataSource`,
scoring this repo's own committed MU/bot_BB3398A957270A39 fixture) so at
least one test exercises the full pipeline's actual output shape rather
than a hand-typed approximation of it. LIMITED/NOT_FOUND/edge cases are
hand-built dicts matching the documented `/api/analyze` contract directly --
data.py's own responsibility for producing that contract correctly is
already covered by test_web_app.py; this file only tests what report_page.py
does with it.
"""

from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List
from xml.etree import ElementTree

import pytest

from Agent.backend.infra.config import config
from Agent.backend.sources.bot_source import BotDataSource
from Agent.backend.sources.market_source import (
    MarketDataSource,
    MarketDataUnavailableError,
)
from Agent.backend.web.data import WebDataService
from Agent.backend.web.report_page import render_bot_report_html
from Agent.backend.web import report_page as report_page_module

DATA_DIR = Path(config.DATA_DIR)
_FIXTURE_BOT_DIR = DATA_DIR / "cex" / "MU" / "bot" / "bot_BB3398A957270A39"
VALID_CODE = "BB3398A957270A39"


# --------------------------------------------------------------------------- #
# A real FULL result, produced the same way test_web_app.py does (no network,
# no mocked-out internals -- the actual QC/Monte Carlo pipeline runs against
# this repo's own committed fixture ledger).
# --------------------------------------------------------------------------- #


class _StubBotSource(BotDataSource):
    def __init__(self, overview: Dict[str, Any], ledger: Dict[str, Any]) -> None:
        self._overview = overview
        self._ledger = ledger

    def get_overview(self, unique_code, bot_dir=None):  # noqa: ANN001
        return self._overview

    def get_ledger(self, unique_code, bot_dir=None):  # noqa: ANN001
        return self._ledger


class _NoMarketSource(MarketDataSource):
    def resolve_venue(self, symbol, venue_type):  # noqa: ANN001
        raise MarketDataUnavailableError("test: no market source")

    def get_candles(self, symbol, venue_type):  # noqa: ANN001
        raise MarketDataUnavailableError("test: no market source")

    def get_orderbook(self, symbol, venue_type):  # noqa: ANN001
        return {}, "TEST_NO_DATA"

    def get_open_interest(self, symbol, venue_type):  # noqa: ANN001
        return {}, "TEST_NO_DATA"

    def get_taker_volume(self, symbol, venue_type):  # noqa: ANN001
        return {}, "TEST_NO_DATA"

    def get_sentiment(self, symbol, venue_type):  # noqa: ANN001
        return {}, "TEST_NO_DATA"

    def get_ticks(self, symbol, venue_type):  # noqa: ANN001
        return {}, "TEST_NO_DATA"

    def get_pool_liquidity(self, symbol, venue_type):  # noqa: ANN001
        return {}, "TEST_NO_DATA"

    def get_token_security(self, symbol, venue_type):  # noqa: ANN001
        return {}, "TEST_NO_DATA"

    def get_macro_context(self, symbol, venue_type):  # noqa: ANN001
        return {}, "TEST_NO_DATA"


@pytest.fixture(scope="module")
def full_result() -> Dict[str, Any]:
    overview = json.loads(
        (_FIXTURE_BOT_DIR / "overview.json").read_text(encoding="utf-8")
    )
    ledger = json.loads(
        (_FIXTURE_BOT_DIR / "trade_list.json").read_text(encoding="utf-8")
    )
    service = WebDataService(
        bot_source_factory=lambda client, bucket: _StubBotSource(overview, ledger),
        market_source_factory=lambda client: _NoMarketSource(),
    )
    result = service.analyze(VALID_CODE)
    assert result["status"] == "FULL"
    return result


# --------------------------------------------------------------------------- #
# SVG-validity helpers
# --------------------------------------------------------------------------- #

_BAD_TOKENS = ("nan", "inf", "-inf", "none", "undefined")
# `none` is only a BROKEN value on an attribute that must hold a number --
# on a paint attribute it is the legal SVG way to say "don't paint this"
# (`fill="none"` is how an outline-only rectangle is drawn). Flagging it
# everywhere made a correct outline look like a bug, so the "none" check is
# scoped to the numeric attributes; every other bad token stays flagged on
# EVERY attribute exactly as before.
_PAINT_ATTRS = frozenset({"fill", "stroke", "stroke-dasharray"})
# Only flag a bad numeric token when it appears as a whole SVG attribute
# value (e.g. `x="nan"`), never as a substring of ordinary prose -- Vietnamese
# and English text legitimately contains "nan" (e.g. "dominant"), "none" etc.
_ATTR_VALUE_RE = re.compile(r'([\w-]+)="([^"]*)"')


def _assert_no_bad_numeric_attrs(svg_fragment: str) -> None:
    for match in _ATTR_VALUE_RE.finditer(svg_fragment):
        name = match.group(1).strip().lower()
        value = match.group(2).strip().lower()
        bad = _BAD_TOKENS
        if name in _PAINT_ATTRS:
            bad = tuple(t for t in _BAD_TOKENS if t != "none")
        assert value not in bad, f"bad SVG attribute value: {match.group(0)!r}"


def _extract_svgs(html_doc: str) -> List[str]:
    return re.findall(r"<svg[^>]*>.*?</svg>", html_doc, flags=re.DOTALL)


def _assert_valid_xml_fragment(fragment: str) -> None:
    """Every SVG must be well-formed XML on its own (every tag closed,
    attributes properly quoted) -- parse it in isolation rather than the
    whole HTML document, which is not XML (it is HTML5: unescaped `&` in
    text, void elements, etc. are all legal there but not in a bare SVG
    fragment parsed as XML).
    """
    ElementTree.fromstring(fragment)


# --------------------------------------------------------------------------- #
# 1. Real FULL response -> valid HTML containing every required section
# --------------------------------------------------------------------------- #


def test_full_result_renders_every_section(full_result: Dict[str, Any]) -> None:
    out = render_bot_report_html(full_result)

    assert out.startswith("<!doctype html>")
    assert "<html" in out and "</html>" in out
    assert out.count("<svg") == out.count("</svg>")
    assert out.count("<details") == out.count("</details>")

    # Section 1: header -- name, code, verdict badge, three headline scores.
    assert full_result["code"] in out
    assert "verdict-badge" in out
    assert full_result["verdict"] in out

    # Section 2: conclusion / recommendation, not dumped into a bare <pre>.
    assert "Conclusion and recommendation" in out
    assert "<pre>" not in out

    # Section ①: "How this bot trades", placed right after the conclusion --
    # Việc 1/2's own fix (strategy/behavioral evidence used to be computed
    # and then discarded before this).
    assert "How this bot trades" in out

    # Section 3: per-dimension bars.
    assert "Score by risk dimension" in out
    assert "bar-chart" in out

    # Section 4: Monte Carlo.
    assert "Monte Carlo simulation" in out

    # Section 6: trade metrics table.
    assert "Trade metrics" in out
    assert "Profit factor" in out

    # Section 7: traded assets.
    assert "Traded assets" in out

    # Every section (3-7, plus the new section ①) that rendered must carry
    # at least one "sở cứ + lý thuyết" collapsible -- the task's own
    # explicit third requirement. Was ">= 5" before section ① added its own
    # theory block.
    assert out.count('<details class="theory">') >= 6


def test_full_result_shows_veto_or_weighted_average_explicitly(
    full_result: Dict[str, Any],
) -> None:
    """The header must say plainly whether the risk score is a plain
    weighted average or was overridden by a veto/emergency rule -- never
    leave that ambiguous (task's own explicit requirement)."""
    out = render_bot_report_html(full_result)
    decided_by = full_result["evidence"]["score_breakdown"]["decided_by"]
    if decided_by != "WEIGHTED_AVERAGE":
        assert "KHÔNG phải bình quân" in out
        for reason in full_result["evidence"]["score_breakdown"]["veto_reasons"]:
            assert reason in out


def test_full_result_all_svgs_are_well_formed_xml(full_result: Dict[str, Any]) -> None:
    out = render_bot_report_html(full_result)
    svgs = _extract_svgs(out)
    assert svgs, "expected at least one chart for a FULL result"
    for svg in svgs:
        _assert_valid_xml_fragment(svg)
        _assert_no_bad_numeric_attrs(svg)


# --------------------------------------------------------------------------- #
# 2. LIMITED status -- must not break, must hide what it cannot show
# --------------------------------------------------------------------------- #


def _limited_result(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "status": "LIMITED",
        "code": "ED2DE1A47EEF62EC",
        "name": "渣哥玩币",
        "limited_reason": (
            "Bot không công khai sổ lệnh (OKX trả lỗi 60004 ở endpoint sổ lệnh)"
        ),
        "unavailable": ["profit_factor", "deferred_loss", "phase_analysis", "psr_dsr"],
        "verdict": "TIỀM ẨN",
        "risk": 62.0,
        "quality": 40.0,
        "confidence": 35.0,
        "evidence": {
            "profile": {"aum": 20000.0, "rank": 3},
            "stats": {"winRatio": "0.62"},
            "weekly_points": 12,
            "equity_curve_basis": "WEEKLY_PNL",
            "components": [
                {
                    "name": "drawdown",
                    "label": "Sụt vốn (suy từ đường vốn tuần)",
                    "score": 40.0,
                    "weight": 1.0,
                    "status": "AVAILABLE",
                    "confidence": 0.55,
                    "findings": ["Sụt vốn tối đa suy từ đường vốn tuần: 12.0%"],
                },
                {
                    "name": "profit_factor",
                    "label": "Profit factor",
                    "score": 70.0,
                    "weight": 0.8,
                    "status": "UNKNOWN_CONCEALED",
                    "confidence": 0.0,
                    "findings": [],
                },
            ],
        },
        "mc": None,
        "assets": [],
        "text": [
            "Đây là ĐÁNH GIÁ HẠN CHẾ cho mã ED2DE1A47EEF62EC: bot không công khai sổ lệnh.",
            "Kết luận: TIỀM ẨN -- điểm rủi ro 62/100, độ tin cậy 35/100.",
        ],
    }
    base.update(overrides)
    return base


def test_limited_result_renders_without_crashing_and_shows_banner() -> None:
    result = _limited_result()
    out = render_bot_report_html(result)
    assert "<!doctype html>" in out
    assert "LIMITED" in out
    assert result["limited_reason"] in out
    for field in result["unavailable"]:
        assert field in out


def test_limited_result_marks_concealed_dimension_and_hides_unmeasured_score() -> None:
    result = _limited_result()
    out = render_bot_report_html(result)
    # The concealed component must show up as "not measured", never with a
    # numeric bar that could be mistaken for an actual measured 70.
    assert "concealed" in out
    assert "Profit factor" in out  # the component's own label still shows


def test_limited_result_shows_public_stats_and_assets_placeholder_not_full_metrics() -> (
    None
):
    """A LIMITED bot has no `evidence.performance` and always empty `assets`
    (see data.py's own contract) -- but per this task's requirement ("report
    đều giống nhau"), the "Số liệu giao dịch"/"Tài sản đang giao dịch"
    sections must still APPEAR (same section ids as a FULL result -- see
    `test_limited_result_has_the_same_section_ids_as_a_full_result` below),
    just filled with whatever public-lead-traders/public-stats fields
    `_limited_result()`'s `evidence.profile`/`evidence.stats` carry, never
    with FULL-only trade-ledger metrics that were never actually measured
    for this bot."""
    result = _limited_result()
    out = render_bot_report_html(result)
    assert "Trade metrics" in out
    assert "Traded assets" in out

    def _section_body(anchor: str) -> str:
        match = re.search(
            rf'<section class="card[^"]*" id="{anchor}">.*?</section>', out, re.S
        )
        assert match, f"missing section {anchor}"
        return match.group(0)

    # FULL-only, ledger-derived metric LABELS (Agent/backend/web/report_page
    # .py's own `_PERFORMANCE_ROWS`) must never appear INSIDE the "so-lieu"/
    # "tai-san" sections themselves as if they had been measured for this
    # LIMITED bot -- scoped to those two sections specifically (rather than
    # the whole page) because some of these words legitimately appear
    # elsewhere on the page in an honest, different context (e.g. "Marked
    # PF" is named inside the "vi-the-mo" placeholder purely to explain WHY
    # it cannot be computed, not presented as a measured number).
    for full_only_metric in ("Payoff ratio", "Sharpe ratio", "Expectancy per trade"):
        assert full_only_metric not in _section_body("so-lieu")
        assert full_only_metric not in _section_body("tai-san")


def test_limited_result_has_the_same_section_ids_as_a_full_result(
    full_result: Dict[str, Any],
) -> None:
    """The task's own main acceptance criterion: a LIMITED result must
    render the exact same set of section anchors a FULL result does, even
    though most of them are honest placeholders for this bot -- a reader
    must never see a materially shorter page and wonder whether the system
    is broken."""
    limited_out = render_bot_report_html(_limited_result())
    full_out = render_bot_report_html(full_result)
    limited_ids = set(
        re.findall(r'<section class="card[^"]*" id="([^"]+)"', limited_out)
    )
    full_ids = set(re.findall(r'<section class="card[^"]*" id="([^"]+)"', full_out))
    assert limited_ids == full_ids
    # 14 -> 17: three deterministic insight sections were added to both pages
    # ("In one look", "Did earlier results hold up later", "Scenario
    # laboratory"). A LIMITED record cannot compute any of them, so each one
    # renders its shell and states the reason -- which is exactly the invariant
    # this test exists to protect.
    # 17 -> 18: "Market compatibility" was added to the market tab. The deep
    # modules now sit in the two deep tabs (market, position) and the result
    # tab keeps only the user-facing overview.
    assert len(full_ids) == 18


def test_limited_result_placeholder_sections_state_a_reason_not_a_bare_dash() -> None:
    """Every section a LIMITED bot cannot honestly fill (no closed ledger)
    must carry a `.notice` explanation, never a bare "0"/"—" that could be
    misread as an actual zero-risk measurement."""
    out = render_bot_report_html(_limited_result())
    for anchor in ("cach-choi", "vi-the-mo", "suy-luan", "danh-sach-lenh"):
        section = re.search(
            rf'<section class="card[^"]*" id="{anchor}">.*?</section>', out, re.S
        )
        assert section, f"missing section {anchor}"
        assert "notice" in section.group(0), f"{anchor} has no explanation notice"


def test_limited_result_with_valid_monte_carlo_renders_mc_section() -> None:
    """A LIMITED bot can still have a usable (if coarser) Monte Carlo result
    -- see Agent/backend/analysis/limited.py's weekly-PnL bootstrap -- and
    when it does, the same MC section a FULL result uses must render."""
    result = _limited_result(
        mc={
            "profit_pct_p05": -10.0,
            "profit_pct_p50": 5.0,
            "profit_pct_p95": 20.0,
            "p_ruin": 12.0,
            "sample_size": 24,
            "iterations": 5000,
            "horizon_trades": 24,
            "horizon_scenarios": [],
        }
    )
    out = render_bot_report_html(result)
    assert "Monte Carlo simulation" in out
    assert out.count("<svg") == out.count("</svg>")


# --------------------------------------------------------------------------- #
# 3. NOT_FOUND -- short, clean page
# --------------------------------------------------------------------------- #


def test_not_found_renders_compact_page() -> None:
    result = {
        "status": "NOT_FOUND",
        "code": "NOSUCHCODE",
        "name": None,
        "limited_reason": None,
        "unavailable": [],
        "verdict": None,
        "risk": None,
        "quality": None,
        "confidence": None,
        "evidence": {},
        "mc": None,
        "assets": [],
        "text": ["Không tìm thấy bot với mã 'NOSUCHCODE' trên OKX."],
    }
    out = render_bot_report_html(result)
    assert "<!doctype html>" in out
    assert "Không tìm thấy" in out
    assert "NOSUCHCODE" in out
    # None of the FULL-only sections should appear.
    for heading in (
        "Mô phỏng Monte Carlo",
        "Suy luận thống kê",
        "Số liệu giao dịch",
        "Tài sản đang giao dịch",
    ):
        assert heading not in out


def test_not_found_with_missing_text_does_not_crash() -> None:
    result = {"status": "NOT_FOUND", "code": "X", "text": []}
    out = render_bot_report_html(result)
    assert "<!doctype html>" in out


# --------------------------------------------------------------------------- #
# 4. XSS -- the mandatory, dedicated escaping test
# --------------------------------------------------------------------------- #


_XSS_PAYLOAD = "<script>alert(1)</script>\"'&<img src=x onerror=alert(2)>"


def _xss_result(**overrides: Any) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "status": "FULL",
        "code": _XSS_PAYLOAD,
        "name": _XSS_PAYLOAD,
        "limited_reason": None,
        "unavailable": [],
        "verdict": "NGUY HIỂM",
        "risk": 90.0,
        "quality": 20.0,
        "confidence": 50.0,
        "evidence": {
            "dimensions": {
                "tail_risk": {
                    "dimension_name": _XSS_PAYLOAD,
                    "score": 95.0,
                    "tier": "CRITICAL",
                    "weight": 1.3,
                    "status": "AVAILABLE",
                    "confidence": 0.8,
                    "key_findings": [_XSS_PAYLOAD],
                }
            },
            "score_breakdown": {
                "decided_by": "VETO_FLOOR",
                "veto_floor": 90.0,
                "veto_reasons": [_XSS_PAYLOAD],
                "weighted_average": 40.0,
            },
            "performance": {"trade_count": 10, "win_rate": 50.0},
        },
        "mc": None,
        "assets": [
            {
                "asset": _XSS_PAYLOAD,
                "state": "ĐANG GIAO DỊCH",
                "open_positions": 1,
                "closed_seen": 2,
                "last_close_days": 1.0,
            }
        ],
        "text": [_XSS_PAYLOAD],
        "narrative": _XSS_PAYLOAD,
    }
    base.update(overrides)
    return base


def test_xss_payload_in_every_string_field_is_escaped_not_executable() -> None:
    out = render_bot_report_html(_xss_result())

    # The literal, unescaped payload must never appear anywhere in the output.
    assert _XSS_PAYLOAD not in out
    assert "<script>alert(1)</script>" not in out
    assert "<img src=x onerror=alert(2)>" not in out

    # It must appear only in its escaped form.
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out
    assert "&amp;" in out
    assert "&#x27;" in out or "&#39;" in out
    assert "&quot;" in out or "&#34;" in out

    # And the document must still be well-formed: the payload must not have
    # opened a new real tag anywhere (e.g. a stray unescaped `<img ...>`).
    assert "<script>" not in out
    assert "<img " not in out


def test_xss_payload_in_veto_reason_is_escaped() -> None:
    out = render_bot_report_html(_xss_result())
    assert "&lt;script&gt;" in out
    assert "<script>alert(1)</script>" not in out


# --------------------------------------------------------------------------- #
# 5. mc is None / missing fields -> no KeyError, section hidden
# --------------------------------------------------------------------------- #


def test_mc_none_hides_monte_carlo_and_inference_sections() -> None:
    result = _xss_result(mc=None, code="OK1", name="OK Bot")
    out = render_bot_report_html(result)
    assert "<h2>Mô phỏng Monte Carlo</h2>" not in out
    assert "<h2>Suy luận thống kê</h2>" not in out


# --------------------------------------------------------------------------- #
# Narrative ("nhận định chuyên môn") -- Agent/backend/qc/reporting/narrative.py
# --------------------------------------------------------------------------- #


def test_narrative_section_hidden_when_none() -> None:
    result = _xss_result(narrative=None, code="OK2", name="OK Bot")
    out = render_bot_report_html(result)
    assert "Nhận định chuyên môn" not in out


@pytest.mark.parametrize("blank", ["", "   ", "\n\t"])
def test_narrative_section_hidden_when_blank(blank: str) -> None:
    result = _xss_result(narrative=blank, code="OK3", name="OK Bot")
    out = render_bot_report_html(result)
    assert "Nhận định chuyên môn" not in out


def test_narrative_section_shown_with_disclosure_and_escaped_text() -> None:
    text = "Điểm rủi ro 26.5 phản ánh xác suất sụt vốn thấp."
    result = _xss_result(narrative=text, code="OK4", name="OK Bot")
    out = render_bot_report_html(result)
    assert "Expert assessment" in out
    assert text in out
    # The task's own explicit requirement: the reader must be able to tell
    # the LLM-authored paragraph apart from the engine's own measurements.
    assert "language model" in out


def test_narrative_appears_right_after_the_conclusion_section() -> None:
    result = _xss_result(
        narrative="Điểm rủi ro thấp, nhất quán với sụt vốn ghi nhận.", code="OK5"
    )
    out = render_bot_report_html(result)
    conclusion_pos = out.index("Conclusion and recommendation")
    narrative_pos = out.index("Expert assessment")
    dimensions_pos = out.index("Score by risk dimension")
    assert conclusion_pos < narrative_pos < dimensions_pos


def test_narrative_field_is_escaped_not_executable() -> None:
    """The XSS payload placed in `narrative` by `_xss_result`'s own base
    dict must come out escaped, exactly like every other untrusted string
    field on this page (see `test_xss_payload_in_every_string_field_is_
    escaped_not_executable`, which already covers this via that shared
    base dict) -- this test only pins the narrative-specific assertion so
    a future change to `_render_narrative` cannot silently drop escaping
    without failing something narrative-named.
    """
    out = render_bot_report_html(_xss_result())
    assert _XSS_PAYLOAD not in out
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out


def test_narrative_section_never_adds_svg_or_details(
    full_result: Dict[str, Any],
) -> None:
    """A narrative is plain prose (see `_render_narrative`'s own docstring)
    -- it must never change this page's chart/collapsible-section counts,
    which is exactly what lets `GET /bot/<code>`'s existing "still has every
    chart" regression test in Agent/none/test/test_web_app.py stay a fixed
    number after this feature was added.
    """
    without = render_bot_report_html(full_result)
    with_narrative = dict(full_result)
    with_narrative["narrative"] = (
        "Điểm rủi ro và điểm chất lượng của bot này cùng phản ánh một bức "
        "tranh nhất quán dựa trên các con số đã đo được ở trên của báo cáo, "
        "không thêm bất kỳ số liệu mới nào ngoài những gì hệ thống đã tính."
    )
    out = render_bot_report_html(with_narrative)
    assert out.count("<svg") == without.count("<svg")
    assert out.count("<details") == without.count("<details")
    assert "Expert assessment" in out


@pytest.mark.parametrize(
    "mc",
    [
        {},
        {"profit_pct_p50": None},
        {"horizon_scenarios": None},
        {"p_5_loss_streak": None, "p_5_loss_streak_baseline": None},
        {"inference_reliable": False, "inference_notes": None},
        {"profit_pct_p05": float("nan"), "profit_pct_p95": float("inf")},
    ],
)
def test_partial_mc_never_raises(mc: Dict[str, Any]) -> None:
    result = _xss_result(mc=mc, code="OK2", name="OK Bot 2")
    out = render_bot_report_html(result)
    assert "<!doctype html>" in out
    for svg in _extract_svgs(out):
        _assert_valid_xml_fragment(svg)
        _assert_no_bad_numeric_attrs(svg)


def test_horizon_scenarios_empty_hides_horizon_comparison() -> None:
    result = _xss_result(
        mc={"profit_pct_p50": 5.0, "horizon_scenarios": []}, code="OK3", name="OK Bot 3"
    )
    out = render_bot_report_html(result)
    assert "So sánh đa horizon" not in out


def test_dimensions_missing_does_not_raise() -> None:
    result = _xss_result(code="OK4", name="OK Bot 4")
    result["evidence"] = {}
    out = render_bot_report_html(result)
    assert "<!doctype html>" in out
    assert "Điểm từng chiều rủi ro" not in out


def test_result_not_a_dict_does_not_raise() -> None:
    out = render_bot_report_html(None)  # type: ignore[arg-type]
    assert "<!doctype html>" in out


def test_evidence_not_a_dict_does_not_raise() -> None:
    result = _xss_result(code="OK5", name="OK Bot 5")
    result["evidence"] = None
    out = render_bot_report_html(result)
    assert "<!doctype html>" in out


# --------------------------------------------------------------------------- #
# 6. General SVG-safety sweep across every fixture above
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "result_factory",
    [
        lambda: _limited_result(),
        lambda: _xss_result(),
        lambda: {"status": "NOT_FOUND", "code": "N", "text": []},
    ],
)
def test_no_bad_numeric_tokens_leak_into_any_svg(result_factory) -> None:
    out = render_bot_report_html(result_factory())
    for svg in _extract_svgs(out):
        _assert_valid_xml_fragment(svg)
        _assert_no_bad_numeric_attrs(svg)


def test_coord_helper_never_returns_non_finite_text() -> None:
    from Agent.backend.web.report_page import _coord

    for bad in (
        float("nan"),
        float("inf"),
        float("-inf"),
        None,
        "not-a-number",
        object(),
    ):
        text = _coord(bad)
        assert text.lower() not in ("nan", "inf", "-inf", "none")
        # Must parse back as a plain finite float.
        assert math.isfinite(float(text))


# --------------------------------------------------------------------------- #
# Growth section: cumulative equity curve + win/loss composition pies +
# horizon-probability grouped bar. New charts added on top of the module
# this file already tests above.
# --------------------------------------------------------------------------- #


def _with_closed_trade_series(
    base: Dict[str, Any], pnls: List[float]
) -> Dict[str, Any]:
    """A FULL result (from the `full_result` fixture) with its
    `evidence.closed_trade_series` replaced by a synthetic sequence -- the
    ONE real key `WebDataService.analyze()` populates for a FULL result
    (see Agent/backend/web/data.py's `_closed_trade_series_from_bot_result`)
    and the only one `_extract_trade_pnls` reads. Used to drive the growth
    curve through specific/degenerate sequences without depending on
    exactly what the fixture bot's own real ledger happens to contain.
    """
    result = copy.deepcopy(base)
    result["evidence"]["closed_trade_series"] = [
        {"realized_pnl": value, "close_time": index} for index, value in enumerate(pnls)
    ]
    return result


def test_growth_curve_renders_for_a_real_full_result(
    full_result: Dict[str, Any],
) -> None:
    """`WebDataService.analyze()` now always attaches
    `evidence.closed_trade_series` for a FULL result (Lỗi 2's fix, see
    data.py), and this fixture bot's own real ledger has closed trades on
    it (see test_web_app.py's own `test_analyze_full_includes_per_asset_context`
    comment) -- so the growth curve must actually render for it, not stay
    hidden. This replaces the old "hidden today" pin, which was true only
    because data.py never used to expose any trade sequence at all.
    """
    out = render_bot_report_html(full_result)
    assert "Cumulative capital curve by closed trade" in out
    assert "Growth &amp; outcome composition" in out
    svgs = _extract_svgs(out)
    assert any("line-chart" in svg for svg in svgs)
    for svg in svgs:
        _assert_valid_xml_fragment(svg)
        _assert_no_bad_numeric_attrs(svg)


def test_growth_curve_hidden_for_empty_closed_trade_series(
    full_result: Dict[str, Any],
) -> None:
    result = _with_closed_trade_series(full_result, [])
    out = render_bot_report_html(result)
    assert "Cumulative capital curve by closed trade" not in out


def test_growth_curve_hidden_when_key_is_missing_entirely(
    full_result: Dict[str, Any],
) -> None:
    """LIMITED/NOT_FOUND results never carry `closed_trade_series` at all
    (a different `evidence` shape, or an empty one) -- simulated here by
    just deleting the key from an otherwise-real FULL result, to isolate
    "key absent" from "key present but empty" (the case just above)."""
    result = copy.deepcopy(full_result)
    del result["evidence"]["closed_trade_series"]
    out = render_bot_report_html(result)
    assert "Cumulative capital curve by closed trade" not in out


def test_growth_curve_hidden_for_limited_result() -> None:
    out = render_bot_report_html(_limited_result())
    assert "Cumulative capital curve by closed trade" not in out


def test_growth_curve_hidden_for_not_found_result() -> None:
    result = {"status": "NOT_FOUND", "code": "N", "text": []}
    out = render_bot_report_html(result)
    assert "Cumulative capital curve by closed trade" not in out


def test_growth_curve_renders_and_validates_for_a_normal_sequence(
    full_result: Dict[str, Any],
) -> None:
    result = _with_closed_trade_series(full_result, [100.0, -40.0, 60.0, -10.0, 200.0])
    out = render_bot_report_html(result)
    assert "Cumulative capital curve by closed trade" in out
    assert "Growth &amp; outcome composition" in out
    svgs = _extract_svgs(out)
    assert any("line-chart" in svg for svg in svgs)
    for svg in svgs:
        _assert_valid_xml_fragment(svg)
        _assert_no_bad_numeric_attrs(svg)


@pytest.mark.parametrize(
    "pnls",
    [
        [500.0],  # a single closed trade
        [-10.0, -20.0, -5.0],  # every trade a loss
        [0.0, 0.0, 0.0, 0.0],  # every trade nets exactly zero -> flat
        # cumulative curve at 0, the classic (max-min)==0 normalization
        # hazard
        [50.0, 50.0, 50.0],  # every trade nets the same nonzero amount
    ],
)
def test_growth_curve_never_crashes_on_degenerate_sequences(
    full_result: Dict[str, Any], pnls: List[float]
) -> None:
    result = _with_closed_trade_series(full_result, pnls)
    out = render_bot_report_html(result)
    assert "Cumulative capital curve by closed trade" in out
    svgs = _extract_svgs(out)
    assert svgs
    for svg in svgs:
        _assert_valid_xml_fragment(svg)
        _assert_no_bad_numeric_attrs(svg)


def test_win_loss_composition_renders_two_pies_for_a_real_full_result(
    full_result: Dict[str, Any],
) -> None:
    out = render_bot_report_html(full_result)
    assert "Win/loss composition" in out
    assert out.count('class="pie-chart"') >= 2
    for svg in _extract_svgs(out):
        _assert_valid_xml_fragment(svg)
        _assert_no_bad_numeric_attrs(svg)


def test_win_loss_composition_hidden_when_performance_is_missing() -> None:
    result: Dict[str, Any] = {
        "status": "FULL",
        "code": "AAAA000000000099",
        "name": "NoPerf",
        "verdict": "TIỀM ẨN",
        "risk": 50.0,
        "quality": 50.0,
        "confidence": 50.0,
        "evidence": {"score_breakdown": {"decided_by": "WEIGHTED_AVERAGE"}},
        "mc": None,
        "text": ["dummy"],
    }
    out = render_bot_report_html(result)
    assert "Win/loss composition" not in out


def test_horizon_probability_chart_present_for_a_real_full_result(
    full_result: Dict[str, Any],
) -> None:
    """The title used to be "Probability of profit by horizon (chart) &
    Multi-horizon risk distribution" -- the name of the separate bar chart this
    unified chart REPLACED, so the page advertised two charts and drew one."""
    out = render_bot_report_html(full_result)
    assert "Outcome distribution by horizon" in out


def test_horizon_probability_chart_hidden_when_scenarios_absent(
    full_result: Dict[str, Any],
) -> None:
    result = copy.deepcopy(full_result)
    result["mc"]["horizon_scenarios"] = []
    out = render_bot_report_html(result)
    assert "Outcome distribution by horizon" not in out


# --------------------------------------------------------------------------- #
# Admin banner (Việc 3) -- navigation only, never a change to the analysis.
# --------------------------------------------------------------------------- #


def test_admin_banner_shown_only_when_is_admin_true(
    full_result: Dict[str, Any],
) -> None:
    plain = render_bot_report_html(full_result)
    admin = render_bot_report_html(full_result, is_admin=True)
    assert '<div class="admin-banner">' not in plain
    assert '<div class="admin-banner">' in admin
    assert "ADMIN" in admin
    assert "ADMIN" not in plain


def test_admin_banner_does_not_change_the_analysis_body(
    full_result: Dict[str, Any],
) -> None:
    """The task's own explicit rule: role changes NAVIGATION only. Strip the
    one banner `<div>` out of the admin page and the remainder must be
    byte-for-byte identical to the plain page.
    """
    plain = render_bot_report_html(full_result)
    admin = render_bot_report_html(full_result, is_admin=True)
    banner_match = re.search(
        r'<div class="admin-banner">.*?</div>', admin, flags=re.DOTALL
    )
    assert banner_match is not None
    stripped = admin[: banner_match.start()] + admin[banner_match.end() :]
    assert stripped == plain


def test_admin_back_url_is_escaped_and_configurable(
    full_result: Dict[str, Any],
) -> None:
    admin = render_bot_report_html(
        full_result, is_admin=True, admin_back_url="/admin?x=1&y=2"
    )
    assert 'href="/admin?x=1&amp;y=2"' in admin


# --------------------------------------------------------------------------- #
# Snapshot timestamp banner -- see Agent/backend/web/snapshot.py's module
# docstring for the caching feature this displays. Navigation-only, same
# rule as the admin banner above: must never change a single word of the
# analysis body.
# --------------------------------------------------------------------------- #


def test_snapshot_banner_omitted_when_no_timestamp_given(
    full_result: Dict[str, Any],
) -> None:
    """Every pre-existing call to render_bot_report_html in this test module
    (and every route that predates this feature) must keep getting
    byte-for-byte the same page -- same backward-compatible default pattern
    as `is_admin`."""
    out = render_bot_report_html(full_result)
    assert '<div class="snapshot-banner">' not in out
    assert "Snapshot taken at" not in out


def test_snapshot_banner_shown_with_timestamp_and_refresh_link(
    full_result: Dict[str, Any],
) -> None:
    out = render_bot_report_html(
        full_result,
        snapshot_at_ms=1_700_000_000_000,
        refresh_url="/bot/BB3398A957270A39?refresh=1",
    )
    assert '<div class="snapshot-banner">' in out
    assert "Snapshot taken at" in out
    assert "Vietnam time" in out
    assert '<a href="/bot/BB3398A957270A39?refresh=1">Re-analyze</a>' in out


def test_snapshot_banner_timestamp_is_vietnam_time_gmt_plus_7(
    full_result: Dict[str, Any],
) -> None:
    # 1_700_000_000_000 ms since epoch = 2023-11-14T22:13:20Z ->
    # 2023-11-15 05:13:20 at UTC+7 (no DST in Vietnam).
    out = render_bot_report_html(full_result, snapshot_at_ms=1_700_000_000_000)
    assert "05:13:20 15/11/2023" in out


def test_snapshot_banner_without_refresh_url_has_no_link(
    full_result: Dict[str, Any],
) -> None:
    out = render_bot_report_html(full_result, snapshot_at_ms=1_700_000_000_000)
    assert '<div class="snapshot-banner">' in out
    assert (
        "<a href="
        not in out.split('<div class="snapshot-banner">')[1].split("</div>")[0]
    )


def test_snapshot_banner_refresh_url_is_escaped(
    full_result: Dict[str, Any],
) -> None:
    out = render_bot_report_html(
        full_result,
        snapshot_at_ms=1_700_000_000_000,
        refresh_url="/bot/X?refresh=1&evil=<script>",
    )
    assert "<script>" not in out
    assert "&amp;evil=" in out


def test_snapshot_banner_does_not_change_the_analysis_body(
    full_result: Dict[str, Any],
) -> None:
    plain = render_bot_report_html(full_result)
    stamped = render_bot_report_html(
        full_result,
        snapshot_at_ms=1_700_000_000_000,
        refresh_url="/bot/BB3398A957270A39?refresh=1",
    )
    banner_match = re.search(
        r'<div class="snapshot-banner">.*?</div>', stamped, flags=re.DOTALL
    )
    assert banner_match is not None
    stripped = stamped[: banner_match.start()] + stamped[banner_match.end() :]
    assert stripped == plain


def test_snapshot_banner_coexists_with_admin_banner(
    full_result: Dict[str, Any],
) -> None:
    out = render_bot_report_html(
        full_result,
        is_admin=True,
        snapshot_at_ms=1_700_000_000_000,
        refresh_url="/bot/BB3398A957270A39?refresh=1",
    )
    assert '<div class="admin-banner">' in out
    assert '<div class="snapshot-banner">' in out


# --------------------------------------------------------------------------- #
# Pie chart geometry (`_pie_chart`) -- imported directly rather than through
# the public HTML entry point: recovering "do the angles really sum to 360"
# from the rendered document would mean re-deriving the exact same
# trigonometry inside the test, which proves nothing a direct call doesn't
# already prove more simply. Every OTHER guarantee (escaping, hidden when
# no data, SVG well-formedness for a real chart) is still exercised through
# the public function above.
# --------------------------------------------------------------------------- #


def test_pie_chart_full_slice_renders_as_a_circle_not_a_degenerate_path() -> None:
    from Agent.backend.web.report_page import _pie_chart

    svg = _pie_chart([("Only", 10.0, "#111111"), ("Empty", 0.0, "#222222")])
    _assert_valid_xml_fragment(svg)
    _assert_no_bad_numeric_attrs(svg)
    assert "<circle" in svg
    assert "<path" not in svg


def test_pie_chart_zero_slice_emits_no_path_but_keeps_its_label() -> None:
    from Agent.backend.web.report_page import _pie_chart

    svg = _pie_chart(
        [("A", 30.0, "#111111"), ("B", 70.0, "#222222"), ("C (rỗng)", 0.0, "#333333")]
    )
    _assert_valid_xml_fragment(svg)
    _assert_no_bad_numeric_attrs(svg)
    # Exactly two wedges get geometry (A, B); C contributes none.
    assert svg.count("<path") == 2
    assert "C (rỗng)" in svg


def test_pie_chart_multiple_slices_sum_to_360_degrees() -> None:
    from Agent.backend.web.report_page import _pie_chart

    width, height = 460.0, 260.0
    cx, cy = width / 2.0, height / 2.0
    svg = _pie_chart(
        [("A", 30.0, "#111111"), ("B", 50.0, "#222222"), ("C", 20.0, "#333333")],
        width=width,
        height=height,
    )
    _assert_valid_xml_fragment(svg)

    total_sweep = 0.0
    for path_d in re.findall(r'<path d="([^"]+)"', svg):
        nums = [float(n) for n in re.findall(r"-?\d+\.\d+", path_d)]
        # M cx,cy L x1,y1 A r,r 0 <flag> <flag> x2,y2 Z -- 8 decimal-formatted
        # numbers in order; the two arc flags are plain integers (no decimal
        # point) and are skipped entirely by this regex.
        assert len(nums) == 8
        _cx, _cy, x1, y1, _r1, _r2, x2, y2 = nums
        a1 = math.degrees(math.atan2(y1 - cy, x1 - cx))
        a2 = math.degrees(math.atan2(y2 - cy, x2 - cx))
        total_sweep += (a2 - a1) % 360.0
    assert abs(total_sweep - 360.0) < 0.5


def test_pie_chart_empty_and_all_zero_render_a_placeholder_not_a_broken_svg() -> None:
    from Agent.backend.web.report_page import _pie_chart

    for svg in (
        _pie_chart([]),
        _pie_chart([("A", 0.0, "#111111"), ("B", 0.0, "#222222")]),
        _pie_chart([("A", None, "#111111")]),
    ):
        _assert_valid_xml_fragment(svg)
        _assert_no_bad_numeric_attrs(svg)
        assert "No data" in svg
        assert "<path" not in svg


def test_pie_chart_negative_value_is_clamped_to_zero_not_subtracted() -> None:
    from Agent.backend.web.report_page import _pie_chart

    svg = _pie_chart([("A", -5.0, "#111111"), ("B", 10.0, "#222222")])
    _assert_valid_xml_fragment(svg)
    _assert_no_bad_numeric_attrs(svg)
    # B alone is then 100% of the (clamped) total -> a circle, not a path,
    # and A must not have somehow inflated the denominator above B's own
    # value.
    assert "<circle" in svg


# --------------------------------------------------------------------------- #
# Shared design tokens (task's Việc 3) -- Agent/frontend/tokens.css is the single
# source of truth for the verdict colors this module used to hardcode
# as a Python literal. These tests parse tokens.css INDEPENDENTLY (a small
# regex written here, not a call into report_page.py's own private parser)
# so a bug in that parser could not simultaneously make both the production
# code AND this test agree on a wrong value -- and never hardcode the
# expected hex strings here either, so editing a color in tokens.css alone
# (no code change) keeps this test meaningful instead of it silently
# checking a stale, copy-pasted constant.
# --------------------------------------------------------------------------- #

_TOKENS_CSS_PATH = Path(config.BASE_DIR) / "frontend" / "tokens.css"

# name written here -> the CSS custom property tokens.css declares for it.
# The Vietnamese label is looked up independently via report_page.VERDICT_COLOR
# and via report_page.TIER_LABEL_VI is NOT used here on purpose -- verdict
# labels are a separate vocabulary from tier labels (see report_page.py's own
# docstring on DIMENSION_LABEL_VI/TIER_LABEL_VI vs VERDICT_COLOR).
_VERDICT_TOKEN_VARS: Dict[str, str] = {
    "DRAWDOWN: HIGH · QUALITY: WEAK": "--verdict-high-dd-weak-q",
    "DRAWDOWN: HIGH · QUALITY: GOOD": "--verdict-high-dd-good-q",
    "DRAWDOWN: LOW · QUALITY: GOOD": "--verdict-low-dd-good-q",
    "DRAWDOWN: LOW · QUALITY: WEAK": "--verdict-low-dd-weak-q",
    "HIDDEN RISK": "--verdict-hidden-risk",
    "INSUFFICIENT EVIDENCE": "--verdict-unknown",
}


def _read_verdict_tokens_from_css_file() -> Dict[str, str]:
    """Independent parse of tokens.css's `:root { ... }` block, used only by
    these tests -- deliberately NOT importing report_page._parse_root_css_custom_properties,
    see this section's own header comment for why.
    """
    text = _TOKENS_CSS_PATH.read_text(encoding="utf-8")
    root_match = re.search(r":root\s*\{([^}]*)\}", text)
    assert root_match is not None, "tokens.css phải có một khối :root { ... }"
    body = root_match.group(1)
    found: Dict[str, str] = {}
    for label, var_name in _VERDICT_TOKEN_VARS.items():
        m = re.search(rf"{re.escape(var_name)}\s*:\s*([^;]+);", body)
        assert m is not None, f"tokens.css thiếu biến {var_name}"
        found[label] = m.group(1).strip()
    return found


def test_verdict_color_dict_matches_tokens_css_file() -> None:
    """report_page.VERDICT_COLOR must be BUILT FROM tokens.css, not a
    separately-maintained copy -- this is the actual point of Việc 3.
    """
    from Agent.backend.web.report_page import VERDICT_COLOR

    expected = _read_verdict_tokens_from_css_file()
    for label, expected_color in expected.items():
        assert VERDICT_COLOR[label] == expected_color


def test_verdict_tier_colors_in_rendered_html_match_tokens_css_file() -> None:
    """The acceptance test's own literal requirement: the verdict
    colors that actually show up in a SERVER-RENDERED report page must be
    byte-identical to whatever tokens.css currently says -- read from the
    file, not hardcoded here, so editing tokens.css alone is caught if the
    render path ever stops actually using it.
    """
    expected = _read_verdict_tokens_from_css_file()
    for verdict_label, expected_color in expected.items():
        if verdict_label == "INSUFFICIENT EVIDENCE":
            # Not a real verdict a FULL/LIMITED result ever carries in
            # `result["verdict"]` (it is the fallback _verdict_color() itself
            # returns for an unrecognised/missing value) -- covered by the
            # embedded-tokens-css assertion below instead.
            continue
        result = _limited_result_with_verdict(verdict_label)
        html_out = render_bot_report_html(result)
        assert expected_color in html_out, (
            f"Màu của bậc '{verdict_label}' ({expected_color}) không xuất hiện "
            "trong HTML server-render -- kiểm tra render_bot_report_html còn "
            "đọc đúng report_page.VERDICT_COLOR không."
        )

    # tokens.css's own raw CSS text (verdict vars included) is also embedded
    # verbatim into the page's <style> tag (see render_bot_report_html) --
    # confirms the "Python đọc rồi nhúng vào <style>" half of Việc 3's wiring
    # is actually wired up, not just the derived-dict half above.
    any_result = _limited_result_with_verdict("DRAWDOWN: LOW · QUALITY: GOOD")
    html_out = render_bot_report_html(any_result)
    for expected_color in expected.values():
        assert expected_color in html_out


def _limited_result_with_verdict(verdict: str) -> Dict[str, Any]:
    """Minimal LIMITED-shaped result dict -- just enough for
    render_bot_report_html to reach `_render_header`'s verdict badge, which
    is where `_verdict_color(verdict)` actually gets embedded into the page.
    """
    return {
        "status": "LIMITED",
        "code": "TESTCODE1",
        "name": "Bot kiểm thử token màu",
        "verdict": verdict,
        "risk_score": 50.0,
        "text": [],
        "evidence": {"components": []},
    }


# --------------------------------------------------------------------------- #
# "Thị trường được chấm" -- Việc 2/3: `bot.identity.symbol_exposure_share`/
# `observed_symbols` (Agent/backend/mcp/service.py::
# _resolve_identity_market) were computed all along but never shown anywhere;
# this section is `_render_market_coverage`'s own, placed right after the
# conclusion (never inside a `<details>`, per the project owner's explicit
# "không giấu" instruction).
# --------------------------------------------------------------------------- #


def _market_coverage_result(**evidence_overrides: Any) -> Dict[str, Any]:
    evidence: Dict[str, Any] = {
        "traded_symbol": "SNDK",
        "dimensions": {},
        "score_breakdown": {},
        "performance": {},
        "observed_symbols": ["SNDK", "ETH", "SOL"],
        "symbol_exposure_share": {"SNDK": 0.42, "ETH": 0.35, "SOL": 0.23},
        "primary_share_pct": 42.0,
        "secondary_market": {
            "symbol": "ETH",
            "share_pct": 35.0,
            "venue_type": "CEX",
            "trend": "BULLISH",
            "volatility": "NORMAL",
            "liquidity_tier": "DEEP",
            "flow_bias": "BUY_PRESSURE",
            "last_price": 3000.0,
        },
    }
    evidence.update(evidence_overrides)
    return {
        "status": "FULL",
        "code": "MARKETCOV",
        "name": "Market Coverage Bot",
        "limited_reason": None,
        "unavailable": [],
        "verdict": "NGUY HIỂM",
        "risk": 60.0,
        "quality": 50.0,
        "confidence": 50.0,
        "evidence": evidence,
        "mc": None,
        "assets": [],
        "text": ["Kết luận: NGUY HIỂM."],
        "narrative": None,
    }


def _market_coverage_fragment(out: str) -> str:
    match = re.search(r'<section class="card" id="thi-truong">.*?</section>', out, re.S)
    assert match, "expected a rendered 'Market being scored' section"
    return match.group(0)


def test_market_coverage_section_present_right_after_conclusion() -> None:
    out = render_bot_report_html(_market_coverage_result())
    conclusion_pos = out.index("Conclusion and recommendation")
    market_pos = out.index("Market being scored")
    assert conclusion_pos < market_pos
    # `_market_coverage_result` carries no `evidence.strategy`, so "Cách bot
    # này chơi" is hidden entirely -- confirms the market-coverage section
    # renders independently, right after the conclusion, not piggy-backing
    # on the strategy section's own placement.
    assert "How this bot trades" not in out
    # Never hidden inside a collapsible block (project owner's own explicit
    # "không giấu trong khối gập" instruction).
    fragment = _market_coverage_fragment(out)
    assert "<details" not in fragment


def test_market_coverage_shows_primary_share_and_other_symbols() -> None:
    out = render_bot_report_html(_market_coverage_result())
    fragment = _market_coverage_fragment(out)
    assert "SNDK" in fragment
    assert "42%" in fragment or "42,0%" in fragment or "42.0%" in fragment
    assert "ETH" in fragment
    assert "SOL" in fragment


def test_market_coverage_shows_secondary_market_regime() -> None:
    out = render_bot_report_html(_market_coverage_result())
    fragment = _market_coverage_fragment(out)
    assert "Second-largest market" in fragment
    assert "up, normal volatility, deep liquidity" in fragment  # TREND/VOL/LIQ_VI
    # No raw English enum token leaks through untranslated.
    assert "BULLISH" not in fragment
    assert "NORMAL" not in fragment
    assert "DEEP" not in fragment


def test_market_coverage_warns_below_60pct() -> None:
    out = render_bot_report_html(_market_coverage_result(primary_share_pct=42.0))
    fragment = _market_coverage_fragment(out)
    assert "notice-warning" in fragment
    assert "market_alignment" in fragment
    assert "liquidity_execution" in fragment
    assert "leverage_exposure" in fragment
    assert "has NOT been reviewed" in fragment


def test_market_coverage_hides_warning_at_or_above_60pct() -> None:
    out = render_bot_report_html(_market_coverage_result(primary_share_pct=60.0))
    fragment = _market_coverage_fragment(out)
    assert "notice-warning" not in fragment


def test_market_coverage_hidden_when_primary_share_pct_absent() -> None:
    """Old assessment.json (written before Việc 2/3) has none of these
    evidence keys at all -- the section must simply not render, never raise.
    """
    result = _market_coverage_result()
    del result["evidence"]["primary_share_pct"]
    del result["evidence"]["observed_symbols"]
    del result["evidence"]["symbol_exposure_share"]
    del result["evidence"]["secondary_market"]
    out = render_bot_report_html(result)
    assert "Market being scored" not in out


def test_market_coverage_hidden_when_evidence_missing_entirely() -> None:
    result = _market_coverage_result()
    del result["evidence"]
    out = render_bot_report_html(result)  # must not raise
    assert "Market being scored" not in out


def test_market_coverage_escapes_untrusted_symbol_strings() -> None:
    """`traded_symbol`/`secondary_market.symbol` ultimately trace back to a
    bot's own ledger data -- treat them as untrusted like every other string
    field this page renders (see this file's own module docstring)."""
    out = render_bot_report_html(
        _market_coverage_result(
            traded_symbol=_XSS_PAYLOAD,
            secondary_market={
                "symbol": _XSS_PAYLOAD,
                "share_pct": 35.0,
                "venue_type": "CEX",
                "trend": "BULLISH",
                "volatility": "NORMAL",
                "liquidity_tier": "DEEP",
                "flow_bias": "BUY_PRESSURE",
                "last_price": 3000.0,
            },
        )
    )
    assert _XSS_PAYLOAD not in out


# --------------------------------------------------------------------------- #
# Phủ sóng theo mục tiêu (Agent/backend/market/coverage.py) -- khi
# `evidence.resolved_markets`/`coverage_achieved_pct` có mặt (kết quả tới từ
# pipeline/cohort đã giải NHIỀU thị trường), headline/ngưỡng cảnh báo phải
# dùng đúng con số phủ sóng THẬT này, không phải `primary_share_pct` (chỉ
# riêng mã chính) như bản cũ. Mọi test `_market_coverage_*` phía trên dùng
# `_market_coverage_result()` KHÔNG có ba khoá này, nên chúng tiếp tục thực
# thi đúng nhánh CŨ nguyên vẹn -- các test dưới đây thực thi nhánh MỚI.
# --------------------------------------------------------------------------- #


def _full_coverage_result(**evidence_overrides: Any) -> Dict[str, Any]:
    evidence: Dict[str, Any] = {
        "traded_symbol": "AAA",
        "dimensions": {},
        "score_breakdown": {},
        "performance": {},
        "observed_symbols": ["AAA", "BBB", "CCC", "DDD"],
        "symbol_exposure_share": {
            "AAA": 0.526,
            "BBB": 0.211,
            "CCC": 0.158,
            "DDD": 0.105,
        },
        "primary_share_pct": 52.6,
        "secondary_market": None,
        "resolved_markets": [
            {
                "symbol": "AAA",
                "share_pct": 52.6,
                "venue_type": "CEX",
                "trend": "BULLISH",
                "volatility": "NORMAL",
                "liquidity_tier": "DEEP",
                "flow_bias": "BUY_PRESSURE",
                "last_price": 100.0,
            },
            {
                "symbol": "BBB",
                "share_pct": 21.1,
                "venue_type": "CEX",
                "trend": "BEARISH",
                "volatility": "HIGH",
                "liquidity_tier": "SHALLOW",
                "flow_bias": "SELL_PRESSURE",
                "last_price": 50.0,
            },
            {
                "symbol": "CCC",
                "share_pct": 15.8,
                "venue_type": "CEX",
                "trend": "RANGING",
                "volatility": "NORMAL",
                "liquidity_tier": "DEEP",
                "flow_bias": "BALANCED",
                "last_price": 10.0,
            },
        ],
        "unresolved_markets": [
            {
                "symbol": "DDD",
                "share_pct": 10.5,
                "reason": "NO_MARKET_DATA_FOR_TRADED_SYMBOL",
            },
        ],
        "coverage_achieved_pct": 89.5,
    }
    evidence.update(evidence_overrides)
    return {
        "status": "FULL",
        "code": "MULTIMKT",
        "name": "Multi Market Bot",
        "limited_reason": None,
        "unavailable": [],
        "verdict": "NGUY HIỂM",
        "risk": 60.0,
        "quality": 50.0,
        "confidence": 50.0,
        "evidence": evidence,
        "mc": None,
        "assets": [],
        "text": ["Kết luận: NGUY HIỂM."],
        "narrative": None,
    }


def test_full_coverage_headline_uses_coverage_achieved_pct() -> None:
    out = render_bot_report_html(_full_coverage_result())
    fragment = _market_coverage_fragment(out)
    headline = fragment.split("</strong>")[0]
    assert "3 markets" in headline
    assert "90%" in headline or "89%" in headline or "89,5%" in headline
    # Headline KHÔNG còn nói con số cũ (primary_share_pct=52.6% -> "53%") --
    # 53% vẫn có thể xuất hiện SAU headline (là share_pct riêng của AAA
    # trong danh sách thị trường đã giải được), nên chỉ kiểm tra headline.
    assert "53%" not in headline


def test_full_coverage_lists_every_resolved_market():
    out = render_bot_report_html(_full_coverage_result())
    fragment = _market_coverage_fragment(out)
    assert "AAA" in fragment
    assert "BBB" in fragment
    assert "CCC" in fragment


def test_full_coverage_lists_unresolved_markets_as_not_measured():
    out = render_bot_report_html(_full_coverage_result())
    fragment = _market_coverage_fragment(out)
    assert "DDD" in fragment
    assert "could not be measured" in fragment


def test_full_coverage_warns_below_target():
    out = render_bot_report_html(_full_coverage_result(coverage_achieved_pct=60.0))
    fragment = _market_coverage_fragment(out)
    assert "notice-warning" in fragment
    assert "market_alignment" in fragment
    assert "liquidity_execution" in fragment
    assert "leverage_exposure" in fragment


def test_full_coverage_hides_warning_at_or_above_target():
    out = render_bot_report_html(_full_coverage_result(coverage_achieved_pct=85.0))
    fragment = _market_coverage_fragment(out)
    assert "notice-warning" not in fragment


def test_full_coverage_falls_back_to_old_rendering_when_resolved_markets_empty():
    """`resolved_markets=[]` (bot không đo được exposure nào ngoài thị
    trường CHÍNH, hoặc file cũ) phải lùi về đúng headline/ngưỡng CŨ dùng
    `primary_share_pct`, không được hiện "0 thị trường"."""
    out = render_bot_report_html(
        _full_coverage_result(resolved_markets=[], unresolved_markets=[])
    )
    fragment = _market_coverage_fragment(out)
    assert "0 markets" not in fragment
    assert "market being scored" in fragment.lower()


def test_full_coverage_escapes_untrusted_symbol_strings():
    out = render_bot_report_html(
        _full_coverage_result(
            resolved_markets=[
                {
                    "symbol": _XSS_PAYLOAD,
                    "share_pct": 52.6,
                    "venue_type": "CEX",
                    "trend": "BULLISH",
                    "volatility": "NORMAL",
                    "liquidity_tier": "DEEP",
                    "flow_bias": "BUY_PRESSURE",
                    "last_price": 100.0,
                }
            ],
            unresolved_markets=[
                {"symbol": _XSS_PAYLOAD, "share_pct": 10.5, "reason": "TIMEOUT"}
            ],
        )
    )
    assert _XSS_PAYLOAD not in out


# --------------------------------------------------------------------------- #
# Section ① -- "How this bot trades" (Việc 1/2 of the strategy-narrative task,
# plus the coordinator's own phase x cách-đánh cross-tab addendum).
# --------------------------------------------------------------------------- #


def _strategy_result(**overrides: Any) -> Dict[str, Any]:
    """A FULL-shaped result whose `evidence["strategy"]`/`["behavioral"]`
    match the shape `Agent/backend/web/data.py`'s `_strategy_evidence`/
    `_behavioral_evidence` build (see that module). Phase figures below are
    the real, committed `MU/bot_BB3398A957270A39` numbers (Modern-dAPI-
    Manatee) the coordinator quoted by hand -- deliberately re-used here so
    a failure message is checkable against a real, known table.
    """
    base: Dict[str, Any] = {
        "status": "FULL",
        "code": "STRATCODE1",
        "name": "Modern-dAPI-Manatee",
        "limited_reason": None,
        "unavailable": [],
        "verdict": "SỤT VỐN: TRUNG BÌNH · CHẤT LƯỢNG: KHÁ",
        "risk": 49.8,
        "quality": 60.0,
        "confidence": 55.0,
        "evidence": {
            "score_breakdown": {"decided_by": "WEIGHTED_AVERAGE"},
            "performance": {"trade_count": 29, "win_rate": 82.8},
            "strategy": {
                "observed_profile": "DayTrading",
                "declared_strategy": None,
                "directional_bias": "TWO_WAY",
                "long_share_pct": 47.2,
                "entry_style": "MEAN_REVERSION",
                "entry_style_evidence": "7/28 lệnh mở thuận chiều biến động 24h trước đó",
                "phase_coverage_pct": 40.3,
                "regime_dependence_pct": 18.7,
                "best_phase": "UPTREND_VOLATILE",
                "worst_phase": "UPTREND_CALM",
                "losing_phases": ["RANGE_VOLATILE"],
                "untested_phases": ["RANGE_CALM"],
                "tested_in_downtrend": False,
                "tested_in_trend": True,
                "phase_breakdown": [
                    {
                        "phase": "UPTREND_VOLATILE",
                        "trades": 15,
                        "win_rate": 86.7,
                        "total_pnl": 9857.0,
                        "long_share_pct": 7.0,
                        "average_leverage": 2.3,
                        "median_hold_minutes": 939.0,
                        "profit_share_pct": 18.7,
                    },
                    {
                        "phase": "UPTREND_CALM",
                        "trades": 9,
                        "win_rate": 88.9,
                        "total_pnl": 6488.0,
                        "long_share_pct": 33.0,
                        "average_leverage": 2.2,
                        "median_hold_minutes": 1382.0,
                        "profit_share_pct": 12.1,
                    },
                    {
                        "phase": "RANGE_VOLATILE",
                        "trades": 2,
                        "win_rate": 50.0,
                        "total_pnl": -51.0,
                        "long_share_pct": 0.0,
                        "average_leverage": 2.0,
                        "median_hold_minutes": 830.0,
                        "profit_share_pct": 1.7,
                    },
                    {
                        "phase": "DOWNTREND_VOLATILE",
                        "trades": 1,
                        "win_rate": 100.0,
                        "total_pnl": 1461.0,
                        "long_share_pct": 100.0,
                        "average_leverage": 2.0,
                        "median_hold_minutes": 734.0,
                        "profit_share_pct": 2.6,
                    },
                    {
                        "phase": "DOWNTREND_CALM",
                        "trades": 2,
                        "win_rate": 100.0,
                        "total_pnl": 829.0,
                        "long_share_pct": 100.0,
                        "average_leverage": 2.5,
                        "median_hold_minutes": 1225.0,
                        "profit_share_pct": 1.5,
                    },
                ],
            },
            "behavioral": {
                "martingale_escalation_detected": False,
                "averaging_down_detected": False,
                "loss_chasing_score": 0.1,
                "overtrading_score": 0.05,
                "reentry_loop_detected": False,
                "size_escalation_score": 0.0,
                "leverage_escalation_detected": False,
                "behavioral_risk_tier": "MEDIUM",
            },
        },
        "mc": None,
        "assets": [],
        "text": ["Kết luận: SỤT VỐN TRUNG BÌNH."],
        "narrative": None,
    }
    base.update(overrides)
    return base


def _cach_choi_fragment(out: str) -> str:
    match = re.search(r'<section class="card" id="cach-choi">.*?</section>', out, re.S)
    assert match, "expected a rendered 'How this bot trades' section"
    return match.group(0)


def test_strategy_section_present_right_after_conclusion_with_own_details() -> None:
    out = render_bot_report_html(_strategy_result())
    conclusion_pos = out.index("Conclusion and recommendation")
    strategy_pos = out.index("How this bot trades")
    assert conclusion_pos < strategy_pos
    fragment = _cach_choi_fragment(out)
    assert '<details class="theory">' in fragment


def test_strategy_section_translates_every_enum_no_raw_tokens_leak() -> None:
    out = render_bot_report_html(_strategy_result())
    fragment = _cach_choi_fragment(out)
    for raw_enum in (
        "TREND_FOLLOWING",
        "MEAN_REVERSION",
        "LONG_ONLY",
        "SHORT_ONLY",
        "LONG_TILTED",
        "SHORT_TILTED",
        "TWO_WAY",
        "MIXED",
        "UPTREND_CALM",
        "UPTREND_VOLATILE",
        "DOWNTREND_CALM",
        "DOWNTREND_VOLATILE",
        "RANGE_CALM",
        "RANGE_VOLATILE",
    ):
        assert raw_enum not in fragment, f"raw enum {raw_enum!r} leaked into the page"
    # And the actual Vietnamese translations are the ones shown.
    assert "mean-reversion" in fragment  # MEAN_REVERSION
    assert "trades both directions" in fragment  # TWO_WAY
    assert "uptrend, highly volatile" in fragment  # UPTREND_VOLATILE
    assert "sideways, calm" in fragment  # RANGE_CALM (untested_phases)


def test_strategy_section_phase_table_sorted_by_profit_share_descending() -> None:
    out = render_bot_report_html(_strategy_result())
    fragment = _cach_choi_fragment(out)
    # The phase with the highest profit_share_pct (18.7, "tăng, biến động
    # mạnh") must lead the table -- coordinator's own explicit ordering
    # requirement ("pha nào làm ra tiền thì đứng trước").
    first_phase_pos = fragment.index("uptrend, highly volatile")
    other_positions = [
        fragment.index(label) for label in ("downtrend, calm", "sideways, highly volatile")
    ]
    assert all(first_phase_pos < pos for pos in other_positions)


def test_strategy_section_marks_phase_row_confidence_tiers() -> None:
    """Three-tier confidence (coordinator's own explicit threshold): N>=10
    "enough sample" (no badge -- the default, trustworthy case), 3<=N<10 "thin sample",
    N<3 "not yet meaningful". The fixture's DOWNTREND_VOLATILE row has exactly
    ONE trade at 100% win rate -- it must never read as equally solid
    evidence as the 15-trade UPTREND_VOLATILE row (coordinator's own
    explicit example of the failure mode this guards against).
    """
    out = render_bot_report_html(_strategy_result())
    fragment = _cach_choi_fragment(out)
    table_match = re.search(r"<table>.*?</table>", fragment, re.S)
    assert table_match, "expected a rendered phase table"
    rows = table_match.group(0).split("<tr>")
    big_sample_row = next(r for r in rows if "uptrend, highly volatile" in r)  # 15 trades
    assert "enough sample" not in big_sample_row  # no badge at all for a healthy row
    assert "thin sample" not in big_sample_row
    assert "not yet meaningful" not in big_sample_row

    thin_sample_row = next(
        r for r in rows if "uptrend, calm" in r
    )  # UPTREND_CALM, 9 trades
    assert "thin sample" in thin_sample_row
    assert "not yet meaningful" not in thin_sample_row

    insufficient_row = next(
        r for r in rows if "downtrend, highly volatile" in r
    )  # DOWNTREND_VOLATILE, 1 trade
    assert "not yet meaningful" in insufficient_row


def test_phase_confidence_vi_thresholds() -> None:
    assert report_page_module._phase_confidence_vi(15) == "enough sample"
    assert report_page_module._phase_confidence_vi(10) == "enough sample"
    assert report_page_module._phase_confidence_vi(9) == "thin sample"
    assert report_page_module._phase_confidence_vi(3) == "thin sample"
    assert report_page_module._phase_confidence_vi(2) == "not yet meaningful"
    assert report_page_module._phase_confidence_vi(1) == "not yet meaningful"
    assert report_page_module._phase_confidence_vi(0) == "not yet meaningful"
    assert report_page_module._phase_confidence_vi(None) == "not yet meaningful"


def test_strategy_section_shows_coverage_next_to_table_and_warns_below_60pct() -> None:
    out = render_bot_report_html(_strategy_result())
    fragment = _cach_choi_fragment(out)
    assert "40,3%" in fragment or "40.3%" in fragment
    assert "notice-warning" in fragment
    assert "HINT, NOT a firm conclusion" in fragment
    # Coordinator's own explicit "nêu đúng lý do" requirement: the real cause
    # is missing reference candles for some traded symbols -- the warning
    # must name that cause and explicitly rule out a timestamp/transition-
    # zone explanation, never invent a different reason.
    assert "reference candle series" in fragment
    assert "not a timing mismatch" in fragment


def test_strategy_section_hides_coverage_warning_at_or_above_60pct() -> None:
    result = _strategy_result()
    result["evidence"]["strategy"]["phase_coverage_pct"] = 75.0
    out = render_bot_report_html(result)
    fragment = _cach_choi_fragment(out)
    assert "GỢI Ý, KHÔNG PHẢI kết luận chắc chắn" not in fragment


def test_strategy_section_shows_untested_phases() -> None:
    out = render_bot_report_html(_strategy_result())
    fragment = _cach_choi_fragment(out)
    assert "Never traded through market phase" in fragment
    assert "sideways, calm" in fragment


def test_strategy_section_hides_untested_block_when_empty() -> None:
    result = _strategy_result()
    result["evidence"]["strategy"]["untested_phases"] = []
    out = render_bot_report_html(result)
    fragment = _cach_choi_fragment(out)
    assert "Never traded through market phase" not in fragment


def test_strategy_section_empty_phase_breakdown_hides_table_not_section() -> None:
    result = _strategy_result()
    result["evidence"]["strategy"]["phase_breakdown"] = []
    out = render_bot_report_html(result)
    fragment = _cach_choi_fragment(out)
    assert "<table>" not in fragment
    # The prose part of the section must still render without crashing.
    assert "Observed profile" in fragment


def test_strategy_section_absent_when_evidence_has_no_strategy_key() -> None:
    result = _xss_result()
    out = render_bot_report_html(result)
    assert "How this bot trades" not in out


def test_strategy_section_unknown_observations_say_insufficient_evidence() -> None:
    result = _strategy_result()
    result["evidence"]["strategy"].update(
        {
            "directional_bias": "UNKNOWN",
            "entry_style": "UNKNOWN",
            "best_phase": None,
            "worst_phase": None,
        }
    )
    out = render_bot_report_html(result)
    fragment = _cach_choi_fragment(out)
    assert fragment.count("not enough evidence to determine") >= 2


def test_strategy_section_behavioral_flags_render_when_detected() -> None:
    result = _strategy_result()
    result["evidence"]["behavioral"]["martingale_escalation_detected"] = True
    result["evidence"]["behavioral"]["leverage_escalation_detected"] = True
    out = render_bot_report_html(result)
    fragment = _cach_choi_fragment(out)
    assert "martingale-style stacking" in fragment
    assert "raising leverage after a losing trade" in fragment


def test_strategy_section_no_behavioral_flags_says_so_explicitly() -> None:
    out = render_bot_report_html(_strategy_result())
    fragment = _cach_choi_fragment(out)
    assert "no sign of averaging down" in fragment


def test_real_full_result_strategy_evidence_has_no_raw_enum_leak(
    full_result: Dict[str, Any],
) -> None:
    """Scans the ACTUAL pipeline output (real MU/bot_BB3398A957270A39 fixture,
    no hand-built evidence) for every enum this task named explicitly --
    the coordinator's own acceptance bar ("quét trang thật, không còn
    TREND_FOLLOWING/LONG_TILTED lọt ra").
    """
    out = render_bot_report_html(full_result)
    for raw_enum in (
        "TREND_FOLLOWING",
        "MEAN_REVERSION",
        "LONG_ONLY",
        "SHORT_ONLY",
        "LONG_TILTED",
        "SHORT_TILTED",
        "TWO_WAY",
        "UPTREND_CALM",
        "UPTREND_VOLATILE",
        "DOWNTREND_CALM",
        "DOWNTREND_VOLATILE",
        "RANGE_CALM",
        "RANGE_VOLATILE",
    ):
        assert raw_enum not in out, f"raw enum {raw_enum!r} leaked into the real page"


def test_phase_label_vi_translates_every_known_phase() -> None:
    for raw, expected_substring in (
        ("UPTREND_CALM", "uptrend"),
        ("UPTREND_VOLATILE", "highly volatile"),
        ("RANGE_CALM", "sideways"),
        ("UNKNOWN", "phase not identified"),
        (None, "phase not identified"),
        ("SOME_FUTURE_PHASE", "phase not identified"),
    ):
        assert expected_substring in report_page_module._phase_label_vi(raw)


# --------------------------------------------------------------------------- #
# Khung trang 2 cột (rail trái + cột nội dung) -- xem `_render_sidebar`/
# `_render_nav`/`_CSS`'s `.page` grid. Việc "nhìn xấu quá" v2.
# --------------------------------------------------------------------------- #


def test_page_has_left_rail_with_identity_scores_and_table_of_contents(
    full_result: Dict[str, Any],
) -> None:
    out = render_bot_report_html(full_result)
    # Rail trái tồn tại và mang đúng ba thứ phải luôn nhìn thấy được: thương
    # hiệu, danh tính bot (kèm nhãn phán quyết) và 3 ô điểm số hero.
    assert '<aside class="side">' in out
    assert '<div class="side-identity">' in out
    assert "verdict-badge" in out
    assert out.count('class="stat-tile stat-tile-hero"') == 3
    # Mục lục trỏ tới đúng các mục ĐANG có trên trang, không phải một danh
    # sách anchor cứng có thể trỏ vào hư không.
    assert '<nav class="nav"' in out
    for anchor in ("ket-luan", "nhan-dinh", "cach-choi", "so-lieu"):
        assert f'href="#{anchor}"' in out, anchor
        assert f'id="{anchor}"' in out, anchor
    # Nút đổi giao diện đã dọn xuống chân rail, không còn nằm cạnh thanh tab.
    assert '<div class="side-foot">' in out
    assert "header-actions" not in out


def test_tab_titles_renamed_and_verdict_wording_gone(
    full_result: Dict[str, Any],
) -> None:
    out = render_bot_report_html(full_result)
    assert '<span class="tab-title">Analyst Result</span>' in out
    assert '<span class="tab-title">Premium Market</span>' in out
    assert '<span class="tab-title">Other &amp; Position</span>' in out
    assert "Báo Cáo Phán Quyết" not in out
    # Vòng tròn số thứ tự tab và animation đổi tab đã bỏ hẳn (animation làm
    # ảnh chụp kiểm thử thị giác bắt được trạng thái mờ dở dang).
    assert "tab-num" not in out
    assert "fadeIn" not in out


def test_section_renders_block_header_and_body_with_optional_eyebrow_note() -> None:
    plain = report_page_module._section("Tiêu đề", "<p>x</p>", anchor="abc")
    assert '<section class="card" id="abc">' in plain
    assert '<header class="block-h"><h2>Tiêu đề</h2></header>' in plain
    assert '<div class="block-b"><p>x</p></div>' in plain
    rich = report_page_module._section(
        "Tiêu đề", "<p>x</p>", eyebrow="Nhóm", note="nguồn: OKX"
    )
    assert '<span class="eyebrow">Nhóm</span>' in rich
    assert '<span class="note">nguồn: OKX</span>' in rich


# --------------------------------------------------------------------------- #
# Bảng kết luận KHÔNG ĐƯỢC BỊA SỐ.
#
# Lỗi ngày 20/09: cả khối này mang nguyên giá trị của bản mockup -- 213 lệnh,
# 2.4 lệnh/ngày, rủi ro 100, chất lượng 33, thị trường "ETH", và một nhãn
# viết cứng "CRITICAL RISK · LIQUIDATION" đè lên nhãn thật. Đo trên sản phẩm
# đang chạy: ba bot khác hẳn nhau (71 / 212 / 268 lệnh, hai nhãn khác nhau)
# đều hiện ra CÙNG một dòng. Số lệnh luôn rơi về 213 vì mã đọc nhầm tên khoá
# (`total_trades`, thứ không tồn tại) thay vì `trade_count`.
#
# Không test nào bắt được vì không test nào so nội dung bảng với dữ liệu
# NGUỒN của chính bot đó -- chúng chỉ đếm khối và tìm chuỗi tiếng Việt.
# --------------------------------------------------------------------------- #


def test_conclusion_panel_shows_this_bots_own_verdict_not_a_hardcoded_one(
    full_result,
):
    html = render_bot_report_html(full_result)
    assert "CRITICAL RISK · LIQUIDATION" not in html, (
        "nhãn viết cứng của bản mockup -- nó không nằm trong 6 nhãn hợp lệ"
    )
    verdict = full_result.get("verdict")
    assert verdict and verdict in html


def test_conclusion_panel_sample_line_uses_this_bots_own_trade_count(full_result):
    html = render_bot_report_html(full_result)
    perf = (full_result.get("evidence") or {}).get("performance") or {}
    real = full_result.get("trade_count") or perf.get("trade_count")
    assert real, "fixture phải có số lệnh thật, nếu không test này vô nghĩa"
    match = re.search(r"SAMPLE: ([\d,]+) TRADES", html)
    assert match, "không thấy dòng SAMPLE"
    assert int(match.group(1).replace(",", "")) == int(real)
    assert "SAMPLE: 213 TRADES" not in html
    assert "2.4 TRADES/DAY" not in html


def test_conclusion_panel_omits_the_sample_line_when_nothing_is_measured():
    """Thiếu số thì BỎ HẲN dòng đó, không điền giá trị thay thế."""
    bare = {
        "status": "FULL",
        "code": "NOSAMPLE1",
        "name": "No Sample",
        "verdict": "INSUFFICIENT EVIDENCE",
        "evidence": {"dimensions": {}, "performance": {}},
    }
    html = render_bot_report_html(bare)
    assert "SAMPLE:" not in html
    assert "TRADES/DAY" not in html
    assert "213" not in html
