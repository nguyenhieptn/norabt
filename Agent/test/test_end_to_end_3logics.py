from __future__ import annotations

# ruff: noqa: E402

import sys
from pathlib import Path

# Thêm root workspace vào sys.path
WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from Agent.backend.control.execution.okx_executor import OKXControlExecutor
from Agent.backend.control.policy.decision_engine import ControlDecisionEngine
from Agent.backend.control.schemas.control_decision import ExecutionMode
from Agent.backend.market.service import MarketService
from Agent.backend.mcp.service import BotObservationService
from Agent.backend.qc.service import QCCoreService


def run_demonstration():
    print("=" * 95)
    print("DEMO KIỂM THỬ TOÀN DIỆN HỆ THỐNG AI RISK SUPERVISOR THEO 3 LOGIC ĐỘC LẬP")
    print("=" * 95)

    # 1. LOGIC 1: MARKET OBSERVATION
    print("\n[LOGIC 1] ĐANG QUAN SÁT THỊ TRƯỜNG THỰC TẾ (MARKET OBSERVATION)...")
    market_svc = MarketService()
    market_btc = market_svc.get_market_result("BTC")
    print(f"  ✓ Thị giá: ${market_btc.price_state.last_price:,.1f}")
    print(
        f"  ✓ Cấu trúc: EMA20 = ${market_btc.structure_state.ema_20:,.1f} | Xu hướng = {market_btc.structure_state.trend_state.value}"
    )
    print(
        f"  ✓ Độ sâu L2 ±0.2%: ${market_btc.liquidity_state.total_depth_02_usd:,.0f} ({market_btc.liquidity_state.state_tier.value})"
    )
    print(
        f"  ✓ Áp lực dòng tiền: {market_btc.orderflow_state.flow_bias} (Taker Ratio = {market_btc.orderflow_state.taker_ratio:.2f})"
    )
    print("  → XUẤT HỢP ĐỒNG: MarketResult")

    # 2. LOGIC 2: BOT OBSERVATION & MONTE CARLO PROBABILITY ENGINE
    print(
        "\n[LOGIC 2] ĐANG QUAN SÁT BOT & CHẠY MÔ PHỎNG PHÂN PHỐI (BOT / MCP ANALYTICS)..."
    )
    bot_svc = BotObservationService()

    print("  ► Phân tích Bot Top 1 (Modern-dAPI-Manatee)...")
    bot_top1 = bot_svc.get_bot_result("BTC", "bot_top_performer")
    sim1 = bot_top1.simulation_results
    print(
        f"    - Số lệnh: {bot_top1.performance.trade_count} | Win Rate: {bot_top1.performance.win_rate:.1f}% | PnL: ${bot_top1.performance.total_pnl:,.2f}"
    )
    print(f"    - Chế độ đo lường: {bot_top1.data_quality.measurement_mode.value}")
    print(
        f"    - Monte Carlo (10,000 runs): P(MDD > 10%) = {sim1.p_mdd_gt_10:.1f}% | P95 Max DD = {sim1.p95_max_drawdown:.1f}% | P(Streak 5 Loss) = {sim1.p_5_loss_streak:.1f}%"
    )

    print("  ► Phân tích Bot Top 20 (Performer cùi)...")
    bot_poor = bot_svc.get_bot_result("BTC", "bot_poor_performer")
    sim2 = bot_poor.simulation_results
    print(
        f"    - Vị thế mở gồng lỗ: {bot_poor.current_state.open_positions_count} vị thế"
    )
    print(
        f"    - Hành vi phát hiện: Martingale={bot_poor.behavioral_observations.martingale_escalation_detected}, AvgDown={bot_poor.behavioral_observations.averaging_down_detected}"
    )
    print(
        f"    - Monte Carlo (10,000 runs): P(MDD > 10%) = {sim2.p_mdd_gt_10:.1f}% | P95 Max DD = {sim2.p95_max_drawdown:.1f}% | P(5+ Loss Streak) = {sim2.p_5_loss_streak:.1f}%"
    )
    print("  → XUẤT HỢP ĐỒNG: BotResult")

    # 3. LOGIC 3: QC CORE RISK SUPERVISION
    print("\n[LOGIC 3] QC CORE THỰC HIỆN KIỂM ĐỊNH CHÉO 10 CHIỀU RỦI RO...")
    qc_top1 = QCCoreService.assess_bot(market_btc, bot_top1)
    qc_poor = QCCoreService.assess_bot(market_btc, bot_poor)

    def print_assessment(name: str, a):
        print(
            f"\n  ══════════════════ PHÁN QUYẾT QC CORE CHO {name} ══════════════════"
        )
        print(
            f"  • Điểm rủi ro tổng hợp: {a.risk_score:.1f}/100 | Cấp bậc rủi ro: [{a.risk_tier.value}]"
        )
        print(
            f"  • Độ tin cậy dữ liệu:  {a.confidence:.0f}% | Xu hướng rủi ro: [{a.risk_trend.value}]"
        )
        print(
            f"  • Hành động khuyến nghị: [{a.recommended_action}] (Cắt giảm: {a.suggested_reduction_pct:.0f}%)"
        )
        print("  • Chi tiết 10 Chiều Rủi Ro:")
        d = a.dimensions
        print(
            f"    01. Market Alignment:      Score={d.market_alignment.score:4.1f} | Tier={d.market_alignment.tier.value}"
        )
        print(
            f"    02. Performance Quality:   Score={d.performance_quality.score:4.1f} | Tier={d.performance_quality.tier.value}"
        )
        print(
            f"    03. Return / R Quality:    Score={d.return_r_quality.score:4.1f} | Tier={d.return_r_quality.tier.value}"
        )
        print(
            f"    04. Drawdown Risk:         Score={d.drawdown_risk.score:4.1f} | Tier={d.drawdown_risk.tier.value}"
        )
        print(
            f"    05. Tail Risk (Simulation):Score={d.tail_risk.score:4.1f} | Tier={d.tail_risk.tier.value}"
        )
        print(
            f"    06. Leverage / Exposure:   Score={d.leverage_exposure.score:4.1f} | Tier={d.leverage_exposure.tier.value}"
        )
        print(
            f"    07. Behavioral Risk:       Score={d.behavioral_risk.score:4.1f} | Tier={d.behavioral_risk.tier.value}"
        )
        print(
            f"    08. Strategy Drift:        Score={d.strategy_drift.score:4.1f} | Tier={d.strategy_drift.tier.value}"
        )
        print(
            f"    09. Liquidity / Execution: Score={d.liquidity_execution.score:4.1f} | Tier={d.liquidity_execution.tier.value}"
        )
        print(
            f"    10. Portfolio / Systemic:  Score={d.portfolio_risk.score:4.1f} | Tier={d.portfolio_risk.tier.value}"
        )
        print(f'  • Lời giải thích tổng thể: "{a.explanation}"')

    print_assessment("BOT TOP 1 (PERFORMER TỐT)", qc_top1)
    print_assessment("BOT TOP 20 (PERFORMER CÙI)", qc_poor)

    # 4. CONTROL LAYER
    print("\n[CONTROL LAYER] CHUYỂN ĐỔI PHÁN QUYẾT RỦI RO SANG LỆNH CAN THIỆP SÀN...")
    controller = ControlDecisionEngine(mode=ExecutionMode.READ_ONLY)
    dec_top1 = controller.decide(qc_top1)
    dec_poor = controller.decide(qc_poor)

    exec_top1 = OKXControlExecutor.execute(dec_top1)
    exec_poor = OKXControlExecutor.execute(dec_poor)

    print(
        f"  ► Lệnh cho Bot Top 1: Action = [{exec_top1.action.value}] | Trạng thái = {exec_top1.execution_status}"
    )
    print(
        f"  ► Lệnh cho Bot Top 20: Action = [{exec_poor.action.value}] | Tỷ lệ cắt giảm = {exec_poor.reduction_pct:.0f}% | Lý do = {exec_poor.reason}"
    )
    print("\n" + "=" * 95)
    print("HOÀN TẤT THÀNH CÔNG KIỂM THỬ TOÀN DIỆN 3 LOGIC VÀ TẦNG CONTROL!")
    print("=" * 95)


if __name__ == "__main__":
    run_demonstration()
