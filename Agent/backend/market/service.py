from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from Agent.backend.infra.config import config
from Agent.backend.infra.quality import (
    EvaluationMode,
    SourceQuality,
    SourceStatus,
    grade_source,
    summarize_quality,
)
from Agent.backend.market.features.derivatives import DerivativesFeatureExtractor
from Agent.backend.market.features.liquidity import LiquidityFeatureExtractor
from Agent.backend.market.features.orderflow import OrderflowFeatureExtractor
from Agent.backend.market.features.price import PriceFeatureExtractor
from Agent.backend.market.features.structure import StructureFeatureExtractor
from Agent.backend.market.schemas.market_result import (
    DefiState,
    MacroState,
    MarketResult,
    SentimentState,
    TokenSecurityState,
)
from Agent.backend.sources.market_source import (
    FileMarketDataSource,
    MarketDataSource,
    MarketDataUnavailableError,
)

# Re-exported so every existing `from Agent.backend.market.service import
# MarketDataUnavailableError` (pipeline.py, agent_server.py, universe/registry.py,
# the QC reporting modules, tests) keeps resolving to the same class unchanged --
# it is defined in sources/market_source.py to avoid a circular import (that
# module needs no import back from this one).
__all__ = ["MarketDataUnavailableError", "MarketService"]


class MarketService:
    """LOGIC 1: normalize crawled observations into a provenance-aware MarketResult."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        evaluation_mode: EvaluationMode = EvaluationMode.SNAPSHOT,
        market_source: Optional[MarketDataSource] = None,
    ) -> None:
        self.data_dir = data_dir or Path(config.DATA_DIR)
        self.evaluation_mode = evaluation_mode
        # Defaults to the on-disk crawl dataset, unchanged from before this
        # source was made pluggable. Pass e.g. a LiveMarketDataSource to read
        # straight from OKX instead -- see Agent/backend/sources/market_source.py.
        self.market_source = market_source or FileMarketDataSource(self.data_dir)

    @staticmethod
    def _clean_symbol(symbol: str) -> str:
        clean = symbol.split("-")[0].split("/")[0].strip().upper()
        if not clean or not clean.replace("_", "").isalnum():
            raise ValueError(f"Invalid symbol: {symbol!r}")
        return clean

    @staticmethod
    def _observed_at(payload: Dict[str, Any]) -> Optional[int]:
        raw = (
            payload.get("updated_at")
            or payload.get("timestamp")
            or payload.get("ts")
            or payload.get("observed_at")
        )
        try:
            return int(raw) if raw is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _token_state(payload: Dict[str, Any]) -> TokenSecurityState:
        """Only fields the provider actually answered; a null stays null."""
        data = (payload or {}).get("security", payload or {})
        return TokenSecurityState(
            is_honeypot=data.get("is_honeypot"),
            buy_tax=data.get("buy_tax"),
            sell_tax=data.get("sell_tax"),
            is_mintable=data.get("is_mintable"),
            is_blacklisted=data.get("is_blacklisted"),
            top10_holder_pct=data.get("top10_holder_pct"),
            liquidity_locked=data.get("liquidity_locked"),
            security_score=data.get("security_score"),
        )

    @staticmethod
    def _macro_state(payload: Dict[str, Any]) -> MacroState:
        data = (payload or {}).get("macro", payload or {})
        return MacroState(
            btc_correlation=data.get("btc_correlation"),
            btc_beta=data.get("btc_beta"),
            macro_regime=data.get("macro_regime") or "UNKNOWN",
            macro_event_risk=data.get("macro_event_risk") or "UNKNOWN",
        )

    @staticmethod
    def _sentiment_state(payload: Dict[str, Any]) -> Optional[SentimentState]:
        if not payload:
            return None
        data = payload.get("sentiment", payload)
        score_raw = data.get("score", data.get("sentiment_score"))
        ls_raw = data.get("ls_ratio")
        ratio = float(ls_raw) if ls_raw not in (None, "") else None
        bullish = ratio / (1.0 + ratio) if ratio is not None and ratio >= 0 else None
        bearish = 1.0 - bullish if bullish is not None else None
        score = (
            float(score_raw)
            if score_raw is not None
            else (bullish * 100.0 if bullish is not None else None)
        )
        label = str(
            data.get("sentiment_label", data.get("sentiment_bias", "UNKNOWN"))
        ).split(" (")[0]
        return SentimentState(
            sentiment_score=score,
            bullish_ratio=bullish,
            bearish_ratio=bearish,
            sentiment_bias=label,
        )

    def get_market_result(
        self,
        symbol: str,
        venue_type: Optional[str] = None,
        as_of_ms: Optional[int] = None,
    ) -> MarketResult:
        clean = self._clean_symbol(symbol)
        resolved_venue_type = self.market_source.resolve_venue(clean, venue_type)
        wall_clock = as_of_ms if as_of_ms is not None else int(time.time() * 1000)
        is_dex = resolved_venue_type == "DEX"

        candles_payload, candles_error = self.market_source.get_candles(
            clean, resolved_venue_type
        )
        raw_candles = candles_payload.get("candles", [])
        candles = raw_candles if isinstance(raw_candles, list) else []
        if candles_error or not candles:
            detail = candles_error or "candles list is empty"
            raise MarketDataUnavailableError(
                f"Cannot build MarketResult for {clean}: {detail}"
            )
        candles = sorted(candles, key=lambda row: int(row.get("timestamp", 0)))
        last_candle_ts = int(candles[-1].get("timestamp", 0))
        last_price = float(candles[-1].get("close", 0.0))
        if last_price <= 0:
            raise MarketDataUnavailableError(
                f"Cannot build MarketResult for {clean}: invalid last close"
            )

        orderbook, orderbook_error = self.market_source.get_orderbook(
            clean, resolved_venue_type
        )
        oi, oi_error = self.market_source.get_open_interest(clean, resolved_venue_type)
        taker, taker_error = self.market_source.get_taker_volume(
            clean, resolved_venue_type
        )
        sentiment, sentiment_error = self.market_source.get_sentiment(
            clean, resolved_venue_type
        )
        ticks, ticks_error = self.market_source.get_ticks(clean, resolved_venue_type)
        pool, pool_error = self.market_source.get_pool_liquidity(
            clean, resolved_venue_type
        )
        security, security_error = self.market_source.get_token_security(
            clean, resolved_venue_type
        )
        macro, macro_error = self.market_source.get_macro_context(
            clean, resolved_venue_type
        )

        bid = float(orderbook["bids"][0][0]) if orderbook.get("bids") else None
        ask = float(orderbook["asks"][0][0]) if orderbook.get("asks") else None
        raw_ticks = ticks.get("ticks", [])
        tick_rows = raw_ticks if isinstance(raw_ticks, list) else []
        tick_times: List[int] = []
        for tick in tick_rows:
            try:
                tick_times.append(int(tick.get("ts", 0)))
            except (TypeError, ValueError):
                continue

        graded_inputs = [
            (
                "ohlcv_1h",
                candles_payload,
                candles_error,
                last_candle_ts,
                len(candles),
                False,
            ),
            (
                "orderbook_l2",
                orderbook,
                orderbook_error,
                self._observed_at(orderbook),
                len(orderbook.get("bids", [])) + len(orderbook.get("asks", [])),
                is_dex,
            ),
            (
                "dex_pool_liquidity",
                pool,
                pool_error,
                pool.get("observed_at") if pool else None,
                1 if pool else 0,
                not is_dex,
            ),
            ("taker_flow", taker, taker_error, self._observed_at(taker), 0, is_dex),
            ("derivatives_oi", oi, oi_error, self._observed_at(oi), 0, is_dex),
            (
                "sentiment",
                sentiment,
                sentiment_error,
                self._observed_at(sentiment),
                0,
                is_dex,
            ),
            (
                "dex_ticks",
                ticks,
                ticks_error,
                max(tick_times) if tick_times else None,
                len(tick_rows),
                not is_dex,
            ),
            (
                "token_security",
                security,
                security_error,
                self._observed_at(security),
                0,
                not is_dex,
            ),
            ("macro", macro, macro_error, self._observed_at(macro), 0, False),
        ]
        observed_times = [
            observed
            for _, _, error, observed, _, skip in graded_inputs
            if not skip and not error and observed is not None
        ]
        anchor = max(observed_times) if observed_times else last_candle_ts

        sources: List[SourceQuality] = []
        for name, _, error, observed, count, skip in graded_inputs:
            if skip:
                sources.append(
                    SourceQuality(
                        source=name,
                        status=SourceStatus.NOT_APPLICABLE,
                        reason="not applicable to venue",
                    )
                )
            elif error:
                sources.append(
                    SourceQuality(
                        source=name,
                        status=SourceStatus.MISSING
                        if error == "file not found"
                        else SourceStatus.INVALID,
                        reason=error,
                    )
                )
            else:
                sources.append(
                    grade_source(
                        name, observed, anchor, wall_clock, self.evaluation_mode, count
                    )
                )
        quality = summarize_quality(sources, self.evaluation_mode, anchor, wall_clock)
        benchmark = candles_payload.get("price_benchmark")
        if is_dex and benchmark:
            quality.warnings.append(
                f"DEX candles are a CEX benchmark proxy ({benchmark}), not on-chain pool prices"
            )
        if is_dex and not pool:
            quality.warnings.append(
                "DEX pool liquidity (TVL, reserves, route depth) has not been collected; "
                "depth-dependent dimensions stay UNKNOWN"
            )
        freshness_ms = max(
            (source.age_ms for source in sources if source.age_ms is not None),
            default=0,
        )

        venue_raw = (
            candles_payload.get("dex_pool", candles_payload.get("exchange", "DEX"))
            if is_dex
            else candles_payload.get("exchange", "OKX")
        )
        venue = str(venue_raw).upper()
        chain = str(
            candles_payload.get("chain", "OFFCHAIN" if not is_dex else "UNKNOWN")
        ).upper()

        pool_vol = (
            float(pool.get("volume_24h_usd") or 0.0) if (is_dex and pool) else None
        )
        pool_spread = (
            float(pool.get("fee_tier_pct") or 0.003) if (is_dex and pool) else None
        )

        return MarketResult(
            asset_id=f"{resolved_venue_type}_{clean}_{re.sub(r'[^A-Z0-9]+', '_', venue).strip('_')}",
            symbol=clean,
            venue=venue,
            venue_type=resolved_venue_type,
            chain=chain,
            timestamp=wall_clock,
            as_of_ms=anchor,
            freshness_ms=freshness_ms,
            data_quality_score=quality.overall_score,
            data_quality=quality,
            price_state=PriceFeatureExtractor.extract(
                last_price,
                bid,
                ask,
                candles,
                override_volume_24h_usd=pool_vol,
                override_spread_pct=pool_spread,
            ),
            structure_state=StructureFeatureExtractor.extract(candles, last_price),
            orderflow_state=OrderflowFeatureExtractor.from_ticks(tick_rows)
            if is_dex
            else OrderflowFeatureExtractor.extract(taker),
            derivatives_state=DerivativesFeatureExtractor.extract(oi, sentiment)
            if not is_dex
            else None,
            liquidity_state=LiquidityFeatureExtractor.extract_from_pool(
                pool, last_price
            )
            if (is_dex and pool)
            else LiquidityFeatureExtractor.extract(orderbook, last_price),
            token_state=self._token_state(security) if is_dex else None,
            sentiment_state=self._sentiment_state(sentiment),
            macro_state=self._macro_state(macro),
            defi_state=DefiState() if is_dex else None,
        )
