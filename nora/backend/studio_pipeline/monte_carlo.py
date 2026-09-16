"""Monte Carlo Simulation Engine cho Studio Pipeline.

Thực hiện Bootstrap Resampling có hoàn lại trên danh sách lệnh OOS:
- Đo lường phân phối xác suất Max Drawdown (Percentile 50th, 90th, 95th, 99th)
- Tính toán Xác suất Cháy / Thua lỗ nghiêm trọng (Risk of Ruin %)
- Xuất dữ liệu biểu đồ phân tán đường vốn (Equity Fan Chart)
"""
import time
from typing import Any, Dict, List, Optional

import numpy as np

from .jobs import complete_mc_job, fail_mc_job
from .schemas import MonteCarloResultContract, MonteCarloRunRequest


def run_monte_carlo(
    trades: List[Dict[str, Any]],
    simulations: int = 1000,
    initial_capital: float = 10000.0,
    ruin_threshold_pct: float = 30.0,
    confidence_levels: Optional[List[float]] = None,
    block_size: int = 1,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """Thực hiện mô phỏng Monte Carlo vector tốc độ cao trên mảng PnL."""
    if confidence_levels is None:
        confidence_levels = [90.0, 95.0, 99.0]

    if seed is not None:
        np.random.seed(seed)

    trades_count = len(trades)
    if trades_count == 0:
        return {
            "simulations": simulations,
            "trades_count": 0,
            "initial_capital": initial_capital,
            "percentile_mdd": {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0, "worst": 0.0},
            "risk_of_ruin_pct": 0.0,
            "ruin_threshold_pct": ruin_threshold_pct,
            "terminal_return_pct": {"p10": 0.0, "p50": 0.0, "p90": 0.0, "worst": 0.0, "best": 0.0},
            "sample_paths": [],
            "summary": {
                "avg_mdd_pct": 0.0,
                "median_profit_usd": 0.0,
                "win_ratio_of_simulations": 0.0,
            },
        }

    pnl_usd_array = np.array([float(t.get("pnl_usd", 0.0)) for t in trades], dtype=np.float64)

    # ─── Bootstrap Resampling ──────────────────────────────────────────────────
    if block_size <= 1:
        # Trade Bootstrap độc lập có hoàn lại
        sampled_pnls = np.random.choice(pnl_usd_array, size=(simulations, trades_count), replace=True)
    else:
        # Block Bootstrap để bảo tồn chuỗi lệnh liên tiếp
        num_blocks = int(np.ceil(trades_count / block_size))
        max_start = max(1, trades_count - block_size + 1)
        block_starts = np.random.choice(max_start, size=(simulations, num_blocks), replace=True)
        sampled_blocks = []
        for sim_idx in range(simulations):
            sim_pnl = []
            for b_start in block_starts[sim_idx]:
                sim_pnl.extend(pnl_usd_array[b_start : b_start + block_size])
            sampled_blocks.append(sim_pnl[:trades_count])
        sampled_pnls = np.array(sampled_blocks, dtype=np.float64)

    # Tính đường cong số dư tài khoản (Equity Curves)
    cum_pnls = np.cumsum(sampled_pnls, axis=1)
    # Thêm điểm xuất phát (initial_capital) vào cột đầu tiên
    all_equities = np.hstack([np.full((simulations, 1), initial_capital, dtype=np.float64), initial_capital + cum_pnls])

    # ─── Max Drawdown Calculation ──────────────────────────────────────────────
    running_max = np.maximum.accumulate(all_equities, axis=1)
    drawdowns = (running_max - all_equities) / np.maximum(running_max, 1e-9) * 100.0
    sim_max_drawdowns = np.max(drawdowns, axis=1)

    # ─── Risk of Ruin ──────────────────────────────────────────────────────────
    ruined_sims = np.sum(sim_max_drawdowns >= ruin_threshold_pct)
    risk_of_ruin_pct = round(float(ruined_sims / simulations * 100.0), 2)

    # ─── Percentile Metrics ────────────────────────────────────────────────────
    percentile_mdd = {
        "p50": round(float(np.percentile(sim_max_drawdowns, 50)), 2),
        "p90": round(float(np.percentile(sim_max_drawdowns, 90)), 2),
        "p95": round(float(np.percentile(sim_max_drawdowns, 95)), 2),
        "p99": round(float(np.percentile(sim_max_drawdowns, 99)), 2),
        "worst": round(float(np.max(sim_max_drawdowns)), 2),
    }

    terminal_equities = all_equities[:, -1]
    terminal_returns = (terminal_equities - initial_capital) / initial_capital * 100.0
    terminal_return_pct = {
        "p10": round(float(np.percentile(terminal_returns, 10)), 2),
        "p50": round(float(np.percentile(terminal_returns, 50)), 2),
        "p90": round(float(np.percentile(terminal_returns, 90)), 2),
        "worst": round(float(np.min(terminal_returns)), 2),
        "best": round(float(np.max(terminal_returns)), 2),
    }

    profitable_sims = np.sum(terminal_returns > 0)
    win_ratio_of_simulations = round(float(profitable_sims / simulations * 100.0), 1)

    # ─── Downsample Sample Paths for UI Fan Chart ──────────────────────────────
    # Chọn 35 đường cong đại diện: Worst, Best, Median, và 32 đường ngẫu nhiên
    num_paths_to_export = min(35, simulations)
    worst_idx = int(np.argmin(terminal_equities))
    best_idx = int(np.argmax(terminal_equities))
    median_idx = int(np.argsort(terminal_equities)[simulations // 2])

    chosen_indices = {worst_idx, best_idx, median_idx}
    rand_indices = np.random.choice(simulations, size=num_paths_to_export, replace=False)
    for idx in rand_indices:
        chosen_indices.add(int(idx))
        if len(chosen_indices) >= num_paths_to_export:
            break

    # ─── Downsample Sample Paths and Compute Quantile Bands for UI Fan Chart ──
    total_steps = all_equities.shape[1]
    step_stride = max(1, total_steps // 60)
    sample_indices = list(range(0, total_steps, step_stride))
    if sample_indices[-1] != total_steps - 1:
        sample_indices.append(total_steps - 1)

    exported_paths = []
    for c_idx in chosen_indices:
        path = [round(float(all_equities[c_idx, s]), 2) for s in sample_indices]
        exported_paths.append(path)

    # Compute step-by-step quantile envelopes across sampled steps
    sampled_matrix = all_equities[:, sample_indices]
    quantile_curves = {
        "steps": len(sample_indices),
        "p5": [round(float(v), 2) for v in np.percentile(sampled_matrix, 5, axis=0)],
        "p25": [round(float(v), 2) for v in np.percentile(sampled_matrix, 25, axis=0)],
        "p50": [round(float(v), 2) for v in np.percentile(sampled_matrix, 50, axis=0)],
        "p75": [round(float(v), 2) for v in np.percentile(sampled_matrix, 75, axis=0)],
        "p95": [round(float(v), 2) for v in np.percentile(sampled_matrix, 95, axis=0)],
        "best": [round(float(v), 2) for v in np.max(sampled_matrix, axis=0)],
        "worst": [round(float(v), 2) for v in np.min(sampled_matrix, axis=0)],
    }

    return {
        "simulations": simulations,
        "trades_count": trades_count,
        "initial_capital": round(initial_capital, 2),
        "percentile_mdd": percentile_mdd,
        "risk_of_ruin_pct": risk_of_ruin_pct,
        "ruin_threshold_pct": ruin_threshold_pct,
        "terminal_return_pct": terminal_return_pct,
        "sample_paths": exported_paths,
        "quantile_curves": quantile_curves,
        "summary": {
            "avg_mdd_pct": round(float(np.mean(sim_max_drawdowns)), 2),
            "median_profit_usd": round(float(np.median(terminal_equities - initial_capital)), 2),
            "win_ratio_of_simulations": win_ratio_of_simulations,
            "min_terminal_equity": round(float(np.min(terminal_equities)), 2),
            "max_terminal_equity": round(float(np.max(terminal_equities)), 2),
        },
    }


def execute_monte_carlo_pipeline(
    job_id: str,
    req: MonteCarloRunRequest,
    trades: List[Dict[str, Any]],
):
    """Tiến trình thực thi Monte Carlo chạy trên background worker thread."""
    try:
        res = run_monte_carlo(
            trades=trades,
            simulations=req.simulations,
            initial_capital=req.initial_capital,
            ruin_threshold_pct=req.ruin_threshold_pct,
            confidence_levels=req.confidence_levels,
            block_size=req.block_size,
        )

        mc_contract = MonteCarloResultContract(
            mc_id=job_id,
            source_wfa_id=req.source_wfa_id,
            strategy_name=req.strategy_name or "Strategy",
            symbol=req.symbol or "SOL",
            simulations=req.simulations,
            trades_count=res["trades_count"],
            initial_capital=res["initial_capital"],
            percentile_mdd=res["percentile_mdd"],
            risk_of_ruin_pct=res["risk_of_ruin_pct"],
            ruin_threshold_pct=res["ruin_threshold_pct"],
            terminal_return_pct=res["terminal_return_pct"],
            sample_paths=res["sample_paths"],
            summary=res["summary"],
            generated_at=int(time.time() * 1000),
        )

        complete_mc_job(job_id, mc_contract.model_dump())

    except Exception as exc:
        import traceback
        traceback.print_exc()
        fail_mc_job(job_id, f"Ngoại lệ khi thực thi Monte Carlo: {str(exc)}")
