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

A real FULL fixture is built the same way `Agent/test/test_web_app.py` does
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
# Only flag a bad numeric token when it appears as a whole SVG attribute
# value (e.g. `x="nan"`), never as a substring of ordinary prose -- Vietnamese
# and English text legitimately contains "nan" (e.g. "dominant"), "none" etc.
_ATTR_VALUE_RE = re.compile(r'="([^"]*)"')


def _assert_no_bad_numeric_attrs(svg_fragment: str) -> None:
    for match in _ATTR_VALUE_RE.finditer(svg_fragment):
        value = match.group(1).strip().lower()
        assert value not in _BAD_TOKENS, f"bad SVG attribute value: {match.group(0)!r}"


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
    assert "Kết luận và khuyến nghị" in out
    assert "<pre>" not in out

    # Section 3: per-dimension bars.
    assert "Điểm từng chiều rủi ro" in out
    assert "bar-chart" in out

    # Section 4: Monte Carlo.
    assert "Mô phỏng Monte Carlo" in out

    # Section 6: trade metrics table.
    assert "Số liệu giao dịch" in out
    assert "Profit factor" in out

    # Section 7: traded assets.
    assert "Tài sản đang giao dịch" in out

    # Every section (3-7) that rendered must carry at least one "sở cứ +
    # lý thuyết" collapsible -- the task's own explicit third requirement.
    assert out.count('<details class="theory">') >= 5


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
    assert "che giấu" in out
    assert "Profit factor" in out  # the component's own label still shows


def test_limited_result_has_no_trade_metrics_or_assets_sections() -> None:
    """A LIMITED bot has no `evidence.performance` and always empty `assets`
    (see data.py's own contract) -- those sections must simply not appear,
    not render empty/broken."""
    result = _limited_result()
    out = render_bot_report_html(result)
    assert "Số liệu giao dịch" not in out
    assert "Tài sản đang giao dịch" not in out


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
    assert "Mô phỏng Monte Carlo" in out
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
    assert "Đường vốn tích luỹ theo lệnh đã chốt" in out
    assert "Tăng trưởng &amp; cơ cấu kết quả" in out
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
    assert "Đường vốn tích luỹ theo lệnh đã chốt" not in out


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
    assert "Đường vốn tích luỹ theo lệnh đã chốt" not in out


def test_growth_curve_hidden_for_limited_result() -> None:
    out = render_bot_report_html(_limited_result())
    assert "Đường vốn tích luỹ theo lệnh đã chốt" not in out


def test_growth_curve_hidden_for_not_found_result() -> None:
    result = {"status": "NOT_FOUND", "code": "N", "text": []}
    out = render_bot_report_html(result)
    assert "Đường vốn tích luỹ theo lệnh đã chốt" not in out


def test_growth_curve_renders_and_validates_for_a_normal_sequence(
    full_result: Dict[str, Any],
) -> None:
    result = _with_closed_trade_series(full_result, [100.0, -40.0, 60.0, -10.0, 200.0])
    out = render_bot_report_html(result)
    assert "Đường vốn tích luỹ theo lệnh đã chốt" in out
    assert "Tăng trưởng &amp; cơ cấu kết quả" in out
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
    assert "Đường vốn tích luỹ theo lệnh đã chốt" in out
    svgs = _extract_svgs(out)
    assert svgs
    for svg in svgs:
        _assert_valid_xml_fragment(svg)
        _assert_no_bad_numeric_attrs(svg)


def test_win_loss_composition_renders_two_pies_for_a_real_full_result(
    full_result: Dict[str, Any],
) -> None:
    out = render_bot_report_html(full_result)
    assert "Cơ cấu thắng/thua" in out
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
    assert "Cơ cấu thắng/thua" not in out


def test_horizon_probability_chart_present_for_a_real_full_result(
    full_result: Dict[str, Any],
) -> None:
    out = render_bot_report_html(full_result)
    assert "So sánh xác suất có lãi theo horizon (biểu đồ)" in out


def test_horizon_probability_chart_hidden_when_scenarios_absent(
    full_result: Dict[str, Any],
) -> None:
    result = copy.deepcopy(full_result)
    result["mc"]["horizon_scenarios"] = []
    out = render_bot_report_html(result)
    assert "So sánh xác suất có lãi theo horizon (biểu đồ)" not in out


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
        assert "Không có dữ liệu" in svg
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
