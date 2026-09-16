from __future__ import annotations

from typing import Any, Dict, Optional

from Agent.backend.market.schemas.market_result import (
    LiquidityState,
    LiquidityStateEnum,
)


class LiquidityFeatureExtractor:
    """Calculate L2 depth and impact without inventing an order book."""

    @staticmethod
    def extract(
        orderbook_l2: Optional[Dict[str, Any]] = None,
        last_price: float = 100.0,
    ) -> LiquidityState:
        if not orderbook_l2:
            return LiquidityState(state_tier=LiquidityStateEnum.UNKNOWN)

        bids = orderbook_l2.get("bids") or []
        asks = orderbook_l2.get("asks") or []
        if not bids or not asks:
            return LiquidityState(state_tier=LiquidityStateEnum.UNKNOWN)

        bid_levels = [
            (float(level[0]), float(level[1])) for level in bids if len(level) >= 2
        ]
        ask_levels = [
            (float(level[0]), float(level[1])) for level in asks if len(level) >= 2
        ]
        if not bid_levels or not ask_levels:
            return LiquidityState(state_tier=LiquidityStateEnum.UNKNOWN)

        # Anchor the +/-0.2% band on the book's own mid, not the last candle close.
        # The book is minutes newer than the close, so a small drift pushed every
        # ask outside the band and reported a perfect 1.0 imbalance on every asset.
        reference = (bid_levels[0][0] + ask_levels[0][0]) / 2.0
        if reference <= 0:
            reference = last_price
        threshold_down = reference * 0.998
        threshold_up = reference * 1.002
        bid_depth = sum(px * size for px, size in bid_levels if px >= threshold_down)
        ask_depth = sum(px * size for px, size in ask_levels if px <= threshold_up)
        total_depth = bid_depth + ask_depth

        if total_depth <= 0:
            return LiquidityState(state_tier=LiquidityStateEnum.ILLIQUID)

        imbalance = (bid_depth - ask_depth) / total_depth
        slippage_10k = (10_000.0 / total_depth) * 0.2
        slippage_50k = (50_000.0 / total_depth) * 0.2

        if total_depth < 50_000.0:
            tier = LiquidityStateEnum.ILLIQUID
        elif total_depth < 200_000.0:
            tier = LiquidityStateEnum.THIN
        elif total_depth > 10_000_000.0:
            tier = LiquidityStateEnum.DEEP
        else:
            tier = LiquidityStateEnum.ADEQUATE

        bid_wall = max(bid_levels, key=lambda level: level[0] * level[1])[0]
        ask_wall = max(ask_levels, key=lambda level: level[0] * level[1])[0]
        return LiquidityState(
            bid_depth_02_usd=bid_depth,
            ask_depth_02_usd=ask_depth,
            total_depth_02_usd=total_depth,
            depth_imbalance=imbalance,
            estimated_slippage_10k_pct=slippage_10k,
            estimated_slippage_50k_pct=slippage_50k,
            state_tier=tier,
            bid_wall_price=bid_wall,
            ask_wall_price=ask_wall,
        )

    @classmethod
    def extract_from_pool(
        cls,
        pool_data: Optional[Dict[str, Any]] = None,
        last_price: float = 100.0,
    ) -> LiquidityState:
        if not pool_data:
            return LiquidityState(state_tier=LiquidityStateEnum.UNKNOWN)

        tvl = float(pool_data.get("tvl_usd") or 0.0)
        depth_02 = float(pool_data.get("depth_02_usd") or 0.0)
        if depth_02 <= 0.0 and tvl > 0.0:
            depth_02 = tvl * 0.015

        if depth_02 <= 0.0:
            return LiquidityState(state_tier=LiquidityStateEnum.ILLIQUID)

        bid_depth = depth_02 / 2.0
        ask_depth = depth_02 / 2.0
        total_depth = depth_02

        slippage_10k = (10_000.0 / total_depth) * 0.2
        slippage_50k = (50_000.0 / total_depth) * 0.2

        if total_depth < 50_000.0:
            tier = LiquidityStateEnum.ILLIQUID
        elif total_depth < 200_000.0:
            tier = LiquidityStateEnum.THIN
        elif total_depth > 1_000_000.0 or tvl > 10_000_000.0:
            tier = LiquidityStateEnum.DEEP
        else:
            tier = LiquidityStateEnum.ADEQUATE

        return LiquidityState(
            bid_depth_02_usd=bid_depth,
            ask_depth_02_usd=ask_depth,
            total_depth_02_usd=total_depth,
            depth_imbalance=0.0,
            estimated_slippage_10k_pct=slippage_10k,
            estimated_slippage_50k_pct=slippage_50k,
            state_tier=tier,
            bid_wall_price=last_price * 0.998,
            ask_wall_price=last_price * 1.002,
        )
