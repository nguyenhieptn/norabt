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
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from Agent.backend.qc.reporting.analysis_store import folder_name
from Agent.backend.qc.reporting.reasons import recommendation_vi

ASSESSMENT_DIRNAME = "assessment"


def _write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Việc 2/3: `bot.identity.symbol_exposure_share`/`observed_symbols`
# (Agent/backend/mcp/service.py::_resolve_identity_market) đã được tính sẵn
# vào `row.exposure_share` (cohort.py) từ trước Việc này, nhưng chưa từng ghi
# xuống assessment.json -- hệ quả: không nơi nào thấy được một bot tập trung
# hay phân tán, mà đó chính là dữ kiện quyết định thị trường được chấm
# (`row.traded_symbol`) có đại diện cho toàn bộ hoạt động bot hay chỉ một
# phần. Ba hàm nhỏ dưới đây là phần thuần dữ liệu của việc ghi đó -- xem nơi
# gọi trong `build_assessment` cho cách chúng khớp vào `bang_chung`.
# --------------------------------------------------------------------------- #


def _observed_symbols_desc(exposure_share: Optional[Dict[str, float]]) -> List[str]:
    """Mọi mã bot từng giao dịch, xếp theo tỉ trọng exposure giảm dần --
    đúng thứ tự `BotIdentity.observed_symbols` đã dùng khi được tính (xem
    `_resolve_identity_market`), suy lại từ `exposure_share` ở đây thay vì
    truyền riêng một trường nữa cho cùng một thông tin.
    """
    share = exposure_share or {}
    return sorted(share, key=lambda name: share[name], reverse=True)


def _share_pct(
    exposure_share: Optional[Dict[str, float]], symbol: str
) -> Optional[float]:
    """Tỉ trọng (0-100) của CHÍNH `symbol` (thường là `row.traded_symbol`)
    trong tổng exposure -- `None` khi không đo được, KHÔNG PHẢI `0.0` (để
    không bị đọc nhầm thành "bot không giao dịch mã này chút nào").
    """
    share = exposure_share or {}
    value = share.get(symbol)
    if not isinstance(value, (int, float)):
        return None
    return round(value * 100.0, 2)


def _secondary_market_payload(row: Any) -> Optional[Dict[str, Any]]:
    """Thị trường đứng thứ hai theo exposure (Việc 3) -- CHỈ để trình bày,
    `None` khi `cohort.py` đã tự lọc (bot chỉ giao dịch một mã, hoặc mã thứ
    hai không có dữ liệu thị trường); xem `BotEvaluationRow.secondary_*`
    (cohort.py) cho nơi ba trường này được tính.
    """
    symbol = getattr(row, "secondary_traded_symbol", None)
    market = getattr(row, "secondary_market", None)
    if not symbol or market is None:
        return None
    share_pct = getattr(row, "secondary_share_pct", None)
    return {
        "symbol": symbol,
        "share_pct": round(share_pct, 2)
        if isinstance(share_pct, (int, float))
        else None,
        "venue_type": market.venue_type,
        "trend": market.trend,
        "volatility": market.volatility,
        "liquidity_tier": market.liquidity_tier,
        "flow_bias": market.flow_bias,
        "last_price": market.last_price,
    }


# --------------------------------------------------------------------------- #
# Phủ sóng theo mục tiêu (xem Agent/backend/market/coverage.py) -- thay
# "luôn đúng 2 thị trường: chính + phụ" (`_secondary_market_payload` ở
# trên, GIỮ NGUYÊN cho tương thích ngược) bằng danh sách ĐẦY ĐỦ mọi thị
# trường đã giải được/chưa giải được trong lượt phủ sóng, cộng con số ĐỘ
# PHỦ THẬT đã đạt -- xem `BotEvaluationRow.resolved_markets`/
# `unresolved_markets`/`coverage_achieved_pct` (cohort.py) cho nơi ba
# trường này được tính.
# --------------------------------------------------------------------------- #


def _resolved_markets_payload(row: Any) -> List[Dict[str, Any]]:
    """Mọi thị trường ĐÃ GIẢI ĐƯỢC trong lượt phủ sóng -- `[]` khi `row`
    không mang trường này (file ghi trước khi tính năng này tồn tại, hoặc
    `row` không phải `BotEvaluationRow` đầy đủ)."""
    out: List[Dict[str, Any]] = []
    for item in getattr(row, "resolved_markets", None) or []:
        market = item.market
        out.append(
            {
                "symbol": item.symbol,
                "share_pct": round(item.share_pct, 2),
                "venue_type": market.venue_type,
                "trend": market.trend,
                "volatility": market.volatility,
                "liquidity_tier": market.liquidity_tier,
                "flow_bias": market.flow_bias,
                "last_price": market.last_price,
            }
        )
    return out


def _unresolved_markets_payload(row: Any) -> List[Dict[str, Any]]:
    """Mọi thị trường NẰM TRONG kế hoạch phủ sóng nhưng KHÔNG lấy được dữ
    liệu -- cổ phiếu (SNDK, MU, SKHYNIX, LITE, PUMP, HYPE, CRCL...) hoặc hết
    hạn chờ. `[]` khi `row` không mang trường này."""
    return [
        {
            "symbol": item.symbol,
            "share_pct": round(item.share_pct, 2),
            "reason": item.reason,
        }
        for item in getattr(row, "unresolved_markets", None) or []
    ]


def build_assessment(
    row: Any,
    generated_at_ms: int,
    slot: Optional[str] = None,
    *,
    strategy_extra: Optional[Dict[str, Any]] = None,
    behavioral_extra: Optional[Dict[str, Any]] = None,
    narrative_text: Optional[str] = None,
    closed_trade_series: Optional[List[Dict[str, Any]]] = None,
    horizon_scenarios: Optional[List[Dict[str, Any]]] = None,
    assets: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """One bot's step-3 verdict as a document, text first.

    `strategy_extra`/`behavioral_extra` (both default `None`, so every
    pre-existing caller is byte-for-byte unaffected) fill in the strategy/
    behavioural fields `row` (`BotEvaluationRow`, cohort.py) does not itself
    carry -- `observed_profile`, `declared_strategy`, `entry_style_evidence`,
    `tested_in_trend`, `phase_breakdown`, and the full set of behavioural
    flags/scores. Shaped exactly like `Agent/backend/web/data.py`'s
    `_strategy_evidence`/`_behavioral_evidence` (same keys), which is what
    `run_report.py` builds them from -- see that module's own docstring for
    WHERE the underlying `StrategyObservations`/`BehavioralObservations`
    come from (a read-only re-fetch of the same bot's `BotResult`, never a
    second, independently-scored pass). `None` (the field is simply absent
    from a degraded row, e.g. the re-fetch failed) degrades every added key
    to `None`/empty rather than raising -- the fields `row` already carries
    directly (`directional_bias`, `entry_style`, `phase_coverage_pct`, ...)
    are untouched either way.

    `narrative_text` (default `None`) is Việc 4's own fix: the OPTIONAL,
    off-by-default LLM-authored "nhận định chuyên môn" paragraph
    (Agent/backend/qc/reporting/narrative.py) used to be reachable only from
    `/api/analyze`'s live path, so every assessment.json this module writes
    was missing it even when an operator had the feature turned on. Kept as
    its own top-level key (`nhan_dinh_chuyen_mon`), never folded into
    `khuyen_nghi` -- that key already holds a DIFFERENT, always-on,
    deterministic Vietnamese write-up (`recommendation_vi(row)` below, no
    LLM involved), and conflating the two would make it impossible to tell
    which one a given sentence came from.

    `closed_trade_series`/`horizon_scenarios`/`assets` (all default `None`,
    một caller cũ không truyền vào vẫn chạy y hệt trước đây) vá đúng lỗ hổng
    đã đo được: trang `/bot/<code>` phục vụ từ SNAPSHOT REDIS hoặc chạy sống
    luôn có đủ 7 `<svg>`/12 `<details>`, nhưng phục vụ từ CHÍNH file
    assessment.json này chỉ còn 5/8. Hai biểu đồ (đường vốn tích luỹ + so
    sánh xác suất theo horizon) cần `evidence.closed_trade_series`
    (`_extract_trade_pnls`) và `mo_phong.horizon_scenarios`
    (`_render_horizon_comparison`/`_render_horizon_probability_chart`); mục
    thứ ba KHÔNG phải biểu đồ -- bảng "Tài sản đang giao dịch"
    (`_render_assets`, report_page.py) chỉ hiện khi khoá `assets` ở gốc kết
    quả khác rỗng, và `assessment_to_analyze_result` (data.py) trước đây
    luôn gán cứng `[]` -- cả ba đều không file nào từng ghi. `row`
    (`BotEvaluationRow`) không tự mang cả ba (cũng off-limits để sửa như
    `strategy_extra`/`behavioral_extra` ở trên), nên chúng tới đây từ
    `run_report.py`'s `build_assessment_extras` -- `closed_trade_series` là
    `bot.trade_ledger_summary` và `assets` là
    `bot.current_state.open_positions` + `bot.trade_ledger_summary` (cả hai
    tất định, không phụ thuộc số vòng lặp Monte Carlo) qua
    `Agent/backend/web/data.py::_closed_trade_series_from_bot_result`/
    `_asset_states_from_bot_result`; `horizon_scenarios` là
    `bot.simulation_results.horizon_scenarios` từ CHÍNH lần re-fetch dùng
    đúng iterations/horizon/seed thật (không phải một lần mô phỏng rẻ tiền
    khác) để không hiện con số khác với con số đã dùng để chấm điểm. `[]`
    (không phải lỗi) khi không lấy lại được `BotResult` -- các mục tương
    ứng đơn giản là không hiện, đúng hành vi "không có dữ liệu thì ẩn mục,
    không bịa" report_page.py đã áp dụng cho mọi mục khác. `assets`' riêng
    `last_close_days`/`state` là ảnh chụp tại `generated_at_ms` của LẦN GHI
    NÀY, không phải tính lại theo giờ đọc -- cùng mức "đóng băng tại thời
    điểm chấm" mọi trường khác trong `bang_chung` đã áp dụng; banner "quá 24
    giờ" đã có sẵn trên trang phục vụ từ file là tín hiệu cho việc này cũ
    tới đâu, không cần một cơ chế tính lại riêng.

    Khác với ba trường ở trên, `observed_symbols`/`symbol_exposure_share`/
    `primary_share_pct`/`secondary_market` (Việc 2/3, không phải tham số của
    hàm này) không cần truyền qua `extra_by_code` -- `row` (`BotEvaluationRow`,
    cohort.py) đã tự mang `exposure_share` và ba trường `secondary_*` từ
    trước, nên đọc thẳng từ `row` (xem `_observed_symbols_desc`/`_share_pct`/
    `_secondary_market_payload` ở đầu file này). `{}`/`None` khi bot không
    có exposure nào đo được, hoặc khi không có mã thứ hai đủ điều kiện --
    không suy diễn, không báo lỗi. File assessment.json ghi TRƯỚC Việc này
    đơn giản là không có bốn khoá này; `assessment_to_analyze_result`
    (data.py) dùng `.get(...)` nên đọc lại vẫn an toàn.

    Cùng cách đọc thẳng từ `row`, giờ có thêm ba khoá của đợt phủ sóng theo
    mục tiêu (xem Agent/backend/market/coverage.py và
    `BotEvaluationRow.resolved_markets`/`unresolved_markets`/
    `coverage_achieved_pct`, cohort.py): `resolved_markets` (mọi thị trường
    đã giải được, `secondary_market` ở trên chỉ là thị trường xếp hạng cao
    nhất trong danh sách này), `unresolved_markets` (mã nằm trong kế hoạch
    nhưng không lấy được dữ liệu, kèm lý do) và `coverage_achieved_pct` (tỉ
    trọng THẬT đã phủ, không phải mục tiêu 80%). `[]`/`None` theo cùng quy
    tắc trên; file cũ (trước đợt này) không có ba khoá này.
    """
    paragraphs = recommendation_vi(row)
    strategy_extra = strategy_extra or {}
    behavioral_extra = behavioral_extra or {}
    return {
        "step": "3_QC_ASSESSMENT",
        # v1 -> v2: thêm `bang_chung.closed_trade_series`,
        # `bang_chung.assets` và `mo_phong.horizon_scenarios` (xem docstring
        # hàm này). File v1 cũ vẫn đọc được nguyên vẹn --
        # `assessment_to_analyze_result` (data.py) dùng `.get(...)` nên các
        # khoá mới vắng mặt chỉ đơn giản là ẩn mục tương ứng, không lỗi.
        "schema_version": "bot_assessment.v3",
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
        # Việc 4: the LLM-authored "nhận định chuyên môn" (see this
        # function's own docstring for `narrative_text`), generated -- when
        # generated at all -- from exactly THIS row's own already-scored
        # numbers by run_report.py, never a stale one from a previous run.
        # `None` when the narrative feature is off (default), `--no-narrative`
        # was passed, or generation degraded for this bot -- same "always
        # present, `None` when not applicable" contract every other optional
        # field in this file already follows.
        "expert_assessment": narrative_text,
        # The narrative comes first in the file because it is the deliverable;
        # everything under it exists to be checked against it.
        "recommendation": {
            "verdict": row.verdict,
            "action": row.recommended_action,
            "quality_score": row.quality_score,
            "risk_score": row.risk_score,
            "confidence": row.confidence,
            "reasons": row.verdict_reason,
            "text": paragraphs,
            "text_full": "\n\n".join(paragraphs),
        },
        "scoring": {
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
            "unknown_dimension_reasons": row.unknown_dimension_reasons,
            "dimension_weights": row.dimension_weights,
            "dimension_confidence": row.dimension_confidence,
            "total_weight": row.total_weight,
            "applicable_dimensions": row.applicable_dimensions,
            "quality_score": row.quality_score,
            "quality_components": row.quality_components,
            "quality_notes": row.quality_notes,
            "hidden_risk_flags": row.hidden_risk_flags,
        },
        "evidence": {
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
            # Việc 1 (assessment side): `row` above already carries the
            # phase-derived fields cohort.py fills onto `BotEvaluationRow`
            # directly; these four cannot come from `row` (that schema does
            # not carry them -- off-limits to edit, see this function's own
            # docstring) so they arrive via `strategy_extra` instead, `None`/
            # empty when it was not supplied.
            "observed_profile": strategy_extra.get("observed_profile"),
            "declared_strategy": strategy_extra.get("declared_strategy"),
            "entry_style_evidence": strategy_extra.get("entry_style_evidence"),
            "tested_in_trend": strategy_extra.get("tested_in_trend"),
            "phase_breakdown": strategy_extra.get("phase_breakdown") or [],
            # Behavioural observation -- computed for every bot and already
            # driving the `behavioral_risk` dimension score above, but never
            # persisted here before Việc 1.
            "martingale_escalation_detected": behavioral_extra.get(
                "martingale_escalation_detected"
            ),
            "averaging_down_detected": behavioral_extra.get("averaging_down_detected"),
            "loss_chasing_score": behavioral_extra.get("loss_chasing_score"),
            "overtrading_score": behavioral_extra.get("overtrading_score"),
            "reentry_loop_detected": behavioral_extra.get("reentry_loop_detected"),
            "size_escalation_score": behavioral_extra.get("size_escalation_score"),
            "leverage_escalation_detected": behavioral_extra.get(
                "leverage_escalation_detected"
            ),
            "behavioral_risk_tier": behavioral_extra.get("behavioral_risk_tier"),
            # Chuỗi lệnh ĐÃ CHỐT (close_time/realized_pnl mỗi lệnh, tăng dần
            # theo thời gian) -- xem docstring hàm này. Đây là dữ liệu duy
            # nhất `report_page.py::_extract_trade_pnls` đọc để vẽ đường vốn
            # tích luỹ; `[]` khi không có (không suy diễn từ các số tổng hợp
            # khác).
            "closed_trade_series": closed_trade_series or [],
            # Trạng thái từng tài sản (đang giao dịch/chỉ đang ôm/đã rời) --
            # xem docstring hàm này. Đây là khoá duy nhất
            # `report_page.py::_render_assets` đọc (qua khoá gốc `assets`
            # data.py map ra); `[]` khi không có -- ẩn cả bảng, không suy
            # diễn trạng thái từ số liệu khác.
            "assets": assets or [],
            # Việc 2: xem module comment ngay trên `_observed_symbols_desc`
            # ở đầu file này. `{}`/`[]` khi bot không có exposure nào đo
            # được (không suy diễn) -- file assessment.json CŨ (ghi trước
            # khi ba khoá này tồn tại) đơn giản là không có chúng, đọc lại ở
            # `assessment_to_analyze_result` (data.py) dùng `.get(...)` nên
            # không vỡ.
            "observed_symbols": _observed_symbols_desc(row.exposure_share),
            "symbol_exposure_share": dict(row.exposure_share or {}),
            "primary_share_pct": _share_pct(row.exposure_share, row.traded_symbol),
            # Việc 3: thị trường đứng thứ hai -- xem
            # `_secondary_market_payload` ở đầu file này.
            "secondary_market": _secondary_market_payload(row),
            # Phủ sóng theo mục tiêu -- xem `_resolved_markets_payload`/
            # `_unresolved_markets_payload` ở đầu file này. `coverage_achieved_pct`
            # là tỉ trọng THẬT đã phủ được (0-100), KHÔNG phải mục tiêu 80%;
            # `None` khi bot không đo được exposure nào (khác `0.0`).
            "resolved_markets": _resolved_markets_payload(row),
            "unresolved_markets": _unresolved_markets_payload(row),
            "coverage_achieved_pct": (
                round(row.coverage_achieved_pct, 2)
                if isinstance(getattr(row, "coverage_achieved_pct", None), (int, float))
                else None
            ),
            # Cùng TÊN KHOÁ mà đường chấm sống dùng
            # (`web/data.py::_full_result`), để hai hình dạng hội tụ thay vì
            # mỗi bên một kiểu. Thiếu nó, khối giải thích ĐỘ TIN CẬY phải
            # nói "bản ghi đã lưu không mang chi tiết này" cho gần như mọi
            # bot, vì phần lớn lượt xem thật đọc từ đĩa chứ không chấm sống.
            # `score_basis.full_confidence_basis` đọc khoá này với mặc định
            # `True`. Không lưu nó nghĩa là mọi bot đọc từ đĩa đều được coi
            # như CÓ bối cảnh thị trường, kể cả bot mà hệ thống không có dữ
            # liệu thị trường -- tức khối giải thích độ tin cậy im lặng bỏ
            # qua đúng một giới hạn mà nó sinh ra để nói.
            "market_available": row.market_available,
            "data_quality": {
                "overall_score": row.data_quality_overall_score,
                "freshness_score": row.data_quality_freshness_score,
                "completeness_score": row.data_quality_completeness_score,
            },
        },
        "simulation": {
            "method": "STATIONARY_BOOTSTRAP",
            "scope": "CLOSED_TRADES_ONLY",
            "iterations": row.mc_iterations,
            "horizon_trades": row.mc_horizon,
            "profit_pct_worst": row.profit_pct_worst,
            "profit_pct_p05": row.profit_pct_p05,
            "profit_pct_p50": row.profit_pct_p50,
            "profit_pct_p95": row.profit_pct_p95,
            "profit_pct_p25": row.profit_pct_p25,
            "profit_pct_p75": row.profit_pct_p75,
            "median_max_drawdown": row.median_max_drawdown,
            "p90_max_drawdown": row.p90_max_drawdown,
            "p99_max_drawdown": row.p99_max_drawdown,
            "sample_is_thin": row.simulation_sample_is_thin,
            "warnings": row.simulation_warnings,
            "observed_span_days": row.observed_span_days,
            "horizon_calendar_days": row.horizon_calendar_days,
            "horizon_exceeds_observed": row.horizon_exceeds_observed,
            "horizon_stability_label": row.horizon_stability_label,
            "var_95_pct": row.var_95_pct,
            "cvar_95_pct": row.cvar_95_pct,
            "mar_ratio_median": row.mar_ratio_median,
            "profit_factor_median": row.profit_factor_median,
            "p95_max_drawdown": row.p95_max_drawdown,
            "worst_drawdown": row.worst_drawdown,
            "p_ruin": row.p_ruin,
            "p_loss_after_horizon": row.p_loss_after_horizon,
            "p_5_loss_streak": row.p_5_loss_streak,
            "p_10_loss_streak": row.p_10_loss_streak,
            "p_5_loss_streak_baseline": row.p_5_loss_streak_baseline,
            "p_10_loss_streak_baseline": row.p_10_loss_streak_baseline,
            "p_5_loss_streak_excess": row.p_5_loss_streak_excess,
            "p_10_loss_streak_excess": row.p_10_loss_streak_excess,
            "deferred_loss_bias": row.simulation_deferred_loss_bias,
            "psr": row.psr,
            "deflated_sharpe": row.deflated_sharpe,
            "min_track_record_trades": row.min_track_record_trades,
            "selection_trials": row.selection_trials,
            "inference_reliable": row.inference_reliable,
            "stress_verdict": row.stress_verdict,
            # So sánh SHORT/MEDIUM/LONG của CHÍNH lần mô phỏng đã chấm bot
            # này -- xem docstring hàm này. Giữ nguyên các khoá
            # `report_page.py::_render_horizon_comparison`/
            # `_render_horizon_probability_chart` đọc (label, horizon_trades,
            # probability_of_profit, p_loss_after_horizon, p_ruin, ...) vì
            # đây là `HorizonOutcome.model_dump(mode="json")` nguyên bản,
            # không đổi tên. `[]` khi không có.
            "horizon_scenarios": horizon_scenarios or [],
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


def build_assessments(
    report: Any,
    data_dir: Path,
    *,
    extra_by_code: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Tuple[Path, Dict[str, Any]]]:
    """Build every scored bot's `(path, payload)` -- the pure half of
    `persist()` below, with no I/O of its own. Split out so a caller can
    inspect exactly what WOULD be written (Việc 4's own `--no-write` test
    requirement: `run_report.py --bot <mã> --no-write` must still produce a
    narrative a test can check, without touching disk) without duplicating
    the slot-resolution/folder-naming logic `persist()` already has.

    `extra_by_code` (default `None`, so an existing caller is unaffected) is
    `{unique_code: {"strategy": {...}, "behavioral": {...}, "narrative":
    "...", "closed_trade_series": [...], "horizon_scenarios": [...],
    "assets": [...]}}`, exactly the shape `run_report.py` builds via
    `Agent/backend/web/data.py`'s `_strategy_evidence`/`_behavioral_evidence`
    plus its own freshly-generated narrative text and re-fetched
    `BotResult` evidence -- see `build_assessment`'s own docstring for what
    each sub-key fills in.
    """
    root = Path(data_dir) / ASSESSMENT_DIRNAME
    slots = _slot_index(Path(data_dir))
    extra_by_code = extra_by_code or {}
    out: List[Tuple[Path, Dict[str, Any]]] = []

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
        extra = extra_by_code.get(row.unique_code) or {}
        payload = build_assessment(
            row,
            report.generated_at_ms,
            f"{venue}/{symbol}",
            strategy_extra=extra.get("strategy"),
            behavioral_extra=extra.get("behavioral"),
            narrative_text=extra.get("narrative"),
            closed_trade_series=extra.get("closed_trade_series"),
            horizon_scenarios=extra.get("horizon_scenarios"),
            assets=extra.get("assets"),
        )
        out.append((bot_dir / "assessment.json", payload))
    return out


def persist(
    report: Any,
    data_dir: Path,
    *,
    extra_by_code: Optional[Dict[str, Dict[str, Any]]] = None,
    write: bool = True,
) -> List[str]:
    """Write one assessment.json per scored bot. Returns the paths -- see
    `build_assessments` above for `extra_by_code`.

    `write=False` (default `True`, so every pre-existing caller keeps
    writing exactly like before) builds every payload and returns the same
    path list WITHOUT touching disk at all -- `run_report.py`'s own
    `--no-write` flag, so a single-bot test run can still be inspected (via
    `build_assessments` directly, or by re-reading the returned paths once a
    real run enables writing) without ever creating/overwriting a file.
    """
    root = Path(data_dir) / ASSESSMENT_DIRNAME
    written: List[str] = []
    summary: List[Dict[str, Any]] = []

    for path, payload in build_assessments(
        report, data_dir, extra_by_code=extra_by_code
    ):
        if write:
            _write(path, payload)
        written.append(str(path))
        bot = payload["bot"]
        khuyen_nghi = payload["recommendation"]
        summary.append(
            {
                "nick_name": bot["nick_name"],
                "unique_code": bot["unique_code"],
                "slot": bot["slot"],
                "verdict": khuyen_nghi["verdict"],
                "quality_score": khuyen_nghi["quality_score"],
                "risk_score": khuyen_nghi["risk_score"],
                "file": str(path),
            }
        )

    # HỢP NHẤT, KHÔNG THAY THẾ. `summary` chỉ chứa các bot của LƯỢT CHẠY
    # NÀY. Một lượt quét đầy đủ thì đó là toàn bộ đàn, nên hợp nhất cho ra
    # đúng kết quả như ghi đè. Nhưng lượt chạy lại MỘT bot -- đúng thứ nút
    # "Re-analyze" gọi mỗi lần người dùng bấm -- cũng đi qua đây, và việc
    # ghi đè khi ấy cắt `index.json` từ cả đàn xuống còn đúng một hàng.
    # Hậu quả không nhìn thấy trên web (trang danh sách duyệt thẳng thư mục)
    # nhưng bóp nghẹt MCP: `agent_server.list_assessed_bots` đọc index, nên
    # sau một cú bấm nút, khách gọi qua marketplace chỉ còn thấy 1 trong 31
    # bot. Hàng cũ chỉ được giữ khi file của nó CÒN trên đĩa, để một bot đã
    # bị xoá không sống sót mãi trong index.
    merged: Dict[str, Dict[str, Any]] = {}
    existing = _read_index_rows(root / "index.json")
    for row in existing:
        code = str(row.get("unique_code") or "")
        file_path = row.get("file")
        if not code or not file_path or not Path(str(file_path)).exists():
            continue
        merged[code] = row
    for row in summary:
        merged[str(row.get("unique_code") or "")] = row
    merged.pop("", None)
    all_rows = sorted(merged.values(), key=lambda r: str(r.get("unique_code") or ""))

    index = {
        "step": "3_QC_ASSESSMENT",
        "generated_at_ms": report.generated_at_ms,
        "bots_assessed": len(all_rows),
        "bots_this_run": len(summary),
        "note": (
            "One assessment.json per bot: quality score, risk score, verdict, "
            "reasons, and the full written recommendation. The text is the "
            "main content; the metrics below it are the evidence behind it."
        ),
        "bots": all_rows,
    }
    index_path = root / "index.json"
    if write:
        _write(index_path, index)
        renumber_ranks(data_dir)
    written.append(str(index_path))
    return written


def _read_index_rows(path: Path) -> List[Dict[str, Any]]:
    """Các hàng trong `index.json` đang có, `[]` khi thiếu hoặc không đọc nổi.

    Cố ý nuốt lỗi: `index.json` là bản tóm tắt dựng lại được từ chính các
    file `assessment.json`, nên một bản ghi hỏng không đáng để làm hỏng cả
    lượt ghi -- trường hợp xấu nhất là quay về đúng hành vi cũ (chỉ giữ các
    bot của lượt này).
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    rows = data.get("bots") if isinstance(data, dict) else None
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []




# Thứ tự mức rủi ro dùng để xếp hạng. BẢN SAO CÓ CHỦ Ý của `TIER_ORDER`
# trong `cohort.py`: import ngược từ đây sang đó tạo vòng import (cohort
# đã import module này). Hai bảng phải khớp; `Agent/test/test_assessment_
# store.py` khoá bằng cách so trực tiếp với bản gốc, nên lệch là đỏ ngay.
_RANK_TIER_ORDER = {
    "EMERGENCY": 0,
    "CRITICAL": 1,
    "HIGH": 2,
    "ELEVATED": 3,
    "WATCH": 4,
    "UNKNOWN": 5,
    "HEALTHY": 6,
}


def renumber_ranks(data_dir: Path) -> int:
    """Đánh lại `rank_in_cohort` cho TOÀN BỘ bot đã chấm trên đĩa.
    Trả về số file phải sửa.

    VÌ SAO: thứ hạng là thuộc tính của CẢ QUẦN THỂ, không phải của lượt chạy
    sinh ra nó. Nhưng `CohortAssessmentService.scan()` xếp hạng trong đúng
    cohort nó vừa quét, nên một lượt chạy lẻ -- nút "Re-analyze", `--bot X`,
    poller -- luôn cho ra hạng 1, rồi ghi đè. Trên đĩa đã có lúc HAI bot
    cùng mang hạng 1.

    Giữ lại hạng cũ cũng không cứu được: bot chưa từng nằm trong một lượt
    chấm cả đàn thì hạng cũ của nó cũng là số bịa. Cách duy nhất đúng là
    tính lại từ chính dữ liệu của cả quần thể -- và mọi trường cần thiết
    (`risk_tier`, `risk_score`, `bot_id`) đều đã nằm sẵn trong từng file,
    nên không phải chấm lại bot nào.

    Dùng ĐÚNG khoá sắp xếp mà `cohort.py` dùng, để hạng đọc từ đĩa và hạng
    của một lượt chấm cả đàn không bao giờ nói hai điều khác nhau.
    """
    root = Path(data_dir) / ASSESSMENT_DIRNAME
    docs = []
    for path in sorted(root.glob("*/*/bot/*/assessment.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        bot = doc.get("bot") or {}
        scoring = doc.get("scoring") or {}
        docs.append((path, doc, bot, scoring))

    docs.sort(
        key=lambda item: (
            _RANK_TIER_ORDER.get(str(item[3].get("risk_tier") or ""), 9),
            -(item[3].get("risk_score") or 0.0),
            str(item[2].get("bot_id") or item[2].get("unique_code") or ""),
        )
    )
    changed = 0
    for rank, (path, doc, bot, _scoring) in enumerate(docs, 1):
        if bot.get("rank_in_cohort") == rank:
            continue
        bot["rank_in_cohort"] = rank
        _write(path, doc)
        changed += 1
    return changed


def rebuild_index(data_dir: Path, *, write: bool = True) -> Dict[str, Any]:
    """Dựng lại `index.json` từ CHÍNH các file `assessment.json` trên đĩa.

    `index.json` là dữ liệu DẪN XUẤT: mọi trường trong nó đều đọc được từ
    file của từng bot. Nên khi hai thứ lệch nhau, file của bot là bản đúng
    và index là bản phải sửa -- đó là việc hàm này làm.

    Cần vì index đã từng bị `persist_assessment` ghi đè bằng đúng tập bot
    của một lượt chạy lẻ (xem chú thích tại chỗ hợp nhất ở trên), cắt nó từ
    cả đàn xuống một hàng. Chỗ hợp nhất chặn việc đó tái diễn; hàm này chữa
    một index đã bị cắt, mà không phải chấm lại bot nào.
    """
    root = Path(data_dir) / ASSESSMENT_DIRNAME
    rows: List[Dict[str, Any]] = []
    for path in sorted(root.glob("*/*/bot/*/assessment.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        bot = payload.get("bot")
        rec = payload.get("recommendation")
        if not isinstance(bot, dict) or not isinstance(rec, dict):
            continue
        rows.append(
            {
                "nick_name": bot.get("nick_name"),
                "unique_code": bot.get("unique_code"),
                "slot": bot.get("slot"),
                "verdict": rec.get("verdict"),
                "quality_score": rec.get("quality_score"),
                "risk_score": rec.get("risk_score"),
                "file": str(path),
            }
        )
    rows.sort(key=lambda r: str(r.get("unique_code") or ""))
    index = {
        "step": "3_QC_ASSESSMENT",
        "generated_at_ms": int(time.time() * 1000),
        "bots_assessed": len(rows),
        "rebuilt_from_disk": True,
        "note": (
            "One assessment.json per bot: quality score, risk score, verdict, "
            "reasons, and the full written recommendation. The text is the "
            "main content; the metrics below it are the evidence behind it."
        ),
        "bots": rows,
    }
    if write:
        _write(root / "index.json", index)
    return index


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


