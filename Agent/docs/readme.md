# AGENT DOCUMENTATION: AI RISK SUPERVISOR

## Tổng Quan Hệ Thống

Hệ thống hoạt động như một **AI Risk Supervisor** độc lập đứng trên các trading bot (chuyên biệt cho OKX và Top DEX), tuân thủ nghiêm ngặt **3 Logic Độc Lập**:

1. **LOGIC 1 — MARKET OBSERVATION:**
   - Quan sát thực tế thị trường khách quan (Price, Structure, Orderflow, Derivatives, Liquidity).
   - Xuất hợp đồng: `MarketResult`.

2. **LOGIC 2 — BOT / MCP OBSERVATION & SIMULATION:**
   - Giám sát bot OKX, quản lý sổ cái `Full Trade Ledger` theo các chế độ đo lường R (`FULL`, `PARTIAL`, `LIMITED`).
   - **Chứa lõi mô phỏng xác suất Monte Carlo & Bootstrap (10.000 runs):** Tính toán các xác suất rủi ro đuôi (`P(MDD > 10%)`, `P95 Max DD`, chuỗi lệnh thua liên tiếp).
   - Xuất hợp đồng: `BotResult`.

3. **LOGIC 3 — QC CORE (AI RISK SUPERVISOR):**
   - Tiếp nhận `MarketResult` + `BotResult` và kiểm định chéo qua **10 Chiều Rủi Ro Độc Lập** (Market Alignment, Performance, Return/R, Drawdown, Tail Risk, Leverage, Behavioral/Martingale, Strategy Drift, Liquidity, Portfolio).
   - Xuất hợp đồng: `BotRiskAssessment` (Risk Score 0-100, Confidence, Risk Tier, Trend).

4. **CONTROL LAYER (TÁCH BIỆT):**
   - Chuyển đổi phán quyết rủi ro thành lệnh can thiệp sàn cụ thể (`MONITOR`, `WARN`, `REDUCE`, `PAUSE`, `EMERGENCY_STOP`) qua API OKX với cơ chế Hysteresis Cooldown.

---

## Danh Mục Tài Liệu Cốt Lõi

1. [IDEA-01 — AI Risk Supervisor: 3 Logic Độc Lập](bmad/idea/IDEA-01_REGIME_CONDITIONED_AGENT_EVALUATION.md) *(APPROVED BASELINE)*
2. [PRD-01 — Engine 1 Scope & Architecture](bmad/prd/PRD-01_ENGINE1_SCOPE_AND_SUCCESS.md)
3. [PRD-02 — OKX CEX Data Foundation](bmad/prd/PRD-02_OKX_CEX_DATA_FOUNDATION.md)
4. [PRD-03 — OKX DEX / Onchain Data Foundation](bmad/prd/PRD-03_OKX_DEX_ONCHAIN_DATA_FOUNDATION.md)
5. [PRD-04 — Data Quality, Provenance & State](bmad/prd/PRD-04_DATA_QUALITY_PROVENANCE_AND_STATE.md)
6. [PRD-05 — Regime Core](bmad/prd/PRD-05_ENGINE1_REGIME_CORE.md)
7. [PRD-06 — Market Intelligence](bmad/prd/PRD-06_ENGINE1_MARKET_INTELLIGENCE.md)
8. [PRD-07 — Risk Scoring & Multi-Lens Ranking](bmad/prd/PRD-07_ENGINE1_RISK_SCORING_AND_RANKING.md)
9. [PRD-08 — Reporting & Assessment Formats](bmad/prd/PRD-08_ENGINE1_REPORTING.md)
10. [PRD-09 — OKX Interaction & Control Interface](bmad/prd/PRD-09_OKX_INTERACTION_AND_AGENT_INTERFACE.md)
11. [PRD-10 — Verification & Definition of Done](bmad/prd/PRD-10_ENGINE1_VERIFICATION_AND_DEFINITION_OF_DONE.md)

Mỗi PRD có danh sách child stories tương ứng trong [bmad/story/](bmad/story/). Active documentation chỉ gồm `readme.md` và `bmad/{idea,prd,story}`; không có archive hoặc tài liệu legacy song song.

## Status vocabulary

| Status | Nghĩa |
|---|---|
| `DRAFT` | Đang đặc tả/chờ review |
| `CURRENT-VERIFIED` | Có code và repeatable evidence |
| `CURRENT-UNVERIFIED` | Có code nhưng evidence chưa đủ |
| `PARTIAL` | Chỉ một phần capability tồn tại |
| `TARGET` | Behavior cần đạt, chưa phải current claim |
| `BLOCKED` | Thiếu dependency/evidence quyết định |
| `IDEA` | Giả thuyết chưa commit |

## Current readiness (2026-09-12)

- Universe policy là Top 30 CEX + Top 20 DEX. Freshness chấm theo anchor của dataset crawl (SNAPSHOT mode); hiện 3/15 candidate đạt eligibility, phần còn lại thiếu order book/spread.
- DEX Top 20: `BLOCKED/UNPROVEN`; local fixtures thiếu pool-liquidity/token-security evidence nên không asset nào được promote eligible.
- OKX interaction: vertical slice hiện chỉ đọc local snapshot/replay; chưa có live public/private adapter trong package này. Execution/asset movement bị deny fail-closed.
- Engine completion: `NOT DONE`; 78 deterministic tests pass cho vertical slice local/read-only, nhưng live ingestion/reconciliation, persistence, resilience/endurance và toàn bộ PRD-10 chưa đóng.

## Backend implementation order after docs approval

1. Freeze canonical contracts and remove favorable defaults.
2. Create canonical OKX public/private-read adapters; only adapters know OKX endpoints.
3. Select one authoritative repository/state implementation.
4. Make Engine 1 pure and explicit-input; keep rolling state outside calculation.
5. Route warm-up and closed WebSocket candles through one application use case into full `evaluate_market_risk`.
6. Implement deterministic CEX Top 50 first; keep DEX discovery/ranking blocked until verified.
7. Convert MCP to structured read-only queries; no order/transfer/withdraw/sign/broadcast tools.
8. Add contract, adapter, repository, pure Engine 1, replay, integration and negative capability tests.
9. Close PRD-10 gates before declaring `ENGINE1_DONE`.

## Source references

- Current backend paths are documented in each STORY and verified against code before status promotion.
- Official OKX v5 reference: <https://www.okx.com/docs-v5/en/>
