from __future__ import annotations

from typing import Any, Dict, List, Optional

from Agent.backend.market.schemas.market_result import PriceState


class PriceFeatureExtractor:
    """Extract price observations; unavailable quote fields remain absent."""

    @staticmethod
    def extract(
        last_price: float,
        bid: Optional[float],
        ask: Optional[float],
        candles_1h: List[Dict[str, Any]],
        override_volume_24h_usd: Optional[float] = None,
        override_spread_pct: Optional[float] = None,
    ) -> PriceState:
        spread = max(0.0, ask - bid) if bid is not None and ask is not None else None
        spread_pct = (
            spread / last_price if spread is not None and last_price > 0 else None
        )
        if spread_pct is None and override_spread_pct is not None:
            spread_pct = override_spread_pct
            spread = spread_pct * last_price

        recent = candles_1h[-24:]
        high = (
            max(float(c.get("high", last_price)) for c in recent)
            if recent
            else last_price
        )
        low = (
            min(float(c.get("low", last_price)) for c in recent)
            if recent
            else last_price
        )
        volume = (
            sum(float(c.get("volCcyQuote", c.get("vol", 0.0))) for c in recent)
            if recent
            else None
        )
        if (volume is None or volume <= 0.0) and override_volume_24h_usd is not None:
            volume = override_volume_24h_usd

        counts = [c.get("count") for c in recent]
        trade_count = (
            sum(int(value) for value in counts if value is not None)
            if any(value is not None for value in counts)
            else None
        )
        return PriceState(
            last_price=last_price,
            bid=bid,
            ask=ask,
            spread=spread,
            spread_pct=spread_pct,
            volume_24h_usd=volume,
            trade_count_24h=trade_count,
            high_24h=high,
            low_24h=low,
        )
