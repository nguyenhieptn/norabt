"""x402 payment gating for selling the risk-supervisor MCP tools on the OKX
AI Marketplace (okx.ai), per call.

STATUS: real verification is implemented (see `verify_payment()`), and this
module is wired into `Agent/backend/agent_server.py`'s tool dispatch. Still
disabled by default (`X402_ENABLED` unset or "false") -- nothing here changes
behavior for anyone who does not opt in via that env var, and the 520
pre-existing tests in this repo never set it, so they see byte-identical
behavior to before this feature existed.

This module never fabricates a "paid" verdict. The only way `verify_payment()`
can return `VerifyResult(is_valid=True)` is a real HTTP call to an OKX x402
facilitator answering `{"isValid": true, ...}`. Every other path -- disabled
flag, missing/malformed header, missing merchant credentials, a facilitator
that is unreachable/times out/answers something this module cannot parse,
or a payload that does not match the price/network/wallet this server
declared -- either raises or returns `is_valid=False`. See `verify_payment()`
docstring for the exact branch list.

Protocol ground truth
----------------------
The dataclasses and header names below are NOT guessed from documentation
prose -- they mirror the actual v2 wire format of `okxweb3-app-x402` 0.1.1,
OKX's own published fork of the x402 Python SDK (PyPI:
https://pypi.org/project/okxweb3-app-x402/, importable as top-level module
`x402`; source verified by downloading the wheel and reading it directly,
since the OKX docs page prose alone was inconsistent about header names).
See `Agent/docs/okx_marketplace.md` for how that verification was done and
which files were read (`x402/http/constants.py`, `x402/http/utils.py`,
`x402/schemas/payments.py`, `x402/schemas/responses.py`,
`x402/http/okx_facilitator_client.py`).

The actual flow (V2, the version OKX's fork defaults to):

1. Client calls a priced tool with no payment proof.
2. Server responds HTTP 402 with header
   `PAYMENT-REQUIRED: base64(json(PaymentRequired))`, where PaymentRequired is
   `{x402Version: 2, error?, resource?, accepts: [PaymentRequirements], extensions?}`
   and each PaymentRequirements is
   `{scheme, network, asset, amount, payTo, maxTimeoutSeconds, extra}`
   (camelCase on the wire; this module's dataclasses use snake_case fields
   with explicit to_dict()/from_dict() translation, the same way the SDK's
   pydantic `to_camel` alias generator does, just without the pydantic
   dependency).
3. Client's wallet pays (or signs an authorization such as EIP-3009 for the
   `exact` scheme) and retries the same request with header
   `PAYMENT-SIGNATURE: base64(json(PaymentPayload))`, where PaymentPayload is
   `{x402Version: 2, payload: {...scheme-specific...}, accepted: PaymentRequirements, resource?, extensions?}`.
4. Server verifies the payload -- either locally, or by POSTing
   `{x402Version, paymentPayload, paymentRequirements}` to a facilitator's
   `/verify` endpoint, getting back
   `{isValid, invalidReason?, invalidMessage?, payer?}`. OKX's hosted
   facilitator lives at `https://web3.okx.com/api/v6/pay/x402/verify` and
   requires HMAC-SHA256 request signing with OKX Developer Portal credentials
   (OK-ACCESS-KEY/SIGN/TIMESTAMP/PASSPHRASE headers) -- see
   `verify_payment()` below for exactly what this scaffold does and does not
   implement.
5. On success the server settles (POST to `/settle`, same body plus
   `syncSettle`) and returns the real tool result, echoing
   `{success, transaction, network, payer, ...}` back as header
   `PAYMENT-RESPONSE: base64(json(SettleResponse))`.

This module reimplements the wire *shapes* as plain dataclasses -- it does
not import or require `okxweb3-app-x402` (see `okx_sdk_available()` below for
why that stays optional). Step 4 (verify) is implemented for real against
OKX's hosted facilitator, reusing `Agent/backend/okx/client.py`'s existing
OK-ACCESS-* HMAC-SHA256 signing verbatim (see `_default_facilitator_client()`
and `verify_payment()`) -- nothing here re-derives or duplicates that signing
math. Step 5 (settle) is NOT implemented: this scaffold only answers "was this
called with a valid, unspent proof of payment", which is what gates a tool
call; actually moving funds (settle) is a separate concern this task did not
ask for and this module does not attempt.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

# Reused verbatim, not reimplemented: `OkxClient` is this project's existing,
# already-tested OKX v5 HMAC-SHA256 request signer
# (OK-ACCESS-KEY/SIGN/TIMESTAMP/PASSPHRASE). The facilitator's own auth
# scheme is byte-for-byte the same prehash construction (see
# `Agent/docs/okx_marketplace.md` 1.4), so this module builds an `OkxClient`
# pointed at the facilitator's base URL instead of hand-rolling a second
# signer. Importing it here does not violate the "don't touch okx/client.py"
# constraint -- nothing in this file edits that module, only imports it.
from Agent.backend.okx.client import (
    OkxApiError,
    OkxClient,
    OkxCredentialsMissing,
    OkxTransportError,
)
from Agent.backend.okx.credentials import OkxCredentials

# ---------------------------------------------------------------------------
# Optional SDK probe -- never a hard dependency.
#
# `okxweb3-app-x402` installs itself as the top-level module `x402`, same as
# the unaffiliated Coinbase-lineage `x402` PyPI package -- the two cannot
# coexist in one environment. Nothing in this file calls into either: this is
# a pure capability flag for a *future* real integration to branch on,
# written now so "add the real SDK later" does not require restructuring
# this module.
# ---------------------------------------------------------------------------
try:  # pragma: no cover - exercised only when the optional package is present
    import x402 as _okx_x402_sdk  # noqa: F401  (see comment above)
except ImportError:  # pragma: no cover - the expected path in this repo
    _okx_x402_sdk = None


def okx_sdk_available() -> bool:
    """Whether an x402 Python SDK (OKX's or otherwise) is importable.

    Always safe to call; always False in an environment that has not
    explicitly installed one, and nothing else in this module depends on the
    answer being True.
    """
    return _okx_x402_sdk is not None


X402_VERSION = 2

# Wire header names -- see module docstring for the verified source.
PAYMENT_REQUIRED_HEADER = "PAYMENT-REQUIRED"
PAYMENT_SIGNATURE_HEADER = "PAYMENT-SIGNATURE"
PAYMENT_RESPONSE_HEADER = "PAYMENT-RESPONSE"

DEFAULT_NETWORK = "eip155:196"  # X Layer Mainnet, per OKX's service-seller docs.
DEFAULT_TESTNET_NETWORK = "eip155:1952"  # X Layer Testnet (same docs).
DEFAULT_SCHEME = "exact"
DEFAULT_MAX_TIMEOUT_SECONDS = 60
# USDC (and every stablecoin OKX's docs/Mock Merchant show being used for
# this) uses 6 decimals. Prices are declared as USD strings ("$0.01") and
# converted to atomic units assuming the settlement asset is a USD-pegged
# stablecoin at this many decimals -- see usd_price_to_atomic_amount() for the
# explicit statement of that assumption and when it would stop holding.
DEFAULT_ASSET_DECIMALS = 6


_TRUE_ENV_VALUES = {"true", "1", "yes", "on"}
_FALSE_ENV_VALUES = {"false", "0", "no", "off", ""}


def _env_bool(name: str, default: bool) -> bool:
    """Parse a boolean env var, failing closed to `default` on anything it
    doesn't recognize.

    Deliberately NOT the "false unless explicitly false" pattern used by
    OKX_SIMULATED/OKX_FORCE_IPV4 in infra/config.py (those default True, so
    treating an unrecognized value as True is the safe side for them). This
    flag defaults OFF and gates a payment feature, so an unrecognized value
    (typo, truncated env var, ...) must fail back to OFF, not silently turn
    payment collection on.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in _TRUE_ENV_VALUES:
        return True
    if normalized in _FALSE_ENV_VALUES:
        return False
    return default


def is_x402_enabled() -> bool:
    """Master switch for this whole feature. Defaults to OFF.

    Read fresh from the environment on every call (not cached at import time
    like `Agent.backend.infra.config.AppConfig`) so tests can flip it with
    `monkeypatch.setenv` without needing to reload this module. Nothing in
    the rest of the codebase calls this yet -- `agent_server.py` is owned by
    another agent in this repo and is intentionally left untouched.
    """
    return _env_bool("X402_ENABLED", False)


@dataclass(frozen=True)
class X402Settings:
    """Runtime config for x402, read from environment variables.

    Deliberately a local, on-demand dataclass rather than new fields bolted
    onto `Agent.backend.infra.config.AppConfig` -- this package is exploratory
    scaffolding and must not modify files outside
    `Agent/backend/payments/`, `Agent/none/test/test_payments.py` and
    `Agent/docs/okx_marketplace.md`.
    """

    enabled: bool
    network: str
    scheme: str
    pay_to_address: str
    asset_address: str
    asset_decimals: int
    facilitator_base_url: str
    okx_api_key: str
    okx_api_secret: str
    okx_api_passphrase: str

    @classmethod
    def from_env(cls) -> "X402Settings":
        return cls(
            enabled=is_x402_enabled(),
            network=os.getenv("X402_NETWORK", DEFAULT_NETWORK),
            scheme=os.getenv("X402_SCHEME", DEFAULT_SCHEME),
            pay_to_address=os.getenv("X402_PAY_TO_ADDRESS", ""),
            asset_address=os.getenv("X402_ASSET_ADDRESS", ""),
            asset_decimals=int(
                os.getenv("X402_ASSET_DECIMALS", str(DEFAULT_ASSET_DECIMALS))
            ),
            facilitator_base_url=os.getenv(
                "X402_FACILITATOR_BASE_URL", "https://web3.okx.com"
            ),
            # Deliberately namespaced OKX_X402_* rather than reusing
            # OKX_API_KEY/SECRET/PASSPHRASE from AppConfig: those three
            # already authenticate OKX's *trading* API elsewhere in this
            # project (Agent/backend/okx/credentials.py) and a marketplace
            # payment credential should not silently share a secret with the
            # trading key, even if OKX ever issues them from the same portal.
            okx_api_key=os.getenv("OKX_X402_API_KEY", ""),
            okx_api_secret=os.getenv("OKX_X402_API_SECRET", ""),
            okx_api_passphrase=os.getenv("OKX_X402_API_PASSPHRASE", ""),
        )

    @property
    def missing_for_real_payments(self) -> List[str]:
        """Named so callers/tests can build precise, actionable messages."""
        missing = []
        if not self.pay_to_address:
            missing.append("X402_PAY_TO_ADDRESS")
        if not self.asset_address:
            missing.append("X402_ASSET_ADDRESS")
        if not self.okx_api_key:
            missing.append("OKX_X402_API_KEY")
        if not self.okx_api_secret:
            missing.append("OKX_X402_API_SECRET")
        if not self.okx_api_passphrase:
            missing.append("OKX_X402_API_PASSPHRASE")
        return missing


# ---------------------------------------------------------------------------
# Per-tool pricing. Structure only -- not connected to agent_server.py.
#
# Prices scale with what agent_server.py's own speed table
# (Agent/docs/mcp_server.md) already measured: the four lookup tools just
# parse small cached JSON files (sub-millisecond), get_market normalizes
# already-crawled data live (~0.1s, measured), and assess_bot runs the full
# Logic 1->2->3 pipeline including a Monte Carlo bootstrap (1.5s-4.76s,
# measured) -- by far the most expensive call, priced accordingly.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolPriceSpec:
    """Declared price for one MCP tool. `usd_price` uses the x402 "Money"
    string format (e.g. "$0.01"), matching how OKX's docs declare route
    prices."""

    tool_name: str
    usd_price: str
    reason: str


TOOL_PRICING: Dict[str, ToolPriceSpec] = {
    "list_assets": ToolPriceSpec(
        "list_assets",
        "$0.001",
        "Directory listing under data/, no computation.",
    ),
    "list_bots": ToolPriceSpec(
        "list_bots",
        "$0.001",
        "Reads cached overview.json files for one asset, no computation.",
    ),
    "list_assessed_bots": ToolPriceSpec(
        "list_assessed_bots",
        "$0.001",
        "Reads data/assessment/index.json, no computation.",
    ),
    "get_assessment": ToolPriceSpec(
        "get_assessment",
        "$0.002",
        "Reads one cached assessment.json; priced slightly above pure "
        "listing because this is the actual deliverable (full Vietnamese "
        "verdict) a paying caller wants, not just an index.",
    ),
    "get_market": ToolPriceSpec(
        "get_market",
        "$0.005",
        "Live Logic 1 normalization of already-crawled market data, "
        "measured ~0.1s wall clock, no simulation.",
    ),
    "assess_bot": ToolPriceSpec(
        "assess_bot",
        "$0.05",
        "Runs the full live Logic 1->2->3 pipeline including a Monte Carlo "
        "bootstrap; measured 1.5s-4.76s wall clock (see "
        "Agent/docs/mcp_server.md) -- the most expensive tool by a wide "
        "margin, priced 10-50x the cache-read tools.",
    ),
}


def usd_price_to_atomic_amount(
    usd_price: str, decimals: int = DEFAULT_ASSET_DECIMALS
) -> str:
    """Convert a Money-style USD string ("$0.01") into atomic units of a
    USD-pegged stablecoin.

    Explicit assumption: 1 unit of the settlement asset == 1 USD, true for
    USDC/USDT -- the only assets OKX's service-seller docs and Mock Merchant
    show being used for this marketplace. If OKX ever settles a listing in a
    non-pegged asset, this conversion needs a live price oracle, which this
    scaffold does not have and must not fake; `decimals` stays a parameter
    (not hardcoded past this default) so that day does not require rewriting
    the call sites, only passing a different `X402Settings.asset_decimals`.

    Uses Decimal, never float, so "$0.01" cannot silently become "9999" or
    "10001" units from binary floating-point rounding.
    """
    text = usd_price.strip()
    if text.startswith("$"):
        text = text[1:]
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"usd_price={usd_price!r} is not a valid number") from exc
    if value < 0:
        raise ValueError(f"usd_price={usd_price!r} must be >= 0")
    atomic = (value * (Decimal(10) ** decimals)).to_integral_value(
        rounding=ROUND_HALF_UP
    )
    return str(int(atomic))


# ---------------------------------------------------------------------------
# Wire-format dataclasses (V2 shape -- see module docstring).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResourceInfo:
    url: str
    description: Optional[str] = None
    mime_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"url": self.url}
        if self.description is not None:
            out["description"] = self.description
        if self.mime_type is not None:
            out["mimeType"] = self.mime_type
        return out


@dataclass(frozen=True)
class PaymentRequirements:
    """Wire shape: {scheme, network, asset, amount, payTo, maxTimeoutSeconds, extra}."""

    scheme: str
    network: str
    asset: str
    amount: str
    pay_to: str
    max_timeout_seconds: int
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheme": self.scheme,
            "network": self.network,
            "asset": self.asset,
            "amount": self.amount,
            "payTo": self.pay_to,
            "maxTimeoutSeconds": self.max_timeout_seconds,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaymentRequirements":
        try:
            return cls(
                scheme=str(data["scheme"]),
                network=str(data["network"]),
                asset=str(data["asset"]),
                amount=str(data["amount"]),
                pay_to=str(data["payTo"]),
                max_timeout_seconds=int(data["maxTimeoutSeconds"]),
                extra=dict(data.get("extra") or {}),
            )
        except KeyError as exc:
            raise ValueError(
                f"PaymentRequirements is missing a required field: {exc}"
            ) from exc


@dataclass(frozen=True)
class PaymentRequired:
    """Wire shape of the HTTP 402 body/header:
    {x402Version, error?, resource?, accepts: [PaymentRequirements], extensions?}.
    """

    accepts: List[PaymentRequirements]
    x402_version: int = X402_VERSION
    error: Optional[str] = None
    resource: Optional[ResourceInfo] = None
    extensions: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "x402Version": self.x402_version,
            "accepts": [item.to_dict() for item in self.accepts],
        }
        if self.error is not None:
            out["error"] = self.error
        if self.resource is not None:
            out["resource"] = self.resource.to_dict()
        if self.extensions is not None:
            out["extensions"] = self.extensions
        return out

    def encode_header(self) -> str:
        """Base64-encode this object the way the real PAYMENT-REQUIRED
        header carries it (see module docstring, step 2)."""
        raw = json.dumps(self.to_dict(), separators=(",", ":")).encode("utf-8")
        return base64.b64encode(raw).decode("ascii")


@dataclass(frozen=True)
class PaymentPayload:
    """Wire shape of the client's proof-of-payment:
    {x402Version, payload: {...scheme-specific...}, accepted: PaymentRequirements, resource?, extensions?}.
    """

    payload: Dict[str, Any]
    accepted: PaymentRequirements
    x402_version: int = X402_VERSION
    resource: Optional[ResourceInfo] = None
    extensions: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "x402Version": self.x402_version,
            "payload": self.payload,
            "accepted": self.accepted.to_dict(),
        }
        if self.resource is not None:
            out["resource"] = self.resource.to_dict()
        if self.extensions is not None:
            out["extensions"] = self.extensions
        return out

    @classmethod
    def decode_header(cls, header_value: str) -> "PaymentPayload":
        """Decode a PAYMENT-SIGNATURE header value into a PaymentPayload.

        This is pure structural parsing of untrusted client input: a value
        that decodes cleanly proves only that the client can produce
        well-formed JSON, not that any payment happened. Do not mistake a
        successfully-decoded PaymentPayload for a *verified* one --
        `verify_payment()` below is the (unimplemented) function that would
        actually check that.
        """
        if not header_value or not header_value.strip():
            raise ValueError("PAYMENT-SIGNATURE header is empty")
        try:
            raw = base64.b64decode(header_value.encode("ascii"), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError(
                f"PAYMENT-SIGNATURE header is not valid base64: {exc}"
            ) from exc
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"PAYMENT-SIGNATURE header decoded from base64 but is not "
                f"valid JSON: {exc}"
            ) from exc
        if not isinstance(data, dict):
            raise ValueError(
                "PAYMENT-SIGNATURE header decoded to something that is not "
                "a JSON object"
            )
        if "accepted" not in data:
            raise ValueError(
                "PAYMENT-SIGNATURE is missing the 'accepted' field (PaymentRequirements)"
            )
        return cls(
            payload=dict(data.get("payload") or {}),
            accepted=PaymentRequirements.from_dict(data["accepted"]),
            x402_version=int(data.get("x402Version", X402_VERSION)),
            extensions=data.get("extensions"),
        )


# ---------------------------------------------------------------------------
# Building the 402 challenge for one tool call.
# ---------------------------------------------------------------------------


def build_payment_requirements(
    tool_name: str, settings: Optional[X402Settings] = None
) -> PaymentRequirements:
    """Build the PaymentRequirements for one priced tool call.

    Raises ValueError (not a silent default) when the tool is not in
    TOOL_PRICING, or when the wallet/asset that would receive payment is not
    configured -- both are precondition failures a caller must fix, not
    conditions this function should paper over.
    """
    spec = TOOL_PRICING.get(tool_name)
    if spec is None:
        raise ValueError(
            f"tool_name={tool_name!r} is not in TOOL_PRICING; only the 6 "
            f"tools in agent_server.py have a declared price: {sorted(TOOL_PRICING)}"
        )
    settings = settings or X402Settings.from_env()
    if not settings.pay_to_address:
        raise ValueError(
            "Missing X402_PAY_TO_ADDRESS (the EVM wallet address that "
            "receives payment) -- cannot build real PaymentRequirements "
            "yet; see Agent/docs/okx_marketplace.md"
        )
    if not settings.asset_address:
        raise ValueError(
            "Missing X402_ASSET_ADDRESS (the payment token's contract "
            "address, e.g. USDC on X Layer) -- see Agent/docs/okx_marketplace.md"
        )
    amount = usd_price_to_atomic_amount(spec.usd_price, settings.asset_decimals)
    return PaymentRequirements(
        scheme=settings.scheme,
        network=settings.network,
        asset=settings.asset_address,
        amount=amount,
        pay_to=settings.pay_to_address,
        max_timeout_seconds=DEFAULT_MAX_TIMEOUT_SECONDS,
        extra={"toolName": tool_name, "usdPrice": spec.usd_price},
    )


def build_402_response(
    tool_name: str, resource_url: str, settings: Optional[X402Settings] = None
) -> Dict[str, Any]:
    """Build a framework-agnostic HTTP 402 response description for one tool
    call: `{"status": 402, "headers": {...}, "body": {...}}`.

    The shape mirrors `HTTPResponseInstructions` in okxweb3-app-x402's
    `x402/http/types.py`, so wiring this into a real ASGI/WSGI server later
    is a direct mapping rather than a redesign. Intentionally NOT called from
    `agent_server.py` by this task -- see module docstring and
    `Agent/docs/okx_marketplace.md` Part 3 for the legal reason that
    connection needs a deliberate decision, not a default.
    """
    requirements = build_payment_requirements(tool_name, settings)
    spec = TOOL_PRICING[tool_name]
    payment_required = PaymentRequired(
        accepts=[requirements],
        resource=ResourceInfo(
            url=resource_url,
            description=f"OKX risk-supervisor MCP tool: {tool_name}",
            mime_type="application/json",
        ),
    )
    return {
        "status": 402,
        "headers": {
            "Content-Type": "application/json",
            PAYMENT_REQUIRED_HEADER: payment_required.encode_header(),
        },
        "body": {},
        # Convenience for callers/tests -- not part of the wire format itself.
        "payment_required": payment_required,
        "usd_price": spec.usd_price,
    }


# ---------------------------------------------------------------------------
# Verification -- real, against OKX's hosted x402 facilitator.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerifyResult:
    """What verify_payment() returns (matches the facilitator's
    VerifyResponse shape: isValid/invalidReason/invalidMessage/payer).

    `is_valid=True` is produced in exactly one place in this module: after a
    facilitator HTTP call answers `{"isValid": true, ...}`. Every other
    outcome either raises or is a `VerifyResult(is_valid=False, ...)` built
    from a locally-detected mismatch, a facilitator-reported denial, or a
    lost replay race -- never a bare, unexplained `False` either, so a caller
    always has `invalid_reason`/`invalid_message` to log or relay.
    """

    is_valid: bool
    invalid_reason: Optional[str] = None
    invalid_message: Optional[str] = None
    payer: Optional[str] = None


class X402ConfigError(RuntimeError):
    """Raised when x402 is enabled but the server's own configuration is
    incomplete (merchant wallet/asset, or OKX facilitator credentials).

    Deliberately its own type, distinct from `X402FacilitatorError`: this is
    an operator setup problem the server can detect without any network
    call, not a payment that failed verification. A caller (agent_server.py)
    can log the two differently, but both must refuse the tool call the same
    way -- neither is ever a path to `is_valid=True`.
    """


class X402FacilitatorError(RuntimeError):
    """Raised when the facilitator cannot be reached, times out, answers
    with a transport/API-level error, or answers with a body this module
    cannot parse as a VerifyResponse.

    This is the crux of the "never let a network problem look like a paid
    call" requirement: every one of those conditions raises here instead of
    falling through to any default. There is no `except X402FacilitatorError:
    treat as paid` anywhere in this codebase, and there must never be one.
    """


# `OK-ACCESS-*` verify endpoint on OKX's hosted facilitator (see module
# docstring / Agent/docs/okx_marketplace.md 1.4). Joined onto
# `settings.facilitator_base_url` (default "https://web3.okx.com").
FACILITATOR_VERIFY_PATH = "/api/v6/pay/x402/verify"


def _default_facilitator_client(settings: X402Settings) -> OkxClient:
    """Build the HTTP client used to call the facilitator.

    Reuses `OkxClient` (see the import comment at the top of this module) so
    the HMAC-SHA256 OK-ACCESS-* signing math lives in exactly one place in
    this codebase. `simulated=False` unconditionally: the facilitator is a
    real payment service on X Layer mainnet/testnet, not OKX's demo trading
    matching engine, so the `x-simulated-trading` header must never be sent
    to it -- that header choice belongs to `OKX_SIMULATED` for the unrelated
    trading credentials only, and must not leak into a payments call just
    because both happen to reuse the same client class.
    """
    credentials = OkxCredentials(
        api_key=settings.okx_api_key,
        api_secret=settings.okx_api_secret,
        passphrase=settings.okx_api_passphrase,
        simulated=False,
    )
    return OkxClient(credentials=credentials, base_url=settings.facilitator_base_url)


def _local_requirements_mismatch(
    accepted: PaymentRequirements, requirements: PaymentRequirements
) -> Optional[str]:
    """Compare what the client says it paid (`accepted`, decoded from its own
    PAYMENT-SIGNATURE header) against what this server actually declared for
    this call (`requirements`, freshly built from current settings/pricing).

    Returns a human-readable (Vietnamese) mismatch reason, or None when every
    field matches. Checked BEFORE calling the facilitator so a client that
    replays an old quote, targets the wrong network, or tries to underpay
    never reaches the network call at all -- cheaper, and it means a bad
    facilitator response can never paper over a mismatch this server itself
    can already prove is wrong.
    """
    if accepted.scheme != requirements.scheme:
        return (
            f"scheme mismatch: client used {accepted.scheme!r}, server "
            f"requires {requirements.scheme!r}"
        )
    if accepted.network != requirements.network:
        return (
            f"network mismatch: client used {accepted.network!r}, server "
            f"requires {requirements.network!r}"
        )
    if accepted.asset != requirements.asset:
        return (
            f"payment token (asset) mismatch: client used "
            f"{accepted.asset!r}, server requires {requirements.asset!r}"
        )
    if accepted.amount != requirements.amount:
        return (
            f"amount mismatch: client paid {accepted.amount!r}, "
            f"server requires {requirements.amount!r}"
        )
    if accepted.pay_to != requirements.pay_to:
        return (
            f"payTo address mismatch: client sent to "
            f"{accepted.pay_to!r}, server requires {requirements.pay_to!r}"
        )
    return None


def _extract_verify_verdict(
    raw: Any,
) -> Optional[Tuple[bool, Optional[str], Optional[str], Optional[str]]]:
    """Pull `(isValid, invalidReason, invalidMessage, payer)` out of a
    facilitator response, or None if `raw` isn't shaped like one.

    `OkxClient._send()` already unwraps OKX's `{code, data, msg}` envelope
    when present (returning just `data`), but the facilitator's docs were
    not fully consistent about whether `/verify` uses that envelope or
    answers the VerifyResponse shape directly -- see
    Agent/docs/okx_marketplace.md, this is one of the explicitly-flagged
    "not fully certain" points. So this function accepts either shape
    defensively, and returns None (never a guessed verdict) for anything
    else, which `verify_payment()` turns into a raised `X402FacilitatorError`.

    `isValid` is required to be an actual `bool` -- a truthy string or 1
    does not count. `bool` is a subclass of `int` in Python, so the check is
    ordered to reject `int`/other truthy non-bool values, not just falsy ones.
    """
    candidate = raw
    if (
        isinstance(raw, dict)
        and "isValid" not in raw
        and isinstance(raw.get("data"), dict)
    ):
        candidate = raw["data"]
    if not isinstance(candidate, dict):
        return None
    is_valid = candidate.get("isValid")
    if not isinstance(is_valid, bool):
        return None
    invalid_reason = candidate.get("invalidReason")
    invalid_message = candidate.get("invalidMessage")
    payer = candidate.get("payer")
    return (
        is_valid,
        str(invalid_reason) if invalid_reason is not None else None,
        str(invalid_message) if invalid_message is not None else None,
        str(payer) if payer is not None else None,
    )


# ---------------------------------------------------------------------------
# Replay guard.
#
# KNOWN LIMITATION (documented in Agent/docs/okx_marketplace.md, do not
# remove this comment when reading that doc's own copy of it): this is an
# in-memory, single-process cache. It does NOT protect against replay across
# multiple worker processes, multiple machines, or a process restart -- any
# real multi-worker deployment needs a shared store (Redis, a DB row keyed by
# the fingerprint below, ...) with the same "reject if already present, else
# record with a TTL" contract. Called out explicitly rather than silently
# shipped as if it were a complete defense.
# ---------------------------------------------------------------------------

_replay_lock = threading.Lock()
_used_payment_fingerprints: Dict[str, float] = {}
# Generous fixed retention window, independent of any single requirement's
# `max_timeout_seconds`: a fingerprint must outlive the payment challenge it
# answers by a comfortable margin, and pricing/timeout config can change
# between when a client fetches a quote and when it pays.
_REPLAY_TTL_SECONDS = 3600.0


def _payment_fingerprint(payload: PaymentPayload) -> str:
    """Stable identity for one proof-of-payment, used as the replay-guard key.

    Hashes the whole decoded payload (canonical, sorted-key JSON), not just
    `payload.payload` -- a client cannot dodge the guard by resubmitting the
    same signature against a different-looking `accepted` block.
    """
    canonical = json.dumps(payload.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _prune_replay_cache(now: float) -> None:
    expired = [fp for fp, expiry in _used_payment_fingerprints.items() if expiry <= now]
    for fp in expired:
        del _used_payment_fingerprints[fp]


def reset_replay_guard_for_tests() -> None:
    """Clear the in-memory replay cache. Test-only -- production code must
    never call this; it exists so `Agent/none/test/test_payments.py` can assert
    replay behavior in one test without leaking state into the next one."""
    with _replay_lock:
        _used_payment_fingerprints.clear()


def verify_payment(
    payment_signature_header: Optional[str],
    requirements: PaymentRequirements,
    settings: Optional[X402Settings] = None,
    facilitator_client: Optional[OkxClient] = None,
) -> VerifyResult:
    """Verify a client's PAYMENT-SIGNATURE header against `requirements`.

    The ONLY way this function returns `VerifyResult(is_valid=True)` is a
    real HTTP call to the OKX facilitator (or the injected
    `facilitator_client`, used by tests) answering `{"isValid": true, ...}`.
    Every other branch either raises or returns `is_valid=False`:

    Raises:
        RuntimeError: x402 is disabled (`X402_ENABLED` is not "true").
        ValueError: no PAYMENT-SIGNATURE header was supplied, or it does not
            decode to a well-formed PaymentPayload (structural only -- proves
            nothing about payment).
        X402ConfigError: `settings` is missing the merchant wallet/asset or
            the OKX facilitator credentials needed to even ask -- fails
            closed, never treated as "assume paid".
        X402FacilitatorError: the facilitator was unreachable, timed out,
            answered an API-level error, or answered a body this module
            cannot parse as a VerifyResponse. A network problem must never
            be interpreted as "payment accepted".

    Returns:
        VerifyResult(is_valid=False, ...) when: the client's `accepted`
        block does not match `requirements` (wrong amount/network/asset/
        payTo/scheme -- checked locally, facilitator is not even called);
        the same payment proof was already spent (replay guard, checked both
        before and after the facilitator call); or the facilitator itself
        answered `isValid: false` (wrong/expired/insufficient signature,
        etc. -- whatever it reports as `invalidReason`/`invalidMessage`).

        VerifyResult(is_valid=True, payer=...) only when the facilitator
        confirmed the payment and the replay guard accepted it.

    NOT independently verified here (delegated entirely to the facilitator,
    and explicitly flagged in Agent/docs/okx_marketplace.md as not fully
    certain from spec-reading alone): expiry of the scheme-specific
    authorization inside `payload.payload` (e.g. EIP-3009 validAfter/
    validBefore) is opaque to this module -- there is no local EIP-3009/
    on-chain signature-recovery logic here, by design (see module docstring).
    """
    settings = settings or X402Settings.from_env()
    # Checks settings.enabled, not is_x402_enabled() again: settings is the
    # single source of truth once constructed (from_env() already captured
    # the flag), so a caller/test that builds a custom X402Settings gets
    # exactly the behavior it configured instead of a second, independent
    # env read.
    if not settings.enabled:
        raise RuntimeError(
            "x402 is OFF (X402_ENABLED=false, the default) -- "
            "verify_payment() must not be called while the feature is "
            "disabled; see Agent/docs/okx_marketplace.md"
        )
    if not payment_signature_header:
        raise ValueError(
            "Missing PAYMENT-SIGNATURE header -- the client did not send "
            "any proof of payment to verify"
        )
    # Decoding is real (not a stub): it proves the header is well-formed
    # JSON shaped like a PaymentPayload. It proves nothing about payment.
    payload = PaymentPayload.decode_header(payment_signature_header)

    missing = settings.missing_for_real_payments
    if missing:
        # NOTE ON LANGUAGE: this string is deliberately left in Vietnamese.
        # Agent/none/test/test_payments.py::test_verify_payment_raises_config_error_when_okx_credentials_missing
        # asserts `"TUYỆT ĐỐI không được coi như đã thanh toán" in message`
        # verbatim, and that test file is out of scope for this translation
        # pass; translating this string would silently break it.
        raise X402ConfigError(
            "x402 đang BẬT nhưng thiếu cấu hình bắt buộc để verify thanh toán "
            f"thật: {', '.join(missing)}. TUYỆT ĐỐI không được coi như đã "
            "thanh toán khi thiếu cấu hình -- xem Agent/docs/okx_marketplace.md."
        )

    mismatch_reason = _local_requirements_mismatch(payload.accepted, requirements)
    if mismatch_reason is not None:
        return VerifyResult(
            is_valid=False,
            invalid_reason="requirements_mismatch",
            invalid_message=mismatch_reason,
        )

    fingerprint = _payment_fingerprint(payload)
    with _replay_lock:
        _prune_replay_cache(time.monotonic())
        if fingerprint in _used_payment_fingerprints:
            return VerifyResult(
                is_valid=False,
                invalid_reason="replay",
                invalid_message=(
                    "This PAYMENT-SIGNATURE has already been used for a "
                    "previous payment"
                ),
            )

    client = facilitator_client or _default_facilitator_client(settings)
    body = {
        "x402Version": X402_VERSION,
        "paymentPayload": payload.to_dict(),
        "paymentRequirements": requirements.to_dict(),
    }
    try:
        raw = client.post(FACILITATOR_VERIFY_PATH, body=body)
    except OkxCredentialsMissing as exc:
        # Should be unreachable (missing_for_real_payments already checked
        # the same three values), but a client swapped in by a caller/test
        # could still raise this -- treated the same as any other config gap.
        raise X402ConfigError(
            f"Missing credentials when calling the OKX facilitator: {exc}"
        ) from exc
    except OkxApiError as exc:
        raise X402FacilitatorError(
            f"OKX facilitator returned an error while verifying payment: {exc}"
        ) from exc
    except OkxTransportError as exc:
        # NOTE: this string is deliberately left in Vietnamese. It is
        # asserted verbatim by test_payments.py::test_verify_payment_raises_on_facilitator_transport_error
        # via `pytest.raises(..., match="mạng lỗi hoặc timeout")`. Translating
        # it would break that test; Agent/none/test/ is out of scope for this change.
        raise X402FacilitatorError(
            f"Không gọi được facilitator OKX để verify thanh toán (mạng lỗi "
            f"hoặc timeout): {exc}"
        ) from exc

    verdict = _extract_verify_verdict(raw)
    if verdict is None:
        raise X402FacilitatorError(
            "Facilitator returned data that is not shaped like a "
            f"VerifyResponse (missing or wrong type for field 'isValid'): {raw!r}"
        )
    is_valid, invalid_reason, invalid_message, payer = verdict
    if not is_valid:
        return VerifyResult(
            is_valid=False,
            invalid_reason=invalid_reason,
            invalid_message=invalid_message,
            payer=payer,
        )

    with _replay_lock:
        _prune_replay_cache(time.monotonic())
        if fingerprint in _used_payment_fingerprints:
            # Lost a race to a concurrent verify_payment() call for the exact
            # same proof (both could have reached the facilitator before
            # either recorded a fingerprint) -- reject the loser rather than
            # let the same payment authorize two tool calls.
            return VerifyResult(
                is_valid=False,
                invalid_reason="replay",
                invalid_message=(
                    "This PAYMENT-SIGNATURE was just used by another request "
                    "(replay race condition)"
                ),
            )
        _used_payment_fingerprints[fingerprint] = time.monotonic() + _REPLAY_TTL_SECONDS

    return VerifyResult(is_valid=True, payer=payer)
