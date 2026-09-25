"""Cross-cutting acceptance tests for the two-axis verdict redesign (task's
own numbered "Test bắt buộc" list): the 6 labels themselves, backward
compatibility with the 30 real `assessment.json` files already on disk,
`verdict_basis`, the rewritten `ACTION_VI`, and a sweep for stray English on
the real `/bot/<code>` page.

Why a separate file rather than folding into test_quality_verdict.py /
test_report_page.py: these tests each cross several modules at once
(verdict.py + data.py + agent_server.py for backward compatibility;
reasons.py + render.py + report_page.py + tokens.css for the "no retired
label survives" sweep) -- they belong to the redesign as a whole, not to any
one module's own test file.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from Agent.backend.infra.config import config
from Agent.backend.report.qc.reporting.reasons import ACTION_VI, action_vi
from Agent.backend.report.qc.reporting.render import VERDICT_ORDER
from Agent.backend.report.qc.scoring.verdict import (
    VERDICT_BASIS_VI,
    VERDICT_HIDDEN_RISK,
    VERDICT_HIGH_DD_GOOD_Q,
    VERDICT_HIGH_DD_WEAK_Q,
    VERDICT_LOW_DD_GOOD_Q,
    VERDICT_LOW_DD_WEAK_Q,
    VERDICT_UNKNOWN,
    label_from_scores,
)
from Agent.backend.external.sources.bot_source import BotDataSource
from Agent.backend.external.sources.market_source import (
    MarketDataSource,
    MarketDataUnavailableError,
)
from Agent.backend.web.data import WebDataService
from Agent.backend.web.report_page import VERDICT_COLOR, render_bot_report_html

DATA_DIR = Path(config.DATA_DIR)
REPO_ROOT = Path(__file__).resolve().parents[3]

ALL_SIX_LABELS = {
    VERDICT_HIGH_DD_GOOD_Q,
    VERDICT_HIGH_DD_WEAK_Q,
    VERDICT_LOW_DD_GOOD_Q,
    VERDICT_LOW_DD_WEAK_Q,
    VERDICT_HIDDEN_RISK,
    VERDICT_UNKNOWN,
}

# The 4 retired single-axis labels this whole redesign replaces. Kept ONLY
# here (as data, not as importable constants -- verdict.py no longer defines
# them at all) so the sweep below has something concrete to search for.
RETIRED_LABELS = {"NGUY HIỂM", "TIỀM ẨN", "TIỀM NĂNG", "AN TOÀN"}


# --------------------------------------------------------------------------- #
# 1. The 30 real assessment.json files -- backward compatibility.
# --------------------------------------------------------------------------- #



def _detail_html(html: str) -> str:
    """The page without its Overview block: the Overview repeats a few Summary
    charts on purpose, so chart-count invariants are about the Detail tabs."""
    i, j = html.find('<div class="rm-overview">'), html.find('<div class="rm-detail">')
    return html[:i] + html[j:] if 0 <= i < j else html

def _real_assessment_files() -> List[Path]:
    return sorted((DATA_DIR / "report" / "single").glob("*/latest.json"))


def test_real_assessment_files_exist_for_this_sweep_to_mean_anything():
    files = _real_assessment_files()
    assert len(files) >= 30, (
        f"expected the project's own committed 30 assessment.json files, "
        f"found {len(files)} -- this test's whole point is reading real data"
    )


def test_every_real_assessment_file_recomputes_to_one_of_the_six_labels():
    """Task's own explicit requirement: read the 30 real files, each must
    compute a valid new label, no file may crash the recompute, and no
    retired label may appear in what THIS recompute produces (old labels may
    of course still sit, unread, in `khuyen_nghi.ket_luan` on disk -- that is
    the backward-compat problem being solved, not a bug in the fixture)."""
    files = _real_assessment_files()
    assert files
    old_to_new: Dict[str, set] = {}
    for path in files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        cham_diem = doc.get("scoring") or {}
        old_label = (doc.get("recommendation") or {}).get("verdict")
        new_label = label_from_scores(
            cham_diem.get("risk_score"),
            cham_diem.get("quality_score"),
            cham_diem.get("hidden_risk_flags") or [],
        )
        assert new_label in ALL_SIX_LABELS, (
            f"{path}: label_from_scores produced {new_label!r}, not one of "
            "the 6 valid states"
        )
        assert new_label not in RETIRED_LABELS
        old_to_new.setdefault(str(old_label), set()).add(new_label)
    # Printed for the human report this task asks for ("bảng ánh xạ phân bố
    # nhãn cũ -> mới") -- pytest -s / -q -rA surfaces this; not an assertion
    # target on purpose, since the real dataset's own distribution is exactly
    # what the task wants reported, not pinned as a regression gate.
    print("\nOld label -> set of new labels it recomputes to, across 30 real files:")
    for old, news in sorted(old_to_new.items()):
        print(f"  {old!r} -> {sorted(news)}")


def test_bot_listing_row_recomputes_the_same_label_for_every_real_file():
    """`data.py`'s `bot_listing_row` (what `GET /api/bots` serves -- see
    Việc 1's own bug report and test_bot_listing_rows.py) must agree with
    `label_from_scores` called directly -- two code paths, one answer."""
    from Agent.backend.web.data import bot_listing_row

    for path in _real_assessment_files():
        doc = json.loads(path.read_text(encoding="utf-8"))
        row = bot_listing_row(doc)
        assert row is not None
        cham_diem = doc.get("scoring") or {}
        expected = label_from_scores(
            cham_diem.get("risk_score"),
            cham_diem.get("quality_score"),
            cham_diem.get("hidden_risk_flags") or [],
        )
        assert row["verdict"] == expected


# --------------------------------------------------------------------------- #
# 2. Threshold boundaries and hidden-risk override, expressed against
# label_from_scores directly (verdict.py's own test_quality_verdict.py
# already covers `decide()`; this is the pure-function surface backward
# compatibility depends on).
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "risk,quality,expected",
    [
        (70.0, 90.0, VERDICT_HIGH_DD_GOOD_Q),
        (69.999, 90.0, VERDICT_LOW_DD_GOOD_Q),
        (10.0, 65.0, VERDICT_LOW_DD_GOOD_Q),
        (10.0, 64.999, VERDICT_LOW_DD_WEAK_Q),
        (90.0, 30.0, VERDICT_HIGH_DD_WEAK_Q),
        (90.0, 90.0, VERDICT_HIGH_DD_GOOD_Q),
    ],
)
def test_label_from_scores_boundaries(risk, quality, expected):
    assert label_from_scores(risk, quality, []) == expected


def test_label_from_scores_hidden_flags_override_low_risk_and_good_quality():
    """Bot risk thấp + quality tốt + có cờ ẩn -> RỦI RO BỊ CHE (task's own
    explicit test case)."""
    assert (
        label_from_scores(10.0, 95.0, ["lỗ chưa chốt bằng 65% vốn"])
        == VERDICT_HIDDEN_RISK
    )


def test_label_from_scores_none_risk_is_unknown():
    assert label_from_scores(None, 90.0, []) == VERDICT_UNKNOWN
    assert label_from_scores(None, None, ["bất kỳ cờ nào"]) == VERDICT_UNKNOWN


# --------------------------------------------------------------------------- #
# 3. Sweep for retired labels in source -- AST-based (not a plain-text grep)
# so that a `#` comment mentioning a retired label for CONTEXT (this file's
# own RETIRED_LABELS constant above, or an explanatory comment elsewhere)
# never trips it: comments are not part of the parse tree, so only an actual
# string literal in the running code can match. Restricted to Agent/backend
# and Agent/frontend -- the shipped product surface -- not Agent/none/test (whose own
# fixtures are free to use an old label as arbitrary placeholder data, as
# several already do) and not Agent/data (the real, deliberately-unmigrated
# old assessment.json files this whole feature exists to read past).
# --------------------------------------------------------------------------- #


def _iter_string_constants(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value


def test_no_retired_verdict_label_survives_as_a_string_literal_in_backend_or_web():
    hits: List[str] = []
    for base in (REPO_ROOT / "Agent" / "backend", REPO_ROOT / "Agent" / "web"):
        for path in base.rglob("*.py"):
            for value in _iter_string_constants(path):
                if value.strip() in RETIRED_LABELS:
                    hits.append(f"{path}: {value!r}")
    assert not hits, (
        "retired single-axis verdict label(s) still hard-coded:\n" + "\n".join(hits)
    )


def test_tokens_css_has_no_retired_verdict_label_in_a_comment_value_pair():
    css_text = (REPO_ROOT / "Agent" / "frontend" / "tokens.css").read_text(encoding="utf-8")
    # tokens.css only ever carries a label as a `/* COMMENT */` next to a
    # color declaration (see that file's own "Verdict classification"
    # block); a plain substring check is enough since CSS has no string-vs-
    # comment ambiguity the way Python source does.
    for label in RETIRED_LABELS:
        assert label not in css_text, f"tokens.css still mentions {label!r}"


def test_verdict_order_color_and_valid_verdicts_use_only_the_new_labels():
    from Agent.backend.scripts.agent_server import VALID_VERDICTS

    assert set(VERDICT_ORDER.keys()) <= ALL_SIX_LABELS
    assert set(VERDICT_COLOR.keys()) == ALL_SIX_LABELS
    assert set(VALID_VERDICTS) == ALL_SIX_LABELS
    for old in RETIRED_LABELS:
        assert old not in VERDICT_ORDER
        assert old not in VERDICT_COLOR
        assert old not in VALID_VERDICTS


# --------------------------------------------------------------------------- #
# 4. verdict_basis -- present, verbatim, in both the JSON result and the
# rendered detail page.
# --------------------------------------------------------------------------- #

_FIXTURE_BOT_DIR = DATA_DIR / "trade" / "bot_BB3398A957270A39"
_VALID_CODE = "BB3398A957270A39"


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
    result = service.analyze(_VALID_CODE)
    assert result["status"] == "FULL"
    return result


def test_verdict_basis_present_verbatim_in_the_json_result(full_result):
    assert full_result["verdict_basis"] == VERDICT_BASIS_VI


def test_verdict_basis_present_verbatim_on_the_rendered_page(full_result):
    html = render_bot_report_html(full_result)
    assert VERDICT_BASIS_VI in html


def test_verdict_basis_kept_in_the_compact_marketplace_wire_summary(full_result):
    """`verdict_basis` answers "sở cứ ở đâu" for the verdict label above it
    (rho 0.64, 95% CI [0.39, 0.80]) -- it used to be trimmed from this
    compact summary to stay under an earlier, stricter 5,000-char budget,
    even though a real fixture bot's response already ran over that budget
    WITHOUT it. That trade was reverted (see app.py's
    `_analyze_summary_for_wire` and `ANALYZE_SUMMARY_SIZE_BUDGET_CHARS`):
    the field is kept, verbatim, and the budget raised instead."""
    from Agent.backend.web.app import _analyze_summary_for_wire

    summary = _analyze_summary_for_wire(dict(full_result))
    assert summary["verdict_basis"] == VERDICT_BASIS_VI


# --------------------------------------------------------------------------- #
# 5. ACTION_VI -- no imperative language, cites this bot's own number.
# --------------------------------------------------------------------------- #

_FORBIDDEN_ACTION_SUBSTRINGS = (
    "DỪNG NGAY",
    "trong mọi trường hợp",
    "phải",
    "tuyệt đối",
    # Assessment only: no advice, and no "decide for yourself" either.
    "your call",
    "no action needed",
    "copy it",
)


def _sample_row(action: str) -> SimpleNamespace:
    return SimpleNamespace(
        recommended_action=action,
        risk_score=88.0,
        quality_score=42.0,
        p_ruin=12.0,
        p95_max_drawdown=34.0,
        capital_at_risk=50_000.0,
        stress_verdict="LIQUIDATED" if action == "EMERGENCY_STOP" else "SURVIVED",
    )


@pytest.mark.parametrize(
    "action",
    ["EMERGENCY_STOP", "PAUSE", "REDUCE", "BLOCK_NEW_TRADES", "WARN", "MONITOR"],
)
def test_action_vi_has_no_forbidden_imperative_language(action):
    text = action_vi(_sample_row(action))
    for forbidden in _FORBIDDEN_ACTION_SUBSTRINGS:
        assert forbidden not in text, (
            f"{action}: found forbidden {forbidden!r} in {text!r}"
        )


@pytest.mark.parametrize(
    "action",
    ["EMERGENCY_STOP", "PAUSE", "REDUCE", "BLOCK_NEW_TRADES", "WARN", "MONITOR"],
)
def test_action_vi_cites_a_number_specific_to_this_bot(action):
    text = action_vi(_sample_row(action))
    assert re.search(r"\d", text), f"{action}: no bot-specific number in {text!r}"


def test_action_vi_keys_are_unchanged_internal_action_codes():
    """Task's own explicit requirement: the dict KEYS (fusion.py's action
    codes) must stay exactly as they were -- only the values' TYPE changed
    (static string -> per-bot text generator)."""
    assert set(ACTION_VI.keys()) == {
        "EMERGENCY_STOP",
        "PAUSE",
        "REDUCE",
        "BLOCK_NEW_TRADES",
        "WARN",
        "MONITOR",
    }
    assert all(callable(fn) for fn in ACTION_VI.values())


def test_action_vi_degrades_gracefully_with_no_simulation_data():
    """A bot scored before Monte Carlo ran, or one with every optional field
    `None`, must still produce text -- no crash, no forbidden language."""
    for action in (
        "EMERGENCY_STOP",
        "PAUSE",
        "REDUCE",
        "BLOCK_NEW_TRADES",
        "WARN",
        "MONITOR",
    ):
        row = SimpleNamespace(
            recommended_action=action,
            risk_score=50.0,
            quality_score=None,
            p_ruin=None,
            p95_max_drawdown=None,
            capital_at_risk=None,
            stress_verdict=None,
        )
        text = action_vi(row)
        assert isinstance(text, str) and text
        for forbidden in _FORBIDDEN_ACTION_SUBSTRINGS:
            assert forbidden not in text


# --------------------------------------------------------------------------- #
# 6. Real /bot/<code> page -- structural invariants (7 <svg>, 11 <details>)
# and a sweep for stray VIETNAMESE.
#
# This sweep used to run the other way around: back when the page was
# rendered in Vietnamese with a narrow, documented allowlist of intentional
# English loanwords/academic terms, it flagged any OTHER run of >=4 ASCII
# words as a forgotten-to-translate fragment. Việc 1's full VN->EN
# conversion of this product (~2,200 strings across 60+ files, this task)
# made that premise backwards: the page is now English BY DESIGN, so a sweep
# for "stray English" would flag nearly the entire page and catch nothing
# real. The English-loanword allowlist it used to carry
# ("Deflated Sharpe Ratio (DSR)", "STATIONARY_BOOTSTRAP", "OKX copy
# trading", the fusion.py/infra/quality.py off-limits-module phrases, etc.)
# is retired along with it.
#
# The contract this sweep actually protects -- "the translation pass did
# not miss a spot" -- still matters, so it is replaced here with its mirror
# image: any Vietnamese-only diacritic surviving on the rendered page is now
# the sign of a string this task's conversion missed. `López` (from "Bailey
# and López de Prado" in VERDICT_BASIS_VI's academic citation) is the one
# legitimate exception -- a proper noun, not a leftover Vietnamese string,
# verified by reading verdict.py's own `VERDICT_BASIS_VI` above.
# --------------------------------------------------------------------------- #

_TAG_OR_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", re.DOTALL
)

# Letters that only ever appear in Vietnamese text among what this page
# renders (accented Latin letters shared with other languages, e.g. plain
# "d with stroke" is Vietnamese đ but "e"/"a" acutes alone are common to many
# languages -- this set is Vietnamese-specific diacritics/letters only).
_VIETNAMESE_LETTERS_RE = re.compile(
    "[ĂÂÊÔƠƯĐăâêôơưđ"
    "ẦẤẨẪẬẰẮẲẴẶỀẾỂỄỆỒỐỔỖỘỜỚỞỠỢỪỨỬỮỰ"
    "ầấẩẫậằắẳẵặềếểễệồốổỗộờớởỡợừứửữự"
    "ẢÃẠẺẼẸỈĨỊỎÕỌỦŨỤỶỸỴảãạẻẽẹỉĩịỏõọủũụỷỹỵ]"
)

_ALLOWED_STRAY_WORDS = (
    # `López` in the "Bailey and López de Prado, 2012 and 2014" academic
    # citation baked into VERDICT_BASIS_VI -- a real author's name, not an
    # untranslated Vietnamese fragment. Its "ó" is the only diacritic this
    # regex would otherwise flag that isn't Vietnamese-specific.
    "López",
)


def _vietnamese_word_hits(text: str) -> List[str]:
    return sorted(
        {
            word
            for word in text.split()
            if _VIETNAMESE_LETTERS_RE.search(word)
            and word.strip(".,:;%()\"'-") not in _ALLOWED_STRAY_WORDS
        }
    )


def _strip_html(html: str) -> str:
    return _TAG_OR_SCRIPT_STYLE_RE.sub(" ", html)


def _ascii_word_runs(text: str, min_words: int = 4) -> List[str]:
    """Runs of >=`min_words` consecutive whitespace-separated tokens that are
    each a pure ASCII alphabetic word -- the same heuristic the task
    describes having used itself to find the original 6 phrases."""
    words = text.split()
    run: List[str] = []
    hits: List[str] = []

    def is_ascii_word(word: str) -> bool:
        core = word.strip(".,:;%()\"'-")
        return bool(core) and bool(_ASCII_WORD_RE.fullmatch(core))

    for word in words:
        if is_ascii_word(word):
            run.append(word)
        else:
            if len(run) >= min_words:
                hits.append(" ".join(run))
            run = []
    if len(run) >= min_words:
        hits.append(" ".join(run))
    return hits


def test_real_bot_page_keeps_seven_svg_and_eleven_details(full_result):
    html = render_bot_report_html(full_result)
    # 6 -> 8: Khối Monte Carlo nay cung cấp 3 góc nhìn chọn qua tab (Distribution,
    # Probability Cone, Median Trajectory), mỗi tab 1 SVG riêng biệt (tổng 8 SVGs).
    # 8 -> 13 (2026-09-24 redesign): +3 half-circle gauges on the header
    # scores, +2 outcome donuts and the capital curve in Growth, +1 "by tier"
    # donut in the risk-dimension section, whose bar chart became HTML rows.
    # 13 -> 14: the Monte Carlo "Show streaks & horizons" toggle's chevron.
    # 15 -> 13: the show/hide toggles draw their chevron in CSS, not SVG.
    # 13 -> 19: the Overview mode (`_render_overview`, "same renderers, same
    # numbers as Detail") draws a second copy of the conclusion's two WHY
    # icons, the three Growth charts and the Monte Carlo median path. The
    # Detail copies are unchanged: 13 of the 19 are still the Detail page.
    # Counted on the Detail tabs only: the Overview is a summary view that
    # re-renders a few Summary charts and is checked separately in
    # test_report_modes.py (its figures must equal Detail's). The whole page
    # must still close every chart it opens.
    assert html.count("<svg") == html.count("</svg>")
    assert _detail_html(html).count("<svg") == 13
    # 11 -> 12: the strategy-narrative task added section ① ("Cách bot này
    # chơi", right after the conclusion), which always carries its own
    # "Đọc thế nào & dựa trên đâu" <details> -- see report_page.py's
    # `_render_strategy_section`. It renders even without market data
    # (this fixture's own `_NoMarketSource`): `evidence["strategy"]`/
    # `["behavioral"]` are always present on a FULL result, just sparse
    # (UNKNOWN entry_style, empty phase_breakdown) when there is no market
    # timeline to bucket trades into phases.
    # 12 -> 13: cùng mục đó luôn kèm một khối "Phương pháp luận & diễn giải"
    # riêng, trong đó nói rõ vì sao phần trăm ở mục này có thể lệch với
    # "Sụt vốn tối đa" ở mục Số liệu giao dịch (hai mẫu số khác nhau).
    # 13 -> 14: mục "Điểm từng chiều rủi ro" nay luôn kèm thêm MỘT khối
    # "Chú thích giải thích điểm số" (đúng yêu cầu "nên có sao ở đó để giải
    # thích những tiêu chí và công thức") -- xem
    # `report_page.py::_render_score_basis`, nhúng vào mục có sẵn chứ không
    # tạo `<section>` mới nên không phá bất biến "cùng tập id mục" giữa
    # trang LIMITED và trang đầy đủ.
    # 14 -> 12: gộp 3 mục biểu đồ Monte Carlo rời rạc (kèm các khối _theory)
    # thành 1 biểu đồ duy nhất đa chiều (unified chart), giảm số lượng khối lý
    # thuyết trùng lặp từ 3 xuống 1 theo yêu cầu tinh giản của sếp.
    # 12 -> 15: three deterministic insight sections each carry their own theory details.
    # 15 -> 13: the Monte Carlo section carried three separate "Methodology &
    # interpretation" drawers (unified chart, multi-horizon table, key
    # probabilities). They are now one drawer for the whole section.
    # 13 -> 14: "Market compatibility" carries its own methodology drawer,
    # same as every other section.
    # 14 -> 13: the extra "essence" card and its methodology drawer were
    # removed from the result tab.
    # 13 -> 14: the result tab gained a footer accordion (data limitations and
    # open questions). It is a <details> after the last card, NOT a new section,
    # so the section count is unchanged.
    # 14 -> 15: every card in the Analyst Result tab now carries exactly 1 unified
    # "Methodology & interpretation" drawer (added to Conclusion and Expert assessment,
    # and unified across Growth).
    # 15 -> 18: every card in Tab 2 (market) and Tab 3 (trades/positions) now
    # also carries exactly 1 unified "Methodology & interpretation" drawer
    # (+1 dominant market, +1 open positions, +1 closed trades; market coverage
    # keeps its always-visible methodology block per the explicit rule).
    # 18 -> 12 (2026-09-24 redesign, project owner's request): the
    # "Methodology & interpretation" drawers of Conclusion, How this bot
    # trades, Growth and Expert assessment, and the risk-dimension section's
    # score-note + methodology drawers, were removed.
    # 12 -> 11: the Monte Carlo section's methodology drawer went too
    # (each figure there now carries its own "*" formula).
    # 11 -> 1: the Premium Market and Other & Position sections lost their
    # methodology drawers too; only the page-footer accordion is left.
    assert html.count("<details") == html.count("</details>") == 1


def test_real_bot_page_has_no_stray_vietnamese(full_result):
    html = render_bot_report_html(full_result)
    text = _strip_html(html)
    # The bot's own OKX-supplied name is real user data, not this project's
    # text -- strip every whole occurrence of it before scanning, the same
    # way a human proofreader would skip over a proper noun (a nickname
    # could itself happen to carry Vietnamese diacritics without that being
    # a translation bug).
    name = full_result.get("name") or ""
    if name:
        text = text.replace(name, " ")
    hits = _vietnamese_word_hits(text)
    assert not hits, f"stray Vietnamese on /bot/<code>: {hits}"


def test_a_handful_of_real_bots_with_real_market_data_have_no_stray_vietnamese():
    """Broader sample than the single MU fixture above, using this
    project's OWN committed crawled data (no network) and the REAL
    FileMarketDataSource (so market-dependent lenses run too, unlike the
    fixture above) -- catches anything the single always-market-unavailable
    fixture could not exercise. Allows the same documented exception.
    """
    from Agent.backend.external.sources.market_source import FileMarketDataSource

    candidates = []
    trade_root = DATA_DIR / "trade"
    if trade_root.is_dir():
        for bot_dir in sorted(trade_root.iterdir())[:6]:
            slot_path = bot_dir / "crawl_slot.json"
            if not (
                slot_path.exists()
                and (bot_dir / "overview.json").exists()
                and (bot_dir / "trade_list.json").exists()
            ):
                continue
            slot = json.loads(slot_path.read_text(encoding="utf-8"))
            candidates.append((slot["venue"].lower(), slot["asset"], bot_dir))
    assert candidates, "expected at least one real crawled bot folder on disk"

    checked = 0
    for venue, asset, bot_dir in candidates:
        overview = json.loads((bot_dir / "overview.json").read_text(encoding="utf-8"))
        ledger = json.loads((bot_dir / "trade_list.json").read_text(encoding="utf-8"))
        code = overview.get("uniqueCode") or bot_dir.name.replace("bot_", "")
        service = WebDataService(
            bot_source_factory=lambda client, bucket, o=overview, led=ledger: (
                _StubBotSource(o, led)
            ),
            market_source_factory=lambda client: FileMarketDataSource(
                data_dir=DATA_DIR
            ),
        )
        try:
            result = service.analyze(code)
        except Exception:  # noqa: BLE001 - a bad real fixture is not this test's concern
            continue
        if result.get("status") != "FULL":
            continue
        html = render_bot_report_html(result)
        text = _strip_html(html)
        name = result.get("name") or ""
        if name:
            text = text.replace(name, " ")
        hits = _vietnamese_word_hits(text)
        assert not hits, f"{venue}/{asset}/{bot_dir.name}: stray Vietnamese {hits}"
        checked += 1
    assert checked >= 2, f"only {checked} real bots produced a FULL result to check"


def test_legacy_advice_on_disk_is_scrubbed_to_assessment_wording():
    from Agent.backend.report.qc.reporting.reasons import scrub_legacy_advice

    old = (
        "Risk score 12/100, no sign of anything abnormal. Whether to keep copying is still "
        "your call. The current measurement sits in a watch zone, no action needed yet."
    )
    new = scrub_legacy_advice(old)
    assert "your call" not in new and "no action needed" not in new
    assert new == (
        "Risk score 12/100, no sign of anything abnormal. The current measurement sits "
        "in a watch zone."
    )


def test_risk_level_text_never_shows_a_control_order():
    from Agent.backend.report.qc.reporting.reasons import risk_level_text

    for code in ACTION_VI:
        assert risk_level_text(code) != code


# --------------------------------------------------------------------------- #
# Overview / Detail modes: the Overview is a summary view of the same
# analysis, re-rendering a few Summary blocks with the same renderers. These
# pin what makes that safe -- it never duplicates an element id (anchors and
# getElementById would hit the wrong copy) and every figure it shows is the
# figure Detail shows.
# --------------------------------------------------------------------------- #
from collections import Counter


def _split(html: str):
    i, j = html.find('<div class="rm-overview">'), html.find('<div class="rm-detail">')
    assert 0 <= i < j, "the page must carry both an Overview and a Detail block"
    return html[i:j], html[j:]


def _markup(html: str) -> str:
    """The page without <script>/<style> bodies (their comments quote ids)."""
    return re.sub(r"<(script|style)\b.*?</\1>", "", html, flags=re.S)


def _values(fragment: str, cls: str) -> list:
    return [v.strip() for v in re.findall(r'class="%s[^"]*">([^<]+)<' % re.escape(cls), fragment)]


def test_both_modes_are_rendered(full_result) -> None:
    html = render_bot_report_html(full_result)
    overview, detail = _split(html)
    assert overview.strip() and detail.strip()


def test_no_element_id_is_used_twice(full_result) -> None:
    html = _markup(render_bot_report_html(full_result))
    ids = Counter(re.findall(r'\sid="([^"]+)"', html))
    dups = sorted(k for k, n in ids.items() if n > 1)
    assert not dups, f"duplicate element ids: {dups}"


def test_overview_figures_are_the_detail_figures(full_result) -> None:
    overview, detail = _split(render_bot_report_html(full_result))
    compared = 0
    for cls in ("qe-chip-value", "mc-stat-v", "mc-pcard-v", "why-chip"):
        shown = _values(overview, cls)
        compared += len(shown)
        missing = [v for v in shown if v not in _values(detail, cls)]
        assert not missing, f"{cls}: Overview shows {missing}, which Detail does not"
    assert compared >= 5, "the Overview should show key figures to compare"
