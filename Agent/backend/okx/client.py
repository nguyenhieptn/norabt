from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import json
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, Optional

from Agent.backend.infra.config import config
from Agent.backend.okx.credentials import OkxCredentials

# OKX's edge answers a request carrying Python's default urllib User-Agent
# ("Python-urllib/x.y") with a bare HTTP 403 before any OKX business logic
# runs -- confirmed by sending the identical request with only this header
# changed. Matches the value Agent/scripts/crawl_bots.py already sends via
# curl; the exact string doesn't matter to OKX, only that it isn't the
# Python default.
DEFAULT_USER_AGENT = "Mozilla/5.0"

# Guards the process-wide socket.getaddrinfo monkey-patch in _prefer_ipv4()
# below so two threads sending OKX requests at once can never see one
# thread's IPv4-only patch while the other thread has already restored it
# (or vice versa) -- see that function's docstring for why the patch exists.
_ipv4_patch_lock = threading.Lock()


@contextlib.contextmanager
def _prefer_ipv4() -> Iterator[None]:
    """Scope one connection attempt to IPv4 only.

    This host's IPv6 route to OKX/Cloudflare is blackholed: a SYN to either
    of the IPv6 addresses OKX's DNS returns gets no answer and no ICMP
    unreachable, while the IPv4 address answers in well under 100ms.
    `getaddrinfo()` lists the IPv6 addresses first, and
    `socket.create_connection()` (what urllib sits on top of) blocks for the
    full connect timeout on each dead address before moving on -- turning
    every request into a ~50s stall instead of an instant IPv4 connect.
    Deliberately does not hardcode an IP address (DNS still resolves
    normally, only the address family is constrained), and always restores
    the original `getaddrinfo` in `finally` -- including when the wrapped
    call raises -- so a failed request can never leave process-wide socket
    behaviour altered for unrelated code.
    """
    with _ipv4_patch_lock:
        original_getaddrinfo = socket.getaddrinfo

        def _ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
            return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

        socket.getaddrinfo = _ipv4_only
        try:
            yield
        finally:
            socket.getaddrinfo = original_getaddrinfo


@contextlib.contextmanager
def _maybe_prefer_ipv4() -> Iterator[None]:
    """No-op unless OKX_FORCE_IPV4 is set, so the toggle actually toggles."""
    if config.OKX_FORCE_IPV4:
        with _prefer_ipv4():
            yield
    else:
        yield


class OkxError(Exception):
    """Base for every error this module raises, so a caller can catch one type
    and know it came from the OKX layer rather than from urllib or json."""


class OkxCredentialsMissing(OkxError):
    """Raised instead of silently degrading to a public-endpoint result -- a
    caller that explicitly asked for private data has to find out immediately
    that it can't be served, not get back something that merely looks plausible."""


class OkxApiError(OkxError):
    """OKX answered but rejected the request. code/msg are passed through
    verbatim (not reworded) so they stay matchable against OKX's own error-code
    reference instead of a paraphrase of it."""

    def __init__(self, code: str, msg: str) -> None:
        self.code = code
        self.msg = msg
        super().__init__(f"OKX API returned an error (code={code}): {msg}")


class OkxTransportError(OkxError):
    """The request never got an answer from OKX (network/timeout/malformed
    response) -- kept distinct from OkxApiError because only this kind of
    failure is safe to retry; a rejected order must not be resent."""


class OkxClient:
    """Thin OKX v5 REST client: signs private calls, leaves public ones alone.

    Built on urllib.request only. The crawler already shells out to curl for
    public data instead of adding an HTTP dependency, so this keeps the same
    "stdlib only" property for the private path.
    """

    def __init__(
        self,
        credentials: Optional[OkxCredentials] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        self.credentials = credentials or OkxCredentials.from_config()
        self.base_url = (base_url or config.OKX_REST_URL).rstrip("/")
        self.timeout = config.OKX_HTTP_TIMEOUT_SECONDS if timeout is None else timeout
        # Overridable (see DEFAULT_USER_AGENT above for why one is always set).
        self.user_agent = user_agent or DEFAULT_USER_AGENT

    @staticmethod
    def _timestamp() -> str:
        # OKX requires ISO8601 with millisecond precision and a literal "Z".
        # datetime.isoformat() gives microseconds and a "+00:00" suffix instead,
        # and OKX's signature check rejects both (surfaces as code 50102/50111),
        # so the format is built by hand rather than trusting a generic isoformat.
        now = datetime.now(timezone.utc)
        millis = now.microsecond // 1000
        return now.strftime("%Y-%m-%dT%H:%M:%S") + f".{millis:03d}Z"

    def sign(self, timestamp: str, method: str, request_path: str, body: str) -> str:
        """Pure per the OKX v5 spec: base64(HMAC-SHA256(secret, prehash)).

        Deliberately does not check `credentials.is_complete` -- that guard
        lives in `headers()` -- so this stays a pure function of its four
        arguments and can be verified against a hand-computed test vector
        without touching the fail-closed path or the network.
        """
        prehash = f"{timestamp}{method.upper()}{request_path}{body}"
        digest = hmac.new(
            self.credentials.api_secret.encode("utf-8"),
            prehash.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    def headers(self, method: str, request_path: str, body: str) -> Dict[str, str]:
        # Single choke point for the fail-closed rule: get() and post() both
        # route through here, so there is exactly one place that could
        # accidentally let an incomplete credential slip through to a signed
        # request instead of failing loudly.
        if not self.credentials.is_complete:
            missing = ", ".join(self.credentials.missing_fields)
            raise OkxCredentialsMissing(
                "OKX credentials are missing, the following environment "
                f"variables must be set: {missing}. See the guide at "
                "Agent/.env.example."
            )
        timestamp = self._timestamp()
        result = {
            "OK-ACCESS-KEY": self.credentials.api_key,
            "OK-ACCESS-SIGN": self.sign(timestamp, method, request_path, body),
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.credentials.passphrase,
            "User-Agent": self.user_agent,
        }
        if self.credentials.simulated:
            # Demo and live are separate matching engines on OKX's side; this
            # header -- not the key itself -- is what actually routes the call
            # to the demo book, so it must track credentials.simulated exactly.
            result["x-simulated-trading"] = "1"
        if method.upper() == "POST":
            result["Content-Type"] = "application/json"
        return result

    def get(self, request_path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        path_with_query = self._with_query(request_path, params)
        headers = self.headers("GET", path_with_query, "")
        return self._send("GET", path_with_query, headers, data=None)

    def post(self, request_path: str, body: Optional[Dict[str, Any]] = None) -> Any:
        # OKX's POST endpoints parse the body as JSON unconditionally, so even
        # a "no body" call has to send the literal object "{}", never "".
        body_str = json.dumps(body) if body else "{}"
        headers = self.headers("POST", request_path, body_str)
        return self._send("POST", request_path, headers, data=body_str.encode("utf-8"))

    def public_get(
        self, request_path: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        # Deliberately skips headers()/sign(): a public endpoint must never
        # carry auth headers, even when credentials happen to be configured,
        # so calling this path can't leak which account is asking or trip a
        # signature check OKX doesn't expect here. User-Agent is not an auth
        # header, and OKX 403s the request outright without it (see
        # DEFAULT_USER_AGENT), so it is still set here.
        path_with_query = self._with_query(request_path, params)
        headers = {"User-Agent": self.user_agent}
        return self._send("GET", path_with_query, headers=headers, data=None)

    @staticmethod
    def _with_query(request_path: str, params: Optional[Dict[str, Any]]) -> str:
        if not params:
            return request_path
        query = urllib.parse.urlencode(params)
        return f"{request_path}?{query}"

    def _send(
        self,
        method: str,
        request_path: str,
        headers: Dict[str, str],
        data: Optional[bytes],
    ) -> Any:
        url = f"{self.base_url}{request_path}"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        max_attempts = config.OKX_HTTP_MAX_RETRIES + 1
        last_error: Optional[Exception] = None
        for attempt in range(max_attempts):
            try:
                with _maybe_prefer_ipv4():
                    with urllib.request.urlopen(
                        request, timeout=self.timeout
                    ) as response:
                        raw = response.read()
            except urllib.error.HTTPError as exc:
                # OKX puts its error JSON in the body even on non-200 status
                # (a bad API key answers HTTP 401 + {"code":"50111",...}), so
                # this still goes through the normal code/msg parsing below --
                # it must NOT be a bare `else` branch (that only runs when the
                # `try` raised nothing at all), or this body gets read and then
                # silently discarded, surfacing as a generic OkxTransportError
                # with the real OKX code/msg lost.
                raw = exc.read()
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                # OKX never answered -- nothing was acknowledged on its side,
                # so retrying is safe, unlike a business-rejected request.
                last_error = exc
                if attempt + 1 < max_attempts:
                    time.sleep(0.3 * (2**attempt))
                    continue
                raise OkxTransportError(
                    f"Could not connect to OKX ({request_path}): {exc}"
                ) from exc
            # Reached by both the plain-success path and the HTTPError path
            # above (never by the URLError/TimeoutError/OSError path, which
            # always either `continue`s or raises before getting here).
            payload = self._parse(raw, request_path)
            code = payload.get("code")
            if code is not None and code != "0":
                # OKX answered and refused the request on its own terms.
                # Resending it would just repeat an already-rejected
                # order/query, so this always raises on the first reply.
                raise OkxApiError(code, payload.get("msg", ""))
            return payload.get("data", payload)
        # Defensive only: the loop above always returns or raises before
        # falling through, since max_attempts >= 1.
        raise OkxTransportError(f"Could not call OKX ({request_path}): {last_error}")

    @staticmethod
    def _parse(raw: bytes, request_path: str) -> Dict[str, Any]:
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise OkxTransportError(
                f"OKX returned invalid data for {request_path}: {exc}"
            ) from exc
