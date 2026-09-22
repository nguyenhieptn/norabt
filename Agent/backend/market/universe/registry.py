from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from Agent.backend.infra.config import config
from Agent.backend.market.service import MarketDataUnavailableError, MarketService
from Agent.backend.market.universe.eligibility import AssetEligibilityVerifier
from Agent.backend.market.universe.ranking import UniverseAsset, UniverseRanker


class UniverseRegistry:
    """Versioned in-memory view of observed candidates and eligible assets."""

    _instance: Optional["UniverseRegistry"] = None

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = data_dir or Path(config.DATA_DIR)
        self._assets: Dict[str, UniverseAsset] = {}
        self._candidates: Dict[str, UniverseAsset] = {}
        self._rejections: Dict[str, str] = {}
        self._by_symbol: Dict[str, List[UniverseAsset]] = {}
        self.reload_from_data()

    @classmethod
    def get_instance(cls) -> "UniverseRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def reload_from_data(self, as_of_ms: Optional[int] = None) -> None:
        self._assets.clear()
        self._candidates.clear()
        self._rejections.clear()
        self._by_symbol.clear()
        service = MarketService(self.data_dir)
        observed: List[UniverseAsset] = []
        for venue_type in ("CEX", "DEX"):
            root = self.data_dir / "market" / venue_type.lower()
            if not root.is_dir():
                continue
            for asset_dir in sorted(path for path in root.iterdir() if path.is_dir()):
                try:
                    result = service.get_market_result(
                        asset_dir.name, venue_type=venue_type, as_of_ms=as_of_ms
                    )
                except (MarketDataUnavailableError, ValueError):
                    continue
                observed.append(
                    UniverseAsset(
                        asset_id=result.asset_id,
                        symbol=result.symbol,
                        venue=result.venue,
                        venue_type=result.venue_type,
                        chain=result.chain or "UNKNOWN",
                        rank=1,
                        volume_24h_usd=result.price_state.volume_24h_usd,
                        liquidity_usd=result.liquidity_state.total_depth_02_usd,
                        spread_pct=result.price_state.spread_pct,
                        depth_02_usd=result.liquidity_state.total_depth_02_usd,
                        selected_at=result.timestamp,
                        data_quality_score=result.data_quality_score,
                        freshness_score=result.data_quality.freshness_score,
                        selection_reason="OBSERVED_LOCAL_DATA",
                    )
                )

        for candidate in UniverseRanker.rank(observed):
            self._candidates[candidate.asset_id] = candidate
            eligible, reason = AssetEligibilityVerifier.verify(candidate)
            if eligible:
                asset = candidate.model_copy(update={"selection_reason": reason})
                self._assets[asset.asset_id] = asset
                self._by_symbol.setdefault(asset.symbol, []).append(asset)
            else:
                self._rejections[candidate.asset_id] = reason

    def list_all(self) -> List[UniverseAsset]:
        return list(self._assets.values())

    def list_candidates(self) -> List[UniverseAsset]:
        return list(self._candidates.values())

    def list_rejections(self) -> Dict[str, str]:
        return dict(self._rejections)

    def list_cex(self) -> List[UniverseAsset]:
        return [asset for asset in self._assets.values() if asset.venue_type == "CEX"]

    def list_dex(self) -> List[UniverseAsset]:
        return [asset for asset in self._assets.values() if asset.venue_type == "DEX"]
