"""Light/dark/mobile rendering invariants for the server-rendered report.

A browser screenshot is the only way to confirm a page *looks* right, and this
repository does not run one. But the failures that a light/dark/mobile check
actually catches are structural, and those are assertable from the emitted
document:

* a token used in one palette but never defined in the other -> invisible text
  in that theme;
* a fixed pixel width wider than a phone viewport -> horizontal scrolling;
* an SVG sized in absolute pixels instead of a viewBox -> a chart that cannot
  shrink;
* a missing viewport meta -> the whole page rendered at desktop width.

These tests cover exactly those. They do not claim to replace a visual review.

The fixture is built locally rather than imported from another test module.
Importing a fixture across test files makes one module's setup run inside
another's session, and that coupling made unrelated report tests fail
depending on collection order.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Set

import pytest

from Agent.backend.infra.config import config
from Agent.backend.sources.bot_source import BotDataSource
from Agent.backend.sources.market_source import MarketDataSource
from Agent.backend.market.service import MarketDataUnavailableError
from Agent.backend.web.data import WebDataService
from Agent.backend.web.report_page import render_bot_report_html

DATA_DIR = Path(config.DATA_DIR)
_FIXTURE_BOT_DIR = DATA_DIR / "cex" / "MU" / "bot" / "bot_BB3398A957270A39"
VALID_CODE = "BB3398A957270A39"

# Phone viewport this product targets; anything wider must be able to shrink.
PHONE_WIDTH_PX = 360

# Tokens the design system defines outside the report document (fonts, spacing
# scale) are resolved from the shared stylesheet, not from this page.
_EXTERNAL_TOKEN_PREFIXES = ("--font", "--space", "--radius", "--shadow", "--ease")


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
def html() -> str:
    overview = json.loads((_FIXTURE_BOT_DIR / "overview.json").read_text(encoding="utf-8"))
    ledger = json.loads((_FIXTURE_BOT_DIR / "trade_list.json").read_text(encoding="utf-8"))
    service = WebDataService(
        bot_source_factory=lambda client, bucket: _StubBotSource(overview, ledger),
        market_source_factory=lambda client: _NoMarketSource(),
    )
    result = service.analyze(VALID_CODE)
    assert result["status"] == "FULL"
    return render_bot_report_html(result)


def _defined_tokens(document: str) -> Set[str]:
    return set(re.findall(r"(--[a-zA-Z0-9-]+)\s*:", document))


def _used_tokens(document: str) -> Set[str]:
    """Tokens used WITHOUT a fallback.

    `var(--x, #fff)` is safe even when `--x` is undefined, so only the bare
    form can leave a property with no value at all.
    """
    return set(re.findall(r"var\(\s*(--[a-zA-Z0-9-]+)\s*\)", document))


def test_viewport_is_declared_for_mobile(html: str) -> None:
    assert 'name="viewport"' in html
    assert "width=device-width" in html


def test_both_palettes_are_defined(html: str) -> None:
    assert "@media (prefers-color-scheme: dark)" in html
    assert ':root[data-theme="dark"]' in html
    assert ':root[data-theme="light"]' in html


def test_every_token_the_page_uses_is_defined_somewhere(html: str) -> None:
    """An undefined token silently resolves to nothing, which in practice means
    unreadable text in whichever theme forgot to define it."""
    used = _used_tokens(html)
    defined = _defined_tokens(html)
    missing = {
        token
        for token in used - defined
        if not token.startswith(_EXTERNAL_TOKEN_PREFIXES)
    }
    assert not missing, f"tokens used but never defined: {sorted(missing)}"


def test_dark_overrides_do_not_introduce_undefined_tokens(html: str) -> None:
    """Whatever the dark block redefines must also have a light value.

    The light palette is an unconditional `:root` block, which in this document
    appears *after* the dark media query, so "light" means "everything not
    inside a dark-scoped block" rather than "everything before the dark one".
    """
    dark_scoped = re.findall(
        r"@media \(prefers-color-scheme: dark\)\s*\{.*?\n\}\n\}", html, flags=re.S
    ) + re.findall(r":root\[data-theme=\"dark\"\]\s*\{.*?\n\}", html, flags=re.S)
    assert dark_scoped, "expected at least one dark-mode block"

    dark_only: Set[str] = set()
    for block in dark_scoped:
        dark_only |= _defined_tokens(block)

    light_source = html
    for block in dark_scoped:
        light_source = light_source.replace(block, "")
    light_tokens = _defined_tokens(light_source)

    missing = {token for token in dark_only if token not in light_tokens}
    assert not missing, (
        f"defined only for dark mode; light mode has no value: {sorted(missing)}"
    )


def test_charts_scale_instead_of_using_a_fixed_pixel_width(html: str) -> None:
    svgs = re.findall(r"<svg\b[^>]*>", html)
    assert svgs, "expected at least one chart"
    for tag in svgs:
        assert "viewBox=" in tag, f"chart cannot scale without a viewBox: {tag[:120]}"
        fixed = re.search(r'\bwidth="(\d+)(?:px)?"', tag)
        if fixed and int(fixed.group(1)) > PHONE_WIDTH_PX:
            assert "max-width" in tag or "100%" in tag, (
                f"chart is pinned wider than a phone viewport: {tag[:120]}"
            )


def test_no_block_is_pinned_wider_than_a_phone_without_an_escape(html: str) -> None:
    """A hard `width: NNNpx` wider than a phone forces horizontal scrolling
    unless the same rule also caps itself with a max-width."""
    offenders = []
    for rule in re.findall(r"\{[^{}]*\}", html):
        match = re.search(r"(?<!max-)(?<!min-)width:\s*(\d{3,})px", rule)
        if not match or int(match.group(1)) <= PHONE_WIDTH_PX:
            continue
        if "max-width" in rule or "100%" in rule:
            continue
        offenders.append(rule.strip()[:120])
    assert not offenders, f"fixed widths wider than a phone: {offenders[:5]}"


def test_theme_toggle_covers_both_directions(html: str) -> None:
    """The page must be able to reach light *and* dark explicitly, not just
    follow the OS: a reader who overrides the system theme has to get a
    complete palette either way."""
    assert 'data-theme="light"' in html or "data-theme='light'" in html
    assert 'data-theme="dark"' in html or "data-theme='dark'" in html


def test_document_declares_a_colour_scheme(html: str) -> None:
    """Without this the browser paints native form controls and scrollbars for
    the wrong theme even when the page itself is correct."""
    assert "color-scheme" in html
