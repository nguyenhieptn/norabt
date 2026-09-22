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
Agent/none/test/test_limited_assessment.py). So every dimension this module
cannot compute is scored as an ELEVATED risk contributor with zero
confidence (see _OPACITY_RISK_SCORE below), never a neutral 50 and never
weight-0 -- "unknown pushes risk up," not "unknown falls back to safe."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from Agent.backend.bot.analysis.limited_matrix import build_matrix, simulate_matrix
from Agent.backend.bot.analysis.population_reference import population_percentile
from Agent.backend.bot.mcp.capital.equity_curve import EquityCurve, EquityCurveBuilder
from Agent.backend.bot.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.bot.mcp.schemas.bot_result import SimulationResults

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
# Agent/none/test/test_limited_assessment.py, which checks this against a real
# QCCoreService.assess_bot confidence for a comparably clean bot).
LIMITED_CONFIDENCE_CEILING = 40.0

# --- Độ tin cậy tỉ lệ với KHỐI LƯỢNG BẰNG CHỨNG THẬT ----------------------
# Trước đây mỗi chiều đo được mang một độ tin cậy HẰNG SỐ (sụt vốn 0,55; ổn
# định 0,50) bất kể đường vốn có 12 tuần hay 120 tuần. Điều đó mâu thuẫn với
# nguyên tắc của chính sản phẩm: ít dữ liệu thì độ tin cậy phải thấp hơn,
# nhiều dữ liệu thì cao hơn. Ba hằng số dưới đây biến nó thành một hàm bão
# hoà: `sàn + (trần - sàn) * min(1, n / mốc_bão_hoà)`.
#
# `_CONFIDENCE_FLOOR_FRACTION = 0.35`: một chiều ĐÃ ĐO ĐƯỢC không bao giờ bị
# đẩy về gần 0 chỉ vì mẫu nhỏ -- nó vẫn là bằng chứng thật, chỉ là yếu. Đặt
# sàn ở 35% mức trần giữ cho nó còn tiếng nói thay vì bị các chiều bị che
# (vốn confidence = 0) nuốt chửng hoàn toàn.
_CONFIDENCE_FLOOR_FRACTION = 0.35

# 52 tuần = một năm đầy đủ, đủ để đường vốn đi qua cả pha tăng lẫn pha giảm
# ít nhất một lần. Dưới mốc đó thì mức sụt vốn quan sát được chưa chắc đã
# gặp kịch bản xấu nhất của chiến lược.
_DRAWDOWN_SATURATION_WEEKS = 52

# 365 ngày lãi/lỗ: cùng lý do, quy về nhịp NGÀY vì public-stats đếm theo
# ngày chứ không theo tuần.
_STABILITY_SATURATION_DAYS = 365

# --- Chiều mới: nhịp độ đường lợi nhuận tích luỹ --------------------------
# `profile.pnlRatios` (public-lead-traders) là một chuỗi RIÊNG, khác endpoint
# và khác nhịp lấy mẫu với chuỗi PnL tuần (đo thật trên bot
# ED2DE1A47EEF62EC: 19 điểm trải 90 ngày, tức ~5 ngày/điểm, so với 12 điểm
# tuần). Hai chuỗi cùng nói về MỘT tài khoản nên KHÔNG độc lập hoàn toàn --
# vì vậy trọng số ở đây cố tình nhỏ hơn `_DRAWDOWN_WEIGHT`: nó bổ sung thông
# tin về NHỊP ĐỘ (đều đặn hay giật cục) chứ không phải đếm cùng một nguồn
# hai lần.
_RETURN_PATH_WEIGHT = 0.7
_RETURN_PATH_CONFIDENCE_MAX = 0.45
_RETURN_PATH_SATURATION_POINTS = 52
# Dưới ngần này điểm thì đường lợi nhuận chưa đủ để nói về nhịp độ.
_RETURN_PATH_MIN_POINTS = 4

# --- Trần độ tin cậy theo SỐ LUỒNG DỮ LIỆU thật sự kết hợp được -----------
# Trần phẳng 40% cũ coi một bot chỉ còn đúng một luồng ngang với một bot còn
# đủ bốn luồng -- trái với nguyên tắc "ít dữ liệu thì càng phải kết hợp
# nhiều nguồn, và kết hợp được nhiều thì đáng tin hơn".
#
# `_CONFIDENCE_CEILING_PER_STREAM = 7.5` và nền 15.0 cho dải 22,5% (1 luồng)
# đến 45,0% (4 luồng). Trần tuyệt đối 45% được chọn có căn cứ ĐO ĐƯỢC, không
# phải số tròn: độ tin cậy THẤP NHẤT trong 31 bot công khai đầy đủ của kho
# hiện tại là 50,8%. Giữ trần của nhánh LIMITED dưới mốc đó bảo đảm một bot
# giấu sổ lệnh KHÔNG BAO GIỜ được tin bằng con bot minh bạch kém tin cậy
# nhất -- đúng tinh thần fail-closed của module này.
_CONFIDENCE_CEILING_BASE = 15.0
_CONFIDENCE_CEILING_PER_STREAM = 7.5
_CONFIDENCE_CEILING_ABSOLUTE = 45.0


def _evidence_confidence(
    observed: Optional[int], saturation: int, ceiling: float
) -> float:
    """Độ tin cậy của MỘT chiều, tỉ lệ bão hoà với số quan sát thật của nó.

    `observed=None`/<=0 -> 0,0 (không có gì để tin). Ngược lại chạy từ
    `ceiling * _CONFIDENCE_FLOOR_FRACTION` lên tới `ceiling` khi số quan sát
    đạt `saturation`. Tuyến tính chứ không phải 1/sqrt(n): mục đích ở đây là
    một thang TRÌNH BÀY dễ giải thích cho người đọc, không phải một sai số
    chuẩn thống kê -- sai số chuẩn thật đã được nói riêng ở cảnh báo mẫu
    mỏng của chính engine mô phỏng.
    """
    if not observed or observed <= 0:
        return 0.0
    reach = min(1.0, float(observed) / float(saturation))
    floor = ceiling * _CONFIDENCE_FLOOR_FRACTION
    return floor + (ceiling - floor) * reach


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


# Ánh xạ chiều -> (tham số trong kho, trường tương ứng của kết quả mô phỏng).
# Hai tên khác nhau vì file lưu dùng tiền tố `mc_`; ánh xạ này KIỂM TỪ
# `Agent/backend/qc/reporting/pair_report.py` (chỗ ghi ra file), không đoán.
_PERCENTILE_PARAMETERS = {
    "drawdown": ("mc_p95_drawdown", "p95_max_drawdown"),
    MONTE_CARLO_KEY: ("mc_p_ruin", "p_ruin"),
}


def _percentile_scored(
    dimension: str, simulation: Any, data_dir: Optional[Path]
) -> Optional[Dict[str, Any]]:
    """Điểm của một chiều tính bằng HẠNG PHÂN VỊ trong quần thể bot đã chấm.

    Thay cho các cut-point tự đặt (`score = 15`, `+50 nếu > 30%`...): điểm
    giờ trả lời đúng một câu kiểm chứng được -- "tham số này tệ hơn bao
    nhiêu phần trăm số bot đã quan sát". Xem
    `Agent/backend/analysis/population_reference.py` cho lý do đầy đủ.

    `None` khi thiếu mô phỏng, thiếu tham số, hoặc quần thể chưa đủ lớn --
    khi đó nơi gọi giữ nguyên nhánh "không đo được", KHÔNG rơi về thang cũ.
    """
    if simulation is None or not getattr(simulation, "is_valid", False):
        return None
    mapping = _PERCENTILE_PARAMETERS.get(dimension)
    if mapping is None or data_dir is None:
        return None
    stored_key, field = mapping
    value = getattr(simulation, field, None)
    return population_percentile(data_dir, stored_key, value)


def _drawdown_component(
    curve: EquityCurve,
    simulation: Any = None,
    data_dir: Optional[Path] = None,
) -> _Component:
    """Same thresholds Agent/backend/qc/evaluator/lenses/drawdown_risk.py uses
    for its own AVAILABLE case (score 15 baseline, +50 past 30%, +25 past
    15%) -- kept numerically aligned so a LIMITED and a FULL assessment of
    comparable drawdowns land on comparable scores, and only the concealment
    penalty (not a different drawdown formula) is what can separate them.
    """
    if curve.wiped_out:
        return _Component(
            "drawdown",
            "Drawdown (inferred from the weekly equity curve)",
            100.0,
            _DRAWDOWN_WEIGHT,
            "AVAILABLE",
            0.55,
            [
                "Weekly equity dropped to 0 during the observed period: the "
                "account was wiped out at least once"
            ],
        )
    if curve.is_usable and curve.max_drawdown_pct is not None:
        # ƯU TIÊN chấm bằng HẠNG PHÂN VỊ trong quần thể đã chấm. Thang cũ
        # (`15` rồi `+50 nếu > 30%`, `+25 nếu > 15%`) là ba con số không
        # suy ra từ đâu; phân vị thì trả lời được một câu kiểm chứng được:
        # "sụt vốn mô phỏng của bot này tệ hơn bao nhiêu phần trăm số bot
        # đã quan sát". Chỉ rơi về thang cũ khi quần thể chưa đủ lớn -- và
        # khi đó `findings` nói rõ đang dùng thang nào.
        ranked = _percentile_scored("drawdown", simulation, data_dir)
        if ranked is not None:
            return _Component(
                "drawdown",
                "Drawdown (inferred from the weekly equity curve)",
                float(ranked["score"]),
                _DRAWDOWN_WEIGHT,
                "AVAILABLE",
                _evidence_confidence(
                    curve.usable_points, _DRAWDOWN_SATURATION_WEEKS, 0.55
                ),
                [
                    f"Max drawdown inferred from the weekly equity curve: "
                    f"{curve.max_drawdown_pct:.1f}% (over {curve.usable_points}/"
                    f"{curve.coverage_weeks} weeks with usable data)",
                    f"Percentile: simulated P95 drawdown {ranked['value']:.1f}% — worse "
                    f"than {ranked['score']:.0f}% of {ranked['population_size']} scored "
                    f"bots (population median {ranked['population_median']:.1f}%)",
                ],
            )
        score = 15.0
        findings = [
            f"Max drawdown inferred from the weekly equity curve: {curve.max_drawdown_pct:.1f}% "
            f"(over {curve.usable_points}/{curve.coverage_weeks} weeks with usable "
            "data)"
        ]
        if curve.max_drawdown_pct > 30:
            score += 50
        elif curve.max_drawdown_pct > 15:
            score += 25
        if curve.consistency == "FLOWS_DETECTED":
            findings.append(
                "There are signs of deposits/withdrawals between weeks; the capital "
                "change is not entirely from trading"
            )
        return _Component(
            "drawdown",
            "Drawdown (inferred from the weekly equity curve)",
            min(100.0, score),
            _DRAWDOWN_WEIGHT,
            "AVAILABLE",
            _evidence_confidence(curve.usable_points, _DRAWDOWN_SATURATION_WEEKS, 0.55),
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
        else "Not enough weekly equity data to infer a drawdown %"
    )
    return _Component(
        "drawdown",
        "Drawdown (inferred from the weekly equity curve)",
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
            "Stability (winning/losing days)",
            _UNKNOWN_GAP_SCORE,
            _STABILITY_WEIGHT,
            "UNKNOWN_GAP",
            0.0,
            ["No public-stats available, so the winning/losing day ratio could not be computed"],
        )

    win_ratio = max(0.0, min(1.0, win_ratio))
    score = (1.0 - win_ratio) * 100.0
    # GỌI ĐÚNG TÊN: `stats.winRatio` bằng ĐÚNG profitDays/(profitDays +
    # lossDays) -- kiểm trên bot thật: 101/172 = 58,72%, khớp chính xác
    # winRatio công bố -- tức tỉ lệ NGÀY LÃI, không phải tỉ lệ LỆNH
    # THẮNG. Nhãn cũ ghi "Tỷ lệ thắng" khiến người đọc đem so thẳng với
    # "tỉ lệ thắng" của bot công khai đầy đủ (vốn tính trên từng LỆNH)
    # rồi kết luận sai.
    findings = [f"Winning-day ratio (public-stats): {win_ratio * 100:.1f}%"]
    if profit_days is not None and loss_days is not None:
        findings.append(
            f"{profit_days} winning days / {loss_days} losing days in the public-stats measurement window"
        )
    invest_amt = _float((stats or {}).get("investAmt"))
    if invest_amt is not None:
        findings.append(f"investAmt (public-stats): {invest_amt:,.0f} USDT")
    return _Component(
        "stability",
        "Stability (winning/losing days)",
        score,
        _STABILITY_WEIGHT,
        "AVAILABLE",
        _evidence_confidence(total_days or None, _STABILITY_SATURATION_DAYS, 0.5),
        findings,
    )


def _return_path_component(profile: Optional[Dict[str, Any]]) -> _Component:
    """Nhịp độ của đường lợi nhuận tích luỹ, dựng từ `profile.pnlRatios`.

    ĐÂY LÀ LUỒNG DỮ LIỆU THỨ BA, trước nay bị bỏ không: `public-lead-traders`
    trả kèm `pnlRatios` -- chuỗi tỉ lệ lợi nhuận TÍCH LUỸ theo mốc thời gian
    (đo thật trên bot ED2DE1A47EEF62EC: 19 điểm trải 90 ngày, ~5 ngày/điểm,
    trong khi chuỗi PnL tuần chỉ có 12 điểm). Với một bot giấu sổ lệnh, đây
    là chuỗi thời gian DÀI NHẤT còn công khai.

    KHÔNG ĐỘC LẬP HOÀN TOÀN với chuỗi PnL tuần -- cùng một tài khoản, chỉ
    khác endpoint và khác nhịp lấy mẫu -- nên trọng số cố tình đặt thấp hơn
    chiều sụt vốn (`_RETURN_PATH_WEIGHT` < `_DRAWDOWN_WEIGHT`). Cái nó thêm
    vào là thông tin về NHỊP ĐỘ: lợi nhuận đi lên đều đặn hay giật cục rồi
    đứng im, và trên chính đường đó đã có lần thụt lùi nào chưa.

    Đo hai thứ, cả hai đều không cần biết quy mô vốn (nên không dính vấn đề
    lệch mẫu số đã chặn ở `_implied_base_spread`):
      * tỉ lệ kỳ ĐI LÊN trên tổng số kỳ;
      * mức thụt lùi sâu nhất của đường tích luỹ so với đỉnh của chính nó.
    """
    raw = (profile or {}).get("pnlRatios")
    points: List[Dict[str, float]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            ts = EquityCurveBuilder._timestamp_ms(item.get("beginTs"))
            ratio = _float(item.get("pnlRatio"))
            if ts is None or ratio is None:
                continue
            points.append({"ts": float(ts), "ratio": ratio})
    points.sort(key=lambda d: d["ts"])

    if len(points) < _RETURN_PATH_MIN_POINTS:
        return _Component(
            "return_path",
            "Return path cadence",
            _UNKNOWN_GAP_SCORE,
            _RETURN_PATH_WEIGHT,
            "UNKNOWN_GAP",
            0.0,
            [
                "The public pnlRatios series is too short to say anything about cadence "
                f"({len(points)} points, at least {_RETURN_PATH_MIN_POINTS} needed)"
            ],
        )

    steps = [points[i]["ratio"] - points[i - 1]["ratio"] for i in range(1, len(points))]
    ups = sum(1 for d in steps if d > 0)
    downs = sum(1 for d in steps if d < 0)
    flats = len(steps) - ups - downs
    up_share = ups / len(steps) if steps else 0.0

    peak = points[0]["ratio"]
    setback = 0.0
    for point in points:
        peak = max(peak, point["ratio"])
        setback = max(setback, peak - point["ratio"])
    # Quy mức thụt lùi về % của đỉnh để so sánh được giữa các bot; đỉnh <= 0
    # nghĩa là đường tích luỹ chưa từng dương, không có "đỉnh" để so.
    setback_pct = (setback / peak * 100.0) if peak > 0 else None

    # KHÔNG CHẤM ĐIỂM RỦI RO Ở ĐÂY NỮA.
    #
    # Bản đầu của hàm này tự đặt ra một công thức: `(1 - tỉ lệ kỳ tăng) *
    # 100`, cộng thêm `+25` nếu thụt lùi > 30% và `+12` nếu > 15%. Cả ba
    # con số đó là do người viết nghĩ ra, không suy từ lý thuyết nào, không
    # hiệu chỉnh trên dữ liệu nào -- đúng loại tham số bịa mà sản phẩm này
    # cấm. Một tỉ lệ kỳ tăng 61% KHÔNG có nghĩa rủi ro là 39/100.
    #
    # Chiều này vì vậy chỉ mang BẰNG CHỨNG QUAN SÁT ĐƯỢC (số kỳ tăng/giảm,
    # mức thụt lùi trên đường tích luỹ) và độ tin cậy theo số điểm thật;
    # điểm rủi ro của nó để trung tính bằng `_UNKNOWN_GAP_SCORE` như mọi
    # chiều chưa có cách chấm chính đáng. Cách chấm ĐÚNG là đưa chuỗi này
    # qua chính bộ chỉ số + mô phỏng mà nhánh đầy đủ dùng (hiệu các
    # `pnlRatio` là lợi suất trên cùng một mẫu số -- đã kiểm: tổng của
    # chúng bằng đúng tích luỹ 9,3951 mà OKX công bố), việc đó làm ở bước
    # xây ma trận dữ liệu, không phải bằng một công thức tự chế ở đây.
    score = _UNKNOWN_GAP_SCORE

    findings = [
        f"{len(points)} cumulative-return points (public-lead-traders), "
        f"{ups} up periods / {downs} down periods / {flats} flat periods "
        f"({up_share * 100:.0f}% of periods moving up)"
    ]
    if setback_pct is not None:
        findings.append(
            f"Deepest setback on the cumulative return path: {setback_pct:.1f}% "
            "below its own peak"
        )
    return _Component(
        "return_path",
        "Return path cadence",
        score,
        _RETURN_PATH_WEIGHT,
        "AVAILABLE",
        _evidence_confidence(
            len(points), _RETURN_PATH_SATURATION_POINTS, _RETURN_PATH_CONFIDENCE_MAX
        ),
        findings,
    )


# Khoảng dao động TỐI ĐA cho phép của "vốn ngầm" giữa các tuần trước khi
# chuỗi tuần bị coi là KHÔNG dùng được cho bootstrap. Vốn ngầm của một tuần
# = pnl / pnlRatio (OKX công bố cả hai), tức quy mô tài khoản mà tuần đó
# kiếm lãi trên đó.
#
# VÌ SAO PHẢI CÓ (đo thật trên bot ED2DE1A47EEF62EC, 18/09): vốn ngầm 12
# tuần của bot này chạy từ 1.020 tới 81.775 USDT -- chênh 80 lần. Bootstrap
# (dù IID hay khối) đứng trên giả định các quan sát ĐỔI CHỖ ĐƯỢC CHO NHAU
# (exchangeable): rút ngẫu nhiên tuần này thay tuần kia phải hợp lệ. Một
# tuần lãi 763 USDT trên vốn 1.749 và một tuần lãi 56.554 USDT trên vốn
# 79.151 KHÔNG phải hai mẫu của cùng một phân phối -- trộn chúng rồi chia
# cho một mốc vốn duy nhất cho ra con số vô nghĩa: mô phỏng đang chạy trả
# về trung vị +9.839% trong khi lợi nhuận tích luỹ THẬT mà OKX công bố cho
# chính bot đó là +963%, lệch hơn 10 lần.
#
# 3.0 là ngưỡng có chủ đích chứ không phải số tròn tuỳ hứng: vốn tài khoản
# co giãn trong khoảng ±3 lần còn có thể coi là cùng một quy mô hoạt động
# (nạp/rút thông thường, lãi kép tích luỹ), vượt qua đó thì tài khoản đã
# đổi hẳn cấp độ và các tuần không còn so sánh trực tiếp được nữa. Ngưỡng
# này chỉ quyết định CÓ CHẠY mô phỏng hay không; nó không tham gia chấm
# điểm bất kỳ chiều nào.
_MAX_IMPLIED_BASE_SPREAD = 3.0

# Dưới ngưỡng này thì `pnlRatio` coi như bằng 0 và tuần đó không suy ra
# được vốn ngầm (chia cho ~0). Không phải tuần lỗi -- chỉ là tuần không
# dùng được cho phép kiểm tra quy mô.
_MIN_RATIO_FOR_IMPLIED_BASE = 1e-6


def _implied_base_spread(rows: List[Dict[str, Any]]) -> Optional[float]:
    """Tỉ số vốn-ngầm lớn nhất / nhỏ nhất của chuỗi tuần, hoặc `None` khi
    không đủ tuần suy ra được vốn ngầm để kết luận điều gì.

    Trả về một con số để nơi gọi tự quyết định, và để câu giải thích cho
    người đọc có được con số thật thay vì một lời khẳng định suông.
    """
    bases: List[float] = []
    for row in rows:
        pnl = _float(row.get("pnl", row.get("pnl_usdt")))
        ratio = _float(row.get("pnlRatio", row.get("pnl_ratio")))
        if pnl is None or ratio is None or abs(ratio) < _MIN_RATIO_FOR_IMPLIED_BASE:
            continue
        base = abs(pnl / ratio)
        if base > 0.0:
            bases.append(base)
    if len(bases) < 2:
        return None
    return max(bases) / min(bases)


def _run_monte_carlo_probe(
    weekly: Optional[List[Dict[str, Any]]],
    curve: EquityCurve,
    iterations: int,
    seed: Optional[int],
    profile: Optional[Dict[str, Any]] = None,
    stats: Optional[Dict[str, Any]] = None,
) -> Any:
    """Mô phỏng cho bot giấu sổ lệnh, đi qua BƯỚC DỰNG MA TRẬN trước.

    Bản trước nạp thẳng chuỗi PnL TUYỆT ĐỐI theo tuần vào engine và chia cho
    vốn của tuần ĐẦU TIÊN. Trên bot thật ED2DE1A47EEF62EC, cách đó cho trung
    vị **+9.839%** trong khi lợi nhuận tích luỹ OKX công bố chỉ **+940%** --
    sai gần 10 lần, vì vốn ngầm của các tuần chạy từ 1.020 tới 81.775 USDT
    nên các tuần không đổi chỗ được cho nhau.

    Nay việc chọn chuỗi giao cho `Agent/backend/analysis/limited_matrix.py`:
    nó gom mọi luồng công khai, kiểm tiền đề đổi chỗ của từng chuỗi ứng
    viên, rồi chọn chuỗi hợp lệ có nhiều quan sát nhất. Với cùng bot đó nó
    chọn `ratio_delta` (18 kỳ, hiệu của lợi suất tích luỹ -- cùng một mẫu số
    là vốn đầu tư, đã kiểm `pnlRatio x investAmt = pnl` lệch 0,0003%) và
    loại `weekly_absolute`. Trung vị mô phỏng khi đó là **+903%**, nằm ngay
    cạnh +940% quan sát được -- đúng thứ một bootstrap phát lại chính lịch
    sử của bot trên đúng độ dài lịch sử đó phải cho ra.

    `MIN_SAMPLE_SIZE`/`THIN_SAMPLE_SIZE` vẫn hoàn toàn do engine quyết định;
    module này không tự kiểm độ dài lần nữa.
    """
    matrix = build_matrix(profile=profile, stats=stats, weekly=weekly)
    result = simulate_matrix(matrix, iterations=iterations, seed=seed)
    if result is not None:
        return result

    # Không chuỗi nào qua được tiền đề -> từ chối, kèm ĐÚNG lý do từng
    # chuỗi bị loại thay vì một câu chung chung.
    rejected = "; ".join(
        f"{series.name}: {series.reason}"
        for series in matrix.series
        if not series.usable
    )
    return SimulationResults(
        simulation_method="STATIONARY_BOOTSTRAP",
        iterations=0,
        sample_size=0,
        horizon_trades=1,
        return_basis="ABSOLUTE_PNL_RELATIVE_TO_EQUITY",
        capital_basis="WEEKLY_EQUITY_CURVE",
        is_valid=False,
        warnings=[
            "No usable return series to simulate"
            + (f". Detail: {rejected}" if rejected else "")
        ],
    )


def _monte_carlo_component_and_payload(
    weekly: Optional[List[Dict[str, Any]]],
    curve: EquityCurve,
    iterations: int,
    seed: Optional[int],
    profile: Optional[Dict[str, Any]] = None,
    stats: Optional[Dict[str, Any]] = None,
    data_dir: Optional[Path] = None,
) -> "tuple[_Component, Optional[Dict[str, Any]], List[str], Any]":
    result = _run_monte_carlo_probe(
        weekly, curve, iterations, seed, profile=profile, stats=stats
    )
    text: List[str] = []
    if not result.is_valid:
        # Engine/chốt chặn từ chối vì NHIỀU lý do khác nhau, nên phải NÓI
        # LẠI ĐÚNG lý do nó đưa ra thay vì đoán. Bản cũ mặc định "không đủ
        # mẫu" cho mọi lần từ chối; sau khi `_implied_base_spread` xuất
        # hiện, một chuỗi 12 tuần (thừa so với `MIN_SAMPLE_SIZE = 10`) bị
        # từ chối vì quy mô vốn lệch nhau lại vẫn in ra câu "chỉ có 12
        # điểm, trong khi engine yêu cầu tối thiểu 10" -- tự mâu thuẫn ngay
        # trong một câu, và giấu mất lý do thật.
        if result.sample_size < MonteCarloSimulationEngine.MIN_SAMPLE_SIZE:
            # Ca THIẾU MẪU: giữ nguyên câu tiếng Việt cũ. KHÔNG chuyển tiếp
            # cảnh báo của engine ở nhánh này vì câu đó là tiếng Anh ("At
            # least N valid trades are required..."), không phải thứ để đưa
            # thẳng ra cho người đọc bản tiếng Việt.
            text.append(
                "Not enough samples to run a Monte Carlo simulation: only "
                f"{result.sample_size} weekly PnL points, while the engine requires "
                f"at least {MonteCarloSimulationEngine.MIN_SAMPLE_SIZE} samples -- "
                "no risk distribution is inferred or fabricated from that few points"
            )
        else:
            # Ca ĐỦ MẪU MÀ VẪN TỪ CHỐI (quy mô vốn giữa các tuần lệch quá xa
            # -- xem `_MAX_IMPLIED_BASE_SPREAD`): cảnh báo ở nhánh này do
            # chính module này viết bằng tiếng Việt nên chuyển tiếp được.
            reason = "; ".join(w for w in result.warnings if w) or "the engine rejected it"
            text.append(f"Monte Carlo was not simulated for this bot. Reason: {reason}")
        component = _Component(
            MONTE_CARLO_KEY,
            "Monte Carlo simulation",
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
        return component, None, text, result

    # Needs >= MIN_SAMPLE_SIZE weekly points -- with the engine's current
    # threshold (10) a typical 60004 bot's ~12 published weeks already
    # clears it, so this is the COMMON case now, not a rare one (it was rare
    # back when MIN_SAMPLE_SIZE was 20). Either way, if the real engine says
    # the sample is big enough, this IS a legitimate -- if
    # coarser-than-trade-level -- bootstrap over real OKX data, not a
    # fabrication, so it is reported rather than discarded. A sample between
    # MIN_SAMPLE_SIZE and THIN_SAMPLE_SIZE still runs but comes back with
    # `sample_is_thin=True` and its own warning on `result.warnings` (see
    # monte_carlo.py's THIN_SAMPLE_WARNING_VI) -- that warning is surfaced
    # by the presentation layer, not re-derived here.
    summary = (
        "Enough samples to run Monte Carlo on weekly PnL (coarser than a per-trade simulation)"
    )
    if result.p_mdd_gt_25 is not None:
        summary += f": probability of drawdown >25% is {result.p_mdd_gt_25:.1f}%"
    if getattr(result, "sample_is_thin", False):
        summary += " -- THIN SAMPLE, read as a reference band (see the warning below)"
    text.append(summary)
    findings = [f"Simulated over {result.sample_size} periods, {result.iterations} iterations"]
    # ƯU TIÊN hạng phân vị của xác suất cháy tài khoản trong quần thể đã
    # chấm -- một câu kiểm chứng được ("tệ hơn bao nhiêu % số bot"), thay
    # cho con số 50.0 mặc định vô căn cứ ở bản cũ.
    ranked = _percentile_scored(MONTE_CARLO_KEY, result, data_dir)
    if ranked is not None:
        score = float(ranked["score"])
        findings.append(
            f"Percentile: probability of ruin {ranked['value']:.1f}% — worse "
            f"than {ranked['score']:.0f}% of {ranked['population_size']} scored bots "
            f"(population median {ranked['population_median']:.1f}%)"
        )
    elif result.p_mdd_gt_25 is not None:
        # Không phải ngưỡng tự đặt: đây là CHÍNH xác suất sụt vốn quá 25%
        # do mô phỏng trả về, dùng thẳng làm điểm trên cùng thang 0-100.
        score = result.p_mdd_gt_25
        findings.append(
            f"Not enough population to rank by percentile yet; using the probability of "
            f"drawdown >25% directly ({result.p_mdd_gt_25:.1f}%) as the score"
        )
    else:
        return (
            _Component(
                MONTE_CARLO_KEY,
                "Monte Carlo simulation",
                _UNKNOWN_GAP_SCORE,
                _OPACITY_WEIGHT,
                "UNKNOWN_GAP",
                0.0,
                findings
                + ["The simulation ran but returned no risk parameter to score"],
            ),
            result.model_dump(),
            text,
            result,
        )
    component = _Component(
        MONTE_CARLO_KEY,
        "Monte Carlo simulation",
        score,
        _OPACITY_WEIGHT,
        "AVAILABLE",
        _evidence_confidence(result.sample_size, _RETURN_PATH_SATURATION_POINTS, 0.4),
        findings,
    )
    payload = result.model_dump()
    return component, payload, text, result


def _pnl_ratio_series(
    profile: Optional[Dict[str, Any]],
) -> Optional[List[Dict[str, Any]]]:
    """Normalize `profile.pnlRatios` (public-lead-traders' own multi-point
    return series, e.g. 19 `{beginTs, pnlRatio}` rows for a 754-lead-day
    bot) into `[{ts_ms, pnl_ratio_pct}]`, sorted ascending by time.

    This is a DIFFERENT series from the weekly PnL/equity curve (`weekly`
    argument to `assess_limited_bot`, built into `weekly_series` below): it
    is the ranking's own running PnL-ratio snapshot, sampled at whatever
    cadence OKX publishes it at, not one point per calendar week. Reported
    separately, never merged into `weekly_series`, so the report layer can
    show both without implying they share an x-axis.

    `pnlRatio` is treated as a fraction (consistent with
    EquityCurveBuilder's own weekly `pnlRatio` handling, e.g. 0.0432 for
    4.32%), so the stored value here is already multiplied by 100 into a
    plain percentage -- the report layer draws it as-is, no further
    conversion. Rows missing either field are dropped rather than
    zero-filled (see module-level "no fabrication" rule); an all-dropped
    input returns `None`, never `[]`, so callers can hide the chart with one
    falsy check.
    """
    raw = (profile or {}).get("pnlRatios")
    if not isinstance(raw, list):
        return None
    rows: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        ts_ms = EquityCurveBuilder._timestamp_ms(item.get("beginTs"))
        ratio = _float(item.get("pnlRatio"))
        if ts_ms is None or ratio is None:
            continue
        rows.append({"ts_ms": ts_ms, "pnl_ratio_pct": ratio * 100.0})
    rows.sort(key=lambda r: r["ts_ms"])
    return rows or None


def _weekly_series(curve: EquityCurve) -> List[Dict[str, Any]]:
    """`curve.points` (already built once by `EquityCurveBuilder.build` in
    `assess_limited_bot`, never recomputed here) reshaped into the plain
    `[{begin_ts, equity, pnl, pnl_ratio}]` contract the report layer's chart
    builder reads. `equity` is `None` for a week the builder marked
    unusable (imprecise ratio, zero PnL, ...) -- left `None`, never
    substituted with 0 or the previous week's value, so the report layer
    can tell "no equity reading this week" apart from "equity was zero".
    Already sorted ascending: `EquityCurveBuilder.build` sorts `points` by
    `week_start_ms` before returning.
    """
    return [
        {
            "begin_ts": point.week_start_ms,
            "equity": point.start_equity,
            "pnl": point.pnl,
            "pnl_ratio": point.pnl_ratio,
        }
        for point in curve.points
    ]


def _drawdown_summary(curve: EquityCurve) -> Optional[Dict[str, Any]]:
    """The three numbers `_drawdown_component`'s own findings string already
    prints in prose ("Sụt vốn tối đa suy từ đường vốn tuần: 95.4% (trên
    10/12 tuần có dữ liệu dùng được)") -- pulled out here as plain fields so
    a report page can use them in a stat tile/table without re-parsing that
    sentence. Read straight off `curve` (the SAME curve `_drawdown_component`
    scored from), never recomputed, so this can never drift from the score
    that was actually used.

    `None` whenever `curve.max_drawdown_pct` is unavailable (basis is not
    WEEKLY_EQUITY_CURVE, e.g. no week had a precise enough ratio) -- this is
    the "not measured" case `_drawdown_component` itself scores as
    UNKNOWN_GAP, so there is no honest percentage to report here either.
    """
    if curve.max_drawdown_pct is None:
        return None
    return {
        "max_dd_pct": curve.max_drawdown_pct,
        "usable_weeks": curve.usable_points,
        "total_weeks": curve.coverage_weeks,
        "wiped_out": curve.wiped_out,
    }


def _opacity_component(dimension: str, label_vi: str) -> _Component:
    return _Component(
        dimension,
        label_vi,
        _OPACITY_RISK_SCORE,
        _OPACITY_WEIGHT,
        "UNKNOWN_CONCEALED",
        0.0,
        [
            "Requires individual trade data (the ledger) to compute, and OKX does "
            "not publish this bot's ledger"
        ],
    )


_ALWAYS_UNAVAILABLE_LABELS_VI = {
    "profit_factor": "Profit factor",
    "deferred_loss": "Deferred loss",
    "phase_analysis": "Market phase analysis",
    PSR_DSR_KEY: "PSR / DSR",
}


# Hệ số chiết khấu cho MỖI nguồn tính từ nguồn thứ hai trở đi khi gộp bằng
# quy tắc bằng chứng độc lập bên dưới. Bốn luồng public của một bot đều mô
# tả CÙNG MỘT tài khoản, chỉ khác endpoint và khác nhịp lấy mẫu, nên chúng
# KHÔNG độc lập hoàn toàn -- gộp thẳng như hai nhân chứng không quen biết
# nhau sẽ thổi phồng độ tin cậy. 0,8 là mức chiết khấu thận trọng: nguồn
# thứ hai chỉ được tính 80% giá trị, nguồn thứ ba 64%, và cứ thế.
_SOURCE_DEPENDENCE_DISCOUNT = 0.8


def _combine_measured_confidence(components: List["_Component"]) -> float:
    """Gộp độ tin cậy của các chiều ĐO ĐƯỢC theo quy tắc bằng chứng độc lập.

    VÌ SAO KHÔNG DÙNG TRUNG BÌNH CÓ TRỌNG SỐ: trung bình khiến việc thêm một
    nguồn mới LÀM GIẢM độ tin cậy nếu nguồn đó yếu hơn mức trung bình hiện
    có -- đo thật khi thêm chiều `return_path`: 12,8% tụt xuống 8,6%. Điều
    đó trái ngược với cách bằng chứng vận hành: biết THÊM một điều không
    bao giờ khiến ta biết ÍT đi.

    Quy tắc dùng ở đây là dạng "noisy-OR" quen thuộc trong hợp nhất bằng
    chứng: xác suất KHÔNG nguồn nào nói được gì là tích của các
    `(1 - c_i)`, nên độ tin cậy gộp là `1 - Π(1 - c_i)`. Hệ quả đúng với
    trực giác và đúng với yêu cầu của sản phẩm: mỗi nguồn thêm vào chỉ có
    thể đẩy kết quả LÊN, nhưng mỗi nguồn riêng lẻ càng mỏng thì đóng góp
    càng nhỏ.

    Các nguồn được sắp giảm dần rồi chiết khấu luỹ tiến
    (`_SOURCE_DEPENDENCE_DISCOUNT`) vì chúng cùng mô tả một tài khoản -- xem
    hằng số đó. Chiều không đo được (confidence = 0) không đóng góp gì và
    cũng không bị trừ gì ở đây; hình phạt cho việc che giấu nằm ở chỗ khác
    (hệ số phủ sóng bên dưới và điểm rủi ro của các chiều bị che).
    """
    values = sorted(
        (
            c.confidence
            for c in components
            if c.status == "AVAILABLE" and c.confidence > 0
        ),
        reverse=True,
    )
    if not values:
        return 0.0
    remaining = 1.0
    for index, value in enumerate(values):
        discounted = value * (_SOURCE_DEPENDENCE_DISCOUNT**index)
        remaining *= 1.0 - max(0.0, min(1.0, discounted))
    return 1.0 - remaining


def _independent_stream_count(
    profile: Optional[Dict[str, Any]],
    stats: Optional[Dict[str, Any]],
    curve: EquityCurve,
    return_path: _Component,
) -> int:
    """Đếm các LUỒNG DỮ LIỆU CÔNG KHAI thật sự có nội dung cho bot này.

    Bốn luồng, mỗi luồng là một endpoint OKX riêng và sống sót độc lập qua
    lỗi 60004: đường vốn tuần (public-weekly-pnl), chuỗi lợi nhuận tích luỹ
    (pnlRatios trong public-lead-traders), thống kê ngày lãi/lỗ
    (public-stats), và hồ sơ xếp hạng (public-lead-traders).

    Chỉ đếm luồng CÓ DỮ LIỆU DÙNG ĐƯỢC, không đếm luồng gọi được nhưng rỗng
    -- nếu không thì trần độ tin cậy sẽ nới ra nhờ những nguồn không đóng
    góp gì, đúng kiểu tự thưởng điểm mà module này phải tránh.
    """
    streams = 0
    if curve.is_usable:
        streams += 1
    if return_path.status == "AVAILABLE":
        streams += 1
    if (
        stats
        and any(_float(stats.get(key)) is not None for key in ("winRatio", "investAmt"))
        or _int((stats or {}).get("profitDays")) is not None
    ):
        streams += 1
    if profile and any(
        _float(profile.get(key)) is not None for key in ("aum", "pnl", "pnlRatio")
    ):
        streams += 1
    return streams


def _verdict_for_risk(risk: float) -> str:
    if risk >= 80:
        return "HIGH RISK (LIMITED ASSESSMENT)"
    if risk >= 60:
        return "NOTABLE RISK (LIMITED ASSESSMENT)"
    if risk >= 40:
        return "NEEDS CAUTION (LIMITED ASSESSMENT)"
    return "NOT ENOUGH EVIDENCE TO BE CONFIDENT (LIMITED ASSESSMENT)"


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
    data_dir: Optional[Path] = None,
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
    docstring and Agent/none/test/test_limited_assessment.py): status/code/name/
    limited_reason/unavailable/verdict/risk/quality/confidence/evidence/mc/
    text. Never raises for the inputs above being None/empty -- absence is
    exactly the case this function exists to describe, not fail on.
    """
    display_name = name or (profile or {}).get("nickName") or code

    if status == STATUS_NOT_FOUND:
        text = [
            f"Could not assess code {code}: this is a limited assessment, but "
            "even the fallback endpoints have no data.",
            reason,
            "This code was not found in the lead-trader ranking, weekly-pnl, "
            "or OKX public-stats -- most likely this is a wrong or nonexistent "
            "uniqueCode, not a bot hiding its ledger.",
        ]
        unavailable = list(ALWAYS_UNAVAILABLE) + [MONTE_CARLO_KEY, PSR_DSR_KEY]
        return {
            "status": STATUS_NOT_FOUND,
            "code": code,
            "name": display_name,
            "limited_reason": reason,
            "unavailable": unavailable,
            "verdict": "NOT FOUND",
            "risk": None,
            "quality": None,
            "confidence": NOT_FOUND_CONFIDENCE,
            "evidence": {"profile": None, "stats": None, "weekly_points": 0},
            "mc": None,
            "text": text,
        }

    if status != STATUS_LIMITED:
        raise ValueError(
            f"assess_limited_bot only accepts LIMITED/NOT_FOUND, got '{status}'"
        )

    curve = EquityCurveBuilder.build(weekly or [])
    # Mô phỏng chạy TRƯỚC: chiều sụt vốn nay chấm bằng hạng phân vị của
    # chính tham số mô phỏng (`p95_max_drawdown`) trong quần thể đã chấm,
    # nên nó cần kết quả này chứ không thể dựng độc lập như trước.
    mc_component, mc_payload, mc_text, mc_result = _monte_carlo_component_and_payload(
        weekly,
        curve,
        monte_carlo_iterations,
        monte_carlo_seed,
        profile=profile,
        stats=stats,
        data_dir=data_dir,
    )
    drawdown = _drawdown_component(curve, mc_result, data_dir)
    stability = _stability_component(stats)

    opacity_components = [
        _opacity_component(name_, label_)
        for name_, label_ in _ALWAYS_UNAVAILABLE_LABELS_VI.items()
    ]

    return_path = _return_path_component(profile)
    components = [drawdown, stability, return_path, mc_component] + opacity_components
    total_weight = sum(c.weight for c in components)
    risk = sum(c.score * c.weight for c in components) / total_weight
    risk = max(0.0, min(100.0, risk))

    # Hai đại lượng KHÁC NHAU, trước đây bị gộp làm một:
    #   * `measured_confidence` -- tin được bao nhiêu vào NHỮNG GÌ ĐÃ ĐO,
    #     gộp theo quy tắc bằng chứng độc lập (xem
    #     `_combine_measured_confidence`): kết hợp được nhiều nguồn thì cao
    #     hơn, mỗi nguồn mỏng thì đóng góp ít hơn.
    #   * `coverage` -- đo được bao nhiêu phần của bức tranh rủi ro, tính
    #     bằng tỉ trọng các chiều đo được trên tổng trọng số. Đây mới là
    #     chỗ việc che giấu bị phạt, và nó vẫn nguyên vẹn như trước.
    # Nhân hai thứ lại: biết rõ một mẩu nhỏ vẫn chỉ là biết một mẩu nhỏ.
    measured_confidence = _combine_measured_confidence(components)
    coverage = (
        sum(c.weight for c in components if c.status == "AVAILABLE") / total_weight
    )
    dimension_confidence = measured_confidence * coverage
    # Trần theo SỐ LUỒNG DỮ LIỆU thật sự có nội dung, không phải một con số
    # phẳng cho mọi bot (xem `_CONFIDENCE_CEILING_*`): còn một luồng thì
    # trần thấp, kết hợp được bốn luồng thì được phép tin hơn -- nhưng vẫn
    # luôn dưới mức tin cậy thấp nhất của một bot công khai đầy đủ.
    streams = _independent_stream_count(profile, stats, curve, return_path)
    ceiling = min(
        _CONFIDENCE_CEILING_ABSOLUTE,
        _CONFIDENCE_CEILING_BASE + _CONFIDENCE_CEILING_PER_STREAM * streams,
    )
    confidence = min(ceiling, dimension_confidence * 100.0)

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
        f"This is a LIMITED ASSESSMENT for code {code} ({display_name}): {reason}",
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
        "Could not be computed (requires individual trade data OKX does not publish): "
        + ", ".join(_ALWAYS_UNAVAILABLE_LABELS_VI[d] for d in ALWAYS_UNAVAILABLE)
        + ", PSR/DSR"
        + (", Monte Carlo simulation" if mc_component.status != "AVAILABLE" else "")
    )
    text.append(
        f"CONCLUSION: {verdict} — risk score {risk:.0f}/100, confidence "
        f"{confidence:.0f}/100 (well below a full assessment with a visible ledger, "
        "because every trade-level piece of evidence is missing)"
    )

    evidence = {
        "profile": profile,
        "stats": stats,
        "weekly_points": len(weekly or []),
        "equity_curve_basis": curve.basis,
        "components": [c.to_dict() for c in components],
        # Added on top of the original contract above (see module's own
        # task history) -- three keys the report layer needs to draw real
        # charts/tables instead of the bare point COUNT `weekly_points`
        # already gave it. Every one of these is read straight off data
        # this function already computed above (`curve`, `profile`), never
        # a new computation and never touching risk/quality/confidence.
        "weekly_series": _weekly_series(curve),
        "drawdown_summary": _drawdown_summary(curve),
        "pnl_ratio_series": _pnl_ratio_series(profile),
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
        return "Profile (lead-trader ranking): none (the bot has dropped off the ranking or is out of its scope)"
    aum = _float(profile.get("aum"))
    pnl = _float(profile.get("pnl"))
    lead_days = _int(profile.get("leadDays"))
    rank = profile.get("rank")
    parts = []
    if aum is not None:
        parts.append(f"AUM {aum:,.0f} USDT")
    if pnl is not None:
        parts.append(f"total PnL {pnl:,.0f} USDT")
    if lead_days is not None:
        parts.append(f"{lead_days} days as a lead trader")
    if rank is not None:
        parts.append(f"rank #{rank} on the lead-trader ranking")
    return "Profile: " + (
        ", ".join(parts) if parts else "present in the ranking but missing detail"
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
    Agent.backend.external.sources.bot_source.LedgerUnavailableError and hand it here
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
