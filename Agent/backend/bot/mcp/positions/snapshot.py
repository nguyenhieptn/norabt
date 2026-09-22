from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from Agent.backend.bot.mcp.inference.public_signals import SubPositionClock
from Agent.backend.bot.mcp.schemas.bot_result import OpenPosition, PositionSide


class PositionSnapshot(BaseModel):
    """Aggregate of open positions, keeping attributed and unattributed risk apart."""

    positions: List[OpenPosition] = Field(default_factory=list)
    declared_count: int = Field(default=0, ge=0)
    parsed_count: int = Field(default=0, ge=0)
    attributed_count: int = Field(default=0, ge=0)
    observed_count: int = Field(default=0, ge=0)
    inferred_count: int = Field(default=0, ge=0)
    outside_universe_count: int = Field(default=0, ge=0)
    unattributed_count: int = Field(default=0, ge=0)
    sides_known_count: int = Field(default=0, ge=0)
    aggregate_side: PositionSide = PositionSide.FLAT
    gross_exposure: Optional[float] = None
    net_exposure: Optional[float] = None
    long_notional: Optional[float] = None
    short_notional: Optional[float] = None
    used_margin: Optional[float] = None
    max_leverage: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    exposure_by_symbol: Dict[str, float] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class PositionSnapshotParser:
    """Read both OKX position payload shapes without discarding partial evidence."""

    @staticmethod
    def _float(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _side(raw: Any) -> PositionSide:
        text = str(raw or "").strip().lower()
        if text in ("long", "buy"):
            return PositionSide.LONG
        if text in ("short", "sell"):
            return PositionSide.SHORT
        if text == "net":
            return PositionSide.NET
        return PositionSide.UNKNOWN

    @staticmethod
    def _base_symbol(instrument: Optional[str]) -> Optional[str]:
        if not instrument:
            return None
        base = str(instrument).split("-")[0].split("/")[0].strip().upper()
        return base or None

    @classmethod
    def _parse_one(cls, raw: Dict[str, Any], index: int) -> OpenPosition:
        instrument = raw.get("instId") or None
        symbol = cls._base_symbol(instrument) or cls._base_symbol(raw.get("asset"))
        source = "OBSERVED" if symbol else "NONE"
        attribution = raw.get("attribution") or {}
        verdict = attribution.get("verdict")
        if symbol is None:
            inferred = cls._base_symbol(raw.get("inferred_instrument"))
            if inferred:
                # Inference is evidence, but it is never recorded as an observation.
                symbol = inferred
                instrument = raw.get("inferred_instrument")
                source = "INFERRED"
        side = cls._side(raw.get("posSide") or raw.get("direction") or raw.get("side"))
        leverage = cls._float(raw.get("lever", raw.get("leverage")))
        margin = cls._float(raw.get("margin", raw.get("margin_usdt")))
        raw_size = cls._float(raw.get("subPos", raw.get("position_size")))
        size = abs(raw_size) if raw_size is not None else None
        entry = cls._float(raw.get("openAvgPx", raw.get("entry_price")))
        mark = cls._float(raw.get("markPx", raw.get("current_mark_price")))
        upl = cls._float(raw.get("upl", raw.get("unrealized_pnl_usdt")))
        upl_ratio = cls._float(raw.get("uplRatio", raw.get("unrealized_pnl_ratio")))

        # Contract sizes differ per instrument, so margin x leverage is the reliable
        # notional; size x price would need a contract multiplier we do not have.
        notional = cls._float(raw.get("notionalUsd", raw.get("notional")))
        if notional is None and margin is not None and leverage is not None:
            notional = margin * leverage

        open_time = cls._float(raw.get("openTime"))
        open_time_source = "PUBLISHED" if open_time else None
        if not open_time:
            decoded = SubPositionClock.open_time_ms(raw.get("subPosId"))
            if decoded:
                open_time = float(decoded)
                open_time_source = "SUBPOS_ID_SNOWFLAKE"
        return OpenPosition(
            position_id=str(
                raw.get("subPosId", raw.get("trade_id", f"position_{index + 1}"))
            ),
            attribution_source=source,
            attribution_verdict=verdict,
            attribution_candidates=list(attribution.get("candidates") or []),
            implied_price_move=attribution.get("implied_price_move"),
            open_time=int(open_time) if open_time else None,
            open_time_source=open_time_source,
            instrument=str(instrument) if instrument else None,
            symbol=symbol,
            side=side,
            leverage=leverage,
            margin=margin,
            contract_size=size,
            notional=notional,
            entry_price=entry,
            mark_price=mark,
            unrealized_pnl=upl,
            unrealized_pnl_pct=upl_ratio * 100.0 if upl_ratio is not None else None,
        )

    @classmethod
    def parse(cls, payload: Dict[str, Any]) -> PositionSnapshot:
        raw_positions = payload.get("open_positions")
        rows = raw_positions if isinstance(raw_positions, list) else []
        declared = payload.get("open_positions_count", len(rows))
        try:
            declared_count = max(0, int(declared))
        except (TypeError, ValueError):
            declared_count = len(rows)

        positions = [
            cls._parse_one(row, index)
            for index, row in enumerate(rows)
            if isinstance(row, dict)
        ]
        warnings: List[str] = []
        if declared_count > len(positions):
            warnings.append(
                f"{declared_count - len(positions)} open positions are declared but absent "
                f"from the payload"
            )

        if not positions and declared_count == 0:
            return PositionSnapshot(declared_count=0, aggregate_side=PositionSide.FLAT)

        attributed = [p for p in positions if p.symbol]
        observed = [p for p in positions if p.attribution_source == "OBSERVED"]
        inferred = [p for p in positions if p.attribution_source == "INFERRED"]
        outside = [
            p for p in positions if p.attribution_verdict == "OUTSIDE_LEDGER_UNIVERSE"
        ]
        sides_known = [p for p in positions if p.side != PositionSide.UNKNOWN]
        with_notional = [p for p in positions if p.notional is not None]

        gross = sum(p.notional or 0.0 for p in with_notional) or None
        long_notional = (
            sum(p.notional or 0.0 for p in with_notional if p.side == PositionSide.LONG)
            if with_notional
            else None
        )
        short_notional = (
            sum(
                p.notional or 0.0 for p in with_notional if p.side == PositionSide.SHORT
            )
            if with_notional
            else None
        )
        net = (
            long_notional - short_notional
            if long_notional is not None and short_notional is not None
            else None
        )

        if not sides_known:
            aggregate = PositionSide.UNKNOWN
        else:
            distinct = {p.side for p in sides_known}
            if len(distinct) == 1:
                aggregate = distinct.pop()
            else:
                aggregate = PositionSide.NET
            if len(sides_known) < declared_count:
                warnings.append(
                    f"Only {len(sides_known)}/{declared_count} open positions expose a side"
                )

        exposure_by_symbol: Dict[str, float] = {}
        for position in attributed:
            if position.notional is None or position.symbol is None:
                continue
            exposure_by_symbol[position.symbol] = (
                exposure_by_symbol.get(position.symbol, 0.0) + position.notional
            )

        unattributed = (
            len(positions) - len(attributed) + max(0, declared_count - len(positions))
        )
        if inferred:
            warnings.append(
                f"{len(inferred)}/{declared_count} positions were attributed by implied "
                f"price move rather than a published instId"
            )
        if outside:
            warnings.append(
                f"{len(outside)}/{declared_count} positions match no instrument in the "
                f"bot's own ledger: it is trading something it has not closed recently"
            )
        if unattributed:
            withheld = not observed
            warnings.append(
                f"{unattributed}/{declared_count} open positions carry no instrument id; "
                + (
                    "OKX does not publish instId for this trader, so this cannot be "
                    "fixed by re-crawling"
                    if withheld
                    else "exposure cannot be attributed to a market"
                )
            )

        margins = [p.margin for p in positions if p.margin is not None]
        levers = [p.leverage for p in positions if p.leverage is not None]
        upls = [p.unrealized_pnl for p in positions if p.unrealized_pnl is not None]

        return PositionSnapshot(
            positions=positions,
            declared_count=declared_count,
            parsed_count=len(positions),
            attributed_count=len(attributed),
            observed_count=len(observed),
            inferred_count=len(inferred),
            outside_universe_count=len(outside),
            unattributed_count=unattributed,
            sides_known_count=len(sides_known),
            aggregate_side=aggregate,
            gross_exposure=gross,
            net_exposure=net,
            long_notional=long_notional,
            short_notional=short_notional,
            used_margin=sum(margins) if len(margins) == len(positions) else None,
            max_leverage=max(levers) if levers else None,
            unrealized_pnl=sum(upls) if upls else None,
            exposure_by_symbol=exposure_by_symbol,
            warnings=warnings,
        )
