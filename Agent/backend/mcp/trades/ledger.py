from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from Agent.backend.mcp.schemas.bot_result import (
    PositionSide,
    RiskMeasurementMode,
    TradeLedgerItem,
)


@dataclass(frozen=True)
class LedgerParseResult:
    trades: List[TradeLedgerItem]
    rejected_count: int
    warnings: List[str]


class TradeLedgerManager:
    """Normalize OKX copy-trading records into a chronological, deduplicated ledger."""

    @staticmethod
    def _float(value: Any) -> Optional[float]:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _int(value: Any) -> Optional[int]:
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _timestamp_ms(value: Any) -> Optional[int]:
        """Accept epoch milliseconds or an ISO-like UTC string."""
        if value in (None, ""):
            return None
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value).strip()
        if text.isdigit():
            return int(text)
        cleaned = text.replace("UTC", "").strip().replace("Z", "")
        for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                parsed = datetime.strptime(cleaned, pattern).replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue
            return int(parsed.timestamp() * 1000)
        return None

    @classmethod
    def parse_trade_list_with_diagnostics(
        cls, raw_data: Dict[str, Any]
    ) -> LedgerParseResult:
        rows = (
            raw_data.get("closed_trades")
            or raw_data.get("history_trades")
            or raw_data.get("trades")
            or []
        )
        if not isinstance(rows, list):
            return LedgerParseResult(
                [], 0, ["closed_trades/history_trades is not a list"]
            )

        parsed: Dict[str, TradeLedgerItem] = {}
        rejected = 0
        warnings: List[str] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                rejected += 1
                continue
            trade_id = str(
                row.get("subPosId", row.get("trade_id", f"trade_{index + 1}"))
            )
            open_time = cls._timestamp_ms(
                row.get("openTime", row.get("cTime", row.get("open_time")))
            )
            close_time = cls._timestamp_ms(
                row.get("closeTime", row.get("uTime", row.get("close_time")))
            )
            pnl = cls._float(
                row.get("pnl", row.get("pnl_usdt", row.get("realized_pnl")))
            )
            if (
                open_time is None
                or close_time is None
                or pnl is None
                or close_time < open_time
            ):
                rejected += 1
                warnings.append(
                    f"Rejected trade {trade_id}: missing/invalid time or PnL"
                )
                continue

            raw_side = str(
                row.get("posSide", row.get("side", row.get("direction", "")))
            ).lower()
            if "long" in raw_side or "buy" in raw_side:
                side = PositionSide.LONG
            elif "short" in raw_side or "sell" in raw_side:
                side = PositionSide.SHORT
            else:
                side = PositionSide.UNKNOWN

            entry = cls._float(row.get("openAvgPx", row.get("entry_price")))
            exit_price = cls._float(row.get("closeAvgPx", row.get("exit_price")))
            raw_quantity = cls._float(
                row.get(
                    "closeSubPos",
                    row.get("subPos", row.get("position_size", row.get("quantity"))),
                )
            )
            # OKX signs the size on some accounts and not others: a short comes back
            # as -8151 from one trader and +8151 from the next, while a long is
            # always positive. Size is a magnitude and `posSide` carries direction,
            # so keep the magnitude -- the old non-negative bound silently rejected
            # every signed short, which cost one bot 87 % of its ledger.
            quantity = abs(raw_quantity) if raw_quantity is not None else None
            if (
                raw_quantity is not None
                and raw_quantity < 0
                and side is PositionSide.LONG
            ):
                warnings.append(
                    f"Trade {trade_id}: negative size on a long position; "
                    "direction taken from posSide"
                )
            margin = cls._float(row.get("margin", row.get("margin_usdt")))
            leverage = cls._float(row.get("lever", row.get("leverage")))
            notional = cls._float(row.get("notionalUsd", row.get("notional")))
            if notional is None and margin is not None and leverage is not None:
                notional = margin * leverage

            pnl_ratio = cls._float(row.get("pnlRatio", row.get("pnl_ratio")))
            normalized_pct = cls._float(
                row.get("realized_pnl_pct", row.get("pnl_percent"))
            )
            return_basis = "ABSOLUTE_PNL"
            pnl_pct = None
            if pnl_ratio is not None:
                pnl_pct = pnl_ratio * 100.0
                return_basis = "MARGIN_RETURN"
            elif normalized_pct is not None:
                pnl_pct = normalized_pct
                return_basis = "NORMALIZED_RETURN"
            elif notional and notional > 0:
                pnl_pct = pnl / notional * 100.0
                return_basis = "NOTIONAL_RETURN"

            stop_loss = cls._float(row.get("stopLoss", row.get("stop_loss")))
            initial_risk = cls._float(row.get("initialRisk", row.get("initial_risk")))
            if (
                initial_risk is None
                and "quantity" in row
                and stop_loss is not None
                and entry is not None
                and quantity is not None
            ):
                initial_risk = abs(entry - stop_loss) * quantity
            r_multiple = (
                pnl / initial_risk
                if initial_risk is not None and initial_risk > 0
                else None
            )

            try:
                item = TradeLedgerItem(
                    trade_id=trade_id,
                    symbol=str(row.get("instId", row.get("symbol", "UNKNOWN"))).upper(),
                    side=side,
                    open_time=open_time,
                    close_time=close_time,
                    entry_price=entry,
                    exit_price=exit_price,
                    quantity=quantity,
                    margin=margin,
                    notional=notional,
                    realized_pnl=pnl,
                    realized_pnl_pct=pnl_pct,
                    return_basis=return_basis,
                    initial_risk=initial_risk,
                    r_multiple=r_multiple,
                    fee=cls._float(row.get("fee")),
                    funding=cls._float(row.get("funding")),
                    holding_time_minutes=(close_time - open_time) / 60_000.0,
                    mfe_pct=cls._float(row.get("mfe_pct", row.get("mfe"))),
                    mae_pct=cls._float(row.get("mae_pct", row.get("mae"))),
                    leverage=leverage,
                    stop_loss=stop_loss,
                    take_profit=cls._float(
                        row.get("takeProfit", row.get("take_profit"))
                    ),
                )
            except ValidationError as exc:
                rejected += 1
                warnings.append(f"Rejected trade {trade_id}: {exc.errors()[0]['msg']}")
                continue
            if trade_id in parsed:
                warnings.append(f"Duplicate trade {trade_id}: kept newest record")
            parsed[trade_id] = item

        trades = sorted(
            parsed.values(),
            key=lambda trade: (trade.close_time, trade.open_time, trade.trade_id),
        )
        return LedgerParseResult(trades, rejected, warnings)

    @staticmethod
    def determine_measurement_mode(
        trades: List[TradeLedgerItem],
    ) -> RiskMeasurementMode:
        if not trades:
            return RiskMeasurementMode.LIMITED
        if all(trade.r_multiple is not None for trade in trades):
            return RiskMeasurementMode.FULL
        normalized = sum(
            trade.entry_price is not None
            and trade.exit_price is not None
            and trade.quantity is not None
            and trade.notional is not None
            and trade.realized_pnl_pct is not None
            for trade in trades
        )
        if normalized / len(trades) >= 0.9:
            return RiskMeasurementMode.PARTIAL
        return RiskMeasurementMode.LIMITED
