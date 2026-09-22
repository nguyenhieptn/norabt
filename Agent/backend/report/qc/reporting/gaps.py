from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from Agent.backend.market.schemas.market_result import MarketResult



class EvidenceGap(BaseModel):
    """One missing input, and what collecting it would unlock."""

    gap_id: str
    scope: str
    evidence: str
    detail: str
    unlocks: List[str] = Field(default_factory=list)
    affected_bots: List[str] = Field(default_factory=list)
    priority: str = "MEDIUM"

    @property
    def weight(self) -> int:
        return len(self.unlocks) * max(1, len(self.affected_bots))


def build_gaps(rows, markets: Dict[str, Optional[MarketResult]]) -> List[EvidenceGap]:
    """Derive the collection backlog from what the assessment could not evaluate."""
    gaps: Dict[str, EvidenceGap] = {}

    def add(
        gap_id: str,
        scope: str,
        evidence: str,
        detail: str,
        unlocks: List[str],
        bot: Optional[str] = None,
    ) -> None:
        gap = gaps.get(gap_id)
        if gap is None:
            gap = EvidenceGap(
                gap_id=gap_id,
                scope=scope,
                evidence=evidence,
                detail=detail,
                unlocks=unlocks,
            )
            gaps[gap_id] = gap
        if bot and bot not in gap.affected_bots:
            gap.affected_bots.append(bot)

    for row in rows:
        if row.status != "EVALUATED":
            continue
        who = row.nick_name

        if not row.market_available:
            add(
                f"market:{row.traded_symbol}",
                f"Market {row.traded_symbol}",
                "OHLCV + order book for the instrument the bot is trading",
                f"The bot trades {row.traded_symbol} but there is no market data yet for this symbol.",
                ["market_alignment", "liquidity_execution"],
                who,
            )
        if row.positions_outside_ledger_universe:
            add(
                "positions:outside_ledger_universe",
                "Positions outside the ledger",
                "A deeper ledger, or a complete instrument list",
                f"{row.positions_outside_ledger_universe} positions do not match any "
                "instrument the bot has recently closed; a deeper history is needed to widen "
                "the inference candidate set.",
                ["market_alignment", "liquidity_execution"],
                who,
            )
        if row.unknown_positions_count:
            if row.instrument_withheld_upstream:
                add(
                    "positions:instrument_id_upstream",
                    "Open positions (not disclosed by OKX)",
                    "instId — could not be collected",
                    "OKX returns an empty instId for this trader. The system inferred "
                    f"{row.inferred_positions_count} positions from implied price movement; "
                    f"{row.unknown_positions_count} positions remain unattributed.",
                    ["market_alignment", "liquidity_execution"],
                    who,
                )
            else:
                add(
                    "positions:instrument_id",
                    "Open positions",
                    "instId for each open position",
                    "Positions have side/margin/leverage but no instrument code, so exposure cannot be attributed to a market.",
                    ["market_alignment", "liquidity_execution", "leverage_exposure"],
                    who,
                )
        if row.capital_basis == "UNAVAILABLE":
            add(
                "capital:equity_history",
                "Account capital",
                "Equity history or deposit/withdrawal history",
                "AUM is smaller than cumulative PnL, so starting capital cannot be reconstructed; historical drawdown can only be reported in USDT.",
                ["drawdown_risk"],
                who,
            )
        if row.reconciliation_status == "IDENTITY_MISMATCH":
            add(
                "ledger:wrong_owner",
                "Ledger belongs to the wrong owner",
                "The correct ledger for this bot",
                "The ledger file belongs to a different uniqueCode and was rejected; the bot "
                "is being assessed with no trade history.",
                [
                    "performance_quality",
                    "return_r_quality",
                    "tail_risk",
                    "drawdown_risk",
                ],
                who,
            )
        if row.reconciliation_status == "PARTIAL_LEDGER":
            add(
                "ledger:full_history",
                "Ledger",
                "Full history covering leadDays",
                "The ledger only covers part of the bot's active period; deeper pagination "
                "is needed to cover the full history.",
                ["performance_quality", "tail_risk"],
                who,
            )
        if row.reconciliation_status == "MISMATCH":
            add(
                "ledger:completeness",
                "Ledger",
                "A complete ledger matching total PnL",
                "The ledger's PnL differs from the reported total, meaning the ledger is incomplete.",
                ["performance_quality", "return_r_quality", "tail_risk"],
                who,
            )
        if "strategy_drift" in (row.unknown_dimensions or []):
            add(
                "bot:declared_strategy",
                "Declared strategy",
                "The bot's own declared strategy",
                "There is no declared strategy to compare against observed behavior.",
                ["strategy_drift"],
                who,
            )

    for symbol, market in markets.items():
        if market is None:
            continue
        for source in market.data_quality.missing_sources:
            unlocks = {
                "orderbook_l2": ["liquidity_execution"],
                "taker_flow": ["market_alignment"],
                "derivatives_oi": ["leverage_exposure"],
                "macro": ["portfolio_risk"],
                "token_security": ["portfolio_risk"],
                "sentiment": ["market_alignment"],
            }.get(source, [])
            add(
                f"market_source:{symbol}:{source}",
                f"Market {symbol}",
                source,
                f"Source {source} has not been collected for {symbol}.",
                unlocks,
            )
        for source in market.data_quality.stale_sources:
            add(
                f"market_stale:{symbol}:{source}",
                f"Market {symbol}",
                f"{source} (stale)",
                f"Source {source} has drifted too far from {symbol}'s data timestamp; it needs to be re-crawled on the same cadence.",
                ["liquidity_execution"] if "orderbook" in source else [],
            )

    ordered = sorted(gaps.values(), key=lambda gap: -gap.weight)
    for gap in ordered:
        gap.priority = (
            "HIGH" if gap.weight >= 4 else "MEDIUM" if gap.weight >= 2 else "LOW"
        )
    return ordered
