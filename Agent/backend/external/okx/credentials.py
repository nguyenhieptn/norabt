from __future__ import annotations

from dataclasses import dataclass

from Agent.backend.infra.config import config


def _mask(value: str, keep_suffix: int = 0) -> str:
    """Collapse a secret to a fixed marker so it is safe in logs/tracebacks.

    A partial mask (e.g. first/last N chars) still leaks enough of a short
    passphrase to narrow a brute-force search, so anything that isn't the API
    key itself gets flattened to a constant placeholder instead of a
    length-revealing pattern.
    """
    if not value:
        return "(empty)"
    if keep_suffix and len(value) > keep_suffix:
        return f"***{value[-keep_suffix:]}"
    return "***"


@dataclass(frozen=True)
class OkxCredentials:
    """Bundle of OKX v5 auth material plus which environment it belongs to.

    Demo and live keys are issued from separate OKX programs and are not
    interchangeable, so `simulated` travels with the key material rather than
    being decided per-call -- mixing a live key with the demo header (or vice
    versa) is exactly the kind of mistake this type exists to prevent.
    """

    api_key: str = ""
    api_secret: str = ""
    passphrase: str = ""
    simulated: bool = True

    @classmethod
    def from_config(cls) -> "OkxCredentials":
        return cls(
            api_key=config.OKX_API_KEY,
            api_secret=config.OKX_API_SECRET,
            passphrase=config.OKX_API_PASSPHRASE,
            simulated=config.OKX_SIMULATED,
        )

    @property
    def is_complete(self) -> bool:
        """All three values are required together; OKX rejects a partial set anyway."""
        return bool(self.api_key and self.api_secret and self.passphrase)

    @property
    def missing_fields(self) -> list:
        """Named so a caller can build a precise, actionable error message."""
        fields = []
        if not self.api_key:
            fields.append("OKX_API_KEY")
        if not self.api_secret:
            fields.append("OKX_API_SECRET")
        if not self.passphrase:
            fields.append("OKX_API_PASSPHRASE")
        return fields

    def __repr__(self) -> str:
        # Never format secret/passphrase into logs or exception messages: this
        # repr is what a stray `print(credentials)` or an uncaught traceback
        # would actually show, so it has to be safe by construction, not by
        # caller discipline.
        return (
            "OkxCredentials(api_key="
            f"{_mask(self.api_key, keep_suffix=4)}, "
            f"api_secret={_mask(self.api_secret)}, "
            f"passphrase={_mask(self.passphrase)}, "
            f"simulated={self.simulated})"
        )

    __str__ = __repr__
