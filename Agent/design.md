# 📐 TÀI LIỆU THIẾT KẾ GIAO DIỆN (UI/UX DESIGN SPECIFICATION)
## DỰ ÁN: AGENT — QC RISK SUPERVISOR (NORABT)
### Phong cách kết hợp: OKX AI · X LAYER (ZK-EVM) · FINANCIAL AGENTIC WORKSTATION

---

## 1. TỔNG QUAN & ĐỊNH VỊ SẢN PHẨM (EXECUTIVE SUMMARY)

### 1.1 Bối Cảnh & Định Vị Hệ Thống
**Agent — QC Risk Supervisor (NoraBT)** là hệ thống giám sát định lượng và bảo vệ rủi ro độc lập hoạt động trên các bot giao dịch và lead trader (đặc biệt trong hệ sinh thái OKX Copy-Trading, Algo Bots và On-chain Agents). Hệ thống không trade thay bot mà đóng vai trò **Thanh tra Rủi ro Cấp cao (QC Supervisor)** theo kiến trúc 3 logic:
1. **Market Observation** (Nến, Orderbook L2, Funding rate, Thanh khoản, Anchor Clock).
2. **Bot / MCP Analytics** (Lỗ hoãn nhận - Deferred Loss, Nền vốn - Equity Curve, Phân phối giao dịch, Mô phỏng Monte Carlo tail risk).
3. **QC Fusion Core** (Hợp nhất dữ liệu, chấm điểm rủi ro đa chiều, kích hoạt Veto chính sách, phân hạng Cohort).

### 1.2 Mục Tiêu Thiết Kế Giao Diện
Chuyển đổi giao diện từ dashboard báo cáo kiểm thử truyền thống thành một **Trạm điều hành rủi ro chuẩn Web3 FinTech (Next-Gen AI Risk Supervisor Workstation)** mang đẳng cấp quốc tế:
- **Thừa hưởng DNA của OKX AI**: Triết lý *Agentic-first*, dữ liệu mật độ cao (*high data density*), bảng điều khiển mô-đun hoá, tích hợp liền mạch luồng lệnh MCP (Model Context Protocol).
- **Thừa hưởng DNA của X Layer**: Thẩm mỹ hình học tối giản (*Minimalist High-Contrast Geometry*), nền đen Obsidian sâu thẳm, viền sắc nét 1px, ánh sáng phát quang công nghệ Zero-Knowledge (Electric Cyan, ZK Violet, Mint Green), tốc độ cao và cảm giác chuẩn xác toán học.
- **Tích hợp cảm hứng từ các thư viện Financial AI Agent hàng đầu** (*OKX Agent Trade Kit, OnchainOS / Agentic Wallet, ElizaOS, GOAT*): Giao diện tương tác câu lệnh tự nhiên (Agent Command HUD), minh bạch hoá các bước suy luận (*Chain-of-Quant*), trực quan hoá gọi công cụ MCP (*Tool Invocations & Telemetry*).

---

## 2. KHẢO SÁT & ĐỐI SÁNH THIẾT KẾ (BENCHMARK & RESEARCH)

### 2.1 OKX AI & OKX Agent Trade Kit
* **Triết lý "Agentic-First" & "Invisible UI"**:
  - OKX không tạo ra một ứng dụng AI tách rời, mà nhúng năng lực AI thông qua **Agent Trade Kit** sử dụng **Model Context Protocol (MCP)** với hơn 80+ công cụ tài chính (Spot, Futures, Options, Earn, Orderbook).
  - Tương tác thông qua câu lệnh tự nhiên kết hợp cấu trúc trả về dạng bảng, thẻ dữ liệu và biểu đồ đo đạc tức thì.
  - Phím tắt điều hướng nhanh, các thẻ tóm tắt rủi ro (*risk limits*) và mô phỏng giao dịch (*transaction simulation*) trước khi thực thi.
* **OKX Design System (OKDS)**:
  - Bố cục lưới thông tin đa tầng (*multi-panel grid*), ưu tiên khả năng hiển thị đồng thời nhiều chiều dữ liệu: sổ lệnh, PnL, vị thế mở mà không gây rối mắt.
  - Tương phản tuyệt đối: Nền than chì sâu (`#0B0F19` đến `#000000`), chữ trắng sáng rõ, mã màu tài chính chuẩn xác (Xanh lá tăng / Đỏ giảm / Vàng cảnh báo).

### 2.2 X Layer (OKX Zero-Knowledge Layer 2)
* **Bản sắc thị giác (Brand Identity)**:
  - Nền tảng phát triển dựa trên Polygon CDK với công nghệ Zero-Knowledge Rollup.
  - Thẩm mỹ: Tối giản công nghệ cao (*Cyber-Minimalism*), các khối hình học sắc nét với điểm nhấn chữ **"X"** biểu trưng cho sự kết nối đa chuỗi và sức mạnh thuật toán.
  - Bảng màu: Lấy Đen nhung (`#000000`) và Trắng tinh khiết (`#FFFFFF`) làm nền móng kiên cố; bổ sung các dải phát quang ZK Violet (`#8B5CF6`) và Cyber Cyan (`#00F0FF`) cho các trạng thái xác thực mật mã (*Cryptographic Proofs*).
  - Chiều sâu giao diện: Kính mờ siêu mỏng (*Subtle Frosted Glass* - 1px border với opacity 8-12%), bóng đổ đa tầng mịn không gắt.

### 2.3 Các Thư Viện Financial AI Agent Tiêu Biểu
* **OKX OnchainOS & Agentic Wallet**:
  - Khái niệm ví tự trị cho AI: Bảo vệ khoá bí mật bằng TEE (*Trusted Execution Environment*), định danh Agent On-chain bền vững (*Persistent Identity*), hệ số uy tín danh tiếng (*Reputation Score*).
  - Yếu tố UI cần có: Badge trạng thái TEE Enclave, ID xác thực agent, nhãn chứng thực độ tin cậy của thuật toán.
* **ElizaOS (ai16z)**:
  - Cấu trúc Agent State, Evaluator và Action Provider.
  - Yếu tố UI: Thẻ đánh giá nhân cách/mục tiêu của Agent, tiến trình suy luận đa tác tử (*Multi-agent consensus*).
* **GOAT (Great Onchain Agent Toolkit)** & **MCP (Model Context Protocol)**:
  - Cung cấp khả năng gọi công cụ chuẩn hoá (Tool calls: `calculate_deferred_loss`, `simulate_monte_carlo`, `inspect_orderbook_liquidity`).
  - Yếu tố UI: Thanh tiến trình thực thi công cụ (*Tool Invocation Breadcrumb*), thời gian trễ (*Latency monitor*), mức độ tự tin (*Confidence Level*).

---

## 3. HỆ THỐNG THIẾT KẾ ĐẶC QUYỀN (NORA X-DS DESIGN SYSTEM)

### 3.1 Bảng Màu Nhận Diện (Chromatic Palette & Tokens)

Hệ thống token màu được cấu trúc hóa theo chuẩn HSL / Hex phục vụ Dark Theme chuyên sâu:

```css
:root, [data-theme="dark"] {
  /* --- Nền Vũ Trụ & Thẻ Bề Mặt (Obsidian & Void Layers) --- */
  --bg-app:                #06080d;   /* Nền sâu thẳm toàn màn hình */
  --bg-surface:            #0b0f19;   /* Lớp nền nội dung chính */
  --bg-card:               #111726;   /* Thẻ card nổi lớp 1 */
  --bg-card-hover:         #162035;   /* Thẻ card khi hover */
  --bg-card-emphasis:      #131d2e;   /* Thẻ ưu tiên điểm nhấn */
  --bg-overlay:            rgba(6, 8, 13, 0.85);

  /* --- Đường Viền Kỹ Thuật (Precision Borders - 1px) --- */
  --border-subtle:         rgba(255, 255, 255, 0.07);
  --border-base:           #1e293b;
  --border-emphasis:       #25334e;
  --border-glow-cyan:      rgba(0, 240, 255, 0.4);
  --border-glow-purple:    rgba(139, 92, 246, 0.4);

  /* --- Màu Văn Bản (High Contrast WCAG AAA/AA) --- */
  --text-primary:          #f8fafc;   /* 100% Trắng sáng ngà */
  --text-secondary:        #94a3b8;   /* 60% Xám slate nhạt */
  --text-muted:            #64748b;   /* 40% Xám ghi kỹ thuật */
  --text-inverse:          #06080d;

  /* --- Dải Màu Thương Hiệu OKX AI & X Layer --- */
  --xlayer-cyan:           #00f0ff;   /* Neon Cyan: Tốc độ, luồng live, anchor clock */
  --xlayer-violet:         #8b5cf6;   /* ZK Violet: Thuật toán QC, mật mã, verify */
  --xlayer-electric-blue:  #3b82f6;   /* Primary Action, button, link chính */
  --xlayer-mint:           #00e599;   /* Mint Green: An toàn, sustainable, pass veto */

  /* --- Hệ Thống 6 Hạng Kết Luận Rủi Ro (Verdict Tiers) --- */
  --verdict-low-dd-good-q:   #10b981; /* BỀN VỮNG: Sụt vốn thấp · Chất lượng tốt (Mint Green) */
  --verdict-low-dd-weak-q:   #0284c7; /* PHÙ PHIẾM: Sụt vốn thấp · Chất lượng yếu (Sky Blue) */
  --verdict-high-dd-good-q:  #f59e0b; /* DRAWDOWN: HIGH · QUALITY: GOOD (Amber Orange) */
  --verdict-high-dd-weak-q:  #ef4444; /* DRAWDOWN: HIGH · QUALITY: WEAK (Crimson Red) */
  --verdict-hidden-risk:     #a855f7; /* RỦI RO BỊ CHE: Lỗ hoãn nhận / Lệnh kẹp (Purple Warning) */
  --verdict-unknown:         #64748b; /* THIẾU DỮ LIỆU: Chưa đủ bằng chứng (Neutral Muted) */

  /* --- Tín Hiệu Nghiệp Vụ Cốt Lõi --- */
  --alert-deferred-loss:     #ff0055; /* Đỏ neon cảnh báo lỗ mở âm nặng */
  --alert-wiped-out:         #ff1744; /* Báo động tài khoản chạm -100% PnL */
  --status-stale:            #eab308; /* Dữ liệu cũ lệch anchor clock */
  --status-fresh:            #10b981; /* Dữ liệu khớp anchor thời gian */
}
```

### 3.2 Hệ Thống Typography Kỹ Thuật (Type Hierarchy)
Đảm bảo tính chân thực của công cụ tài chính chuyên nghiệp:
- **Display & Headings (Space Grotesk)**: Dành cho tiêu đề màn hình, tên mã Bot, điểm số rủi ro Hero Score (mang âm hưởng hình học Web3 hiện đại).
- **Body & Controls (Inter)**: Dành cho nội dung giải trình, nhãn nhãn form, văn bản báo cáo (đạt chuẩn tương phản cao, chống mỏi mắt khi đọc lâu).
- **Data & Numerals (JetBrains Mono)**: Toàn bộ con số tài chính (AUM, PnL, Win Rate, Expectancy, Max Drawdown, Giá, Khối lượng, Địa chỉ ví). Bắt buộc bật thuộc tính `font-variant-numeric: tabular-nums` để các cột số luôn thẳng hàng hoàn hảo.

| Cấp bậc | Font | Kích thước | Line Height | Tracking | Ứng dụng |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hero 2XL** | Space Grotesk Bold | `clamp(2.0rem, 2.5vw, 3.2rem)` | 1.1 | -0.03em | Điểm tổng rủi ro (0-100), Tên Bot |
| **Heading XL**| Space Grotesk SemiBold | `clamp(1.4rem, 1.8vw, 1.9rem)` | 1.25 | -0.02em | Tiêu đề 4 Lens kiểm định, Card Header |
| **Heading LG**| Space Grotesk Medium | `1.25rem (20px)` | 1.3 | -0.01em | Tiêu đề khối dữ liệu con, Modal title |
| **Body Base** | Inter Regular/Medium | `0.9375rem (15px)` | 1.5 | 0.00em | Văn bản phân tích, tóm tắt QC fusion |
| **Data Mono** | JetBrains Mono Medium | `0.875rem (14px)` | 1.4 | -0.01em | Bảng chỉ số, PnL, PF, Monte Carlo VaR |
| **Eyebrow/Tag**| JetBrains Mono Bold | `0.72rem (11.5px)` | 1.2 | 0.08em | Nhãn phân loại UPPERCASE, Status Chip |

### 3.3 Hiệu Ứng Chiều Sâu & Ánh Sáng (Elevation, Glass & Ambient Glow)
1. **Lớp nền không gian 3 tầng (3-Tier Layering)**:
   - *Tầng 0*: Background `#06080D` phủ vân lưới kỹ thuật cực mờ (`grid-pattern: rgba(255,255,255,0.02)` 32px x 32px).
   - *Tầng 1*: Card Module `#111726` với viền `1px solid var(--border-subtle)`.
   - *Tầng 2*: Floating Island / Active Card với viền phát sáng gradient mềm (`linear-gradient(135deg, rgba(0,240,255,0.3), rgba(139,92,246,0.2))`).
2. **Kính mờ X-Layer Glass**:
   - `backdrop-filter: blur(16px) saturate(180%)`
   - Background: `rgba(17, 23, 38, 0.75)`
   - Border: `1px solid rgba(255, 255, 255, 0.08)`
3. **Hiệu ứng phát quang định hướng (Directional Ambient Glow)**:
   - Dành riêng cho trạng thái Veto (`box-shadow: 0 0 30px -5px rgba(239, 68, 68, 0.25)`).
   - Dành riêng cho Bot đạt chuẩn Sustainable (`box-shadow: 0 0 30px -5px rgba(0, 229, 153, 0.2)`).

---

## 4. KIẾN TRÚC THÔNG TIN & TRẢI NGHIỆM NGƯỜI DÙNG (IA & UX FLOWS)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                    GLOBAL HUD: ANCHOR CLOCK · ENGINE STATUS · WALLET/ROLE        │
├──────────────────────────────────────────────────────────────────────────────────┤
│           NATURAL LANGUAGE AGENT COMMAND BAR (OKX AI Copilot / Quick Query)      │
├───────────────────────────────┬──────────────────────────────────────────────────┤
│       MAIN VIEWPORTS          │                DYNAMIC INSPECTOR                 │
│                               │                                                  │
│  [1] COHORT RISK MATRIX       │  [3] BOT DEEP-DIVE X-RAY (/bot/<code>)           │
│      - Multi-column datagrid  │      - Hero Assessment & Veto Banner             │
│      - Deferred Loss delta    │      - 4 Quant Lenses Split:                     │
│      - Filter by Verdict/AUM  │        • Lens 1: Real PF & Expectancy            │
│                               │        • Lens 2: Equity Curve & Cash Flow        │
│  [2] BATCH MCP RUNNER         │        • Lens 3: Orderbook Depth & Stale Budget  │
│      - Auto snapshot triggers │        • Lens 4: Monte Carlo Tail Risk (VaR/CVaR)│
│      - Data crawl freshness   │      - Marked-to-Market Open Positions Matrix    │
│                               │                                                  │
├───────────────────────────────┴──────────────────────────────────────────────────┤
│     TELEMETRY DOCK: MCP Tool Logs · Stale Warnings · TEE Security Verification   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Thanh Điều Hành Toàn Cục (Global Agent HUD)
Nằm cố định ở đầu màn hình (Top Sticky Header), độ cao 56px:
- **Logo NoraBT x OKX AI & X Layer**: Biểu tượng hình học cách điệu kèm huy hiệu mạng.
- **Anchor Clock Widget**:
  - Khẳng định triết lý Snapshot Crawl: Hiển thị mốc thời gian chốt của bộ dữ liệu (`Anchor: 2024-03-28 14:00:00 UTC`).
  - Đèn tín hiệu xung nhịp (Pulse indicator): Xanh khi dataset đồng bộ, Vàng cam khi có luồng dữ liệu bị `STALE` (ví dụ: orderbook lệch nến).
- **Engine State**: Báo hiệu trạng thái backend (`QC Core: READ_ONLY`, `MCP Analytics: ACTIVE`).
- **Identity & Session Capsule**:
  - Dành cho `user`: Hiển thị địa chỉ ví rút gọn (`0x71...8F9C` hoặc User Ref Code), vai trò Read-only.
  - Dành cho `admin`: Huy hiệu chìa khoá vàng, mở quyền tra cứu danh sách toàn bộ lead trader và kích hoạt crawl lại.

### 4.2 Thanh Lệnh Tự Nhiên & Tìm Kiếm Thông Minh (Agent Command Bar)
Học hỏi từ **OKX Agent Trade Kit** và Command Palette hiện đại (`Cmd + K` / `Ctrl + K`):
- Cho phép người dùng nhập tự nhiên hoặc chọn gợi ý tức thì:
  - *"Tìm các bot có lỗ mở > 15% vốn"* (`filter: deferred_loss >= 15%`)
  - *"So sánh độ sụt vốn thực giữa HaveARestin và RuiJie"*
  - *"Liệt kê top 5 bot chịu được cú sốc thanh toán Monte Carlo"*
  - *"Tra cứu mã lead trader: 8B92F1A"*
- Phản hồi dạng tức thì (Sub-100ms instant feedback): Dropdown kết quả hiển thị thẻ tóm tắt thu nhỏ (Mini-Card) với màu sắc Verdict, AUM, và cảnh báo Lỗ Hoãn Nhận trước khi click.

### 4.3 Bảng Ma Trận Cohort (Cohort Risk Leaderboard)
Màn hình trung tâm quản trị và giám sát danh sách bot:
- **Cột Trọng Tâm: So Sánh Danh Nghĩa vs Thực Tế**:
  - **Cột PnL & PF Đóng**: Hiển thị con số bot tự công bố trên sàn.
  - **Cột Lỗ Hoãn Nhận (Deferred Loss)**: Số tiền và tỷ lệ phần trăm lỗ đang gồng âm.
  - **Cột PF Điều Chỉnh**: Ví dụ `11.09 → 0.16` (Kèm nhãn chuyển hạng `SUSTAINABLE → LOSING`).
  - **Dấu Chấm Than Cảnh Báo (`!`)**: Chỉ xuất hiện khi việc chốt lỗ mở làm **thay đổi bản chất kết luận** (tránh báo động giả như giải thích trong README.md).
- **Bộ Lọc Đa Chiều Nhanh (Smart Filter Pills)**:
  - `Tất cả` · `Bền Vững (Mint)` · `Rủi Ro Bị Che (Tím)` · `Nguy Hiểm (Đỏ)` · `Đang Gồng Lỗ ≥ 10%`.
- **Tương tác dòng (Row Hover & Action)**:
  - Rê chuột làm sáng dòng bằng hiệu ứng kính viền Cyan mỏng.
  - Nhấp chuột kích hoạt mở trạm kiểm định chi tiết (`/bot/<code>`).

---

## 5. THIẾT KẾ CHI TIẾT TRẠM KIỂM ĐỊNH BOT (BOT DEEP-DIVE INSPECTOR)

Trang chi tiết bot (`/bot/<code>` hoặc modal toàn màn hình) là nơi thể hiện tinh hoa của hệ thống QC Supervisor, kết hợp giao diện Starlette Server-Render tốc độ cao và các module tương tác động:

### 5.1 Khối Tiêu Điểm: Thước Đo Rủi Ro & Biểu Ngữ VETO (Hero Assessment Card)
1. **Thước đo rủi ro trực quan (Radial Risk Arc / Gauge)**:
   - Thang điểm từ 0 (Hoàn toàn an toàn) đến 100 (Cực kỳ nguy hiểm).
   - Vòng cung viền gradient đổi màu theo điểm số:
     - 0 - 39: Xanh Mint (`--verdict-low-dd-good-q`)
     - 40 - 59: Xanh Lam Trời (`--verdict-low-dd-weak-q`)
     - 60 - 74: Vàng Hổ Phách (`--verdict-high-dd-good-q`)
     - 75 - 100: Đỏ Thẫm Cảnh Báo (`--verdict-high-dd-weak-q`)
2. **Khung Cảnh Báo Veto Tuyệt Đối (Veto Enforcement Banner)**:
   - Khi bot vi phạm các quy tắc nghiêm ngặt (Ví dụ: Lỗ mở ≥ 15% vốn, hoặc tuần có `wiped_out = true`):
   - Banner màu đỏ thẫm viền phát quang nhấp nháy nhẹ:
     > 🛑 **VETO ĐƯỢC KÍCH HOẠT: SÀN RỦI RO CỐ ĐỊNH 70 ĐIỂM**  
     > *Lý do*: Lỗ hoãn nhận đang âm $14,230 (chiếm 26.4% vốn khả dụng). Kết luận bị hạ thẳng từ Hạng 1 xuống Hạng 4.

### 5.2 Lưới 4 Thấu Kính Định Lượng (The 4 Quant Lenses Grid)

Bố cục 2x2 hoặc 4 cột cân xứng phản ánh trung thực kết quả phân tích từ `BotResult` và `MarketResult`:

#### Thấu Kính 1: Hiệu Suất & Lỗ Hoãn Nhận (Performance Lens)
- **Visual Card**: Thẻ đo đa tầng.
- **Dữ liệu mấu chốt**:
  - Profit Factor (PF) danh nghĩa vs PF điều chỉnh.
  - Win Rate đóng vs Win Rate toàn diện.
  - Trạng thái Lỗ Mở: Phân loại theo 4 cấp bậc (`NO_CLOSED_TRADES`, `REPRESENTATIVE`, `PARTIAL`, `UNREPRESENTATIVE`).
  - Thanh so sánh tương phản: Biểu đồ thanh ngang kép trực quan hoá phần lãi đã đút túi so với phần lỗ đang gồng ngầm dưới giá thị trường.

#### Thấu Kính 2: Nền Vốn & Đường Cong Vốn (Capital & Equity Curve Lens)
- **Visual Card**: Biểu đồ đường nét công nghệ cao (Interactive Canvas / SVG).
- **Dữ liệu mấu chốt**:
  - Dựng từ `pnl / pnlRatio` từng tuần của OKX để tạo ra **toàn bộ đường cong vốn thực tế**, không dùng con số AUM tĩnh.
  - **Điểm đánh dấu nạp/rút gộp**: Thể hiện các xung đột dòng tiền bất thường (ví dụ: dòng nạp rút gộp 3.3M USD nhưng net chỉ 9k USD).
  - **Điểm cảnh báo Cháy Tài Khoản (`Wiped Out Badge`)**: Điểm rơi rụng tuần có `pnlRatio = -1.0` được ghim cờ đỏ cảnh báo vĩnh viễn.
  - Drawdown lịch sử tính theo equity tại đúng thời điểm đóng từng lệnh (`equity_at(close_time)`).

#### Thấu Kính 3: Thanh Khoản Thị Trường & Ngân Sách Stale (Market Liquidity Lens)
- **Visual Card**: Thước đo độ lệch thời gian (Time Disparity Bar) + Độ sâu sổ lệnh L2.
- **Dữ liệu mấu chốt**:
  - **Đồng hồ Anchor vs Nguồn dữ liệu**:
    - Nến 1h BTC: Khớp 100% (Freshness Score: A)
    - Sổ lệnh L2: Hiển thị độ lệch thực tế (ví dụ: lệch ~550 ngày → Gán nhãn `STALE`).
  - **Phạt giảm tự tin (Confidence Penalty)**: Thanh hiển thị mức sụt giảm độ tin cậy từ 1.0x xuống 0.4x khi dữ liệu sổ lệnh không đồng nhất.

#### Thấu Kính 4: Mô Phỏng Đuôi Rủi Ro Monte Carlo (Tail Risk Simulation Lens)
- **Visual Card**: Phân phối xác suất dạng sóng phổ (Probability Density Histogram).
- **Dữ liệu mấu chốt**:
  - 1,000 kịch bản mô phỏng tương lai chạy trên nền equity mới nhất.
  - **Hình phạt Deferred Loss Bias**: Hiển thị rõ vùng đuôi lỗ (Tail Risk) bị kéo giãn ra do phân phối lệnh đóng thiếu hụt các khoản lỗ chưa ghi nhận.
  - Chỉ số VaR (Value at Risk 95%) và CVaR (Conditional VaR / Expected Shortfall).

### 5.3 Bảng X-Ray Vị Thế Mở (Open Position & Orderbook Inspection)
- Đọc cả hai schema vị thế của OKX (vị thế đang giữ và chi tiết từng nhánh).
- Bảng hiển thị:
  - Cặp giao dịch (`BTC-USDT-SWAP`, `ETH-USDT-SWAP`) kèm đòn bẩy (`Cross 20x`, `Isolated 5x`).
  - Giá vào lệnh (Entry Price) vs Giá đánh dấu hiện tại (Mark Price).
  - Khoảng cách tới giá thanh lý (Liquidation Distance %): Chữ đỏ nhấp nháy nếu khoảng cách < 8%.
  - Unhedged Exposure (Mức độ phơi nhiễm rủi ro không có bảo hiểm).

---

## 6. THƯ VIỆN COMPONENT KỸ THUẬT (TECHNICAL COMPONENT CATALOGUE)

Dưới đây là đặc tả chi tiết mã HTML/CSS/React mẫu cho các thành phần then chốt của dự án:

### 6.1 Badge Hạng Kết Luận Rủi Ro (Verdict Badge)
Sử dụng các class token chuẩn mực, viền 1px mờ kèm chấm đèn trạng thái:

```jsx
// frontend/src/components/VerdictBadge.jsx
import React from 'react';

const VERDICT_CONFIG = {
  LOW_DD_GOOD_Q: {
    label: "BỀN VỮNG",
    sub: "Sụt vốn thấp · Chất lượng tốt",
    colorVar: "var(--verdict-low-dd-good-q)",
    bg: "rgba(16, 185, 129, 0.1)",
    border: "rgba(16, 185, 129, 0.3)"
  },
  LOW_DD_WEAK_Q: {
    label: "PHÙ PHIẾM",
    sub: "Sụt vốn thấp · Chất lượng yếu",
    colorVar: "var(--verdict-low-dd-weak-q)",
    bg: "rgba(2, 132, 199, 0.1)",
    border: "rgba(2, 132, 199, 0.3)"
  },
  HIGH_DD_GOOD_Q: {
    label: "DRAWDOWN: HIGH · QUALITY: GOOD",
    sub: "Sụt vốn cao · Chất lượng tốt",
    colorVar: "var(--verdict-high-dd-good-q)",
    bg: "rgba(245, 158, 11, 0.1)",
    border: "rgba(245, 158, 11, 0.3)"
  },
  HIGH_DD_WEAK_Q: {
    label: "DRAWDOWN: HIGH · QUALITY: WEAK",
    sub: "Sụt vốn cao · Chất lượng yếu",
    colorVar: "var(--verdict-high-dd-weak-q)",
    bg: "rgba(239, 68, 68, 0.12)",
    border: "rgba(239, 68, 68, 0.35)"
  },
  HIDDEN_RISK: {
    label: "RỦI RO BỊ CHE",
    sub: "Lỗ hoãn nhận nghiêm trọng",
    colorVar: "var(--verdict-hidden-risk)",
    bg: "rgba(168, 85, 247, 0.12)",
    border: "rgba(168, 85, 247, 0.4)"
  },
  UNKNOWN: {
    label: "THIẾU DỮ LIỆU",
    sub: "Chưa đủ cơ sở kết luận",
    colorVar: "var(--verdict-unknown)",
    bg: "rgba(100, 116, 139, 0.1)",
    border: "rgba(100, 116, 139, 0.25)"
  }
};

export function VerdictBadge({ verdictKey }) {
  const config = VERDICT_CONFIG[verdictKey] || VERDICT_CONFIG.UNKNOWN;
  return (
    <div 
      className="verdict-pill"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        padding: "4px 10px",
        borderRadius: "var(--radius-sm, 8px)",
        backgroundColor: config.bg,
        border: `1px solid ${config.border}`,
        color: config.colorVar,
        fontFamily: "var(--sans)",
        fontSize: "var(--font-size-xs, 0.75rem)",
        fontWeight: 600,
        letterSpacing: "0.02em"
      }}
    >
      <span 
        style={{
          width: "6px",
          height: "6px",
          borderRadius: "50%",
          backgroundColor: config.colorVar,
          boxShadow: `0 0 8px ${config.colorVar}`
        }}
      />
      <span>{config.label}</span>
    </div>
  );
}
```

### 6.2 Thẻ So Sánh Lỗ Hoãn Nhận (Deferred Loss Delta Card)

```jsx
// frontend/src/components/DeferredLossCard.jsx
import React from 'react';

export function DeferredLossCard({ nominalPF, adjustedPF, unclosedLoss, lossRatio, status }) {
  const isDangerous = status === 'UNREPRESENTATIVE';
  
  return (
    <div className="card-glass p-4 rounded-xl border border-slate-800 bg-slate-900/60">
      <div className="flex items-center justify-between mb-3">
        <div className="text-xs font-mono tracking-wider text-slate-400 uppercase">
          LỖ HOÃN NHẬN (DEFERRED LOSS)
        </div>
        {isDangerous && (
          <span className="flex items-center gap-1 text-xs font-mono font-bold text-rose-500 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/30 animate-pulse">
            ! ĐỔI HẠNG KẾT LUẬN
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="text-xs text-slate-500">Profit Factor (Đóng → Mở)</div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-lg font-mono line-through text-slate-400">
              {nominalPF ? nominalPF.toFixed(2) : "—"}
            </span>
            <span className="text-sm text-slate-500">→</span>
            <span className={`text-2xl font-mono font-bold ${isDangerous ? 'text-rose-400' : 'text-emerald-400'}`}>
              {adjustedPF.toFixed(2)}
            </span>
          </div>
        </div>

        <div>
          <div className="text-xs text-slate-500">Lỗ Mở Trên Vốn</div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-mono font-bold text-slate-200">
              {(lossRatio * 100).toFixed(1)}%
            </span>
            <span className="text-xs font-mono text-slate-400">
              (-${Math.abs(unclosedLoss).toLocaleString()} USDT)
            </span>
          </div>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-slate-800/80 text-xs text-slate-400 leading-relaxed">
        {status === 'UNREPRESENTATIVE' && (
          <p className="text-rose-300">
            Cảnh báo: Nếu chốt sạch các lệnh lỗ đang mở, hồ sơ sẽ lập tức tụt từ <strong>SUSTAINABLE</strong> xuống <strong>LOSING/FRAGILE</strong>. Các chỉ số công bố trên sàn không còn tính đại diện.
          </p>
        )}
        {status === 'REPRESENTATIVE' && (
          <p className="text-emerald-400/90">
            Hồ sơ trung thực: Vị thế mở an toàn, không làm lệch hạng hiệu suất của bot.
          </p>
        )}
      </div>
    </div>
  );
}
```

### 6.3 Bảng Log Gọi Công Cụ MCP (MCP Tool Invocation Telemetry)

Thành phần hiển thị luồng làm việc thực chiến của các tác tử tài chính:

```html
<div class="mcp-telemetry-panel">
  <div class="mcp-header">
    <span class="mcp-icon">⚡</span>
    <span class="mcp-title">MCP QUANT PIPELINE EXECUTION</span>
    <span class="mcp-latency">Latency: 64ms</span>
  </div>
  <div class="mcp-steps">
    <div class="mcp-step completed">
      <span class="step-num">01</span>
      <span class="step-tool">mcp.market.fetch_anchor_candles</span>
      <span class="step-status">OK (200 nến 1H)</span>
    </div>
    <div class="mcp-step completed">
      <span class="step-num">02</span>
      <span class="step-tool">mcp.analytics.deferred_loss_evaluator</span>
      <span class="step-status">FLAGGED: UNREPRESENTATIVE</span>
    </div>
    <div class="mcp-step completed">
      <span class="step-num">03</span>
      <span class="step-tool">mcp.analytics.monte_carlo_tail_sampler</span>
      <span class="step-status">PENALIZED: Bias 40%</span>
    </div>
    <div class="mcp-step active">
      <span class="step-num">04</span>
      <span class="step-tool">qc.core.fuse_and_apply_veto</span>
      <span class="step-status">VETO ENFORCED (Score: 78)</span>
    </div>
  </div>
</div>
```

---

## 7. QUY TẮC THIẾT KẾ VÀ TRẢI NGHIỆM VÀNG (DO'S & DON'TS)

### 7.1 Những Điều BẮT BUỘC Phải Làm (DO'S)
1. **Luôn hiển thị ngữ cảnh Snapshot**: Không bao giờ trình bày dữ liệu crawl như thể nó là realtime. Mọi màn hình phải có nhãn thời gian Anchor rõ ràng.
2. **Minh bạch hóa sự thật của số liệu**: Mọi chỉ số hiệu suất danh nghĩa (Win Rate, Profit Factor) đều phải đi kèm phiên bản sau khi hạch toán Lỗ Hoãn Nhận nếu có sự khác biệt.
3. **Giữ nguyên khả năng Server-Render độc lập**: Báo cáo chi tiết `/bot/<code>` phải đọc được, in được và chia sẻ được qua một liên kết trực tiếp không phụ thuộc vào trạng thái SPA.
4. **Phông số Mono nhất quán**: Bắt buộc dùng `JetBrains Mono` cho toàn bộ số liệu tài chính để tránh tình trạng các dòng số bị co giật khi giá trị thay đổi.
5. **Đạt chuẩn tương phản tối thiểu WCAG AA**: Mọi văn bản quan trọng phải có tỷ lệ tương phản tối thiểu `4.5:1` trên nền tối.

### 7.2 Những Điều TUYỆT ĐỐI Tránh (DON'TS)
1. **Không tạo báo động giả về tỷ lệ**: Không chia lỗ hoãn nhận cho lãi ròng (vì lãi ròng tiệm cận 0 sẽ làm bùng nổ vô lý), không so mức giảm tương đối đơn thuần (chỉ kích hoạt báo động khi kết luận thực sự đổi hạng).
2. **Không làm phẳng (smooth) đường cong vốn**: Không bỏ các tuần lỗ khỏi biểu đồ equity curve; không che giấu sự kiện `wiped_out = true`.
3. **Không dùng màu sắc lòe loẹt vô nghĩa**: Tránh các màu gradient cầu vồng generic của Web3. Chỉ dùng màu sắc như một tín hiệu nghiệp vụ có định nghĩa rõ ràng.
4. **Không làm mất thanh điều hướng phím bấm**: Phải hỗ trợ điều hướng nhanh bảng số liệu bằng bàn phím (`Tab`, `Enter`, `Esc`, `J/K`).

---

## 8. LỘ TRÌNH TRIỂN KHAI NÂNG CẤP GIAO DIỆN (IMPLEMENTATION ROADMAP)

### Giai đoạn 1: Chuẩn Hoá Tokens & Dark Theme Nền Tảng (Foundation)
- Đồng bộ `Agent/web/tokens.css` với bảng màu OKX AI & X Layer (bổ sung đầy đủ HSL biến thể, tokens phát quang ZK, thang type clamp chuẩn).
- Kiểm tra kế thừa token trong Starlette `report_page.py` và React SPA `frontend/src/styles/global.css`.

### Giai đoạn 2: Tái Cấu Trúc Bảng Cohort & Header Điều Hành (Workspace & Grid)
- Cập nhật `frontend/src/App.jsx` và header với Global HUD (Anchor Clock widget, Trạng thái Snapshot, Identity badge).
- Nâng cấp `frontend/src/pages/AdminHome.jsx` và `UserHome.jsx` với bảng dữ liệu mật độ cao, tích hợp cột so sánh Lỗ Hoãn Nhận và cờ cảnh báo `!`.

### Giai đoạn 3: Hiện Đại Hoá Trang Báo Cáo Chuyên Sâu (Deep-Dive Report Page)
- Tinh chỉnh `Agent/backend/web/report_page.py` để render khối Hero Gauge 0-100 trực quan, Banner Veto sắc sảo và lưới 4 Thấu Kính Định Lượng.
- Bổ sung biểu đồ phân bổ Monte Carlo và đường cong vốn dạng SVG tinh gọn, siêu nhẹ, không phụ thuộc thư viện nặng.

### Giai đoạn 4: Tích Hợp Lệnh Tự Nhiên & Telemetry HUD (Agentic Copilot)
- Tích hợp thanh Command Bar (`Cmd+K`) tra cứu tự nhiên.
- Module hóa bảng log MCP Telemetry giúp người dùng và nhà phát triển quan sát trực tiếp các bước tính toán của AI Risk Supervisor.
