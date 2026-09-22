from __future__ import annotations

from typing import Optional

from Agent.backend.market.schemas.market_result import OnchainActivityState
from Agent.backend.external.oklink.settings import is_oklink_enabled


class OnchainActivityFeatureExtractor:
    """On-chain whale/large-transfer signal for a token on X Layer.

    Scaffolding only -- returns `data_state="DISABLED"` whenever
    `OKLINK_ENABLED` is unset/false (the default), which is the case for
    every asset today: no asset in this project has a confirmed
    `get_large_transfers()` call to make yet (see
    `Agent/backend/oklink/client.py` module docstring for exactly what's
    missing). Deliberately does not accept an already-fetched payload the way
    `LiquidityFeatureExtractor.extract_from_pool()` does, because there is no
    real payload shape to accept until that endpoint is confirmed.
    """

    @staticmethod
    def extract(token_address: Optional[str] = None) -> OnchainActivityState:
        if not is_oklink_enabled() or not token_address:
            return OnchainActivityState(data_state="DISABLED")
        # Intentionally does not call OkLinkClient().get_large_transfers()
        # here: that method raises NotImplementedError by design (see its
        # docstring), and this extractor must not swallow that into a
        # fabricated UNKNOWN/OK result -- a caller flipping OKLINK_ENABLED=true
        # before the endpoint is implemented should see the real error, not a
        # silently-empty state that looks like "checked, nothing found".
        raise NotImplementedError(
            "OKLINK_ENABLED=true but OkLinkClient.get_large_transfers() is not "
            "implemented yet -- see Agent/backend/oklink/client.py."
        )
