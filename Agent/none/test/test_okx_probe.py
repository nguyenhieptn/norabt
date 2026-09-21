"""Diagnostic probes must answer honestly, and never touch the network in tests.

Every HTTP round trip is faked by patching `urllib.request.urlopen` at the
module the probe imported it into -- the same technique test_okx_client.py
uses -- so a real socket is never opened here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError

import pytest

import Agent.backend.okx.probe as probe
from Agent.backend.infra.config import config
from Agent.backend.okx.probe import (
    OKX_ERROR_MESSAGES_VI,
    LiveTradingRefused,
    check_private_access,
    check_public_access,
    explain_error_vi,
    probe_copy_trading,
)


# ---------------------------------------------------------------------------
# shared fixtures / fakes
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_real_delays(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every probe function paces itself with time.sleep(); tests don't wait."""
    monkeypatch.setattr(probe.time, "sleep", lambda _seconds: None)


@pytest.fixture()
def sample_universe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """A minimal bot_selection.json with one lead trader, isolated from the
    real (and constantly changing) crawled universe file."""
    universe_dir = tmp_path / "universe"
    universe_dir.mkdir()
    payload = {
        "assets": [
            {
                "underlying": "BTC",
                "top": {"code": "SAMPLECODE123456", "name": "Test Trader"},
            }
        ]
    }
    (universe_dir / "bot_selection.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    monkeypatch.setattr(config, "DATA_DIR", str(tmp_path))
    return "SAMPLECODE123456"


@pytest.fixture()
def blank_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "OKX_API_KEY", "")
    monkeypatch.setattr(config, "OKX_API_SECRET", "")
    monkeypatch.setattr(config, "OKX_API_PASSPHRASE", "")


@pytest.fixture()
def demo_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "OKX_API_KEY", "demo-key-0001")
    monkeypatch.setattr(config, "OKX_API_SECRET", "demo-secret-value")
    monkeypatch.setattr(config, "OKX_API_PASSPHRASE", "demo-passphrase")
    monkeypatch.setattr(config, "OKX_SIMULATED", True)


@pytest.fixture()
def live_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "OKX_API_KEY", "live-key-0001")
    monkeypatch.setattr(config, "OKX_API_SECRET", "live-secret-value")
    monkeypatch.setattr(config, "OKX_API_PASSPHRASE", "live-passphrase")
    monkeypatch.setattr(config, "OKX_SIMULATED", False)


class _FakeResponse:
    def __init__(self, payload: Dict[str, Any], status: int = 200):
        self._raw = json.dumps(payload).encode("utf-8")
        self.status = status

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc_info) -> None:
        return None

    def read(self) -> bytes:
        return self._raw


def _install_sequenced_urlopen(
    monkeypatch: pytest.MonkeyPatch,
    responses: List[Any],
    calls: Optional[List[Dict[str, Any]]] = None,
):
    """Each call to urlopen consumes the next entry of `responses`.

    An entry is either a dict (200 OK JSON body), an Exception instance to
    raise, or an (payload, status) tuple to raise as HTTPError with a JSON
    body -- mirrors how OKX actually answers auth failures (HTTP 401 + a real
    {code, msg} body), which is exactly the shape probe.py has to parse
    correctly.
    """
    state = {"index": 0}

    def fake_urlopen(request, timeout=None):
        if calls is not None:
            calls.append(
                {
                    "method": request.get_method(),
                    "url": request.full_url,
                    "headers": dict(request.header_items()),
                    "body": request.data,
                }
            )
        index = state["index"]
        state["index"] += 1
        if index >= len(responses):
            raise AssertionError(
                f"urlopen called more times than expected (call #{index + 1})"
            )
        entry = responses[index]
        if isinstance(entry, Exception):
            raise entry
        if isinstance(entry, tuple):
            payload, status = entry
            raw = json.dumps(payload).encode("utf-8")
            raise HTTPError(
                request.full_url, status, "error", {}, __import__("io").BytesIO(raw)
            )
        return _FakeResponse(entry)

    monkeypatch.setattr(probe.urllib.request, "urlopen", fake_urlopen)


# ---------------------------------------------------------------------------
# check_public_access
# ---------------------------------------------------------------------------


def test_public_access_survives_endpoint_errors_without_crashing(
    monkeypatch: pytest.MonkeyPatch, sample_universe: str
):
    calls: List[Dict[str, Any]] = []
    _install_sequenced_urlopen(
        monkeypatch,
        [
            URLError("connection refused"),
            URLError("connection refused"),
            URLError("connection refused"),
        ],
        calls,
    )

    result = check_public_access()

    assert result["status"] == "LOI"
    assert len(result["checks"]) == 3
    for check in result["checks"]:
        assert check["ok"] is False
        assert "Call failed" in check["detail"]
    assert result["clock_skew_ms"] is None
    assert len(calls) == 3


def test_public_access_computes_clock_skew(
    monkeypatch: pytest.MonkeyPatch, sample_universe: str
):
    # Server says 5 seconds (5000 ms) ahead of the fixed local clock below.
    server_ts_ms = 1_700_000_005_000
    _install_sequenced_urlopen(
        monkeypatch,
        [
            {"code": "0", "data": [{"ts": str(server_ts_ms)}], "msg": ""},
            {"code": "0", "data": [{"minCopyAmt": "10"}], "msg": ""},
            {"code": "0", "data": [], "msg": ""},
        ],
    )
    # time.time() is read twice (before/after the first call); both fixed to
    # the same instant so the round-trip midpoint is exact and deterministic.
    local_ts_s = 1_700_000_000.0
    monkeypatch.setattr(probe.time, "time", lambda: local_ts_s)

    result = check_public_access()

    assert result["status"] == "OK"
    assert result["clock_skew_ms"] == pytest.approx(5000.0, abs=0.5)
    assert result["clock_skew_ok"] is True


def test_public_access_flags_clock_skew_beyond_okx_limit(
    monkeypatch: pytest.MonkeyPatch, sample_universe: str
):
    server_ts_ms = 1_700_000_000_000 + 45_000  # 45s ahead, past OKX's 30s cutoff
    _install_sequenced_urlopen(
        monkeypatch,
        [
            {"code": "0", "data": [{"ts": str(server_ts_ms)}], "msg": ""},
            {"code": "0", "data": [{"minCopyAmt": "10"}], "msg": ""},
            {"code": "0", "data": [], "msg": ""},
        ],
    )
    monkeypatch.setattr(probe.time, "time", lambda: 1_700_000_000.0)

    result = check_public_access()

    assert result["clock_skew_ok"] is False


# ---------------------------------------------------------------------------
# check_private_access
# ---------------------------------------------------------------------------


def test_private_access_missing_credentials_reports_status_without_raising(
    blank_credentials,
):
    result = check_private_access()

    assert result["status"] == "CHUA_CAU_HINH"
    assert set(result["missing_fields"]) == {
        "OKX_API_KEY",
        "OKX_API_SECRET",
        "OKX_API_PASSPHRASE",
    }
    assert "OKX_API_KEY" in result["message_vi"]


def test_private_access_reports_demo_environment_on_success(
    monkeypatch: pytest.MonkeyPatch, demo_credentials
):
    _install_sequenced_urlopen(
        monkeypatch, [{"code": "0", "data": [{"ccy": "USDT"}], "msg": ""}]
    )

    result = check_private_access()

    assert result["status"] == "OK"
    assert result["environment"] == "DEMO"


def test_private_access_extracts_code_from_http_error_body(
    monkeypatch: pytest.MonkeyPatch, demo_credentials
):
    # Reproduces what OKX actually returns for a bad key: HTTP 401 whose body
    # still carries the real {code, msg} -- must not become a generic failure.
    _install_sequenced_urlopen(
        monkeypatch, [({"code": "50111", "msg": "Invalid OK-ACCESS-KEY"}, 401)]
    )

    result = check_private_access()

    assert result["status"] == "LOI"
    assert result["error_code"] == "50111"
    assert "OKX_API_KEY" in result["message_vi"]


def test_private_access_reports_live_environment(
    monkeypatch: pytest.MonkeyPatch, live_credentials
):
    _install_sequenced_urlopen(monkeypatch, [{"code": "0", "data": [], "msg": ""}])

    result = check_private_access()

    assert result["environment"] == "LIVE"


# ---------------------------------------------------------------------------
# OKX error code translation table
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code,expected_keyword",
    [
        ("50102", "30 seconds"),
        ("50103", "OK-ACCESS-KEY"),
        ("50104", "OK-ACCESS-PASSPHRASE"),
        ("50111", "OKX_API_KEY"),
        ("50113", "OKX_API_SECRET"),
        ("50038", "demo"),
    ],
)
def test_explain_error_vi_translates_known_codes(code: str, expected_keyword: str):
    message = explain_error_vi(code)
    assert expected_keyword.lower() in message.lower()
    assert code in OKX_ERROR_MESSAGES_VI


def test_explain_error_vi_never_invents_meaning_for_unknown_code():
    message = explain_error_vi("99999")
    assert "99999" in message
    assert "not in the probe's internal lookup table" in message


def test_explain_error_vi_handles_missing_code():
    message = explain_error_vi(None)
    assert "No specific error code" in message


# ---------------------------------------------------------------------------
# probe_copy_trading: dry-run makes zero network calls
# ---------------------------------------------------------------------------


def test_dry_run_makes_no_http_calls_with_credentials(
    monkeypatch: pytest.MonkeyPatch, demo_credentials, sample_universe
):
    calls: List[Dict[str, Any]] = []
    _install_sequenced_urlopen(monkeypatch, [], calls)

    result = probe_copy_trading(dry_run=True)

    assert len(calls) == 0
    assert result["status"] == "DRY_RUN"
    assert result["would_call"]["endpoint"] == "/api/v5/copytrading/first-copy-settings"
    assert result["would_call"]["body"]["uniqueCode"] == "SAMPLECODE123456"


def test_dry_run_makes_no_http_calls_without_credentials(
    monkeypatch: pytest.MonkeyPatch, blank_credentials, sample_universe
):
    calls: List[Dict[str, Any]] = []
    _install_sequenced_urlopen(monkeypatch, [], calls)

    result = probe_copy_trading(dry_run=True)

    assert len(calls) == 0
    assert result["status"] == "DRY_RUN"


def test_dry_run_never_leaks_secret_or_passphrase(
    monkeypatch: pytest.MonkeyPatch, demo_credentials, sample_universe
):
    _install_sequenced_urlopen(monkeypatch, [])

    result = probe_copy_trading(dry_run=True)
    rendered = json.dumps(result, ensure_ascii=False)

    assert "demo-secret-value" not in rendered
    assert "demo-passphrase" not in rendered
    # The signature is derived from the secret and must be masked too, not
    # just the raw credential fields.
    assert result["would_call"]["headers"]["OK-ACCESS-SIGN"] == "***"
    assert result["would_call"]["headers"]["OK-ACCESS-PASSPHRASE"] == "***"


# ---------------------------------------------------------------------------
# probe_copy_trading: live-key safety refusal
# ---------------------------------------------------------------------------


def test_execute_refuses_live_credentials_before_any_call(
    monkeypatch: pytest.MonkeyPatch, live_credentials, sample_universe
):
    calls: List[Dict[str, Any]] = []
    _install_sequenced_urlopen(monkeypatch, [], calls)

    with pytest.raises(LiveTradingRefused):
        probe_copy_trading(dry_run=False)

    assert len(calls) == 0


def test_execute_dry_run_true_is_fine_even_with_live_credentials(
    monkeypatch: pytest.MonkeyPatch, live_credentials, sample_universe
):
    # dry_run=True never touches the network regardless of which key is
    # configured -- only dry_run=False is a safety-relevant action.
    calls: List[Dict[str, Any]] = []
    _install_sequenced_urlopen(monkeypatch, [], calls)

    result = probe_copy_trading(dry_run=True)

    assert result["status"] == "DRY_RUN"
    assert len(calls) == 0


# ---------------------------------------------------------------------------
# probe_copy_trading: dry_run=False outcome interpretation
# ---------------------------------------------------------------------------


def test_execute_missing_credentials_reports_status_without_raising(
    monkeypatch: pytest.MonkeyPatch, blank_credentials, sample_universe
):
    calls: List[Dict[str, Any]] = []
    _install_sequenced_urlopen(monkeypatch, [], calls)

    result = probe_copy_trading(dry_run=False)

    assert result["status"] == "CHUA_CAU_HINH"
    assert len(calls) == 0


def test_execute_code_50038_means_demo_does_not_support_copy_trading(
    monkeypatch: pytest.MonkeyPatch, demo_credentials, sample_universe
):
    _install_sequenced_urlopen(
        monkeypatch,
        [
            {"code": "0", "data": [{"minCopyAmt": "10"}], "msg": ""},
            {
                "code": "50038",
                "data": [],
                "msg": "This feature is unavailable in demo trading",
            },
        ],
    )

    result = probe_copy_trading(dry_run=False)

    assert result["status"] == "DEMO_KHONG_HO_TRO"
    assert result["code"] == "50038"
    assert "does not support" in result["message_vi"].lower()


def test_execute_code_zero_means_demo_supports_copy_trading_and_warns_to_clean_up(
    monkeypatch: pytest.MonkeyPatch, demo_credentials, sample_universe
):
    _install_sequenced_urlopen(
        monkeypatch,
        [
            {"code": "0", "data": [{"minCopyAmt": "10"}], "msg": ""},
            {"code": "0", "data": [{"result": True}], "msg": ""},
        ],
    )

    result = probe_copy_trading(dry_run=False)

    assert result["status"] == "DEMO_CO_HO_TRO"
    assert "does support" in result["message_vi"].lower()
    assert "canh_bao" in result
    assert "stop-copy-trading" in result["canh_bao"]
    assert "SAMPLECODE123456" in result["canh_bao"]


def test_execute_unrecognized_code_is_reported_verbatim_not_guessed(
    monkeypatch: pytest.MonkeyPatch, demo_credentials, sample_universe
):
    _install_sequenced_urlopen(
        monkeypatch,
        [
            {"code": "0", "data": [{"minCopyAmt": "10"}], "msg": ""},
            {"code": "51000", "data": [], "msg": "Some other business error"},
        ],
    )

    result = probe_copy_trading(dry_run=False)

    assert result["status"] == "MA_LOI_KHAC"
    assert result["code"] == "51000"
    assert result["raw_msg"] == "Some other business error"
