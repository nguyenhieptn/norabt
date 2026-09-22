"""Thin OKLink Open API client -- X Layer on-chain data, read-only.

OKLink (oklink.com) is OKX's block-explorer product: a *separate* service
from both the OKX trading API (`Agent/backend/okx/client.py`) and the OKX
Web3 Developer Portal x402 facilitator (`Agent/backend/payments/x402.py`).
Confirmed 2026-09 (web search + fetch against oklink.com's own docs/pages,
no API key available yet to make a real call -- see "NOT YET CONFIRMED"
below):
  - Base URL: `https://www.oklink.com`, paths under `/api/v5/explorer/...`.
  - Auth: a single `Ok-Access-Key: <key>` header. No HMAC signing, no
    timestamp, no passphrase -- unlike the OKX trading API this deliberately
    does NOT reuse `okx/client.py`'s `sign()`/`headers()`.
  - `chainShortName=XLAYER` selects OKX's X Layer mainnet (also confirmed:
    `XLAYER_TESTNET` exists for the testnet).
  - Two endpoints have a confirmed exact path (via a third-party Go client
    that wraps this same API): `address/address-summary` (native-token
    balance + tx count for one address) and `token/token-list`.

NOT YET CONFIRMED, do not implement further without a real key + a real
response to check against: the exact endpoint/parameters for a *token
contract's transfer history filtered/sorted by amount* -- the piece an
on-chain "whale / large-transfer" signal actually needs. OKLink's own site
has a "large transfer monitor" page (oklink.com/large-transfer-monitor/xlayer)
proving the data exists, but its docs site is a JS-rendered SPA that could
not be read far enough to pin down the REST path. `get_large_transfers()`
below raises `NotImplementedError` rather than guess at a path/response
shape -- this codebase's established rule is to verify a real credential/API
against a real response before trusting it, not to ship a plausible-looking
guess (see the X402_ASSET_ADDRESS discrepancy warning in `Agent/.env` for
why that rule exists).

Also unconfirmed: whether OKLink's JSON envelope matches OKX's own
`{"code": "0", "msg": "", "data": [...]}` shape. `_send()` assumes it does
(same family of API, same `/api/v5/` path prefix), but this must be
double-checked against a real response the first time `OKLINK_API_KEY` is
set -- if the shape differs, `_parse_envelope()` is the one place to fix.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

from Agent.backend.external.oklink.settings import OkLinkSettings

DEFAULT_USER_AGENT = "Mozilla/5.0"


class OkLinkError(Exception):
    """Base for every error this module raises."""


class OkLinkCredentialsMissing(OkLinkError):
    """Raised instead of silently sending an unauthenticated request that
    OKLink would just reject -- a caller finds out immediately, the same
    fail-closed shape as `OkxCredentialsMissing`."""


class OkLinkApiError(OkLinkError):
    """OKLink answered but rejected the request. code/msg passed through
    verbatim, unverified envelope shape -- see module docstring."""

    def __init__(self, code: str, msg: str) -> None:
        self.code = code
        self.msg = msg
        super().__init__(f"OKLink API returned an error (code={code}): {msg}")


class OkLinkTransportError(OkLinkError):
    """The request never got an answer (network/timeout/malformed response) --
    kept distinct from OkLinkApiError because only this kind is retry-safe."""


class OkLinkClient:
    """Read-only OKLink v5 explorer client. Confirmed endpoints only -- see
    module docstring for what is deliberately NOT implemented yet."""

    def __init__(self, settings: Optional[OkLinkSettings] = None) -> None:
        self.settings = settings or OkLinkSettings.from_env()
        self.base_url = self.settings.base_url.rstrip("/")

    def _headers(self) -> Dict[str, str]:
        if not self.settings.api_key:
            raise OkLinkCredentialsMissing(
                "OKLINK_API_KEY is not set. Get one at https://www.oklink.com "
                "(connect a wallet, verify by signature) -- see "
                "Agent/.env.example for the full explanation."
            )
        return {"Ok-Access-Key": self.settings.api_key, "User-Agent": DEFAULT_USER_AGENT}

    def get_address_summary(
        self, address: str, chain_short_name: Optional[str] = None
    ) -> Any:
        """Native-token balance + tx count for one address.

        Confirmed path: `GET /api/v5/explorer/address/address-summary`.
        """
        return self._get(
            "/api/v5/explorer/address/address-summary",
            {
                "chainShortName": chain_short_name or self.settings.chain_short_name,
                "address": address,
            },
        )

    def get_token_list(
        self, chain_short_name: Optional[str] = None, **params: Any
    ) -> Any:
        """Confirmed path: `GET /api/v5/explorer/token/token-list`.

        `**params` is passed through as-is (e.g. `limit`, `page`) since the
        exact optional-parameter set was not itself part of what got
        confirmed -- only the path was.
        """
        query = {"chainShortName": chain_short_name or self.settings.chain_short_name}
        query.update(params)
        return self._get("/api/v5/explorer/token/token-list", query)

    def get_large_transfers(self, *args: Any, **kwargs: Any) -> Any:
        """Not implemented -- see module docstring's "NOT YET CONFIRMED"
        section. Deliberately raises instead of guessing an endpoint path or
        response shape, so a caller can never mistake a fabricated result for
        real on-chain data."""
        raise NotImplementedError(
            "OKLink's endpoint for a token's large-transfer/whale history is "
            "not yet confirmed against a real API key. Get an OKLINK_API_KEY "
            "(see Agent/.env.example), read https://www.oklink.com/docs/en/ "
            "while authenticated, and implement this method against the real "
            "documented endpoint + response shape before calling it."
        )

    def _get(self, request_path: str, params: Dict[str, Any]) -> Any:
        headers = self._headers()
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        url = f"{self.base_url}{request_path}?{query}"
        return self._send(url, headers, request_path)

    def _send(self, url: str, headers: Dict[str, str], request_path: str) -> Any:
        request = urllib.request.Request(url, headers=headers, method="GET")
        max_attempts = self.settings.max_retries + 1
        last_error: Optional[Exception] = None
        for attempt in range(max_attempts):
            try:
                with urllib.request.urlopen(
                    request, timeout=self.settings.timeout_seconds
                ) as response:
                    raw = response.read()
            except urllib.error.HTTPError as exc:
                # Mirrors okx/client.py: OKX-family APIs put error JSON in the
                # body even on non-200 status, so this still parses below.
                raw = exc.read()
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt + 1 < max_attempts:
                    time.sleep(0.3 * (2**attempt))
                    continue
                raise OkLinkTransportError(
                    f"Could not connect to OKLink ({request_path}): {exc}"
                ) from exc
            return self._parse_envelope(raw, request_path)
        raise OkLinkTransportError(f"Could not call OKLink ({request_path}): {last_error}")

    @staticmethod
    def _parse_envelope(raw: bytes, request_path: str) -> Any:
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise OkLinkTransportError(
                f"OKLink returned invalid data for {request_path}: {exc}"
            ) from exc
        # ASSUMED envelope shape, not yet verified against a real response --
        # see module docstring. `.get(...)` throughout so an unexpected shape
        # degrades to `code=None` (treated as success, `data` falls back to
        # the whole payload) rather than raising a confusing KeyError.
        code = payload.get("code") if isinstance(payload, dict) else None
        if code is not None and code != "0":
            raise OkLinkApiError(code, payload.get("msg", ""))
        return payload.get("data", payload) if isinstance(payload, dict) else payload
