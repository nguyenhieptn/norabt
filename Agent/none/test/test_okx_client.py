from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import re
import socket
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError

import pytest

import Agent.backend.okx.client as client_module
from Agent.backend.infra.config import config
from Agent.backend.okx.client import (
    DEFAULT_USER_AGENT,
    OkxApiError,
    OkxClient,
    OkxCredentialsMissing,
    OkxTransportError,
)
from Agent.backend.okx.credentials import OkxCredentials

FIXED_TIMESTAMP = "2020-12-08T09:08:57.715Z"


def _complete_credentials(simulated: bool = True) -> OkxCredentials:
    return OkxCredentials(
        api_key="test-api-key-0001",
        api_secret="super-secret-value",
        passphrase="my-passphrase",
        simulated=simulated,
    )


class _FakeResponse:
    """Stands in for the context-manager object urlopen() returns."""

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
):
    """Patch urllib.request.urlopen at the module the client imported it into.

    Every real call is recorded (method/url/headers/body) so tests can assert
    on what was actually sent without a real socket ever opening.
    """
    import Agent.backend.okx.client as client_module

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
        if raise_transport_error:
            raise URLError("connection refused")
        return _FakeResponse(payload)

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    # Keep retry-with-backoff tests fast; backoff duration itself isn't under test.
    monkeypatch.setattr(client_module.time, "sleep", lambda _seconds: None)


# ---------------------------------------------------------------------------
# sign() -- deterministic vector, recomputed independently of the client code
# ---------------------------------------------------------------------------


def test_sign_matches_hand_computed_hmac_vector():
    creds = _complete_credentials()
    client = OkxClient(credentials=creds, base_url="https://www.okx.com")

    method = "GET"
    request_path = "/api/v5/account/balance?ccy=BTC"
    body = ""

    # Recompute the OKX v5 formula from scratch here (not by importing any
    # helper from client.py) so this test actually pins the algorithm rather
    # than mirroring whatever client.py happens to do.
    prehash = f"{FIXED_TIMESTAMP}{method}{request_path}{body}"
    expected_digest = hmac.new(
        creds.api_secret.encode("utf-8"), prehash.encode("utf-8"), hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(expected_digest).decode("utf-8")

    actual = client.sign(FIXED_TIMESTAMP, method, request_path, body)

    assert actual == expected_signature


def test_sign_changes_with_body_for_post():
    creds = _complete_credentials()
    client = OkxClient(credentials=creds)
    body = json.dumps({"instId": "BTC-USDT", "sz": "1"})

    prehash = f"{FIXED_TIMESTAMP}POST/api/v5/trade/order{body}"
    expected = base64.b64encode(
        hmac.new(
            creds.api_secret.encode("utf-8"), prehash.encode("utf-8"), hashlib.sha256
        ).digest()
    ).decode("utf-8")

    assert client.sign(FIXED_TIMESTAMP, "post", "/api/v5/trade/order", body) == expected


# ---------------------------------------------------------------------------
# prehash shape: query string lives in the path, GET body is empty, POST carries JSON
# ---------------------------------------------------------------------------


def test_get_signs_query_string_in_path_with_empty_body(monkeypatch):
    creds = _complete_credentials()
    client = OkxClient(credentials=creds)

    recorded = {}
    original_sign = client.sign

    def spy_sign(timestamp, method, request_path, body):
        recorded["timestamp"] = timestamp
        recorded["method"] = method
        recorded["request_path"] = request_path
        recorded["body"] = body
        return original_sign(timestamp, method, request_path, body)

    monkeypatch.setattr(client, "sign", spy_sign)
    _install_fake_urlopen(monkeypatch, {"code": "0", "data": []})

    client.get("/api/v5/account/balance", params={"ccy": "BTC"})

    assert recorded["method"] == "GET"
    assert recorded["request_path"] == "/api/v5/account/balance?ccy=BTC"
    assert recorded["body"] == ""


def test_post_signs_json_body(monkeypatch):
    creds = _complete_credentials()
    client = OkxClient(credentials=creds)

    recorded = {}
    original_sign = client.sign

    def spy_sign(timestamp, method, request_path, body):
        recorded["method"] = method
        recorded["request_path"] = request_path
        recorded["body"] = body
        return original_sign(timestamp, method, request_path, body)

    monkeypatch.setattr(client, "sign", spy_sign)
    _install_fake_urlopen(monkeypatch, {"code": "0", "data": []})

    client.post("/api/v5/trade/order", body={"instId": "BTC-USDT", "sz": "1"})

    assert recorded["method"] == "POST"
    assert recorded["request_path"] == "/api/v5/trade/order"
    assert recorded["body"] == json.dumps({"instId": "BTC-USDT", "sz": "1"})
    # Body must be valid, non-empty JSON -- never the empty string GET uses.
    assert json.loads(recorded["body"]) == {"instId": "BTC-USDT", "sz": "1"}


# ---------------------------------------------------------------------------
# timestamp format
# ---------------------------------------------------------------------------


def test_timestamp_is_iso8601_with_milliseconds_and_z_suffix():
    timestamp = OkxClient._timestamp()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", timestamp), (
        timestamp
    )


# ---------------------------------------------------------------------------
# x-simulated-trading header
# ---------------------------------------------------------------------------


def test_headers_include_simulated_flag_when_enabled():
    client = OkxClient(credentials=_complete_credentials(simulated=True))
    headers = client.headers("GET", "/api/v5/account/balance", "")
    assert headers["x-simulated-trading"] == "1"


def test_headers_omit_simulated_flag_when_disabled():
    client = OkxClient(credentials=_complete_credentials(simulated=False))
    headers = client.headers("GET", "/api/v5/account/balance", "")
    assert "x-simulated-trading" not in headers


def test_headers_set_content_type_only_for_post():
    client = OkxClient(credentials=_complete_credentials())
    get_headers = client.headers("GET", "/api/v5/account/balance", "")
    post_headers = client.headers("POST", "/api/v5/trade/order", "{}")
    assert "Content-Type" not in get_headers
    assert post_headers["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# fail-closed: missing credentials must raise, never silently fall back
# ---------------------------------------------------------------------------


def test_private_call_without_credentials_raises_credentials_missing(monkeypatch):
    client = OkxClient(credentials=OkxCredentials())  # all fields blank
    _install_fake_urlopen(monkeypatch, {"code": "0", "data": []})

    with pytest.raises(OkxCredentialsMissing) as exc_info:
        client.get("/api/v5/account/balance")

    message = str(exc_info.value)
    assert "OKX_API_KEY" in message
    assert "OKX_API_SECRET" in message
    assert "OKX_API_PASSPHRASE" in message


def test_private_call_with_partial_credentials_raises_credentials_missing():
    client = OkxClient(
        credentials=OkxCredentials(api_key="only-key", api_secret="", passphrase="")
    )
    with pytest.raises(OkxCredentialsMissing):
        client.headers("GET", "/api/v5/account/balance", "")


# ---------------------------------------------------------------------------
# public_get never attaches auth headers, even with valid credentials present
# ---------------------------------------------------------------------------


def test_public_get_sends_no_auth_headers_even_with_credentials(monkeypatch):
    client = OkxClient(credentials=_complete_credentials())
    calls: List[Dict[str, Any]] = []
    _install_fake_urlopen(
        monkeypatch, {"code": "0", "data": [{"last": "50000"}]}, calls
    )

    client.public_get("/api/v5/market/ticker", params={"instId": "BTC-USDT"})

    assert len(calls) == 1
    sent_headers = {key.lower() for key in calls[0]["headers"]}
    for private_header in (
        "ok-access-key",
        "ok-access-sign",
        "ok-access-timestamp",
        "ok-access-passphrase",
        "x-simulated-trading",
    ):
        assert private_header not in sent_headers


# ---------------------------------------------------------------------------
# credentials repr/str must never leak secret or passphrase
# ---------------------------------------------------------------------------


def test_credentials_repr_never_contains_secret_or_passphrase():
    creds = _complete_credentials()
    rendered = repr(creds)
    assert creds.api_secret not in rendered
    assert creds.passphrase not in rendered
    # The key is allowed to show only its last 4 characters, never in full.
    assert creds.api_key not in rendered
    assert str(creds) == rendered


# ---------------------------------------------------------------------------
# business error (code != "0") raises OkxApiError and is never retried
# ---------------------------------------------------------------------------


def test_api_error_raises_and_does_not_retry(monkeypatch):
    client = OkxClient(credentials=_complete_credentials())
    calls: List[Dict[str, Any]] = []
    _install_fake_urlopen(
        monkeypatch,
        {"code": "50011", "msg": "Invalid signature", "data": []},
        calls,
    )

    with pytest.raises(OkxApiError) as exc_info:
        client.get("/api/v5/account/balance", params={"ccy": "BTC"})

    assert exc_info.value.code == "50011"
    assert exc_info.value.msg == "Invalid signature"
    # A rejected request must not be silently resent, regardless of retry config.
    assert len(calls) == 1


def test_transport_error_retries_then_raises(monkeypatch):
    client = OkxClient(credentials=_complete_credentials(), timeout=1)
    calls: List[Dict[str, Any]] = []
    _install_fake_urlopen(
        monkeypatch, {"code": "0", "data": []}, calls, raise_transport_error=True
    )

    with pytest.raises(OkxTransportError):
        client.get("/api/v5/account/balance")

    # OKX_HTTP_MAX_RETRIES defaults to 2 retries beyond the first attempt.
    from Agent.backend.infra.config import config

    assert len(calls) == config.OKX_HTTP_MAX_RETRIES + 1


# ---------------------------------------------------------------------------
# LỖI 1 -- OKX 403s the default urllib User-Agent; a real one must always be
# sent, on every code path (get/post/public_get), even though public_get
# otherwise deliberately skips every auth header.
# ---------------------------------------------------------------------------


def _sent_user_agent(headers: Dict[str, str]) -> Optional[str]:
    for key, value in headers.items():
        if key.lower() == "user-agent":
            return value
    return None


def test_get_sends_default_user_agent(monkeypatch):
    client = OkxClient(credentials=_complete_credentials())
    calls: List[Dict[str, Any]] = []
    _install_fake_urlopen(monkeypatch, {"code": "0", "data": []}, calls)

    client.get("/api/v5/account/balance")

    assert _sent_user_agent(calls[0]["headers"]) == DEFAULT_USER_AGENT


def test_post_sends_default_user_agent(monkeypatch):
    client = OkxClient(credentials=_complete_credentials())
    calls: List[Dict[str, Any]] = []
    _install_fake_urlopen(monkeypatch, {"code": "0", "data": []}, calls)

    client.post("/api/v5/trade/order", body={"instId": "BTC-USDT", "sz": "1"})

    assert _sent_user_agent(calls[0]["headers"]) == DEFAULT_USER_AGENT


def test_public_get_sends_default_user_agent(monkeypatch):
    client = OkxClient(credentials=OkxCredentials())  # no credentials needed at all
    calls: List[Dict[str, Any]] = []
    _install_fake_urlopen(monkeypatch, {"code": "0", "data": []}, calls)

    client.public_get("/api/v5/market/ticker", params={"instId": "BTC-USDT"})

    assert _sent_user_agent(calls[0]["headers"]) == DEFAULT_USER_AGENT


def test_user_agent_is_overridable(monkeypatch):
    client = OkxClient(credentials=_complete_credentials(), user_agent="custom-agent/9")
    calls: List[Dict[str, Any]] = []
    _install_fake_urlopen(monkeypatch, {"code": "0", "data": []}, calls)

    client.get("/api/v5/account/balance")

    assert _sent_user_agent(calls[0]["headers"]) == "custom-agent/9"


# ---------------------------------------------------------------------------
# LỖI 2 -- the try/except/else bug: an HTTPError response with OKX's real
# {code, msg} body must raise OkxApiError with that code, never a generic
# OkxTransportError that throws the code away.
# ---------------------------------------------------------------------------


def _install_fake_urlopen_raising_http_error(
    monkeypatch: pytest.MonkeyPatch, status: int, payload: Dict[str, Any]
) -> None:
    """Fake urlopen() that raises a *real* HTTPError carrying a JSON body.

    Built from the actual urllib.error.HTTPError (not a hand-rolled stand-in)
    so this test exercises the exact `except HTTPError as exc: raw = exc.read()`
    branch client.py hits for real -- HTTPError.read() delegates to the `fp`
    file object passed to its constructor, so wrapping the JSON bytes in a
    BytesIO reproduces OKX's real "401 + JSON error body" response shape.
    """
    body = json.dumps(payload).encode("utf-8")

    def fake_urlopen(request, timeout=None):
        raise HTTPError(request.full_url, status, "error", {}, io.BytesIO(body))

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(client_module.time, "sleep", lambda _seconds: None)


def test_http_401_with_okx_error_body_raises_api_error_not_transport_error(
    monkeypatch,
):
    client = OkxClient(credentials=_complete_credentials())
    _install_fake_urlopen_raising_http_error(
        monkeypatch, 401, {"code": "50111", "msg": "Invalid OK-ACCESS-KEY"}
    )

    with pytest.raises(OkxApiError) as exc_info:
        client.get("/api/v5/account/balance")

    assert exc_info.value.code == "50111"
    assert exc_info.value.msg == "Invalid OK-ACCESS-KEY"


def test_http_error_body_is_not_retried_like_a_transport_failure(monkeypatch):
    """A business rejection surfaced via non-2xx status must still raise on
    the first attempt -- exactly like the pure-200 OkxApiError case -- not
    get treated as a retryable transport error."""
    calls: List[int] = []
    body = json.dumps({"code": "50111", "msg": "Invalid OK-ACCESS-KEY"}).encode("utf-8")

    def fake_urlopen(request, timeout=None):
        calls.append(1)
        raise HTTPError(request.full_url, 401, "error", {}, io.BytesIO(body))

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(client_module.time, "sleep", lambda _seconds: None)
    client = OkxClient(credentials=_complete_credentials())

    with pytest.raises(OkxApiError):
        client.get("/api/v5/account/balance")

    assert len(calls) == 1


# ---------------------------------------------------------------------------
# LỖI 3 -- IPv6 to OKX is blackholed on this host; OkxClient must scope every
# request to IPv4 only (via OKX_FORCE_IPV4, default on) and must always put
# socket.getaddrinfo back exactly as it found it, success or failure.
# ---------------------------------------------------------------------------


def test_prefer_ipv4_forces_af_inet_and_restores_getaddrinfo(monkeypatch):
    # Install the spy as the "original" getaddrinfo *before* entering the
    # scope, so _prefer_ipv4() captures it as the function it wraps -- that
    # is what actually proves the wrapper forces AF_INET, rather than just
    # observing that *some* function got installed.
    calls: List[int] = []

    def _spy(host, port, family=0, type=0, proto=0, flags=0):
        calls.append(family)
        return []

    monkeypatch.setattr(socket, "getaddrinfo", _spy)
    original = socket.getaddrinfo  # == _spy

    with client_module._prefer_ipv4():
        patched = socket.getaddrinfo
        assert patched is not original
        patched("example.com", 443, socket.AF_INET6)  # asks for IPv6...
        assert calls == [socket.AF_INET]  # ...but AF_INET is what gets requested

    assert socket.getaddrinfo is original


def test_prefer_ipv4_restores_getaddrinfo_even_when_the_body_raises():
    original = socket.getaddrinfo
    with pytest.raises(RuntimeError):
        with client_module._prefer_ipv4():
            assert socket.getaddrinfo is not original
            raise RuntimeError("simulated failure inside the scoped block")
    assert socket.getaddrinfo is original


def test_maybe_prefer_ipv4_is_a_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(config, "OKX_FORCE_IPV4", False)
    original = socket.getaddrinfo
    with client_module._maybe_prefer_ipv4():
        assert socket.getaddrinfo is original
    assert socket.getaddrinfo is original


def test_maybe_prefer_ipv4_patches_when_enabled(monkeypatch):
    monkeypatch.setattr(config, "OKX_FORCE_IPV4", True)
    original = socket.getaddrinfo
    with client_module._maybe_prefer_ipv4():
        assert socket.getaddrinfo is not original
    assert socket.getaddrinfo is original


def test_request_patches_getaddrinfo_during_the_call_when_enabled(monkeypatch):
    monkeypatch.setattr(config, "OKX_FORCE_IPV4", True)
    original = socket.getaddrinfo
    observed: Dict[str, bool] = {}

    def fake_urlopen(request, timeout=None):
        observed["patched"] = socket.getaddrinfo is not original
        return _FakeResponse({"code": "0", "data": []})

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    client = OkxClient(credentials=_complete_credentials())

    client.get("/api/v5/account/balance")

    assert observed["patched"] is True
    assert socket.getaddrinfo is original, "must be restored after the call returns"


def test_request_does_not_touch_getaddrinfo_when_disabled(monkeypatch):
    monkeypatch.setattr(config, "OKX_FORCE_IPV4", False)
    original = socket.getaddrinfo
    observed: Dict[str, bool] = {}

    def fake_urlopen(request, timeout=None):
        observed["patched"] = socket.getaddrinfo is not original
        return _FakeResponse({"code": "0", "data": []})

    monkeypatch.setattr(client_module.urllib.request, "urlopen", fake_urlopen)
    client = OkxClient(credentials=_complete_credentials())

    client.get("/api/v5/account/balance")

    assert observed["patched"] is False


def test_getaddrinfo_restored_after_request_raises(monkeypatch):
    """The IPv4 patch must come off even when the whole request ultimately
    fails and OkxTransportError propagates out of _send()."""
    client = OkxClient(credentials=_complete_credentials(), timeout=1)
    _install_fake_urlopen(
        monkeypatch, {"code": "0", "data": []}, raise_transport_error=True
    )
    original = socket.getaddrinfo

    with pytest.raises(OkxTransportError):
        client.get("/api/v5/account/balance")

    assert socket.getaddrinfo is original
