# HỆ THỐNG TÀI LIỆU CHUẨN BMAD — NORABT AI RISK SUPERVISOR

> **BMAD Documentation Framework**  
> **System Name:** NoraBT (Quantitative Risk Supervisor & Copier Guard for OKX)  
> **Repository:** `norabt`  
> **Documentation Root:** `Agent/docs/`  
> **Framework Architecture:** BMAD (Business, Model, Architecture, Delivery)  
> **Status:** ACTIVE / PRODUCTION  
> **Version:** 2.4.0  
> **Last Updated:** 2026-09-18  

---

## 1. Kiến Trúc Bộ Tài Liệu (Documentation Hierarchy)

Bộ tài liệu kỹ thuật của dự án NoraBT được tinh gọn và quy chuẩn hóa thành hai thành phần duy nhất theo đúng tiêu chuẩn phương pháp luận BMAD:

```
Agent/docs/
├── readme.md                 <-- [Bạn đang ở đây] Chỉ mục toàn diện & Kiến trúc tổng quan
└── bmad/
    ├── story/                <-- QUÁ TRÌNH & TIẾN ĐỘ PHÁT TRIỂN HỆ THỐNG
    │   ├── STORY-00_SYSTEM_PROGRESSION_AND_STATUS.md  <-- Báo cáo tiến độ tổng thể các giai đoạn
    │   └── STORY-*.md        <-- Các story kỹ thuật chi tiết theo từng gate nghiệm thu
    │
    └── spec/                 <-- BÓC TÁCH CHI TIẾT TỪNG KỸ NĂNG CỦA HỆ THỐNG
        ├── SPEC-01_OKX_INGESTION_AND_LEDGER_SKILL.md         <-- Kỹ năng Nạp & Sổ lệnh OKX
        ├── SPEC-02_MARKET_REGIME_AND_STRUCTURE_SKILL.md      <-- Kỹ năng Nhận diện Chế độ Thị trường
        ├── SPEC-03_TEN_DIMENSIONAL_QUANTITATIVE_RISK_SKILL.md <-- Kỹ năng Đo lường Rủi ro 10 Chiều
        ├── SPEC-04_MONTE_CARLO_AND_STATIONARY_BOOTSTRAP_SKILL.md <-- Kỹ năng Mô phỏng Monte Carlo
        ├── SPEC-05_SAFETY_VETO_AND_DECISION_ENGINE_SKILL.md   <-- Kỹ năng Veto An toàn & Xếp loại
        ├── SPEC-06_QUALITATIVE_NARRATIVE_SYNTHESIS_SKILL.md   <-- Kỹ năng Nhận định Chuyên môn
        ├── SPEC-07_MCP_SERVER_AND_MICRO_PAYMENTS_SKILL.md    <-- Kỹ năng MCP & Thanh toán x402
        └── SPEC-08_INSTITUTIONAL_UI_AND_VISUALIZATION_SKILL.md <-- Kỹ năng Giao diện Brutal AI
```

---

## 2. Phần 1: BMAD Story — Quá Trình & Tiến Độ Phát Triển

Thư mục `bmad/story/` lưu trữ toàn bộ tiến trình lịch sử phát triển, các cột mốc đã hoàn thành, các rào cản kỹ thuật đã vượt qua và trạng thái vận hành hiện tại của hệ thống.

- 📘 **Tài liệu trung tâm:** [STORY-00: Quá Trình và Tiến Độ Phát Triển Toàn Diện Hệ Thống](bmad/story/STORY-00_SYSTEM_PROGRESSION_AND_STATUS.md)
  - **Giai đoạn 1 (10-12/09):** Khởi tạo Engine 1 — Tái cấu trúc sổ lệnh, 10 lăng kính rủi ro và bộ tiêu chí Veto an toàn.
  - **Giai đoạn 2 (13-14/09):** Chuẩn hóa giao thức MCP Server (cổng 8000), cơ chế thanh toán vi mô x402 qua USDC trên X Layer và bộ đệm Redis Snapshot.
  - **Giai đoạn 3 (15/09):** Thẩm định ngoài mẫu (Out-of-sample) trên 36 bot OKX thực tế, kiểm chuẩn tương quan hạng Spearman, Deflated Sharpe Ratio và MinTRL.
  - **Giai đoạn 4 (16-17/09):** Xây dựng ứng dụng quản trị Single-Page App (React SPA), thẻ tóm tắt Quant, phân quyền Admin truy cập mở.
  - **Giai đoạn 5 (17-18/09):** Tích hợp Động cơ Nhận định Chuyên môn Định tính (Narrative Synthesizer), bỏ nhãn AI máy móc, popup chú giải công thức tài chính.
  - **Giai đoạn 6 (18/09 - Hiện tại):** Tái thiết kế giao diện **NORA // BRUTAL AI TRADING SYSTEM** — kết hợp 70% OKX AI Fintech với 30% Neo-Brutalism, cân chỉnh màu sắc hài hòa Deep Slate Obsidian (`#0B0E17`, `#101522`, `#1E283D`).
- 📂 **Các story kiểm thử cổng (Acceptance Gates):** Các tệp `STORY-02.*` đến `STORY-10.*` trong thư mục [bmad/story/](bmad/story/) ghi lại chi tiết các điều kiện nghiệm thu nghiêm ngặt của từng phân hệ.

---

## 3. Phần 2: BMAD Spec — Bóc Tách Chi Tiết Từng Kỹ Năng Hệ Thống

Thư mục `bmad/spec/` mô tả chi tiết, bóc tách về mặt toán học, thuật toán, luồng dữ liệu và hợp đồng giao tiếp của từng năng lực (Skill) cốt lõi:

| Mã Spec | Tên Kỹ Năng (Skill Specification) | Phân Hệ Phụ Trách | Tài Liệu Chi Tiết |
| :---: | :--- | :--- | :---: |
| **SPEC-01** | **Kỹ năng Thu thập Dữ liệu & Sổ lệnh OKX**<br>Ghép lệnh chuẩn FIFO, phát hiện om vị thế, tính PnL và Drawdown chuỗi thời gian thực. | `sources/bot_source.py`<br>`market/service.py` | [Xem Spec 01](bmad/spec/SPEC-01_OKX_INGESTION_AND_LEDGER_SKILL.md) |
| **SPEC-02** | **Kỹ năng Nhận diện Chế độ Thị trường & Phân tích Nến**<br>Keltner Channels (EMA 20, ATR 14), 4 chế độ thị trường vi mô/vĩ mô, đồng thuận BTC Beta. | `market/service.py`<br>`lenses/market_alignment.py` | [Xem Spec 02](bmad/spec/SPEC-02_MARKET_REGIME_AND_STRUCTURE_SKILL.md) |
| **SPEC-03** | **Kỹ năng Đo lường Rủi ro Lượng hóa 10 Chiều**<br>Fat-tail VaR/CVaR, Đòn bẩy hiệu dụng, Trượt giá khớp lệnh, Bẫy Martingale/DCA, Strategy Drift. | `qc/evaluator/lenses/` | [Xem Spec 03](bmad/spec/SPEC-03_TEN_DIMENSIONAL_QUANTITATIVE_RISK_SKILL.md) |
| **SPEC-04** | **Kỹ năng Mô phỏng Monte Carlo & Bootstrap Thống kê**<br>10.000 kịch bản Stationary Bootstrap (Politis & Romano 1994), Deflated Sharpe (DSR), PSR, MinTRL. | `mcp/analytics/simulation/` | [Xem Spec 04](bmad/spec/SPEC-04_MONTE_CARLO_AND_STATIONARY_BOOTSTRAP_SKILL.md) |
| **SPEC-05** | **Kỹ năng Veto An toàn & Xếp loại Chất lượng**<br>Ma trận phân loại 4 góc phần tư (Drawdown vs Quality), 6 điều kiện Veto cứng, tính toán Risk Score 0–100. | `qc/scoring/verdict.py`<br>`qc/reporting/reasons.py` | [Xem Spec 05](bmad/spec/SPEC-05_SAFETY_VETO_AND_DECISION_ENGINE_SKILL.md) |
| **SPEC-06** | **Kỹ năng Tổng hợp Nhận định Chuyên môn Định tính**<br>Cấu trúc lập luận 3 tầng (Kết luận → Nguyên nhân cốt lõi → Luận cứ chứng minh `◆`), loại bỏ nhãn AI thô. | `qc/reporting/narrative.py`<br>`web/report_page.py` | [Xem Spec 06](bmad/spec/SPEC-06_QUALITATIVE_NARRATIVE_SYNTHESIS_SKILL.md) |
| **SPEC-07** | **Kỹ năng Máy chủ MCP & Thanh toán Vi mô x402**<br>Chuẩn giao tiếp Model Context Protocol (JSON-RPC 2.0), thanh toán USDC onchain x402, chống replay attack. | `backend/agent_server.py`<br>`payments/x402.py` | [Xem Spec 07](bmad/spec/SPEC-07_MCP_SERVER_AND_MICRO_PAYMENTS_SKILL.md) |
| **SPEC-08** | **Kỹ năng Giao diện Quản trị & Báo cáo Bot Chuẩn Fintech**<br>Hệ thống Design Tokens (`tokens.css`), triết lý 70% OKX + 30% Neo-Brutalism, Deep Slate Obsidian, radar SYSTEM ONLINE. | `frontend/`<br>`web/tokens.css`<br>`web/report_page.py` | [Xem Spec 08](bmad/spec/SPEC-08_INSTITUTIONAL_UI_AND_VISUALIZATION_SKILL.md) |

---

## 4. Tiêu Chuẩn Truy Vết & Kiểm Thử Hệ Thống (Verification Matrix)

Mọi kỹ năng trong bộ Spec và mọi chặng trong bộ Story đều được bảo đảm bằng bộ kiểm thử tự động toàn diện:
- **Pytest Suite:** Đạt **99/99 bài test PASS** trong [test_report_page.py](file:///home/ubuntu/norabt/Agent/test/test_report_page.py) cùng toàn bộ các bài test đơn vị trong `Agent/test/`.
- **Docker Compose Services:**
  - `norabt-agent-web` (Cổng 8770): Phục vụ REST API, React SPA bundle và trang báo cáo HTML máy chủ.
  - `norabt-agent-redis` (Cổng 6379): Bộ đệm snapshot kết quả thẩm định dưới 50ms.
- **Frontend SPA Build:** Vite bundle biên dịch tối ưu (199 KB JS gzip 65 KB, 18.7 KB CSS gzip 4.6 KB).
