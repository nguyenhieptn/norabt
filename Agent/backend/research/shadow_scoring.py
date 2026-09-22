"""Score a bot with only its in-sample (pre-cutoff) trades, through the real
product pipeline -- not a hand-rolled re-implementation of the scoring math.

Why a "shadow" data directory
------------------------------
RiskSupervisionPipeline (Agent/backend/pipeline.py) does not accept a trade
ledger as an argument: it reads overview.json/trade_list.json straight off
disk for a given (asset, bot_folder, venue_type), through
BotObservationService -> FileBotDataSource (Agent/backend/external/sources/
bot_source.py). To score "what the product would have said using only the
first N trades" without touching the real Agent/data tree or reimplementing
any scoring logic, this module builds a throwaway directory that looks
exactly like Agent/data to every file-reading component in the pipeline
(MarketService, UniverseRegistry, BotObservationService), except that one
bot's two JSON files are replaced with truncated, in-sample-only versions.
Everything else -- every other bot, every asset's market/candle data, the
universe files -- is a symlink to the real file, so market resolution,
universe eligibility and phase-timeline lookups all see the exact same data
a real run would. This is the "clean splice point" into the production
scoring path that the validation design calls for: RiskSupervisionPipeline.run()
itself is never modified or subclassed, only the files it reads are.

What gets truncated, and why
-----------------------------
1. trade_list.json: only rows whose own close time is at/before the cutoff
   are kept (see `_truncate_raw_ledger`). Filtering re-uses
   TradeLedgerManager._timestamp_ms -- the exact function the production
   parser itself uses to read a row's close time -- so a row this keeps or
   drops is decided the identical way a real crawl-time cutoff would decide
   it, not by a second, hand-rolled reading of closeTime/uTime/close_time.
   open_positions is forced to empty: the project-wide rule is that an open
   position is never a counted result, and the only open-position snapshot
   this data has is the one taken at crawl time -- which is AFTER the
   cutoff, i.e. it would leak future state into an in-sample score.
2. overview.json: weekly_pnl_history is cut at the same boundary. That
   series feeds CapitalResolver's equity curve (Agent/backend/bot/mcp/capital/
   equity_curve.py), which is what DrawdownRiskLens's max_dd_pct is measured
   against. Left un-truncated, a bot's post-cutoff weeks would leak its
   future drawdown straight into the in-sample score -- exactly the leak
   this whole validation exists to rule out. Single scalar fields
   (aum/pnl/pnlRatio/currentEquity) are left as reported: they are not fed
   into the scoring lenses directly (only into a reconciliation status
   string), so leaving them as-is does not add a scoring leak; this is
   documented in Agent/docs/out_of_sample_validation.md as a residual,
   inherent limitation of a copy-trading snapshot instead of a point-in-time
   feed.

What is knowingly NOT rewound
------------------------------
Market data (candles/orderbook/open interest) is read unchanged -- there is
no per-cutoff market snapshot in this dataset, only the latest crawl. So the
market_alignment and liquidity_execution lenses see today's market
conditions, not the conditions as of each bot's own cutoff. This is a real,
disclosed limitation (see the validation report), not something this module
tries to paper over.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Dict

from Agent.backend.bot.mcp.capital.equity_curve import EquityCurveBuilder
from Agent.backend.bot.mcp.trades.ledger import TradeLedgerManager
from Agent.backend.pipeline import RiskSupervisionPipeline, RiskSupervisionResult
from Agent.backend.report.qc.history.store import AssessmentHistoryStore

_LEDGER_ROW_KEYS = ("closed_trades", "history_trades", "trades")


def _raw_rows_key(raw_ledger: Dict[str, Any]) -> str:
    for key in _LEDGER_ROW_KEYS:
        if isinstance(raw_ledger.get(key), list):
            return key
    return _LEDGER_ROW_KEYS[0]


def truncate_raw_ledger(raw_ledger: Dict[str, Any], cutoff_ms: int) -> Dict[str, Any]:
    """Same-shape trade_list.json payload holding only rows closing <= cutoff_ms.

    See module docstring point 1. The re-parsed row count need not exactly
    equal a TimeSplit's `len(train)`: TimeSplit works on already-parsed,
    already-deduplicated TradeLedgerItem objects, while this filters raw
    rows before they are deduplicated. Re-running the same
    TradeLedgerManager over these rows reproduces the identical, final
    dedup/validity decisions a full run would make, which is what matters --
    an exact raw row count is not a correctness requirement.
    """
    truncated = dict(raw_ledger)
    key = _raw_rows_key(raw_ledger)
    rows = raw_ledger.get(key) or []
    kept = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        close_ts = TradeLedgerManager._timestamp_ms(
            row.get("closeTime", row.get("uTime", row.get("close_time")))
        )
        if close_ts is not None and close_ts <= cutoff_ms:
            kept.append(row)
    truncated[key] = kept
    truncated["closed_trades_count"] = len(kept)
    truncated["open_positions_count"] = 0
    truncated["open_positions"] = []
    return truncated


def truncate_overview(overview: Dict[str, Any], cutoff_ms: int) -> Dict[str, Any]:
    """Copy of overview.json with weekly_pnl_history cut at cutoff_ms.

    See module docstring point 2.
    """
    result = dict(overview)
    rows = overview.get("weekly_pnl_history")
    if isinstance(rows, list):
        kept = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            week_ts = EquityCurveBuilder._timestamp_ms(
                row.get("beginTs", row.get("week_start"))
            )
            if week_ts is not None and week_ts <= cutoff_ms:
                kept.append(row)
        result["weekly_pnl_history"] = kept
    return result


def _link_or_copy_asset_subtree(
    shadow_asset_dir: Path,
    real_asset_dir: Path,
    bot_folder: str,
    truncated_ledger: Dict[str, Any],
    truncated_overview: Dict[str, Any],
) -> None:
    """Rebuild one asset directory in the shadow tree: everything symlinked
    except the target bot's own folder, which gets the truncated files.
    """
    shadow_asset_dir.mkdir(parents=True, exist_ok=True)
    for child in real_asset_dir.iterdir():
        if child.name != "bot":
            (shadow_asset_dir / child.name).symlink_to(
                child, target_is_directory=child.is_dir()
            )
            continue
        shadow_bot_root = shadow_asset_dir / "bot"
        shadow_bot_root.mkdir(parents=True, exist_ok=True)
        for bot_dir in child.iterdir():
            if bot_dir.name != bot_folder:
                (shadow_bot_root / bot_dir.name).symlink_to(
                    bot_dir, target_is_directory=True
                )
                continue
            target = shadow_bot_root / bot_dir.name
            target.mkdir(parents=True, exist_ok=True)
            (target / "trade_list.json").write_text(
                json.dumps(truncated_ledger, ensure_ascii=False), encoding="utf-8"
            )
            (target / "overview.json").write_text(
                json.dumps(truncated_overview, ensure_ascii=False), encoding="utf-8"
            )


def build_shadow_data_dir(
    shadow_root: Path,
    real_data_dir: Path,
    venue_type: str,
    asset: str,
    bot_folder: str,
    truncated_ledger: Dict[str, Any],
    truncated_overview: Dict[str, Any],
) -> None:
    """Populate shadow_root so it reads, to every pipeline component, exactly
    like real_data_dir except for one bot's two JSON files.

    `state/` is deliberately created empty rather than symlinked, so nothing
    reachable from this shadow run can ever write into the real
    Agent/data/state/assessments history -- callers should also pass an
    explicit AssessmentHistoryStore rooted under shadow_root and
    persist_history=False to RiskSupervisionPipeline as a second, independent
    guard against that (see score_in_sample).
    """
    venue_key = venue_type.lower()
    for vk in ("cex", "dex"):
        real_venue_dir = real_data_dir / vk
        if not real_venue_dir.is_dir():
            continue
        shadow_venue_dir = shadow_root / vk
        shadow_venue_dir.mkdir(parents=True, exist_ok=True)
        for asset_dir in real_venue_dir.iterdir():
            if not asset_dir.is_dir():
                continue
            if vk == venue_key and asset_dir.name == asset:
                _link_or_copy_asset_subtree(
                    shadow_venue_dir / asset_dir.name,
                    asset_dir,
                    bot_folder,
                    truncated_ledger,
                    truncated_overview,
                )
            else:
                (shadow_venue_dir / asset_dir.name).symlink_to(
                    asset_dir, target_is_directory=True
                )

    for entry in real_data_dir.iterdir():
        if entry.name in ("cex", "dex", "state"):
            continue
        (shadow_root / entry.name).symlink_to(entry, target_is_directory=entry.is_dir())
    (shadow_root / "state" / "assessments").mkdir(parents=True, exist_ok=True)


def score_in_sample(
    *,
    real_data_dir: Path,
    venue_type: str,
    asset: str,
    bot_folder: str,
    raw_ledger: Dict[str, Any],
    overview: Dict[str, Any],
    cutoff_ms: int,
    seed: int = 42,
    simulation_iterations: int = 2_000,
    simulation_horizon: int = 200,
) -> RiskSupervisionResult:
    """Run the real, unmodified RiskSupervisionPipeline against a bot whose
    ledger has been truncated to trades closing at/before cutoff_ms.

    A fresh AssessmentHistoryStore rooted inside the throwaway shadow
    directory is used (not the real one), and persist_history=False is
    passed explicitly: an in-sample score must never read a "previous
    assessment" computed from the bot's full, real ledger (that would leak
    the future straight into the strategy-drift comparison), and must never
    write into the real assessment history that production monitoring
    relies on.
    """
    truncated_ledger = truncate_raw_ledger(raw_ledger, cutoff_ms)
    truncated_overview = truncate_overview(overview, cutoff_ms)
    with tempfile.TemporaryDirectory(prefix="oos_shadow_") as tmp_name:
        shadow_root = Path(tmp_name)
        build_shadow_data_dir(
            shadow_root,
            real_data_dir,
            venue_type,
            asset,
            bot_folder,
            truncated_ledger,
            truncated_overview,
        )
        history = AssessmentHistoryStore(root=shadow_root / "state" / "assessments")
        pipeline = RiskSupervisionPipeline(
            data_dir=shadow_root,
            history=history,
            persist_history=False,
        )
        return pipeline.run(
            asset,
            bot_folder,
            venue_type=venue_type,
            seed=seed,
            as_of_ms=cutoff_ms,
            simulation_iterations=simulation_iterations,
            simulation_horizon=simulation_horizon,
        )
