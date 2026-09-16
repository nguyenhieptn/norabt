"""Walk-Forward Analysis (WFA) Orchestrator & Windowed Runner cho Studio Pipeline.

Thực hiện:
- Tự động chia cửa sổ trượt In-Sample (Train) và Out-of-Sample (Test)
- Chạy Backtest tuần tự từng Fold an toàn tài nguyên
- Đánh giá tiêu chí Acceptance Gate (10/12 Fold dương, MDD <= 15%, Tổng OOS Profit)
- Xuất danh sách lệnh OOS tổng hợp (aggregate_oos_trades) cho Monte Carlo
"""
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.alpha.validator import ASTValidator
from backend.backtest.engine import BacktestEngine
from backend.backtest.metrics import MetricsCalculator
from backend.core.params import StrategyParams
from backend.db.local_pkl import default_data_root, has_frame
from .jobs import complete_wfa_job, fail_wfa_job, update_wfa_progress
from .schemas import (
    StrategySnapshot,
    WfaFoldConfig,
    WfaFoldResult,
    WfaResultContract,
)


def _ts_to_date_str(ts_ms: Optional[int]) -> str:
    if not ts_ms:
        return "N/A"
    return datetime.fromtimestamp(ts_ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def generate_folds(
    start_ts: int,
    end_ts: int,
    train_window_months: int = 1,
    test_window_months: int = 1,
    step_months: int = 1,
    max_folds: int = 6,
) -> List[Dict[str, int]]:
    """Tự động tính toán các khoảng thời gian IS (Train) và OOS (Test) theo rolling window."""
    total_duration_ms = max(0, end_ts - start_ts)
    one_day_ms = 86_400_000
    target_folds = max(1, min(max_folds, 12))

    if total_duration_ms < (10 * one_day_ms):
        train_len_ms = max(one_day_ms, int(total_duration_ms * 0.6))
        test_len_ms = max(one_day_ms // 2, int(total_duration_ms * 0.3))
        step_len_ms = max(one_day_ms // 2, int(total_duration_ms * 0.2))
    else:
        # Dynamic allocation for 90-day (or arbitrary) datasets:
        # 40% of duration for In-Sample training, 15% for Out-of-Sample testing
        train_len_ms = int(total_duration_ms * 0.40)
        test_len_ms = int(total_duration_ms * 0.15)
        
        remaining_ms = total_duration_ms - train_len_ms - test_len_ms
        if target_folds > 1 and remaining_ms > 0:
            step_len_ms = max(one_day_ms, int(remaining_ms / (target_folds - 1)))
        else:
            step_len_ms = max(one_day_ms, int(total_duration_ms * 0.1))

    folds = []
    curr_train_start = start_ts
    for fold_i in range(target_folds):
        curr_train_end = curr_train_start + train_len_ms
        curr_test_start = curr_train_end
        curr_test_end = curr_test_start + test_len_ms

        if curr_test_end > end_ts:
            curr_test_end = end_ts
            if curr_test_start >= end_ts:
                break

        folds.append({
            "train_start_ts": int(curr_train_start),
            "train_end_ts": int(curr_train_end),
            "test_start_ts": int(curr_test_start),
            "test_end_ts": int(curr_test_end),
        })
        curr_train_start += step_len_ms
        if curr_train_start + train_len_ms >= end_ts:
            break

    if not folds:
        mid_ts = start_ts + int(total_duration_ms * 0.6)
        folds.append({
            "train_start_ts": start_ts,
            "train_end_ts": mid_ts,
            "test_start_ts": mid_ts,
            "test_end_ts": end_ts,
        })

    return folds


def _run_single_window(
    symbol: str,
    flows: List[Dict[str, Any]],
    start_ts: int,
    end_ts: int,
    initial_capital: float,
    leverage: float,
    stop_loss_rate: float,
    take_profit_rate: float,
    using_match_price: bool,
    max_open_trades: int,
    timeout: int,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Chạy backtest cho một cửa sổ thời gian đơn lẻ qua BacktestEngine chuẩn."""
    engine = BacktestEngine(
        account_id=0,
        campaign_id=0,
        symbol=symbol,
        start_ts=start_ts,
        end_ts=end_ts,
    )

    for index, flow in enumerate(flows):
        flow_ast = flow.get("ast", flow)
        flow_type = str(flow_ast.get("type", "LONG")).upper()
        flow_name = str(flow.get("name") or flow.get("id") or f"{flow_type}_{index + 1}")
        if flow_type not in flow_name.upper():
            flow_name = f"{flow_type}_{flow_name}"

        params = StrategyParams(
            name=flow_name,
            strategy="studio_ast",
            data_type="1m",
            using_match_price=bool(using_match_price),
            max_open_trades=int(max_open_trades),
            volume_rate=1.0,
            leverage=int(leverage),
            stop_loss_rate=float(stop_loss_rate),
            take_profit_rate=float(take_profit_rate),
            timeout=int(timeout),
            extra={"ast": flow_ast},
        )
        engine.add_strategy_flow(flow_name, params)

    engine.load_data()
    if engine.df_1m is None or engine.df_1m.empty:
        return {"return_pct": 0.0, "max_drawdown_pct": 0.0, "total_trades": 0, "win_rate": 0.0, "profit_factor": 0.0}, []

    engine.run()
    res = engine.get_results()
    positions = res.get("positions", [])

    base = MetricsCalculator.calculate(positions, initial_capital)
    total_trades = int(base.get("total_trades", 0) or 0)
    win_rate = float(base.get("winrate", 0.0) or 0.0)
    return_pct = float(base.get("total_pnl_pct", 0.0) or 0.0)
    mdd_pct = float(base.get("max_drawdown_pct", 0.0) or 0.0)
    profit_factor = float(base.get("profit_factor", 0.0) or 0.0)
    net_profit = round(initial_capital * return_pct / 100.0, 2)

    # Thu thập danh sách chi tiết các vị thế
    trade_items: List[Dict[str, Any]] = []
    for index, pos in enumerate(positions, start=1):
        pnl_pct = round(float(pos.profit_pct or 0.0), 4)
        pnl_usd = round(initial_capital * pnl_pct / 100.0, 2)
        pos_type = str(getattr(pos.pos_type, "name", pos.pos_type) or "LONG").upper()
        trade_items.append({
            "trade_id": str(pos.result_id or index),
            "pos_type": pos_type,
            "entry_time": pos.enter_time,
            "entry_date": _ts_to_date_str(pos.enter_time),
            "entry_price": float(pos.enter_price or 0.0),
            "close_time": pos.close_time or pos.enter_time,
            "close_date": _ts_to_date_str(pos.close_time),
            "close_price": float(pos.close_price or 0.0),
            "pnl_usd": pnl_usd,
            "pnl_pct": pnl_pct,
            "reason": str(pos.close_reason or pos.start_reason or ""),
        })

    summary = {
        "return_pct": return_pct,
        "max_drawdown_pct": mdd_pct,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "net_profit": net_profit,
    }
    return summary, trade_items


def execute_wfa_pipeline(
    job_id: str,
    snapshot: StrategySnapshot,
    cfg: WfaFoldConfig,
    source_handle: str,
):
    """Tiến trình thực thi WFA hoàn chỉnh chạy trên background thread."""
    try:
        import os
        from backend.db.local_pkl import resolve_symbol_dir
        raw_sym = str(snapshot.symbol or "SOL").upper().strip()
        data_root = default_data_root()
        sym_dir = resolve_symbol_dir(raw_sym, data_root=data_root)
        if sym_dir:
            symbol = os.path.basename(sym_dir).upper()
        else:
            if os.path.isdir(os.path.join(data_root, "SOL")):
                symbol = "SOL"
            else:
                avail = [d for d in os.listdir(data_root) if os.path.isdir(os.path.join(data_root, d)) and not d.startswith(".")]
                symbol = avail[0] if avail else "SOL"

        flows = snapshot.flows
        if not flows:
            fail_wfa_job(job_id, "Chiến lược không có flows AST.")
            return

        # Kiểm tra dữ liệu nến
        for frame in ["1m", "4h"]:
            if not has_frame(symbol, frame, data_root=data_root):
                fail_wfa_job(job_id, f"Thiếu nến {frame} cho {symbol} trong data_root.")
                return

        start_ts = snapshot.start_ts
        end_ts = snapshot.end_ts
        if start_ts <= 0 or end_ts <= 0 or end_ts <= start_ts:
            from backend.db.local_pkl import fetch_candles_df
            df_check = fetch_candles_df(symbol, "1m", data_root=default_data_root())
            if not df_check.empty:
                max_ts = int(df_check["open_time"].max())
                min_ts = int(df_check["open_time"].min())
                start_ts = max(min_ts, max_ts - (60 * 86_400_000))
                end_ts = max_ts

        # Tạo danh sách các Fold
        raw_folds = generate_folds(
            start_ts=start_ts,
            end_ts=end_ts,
            train_window_months=cfg.train_window_months,
            test_window_months=cfg.test_window_months,
            step_months=cfg.step_months,
            max_folds=cfg.fold_count,
        )

        if not raw_folds:
            fail_wfa_job(job_id, "Khoảng thời gian không đủ để tạo ít nhất 1 Fold WFA.")
            return

        total_folds = len(raw_folds)
        update_wfa_progress(job_id, 0, total_folds, f"Đã sinh {total_folds} folds. Bắt đầu kiểm định...")

        fold_results: List[WfaFoldResult] = []
        all_oos_trades: List[Dict[str, Any]] = []

        for idx, fold_range in enumerate(raw_folds, start=1):
            update_wfa_progress(job_id, idx - 1, total_folds, f"Đang chạy Fold {idx}/{total_folds}...")

            # 1. Chạy In-Sample (Train)
            is_summary, _ = _run_single_window(
                symbol=symbol,
                flows=flows,
                start_ts=fold_range["train_start_ts"],
                end_ts=fold_range["train_end_ts"],
                initial_capital=snapshot.initial_capital,
                leverage=snapshot.leverage,
                stop_loss_rate=snapshot.stop_loss_rate,
                take_profit_rate=snapshot.take_profit_rate,
                using_match_price=snapshot.using_match_price,
                max_open_trades=snapshot.max_open_trades,
                timeout=snapshot.timeout,
            )

            # 2. Chạy Out-of-Sample (Test)
            oos_summary, oos_trades = _run_single_window(
                symbol=symbol,
                flows=flows,
                start_ts=fold_range["test_start_ts"],
                end_ts=fold_range["test_end_ts"],
                initial_capital=snapshot.initial_capital,
                leverage=snapshot.leverage,
                stop_loss_rate=snapshot.stop_loss_rate,
                take_profit_rate=snapshot.take_profit_rate,
                using_match_price=snapshot.using_match_price,
                max_open_trades=snapshot.max_open_trades,
                timeout=snapshot.timeout,
            )

            # Kiểm tra Gate cho từng Fold
            gate_notes = []
            passed_gate = True
            if oos_summary["return_pct"] < cfg.min_oos_profit_pct:
                passed_gate = False
                gate_notes.append(f"OOS Profit {oos_summary['return_pct']}% < {cfg.min_oos_profit_pct}%")
            if oos_summary["max_drawdown_pct"] > cfg.max_oos_mdd_pct:
                passed_gate = False
                gate_notes.append(f"OOS MDD {oos_summary['max_drawdown_pct']}% > {cfg.max_oos_mdd_pct}%")

            fold_res = WfaFoldResult(
                fold_index=idx,
                train_start_ts=fold_range["train_start_ts"],
                train_end_ts=fold_range["train_end_ts"],
                train_start_date=_ts_to_date_str(fold_range["train_start_ts"]),
                train_end_date=_ts_to_date_str(fold_range["train_end_ts"]),
                test_start_ts=fold_range["test_start_ts"],
                test_end_ts=fold_range["test_end_ts"],
                test_start_date=_ts_to_date_str(fold_range["test_start_ts"]),
                test_end_date=_ts_to_date_str(fold_range["test_end_ts"]),
                is_return_pct=is_summary["return_pct"],
                is_max_drawdown_pct=is_summary["max_drawdown_pct"],
                is_trades_count=is_summary["total_trades"],
                is_win_rate=is_summary["win_rate"],
                oos_return_pct=oos_summary["return_pct"],
                oos_max_drawdown_pct=oos_summary["max_drawdown_pct"],
                oos_trades_count=oos_summary["total_trades"],
                oos_win_rate=oos_summary["win_rate"],
                oos_profit_factor=oos_summary["profit_factor"],
                passed_gate=passed_gate,
                gate_notes=gate_notes,
                oos_trades=oos_trades,
            )
            fold_results.append(fold_res)
            all_oos_trades.extend(oos_trades)

        # Tổng hợp OOS metrics
        total_oos_return = round(sum(f.oos_return_pct for f in fold_results), 2)
        avg_oos_return = round(total_oos_return / total_folds, 2)
        worst_fold_mdd = round(max((f.oos_max_drawdown_pct for f in fold_results), default=0.0), 2)
        avg_oos_mdd = round(sum(f.oos_max_drawdown_pct for f in fold_results) / total_folds, 2)
        positive_folds_count = sum(1 for f in fold_results if f.oos_return_pct > 0)
        total_oos_trades = len(all_oos_trades)
        winning_oos_trades = sum(1 for t in all_oos_trades if t.get("pnl_usd", 0) > 0)
        overall_oos_win_rate = round((winning_oos_trades / total_oos_trades * 100.0), 1) if total_oos_trades > 0 else 0.0

        # Sắp xếp lệnh OOS theo thời gian vào lệnh
        all_oos_trades.sort(key=lambda t: t.get("entry_time", 0))

        # Tạo đường vốn OOS tổng hợp (Cumulative OOS closed-trade equity)
        aggregate_oos_equity = []
        running_equity = snapshot.initial_capital
        peak_equity = running_equity
        for i, trade in enumerate(all_oos_trades):
            running_equity += trade.get("pnl_usd", 0.0)
            peak_equity = max(peak_equity, running_equity)
            dd = round(((peak_equity - running_equity) / peak_equity * 100.0), 2) if peak_equity > 0 else 0.0
            aggregate_oos_equity.append({
                "time": trade.get("close_time", trade.get("entry_time", 0)),
                "date": trade.get("close_date", ""),
                "equity": round(running_equity, 2),
                "drawdown": dd,
                "trade_index": i + 1,
            })

        # Đánh giá Acceptance Gate tổng thể theo sơ đồ
        gate_checks = {
            "positive_folds": {
                "label": f"Số Fold OOS có lãi ({positive_folds_count}/{total_folds})",
                "required": f">= {cfg.min_positive_folds} folds",
                "actual": positive_folds_count,
                "passed": positive_folds_count >= min(cfg.min_positive_folds, total_folds),
            },
            "worst_mdd": {
                "label": f"Max Drawdown tệ nhất từng Fold ({worst_fold_mdd}%)",
                "required": f"<= {cfg.max_oos_mdd_pct}%",
                "actual": worst_fold_mdd,
                "passed": worst_fold_mdd <= cfg.max_oos_mdd_pct,
            },
            "total_return": {
                "label": f"Tổng lợi nhuận OOS 12 Fold ({total_oos_return}%)",
                "required": f">= {cfg.min_total_oos_profit_pct}%",
                "actual": total_oos_return,
                "passed": total_oos_return >= cfg.min_total_oos_profit_pct,
            },
        }
        acceptance_gate_passed = all(check["passed"] for check in gate_checks.values())

        wfa_result = WfaResultContract(
            wfa_id=job_id,
            source_handle=source_handle,
            strategy_name=snapshot.name,
            symbol=symbol,
            total_folds=total_folds,
            folds=fold_results,
            positive_folds_count=positive_folds_count,
            total_oos_return_pct=total_oos_return,
            avg_oos_return_pct=avg_oos_return,
            worst_fold_mdd_pct=worst_fold_mdd,
            avg_oos_mdd_pct=avg_oos_mdd,
            total_oos_trades=total_oos_trades,
            overall_oos_win_rate=overall_oos_win_rate,
            acceptance_gate_passed=acceptance_gate_passed,
            gate_checks=gate_checks,
            aggregate_oos_trades=all_oos_trades,
            aggregate_oos_equity=aggregate_oos_equity,
            generated_at=int(time.time() * 1000),
        )

        complete_wfa_job(job_id, wfa_result.model_dump())

    except Exception as exc:
        import traceback
        traceback.print_exc()
        fail_wfa_job(job_id, f"Ngoại lệ khi thực thi WFA: {str(exc)}")
