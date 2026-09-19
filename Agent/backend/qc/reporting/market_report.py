from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.market.service import MarketDataUnavailableError, MarketService
from Agent.backend.qc.reporting.reasons import (
    FLOW_VI,
    LIQ_VI,
    TREND_VI,
    VOL_VI,
    regime_label_vi,
)
from Agent.backend.qc.reporting.market_posture import (
    POSTURE_GROWTH,
    POSTURE_RISK,
    POSTURE_STABLE,
    POSTURE_UNCLEAR,
    assess as assess_posture,
)
from Agent.backend.universe.registry import UniverseRegistry


class MarketRegimeRow(BaseModel):
    """BƯỚC 1 — một thị trường đã được quan sát và phân loại chế độ."""

    symbol: str
    venue: str
    venue_type: str
    regime: str
    trend: str
    volatility: str
    liquidity_tier: str
    flow_bias: str
    last_price: float
    atr_pct: Optional[float] = None
    range_position_pct: Optional[float] = None
    keltner_width_zscore: Optional[float] = None
    depth_02_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    data_quality: float = Field(..., ge=0.0, le=1.0)
    freshness_hours: float = Field(..., ge=0.0)
    posture: str = POSTURE_UNCLEAR
    posture_evidence: List[str] = Field(default_factory=list)
    risk_score: int = 0
    growth_score: int = 0
    stability_score: int = 0
    eligible: bool = False
    eligibility_reason: str = "UNKNOWN"
    bots_trading: int = Field(default=0, ge=0)
    missing_sources: List[str] = Field(default_factory=list)
    note: str = ""


class MarketRegimeReport(BaseModel):
    schema_version: str = "market_regime_report.v1"
    generated_at_ms: int
    evaluation_mode: EvaluationMode
    markets_observed: int = Field(..., ge=0)
    markets_eligible: int = Field(..., ge=0)
    regime_summary: Dict[str, int] = Field(default_factory=dict)
    posture_summary: Dict[str, int] = Field(default_factory=dict)
    rows: List[MarketRegimeRow] = Field(default_factory=list)
    failures: Dict[str, str] = Field(default_factory=dict)


class MarketRegimeService:
    """Chạy Logic 1 trên toàn bộ thị trường có dữ liệu và xếp theo chế độ."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        evaluation_mode: EvaluationMode = EvaluationMode.SNAPSHOT,
    ) -> None:
        self.data_dir = data_dir or Path(config.DATA_DIR)
        self.evaluation_mode = evaluation_mode
        self.market_service = MarketService(self.data_dir, evaluation_mode)

    # Ledgers record the underlying a bot actually traded, so a wrapped DEX
    # market has to count its underlying's bots or it reads as untraded.
    WRAPPED_UNDERLYING = {"WBTC": "BTC", "WETH": "ETH"}

    def _bots_per_symbol(self) -> Dict[str, int]:
        """How many crawled bots actually trade each market, read off the ledgers.

        Cheaper than a full cohort assessment, which this report does not need,
        and it counts the market a bot really traded rather than its folder name.
        """
        counts: Dict[str, int] = {}
        for path in self.data_dir.rglob("bot_*/trade_list.json"):
            try:
                ledger = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            symbols = {
                str(trade.get("instId", "")).split("-")[0].upper()
                for trade in ledger.get("closed_trades") or []
                if trade.get("instId")
            }
            for symbol in symbols:
                counts[symbol] = counts.get(symbol, 0) + 1
        for wrapped, underlying in self.WRAPPED_UNDERLYING.items():
            if underlying in counts:
                counts.setdefault(wrapped, counts[underlying])
        return counts

    def build(
        self,
        as_of_ms: Optional[int] = None,
        bots_per_symbol: Optional[Dict[str, int]] = None,
        only_symbols: Optional[set] = None,
    ) -> MarketRegimeReport:
        now = as_of_ms if as_of_ms is not None else int(time.time() * 1000)
        registry = UniverseRegistry(self.data_dir)
        eligible_ids = {asset.asset_id for asset in registry.list_all()}
        rejections = registry.list_rejections()
        counts = bots_per_symbol or self._bots_per_symbol()

        rows: List[MarketRegimeRow] = []
        failures: Dict[str, str] = {}
        for venue_type in ("CEX", "DEX"):
            root = self.data_dir / venue_type.lower()
            if not root.is_dir():
                continue
            for asset_dir in sorted(p for p in root.iterdir() if p.is_dir()):
                if not (asset_dir / "market").is_dir():
                    continue
                if only_symbols and asset_dir.name not in only_symbols:
                    continue
                try:
                    market = self.market_service.get_market_result(
                        asset_dir.name, venue_type=venue_type, as_of_ms=now
                    )
                except (MarketDataUnavailableError, ValueError) as exc:
                    failures[f"{venue_type}/{asset_dir.name}"] = str(exc)
                    continue

                structure = market.structure_state
                eligible = market.asset_id in eligible_ids
                reason = rejections.get(
                    market.asset_id, "ELIGIBLE" if eligible else "NOT_IN_UNIVERSE"
                )
                atr_pct = (
                    structure.atr_14 / market.price_state.last_price * 100.0
                    if market.price_state.last_price
                    else None
                )
                note = cls_note(market, eligible, reason)
                # Answers the three questions this step is asked: where the risk
                # is, where something is growing, where it is steady.
                posture = assess_posture(market)
                evidence = {
                    POSTURE_RISK: posture.risk_flags,
                    POSTURE_GROWTH: posture.growth_flags,
                    POSTURE_STABLE: posture.stability_flags,
                }.get(posture.posture, [])
                rows.append(
                    MarketRegimeRow(
                        symbol=market.symbol,
                        venue=market.venue,
                        venue_type=market.venue_type,
                        regime=regime_label_vi(
                            structure.trend_state.value,
                            structure.volatility_state.value,
                        ),
                        posture=posture.posture,
                        posture_evidence=evidence,
                        risk_score=posture.risk_score,
                        growth_score=posture.growth_score,
                        stability_score=posture.stability_score,
                        trend=structure.trend_state.value,
                        volatility=structure.volatility_state.value,
                        liquidity_tier=market.liquidity_state.state_tier.value,
                        flow_bias=market.orderflow_state.flow_bias,
                        last_price=market.price_state.last_price,
                        atr_pct=atr_pct,
                        range_position_pct=structure.range_position_pct,
                        keltner_width_zscore=structure.keltner_width_zscore,
                        depth_02_usd=market.liquidity_state.total_depth_02_usd,
                        volume_24h_usd=market.price_state.volume_24h_usd,
                        data_quality=market.data_quality_score,
                        freshness_hours=market.freshness_ms / 3_600_000.0,
                        eligible=eligible,
                        eligibility_reason=reason,
                        bots_trading=counts.get(market.symbol, 0),
                        missing_sources=market.data_quality.missing_sources,
                        note=note,
                    )
                )

        rows.sort(key=lambda r: (-r.bots_trading, not r.eligible, r.symbol))
        summary: Dict[str, int] = {}
        postures: Dict[str, int] = {}
        for row in rows:
            summary[row.regime] = summary.get(row.regime, 0) + 1
            postures[row.posture] = postures.get(row.posture, 0) + 1
        return MarketRegimeReport(
            generated_at_ms=now,
            evaluation_mode=self.evaluation_mode,
            markets_observed=len(rows),
            markets_eligible=sum(1 for r in rows if r.eligible),
            regime_summary=summary,
            posture_summary=postures,
            rows=rows,
            failures=failures,
        )


def cls_note(market, eligible: bool, reason: str) -> str:
    """Một câu tiếng Việt nói rõ thị trường này đang ở trạng thái nào."""
    structure = market.structure_state
    bits = [
        f"Price {market.price_state.last_price:,.4g}",
        TREND_VI.get(structure.trend_state.value, "unclear"),
        VOL_VI.get(structure.volatility_state.value, ""),
        LIQ_VI.get(market.liquidity_state.state_tier.value, ""),
        FLOW_VI.get(market.orderflow_state.flow_bias, ""),
    ]
    text = ", ".join(b for b in bits if b)
    if not eligible:
        explain = {
            "DEX_POOL_LIQUIDITY_NOT_COLLECTED": "pool liquidity has not been collected yet, so it is not eligible for monitoring",
            "NOT_IN_UNIVERSE": "not yet in the universe",
        }.get(reason)
        if explain is None and reason.startswith("UNKNOWN_EVIDENCE"):
            explain = "missing order book depth or spread"
        elif explain is None and reason.startswith("DATA_STALE"):
            explain = "data has drifted too far from the snapshot timestamp"
        elif explain is None and reason.startswith("DATA_QUALITY"):
            explain = "data quality is below threshold"
        text += f". Not eligible: {explain or reason}"
    return text + "."
