from __future__ import annotations

import time
from typing import List, Optional

from pydantic import BaseModel, Field


class UniverseAsset(BaseModel):
    asset_id: str
    symbol: str
    venue: str
    venue_type: str
    chain: str
    rank: int = Field(..., ge=1)
    volume_24h_usd: Optional[float] = Field(default=None, ge=0.0)
    liquidity_usd: Optional[float] = Field(default=None, ge=0.0)
    spread_pct: Optional[float] = Field(default=None, ge=0.0)
    depth_02_usd: Optional[float] = Field(default=None, ge=0.0)
    selected_at: int = Field(default_factory=lambda: int(time.time() * 1000), ge=0)
    data_quality_score: float = Field(..., ge=0.0, le=1.0)
    freshness_score: float = Field(..., ge=0.0, le=1.0)
    selection_reason: str


class UniverseRanker:
    """Rank observed assets by venue cohort without fabricating market metrics."""

    CEX_LIMIT = 30
    DEX_LIMIT = 20

    @classmethod
    def rank(cls, assets: List[UniverseAsset]) -> List[UniverseAsset]:
        ranked: List[UniverseAsset] = []
        for venue_type, limit in (("CEX", cls.CEX_LIMIT), ("DEX", cls.DEX_LIMIT)):
            cohort = [asset for asset in assets if asset.venue_type == venue_type]
            cohort.sort(
                key=lambda asset: (
                    -(
                        asset.volume_24h_usd
                        if asset.volume_24h_usd is not None
                        else -1.0
                    ),
                    -(asset.liquidity_usd if asset.liquidity_usd is not None else -1.0),
                    asset.symbol,
                    asset.venue,
                )
            )
            ranked.extend(
                asset.model_copy(update={"rank": index})
                for index, asset in enumerate(cohort[:limit], 1)
            )
        return ranked
