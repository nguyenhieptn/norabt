"""GET /api/v2/dossier -- the one serialized dossier payload (design section 10),
plus the server-side role scoping of the rendered report (design section 9).

Everything this module needs is built locally. Importing helpers from another
test module makes that module's session-level setup run inside this one, and
that coupling made unrelated report tests fail depending on collection order.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from starlette.testclient import TestClient

from Agent.backend.infra.config import config
from Agent.backend.market.service import MarketDataUnavailableError
from Agent.backend.external.sources.bot_source import BotDataSource
from Agent.backend.external.sources.market_source import MarketDataSource
from Agent.backend.report.qc.reporting.view_policy import WITHHELD_MARKER
from Agent.backend.web.app import create_app
from Agent.backend.web.data import WebDataService

DATA_DIR = Path(config.DATA_DIR)
_FIXTURE_BOT_DIR = DATA_DIR / "trade" / "bot_BB3398A957270A39"

# A bot this repository has a committed, already-scored assessment.json for.
_REAL_SCORED_CODE = "811997770117827919"


class _StubBotSource(BotDataSource):
    def __init__(self) -> None:
        self._overview = json.loads(
            (_FIXTURE_BOT_DIR / "overview.json").read_text(encoding="utf-8")
        )
        self._ledger = json.loads(
            (_FIXTURE_BOT_DIR / "trade_list.json").read_text(encoding="utf-8")
        )

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


def _client() -> TestClient:
    service = WebDataService(
        bot_source_factory=lambda client, bucket: _StubBotSource(),
        market_source_factory=lambda client: _NoMarketSource(),
        data_dir=DATA_DIR,
    )
    return TestClient(create_app(data_service=service), base_url="http://testserver")


def test_dossier_endpoint_serves_a_scored_bot() -> None:
    resp = _client().get(f"/api/v2/dossier?code={_REAL_SCORED_CODE}")
    assert resp.status_code == 200
    payload: Dict[str, Any] = resp.json()
    assert payload["schema_version"] == "persisted_dossier_view.v1"
    assert payload["source_shape"] == "COMPACT_ASSESSMENT_RECORD"
    assert payload["subject"]["unique_code"] == _REAL_SCORED_CODE
    # A compact record must say what it cannot carry rather than imply it has it.
    assert payload["unavailable_fields"]
    assert payload["limitations"]


def test_dossier_endpoint_defaults_to_the_user_view() -> None:
    payload = _client().get(f"/api/v2/dossier?code={_REAL_SCORED_CODE}").json()
    assert payload["view_role"] == "USER"


def test_dossier_endpoint_rejects_an_invalid_code() -> None:
    resp = _client().get("/api/v2/dossier?code=not a code")
    assert resp.status_code == 400


def test_dossier_endpoint_404s_for_an_unscored_code() -> None:
    resp = _client().get("/api/v2/dossier?code=999999999999999999")
    assert resp.status_code == 404


def test_dossier_endpoint_never_triggers_a_live_analysis(monkeypatch) -> None:
    """The route is a read. If it could start the pipeline, an unauthenticated
    GET would become a way to run a ~70s job on demand."""
    import Agent.backend.pipeline as pipeline_module

    def explode(*args: Any, **kwargs: Any):
        raise AssertionError("the dossier endpoint must not run the pipeline")

    monkeypatch.setattr(pipeline_module.RiskSupervisionPipeline, "run", explode)
    resp = _client().get(f"/api/v2/dossier?code={_REAL_SCORED_CODE}")
    assert resp.status_code == 200


def test_user_view_marks_withheld_branches_instead_of_dropping_them() -> None:
    """A compact record has no `bot_result`, so nothing is withheld from it --
    but the contract fields that say so must still be present and honest."""
    payload = _client().get(f"/api/v2/dossier?code={_REAL_SCORED_CODE}").json()
    assert "withheld_paths" in payload
    assert isinstance(payload["withheld_paths"], list)
    for path in payload["withheld_paths"]:
        assert any(
            limitation == f"{WITHHELD_MARKER}: {path}"
            for limitation in payload["limitations"]
        )


# --------------------------------------------------------------------------- #
# Server-side role scoping of the rendered report (design section 9)
# --------------------------------------------------------------------------- #


def test_user_view_keeps_panel_ids_and_marks_them_withheld() -> None:
    """The panel ids are a compatibility contract, so a withheld panel keeps
    its shell and says it is withheld instead of vanishing."""
    body = _client().get(f"/bot/{_REAL_SCORED_CODE}?view=user").text
    assert 'id="panel-report"' in body
    assert 'id="panel-market"' in body
    assert 'id="panel-trades"' in body
    assert "DETAIL_WITHHELD_BY_ROLE" in body
    assert 'data-hidden-panels="panel-market panel-trades"' in body


def test_default_report_is_unchanged_without_the_view_parameter() -> None:
    body = _client().get(f"/bot/{_REAL_SCORED_CODE}").text
    assert "DETAIL_WITHHELD_BY_ROLE" not in body
    assert "data-hidden-panels" not in body


def test_user_view_does_not_change_the_score() -> None:
    """Role may narrow presentation, never the calculation."""
    import re

    scoped = _client().get(f"/bot/{_REAL_SCORED_CODE}?view=user").text
    full = _client().get(f"/bot/{_REAL_SCORED_CODE}").text
    pattern = re.compile(r'id="panel-report".*?</div>', re.S)
    scoped_scores = re.findall(r"(\d+)/100", pattern.search(scoped).group(0)[:4000])
    full_scores = re.findall(r"(\d+)/100", pattern.search(full).group(0)[:4000])
    assert scoped_scores == full_scores


def test_endpoint_can_return_a_named_report_product() -> None:
    resp = _client().get(f"/api/v2/dossier?code={_REAL_SCORED_CODE}&product=analyst")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["report_product"] == "analyst"
    assert set(payload["available_products"]) == {
        "analyst",
        "premium_market",
        "other_position",
    }


def test_endpoint_rejects_an_unknown_product() -> None:
    resp = _client().get(f"/api/v2/dossier?code={_REAL_SCORED_CODE}&product=nope")
    assert resp.status_code == 400
