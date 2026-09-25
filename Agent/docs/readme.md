# HỆ THỐNG TÀI LIỆU CHUẨN BMAD — NORABT AI RISK SUPERVISOR

> **BMAD Documentation Framework**  
> **System Name:** NoraBT (Quantitative Risk Supervisor & Copier Guard for OKX)  
> **Repository:** `norabt`  
> **Documentation Root:** `Agent/docs/`  
> **Framework Architecture:** BMAD (Business, Model, Architecture, Delivery)  
> **Status:** ACTIVE / PRODUCTION  
> **Version:** 2.4.0  
> **Last Updated:** 2026-09-21  

---

## 1. Kiến Trúc Bộ Tài Liệu (Documentation Hierarchy)

Bộ tài liệu kỹ thuật của dự án NoraBT tại `Agent/docs/` được tinh gọn và quy chuẩn hóa thành **3 thành phần chính thức**:

```
Agent/docs/
├── readme.md                 <-- [Bạn đang ở đây] Chỉ mục toàn diện & Kiến trúc tổng quan
├── OKX_AI_REPORT.md          <-- Báo cáo đặc tả kỹ thuật đạt chuẩn OKX AI Track (Agents & AI-Native Businesses)
├── SYSTEM_OVERVIEW.md        <-- Mô tả hệ thống: bài toán, kiến trúc, mô hình kinh doanh (cài đặt & sử dụng: README.md ở gốc repo)
└── bmad/
    ├── story/                <-- QUÁ TRÌNH & TIẾN ĐỘ PHÁT TRIỂN HỆ THỐNG (Chia theo 10 phân hệ)
    │   ├── 00_overview/                  <-- Báo cáo tiến độ tổng thể (STORY-00)
    │   ├── 02_cex_data_foundation/       <-- Thu thập nến, lệnh, funding, thanh lý CEX (STORY-02.1 → 02.10)
    │   ├── 03_dex_onchain_foundation/    <-- Dữ liệu DEX, liquidity pool, audit token (STORY-03.1 → 03.10)
    │   ├── 04_data_quality_and_state/    <-- Chuẩn hóa, lọc trùng, snapshot, độ tươi (STORY-04.1 → 04.9)
    │   ├── 05_regime_core/               <-- Động cơ chế độ Keltner, ATR, vi mô/vĩ mô (STORY-05.1 → 05.10)
    │   ├── 06_market_intelligence/       <-- CVD, Orderbook imbalance, Market breadth (STORY-06.1 → 06.11)
    │   ├── 07_risk_scoring_and_ranking/  <-- Lượng hóa rủi ro VaR/CVaR, ranking (STORY-07.1 → 07.13)
    │   ├── 08_financial_reporting/       <-- Hồ sơ JSON, render HTML, view đa chiều (STORY-08.1 → 08.12)
    │   ├── 09_agent_interface_and_mcp/   <-- Ranh giới an toàn, 6 MCP tools, x402 (STORY-09.1 → 09.10)
    │   └── 10_verification_and_gates/    <-- 15 Cổng kiểm định & Definition of Done (STORY-10.1 → 10.15)
    │
    └── spec/                 <-- BÓC TÁCH CHI TIẾT TỪNG CHỨC NĂNG HỆ THỐNG
        ├── 00_overview/                  <-- Chỉ mục đặc tả (SPEC-00) & Ý tưởng khởi nguyên (IDEA-01)
        ├── 01_prd_engine1/               <-- 10 Bản yêu cầu sản phẩm Engine 1 (PRD-01 → PRD-10)
        └── 02_technical_skills/          <-- 8 Bản đặc tả kỹ năng kỹ thuật chuyên sâu (SPEC-01 → SPEC-08)
```

---

## 2. Phần 1: BMAD Story — Quá Trình & Tiến Độ Phát Triển

Thư mục `bmad/story/` lưu trữ toàn bộ tiến trình lịch sử phát triển, các cột mốc đã hoàn thành, các rào cản kỹ thuật đã vượt qua và trạng thái vận hành hiện tại của hệ thống.

- 📘 **Tài liệu trung tâm:** [STORY-00: Quá Trình và Tiến Độ Phát Triển Toàn Diện Hệ Thống](bmad/story/00_overview/STORY-00_SYSTEM_PROGRESSION_AND_STATUS.md)
  - **Giai đoạn 1 (10-12/09):** Khởi tạo Engine 1 — Tái cấu trúc sổ lệnh, 10 lăng kính rủi ro và bộ tiêu chí Veto an toàn.
  - **Giai đoạn 2 (13-14/09):** Chuẩn hóa giao thức MCP Server (cổng 8765), cơ chế thanh toán vi mô x402 qua USDC trên X Layer và bộ đệm Redis Snapshot.
  - **Giai đoạn 3 (15/09):** Thẩm định ngoài mẫu (Out-of-sample) trên 36 bot OKX thực tế, kiểm chuẩn tương quan hạng Spearman, Deflated Sharpe Ratio và MinTRL.
  - **Giai đoạn 4 (16-17/09):** Xây dựng ứng dụng quản trị Single-Page App (React SPA), thẻ tóm tắt Quant, phân quyền Admin truy cập mở.
  - **Giai đoạn 5 (17-18/09):** Tích hợp Động cơ Nhận định Chuyên môn Định tính (Narrative Synthesizer), bỏ nhãn AI máy móc, popup chú giải công thức tài chính.
  - **Giai đoạn 6 (18/09):** Tái thiết kế giao diện **NORA // BRUTAL AI TRADING SYSTEM** — kết hợp 70% OKX AI Fintech với 30% Neo-Brutalism, cân chỉnh màu sắc hài hòa Deep Slate Obsidian (`#0B0E17`, `#101522`, `#1E283D`).
  - **Giai đoạn 7 (19/09):** Quốc tế hóa sang tiếng Anh toàn bộ văn bản đầu ra, chuyển LLM sang `agy/Gemini 3.8 Flash`, hợp nhất lõi và dọn kiến trúc.
  - **Giai đoạn 8 (21/09):** Chuẩn hóa & phân nhóm folder chi tiết cho `spec/` (overview, prd, skills) và `story/` (10 phân hệ chuyên đề), bảo đảm khớp nối 100% tài liệu và hiện vật thật.
- 📂 **Các story kiểm thử cổng (Acceptance Gates):** 100 story chi tiết được chia theo 10 thư mục chuyên đề tương ứng tại [bmad/story/](bmad/story/).

---

## 3. Phần 2: BMAD Spec — Bóc Tách Chi Tiết Từng Kỹ Năng Hệ Thống

Thư mục `bmad/spec/` mô tả chi tiết, bóc tách về mặt toán học, thuật toán, luồng dữ liệu và hợp đồng giao tiếp của từng năng lực (Skill) cốt lõi:

* **Chỉ mục trung tâm:** [SPEC-00: Master Specification Index](bmad/spec/00_overview/SPEC-00_SPECIFICATION_INDEX.md)

| Mã Spec | Tên Kỹ Năng (Skill Specification) | Phân Hệ Phụ Trách | Tài Liệu Chi Tiết |
| :---: | :--- | :--- | :---: |
| **SPEC-01** | **Kỹ năng Thu thập Dữ liệu & Sổ lệnh OKX**<br>Ghép lệnh chuẩn FIFO, phát hiện om vị thế, tính PnL và Drawdown chuỗi thời gian thực. | `sources/bot_source.py`<br>`market/service.py` | [Xem Spec 01](bmad/spec/02_technical_skills/SPEC-01_OKX_INGESTION_AND_LEDGER_SKILL.md) |
| **SPEC-02** | **Kỹ năng Nhận diện Chế độ Thị trường & Phân tích Nến**<br>Keltner Channels (EMA 20, ATR 14), 4 chế độ thị trường vi mô/vĩ mô, đồng thuận BTC Beta. | `market/service.py`<br>`lenses/market_alignment.py` | [Xem Spec 02](bmad/spec/02_technical_skills/SPEC-02_MARKET_REGIME_AND_STRUCTURE_SKILL.md) |
| **SPEC-03** | **Kỹ năng Đo lường Rủi ro Lượng hóa 10 Chiều**<br>Fat-tail VaR/CVaR, Đòn bẩy hiệu dụng, Trượt giá khớp lệnh, Bẫy Martingale/DCA, Strategy Drift. | `qc/evaluator/lenses/` | [Xem Spec 03](bmad/spec/02_technical_skills/SPEC-03_TEN_DIMENSIONAL_QUANTITATIVE_RISK_SKILL.md) |
| **SPEC-04** | **Kỹ năng Mô phỏng Monte Carlo & Bootstrap Thống kê**<br>10.000 kịch bản Stationary Bootstrap (Politis & Romano 1994), Deflated Sharpe (DSR), PSR, MinTRL. | `mcp/analytics/simulation/` | [Xem Spec 04](bmad/spec/02_technical_skills/SPEC-04_MONTE_CARLO_AND_STATIONARY_BOOTSTRAP_SKILL.md) |
| **SPEC-05** | **Kỹ năng Veto An toàn & Xếp loại Chất lượng**<br>Ma trận phân loại 4 góc phần tư (Drawdown vs Quality), 6 điều kiện Veto cứng, tính toán Risk Score 0–100. | `qc/scoring/verdict.py`<br>`qc/reporting/reasons.py` | [Xem Spec 05](bmad/spec/02_technical_skills/SPEC-05_SAFETY_VETO_AND_DECISION_ENGINE_SKILL.md) |
| **SPEC-06** | **Kỹ năng Tổng hợp Nhận định Chuyên môn Định tính**<br>Cấu trúc lập luận 3 tầng (Kết luận → Nguyên nhân cốt lõi → Luận cứ chứng minh `◆`), 5 cổng kiểm duyệt khắt khe. | `qc/reporting/narrative.py`<br>`web/report_page.py` | [Xem Spec 06](bmad/spec/02_technical_skills/SPEC-06_QUALITATIVE_NARRATIVE_SYNTHESIS_SKILL.md) |
| **SPEC-07** | **Kỹ năng Máy chủ MCP & Thanh toán Vi mô x402**<br>Chuẩn giao tiếp Model Context Protocol (JSON-RPC 2.0), 6 công cụ MCP, thanh toán USDC onchain x402. | `backend/scripts/agent_server.py`<br>`payments/x402.py` | [Xem Spec 07](bmad/spec/02_technical_skills/SPEC-07_MCP_SERVER_AND_MICRO_PAYMENTS_SKILL.md) |
| **SPEC-08** | **Kỹ năng Giao diện Quản trị & Báo cáo Bot Chuẩn Fintech**<br>Hệ thống Design Tokens (`tokens.css`), triết lý 70% OKX + 30% Neo-Brutalism, Deep Slate Obsidian, radar SYSTEM ONLINE. | `frontend/`<br>`web/tokens.css`<br>`web/report_page.py` | [Xem Spec 08](bmad/spec/02_technical_skills/SPEC-08_INSTITUTIONAL_UI_AND_VISUALIZATION_SKILL.md) |

---

## 4. Tiêu Chuẩn Truy Vết & Kiểm Thử Hệ Thống (Verification Matrix)

Mọi kỹ năng trong bộ Spec và mọi chặng trong bộ Story đều được bảo đảm bằng bộ kiểm thử tự động toàn diện:
- **Pytest Suite:** Đạt **99/99 bài test PASS** trong [test_report_page.py](file:///home/ubuntu/norabt/Agent/none/test/test_report_page.py) cùng toàn bộ các bài test đơn vị trong `Agent/none/test/`.
- **Docker Compose Services (Production Ready & Live):**
  - `norabt-agent-web` (Cổng 8770): Phục vụ REST API, React SPA bundle và trang báo cáo HTML máy chủ. Đã cấu hình Nginx reverse proxy tại domain chính thức: `https://agent.expsolution.io`.
  - `norabt-agent-redis` (Cổng 6379): Bộ đệm snapshot kết quả thẩm định dưới 50ms (in-memory allkeys-lru).
- **OKX OnchainOS Integration (Live Mainnet):** Đã đăng ký dịch vụ thành công với **Agentic ID: `13753`**, **Service SID: `40700`**, endpoint `https://agent.expsolution.io/api/analyze`.
- **Frontend SPA Build:** Vite bundle biên dịch tối ưu (199 KB JS gzip 65 KB, 18.7 KB CSS gzip 4.6 KB).
