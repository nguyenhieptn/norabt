# NoraBT — AI-Native Quantitative Risk Supervisor & Copier Guard on OKX

> **Track:** OKX AI — Agents & AI-Native Businesses  
> **Live Web App:** `http://localhost:8770` (hoặc Nginx / OKX AI Agent Gateway)  
> **MCP Server Protocol:** JSON-RPC 2.0 trên cổng `8000` (FastMCP / Model Context Protocol)  
> **Documentation Root:** [Agent/docs/readme.md](file:///home/ubuntu/norabt/Agent/docs/readme.md)  
> **BMAD Master Index:** [SPEC-00: Specification Index](file:///home/ubuntu/norabt/Agent/docs/bmad/spec/00_overview/SPEC-00_SPECIFICATION_INDEX.md) & [STORY-00: Progression Status](file:///home/ubuntu/norabt/Agent/docs/bmad/story/00_overview/STORY-00_SYSTEM_PROGRESSION_AND_STATUS.md)  
> **End-to-End Verification:** `17/17 ĐẠT` ([Agent/none/scripts/acceptance_check.py](file:///home/ubuntu/norabt/Agent/none/scripts/acceptance_check.py))  

---

## 1. Executive Summary & Value Proposition

### Problem Statement (Vấn đề)
Thị trường Copy-trading (CEX) và giao dịch Onchain (DEX) trên OKX đang đối mặt với những vấn đề nghiêm trọng:
1. **Nhiễu loạn PnL danh nghĩa & Ẩn giấu Drawdown:** Các lead trader thường che giấu rủi ro bằng cách chốt lời non các lệnh xanh để có tỷ lệ thắng danh nghĩa cao (90%+), trong khi cố tình om các vị thế lỗ thả nổi (floating drawdown) mà không đặt Stop-Loss.
2. **Bẫy Martingale / DCA nhồi lệnh liều lĩnh:** Khi thị trường đi ngược xu hướng, bot tự động nhân đôi khối lượng vị thế để gỡ lỗ. Khi gặp cú sốc thanh khoản (Flash Crash / Thiên nga đen), toàn bộ tài khoản của người sao chép (Copier) bị thanh lý cưỡng bức (cháy tài khoản).
3. **Thiếu hạ tầng đánh giá rủi ro độc lập cho AI Agents:** Trong hệ sinh thái OKX AI Marketplace, chưa có một AI Agent chuyên biệt đóng vai trò là **Giám sát viên Rủi ro Định lượng (Quantitative Risk Auditor)** có khả năng bóc tách sổ lệnh theo chuẩn FIFO, chạy mô phỏng ngẫu nhiên 10.000 kịch bản và cung cấp nhận định chuyên môn không thiên vị.

### Our Solution (Giải pháp)
**NoraBT (Nora Bot Tracker & Supervisor)** là một **AI-Native Risk Supervisor & Copier Guard Agent** vận hành tự chủ:
- **Tái cấu trúc sổ lệnh FIFO:** Nạp dữ liệu lệnh thực tế từ OKX CEX/DEX, ghép cặp mua/bán chuẩn xác, bóc tách triệt để các vị thế đang gồng lỗ và chuỗi PnL ròng.
- **10 Lăng kính rủi ro lượng hóa (10 Quantitative Risk Lenses):** Đánh giá đa chiều về Drawdown, Fat-tail VaR/CVaR 95%, Đòn bẩy hiệu dụng, Rủi ro thanh khoản & trượt giá, Bẫy hành vi Martingale, Sự suy thoái chiến lược (Strategy Drift), và Sự đồng thuận xu hướng với BTC (Market Alignment).
- **Mô phỏng Monte Carlo Stationary Bootstrap 10.000 kịch bản:** Tái lập 10.000 kịch bản tương lai theo phương pháp Politis & Romano (1994), kết hợp kiểm định **Deflated Sharpe Ratio (DSR)** và **Minimum Track Record Length (MinTRL)** của GS. Marcos López de Prado để triệt tiêu may mắn ngẫu nhiên.
- **Cơ chế 6 Tiêu chuẩn Veto An toàn Cứng (Hard Safety Veto):** Lập tức phát cờ đỏ và khuyến nghị rút vốn nếu bot vi phạm các ngưỡng sinh tồn.
- **Tổng hợp nhận định chuyên môn (Narrative Synthesizer):** Sử dụng LLM `agy/gemini-3.8-flash-medium` với cấu trúc lập luận 3 tầng (Kết luận → Nguyên nhân → Bằng chứng thực nghiệm `◆`), vượt qua 5 cổng kiểm duyệt khắt khe (Flesch-Kincaid grade 10–14, cấm từ AI, khóa số liệu).
- **Giao diện đẳng cấp (Elite UI):** Thiết kế **70% OKX AI Fintech + 30% Neo-Brutalism** trên bảng màu Deep Slate Obsidian (`#0B0F19`), hỗ trợ cả React SPA và báo cáo kết xuất máy chủ.

### Business Model (Mô hình kinh doanh AI-native)
NoraBT xây dựng mô hình kinh tế đại lý AI (Agent Economy) qua giao thức **x402 (HTTP 402 Payment Required)**:
- **Phí vi mô x402 trên X Layer (USDC):**
  - Tra cứu danh sách bot đã thẩm định (`list_assessed_bots`): **$0.001 USDC**
  - Truy vấn hồ sơ phân tích chi tiết (`get_assessment`): **$0.002 USDC** (Redis cache < 50ms)
  - Yêu cầu cào dữ liệu mới & chạy 10.000 kịch bản Monte Carlo (`assess_bot`): **$0.050 USDC**
- **B2B Risk-as-a-Service cho Quỹ & Copier:** Gói subscription giám sát danh mục tự động cảnh báo real-time qua Webhook/Telegram khi bot đang sao chép bắt đầu có dấu hiệu om lệnh hoặc vi phạm Veto.

---

## 2. System Architecture & Agent Workflow

### Sơ đồ kiến trúc (System Flow)

```text
[OKX Copier / Trader / AI Agent / Web Client]
                       │
                       ▼
            ┌─────────────────────┐
            │   NoraBT MCP / API  │ ◄───► [Redis Snapshot Cache (<50ms)]
            │  (FastMCP Port 8000)│ ◄───► [Assessment Store (index.json)]
            └──────────┬──────────┘
                       │
                       ▼
      ┌─────────────────────────────────┐
      │     Agent Supervisory Core      │ ◄───► [LLM: agy / Gemini 3.8 Flash]
      │  (ReAct Planner & 5 DoD Gates)  │       (5 Cổng kiểm duyệt nhận định)
      └────────────────┬────────────────┘
                       │
 ┌─────────────────────┴────────────────────────────────────┐
 │                     Tool Execution Layer                 │
 ├────────────────────────────┬─────────────────────────────┤
 │     Hạ tầng OKX / Web3     │      Động cơ Lượng hóa QC   │
 │  - OKX Public Market API   │  - FIFO Ledger Reconstruction│
 │  - OKX Swap / Orderbook L2 │  - 10 Independent Risk Lenses│
 │  - OKX DEX Onchain Pools   │  - 10.000 Monte Carlo Sim    │
 │  - X Layer Micro-pay (x402)│  - 6 Hard Safety Veto Rules  │
 └────────────────────────────┴─────────────────────────────┘
                       │
                       ▼
       [Hồ sơ Thẩm định Độc lập: JSON v3 / React SPA / Server HTML]
```

### Chi tiết thiết kế Agent (Technical Blueprint)

* **Agent Framework:** FastMCP Server (JSON-RPC 2.0) kết hợp Autonomous Supervisory Pipeline hướng sự kiện (`Agent/backend/pipeline.py`, `Agent/backend/scripts/agent_server.py`).
* **LLM Engine:** `agy` / `gemini-3.8-flash-medium` vận hành Động cơ Nhận định Chuyên môn Định tính (`Agent/backend/qc/reporting/narrative.py`).
* **Reasoning Loop (Vòng suy luận):**
  1. *Perceive:* Tiếp nhận yêu cầu kiểm định bot từ mã định danh `uniqueCode` qua giao thức MCP Tool hoặc REST API `/api/analyze`.
  2. *Plan:* Kiểm tra cache Redis và đĩa `data/assessment/`. Nếu chưa có hoặc quá hạn, kích hoạt pipeline nạp lịch sử lệnh OKX CEX/DEX.
  3. *Action:*
     - Tái cấu trúc lịch sử vị thế FIFO (`bot_source.py`).
     - Đo lường 10 lăng kính rủi ro lượng hóa (`qc/evaluator/lenses/`).
     - Chạy mô phỏng 10.000 kịch bản Stationary Bootstrap và tính toán Deflated Sharpe Ratio (`mcp/analytics/simulation/`).
     - Đối chiếu 6 tiêu chuẩn Veto cứng và xác định nhãn xếp loại 4 góc phần tư 2 trục (`qc/scoring/verdict.py`).
     - Kích hoạt LLM sinh bài nhận định chuyên môn 3 tầng có dẫn chứng `◆`.
  4. *Observe & Reflect:* Đưa bài nhận định qua **5 cổng kiểm duyệt tự động** (Độ dài 80-150 từ, Flesch-Kincaid 10.0-14.0, cấm từ AI, khóa số liệu định lượng, văn phong kiểm toán viên). Nếu không đạt, tự động điều chỉnh tham số sinh lại.
* **State & Memory Management:**
  - **Short-term Memory:** Quản lý hàng đợi tác vụ nền `TaskStatusQueue` (`PENDING` → `RUNNING` → `DONE`), ngăn chặn hiện tượng duplicate job khi client làm mới trang.
  - **Long-term Memory:** Kho lưu trữ bất biến `data/assessment/` (JSON Schema `bot_assessment.v3`), chỉ mục đàn bot `index.json`, và tầng đệm `Redis Snapshot Cache` phản hồi tức thì dưới 50ms.

---

## 3. OKX Integration Specifications (Trọng tâm chấm điểm)

| Thành phần OKX | Vai trò trong hệ thống | File triển khai trong Codebase |
| :--- | :--- | :--- |
| **OKX Market / Data API** | Thu thập nến OHLCV, sổ lệnh L2, lịch sử trade, funding rate, open interest và dữ liệu thanh lý | [bot_source.py](file:///home/ubuntu/norabt/Agent/backend/sources/bot_source.py), [service.py](file:///home/ubuntu/norabt/Agent/backend/market/service.py) |
| **OKX Agent Trade Kit / MCP** | Máy chủ FastMCP đạt chuẩn JSON-RPC 2.0 phục vụ các AI Agent trên OKX AI Marketplace | [agent_server.py](file:///home/ubuntu/norabt/Agent/backend/scripts/agent_server.py) |
| **X Layer (Contract / Micro-pay)** | Kiểm thực thanh toán vi mô USDC chuẩn x402, chống replay attack trên mạng X Layer | [x402.py](file:///home/ubuntu/norabt/Agent/backend/payments/x402.py) |

* **Chi tiết On-Chain & Ranh giới An toàn Ví (Safety Boundary):**
  - **Mạng hỗ trợ:** **X Layer Testnet** (Chain ID: 195) & **X Layer Mainnet** (Chain ID: 196).
  - **Hợp đồng thanh toán:** Token USDC chuẩn trên X Layer.
  - **Chính sách Read-Only Tuyệt đối (Negative Capability Guardrail):**
    - NoraBT được thiết kế với **ranh giới an toàn đóng kín**: Hệ thống **KHÔNG BAO GIỜ** yêu cầu hoặc lưu trữ Private Key của người dùng.
    - Đại lý **hoàn toàn không có quyền rút tiền, nộp tiền hay can thiệp vào lệnh giao dịch** (Được bảo vệ bởi 10 bài test phủ định trong `Agent/none/test/test_agent_server.py` và `test_acceptance_gates.py`).
    - NoraBT chỉ đóng vai trò là **Người Giám Sát Độc Lập** đưa ra khuyến nghị khách quan cho nhà đầu tư.

---

## 4. Tools & Functions Directory (Danh mục công cụ của Agent)

Máy chủ MCP cung cấp **6 công cụ chuẩn hóa** phục vụ các Agent khác và người dùng:

### Tool 1: `list_assets`
* **Mục đích:** Liệt kê toàn bộ tài sản đã có dữ liệu nạp trên đĩa và các sàn hỗ trợ (`CEX`/`DEX`).
* **Input Parameters:** `ctx: Context`
* **Output:** JSON danh sách tài sản kèm mảng sàn giao dịch tương ứng (`{"assets": [{"asset": "BTC", "venues": ["CEX", "DEX"]}]}`).
* **Chi phí x402:** Miễn phí (< 10ms).

### Tool 2: `list_bots`
* **Mục đích:** Liệt kê các bot đã cào dữ liệu của một tài sản trên sàn cụ thể.
* **Input Parameters:**
```json
{
  "asset": "BTC",
  "venue_type": "CEX"
}
```
* **Output:** JSON danh sách bot gồm `bot_folder_name`, `nick_name`, `unique_code`.
* **Chi phí x402:** Miễn phí (< 15ms).

### Tool 3: `list_assessed_bots`
* **Mục đích:** Liệt kê danh sách các bot đã được chấm điểm rủi ro từ `index.json`, hỗ trợ lọc theo 6 nhãn phân hạng hai trục.
* **Input Parameters:**
```json
{
  "verdict": "LOW DD · GOOD QUALITY"
}
```
* **Output:** JSON danh sách bot kèm thứ hạng `rank_in_cohort`, `risk_score`, `quality_score`, `verdict`.
* **Chi phí x402:** $0.001 USDC (< 20ms).

### Tool 4: `get_assessment`
* **Mục đích:** Trích xuất kết quả thẩm định định lượng chuyên sâu từ bộ nhớ cache hoặc file JSON.
* **Input Parameters:**
```json
{
  "unique_code": "EF1CC6F40E834D1A"
}
```
* **Output:** Hồ sơ thẩm định đầy đủ gồm 10 lăng kính rủi ro, phân phối Monte Carlo, trạng thái Veto và nhận định chuyên gia.
* **Chi phí x402:** $0.002 USDC (< 30ms).

### Tool 5: `assess_bot`
* **Mục đích:** **Công cụ phân tích nặng nhất:** Nạp dữ liệu sổ lệnh mới nhất từ OKX, tái tạo vị thế FIFO, chạy 10 lăng kính rủi ro, 10.000 kịch bản Monte Carlo và sinh bài nhận định thẩm định.
* **Input Parameters:**
```json
{
  "asset": "BTC",
  "unique_code": "EF1CC6F40E834D1A",
  "venue_type": "CEX"
}
```
* **Output:** Kết quả thẩm định mới nhất được lưu bất biến vào kho dữ liệu và cập nhật bảng xếp hạng.
* **Chi phí x402:** $0.050 USDC (1.5s – 4.8s).

### Tool 6: `get_market`
* **Mục đích:** Lấy thông tin trạng thái thị trường, độ rộng kênh Keltner Channels và chỉ số đối chuẩn BTC.
* **Input Parameters:**
```json
{
  "asset": "BTC",
  "venue_type": "CEX"
}
```
* **Output:** JSON chế độ thị trường (`UPTREND_CALM`, `RANGE_VOLATILE`...), ATR14 và Keltner Bandwidth.
* **Chi phí x402:** $0.001 USDC (< 50ms).

---

## 5. Safety, Risk Limits & Guardrails

* **Bộ 6 Tiêu chuẩn Veto Cứng (Hard Safety Veto):**
  1. `VETO-01 (Kịch bản stress dẫn tới thanh lý):` $CVaR_{95\%} \ge 85\%$ hoặc $MDD_{sim} \ge 90\%$.
  2. `VETO-02 (Rủi ro đuôi mô phỏng cực đoan):` $VaR_{95\%} \ge 60\%$ trong 3 chu kỳ liên tiếp.
  3. `VETO-03 (Hành vi giao dịch hủy hoại):` Nhồi lệnh Martingale $> 3$ bậc hoặc gồng lỗ kéo dài $> 72$ giờ.
  4. `VETO-04 (Đòn bẩy nguy hiểm):` Đòn bẩy hiệu dụng $> 20x$ trên Altcoin hoặc tỷ lệ ký quỹ cận kề thanh lý.
  5. `VETO-05 (Trôi chiến lược - Strategy Drift):` Suy thoái hiệu suất nghiêm trọng giữa backtest và live trading.
  6. `VETO-06 (Bẫy thanh khoản & Trượt giá):` Giao dịch khối lượng lớn trên token thanh khoản mỏng.
* **Ma trận phân loại 4 góc phần tư hai trục:**
  - `SỤT VỐN: THẤP · CHẤT LƯỢNG: TỐT (LOW DD · GOOD QUALITY)`: Lành mạnh nhất, khuyến nghị phân bổ vốn.
  - `SỤT VỐN: THẤP · CHẤT LƯỢNG: YẾU (LOW DD · WEAK QUALITY)`: Lợi nhuận mỏng.
  - `SỤT VỐN: CAO · CHẤT LƯỢNG: TỐT (HIGH DD · GOOD QUALITY)`: Dành cho khẩu vị mạo hiểm cao.
  - `SỤT VỐN: CAO · CHẤT LƯỢNG: YẾU (HIGH DD · WEAK QUALITY)`: Cực kỳ nguy hiểm, cảnh báo cấm sao chép.
  - `RỦI RO BỊ CHE (HIDDEN RISK)`: Có dấu hiệu om lệnh âm hoặc ngụy tạo win rate.
  - `THIẾU BẰNG CHỨNG (UNKNOWN)`: Dữ liệu dưới 30 lệnh, chưa đủ căn cứ toán học.
* **Cơ chế chịu lỗi (Resilience & Rate Limiting):** Tự động áp dụng Exponential Backoff khi API OKX báo lỗi `HTTP 429 Too Many Requests`; fallback về Redis Snapshot mà không làm gián đoạn trải nghiệm người dùng.

---

## 6. Step-by-Step Quickstart (Hướng dẫn chạy thử Local)

Hệ thống có thể khởi chạy và kiểm thử trong vòng **dưới 3 phút**:

### Yêu cầu tiên quyết (Prerequisites)
* Python >= 3.11
* Node.js >= 20.x
* Docker & Docker Compose (tùy chọn)

### Cài đặt từng bước

1. **Clone repository:**
```bash
git clone https://github.com/nguyenhieptn/norabt.git
cd norabt
```

2. **Cấu hình môi trường (`.env`):**
```bash
cp Agent/.env.example Agent/.env
```
*(Hệ thống đã cấu hình sẵn cổng Web 8770, Redis 6379 và chế độ mở `NORABT_ADMIN_OPEN_ACCESS=true` để kiểm thử ngay lập tức).*

3. **Cài đặt thư viện phụ thuộc:**
```bash
pip install -r Agent/requirements.txt
```

4. **Khởi chạy Hệ thống:**
```bash
# Khởi động dịch vụ NoraBT Web & MCP Server
bash start_nora.sh
```

5. **Chạy Bộ Kiểm Thử Nghiệm Thu Đầu-Cuối (100% PASS):**
```bash
PYTHONPATH=. python3 Agent/none/scripts/acceptance_check.py
```
*Kết quả mong đợi:* **ĐẠT toàn bộ 17/17 mục nghiệm thu thực tế trên đĩa.**

---

## 7. Sample Test Prompts (Kịch bản để Giám khảo test)

### Test Case 1: Tra cứu Hồ sơ Thẩm định Định lượng Toàn diện của Bot
* **Hành động:** Mở trình duyệt tại `http://localhost:8770/#/analyze` hoặc gọi API:
```bash
curl -s http://localhost:8770/api/bots | jq '.[0]'
```
* **Kỳ vọng:** Trả về đầy đủ Risk Score, Quality Score, 10 lăng kính rủi ro, phân vị Monte Carlo và nhận định Wall Street tiếng Anh có cấu trúc 3 tầng kèm bằng chứng `◆`.

### Test Case 2: Kiểm tra Phản xạ Veto An toàn đối với Bot Nguy hiểm
* **Prompt MCP:** Gọi tool `assess_bot` với một bot có hành vi gồng lỗ hoặc nhồi lệnh Martingale.
* **Kỳ vọng:** Hệ thống phát hiện $CVaR_{95\%} \ge 85\%$ hoặc gồng lỗ $> 72$h, gán nhãn `VETO-01` hoặc `VETO-03`, xếp vào nhóm `HIGH DD · WEAK QUALITY` và xuất khuyến nghị cấm sao chép ngay lập tức.

### Test Case 3: Kiểm tra Ranh giới An toàn Ví (Negative Capability Test)
* **Kịch bản:** Thử nghiệm gọi lệnh yêu cầu can thiệp rút tiền hoặc thực thi lệnh mua/bán onchain.
* **Kỳ vọng:** Hệ thống kích hoạt cơ chế phòng thủ Guardrail, từ chối toàn bộ các hành động mang tính can thiệp tài sản và khẳng định ranh giới **READ-ONLY SUPERVISOR** của mình.

---

## 8. Cấu Trúc Tài Liệu Kỹ Thuật (BMAD Documentation Standard)

Toàn bộ tài liệu được chuẩn hóa và phân rã chi tiết theo phương pháp luận **BMAD** tại [Agent/docs/bmad/](file:///home/ubuntu/norabt/Agent/docs/bmad/):
- **`bmad/spec/` (Đặc tả chức năng):**
  - `00_overview/`: Bản đồ đặc tả trung tâm ([SPEC-00](file:///home/ubuntu/norabt/Agent/docs/bmad/spec/00_overview/SPEC-00_SPECIFICATION_INDEX.md)) & Ý tưởng khởi nguyên ([IDEA-01](file:///home/ubuntu/norabt/Agent/docs/bmad/spec/00_overview/IDEA-01_REGIME_CONDITIONED_AGENT_EVALUATION.md)).
  - `01_prd_engine1/`: 10 Bản yêu cầu sản phẩm Engine 1 (`PRD-01` đến `PRD-10`).
  - `02_technical_skills/`: 8 Bản đặc tả kỹ năng kỹ thuật chuyên sâu (`SPEC-01` đến `SPEC-08`).
- **`bmad/story/` (Tiến độ & Tình trạng hệ thống):**
  - `00_overview/`: Lộ trình phát triển 8 giai đoạn & Ma trận sẵn sàng kỹ thuật ([STORY-00](file:///home/ubuntu/norabt/Agent/docs/bmad/story/00_overview/STORY-00_SYSTEM_PROGRESSION_AND_STATUS.md)).
  - `02_cex_data_foundation/` đến `10_verification_and_gates/`: 100 User Stories chi tiết theo 10 phân hệ nghiệp vụ.
