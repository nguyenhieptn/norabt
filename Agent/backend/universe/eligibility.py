from __future__ import annotations

from typing import Tuple

from Agent.backend.universe.ranking import UniverseAsset


class AssetEligibilityVerifier:
    MIN_24H_VOLUME_USD = 1_000_000.0
    MIN_DEPTH_02_USD = 50_000.0
    MAX_SPREAD_PCT = 0.005
    MIN_DATA_QUALITY = 0.35
    MIN_FRESHNESS_SCORE = 0.50

    @classmethod
    def verify(cls, asset: UniverseAsset) -> Tuple[bool, str]:
        missing = [
            name
            for name, value in (
                ("volume_24h_usd", asset.volume_24h_usd),
                ("depth_02_usd", asset.depth_02_usd),
                ("spread_pct", asset.spread_pct),
            )
            if value is None
        ]
        if missing:
            if asset.venue_type == "DEX":
                return False, "DEX_POOL_LIQUIDITY_NOT_COLLECTED"
            return False, f"UNKNOWN_EVIDENCE: {', '.join(missing)}"
        if asset.data_quality_score < cls.MIN_DATA_QUALITY:
            return False, f"DATA_QUALITY_TOO_LOW: {asset.data_quality_score:.2f}"
        if asset.freshness_score < cls.MIN_FRESHNESS_SCORE:
            return False, f"DATA_STALE: freshness score {asset.freshness_score:.2f}"
        if asset.volume_24h_usd < cls.MIN_24H_VOLUME_USD:
            return False, f"VOLUME_BELOW_MINIMUM: {asset.volume_24h_usd:.0f}"
        if asset.depth_02_usd < cls.MIN_DEPTH_02_USD:
            return False, f"DEPTH_BELOW_MINIMUM: {asset.depth_02_usd:.0f}"
        if asset.spread_pct > cls.MAX_SPREAD_PCT:
            return False, f"SPREAD_TOO_WIDE: {asset.spread_pct:.6f}"
        return True, "ELIGIBLE"
