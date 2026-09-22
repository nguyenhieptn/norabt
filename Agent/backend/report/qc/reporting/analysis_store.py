"""Persist what step 2 produced, so step 3 has a visible, per-bot input.

Why on disk: step 3 is the decision, and its input has to be inspectable one bot
at a time rather than existing only inside a process. Step 1's crawl already
lands in data/cex and data/dex; this writes the analysed layer beside it.

    data/analysis/<venue>/<ASSET>/market/market.json
    data/analysis/<venue>/<ASSET>/bot/<TenBot__code>/performance.json
    data/analysis/<venue>/<ASSET>/bot/<TenBot__code>/monte_carlo.json

Folders carry the bot's name so a person can find one by eye, with the
uniqueCode appended because names are not unique, change over time, and contain
spaces and CJK that do not belong in a path.

Two files per bot, not one: the performance profile is what the bot did, the
Monte Carlo file is what could happen next. They answer different questions and
get read by different parts of step 3, so merging them only makes both harder
to read.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

ANALYSIS_DIRNAME = "analysis"

PERFORMANCE_FIELDS = (
    "role",
    "nick_name",
    "unique_code",
    "okx_rank",
    "board_roi_pct",
    "trade_count",
    "trades_on_asset",
    "win_rate",
    "profit_factor",
    "marked_profit_factor",
    "expectancy",
    "payoff_ratio",
    "average_win",
    "average_loss",
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
    "recovery_factor",
    "max_drawdown_pct",
    "max_drawdown_capped",
    "ledger_pnl",
    "max_win_streak",
    "max_loss_streak",
    "median_hold_minutes",
    "trades_per_day",
    "open_positions",
    "gross_exposure",
    "unrealized_pnl",
    "open_loss",
    "current_leverage",
    "pnl_median",
    "pnl_std",
    "pnl_skew",
    "pnl_kurtosis",
    "pnl_p05",
    "pnl_p95",
    "mean_pnl_ci",
    "measurement_mode",
    "capital_at_risk",
    "capital_basis",
    "ledger_coverage_days",
    "declared_lead_days",
    "directional_bias",
    "entry_style",
    "entry_style_evidence",
    "phase_coverage_pct",
    "regime_dependence_pct",
    "best_phase",
    "worst_phase",
    "losing_phases",
    "untested_phases",
    "tested_in_downtrend",
    "phase_rows",
    "data_quality",
    "reconciliation",
    "warnings",
)

MONTE_CARLO_FIELDS = (
    "role",
    "nick_name",
    "unique_code",
    "mc_iterations",
    "mc_horizon",
    "mc_sample_size",
    "mc_deferred_loss_bias",
    "mc_profit_worst_pct",
    "mc_profit_p05_pct",
    "mc_profit_p50_pct",
    "mc_profit_p95_pct",
    "mc_profit_best_pct",
    "mc_p95_drawdown",
    "mc_worst_drawdown",
    "mc_p_ruin",
    "mc_p_loss",
    "sharpe_per_trade",
    "psr",
    "deflated_sharpe",
    "min_track_record_trades",
    "selection_trials",
    "inference_reliable",
    "inference_notes",
    "stress_volatility_2x",
    "stress_spread_3x",
    "stress_liquidity_half",
    "stress_verdict",
)


def folder_name(nick_name: str, unique_code: str) -> str:
    """`HaveARestin__53AEED5A8E4EBBB2` — readable, still unique, path-safe."""
    slug = "".join(
        ch if ch.isalnum() or ch in "-_" else "-" for ch in (nick_name or "").strip()
    ).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)[:40]
    return f"{slug}__{unique_code}" if slug else unique_code


def _write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def _pick(row: Any, fields: tuple) -> Dict[str, Any]:
    data = row.model_dump(mode="json")
    return {key: data.get(key) for key in fields}


def persist(report: Any, data_dir: Path) -> List[str]:
    """Write one market file per asset and two files per bot. Returns the paths.

    Unified layout: market.json lands beside every other market file for that
    asset (`data/market/<venue>/<asset>/market.json`, see
    `Agent.backend.external.sources.market_source.FileMarketDataSource._market_dir`);
    performance.json/monte_carlo.json land beside step 3's own `latest.json`
    for the same bot (`data/report/single/<bot_id>/`, see
    `Agent.backend.report.qc.reporting.assessment_store`) -- one bot, one folder,
    across both steps.
    """
    market_root = Path(data_dir) / "market"
    report_root = Path(data_dir) / "report" / "single"
    written: List[str] = []

    for block in report.blocks:
        market = {
            "step": "2.1_MARKET_ANALYSIS",
            "generated_at_ms": report.generated_at_ms,
            "venue_type": block.venue_type,
            "symbol": block.symbol,
            "underlying": block.underlying,
            "available": block.market_available,
            "posture": block.market_posture,
            "posture_evidence": block.market_evidence,
            "trend": block.market_trend,
            "volatility": block.market_volatility,
            "liquidity": block.market_liquidity,
            "data_quality": block.market_quality,
            "error": block.market_error,
            "comparison": block.comparison,
        }
        path = market_root / block.venue_type.lower() / block.symbol / "market.json"
        _write(path, market)
        written.append(str(path))

        for bot in block.bots:
            if bot.error:
                continue
            bot_dir = report_root / bot.unique_code
            performance = {
                "step": "2.2_PERFORMANCE",
                "generated_at_ms": report.generated_at_ms,
                "slot": f"{block.venue_type}/{block.symbol}",
                "underlying": block.underlying,
                **_pick(bot, PERFORMANCE_FIELDS),
            }
            simulation = {
                "step": "2.2_MONTE_CARLO",
                "generated_at_ms": report.generated_at_ms,
                "slot": f"{block.venue_type}/{block.symbol}",
                "underlying": block.underlying,
                "method": "STATIONARY_BOOTSTRAP",
                "scope": "CHI_LENH_DA_CHOT",
                **_pick(bot, MONTE_CARLO_FIELDS),
            }
            for name, payload in (
                ("performance.json", performance),
                ("monte_carlo.json", simulation),
            ):
                path = bot_dir / name
                _write(path, payload)
                written.append(str(path))

    index = {
        "step": "2_ANALYSIS_AND_SIMULATION",
        "generated_at_ms": report.generated_at_ms,
        "slots": report.slots,
        "bots_evaluated": report.bots_evaluated,
        "bots_failed": report.bots_failed,
        "note": (
            "Đây là đầu vào của bước 3. Mỗi asset có market.json; mỗi bot có "
            "performance.json (đã làm gì) và monte_carlo.json (có thể xảy ra gì)."
        ),
        "files": written,
    }
    # Own run manifest, not `data/report/single/index.json` (assessment_store.py owns
    # that name) -- nothing reads this one back (verified: no consumer
    # anywhere under Agent/ greps for "analysis_run_index" or the old
    # `analysis/index.json`), it exists purely as a per-run audit trail.
    index_path = Path(data_dir) / "analysis_run_index.json"
    _write(index_path, index)
    written.append(str(index_path))
    return written


def load_bot(
    data_dir: Path, venue_type: str, symbol: str, unique_code: str
) -> Optional[Dict[str, Any]]:
    """Read one bot's step-2 output back, the way step 3 consumes it.

    `venue_type`/`symbol` kept for backward compatibility with existing
    callers but no longer part of the lookup path -- see
    `Agent.backend.report.qc.reporting.assessment_store.load_bot`'s matching change.
    """
    bot_dir = Path(data_dir) / "report" / "single" / unique_code
    performance = bot_dir / "performance.json"
    simulation = bot_dir / "monte_carlo.json"
    if not performance.exists() or not simulation.exists():
        return None
    return {
        "performance": json.loads(performance.read_text(encoding="utf-8")),
        "monte_carlo": json.loads(simulation.read_text(encoding="utf-8")),
    }
