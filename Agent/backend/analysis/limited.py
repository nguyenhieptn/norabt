"""Limited assessment for a bot whose order book OKX will not show.

Context: Agent/backend/sources/bot_source.py's LiveBotDataSource.get_ledger
raises LedgerUnavailableError when a uniqueCode's ledger endpoints
(public-subpositions-history / public-current-subpositions) answer OKX error
60004 ("Trader doesn't exist"). Measured against a 36-lead-trader sample
pulled straight off the ranking, 7/36 (19%) of bots do this while every other
endpoint about them (public-lead-traders, public-weekly-pnl, public-stats)
keeps answering normally -- this is not a rare edge case, and it is not a
total data loss either: it is the loss of exactly one layer (the trade-level
ledger), with the aggregate layer still intact.

This module is deliberately NOT a shortcut into Agent/backend/qc's full
10-dimension pipeline (QCCoreService / RiskFusionEngine). That pipeline is
built entirely on top of a full BotResult, which itself requires a trade
ledger (TradeLedgerManager, DeferredLossProfile, per-trade Monte Carlo,
phase attribution, ...) -- forcing a LIMITED bot's thin aggregate data
through it would either crash on missing ledger fields or, worse, silently
manufacture plausible-looking numbers (a fabricated profit factor, a
fabricated phase breakdown) out of data that was never trade-level to begin
with. So this module recomputes a small, independent, honestly-labelled
assessment from only what a 60004 bot still publishes:

  - a weekly account-equity curve (Agent/backend/mcp/capital/equity_curve.py,
    reused as-is -- it already only needs weekly PnL/PnL-ratio rows, which
    survive 60004)
  - public-stats' winRatio/investAmt/profitDays/lossDays
  - the lead-trader ranking row (aum/pnl/pnlRatio/leadDays/rank)

and it says plainly, in both `unavailable` and `text`, which of the full
pipeline's usual dimensions (profit factor, deferred loss, phase analysis,
Monte Carlo, PSR/DSR) it could not touch, because every one of them needs
individual trade rows this bot will not show.

Fail-closed scoring, not neutral scoring
-----------------------------------------
Agent/backend/qc/scoring/fusion.py's own UNKNOWN handling (see
Agent/backend/qc/evaluator/common.py's `unknown()`) scores a dimension it
cannot evaluate at a neutral 50/100 with zero weight-bearing confidence --
appropriate there because in the FULL pipeline "unknown" usually means an
ordinary, incidental data gap for an otherwise-cooperative bot (a market
feed hiccup, a dropped-off leaderboard rank).

That reasoning does not transfer here. In a LIMITED assessment, "unknown"
specifically means the bot itself chose not to publish the one thing every
missing dimension is computed from. Scoring that neutrally (or excluding it
as NOT_APPLICABLE, i.e. weight 0) would make concealment read as "no
evidence either way" -- which would let a bot that hides its ledger end up
looking as good as, or better than, an equally-performing bot that publishes
one. That is the one outcome this module must never produce (see
`test_limited_bot_never_scores_better_than_an_equivalent_transparent_bot` in
Agent/test/test_limited_assessment.py). So every dimension this module
cannot compute is scored as an ELEVATED risk contributor with zero
confidence (see _OPACITY_RISK_SCORE below), never a neutral 50 and never
weight-0 -- "unknown pushes risk up," not "unknown falls back to safe."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from Agent.backend.mcp.capital.equity_curve import EquityCurve, EquityCurveBuilder
from Agent.backend.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.mcp.schemas.bot_result import PositionSide, TradeLedgerItem

# ---------------------------------------------------------------------------
# Vocabulary shared with Agent/backend/sources/bot_source.LedgerUnavailableError.
# Repeated as plain strings (not imported) so this module has zero import-time
# dependency on bot_source -- it only needs the values a LedgerUnavailableError
# already carries, handed to it as plain arguments, not the exception type
# itself. That keeps this module callable from a unit test with hand-built
# dicts, with no OKX client or exception plumbing involved.
# ---------------------------------------------------------------------------
STATUS_LIMITED = "LIMITED"
STATUS_NOT_FOUND = "NOT_FOUND"

# Dimensions the FULL pipeline (Agent/backend/qc/*) computes but this module
# structurally cannot, in every case, because each one needs individual
# trade rows a 60004 ledger will never provide:
#   profit_factor    -- gross profit / gross loss over individual trades
#   deferred_loss    -- marking open positions to market against realized PnL
#   phase_analysis   -- attributing each trade to a market regime
#   psr_dsr          -- probabilistic/deflated Sharpe over a trade return series
# monte_carlo is handled separately (see _run_monte_carlo_probe): it is
# attempted for real against the weekly PnL series and only ends up in this
# list if the real engine says the sample is too small (see module docstring
# of Agent/backend/mcp/analytics/simulation/monte_carlo.py).
ALWAYS_UNAVAILABLE = ["profit_factor", "deferred_loss", "phase_analysis"]
MONTE_CARLO_KEY = "monte_carlo"
PSR_DSR_KEY = "psr_dsr"

# Score an unavailable/concealed dimension is given instead of a neutral 50 --
# OKX's own HIGH-tier boundary (see Agent/backend/qc/evaluator/common.tier_for),
# chosen so concealment reads as a real risk contributor, not noise. See the
# module docstring's "Fail-closed scoring" section for why 50 (fusion.py's
# ordinary UNKNOWN score) would be wrong here.
_OPACITY_RISK_SCORE = 75.0
_OPACITY_WEIGHT = 1.3

# Same fail-closed treatment (elevated, not neutral) for a dimension that IS
# attempted from what data survives 60004 but comes back unusable (e.g. the
# weekly equity curve has too few precise-enough points to derive a drawdown
# percentage) -- lower than _OPACITY_RISK_SCORE because this is a genuine data
# gap, not the bot withholding anything, but still must not default to safe.
_UNKNOWN_GAP_SCORE = 65.0

_DRAWDOWN_WEIGHT = 1.1
_STABILITY_WEIGHT = 1.0

# However clean every surface number looks, a LIMITED assessment can never
# reach the confidence a FULL one can -- it has zero trade-level evidence by
# construction. This hard ceiling makes that true regardless of how the
# weighted components below land (see the "same surface stats" test in
# Agent/test/test_limited_assessment.py, which checks this against a real
# QCCoreService.assess_bot confidence for a comparably clean bot).
LIMITED_CONFIDENCE_CEILING = 40.0

# NOT_FOUND carries no evidence about a real bot at all, so confidence is
# fixed at zero rather than derived from any formula (there is nothing to
# derive it from).
NOT_FOUND_CONFIDENCE = 0.0

# Enough for a stable Monte Carlo read without a multi-second run -- this
# module's simulation input is at most a couple of dozen weekly points, so
# the engine's own per-batch cost is trivial regardless of iteration count.
_MONTE_CARLO_ITERATIONS = 2_000
_MONTE_CARLO_SEED = 42
_WEEK_MS = 7 * 24 * 3_600 * 1_000


def _float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> Optional[int]:
    as_float = _float(value)
    return None if as_float is None else int(round(as_float))


@dataclass
class _Component:
    """One scored input to the blended risk/confidence numbers below.

    Mirrors the shape of Agent/backend/qc/schemas/risk_assessment
    .DimensionEvaluation just closely enough to be readable side by side with
    the FULL pipeline's own dimensions -- it is intentionally NOT that class
    (no pydantic dependency here, no NOT_APPLICABLE status: see module
    docstring for why every gap here is scored, never excluded).
    """

    name: str
    label_vi: str
    score: float
    weight: float
    status: str  # "AVAILABLE" | "UNKNOWN_GAP" | "UNKNOWN_CONCEALED"
    confidence: float
    findings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label_vi,
            "score": round(self.score, 1),
            "weight": self.weight,
            "status": self.status,
            "confidence": self.confidence,
            "findings": list(self.findings),
        }


def _drawdown_component(curve: EquityCurve) -> _Component:
    """Same thresholds Agent/backend/qc/evaluator/lenses/drawdown_risk.py uses
    for its own AVAILABLE case (score 15 baseline, +50 past 30%, +25 past
    15%) -- kept numerically aligned so a LIMITED and a FULL assessment of
    comparable drawdowns land on comparable scores, and only the concealment
    penalty (not a different drawdown formula) is what can separate them.
    """
    if curve.wiped_out:
        return _Component(
            "drawdown",
            "Sụt vốn (suy từ đường vốn tuần)",
            100.0,
            _DRAWDOWN_WEIGHT,
            "AVAILABLE",
            0.55,
            [
                "Đường vốn tuần từng về 0 trong giai đoạn quan sát: tài khoản "
                "đã cháy vốn ít nhất một lần"
            ],
        )
    if curve.is_usable and curve.max_drawdown_pct is not None:
        score = 15.0
        findings = [
            f"Sụt vốn tối đa suy từ đường vốn tuần: {curve.max_drawdown_pct:.1f}% "
            f"(trên {curve.usable_points}/{curve.coverage_weeks} tuần có dữ liệu "
            "dùng được)"
        ]
        if curve.max_drawdown_pct > 30:
            score += 50
        elif curve.max_drawdown_pct > 15:
            score += 25
        if curve.consistency == "FLOWS_DETECTED":
            findings.append(
                "Có dấu hiệu nạp/rút vốn giữa các tuần, thay đổi vốn không chỉ "
                "đến từ giao dịch"
            )
        return _Component(
            "drawdown",
            "Sụt vốn (suy từ đường vốn tuần)",
            min(100.0, score),
            _DRAWDOWN_WEIGHT,
            "AVAILABLE",
            0.55,
            findings,
        )
    # Weekly-pnl itself is one of the endpoints that survives 60004 (see
    # module docstring), so an unusable curve here is a genuine data gap
    # (e.g. every weekly pnlRatio too small to divide by, or no weeks at
    # all) rather than concealment -- still scored elevated, never neutral,
    # per the module's fail-closed rule.
    reason = (
        curve.warnings[0]
        if curve.warnings
        else "Không đủ dữ liệu đường vốn tuần để suy ra % sụt vốn"
    )
    return _Component(
        "drawdown",
        "Sụt vốn (suy từ đường vốn tuần)",
        _UNKNOWN_GAP_SCORE,
        _DRAWDOWN_WEIGHT,
        "UNKNOWN_GAP",
        0.0,
        [reason],
    )


def _stability_component(stats: Optional[Dict[str, Any]]) -> _Component:
    """Win ratio and profit/loss day counts, both from public-stats.

    public-stats' own winRatio is exactly profitDays / (profitDays +
    lossDays) (confirmed against the task's captured sample: 152/365 =
    0.4164 = the published winRatio) -- so the two are not independent
    signals, but winRatio is used when present and the day counts are only
    a fallback, plus reported alongside as corroborating evidence either way.
    """
    win_ratio = _float((stats or {}).get("winRatio"))
    profit_days = _int((stats or {}).get("profitDays"))
    loss_days = _int((stats or {}).get("lossDays"))
    total_days = (profit_days or 0) + (loss_days or 0)
    if (
        win_ratio is None
        and profit_days is not None
        and loss_days is not None
        and total_days > 0
    ):
        win_ratio = profit_days / total_days

    if win_ratio is None:
        return _Component(
            "stability",
            "Tính ổn định (ngày lãi/lỗ)",
            _UNKNOWN_GAP_SCORE,
            _STABILITY_WEIGHT,
            "UNKNOWN_GAP",
            0.0,
            ["Không có public-stats nên không tính được tỷ lệ ngày lãi/lỗ"],
        )

    win_ratio = max(0.0, min(1.0, win_ratio))
    score = (1.0 - win_ratio) * 100.0
    findings = [f"Tỷ lệ thắng (public-stats): {win_ratio * 100:.1f}%"]
    if profit_days is not None and loss_days is not None:
        findings.append(
            f"{profit_days} ngày lãi / {loss_days} ngày lỗ trong cửa sổ đo public-stats"
        )
    invest_amt = _float((stats or {}).get("investAmt"))
    if invest_amt is not None:
        findings.append(f"investAmt (public-stats): {invest_amt:,.0f} USDT")
    return _Component(
        "stability",
        "Tính ổn định (ngày lãi/lỗ)",
        score,
        _STABILITY_WEIGHT,
        "AVAILABLE",
        0.5,
        findings,
    )


def _run_monte_carlo_probe(
    weekly: Optional[List[Dict[str, Any]]],
    curve: EquityCurve,
    iterations: int,
    seed: Optional[int],
) -> Any:
    """Feed the weekly PnL series to the REAL MonteCarloSimulationEngine so
    its own MIN_SAMPLE_SIZE gate is what decides validity here -- never a
    hand-rolled `len(weekly) < 20` check that could silently drift from the
    engine's actual threshold.

    This is the single most important thing this module must get right (see
    module docstring / the task this module was written for): a bot only
    ever publishes a handful of weekly PnL points (12 is typical), and
    MIN_SAMPLE_SIZE=20 means the engine legitimately refuses to run. That
    refusal must be surfaced honestly (is_valid=False, mc=None, plain text
    saying so) -- never smoothed over by lowering the threshold or dressing
    up a 12-point bootstrap as if it were trade-level Monte Carlo.
    """
    rows = [r for r in (weekly or []) if isinstance(r, dict)]
    trades: List[TradeLedgerItem] = []
    for index, row in enumerate(rows):
        pnl = _float(row.get("pnl", row.get("pnl_usdt")))
        if pnl is None:
            continue
        week_ms = EquityCurveBuilder._timestamp_ms(
            row.get("beginTs", row.get("week_start"))
        )
        open_time = week_ms if week_ms is not None else index * _WEEK_MS
        trades.append(
            TradeLedgerItem(
                trade_id=f"WEEKLY_{index}",
                symbol="AGGREGATED_WEEKLY",
                side=PositionSide.NET,
                open_time=open_time,
                close_time=open_time + _WEEK_MS,
                realized_pnl=pnl,
                holding_time_minutes=float(_WEEK_MS / 60_000),
            )
        )
    initial_equity = curve.start_equity if curve.is_usable else None
    return MonteCarloSimulationEngine.run_simulation(
        trades=trades,
        initial_equity=initial_equity,
        iterations=iterations,
        horizon_trades=max(len(trades), 1),
        seed=seed,
    )


def _monte_carlo_component_and_payload(
    weekly: Optional[List[Dict[str, Any]]],
    curve: EquityCurve,
    iterations: int,
    seed: Optional[int],
) -> "tuple[_Component, Optional[Dict[str, Any]], List[str]]":
    result = _run_monte_carlo_probe(weekly, curve, iterations, seed)
    text: List[str] = []
    if not result.is_valid:
        text.append(
            "Không đủ mẫu để mô phỏng Monte Carlo: chỉ có "
            f"{result.sample_size} điểm PnL tuần, trong khi engine yêu cầu tối "
            f"thiểu {MonteCarloSimulationEngine.MIN_SAMPLE_SIZE} mẫu -- không "
            "suy diễn phân phối rủi ro hay bịa số liệu từ 12 điểm tuần"
        )
        component = _Component(
            MONTE_CARLO_KEY,
            "Mô phỏng Monte Carlo",
            _OPACITY_RISK_SCORE,
            _OPACITY_WEIGHT,
            "UNKNOWN_GAP",
            0.0,
            [
                f"is_valid=False ({'; '.join(result.warnings)})"
                if result.warnings
                else "is_valid=False"
            ],
        )
        return component, None, text

    # Rare (needs >= MIN_SAMPLE_SIZE weekly points, i.e. years of lead time),
    # but if the real engine says the sample is big enough, this IS a
    # legitimate -- if coarser-than-trade-level -- bootstrap over real OKX
    # data, not a fabrication, so it is reported rather than discarded.
    summary = (
        "Đủ mẫu để chạy Monte Carlo trên PnL tuần (thô hơn mô phỏng theo từng lệnh)"
    )
    if result.p_mdd_gt_25 is not None:
        summary += f": xác suất sụt vốn >25% là {result.p_mdd_gt_25:.1f}%"
    text.append(summary)
    score = result.p_mdd_gt_25 if result.p_mdd_gt_25 is not None else 50.0
    component = _Component(
        MONTE_CARLO_KEY,
        "Mô phỏng Monte Carlo",
        score,
        _OPACITY_WEIGHT,
        "AVAILABLE",
        0.4,
        [
            f"Mô phỏng trên {result.sample_size} điểm PnL tuần, {result.iterations} lần lặp"
        ],
    )
    payload = result.model_dump()
    return component, payload, text


def _opacity_component(dimension: str, label_vi: str) -> _Component:
    return _Component(
        dimension,
        label_vi,
        _OPACITY_RISK_SCORE,
        _OPACITY_WEIGHT,
        "UNKNOWN_CONCEALED",
        0.0,
        [
            "Cần dữ liệu từng lệnh (sổ lệnh) để tính, mà OKX không công khai "
            "sổ lệnh của bot này"
        ],
    )


_ALWAYS_UNAVAILABLE_LABELS_VI = {
    "profit_factor": "Profit factor",
    "deferred_loss": "Lỗ hoãn (deferred loss)",
    "phase_analysis": "Phân tích theo pha thị trường",
    PSR_DSR_KEY: "PSR / DSR",
}


def _verdict_for_risk(risk: float) -> str:
    if risk >= 80:
        return "RỦI RO CAO (ĐÁNH GIÁ HẠN CHẾ)"
    if risk >= 60:
        return "RỦI RO ĐÁNG CHÚ Ý (ĐÁNH GIÁ HẠN CHẾ)"
    if risk >= 40:
        return "CẦN THẬN TRỌNG (ĐÁNH GIÁ HẠN CHẾ)"
    return "CHƯA ĐỦ BẰNG CHỨNG ĐỂ YÊN TÂM (ĐÁNH GIÁ HẠN CHẾ)"


def assess_limited_bot(
    *,
    code: str,
    status: str,
    reason: str,
    name: Optional[str] = None,
    profile: Optional[Dict[str, Any]] = None,
    stats: Optional[Dict[str, Any]] = None,
    weekly: Optional[List[Dict[str, Any]]] = None,
    monte_carlo_iterations: int = _MONTE_CARLO_ITERATIONS,
    monte_carlo_seed: Optional[int] = _MONTE_CARLO_SEED,
) -> Dict[str, Any]:
    """Build the limited/not-found assessment contract for one uniqueCode.

    `status` must be STATUS_LIMITED or STATUS_NOT_FOUND (the same two values
    Agent/backend/sources/bot_source.LedgerUnavailableError.status carries --
    see assess_from_error below for the direct wiring). `profile`/`stats`/
    `weekly` are the raw dicts/lists OKX returned from public-lead-traders,
    public-stats and public-weekly-pnl respectively; all optional because a
    NOT_FOUND code has none of them, and even a LIMITED one may be missing
    one or two.

    Returns the plain-dict contract other layers depend on (see module
    docstring and Agent/test/test_limited_assessment.py): status/code/name/
    limited_reason/unavailable/verdict/risk/quality/confidence/evidence/mc/
    text. Never raises for the inputs above being None/empty -- absence is
    exactly the case this function exists to describe, not fail on.
    """
    display_name = name or (profile or {}).get("nickName") or code

    if status == STATUS_NOT_FOUND:
        text = [
            f"Không đánh giá được mã {code}: đây là đánh giá hạn chế nhưng "
            "ngay cả các endpoint dự phòng cũng không có dữ liệu.",
            reason,
            "Không tìm thấy mã này ở bảng xếp hạng lead traders, weekly-pnl "
            "hay public-stats của OKX -- nhiều khả năng đây là uniqueCode sai "
            "hoặc không tồn tại, không phải một bot đang che giấu sổ lệnh.",
        ]
        unavailable = list(ALWAYS_UNAVAILABLE) + [MONTE_CARLO_KEY, PSR_DSR_KEY]
        return {
            "status": STATUS_NOT_FOUND,
            "code": code,
            "name": display_name,
            "limited_reason": reason,
            "unavailable": unavailable,
            "verdict": "KHÔNG TÌM THẤY",
            "risk": None,
            "quality": None,
            "confidence": NOT_FOUND_CONFIDENCE,
            "evidence": {"profile": None, "stats": None, "weekly_points": 0},
            "mc": None,
            "text": text,
        }

    if status != STATUS_LIMITED:
        raise ValueError(
            f"assess_limited_bot chỉ nhận LIMITED/NOT_FOUND, nhận '{status}'"
        )

    curve = EquityCurveBuilder.build(weekly or [])
    drawdown = _drawdown_component(curve)
    stability = _stability_component(stats)
    mc_component, mc_payload, mc_text = _monte_carlo_component_and_payload(
        weekly, curve, monte_carlo_iterations, monte_carlo_seed
    )

    opacity_components = [
        _opacity_component(name_, label_)
        for name_, label_ in _ALWAYS_UNAVAILABLE_LABELS_VI.items()
    ]

    components = [drawdown, stability, mc_component] + opacity_components
    total_weight = sum(c.weight for c in components)
    risk = sum(c.score * c.weight for c in components) / total_weight
    risk = max(0.0, min(100.0, risk))

    dimension_confidence = (
        sum(c.confidence * c.weight for c in components) / total_weight
    )
    confidence = min(LIMITED_CONFIDENCE_CEILING, dimension_confidence * 100.0)

    quality = _quality_score(profile, stats, curve)

    unavailable: List[str] = list(ALWAYS_UNAVAILABLE)
    if mc_component.status != "AVAILABLE":
        unavailable.append(MONTE_CARLO_KEY)
    unavailable.append(PSR_DSR_KEY)
    if drawdown.status != "AVAILABLE":
        unavailable.append("drawdown_pct")
    if stability.status != "AVAILABLE":
        unavailable.append("win_ratio")
    if not profile:
        unavailable.append("profile")

    verdict = _verdict_for_risk(risk)

    text: List[str] = [
        f"Đây là ĐÁNH GIÁ HẠN CHẾ cho mã {code} ({display_name}): {reason}",
    ]
    profile_line = _profile_text(profile)
    if profile_line:
        text.append(profile_line)
    text.extend(
        f"{c.label_vi}: {'; '.join(c.findings)}"
        for c in [drawdown, stability]
        if c.findings
    )
    text.extend(mc_text)
    text.append(
        "Không tính được (cần dữ liệu từng lệnh mà OKX không công khai): "
        + ", ".join(_ALWAYS_UNAVAILABLE_LABELS_VI[d] for d in ALWAYS_UNAVAILABLE)
        + ", PSR/DSR"
        + (", Mô phỏng Monte Carlo" if mc_component.status != "AVAILABLE" else "")
    )
    text.append(
        f"Kết luận: {verdict} -- điểm rủi ro {risk:.0f}/100, độ tin cậy "
        f"{confidence:.0f}/100 (thấp hơn hẳn một đánh giá đầy đủ có sổ lệnh, vì "
        "thiếu toàn bộ bằng chứng cấp độ từng lệnh)"
    )

    evidence = {
        "profile": profile,
        "stats": stats,
        "weekly_points": len(weekly or []),
        "equity_curve_basis": curve.basis,
        "components": [c.to_dict() for c in components],
    }

    return {
        "status": STATUS_LIMITED,
        "code": code,
        "name": display_name,
        "limited_reason": reason,
        "unavailable": unavailable,
        "verdict": verdict,
        "risk": round(risk, 1),
        "quality": round(quality, 1),
        "confidence": round(confidence, 1),
        "evidence": evidence,
        "mc": mc_payload,
        "text": text,
    }


def _profile_text(profile: Optional[Dict[str, Any]]) -> Optional[str]:
    if not profile:
        return "Hồ sơ (bảng xếp hạng lead traders): không có (bot đã rớt hạng hoặc ngoài phạm vi bảng xếp hạng)"
    aum = _float(profile.get("aum"))
    pnl = _float(profile.get("pnl"))
    lead_days = _int(profile.get("leadDays"))
    rank = profile.get("rank")
    parts = []
    if aum is not None:
        parts.append(f"AUM {aum:,.0f} USDT")
    if pnl is not None:
        parts.append(f"tổng PnL {pnl:,.0f} USDT")
    if lead_days is not None:
        parts.append(f"{lead_days} ngày làm lead trader")
    if rank is not None:
        parts.append(f"hạng #{rank} trên bảng xếp hạng lead traders")
    return "Hồ sơ: " + (
        ", ".join(parts) if parts else "có trong bảng xếp hạng nhưng thiếu chi tiết"
    )


def _quality_score(
    profile: Optional[Dict[str, Any]],
    stats: Optional[Dict[str, Any]],
    curve: EquityCurve,
) -> float:
    """How good the bot's SURFACE numbers look -- deliberately not "how good
    the bot is": profit factor/payoff/deferred-loss are exactly the things
    this module cannot verify (see module docstring), so quality here can
    only ever describe what public-stats/the ranking/the equity curve show,
    never a verdict on trade-level skill. Capped below AVAILABLE_QUALITY_CAP
    for that reason -- a LIMITED bot can look decent, never "excellent",
    without a ledger to back it up.
    """
    score = 50.0
    lead_days = _int((profile or {}).get("leadDays"))
    if lead_days is not None:
        score += min(15.0, lead_days / 40.0)
    pnl = _float((profile or {}).get("pnl"))
    if pnl is not None:
        score += 10.0 if pnl > 0 else -20.0
    win_ratio = _float((stats or {}).get("winRatio"))
    if win_ratio is not None:
        score += (win_ratio - 0.5) * 40.0
    if curve.wiped_out:
        score -= 30.0
    AVAILABLE_QUALITY_CAP = 75.0
    return max(0.0, min(AVAILABLE_QUALITY_CAP, score))


def assess_from_error(
    exc: Any, *, name: Optional[str] = None, **kwargs: Any
) -> Dict[str, Any]:
    """Convenience wiring for the expected caller shape: catch
    Agent.backend.sources.bot_source.LedgerUnavailableError and hand it here
    directly, e.g.::

        try:
            ledger = source.get_ledger(unique_code)
        except LedgerUnavailableError as exc:
            return assess_from_error(exc)

    Accepts any object exposing .status/.code/.args[0] (the reason
    message)/.profile/.stats/.weekly -- duck-typed rather than importing
    LedgerUnavailableError so this module has no import-time dependency on
    bot_source (see the vocabulary note above STATUS_LIMITED).
    """
    reason = str(exc)
    return assess_limited_bot(
        code=exc.code,
        status=exc.status,
        reason=reason,
        name=name,
        profile=getattr(exc, "profile", None),
        stats=getattr(exc, "stats", None),
        weekly=getattr(exc, "weekly", None),
        **kwargs,
    )
