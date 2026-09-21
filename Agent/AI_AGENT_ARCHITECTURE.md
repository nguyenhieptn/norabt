# Kiến Trúc NoraBT: Autonomous AI Risk Supervisor
> **Hệ thống Giám sát & Đánh giá Rủi ro Bot Copy-Trading OKX**  
> **Định hướng dự thi:** [OKX Dev Day 2026](https://luma.com/l4aq8vii) — **Track 2: OKX AI (Agents and AI-native businesses)**

---

## 1. Triết Lý Thiết Kế Cốt Lõi (Dual-Engine Architecture)

NoraBT được xây dựng theo nguyên tắc **"Evidence-First & Dual-Engine"**: Tách bạch tuyệt đối giữa **Toán học định lượng** và **Trí tuệ nhân tạo (AI Agent)**.

```text
┌────────────────────────────────────────────────────────────────────────┐
│ 1. DATA INGESTION & RECONCILIATION                                    │
│    OKX Ledger & Positions  ──►  Đối soát sổ lệnh & Bóc trần gồng lỗ    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. DETERMINISTIC QUANT ENGINE (Bộ não tính toán sự thật)              │
│    • 10 Lăng kính rủi ro (Risk Lenses)                                 │
│    • Mô phỏng Monte Carlo 10.000 kịch bản (Stationary Bootstrap)       │
│    • Deflated Sharpe Ratio (DSR), VaR 95%, CVaR, Stress Test           │
│    • Cơ chế Sàn phủ quyết cứng (Veto Floor) & Cờ HIDDEN RISK           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │  (Sealed Analysis Dossier)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. COGNITIVE AI AGENT LAYER (Nhận thức, Diễn giải & Giám sát)         │
│    • 3 Cổng kiểm duyệt nghiêm ngặt (Number-Lock, Anti-Hallucination)   │
│    • Executive Risk Narrative (Nhận định chuyên gia)                   │
│    • Interactive Forensic Q&A (Hỏi đáp điều tra chuyên sâu)            │
│    • MCP Server (Model Context Protocol cho Agent-to-Agent)            │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
                    ▼                                ▼
       [Nhà Đầu Tư (Human UI)]         [Các Trading Agent Khác (M2M)]
```

- **Quant Engine giữ "Chân lý" (Truth):** Toàn bộ điểm số, kịch bản sụt vốn, phán quyết đều được tính toán bằng toán học xác suất tất định. Không để AI tự ý tính toán hay thay đổi số liệu.
- **AI Agent giữ "Tiếng nói & Nhận thức" (Voice & Cognition):** AI làm nhiệm vụ phiên dịch rủi ro cho người dùng và đóng vai trò người gác cổng (Supervisor) cho các AI Agent khác trong hệ sinh thái OKX.

---

## 2. Ba Vai Trò Sống Còn Của AI Agent

### 2.1. Phiên Dịch Viên Rủi Ro (Risk Translator & Narrative)
- **Vấn đề:** Bề mặt sàn OKX thường hiển thị bot "Win Rate 100%, PnL +300%", người dùng không thể nhận biết bot đang gồng lỗ sắp cháy.
- **Nhiệm vụ của Agent:** Đọc toàn bộ hồ sơ định lượng và viết bản **"Nhận định chuyên môn" (Executive Briefing)**:
  - Bóc trần chiêu trò: *"Bot có lãi chốt lời 2.000 USDT nhưng đang gánh khoản lỗ thả nổi 5.000 USDT chưa cắt. Đóng lệnh lúc này sẽ biến bot thành thua lỗ."*
  - Cảnh báo điều kiện thị trường: *"85% lợi nhuận chỉ gom vào sóng uptrend tháng 3, bot hoàn toàn chưa từng vượt qua pha downtrend."*

### 2.2. Điều Tra Viên Tương Tác (Interactive Forensic Investigator)
- Người dùng không chỉ xem bảng tĩnh mà có thể đối thoại trực tiếp với Agent về hồ sơ bot:
  - *"Tại sao bot này bị dán nhãn HIDDEN RISK?"* $\rightarrow$ Agent giải trình bằng chứng từ sổ lệnh.
  - *"Nếu Bitcoin giảm 20%, tài khoản của tôi sẽ ra sao?"* $\rightarrow$ Agent trích xuất kết quả Stress Test và ngưỡng thanh lý (Liquidation point).

### 2.3. Giám Sát Viên Cho Các Agent Khác (Agent-to-Agent Risk Supervisor)
- **Khớp 100% đề bài OKX AI Track:** *"Tools that help agents work or transact with other agents"*.
- NoraBT đóng gói năng lực thành **MCP Server (Model Context Protocol)** chạy qua `stdio` hoặc `streamable HTTP`.
- Các Autonomous Trading Agent trên OKX trước khi quyết định copy hoặc phân bổ vốn cho một bot bất kỳ sẽ gọi MCP của NoraBT để kiểm tra:
  > **Trading Agent** $\xrightarrow{\text{Call MCP: assess_bot}}$ **NoraBT** $\xrightarrow{\text{Return Verdict: HIDDEN RISK}}$ **Trading Agent từ chối copy**.

---

## 3. Lớp Bảo Vệ Độc Quyền: 3 Cổng Kiểm Duyệt AI (Validation Gates)

Để giải quyết triệt để vấn đề **AI Hallucination (Ảo giác số liệu tài chính)**, module `narrative.py` thiết lập 3 cổng kiểm duyệt kỹ thuật cứng:

1. **Gate 1 — Number Lock (Khóa số liệu tuyệt đối):**  
   Mọi chuỗi số xuất hiện trong văn bản do AI sinh ra bắt buộc phải truy vết được từ hồ sơ Dossier đã tính toán. Nếu AI tự ý bịa ra số mới $\rightarrow$ **Reject & Retry / Fallback ngay lập tức**.
2. **Gate 2 — Future Certainty Gate (Chống cam kết tương lai):**  
   Từ chối các mẫu câu khẳng định chắc chắn về lợi nhuận (*"chắc chắn sẽ lãi", "đảm bảo an toàn"*).
3. **Gate 3 — Imperative Command Gate (Chống lệnh cưỡng ép):**  
   Chặn các câu mệnh lệnh trực tiếp (*"hãy nạp tiền ngay", "bán hết đi"*). Giữ đúng vị thế là chuyên gia phân tích rủi ro độc lập (Read-only Advisor).

---

## 4. Cấu Trúc Thành Phần Kỹ Thuật Đã Có Sẵn

Dự án đã có sẵn nền tảng vững chắc trong codebase, sẵn sàng để hoàn thiện:

- **Quant Core:**
  - `backend/qc/evaluator/lenses/`: 10 lăng kính rủi ro độc lập.
  - `backend/mcp/analytics/simulation/`: Mô phỏng Monte Carlo (10.000 vòng) & Deflated Sharpe.
  - `backend/qc/scoring/fusion.py` & `verdict.py`: Hệ thống 2 trục và cơ chế sàn phủ quyết.
- **AI / Agent Layer:**
  - `backend/qc/reporting/narrative.py`: Bộ sinh nhận định chuyên môn với 3 Validation Gates.
  - `backend/agent_server.py`: MCP Server chuẩn hỗ trợ `stdio` và `streamable HTTP` (6 tools kiểm toán bot).
  - `docs/ideallm.md`: Hợp đồng thiết kế tương tác LLM chuyên sâu.

---

## 5. Lộ Trình Triển Khai (Action Plan cho OKX Dev Day)

### Giai đoạn 1: Chuẩn bị nộp bài (Hạn chót: 25/09/2026)
1. **Hoàn thiện UI Narrative:** Hiển thị khối *"Nora AI Risk Executive Briefing"* nổi bật ở đầu trang chi tiết bot trên giao diện web.
2. **Pre-cache dữ liệu Demo:** Quét và cache sẵn kết quả phân tích + đoạn văn AI cho top 10 bot tiêu biểu (có cả bot tốt, bot sụt vốn cao và bot dính `HIDDEN RISK`) để demo mượt mà, không bị độ trễ API.
3. **Kích hoạt MCP Endpoint:** Kiểm thử lệnh khởi động `python3 -m Agent.backend.agent_server --transport http --port 8765` để chứng minh khả năng tích hợp Machine-to-Machine.

### Giai đoạn 2: Chuẩn bị Live Demo chung kết tại Singapore (07/10/2026)
1. **Interactive Q&A Widget:** Thêm khung chat nhỏ tại frontend cho phép gõ câu hỏi: *"Hỏi Nora AI về bot này"*.
2. **Kịch bản Demo Agent-to-Agent:** Demo trực quan bằng Claude Code hoặc 1 script Python giả lập Trading Agent gọi MCP tool `assess_bot_risk` của NoraBT và tự động hủy lệnh khi thấy rủi ro cao.

---

## 6. Kịch Bản Thuyết Trình Demo 3 Phút (Pitching Script)

- **Phút 1 — Vấn nạn:** *"Trên OKX Copy-Trading, 80% bot top đầu hiển thị tỷ lệ thắng 100% thực chất là bẫy Martingale và gồng lỗ ngầm. Người dùng và các AI Copy-Trading Agent khác đang mất tiền vì tin vào số liệu bề mặt."*
- **Phút 2 — Giải pháp NoraBT:** *"NoraBT là AI Risk Supervisor đầu tiên sở hữu kiến trúc kép: Chạy 10.000 mô phỏng Monte Carlo để bóc trần rủi ro đuôi, kết hợp với AI Agent được khóa số liệu (Zero-Hallucination) để giải trình rủi ro cho người dùng."*
- **Phút 3 — Khả năng mở rộng (The OKX AI Vision):** *"NoraBT không chỉ phục vụ con người. Qua giao thức MCP, NoraBT đóng vai trò là 'Lớp kiểm toán rủi ro độc lập' cho toàn bộ mạng lưới Trading Agent trên OKX AI Marketplace."*
