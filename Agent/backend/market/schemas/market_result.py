from __future__ import annotations

import time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from Agent.backend.infra.quality import DataQualitySummary


class TrendState(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    SIDEWAYS = "SIDEWAYS"
    BREAKOUT_BULL = "BREAKOUT_BULL"
    BREAKOUT_BEAR = "BREAKOUT_BEAR"
    UNKNOWN = "UNKNOWN"


class VolatilityState(str, Enum):
    COMPRESSED = "COMPRESSED"
    NORMAL = "NORMAL"
    EXPANDING = "EXPANDING"
    EXTREME = "EXTREME"
    UNKNOWN = "UNKNOWN"


class LiquidityStateEnum(str, Enum):
    DEEP = "DEEP"
    ADEQUATE = "ADEQUATE"
    THIN = "THIN"
    ILLIQUID = "ILLIQUID"
    UNKNOWN = "UNKNOWN"


class PriceState(BaseModel):
    last_price: float = Field(..., gt=0.0)
    bid: Optional[float] = Field(default=None, gt=0.0)
    ask: Optional[float] = Field(default=None, gt=0.0)
    spread: Optional[float] = Field(default=None, ge=0.0)
    spread_pct: Optional[float] = Field(default=None, ge=0.0)
    volume_24h_usd: Optional[float] = Field(default=None, ge=0.0)
    trade_count_24h: Optional[int] = Field(default=None, ge=0)
    high_24h: float = Field(..., gt=0.0)
    low_24h: float = Field(..., gt=0.0)


class StructureState(BaseModel):
    ema_20: float = Field(..., gt=0.0)
    ema_50: Optional[float] = Field(default=None, gt=0.0)
    ema_200: Optional[float] = Field(default=None, gt=0.0)
    atr_14: float = Field(..., ge=0.0)
    keltner_middle: float = Field(..., gt=0.0)
    keltner_upper: float = Field(..., gt=0.0)
    keltner_lower: float = Field(..., gt=0.0)
    keltner_width: float = Field(..., ge=0.0)
    keltner_width_zscore: Optional[float] = None
    realized_volatility: Optional[float] = Field(default=None, ge=0.0)
    volatility_percentile: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    trend_state: TrendState
    volatility_state: VolatilityState
    range_high: float = Field(..., gt=0.0)
    range_low: float = Field(..., gt=0.0)
    range_position_pct: float = Field(..., ge=0.0, le=100.0)


class OrderflowState(BaseModel):
    taker_buy_vol: Optional[float] = Field(default=None, ge=0.0)
    taker_sell_vol: Optional[float] = Field(default=None, ge=0.0)
    taker_ratio: Optional[float] = Field(default=None, ge=0.0)
    flow_bias: str
    cvd: Optional[float] = None
    cvd_delta: Optional[float] = None
    cvd_slope: Optional[float] = None
    cvd_divergence: str = "UNKNOWN"


class DerivativesState(BaseModel):
    open_interest: Optional[float] = Field(default=None, ge=0.0)
    delta_oi: Optional[float] = None
    delta_oi_pct: Optional[float] = None
    oi_zscore: Optional[float] = None
    funding_rate: Optional[float] = None
    funding_zscore: Optional[float] = None
    long_short_ratio: Optional[float] = Field(default=None, ge=0.0)
    liquidation_squeeze_index: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    liquidation_long_usd: Optional[float] = Field(default=None, ge=0.0)
    liquidation_short_usd: Optional[float] = Field(default=None, ge=0.0)


class LiquidityState(BaseModel):
    bid_depth_02_usd: Optional[float] = Field(default=None, ge=0.0)
    ask_depth_02_usd: Optional[float] = Field(default=None, ge=0.0)
    total_depth_02_usd: Optional[float] = Field(default=None, ge=0.0)
    depth_imbalance: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    estimated_slippage_10k_pct: Optional[float] = Field(default=None, ge=0.0)
    estimated_slippage_50k_pct: Optional[float] = Field(default=None, ge=0.0)
    state_tier: LiquidityStateEnum = LiquidityStateEnum.UNKNOWN
    bid_wall_price: Optional[float] = Field(default=None, gt=0.0)
    ask_wall_price: Optional[float] = Field(default=None, gt=0.0)


class TokenSecurityState(BaseModel):
    is_honeypot: Optional[bool] = None
    buy_tax: Optional[float] = Field(default=None, ge=0.0)
    sell_tax: Optional[float] = Field(default=None, ge=0.0)
    is_mintable: Optional[bool] = None
    is_blacklisted: Optional[bool] = None
    top10_holder_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    liquidity_locked: Optional[bool] = None
    security_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)


class SentimentState(BaseModel):
    sentiment_score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    bullish_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    bearish_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sentiment_bias: str = "UNKNOWN"


class MacroState(BaseModel):
    btc_correlation: Optional[float] = Field(default=None, ge=-1.0, le=1.0)
    btc_beta: Optional[float] = None
    macro_regime: str = "UNKNOWN"
    macro_event_risk: str = "UNKNOWN"


class DefiState(BaseModel):
    dex_liquidity_usd: Optional[float] = Field(default=None, ge=0.0)
    tvl_usd: Optional[float] = Field(default=None, ge=0.0)
    lending_utilization_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)


class MarketResult(BaseModel):
    """LOGIC 1 output: market observations only, never a bot verdict."""

    schema_version: str = "market_result.v1"
    methodology_version: str = "market_features.v1"
    asset_id: str
    symbol: str
    venue: str
    venue_type: str
    chain: Optional[str] = None
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000), ge=0)
    as_of_ms: int = Field(default_factory=lambda: int(time.time() * 1000), ge=0)
    freshness_ms: int = Field(default=0, ge=0)
    data_quality_score: float = Field(..., ge=0.0, le=1.0)
    data_quality: DataQualitySummary

    price_state: PriceState
    structure_state: StructureState
    orderflow_state: OrderflowState
    derivatives_state: Optional[DerivativesState] = None
    liquidity_state: LiquidityState
    token_state: Optional[TokenSecurityState] = None
    sentiment_state: Optional[SentimentState] = None
    macro_state: Optional[MacroState] = None
    defi_state: Optional[DefiState] = None

    @field_validator("symbol", "venue_type")
    @classmethod
    def uppercase_identity(cls, value: str) -> str:
        return value.upper()
