from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from urllib.error import URLError

import pytest

import Agent.backend.external.oklink.client as client_module
from Agent.backend.market.features.onchain_activity import (
    OnchainActivityFeatureExtractor,
)
from Agent.backend.market.schemas.market_result import OnchainActivityState
from Agent.backend.external.oklink.client import (
    OkLinkApiError,
    OkLinkClient,
    OkLinkCredentialsMissing,
    OkLinkTransportError,
)
from Agent.backend.external.oklink.settings import OkLinkSettings, is_oklink_enabled


def _settings(api_key: str = "", enabled: bool = False) -> OkLinkSettings:
    return OkLinkSettings(
        enabled=enabled,
        api_key=api_key,
        base_url="https://www.oklink.com",
        chain_short_name="XLAYER",
        timeout_seconds=5.0,
        max_retries=1,
    )


class _FakeResponse:
    def __init__(self, payload: Dict[str, Any]):
        self._raw = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc_info) -> None:
        return None

    def read(self) -> bytes:
        return self._raw


def _install_fake_urlopen(
    monkeypatch: pytest.MonkeyPatch,
    payload: Dict[str, Any],
    calls: Optional[List[Dict[str, Any]]] = None,
    raise_transport_error: bool = False,
) -> None:
    def fake_urlopen(request, timeout=None):
        if calls is not None:
            calls.append(
                {
                    "method": request.get_method(),
                    "url": request.full_url,
                    "headers": dict(request.header_items()),
                }
            )
        if raise_transport_error:
            raise URLError("connection refused")
        return _FakeResponse(payload)

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(client_module.time, "sleep", lambda _seconds: None)


# ---------------------------------------------------------------------------
# is_oklink_enabled() -- fail-closed boolean parsing
# ---------------------------------------------------------------------------


def test_oklink_enabled_defaults_off(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OKLINK_ENABLED", raising=False)
    assert is_oklink_enabled() is False


def test_oklink_enabled_rejects_unrecognized_value_back_to_default(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("OKLINK_ENABLED", "definitely-not-a-boolean")
    assert is_oklink_enabled() is False


def test_oklink_enabled_true_recognized(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("OKLINK_ENABLED", "true")
    assert is_oklink_enabled() is True


# ---------------------------------------------------------------------------
# OkLinkClient -- fail-closed on missing credentials, never a silent guess
# ---------------------------------------------------------------------------


def test_missing_api_key_raises_before_any_network_call(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: List[Dict[str, Any]] = []
    _install_fake_urlopen(monkeypatch, {"code": "0", "data": []}, calls=calls)
    client = OkLinkClient(settings=_settings(api_key=""))

    with pytest.raises(OkLinkCredentialsMissing):
        client.get_address_summary("0xabc")

    assert calls == []


def test_get_address_summary_sends_confirmed_header_and_path(
    monkeypatch: pytest.MonkeyPatch,
):
    calls: List[Dict[str, Any]] = []
    _install_fake_urlopen(
        monkeypatch, {"code": "0", "msg": "", "data": [{"balance": "1.5"}]}, calls=calls
    )
    client = OkLinkClient(settings=_settings(api_key="test-key"))

    result = client.get_address_summary("0xabc123")

    assert result == [{"balance": "1.5"}]
    assert len(calls) == 1
    assert calls[0]["headers"].get("Ok-access-key") == "test-key"
    assert "/api/v5/explorer/address/address-summary" in calls[0]["url"]
    assert "chainShortName=XLAYER" in calls[0]["url"]
    assert "address=0xabc123" in calls[0]["url"]


def test_get_token_list_uses_confirmed_path(monkeypatch: pytest.MonkeyPatch):
    calls: List[Dict[str, Any]] = []
    _install_fake_urlopen(monkeypatch, {"code": "0", "data": []}, calls=calls)
    client = OkLinkClient(settings=_settings(api_key="test-key"))

    client.get_token_list()

    assert "/api/v5/explorer/token/token-list" in calls[0]["url"]


def test_api_error_code_raises_with_code_and_msg_preserved(
    monkeypatch: pytest.MonkeyPatch,
):
    _install_fake_urlopen(monkeypatch, {"code": "50111", "msg": "bad key"})
    client = OkLinkClient(settings=_settings(api_key="wrong-key"))

    with pytest.raises(OkLinkApiError) as excinfo:
        client.get_address_summary("0xabc")

    assert excinfo.value.code == "50111"
    assert excinfo.value.msg == "bad key"


def test_transport_error_retries_then_raises(monkeypatch: pytest.MonkeyPatch):
    _install_fake_urlopen(monkeypatch, {}, raise_transport_error=True)
    client = OkLinkClient(settings=_settings(api_key="test-key"))

    with pytest.raises(OkLinkTransportError):
        client.get_address_summary("0xabc")


def test_get_large_transfers_raises_not_implemented_instead_of_guessing():
    client = OkLinkClient(settings=_settings(api_key="test-key"))

    with pytest.raises(NotImplementedError):
        client.get_large_transfers()


# ---------------------------------------------------------------------------
# OnchainActivityFeatureExtractor -- disabled by default, never fabricates data
# ---------------------------------------------------------------------------


def test_extractor_disabled_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("OKLINK_ENABLED", raising=False)

    state = OnchainActivityFeatureExtractor.extract(token_address="0xabc")

    assert state == OnchainActivityState(data_state="DISABLED")


def test_extractor_disabled_without_token_address_even_if_enabled(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("OKLINK_ENABLED", "true")

    state = OnchainActivityFeatureExtractor.extract(token_address=None)

    assert state.data_state == "DISABLED"


def test_extractor_raises_not_implemented_when_enabled_with_address(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("OKLINK_ENABLED", "true")

    with pytest.raises(NotImplementedError):
        OnchainActivityFeatureExtractor.extract(token_address="0xabc")
