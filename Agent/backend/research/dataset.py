"""Discover bot ledgers on disk and parse them the same way the product does.

Mirrors how Agent/backend/sources/bot_source.py's FileBotDataSource and
Agent/backend/mcp/service.py read a bot snapshot: two JSON files,
overview.json and trade_list.json, under
data_dir/<cex|dex>/<asset>/bot/<folder>/. This module only reads them (never
writes into the real data tree) and hands the raw ledger to the exact same
Agent.backend.mcp.trades.ledger.TradeLedgerManager the product uses, so
"how many closed trades this bot has" and "what each trade's close_time and
realized_pnl are" mean the same thing here as they do inside a real
assessment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from Agent.backend.mcp.schemas.bot_result import TradeLedgerItem
from Agent.backend.mcp.trades.ledger import TradeLedgerManager

VENUE_TYPES = ("CEX", "DEX")


@dataclass(frozen=True)
class BotLedgerRecord:
    """One bot's on-disk snapshot, already run through the production parser."""

    venue_type: str
    asset: str
    bot_folder: str
    bot_dir: Path
    overview: Dict[str, Any]
    raw_ledger: Dict[str, Any]
    trades: List[TradeLedgerItem]
    rejected_count: int
    parse_warnings: List[str]


def discover_bot_dirs(data_dir: Path) -> List[Tuple[str, str, Path]]:
    """List every (venue_type, asset, bot_dir) that has both JSON files.

    Sorted so a run's bot order (and therefore its progress log) is
    deterministic across machines and repeat runs.
    """
    found: List[Tuple[str, str, Path]] = []
    for venue_type in VENUE_TYPES:
        venue_root = data_dir / venue_type.lower()
        if not venue_root.is_dir():
            continue
        for asset_dir in sorted(p for p in venue_root.iterdir() if p.is_dir()):
            bot_root = asset_dir / "bot"
            if not bot_root.is_dir():
                continue
            for bot_dir in sorted(p for p in bot_root.iterdir() if p.is_dir()):
                if (bot_dir / "overview.json").is_file() and (
                    bot_dir / "trade_list.json"
                ).is_file():
                    found.append((venue_type, asset_dir.name, bot_dir))
    return found


def load_bot_ledger(
    venue_type: str, asset: str, bot_dir: Path
) -> Optional[BotLedgerRecord]:
    """Read + parse one bot's overview.json/trade_list.json.

    Returns None (rather than raising) for a file that is missing, is not
    valid JSON, or is not a JSON object -- the same "this bot's data is
    unusable, skip it" outcome FileBotDataSource signals to its caller,
    just without the BotSourceError type since this is read-only research
    tooling, not the production read path.
    """
    try:
        overview = json.loads((bot_dir / "overview.json").read_text(encoding="utf-8"))
        raw_ledger = json.loads(
            (bot_dir / "trade_list.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(overview, dict) or not isinstance(raw_ledger, dict):
        return None

    parsed = TradeLedgerManager.parse_trade_list_with_diagnostics(raw_ledger)
    return BotLedgerRecord(
        venue_type=venue_type,
        asset=asset,
        bot_folder=bot_dir.name,
        bot_dir=bot_dir,
        overview=overview,
        raw_ledger=raw_ledger,
        trades=parsed.trades,
        rejected_count=parsed.rejected_count,
        parse_warnings=parsed.warnings,
    )


def load_all_bot_ledgers(data_dir: Path) -> List[BotLedgerRecord]:
    """Convenience wrapper: discover + load every bot, skipping unreadable ones."""
    records: List[BotLedgerRecord] = []
    for venue_type, asset, bot_dir in discover_bot_dirs(data_dir):
        record = load_bot_ledger(venue_type, asset, bot_dir)
        if record is not None:
            records.append(record)
    return records
