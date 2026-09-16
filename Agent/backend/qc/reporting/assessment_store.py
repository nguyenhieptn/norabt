"""Persist step 3 one bot at a time, the way step 2 is persisted.

    data/assessment/<venue>/<ASSET>/bot/<TenBot__code>/assessment.json
    data/assessment/index.json

Step 3 is the decision, and a decision that only exists inside a terminal
scroll cannot be handed to a trading agent. Each file carries the two scores,
the tier, every driver behind them, and -- the part that matters most -- the
full Vietnamese narrative, because the numbers are the attachment and the text
is the message.

The folder layout mirrors data/analysis deliberately: the same bot sits at the
same path in both trees, so reading "what step 2 measured" and "what step 3
concluded" about one bot is two reads of the same path with one directory
changed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from Agent.backend.qc.reporting.analysis_store import folder_name
from Agent.backend.qc.reporting.reasons import recommendation_vi

ASSESSMENT_DIRNAME = "assessment"


def _write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


def build_assessment(
    row: Any, generated_at_ms: int, slot: Optional[str] = None
) -> Dict[str, Any]:
    """One bot's step-3 verdict as a document, text first."""
    paragraphs = recommendation_vi(row)
    return {
        "step": "3_QC_DANH_GIA",
        "schema_version": "bot_assessment.v1",
        "generated_at_ms": generated_at_ms,
        "bot": {
            "nick_name": row.nick_name,
            "unique_code": row.unique_code,
            "traded_symbol": row.traded_symbol,
            "venue_type": row.venue_type,
            "asset_context": row.asset_context,
            # The slot the bot was selected to fill, which is not always the
            # instrument its ledger names -- every DEX slot is filled by an OKX
            # trader, so the two differ by design and both belong in the file.
            "slot": slot or f"{row.venue_type}/{row.traded_symbol}",
            "rank_in_cohort": row.rank,
        },
        # The narrative comes first in the file because it is the deliverable;
        # everything under it exists to be checked against it.
        "khuyen_nghi": {
            "ket_luan": row.verdict,
            "hanh_dong": row.recommended_action,
            "diem_chat_luong": row.quality_score,
            "diem_rui_ro": row.risk_score,
            "do_tin_cay": row.confidence,
            "nguyen_nhan": row.verdict_reason,
            "text": paragraphs,
            "text_full": "\n\n".join(paragraphs),
        },
        "cham_diem": {
            "risk_score": row.risk_score,
            "risk_tier": row.risk_tier,
            "weighted_average": row.weighted_average,
            "veto_floor": row.veto_floor,
            "score_decided_by": row.score_decided_by,
            "veto_reasons": row.veto_reasons,
            "raised_the_score": row.raised_the_score,
            "held_the_score_down": row.held_the_score_down,
            "dimension_scores": row.dimension_scores,
            "top_risk_drivers": row.top_risk_drivers,
            "unknown_dimensions": row.unknown_dimensions,
            "quality_score": row.quality_score,
            "quality_components": row.quality_components,
            "quality_notes": row.quality_notes,
            "hidden_risk_flags": row.hidden_risk_flags,
        },
        "bang_chung": {
            "trade_count": row.trade_count,
            "win_rate": row.win_rate,
            "profit_factor": row.profit_factor,
            "marked_profit_factor": row.marked_profit_factor,
            "payoff_ratio": row.payoff_ratio,
            "expectancy": row.expectancy,
            "total_pnl": row.total_pnl,
            "max_drawdown_pct": row.max_drawdown_pct,
            "sharpe_ratio": row.sharpe_ratio,
            "sortino_ratio": row.sortino_ratio,
            "open_positions": row.open_positions,
            "open_loss": row.open_loss,
            "open_loss_to_capital_pct": row.open_loss_to_capital_pct,
            "capital_at_risk": row.capital_at_risk,
            "capital_basis": row.capital_basis,
            "pnl_skew": row.pnl_skew,
            "pnl_kurtosis": row.pnl_kurtosis,
            "directional_bias": row.directional_bias,
            "entry_style": row.entry_style,
            "phase_coverage_pct": row.phase_coverage_pct,
            "regime_dependence_pct": row.regime_dependence_pct,
            "best_phase": row.best_phase,
            "worst_phase": row.worst_phase,
            "losing_phases": row.losing_phases,
            "untested_phases": row.untested_phases,
            "tested_in_downtrend": row.tested_in_downtrend,
            "measurement_mode": row.measurement_mode,
            "reconciliation_status": row.reconciliation_status,
            "ledger_coverage_days": row.ledger_coverage_days,
            "declared_lead_days": row.declared_lead_days,
        },
        "mo_phong": {
            "method": "STATIONARY_BOOTSTRAP",
            "scope": "CHI_LENH_DA_CHOT",
            "iterations": row.mc_iterations,
            "horizon_trades": row.mc_horizon,
            "profit_pct_worst": row.profit_pct_worst,
            "profit_pct_p05": row.profit_pct_p05,
            "profit_pct_p50": row.profit_pct_p50,
            "profit_pct_p95": row.profit_pct_p95,
            "var_95_pct": row.var_95_pct,
            "cvar_95_pct": row.cvar_95_pct,
            "mar_ratio_median": row.mar_ratio_median,
            "profit_factor_median": row.profit_factor_median,
            "p95_max_drawdown": row.p95_max_drawdown,
            "worst_drawdown": row.worst_drawdown,
            "p_ruin": row.p_ruin,
            "p_loss_after_horizon": row.p_loss_after_horizon,
            "p_5_loss_streak": row.p_5_loss_streak,
            "deferred_loss_bias": row.simulation_deferred_loss_bias,
            "psr": row.psr,
            "deflated_sharpe": row.deflated_sharpe,
            "min_track_record_trades": row.min_track_record_trades,
            "selection_trials": row.selection_trials,
            "inference_reliable": row.inference_reliable,
            "stress_verdict": row.stress_verdict,
        },
    }


def _slot_index(data_dir: Path) -> Dict[str, tuple]:
    """uniqueCode -> (venue, symbol) of the slot the bot was selected to fill.

    A bot is filed under the slot it was picked for, not the instrument its
    ledger happens to name. Every DEX slot is filled by an OKX trader, so
    filing by traded symbol collapsed all five DEX assets into cex/ and left
    the assessment tree looking like the DEX side had never been assessed.
    """
    path = Path(data_dir) / "universe" / "bot_selection.json"
    if not path.exists():
        return {}
    try:
        selection = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    index: Dict[str, tuple] = {}
    for asset in selection.get("assets") or []:
        venue = asset.get("venue") or "CEX"
        symbol = asset.get("symbol") or asset.get("underlying")
        if not symbol:
            continue
        for role in ("top", "mid"):
            code = (asset.get(role) or {}).get("code")
            if code:
                index[code] = (venue, symbol.upper())
    return index


def persist(report: Any, data_dir: Path) -> List[str]:
    """Write one assessment.json per scored bot. Returns the paths."""
    root = Path(data_dir) / ASSESSMENT_DIRNAME
    written: List[str] = []
    summary: List[Dict[str, Any]] = []
    slots = _slot_index(Path(data_dir))

    for row in report.rows:
        # A row that failed to evaluate has no verdict to record; step 3's own
        # gaps section is where those belong, not a file claiming an assessment.
        if row.error or row.verdict is None:
            continue
        venue, symbol = slots.get(
            row.unique_code,
            (
                row.venue_type or "CEX",
                (row.traded_symbol or row.asset_context or "UNKNOWN").upper(),
            ),
        )
        bot_dir = (
            root
            / venue.lower()
            / symbol
            / "bot"
            / folder_name(row.nick_name, row.unique_code)
        )
        payload = build_assessment(row, report.generated_at_ms, f"{venue}/{symbol}")
        path = bot_dir / "assessment.json"
        _write(path, payload)
        written.append(str(path))
        summary.append(
            {
                "nick_name": row.nick_name,
                "unique_code": row.unique_code,
                "slot": f"{venue}/{symbol}",
                "verdict": row.verdict,
                "quality_score": row.quality_score,
                "risk_score": row.risk_score,
                "file": str(path),
            }
        )

    index = {
        "step": "3_QC_DANH_GIA",
        "generated_at_ms": report.generated_at_ms,
        "bots_assessed": len(summary),
        "note": (
            "Mỗi bot một file assessment.json: điểm chất lượng, điểm rủi ro, xếp "
            "loại, nguyên nhân và bản khuyến nghị text đầy đủ. Text là phần "
            "chính; các chỉ số bên dưới là bằng chứng cho text đó."
        ),
        "bots": summary,
    }
    index_path = root / "index.json"
    _write(index_path, index)
    written.append(str(index_path))
    return written


def load_bot(
    data_dir: Path, venue_type: str, symbol: str, unique_code: str
) -> Optional[Dict[str, Any]]:
    """Read one bot's step-3 assessment back, looked up by uniqueCode."""
    root = Path(data_dir) / ASSESSMENT_DIRNAME / venue_type.lower() / symbol / "bot"
    if not root.is_dir():
        return None
    bot_dir = next(
        (path for path in root.glob(f"*{unique_code}") if path.is_dir()), None
    )
    if bot_dir is None:
        return None
    path = bot_dir / "assessment.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
