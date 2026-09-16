"""Step 1 report: what data we hold, for markets and for bots.

Why this is its own step: the pipeline splits into collecting data, analysing it,
and judging bots. The earlier reports mixed the first two -- market analysis was
labelled step 1 -- which hid the question this step exists to answer: is the input
complete enough to analyse at all, on both sides.

Nothing here interprets the data. A source is present, stale, or absent; a bot
ledger is complete or it names what is missing. Scores and regimes belong to the
next step.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.market.service import MarketDataUnavailableError, MarketService

# Trade fields the risk maths cannot run without.
TRADE_FIELDS = (
    "subPosId",
    "instId",
    "posSide",
    "openTime",
    "closeTime",
    "pnl",
    "pnlRatio",
    "margin",
    "lever",
)
ACTIVE_WITHIN_DAYS = 7


class MarketDataRow(BaseModel):
    venue_type: str
    symbol: str
    available: bool = False
    quality: Optional[float] = None
    candles: int = Field(default=0, ge=0)
    newest_candle_ms: Optional[int] = None
    sources_ok: int = Field(default=0, ge=0)
    sources_total: int = Field(default=0, ge=0)
    missing: List[str] = Field(default_factory=list)
    stale: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class BotDataRow(BaseModel):
    slot: str
    role: str
    nick_name: str
    unique_code: str
    folder: Optional[str] = None
    trades: int = Field(default=0, ge=0)
    trades_on_asset: int = Field(default=0, ge=0)
    open_positions: int = Field(default=0, ge=0)
    positions_without_instrument: int = Field(default=0, ge=0)
    weekly_points: int = Field(default=0, ge=0)
    has_profile: bool = False
    ledger_truncated: bool = False
    last_close_days: Optional[float] = None
    active: bool = False
    blocking: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class DataReport(BaseModel):
    schema_version: str = "data_report.v1"
    generated_at_ms: int
    evaluation_mode: EvaluationMode
    markets: List[MarketDataRow] = Field(default_factory=list)
    bots: List[BotDataRow] = Field(default_factory=list)
    markets_complete: int = Field(default=0, ge=0)
    bots_complete: int = Field(default=0, ge=0)
    notes: List[str] = Field(default_factory=list)


class DataReportService:
    """Inventory the crawled inputs for the 15 markets and the 30 selected bots."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        evaluation_mode: EvaluationMode = EvaluationMode.SNAPSHOT,
    ) -> None:
        self.data_dir = data_dir or Path(config.DATA_DIR)
        self.evaluation_mode = evaluation_mode
        self.market = MarketService(self.data_dir, evaluation_mode)

    def _market_row(self, venue: str, symbol: str, now: int) -> MarketDataRow:
        row = MarketDataRow(venue_type=venue, symbol=symbol)
        try:
            result = self.market.get_market_result(
                symbol, venue_type=venue, as_of_ms=now
            )
        except MarketDataUnavailableError as exc:
            return row.model_copy(update={"error": str(exc)})

        quality = result.data_quality
        applicable = [
            source
            for source in quality.sources
            if str(source.status).split(".")[-1] != "NOT_APPLICABLE"
        ]
        ok = [s for s in applicable if str(s.status).split(".")[-1] == "AVAILABLE"]
        candles = next(
            (s.record_count for s in quality.sources if s.source == "ohlcv_1h"), 0
        )
        return row.model_copy(
            update={
                "available": True,
                "quality": result.data_quality_score,
                "candles": candles or 0,
                "newest_candle_ms": quality.anchor_ms,
                "sources_ok": len(ok),
                "sources_total": len(applicable),
                "missing": list(quality.missing_sources),
                "stale": list(quality.stale_sources),
            }
        )

    def _bot_row(
        self, slot: str, role: str, entry: Dict[str, Any], underlying: str, now: int
    ) -> BotDataRow:
        code = entry["code"]
        row = BotDataRow(
            slot=slot,
            role=role,
            nick_name=entry.get("name") or code,
            unique_code=code,
        )
        folder = next(
            (
                path
                for path in self.data_dir.rglob(f"bot_{code}")
                if (path / "trade_list.json").exists()
            ),
            None,
        )
        if folder is None:
            return row.model_copy(update={"blocking": ["chưa crawl"]})

        overview = json.loads((folder / "overview.json").read_text(encoding="utf-8"))
        ledger = json.loads((folder / "trade_list.json").read_text(encoding="utf-8"))
        trades: List[Dict[str, Any]] = ledger.get("closed_trades") or []
        positions: List[Dict[str, Any]] = ledger.get("open_positions") or []
        weekly = overview.get("weekly_pnl_history") or []

        blocking: List[str] = []
        notes: List[str] = []

        foreign = sum(1 for t in trades if str(t.get("uniqueCode", code)) != code)
        if foreign:
            blocking.append(f"{foreign} lệnh của trader khác")
        if not trades:
            blocking.append("không có lệnh đóng")
        for field in TRADE_FIELDS:
            gaps = sum(1 for t in trades if t.get(field) in (None, ""))
            if not gaps:
                continue
            (blocking if gaps == len(trades) else notes).append(
                f"{gaps}/{len(trades)} lệnh trống {field}"
            )
        if not weekly:
            blocking.append("không có chuỗi PnL tuần")

        profile_fields = ("aum", "pnl", "pnlRatio", "winRatio")
        missing_profile = [f for f in profile_fields if overview.get(f) in (None, "")]
        if missing_profile:
            blocking.append("overview thiếu " + ",".join(missing_profile))

        on_asset = sum(
            1
            for t in trades
            if str(t.get("instId", "")).split("-")[0].upper() == underlying
        )
        if on_asset == 0:
            blocking.append(f"không có lệnh nào trên {underlying}")

        last_close = max((int(t.get("closeTime") or 0) for t in trades), default=0)
        age_days = (now - last_close) / 86_400_000 if last_close else None
        active = bool(positions) or (
            age_days is not None and age_days <= ACTIVE_WITHIN_DAYS
        )
        if not active:
            blocking.append("không còn hoạt động")

        failures = (overview.get("provenance") or {}).get("fetch_failures") or []
        if failures:
            notes.append(f"{len(failures)} request phải thử lại")

        return row.model_copy(
            update={
                "folder": str(folder.relative_to(self.data_dir)),
                "nick_name": overview.get("nickName") or row.nick_name,
                "trades": len(trades),
                "trades_on_asset": on_asset,
                "open_positions": len(positions),
                "positions_without_instrument": sum(
                    1 for p in positions if not p.get("instId")
                ),
                "weekly_points": len(weekly),
                "has_profile": not missing_profile,
                "ledger_truncated": bool(ledger.get("ledger_truncated")),
                "last_close_days": age_days,
                "active": active,
                "blocking": blocking,
                "notes": notes,
            }
        )

    def build(
        self,
        as_of_ms: Optional[int] = None,
        selection_path: Optional[Path] = None,
        only_codes: Optional[set] = None,
    ) -> DataReport:
        path = selection_path or (self.data_dir / "universe" / "bot_selection.json")
        selection = json.loads(path.read_text(encoding="utf-8"))
        now = as_of_ms or int(time.time() * 1000)

        records = selection["assets"]
        if only_codes:
            records = [
                record
                for record in records
                if any(
                    record.get(slot) and record[slot]["code"] in only_codes
                    for slot in ("top", "mid")
                )
            ]
        markets = [
            self._market_row(record["venue"], record["symbol"], now)
            for record in records
        ]
        bots: List[BotDataRow] = []
        for record in records:
            slot = f"{record['venue']}/{record['symbol']}"
            for role, key in (("CHẠY NGON", "top"), ("YẾU HƠN", "mid")):
                entry = record.get(key)
                if entry and (not only_codes or entry["code"] in only_codes):
                    bots.append(
                        self._bot_row(slot, role, entry, record["underlying"], now)
                    )

        return DataReport(
            generated_at_ms=now,
            evaluation_mode=self.evaluation_mode,
            markets=markets,
            bots=bots,
            markets_complete=sum(
                1 for m in markets if m.available and not m.missing and not m.stale
            ),
            bots_complete=sum(1 for b in bots if not b.blocking),
            notes=[
                "Bước này chỉ kiểm kê dữ liệu; mọi diễn giải nằm ở bước 2.",
                "CHẶN = thiếu thứ mà phép tính rủi ro không chạy được nếu không có.",
                "GHI CHÚ = khiếm khuyết OKX để trống, ghi rõ số lượng, không tự điền.",
            ],
        )
