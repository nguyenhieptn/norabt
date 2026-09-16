from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from Agent.backend.market.service import MarketService
from Agent.backend.mcp.service import BotObservationService

FIXED_AS_OF_MS = 1789230000000
SIM_ITERATIONS = 1_000
SIM_HORIZON = 500

# --------------------------------------------------------------------------- #
# Lỗi 1 fix: isolate every NORABT_* environment variable from the whole test
# suite.
#
# WHY THIS EXISTS: Agent/backend/infra/envfile.py loads Agent/.env straight
# into the REAL process environment (os.environ), and several modules under
# test read those same variables live at call time (e.g.
# Agent/backend/web/data.py's report_base_url(), which reads
# NORABT_WEB_REPORT_BASE_URL on every call, by design, so an operator's env
# change takes effect without a restart). That is exactly right for
# production, but it means a test asserting a DEFAULT value (e.g.
# build_report_url's fallback to http://127.0.0.1:8770) silently depends on
# whether the machine running pytest happens to have that variable set in
# its own Agent/.env -- a config file every operator is expected to have,
# and which this project's own docs tell them to fill in. The exact same
# commit would then be green on one machine and red on another, with the
# ONLY difference being local `.env` contents nobody wrote into the test
# itself. A test whose pass/fail depends on what a developer configured
# locally is not testing anything reproducible: it must be isolated from
# that machine-local configuration, the same way this suite already avoids
# depending on the real network or real OKX credentials.
#
# HOW: delete every already-set NORABT_* key from os.environ before each
# test runs, via `monkeypatch.delenv` (not a manual try/finally) so this
# composes correctly with any test that ALSO calls
# `monkeypatch.setenv`/`monkeypatch.delenv` on the same key inside its own
# body -- see e.g. Agent/test/test_web_app.py's own
# `monkeypatch.setenv(REPORT_BASE_URL_ENV, ...)` tests. monkeypatch's own
# undo stack restores each variable to whatever it was at the moment ITS
# OWN setenv/delenv call ran (here: "absent", since this fixture already
# removed it before the test body starts), regardless of fixture teardown
# ordering, so a test's own explicit env manipulation always wins for the
# duration of that test and is still cleanly undone afterwards.
#
# Deliberately scoped to the "NORABT_" prefix only -- OKX_* variables
# (OKX_API_KEY, OKX_API_SECRET, OKX_SIMULATED, ...) are read by tests that
# genuinely need them and are NOT the source of this bug, so they are left
# completely untouched.
# --------------------------------------------------------------------------- #

_ISOLATED_ENV_PREFIX = "NORABT_"


@pytest.fixture(autouse=True)
def _isolate_norabt_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [k for k in os.environ if k.startswith(_ISOLATED_ENV_PREFIX)]:
        monkeypatch.delenv(key, raising=False)


def _bot(asset: str, folder: str, venue: str = "CEX"):
    return BotObservationService().get_bot_result(
        asset,
        folder,
        venue_type=venue,
        seed=42,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=SIM_ITERATIONS,
        simulation_horizon=SIM_HORIZON,
    )


@pytest.fixture(scope="session")
def market_btc():
    return MarketService().get_market_result(
        "BTC", venue_type="CEX", as_of_ms=FIXED_AS_OF_MS
    )


@pytest.fixture(scope="session")
def market_mu():
    return MarketService().get_market_result(
        "MU", venue_type="CEX", as_of_ms=FIXED_AS_OF_MS
    )


@pytest.fixture(scope="session")
def market_eth():
    return MarketService().get_market_result(
        "ETH", venue_type="CEX", as_of_ms=FIXED_AS_OF_MS
    )


@pytest.fixture(scope="session")
def market_hype():
    return MarketService().get_market_result(
        "HYPE", venue_type="CEX", as_of_ms=FIXED_AS_OF_MS
    )


@pytest.fixture(scope="session")
def bot_top():
    """Modern-dAPI-Manatee: complete ledger, reconciled, flat."""
    return _bot("MU", "bot_BB3398A957270A39")


@pytest.fixture(scope="session")
def bot_poor():
    """Positions whose instrument OKX withholds."""
    return _bot("HYPE", "bot_793739635259546051")


@pytest.fixture(scope="session")
def bot_oversized():
    """Large leveraged book with a weekly equity curve that once hit zero."""
    return _bot("ETH", "bot_F6476365DB0D09A3")


@pytest.fixture(scope="session")
def bot_deferred():
    """HaveARestin: closes winners, holds a large losing book.

    The folder tracks the bot's dominant market by notional, which moved to ETH
    after the 13/09 crawl -- the bot spreads across XRP/ETH/NEAR/ADA/DOGE.
    """
    return _bot("ETH", "bot_53AEED5A8E4EBBB2")


@pytest.fixture(scope="session")
def bot_empty():
    """CryptoPanda: one open position, no closed trades."""
    return _bot("BTC", "bot_E5513524191E576E")


def write_bot_dataset(
    root: Path,
    *,
    venue: str = "cex",
    asset: str = "TEST",
    folder: str = "bot_TEST",
    overview: Optional[Dict[str, Any]] = None,
    closed_trades: Optional[List[Dict[str, Any]]] = None,
    open_positions: Optional[List[Dict[str, Any]]] = None,
    extra_ledger: Optional[Dict[str, Any]] = None,
) -> Path:
    """Build a minimal on-disk bot snapshot so defect cases stay synthetic."""
    directory = root / venue / asset / "bot" / folder
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "overview.json").write_text(
        json.dumps(overview or {"uniqueCode": "TESTCODE", "nickName": "Test Bot"}),
        encoding="utf-8",
    )
    ledger: Dict[str, Any] = {
        "uniqueCode": (overview or {}).get("uniqueCode", "TESTCODE"),
        "open_positions_count": len(open_positions or []),
        "open_positions": open_positions or [],
        "closed_trades": closed_trades or [],
    }
    ledger.update(extra_ledger or {})
    (directory / "trade_list.json").write_text(json.dumps(ledger), encoding="utf-8")
    return directory


def write_market_dataset(
    root: Path,
    *,
    venue: str = "cex",
    asset: str = "TEST",
    last_candle_ms: int = 1_789_000_000_000,
    candle_count: int = 60,
    orderbook_ms: Optional[int] = None,
    extra_files: Optional[Dict[str, Any]] = None,
) -> Path:
    """Build a minimal on-disk market snapshot so freshness cases stay synthetic."""
    directory = root / venue / asset / "market"
    directory.mkdir(parents=True, exist_ok=True)
    candles = [
        {
            "timestamp": last_candle_ms - (candle_count - 1 - i) * 3_600_000,
            "open": 100.0 + i,
            "high": 101.0 + i,
            "low": 99.0 + i,
            "close": 100.5 + i,
            "vol": 10.0,
            "volCcy": 10.0,
            "volCcyQuote": 1000.0,
        }
        for i in range(candle_count)
    ]
    (directory / "ohlcv_1h_2023_present.json").write_text(
        json.dumps({"instId": f"{asset}-USDT-SWAP", "bar": "1H", "candles": candles}),
        encoding="utf-8",
    )
    if orderbook_ms is not None:
        (directory / "orderbook_l2.json").write_text(
            json.dumps(
                {
                    "symbol": f"{asset}-USDT-SWAP",
                    "timestamp": orderbook_ms,
                    "bids": [["100.0", "5.0", "3"]],
                    "asks": [["100.2", "5.0", "3"]],
                }
            ),
            encoding="utf-8",
        )
    for name, payload in (extra_files or {}).items():
        (directory / name).write_text(json.dumps(payload), encoding="utf-8")
    return directory
