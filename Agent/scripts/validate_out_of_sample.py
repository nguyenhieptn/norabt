"""Does the risk score computed from a bot's past trades predict its future?

Chạy tuần tự, không song song hoá: với khoảng vài chục bot đủ điều kiện và một
tiến trình Python duy nhất, việc này chạy trong vài phút trên một nhân CPU --
không có lý do gì để thêm worker và mạo hiểm vượt trần tài nguyên của máy
(xem Agent/docs/out_of_sample_validation.md, mục "Giới hạn tài nguyên"). Tiến
độ được in ra theo từng bot để có thể theo dõi khi chạy thật, không chạy ngầm
âm thầm.

For every bot with enough closed trades:
  1. Split its closed-trade ledger in TIME (never randomly) at
     --train-fraction (default 60%).
  2. Score the FIRST half through the real, unmodified RiskSupervisionPipeline
     (Agent.backend.research.shadow_scoring builds a symlinked shadow copy of
     Agent/data with only that bot's ledger truncated -- see that module's
     docstring for exactly what is and is not rewound).
  3. Measure what actually happened in the SECOND half, directly from its
     realized PnL (Agent.backend.research.outcomes) -- no simulation.
  4. Correlate the first half's risk_score against the second half's
     outcomes (Spearman rank correlation, a bootstrap confidence interval,
     and a shuffle-based null benchmark -- Agent.backend.research.statistics).

Reads only Agent/data (or --data-dir); makes no network calls; writes nothing
under Agent/data. Pass --out-json to also save the full per-bot table for
independent re-analysis.
"""

from __future__ import annotations

import argparse
import json
import statistics as pystats
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Agent.backend.market.service import MarketDataUnavailableError  # noqa: E402
from Agent.backend.mcp.service import BotDataUnavailableError  # noqa: E402
from Agent.backend.research.dataset import (  # noqa: E402
    discover_bot_dirs,
    load_bot_ledger,
)
from Agent.backend.research.outcomes import compute_outcome_metrics  # noqa: E402
from Agent.backend.research.shadow_scoring import score_in_sample  # noqa: E402
from Agent.backend.research.splitting import split_by_close_time  # noqa: E402
from Agent.backend.research.statistics import (  # noqa: E402
    bootstrap_correlation_ci,
    permutation_null_correlation,
    spearman_correlation,
)

DATA_DIR = REPO_ROOT / "Agent" / "data"

DIMENSION_NAMES = (
    "market_alignment",
    "performance_quality",
    "return_r_quality",
    "drawdown_risk",
    "tail_risk",
    "leverage_exposure",
    "behavioral_risk",
    "strategy_drift",
    "liquidity_execution",
    "portfolio_risk",
)

# (result key, Vietnamese label, "higher is worse" for interpretation notes)
OUTCOME_METRICS: Tuple[Tuple[str, str], ...] = (
    ("oos_total_pnl_pct", "PnL nửa sau, % vốn tham chiếu"),
    ("oos_max_drawdown_pct", "Sụt vốn lớn nhất nửa sau, %"),
    ("oos_win_rate_pct", "Tỉ lệ thắng nửa sau, %"),
    ("oos_collapsed_flag", "Có 'sập' ở nửa sau (1) hay không (0)"),
)


def log(message: str) -> None:
    print(message, flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--min-trades", type=int, default=80)
    parser.add_argument("--train-fraction", type=float, default=0.6)
    parser.add_argument("--collapse-drawdown-pct", type=float, default=30.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--bootstrap-resamples", type=int, default=2000)
    parser.add_argument("--permutations", type=int, default=2000)
    parser.add_argument("--simulation-iterations", type=int, default=2000)
    parser.add_argument("--simulation-horizon", type=int, default=200)
    parser.add_argument(
        "--score-group-edges",
        type=float,
        nargs="*",
        default=[30.0, 50.0, 70.0],
        help="Ranh giới nhóm điểm rủi ro (mặc định <30, 30-50, 50-70, >=70)",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Ghi toàn bộ bảng kết quả từng bot ra JSON để đối chiếu độc lập",
    )
    return parser.parse_args()


def score_group(score: float, edges: Sequence[float]) -> str:
    edges = sorted(edges)
    lower = None
    for edge in edges:
        if score < edge:
            return f"<{edge:g}" if lower is None else f"{lower:g}-{edge:g}"
        lower = edge
    return f">={lower:g}" if lower is not None else "tất cả"


def run() -> Dict[str, Any]:
    args = parse_args()
    t_start = time.time()

    bot_dirs = discover_bot_dirs(args.data_dir)
    log(f"Tìm thấy {len(bot_dirs)} thư mục bot có đủ overview.json + trade_list.json.")

    ledgers = []
    for venue_type, asset, bot_dir in bot_dirs:
        record = load_bot_ledger(venue_type, asset, bot_dir)
        if record is None:
            log(f"  [bỏ qua] {venue_type}/{asset}/{bot_dir.name}: JSON không đọc được")
            continue
        ledgers.append(record)

    eligible = [r for r in ledgers if len(r.trades) >= args.min_trades]
    log(
        f"{len(ledgers)} bot đọc được ledger; {len(eligible)} bot có "
        f">= {args.min_trades} lệnh đã chốt (ngưỡng lọc tối thiểu)."
    )

    results: List[Dict[str, Any]] = []
    skipped: List[Dict[str, str]] = []

    for i, record in enumerate(eligible, 1):
        label = f"{record.venue_type}/{record.asset}/{record.bot_folder}"
        log(f"[{i}/{len(eligible)}] {label}: {len(record.trades)} lệnh đã chốt")
        try:
            split = split_by_close_time(record.trades, args.train_fraction)
        except ValueError as exc:
            log(f"    BỎ QUA (không chia được theo thời gian): {exc}")
            skipped.append({"bot": label, "stage": "split", "reason": str(exc)})
            continue
        log(
            f"    train={len(split.train)} test={len(split.test)} "
            f"(tỉ lệ train thực tế {split.train_fraction_actual:.1%}, "
            f"cutoff_ms={split.cutoff_ms})"
        )

        t0 = time.time()
        try:
            result = score_in_sample(
                real_data_dir=args.data_dir,
                venue_type=record.venue_type,
                asset=record.asset,
                bot_folder=record.bot_folder,
                raw_ledger=record.raw_ledger,
                overview=record.overview,
                cutoff_ms=split.cutoff_ms,
                seed=args.seed,
                simulation_iterations=args.simulation_iterations,
                simulation_horizon=args.simulation_horizon,
            )
        except (BotDataUnavailableError, MarketDataUnavailableError, ValueError) as exc:
            log(f"    BỎ QUA (chấm điểm nửa đầu thất bại): {exc}")
            skipped.append({"bot": label, "stage": "score", "reason": str(exc)})
            continue
        elapsed = time.time() - t0

        assessment = result.risk_assessment
        reference_capital = result.bot_result.current_state.reference_capital
        outcome = compute_outcome_metrics(
            split.test,
            reference_capital=reference_capital,
            collapse_drawdown_pct=args.collapse_drawdown_pct,
        )

        pnl_pct_txt = (
            f"{outcome.total_pnl_pct:+.1f}%"
            if outcome.total_pnl_pct is not None
            else "N/A"
        )
        dd_pct_txt = (
            f"{outcome.max_drawdown_pct:.1f}%"
            if outcome.max_drawdown_pct is not None
            else "N/A"
        )
        collapsed_txt = (
            "?"
            if outcome.collapsed is None
            else ("CÓ" if outcome.collapsed else "không")
        )
        log(
            f"    risk_score={assessment.risk_score:.1f} "
            f"quality_score={assessment.quality_score} "
            f"verdict={assessment.verdict!r} confidence={assessment.confidence:.0f} "
            f"| nửa sau: PnL%={pnl_pct_txt} maxDD%={dd_pct_txt} "
            f"winrate={outcome.win_rate_pct:.1f}% sập={collapsed_txt} "
            f"({elapsed:.1f}s)"
        )

        results.append(
            {
                "bot_id": result.bot_result.identity.bot_id,
                "venue_type": record.venue_type,
                "asset": record.asset,
                "bot_folder": record.bot_folder,
                "n_total": len(record.trades),
                "n_train": len(split.train),
                "n_test": len(split.test),
                "train_fraction_actual": split.train_fraction_actual,
                "cutoff_ms": split.cutoff_ms,
                "risk_score": assessment.risk_score,
                "quality_score": assessment.quality_score,
                "quality_components": dict(assessment.quality_components),
                "verdict": assessment.verdict,
                "confidence": assessment.confidence,
                "risk_tier": assessment.risk_tier.value,
                "dimensions": {
                    name: getattr(assessment.dimensions, name).score
                    for name in DIMENSION_NAMES
                },
                "reference_capital": reference_capital,
                "oos_total_pnl": outcome.total_pnl,
                "oos_total_pnl_pct": outcome.total_pnl_pct,
                "oos_max_drawdown_abs": outcome.max_drawdown_abs,
                "oos_max_drawdown_pct": outcome.max_drawdown_pct,
                "oos_win_rate_pct": outcome.win_rate_pct,
                "oos_max_losing_streak": outcome.max_losing_streak,
                "oos_has_losing_streak_5": outcome.has_losing_streak_5,
                "oos_has_losing_streak_10": outcome.has_losing_streak_10,
                "oos_collapsed": outcome.collapsed,
                "oos_collapsed_flag": (
                    None
                    if outcome.collapsed is None
                    else (1.0 if outcome.collapsed else 0.0)
                ),
            }
        )

    log("")
    log(
        f"Chấm điểm xong: {len(results)}/{len(eligible)} bot thành công, "
        f"{len(skipped)} bot bị bỏ qua trong lúc chạy."
    )
    if skipped:
        for item in skipped:
            log(f"  - {item['bot']} ({item['stage']}): {item['reason']}")

    correlations: Dict[str, Any] = {}
    for key, label in OUTCOME_METRICS:
        pairs = [(r["risk_score"], r[key]) for r in results if r.get(key) is not None]
        n = len(pairs)
        if n < 8:
            log(
                f"\n[{label}] chỉ có {n} bot có số liệu -- quá ít để tính tương "
                f"quan có ý nghĩa, bỏ qua."
            )
            correlations[key] = {"label": label, "n": n, "skipped": True}
            continue
        xs = [p[0] for p in pairs]
        ys = [p[1] for p in pairs]
        rho = spearman_correlation(xs, ys)
        boot = bootstrap_correlation_ci(
            xs, ys, seed=args.seed, n_resamples=args.bootstrap_resamples
        )
        perm = permutation_null_correlation(
            xs, ys, seed=args.seed, n_permutations=args.permutations
        )
        conclusive = not (boot.ci_low <= 0.0 <= boot.ci_high)
        log(
            f"\n[{label}] n={n} rho={rho:.3f} "
            f"CI95%=[{boot.ci_low:.3f}, {boot.ci_high:.3f}] "
            f"(bootstrap {boot.n_valid_resamples}/{boot.n_resamples} mẫu hợp lệ) "
            f"p(hoán vị, 2 phía)={perm.p_value_two_sided:.3f}"
        )
        log(
            "    => "
            + (
                "khoảng tin cậy KHÔNG chứa 0: có tín hiệu, nhưng vẫn phải đọc "
                "cùng cỡ mẫu và các thiên lệch nêu trong báo cáo."
                if conclusive
                else "khoảng tin cậy CHỨA 0: CHƯA KẾT LUẬN ĐƯỢC có tương quan thật hay không."
            )
        )
        correlations[key] = {
            "label": label,
            "n": n,
            "spearman_rho": rho,
            "bootstrap_ci_low": boot.ci_low,
            "bootstrap_ci_high": boot.ci_high,
            "bootstrap_n_valid": boot.n_valid_resamples,
            "bootstrap_n_resamples": boot.n_resamples,
            "permutation_p_value_two_sided": perm.p_value_two_sided,
            "permutation_n": perm.n_permutations,
            "ci_excludes_zero": conclusive,
        }

    edges = sorted(args.score_group_edges)
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        groups.setdefault(score_group(r["risk_score"], edges), []).append(r)

    def _group_order(name: str) -> float:
        if name.startswith("<"):
            return float(name[1:])
        if name.startswith(">="):
            return float(name[2:]) + 1_000_000.0
        return float(name.split("-")[0])

    log("\nBảng theo nhóm điểm rủi ro (risk_score chấm trên nửa đầu):")
    log(
        f"  {'nhóm':<10}{'n':>4}  {'PnL% trung vị':>16}  "
        f"{'maxDD% trung vị':>18}  {'tỉ lệ sập':>10}"
    )
    group_table = []
    for name in sorted(groups, key=_group_order):
        members = groups[name]
        pnl_vals = [
            m["oos_total_pnl_pct"]
            for m in members
            if m["oos_total_pnl_pct"] is not None
        ]
        dd_vals = [
            m["oos_max_drawdown_pct"]
            for m in members
            if m["oos_max_drawdown_pct"] is not None
        ]
        collapse_known = [
            m["oos_collapsed"] for m in members if m["oos_collapsed"] is not None
        ]
        median_pnl = pystats.median(pnl_vals) if pnl_vals else None
        median_dd = pystats.median(dd_vals) if dd_vals else None
        collapse_rate = (
            100.0 * sum(1 for c in collapse_known if c) / len(collapse_known)
            if collapse_known
            else None
        )
        log(
            f"  {name:<10}{len(members):>4}  "
            f"{(f'{median_pnl:+.1f}%' if median_pnl is not None else 'N/A'):>16}  "
            f"{(f'{median_dd:.1f}%' if median_dd is not None else 'N/A'):>18}  "
            f"{(f'{collapse_rate:.0f}% (n={len(collapse_known)})' if collapse_rate is not None else 'N/A'):>10}"
        )
        group_table.append(
            {
                "group": name,
                "n": len(members),
                "median_oos_pnl_pct": median_pnl,
                "median_oos_max_drawdown_pct": median_dd,
                "collapse_rate_pct": collapse_rate,
                "n_with_collapse_known": len(collapse_known),
            }
        )

    total_elapsed = time.time() - t_start
    log(f"\nTổng thời gian chạy: {total_elapsed:.1f}s")
    log(f"Số bot cuối cùng đưa vào kiểm định tương quan: {len(results)}")

    summary = {
        "params": {
            "data_dir": str(args.data_dir),
            "min_trades": args.min_trades,
            "train_fraction": args.train_fraction,
            "collapse_drawdown_pct": args.collapse_drawdown_pct,
            "seed": args.seed,
            "bootstrap_resamples": args.bootstrap_resamples,
            "permutations": args.permutations,
            "simulation_iterations": args.simulation_iterations,
            "simulation_horizon": args.simulation_horizon,
            "score_group_edges": edges,
        },
        "n_bot_dirs_found": len(bot_dirs),
        "n_ledgers_readable": len(ledgers),
        "n_eligible_min_trades": len(eligible),
        "n_scored_ok": len(results),
        "n_skipped_during_run": len(skipped),
        "skipped": skipped,
        "correlations": correlations,
        "group_table": group_table,
        "bots": results,
        "elapsed_seconds": total_elapsed,
    }

    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log(f"Đã ghi bảng kết quả đầy đủ vào {args.out_json}")

    return summary


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
