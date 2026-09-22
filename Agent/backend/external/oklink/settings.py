"""Runtime config for the OKLink Open API integration (X Layer on-chain data).

Deliberately a local, on-demand dataclass rather than new fields bolted onto
`Agent.backend.infra.config.AppConfig` -- this package is scaffolding for an
on-chain whale/large-transfer feature that is NOT complete yet (see
`Agent/backend/oklink/client.py` module docstring for exactly what is/isn't
confirmed against OKLink's real API), so it is kept isolated the same way
`Agent/backend/payments/x402.py` isolates its own exploratory scaffolding.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://www.oklink.com"
# The chain identifier OKLink's docs list for OKX's X Layer mainnet (verified
# via https://web3.okx.com/xlayer/onchaindata/docs/en/, 2026-09: "supported
# chains include ... XLAYER, XLAYER_TESTNET ...").
DEFAULT_CHAIN_SHORT_NAME = "XLAYER"
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RETRIES = 2

_TRUE_ENV_VALUES = {"true", "1", "yes", "on"}
_FALSE_ENV_VALUES = {"false", "0", "no", "off", ""}


def _env_bool(name: str, default: bool) -> bool:
    """Parse a boolean env var, failing closed to `default` on anything it
    doesn't recognize. Same convention as `Agent.backend.external.payments.x402._env_bool`
    -- this flag defaults OFF and gates a not-yet-finished data source, so an
    unrecognized value must fail back to OFF, never silently turn it on."""
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in _TRUE_ENV_VALUES:
        return True
    if normalized in _FALSE_ENV_VALUES:
        return False
    return default


def is_oklink_enabled() -> bool:
    """Master switch for this whole feature. Defaults to OFF.

    Read fresh from the environment on every call (not cached at import time
    like `AppConfig`) so tests can flip it with `monkeypatch.setenv`. Must stay
    OFF until a real `OKLINK_API_KEY` has been obtained AND the large-transfer
    endpoint has been confirmed against a real response (see client.py) --
    turning this on before that only gets you `OnchainActivityFeatureExtractor`
    raising `NotImplementedError` on every call.
    """
    return _env_bool("OKLINK_ENABLED", False)


@dataclass(frozen=True)
class OkLinkSettings:
    """Read-only snapshot of the OKLink env vars, taken once via `from_env()`."""

    enabled: bool
    api_key: str
    base_url: str
    chain_short_name: str
    timeout_seconds: float
    max_retries: int

    @classmethod
    def from_env(cls) -> "OkLinkSettings":
        return cls(
            enabled=is_oklink_enabled(),
            # Deliberately its own env var, not reused from OKX_API_KEY or
            # OKX_X402_API_KEY: OKLink issues keys via its own wallet-connect
            # flow at oklink.com, a separate credential system from both the
            # OKX trading API (Agent/backend/okx/credentials.py) and the
            # OKX Web3 Developer Portal x402 key (Agent/backend/payments/x402.py).
            api_key=os.getenv("OKLINK_API_KEY", ""),
            base_url=os.getenv("OKLINK_BASE_URL", DEFAULT_BASE_URL),
            chain_short_name=os.getenv(
                "OKLINK_CHAIN_SHORT_NAME", DEFAULT_CHAIN_SHORT_NAME
            ),
            timeout_seconds=float(
                os.getenv("OKLINK_HTTP_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
            ),
            max_retries=max(
                int(os.getenv("OKLINK_HTTP_MAX_RETRIES", str(DEFAULT_MAX_RETRIES))), 0
            ),
        )

    @property
    def missing_for_real_calls(self) -> list[str]:
        """Names of the env vars still needed before a real API call can be made."""
        missing = []
        if not self.api_key:
            missing.append("OKLINK_API_KEY")
        return missing
