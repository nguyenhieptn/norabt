# IDEA-01: AI RISK SUPERVISOR — HỆ THỐNG GIÁM SÁT RỦI RO BOT TRADING 3 LOGIC ĐỘC LẬP

> **Document ID:** IDEA-01  
> **Type:** IDEA  
> **Status:** APPROVED BASELINE — COMMITTED  
> **Scope:** AI RISK SUPERVISOR ARCHITECTURE  
> **Evidence as of:** 2026-09-12  
> **Source of truth for:** Ý tưởng và kiến trúc chuẩn hóa của hệ thống AI Risk Supervisor theo 3 Logic độc lập  

---

## 1. Tuyên Ngôn Sản Phẩm (Product Vision)

Sản phẩm là một **AI Risk Supervisor** độc lập đứng trên các trading bot (chuyên biệt cho sàn OKX và các Pool DEX trọng điểm).

Hệ thống:
* **Không cố trade thay bot.**
* **Không phụ thuộc vào nhãn tự xưng của bot** (như Momentum, Mean Reversion, Grid, Martingale...).
* **Không đợi đến khi PnL âm mới phát hiện lỗ.**

### 3 Nhiệm Vụ Cốt Lõi:
```text
A. NHÌN MARKET  → Market hiện tại thực sự đang có trạng thái và đặc tính gì?
B. NHÌN BOT     → Bot thực tế đang trade như thế nào, kết quả và quỹ đạo rủi ro ra sao?
C. KIỂM SOÁT    → Kết hợp 2 nguồn dữ liệu trên để đánh giá rủi ro đa chiều và can thiệp bảo vệ vốn.
```

---

## 2. Kiến Trúc 3 Logic Độc Lập

```text
┌──────────────────────────────────────────┐
│              LOGIC 1                     │
│         MARKET OBSERVATION               │
│                                          │
│ Market Data → Market Result              │
└────────────────────┬─────────────────────┘
                     │
                     │
┌────────────────────▼─────────────────────┐
│              LOGIC 2                     │
│         BOT / MCP OBSERVATION             │
│                                          │
│ OKX Bot Data → Bot Result                │
│              +                           │
│         Trade Analytics                  │
│              +                           │
│       Probability / Simulation           │
│        (Bootstrap & Monte Carlo)         │
└────────────────────┬─────────────────────┘
                     │
                     │
                     ▼
           ╔══════════════════╗
           ║     LOGIC 3      ║
           ║      QC CORE     ║
           ║                  ║
           ║ Market Result    ║
           ║       +          ║
           ║ Bot Result       ║
           ║       ↓          ║
           ║ Final Risk       ║
           ║ Assessment       ║
           ║ (10 Dimensions)  ║
           ╚════════╤═════════╝
                    │
                    ▼
             CONTROL DECISION
             (Separate Execution)
```

---

## 3. LOGIC 1: MARKET OBSERVATION

* **Mục tiêu:** Trả lời khách quan: *"Market thực tế hiện tại có trạng thái và đặc tính gì?"*
* **Phạm vi Universe:** Khóa Top 30 CEX (Turnover USD 24h) và Top 20 DEX (Pool Liquidity).
* **4 Tầng Xây Dựng:**
  ```text
  RAW MARKET DATA → NORMALIZATION → FEATURE CALCULATION → MarketResult
  ```
* **Đặc trưng tính toán:**
  * *Price & Structure:* OHLCV, EMA20/50/200, ATR14, Keltner Bands, Keltner Width Z-Score, Realized Volatility, Range Position.
  * *Orderflow:* Taker Buy/Sell, Taker Ratio, CVD Delta, CVD Slope, CVD Divergence.
  * *Derivatives:* Open Interest (OI), Delta OI Z-score, Funding Rate Z-score, Liquidation Squeeze Index (LSI).
  * *Liquidity:* Orderbook L2 Depth (±0.2%), Depth Imbalance, Slippage Estimates (10k, 50k), Bid/Ask Walls.
  * *Token / Onchain / Macro:* Tax, Honeypot, Holder Concentration, BTC Beta, BTC Correlation.
* **Đầu ra duy nhất:** Hợp đồng `MarketResult`. Tuyệt đối không chứa phán quyết rủi ro bot hay tín hiệu BUY/SELL.

---

## 4. LOGIC 2: BOT / MCP OBSERVATION & SIMULATION

* **Mục tiêu:** Giám sát bot OKX thuộc Universe, xây dựng hồ sơ giao dịch thực chất và chạy các mô hình mô phỏng xác suất toán học.
* **3 Khối Dữ Liệu Bắt Buộc:**
  1. *Current Bot Snapshot:* Equity, Balance, Margin Ratio, Vị thế mở (Side, Size, Leverage, Unrealized PnL, Liquidation Distance).
  2. *Bot Summary Metrics:* Trade count, Win/Loss rate, Total PnL, ROI, Profit Factor, Expectancy, Payoff ratio, Max Drawdown, Sharpe, Sortino, Calmar.
  3. *Full Trade Ledger:* Chuỗi lịch sử lệnh hoàn chỉnh (Entry, Exit, Size, Notional, Realized PnL, Fees, Hold times, MFE, MAE).
* **Phân cấp đo lường R-Multiple (Risk Measurement Mode):**
  * `FULL`: Có Size, Entry, Stop Loss ban đầu → Tính R-Multiple chuẩn.
  * `PARTIAL`: Có Size, Entry, Exit, PnL → Tỷ suất lợi nhuận chuẩn hóa (Normalized Return), không suy diễn initial-risk R.
  * `LIMITED`: Chỉ có PnL tuyệt đối → Phân tích kết quả thực hiện (Outcome analysis).
* **Định Vị Quan Trọng về Monte Carlo:**
  > **Monte Carlo và Bootstrap thuộc về Logic 2 (Bot / MCP Analytics), KHÔNG nằm trong QC Core.**  
  > Bởi vì Logic 2 sở hữu dữ liệu chuỗi lệnh thực tế (`Full Trade Ledger`) và chuỗi vốn (`Equity Curve`) để xây phân phối xác suất.
* **Đầu ra mô phỏng của Logic 2:**
  * `P(MDD > 10%)`, `P(MDD > 15%)`, `P(MDD > 25%)`
  * `P(5+ consecutive losses)`, `P(10+ loss streak)`
  * `P95 Max Drawdown`, `P99 Max Drawdown` (Value at Risk of Drawdown)
  * `P(loss after 500 trades)`, `Expected & Median Terminal Equity`
* **Đầu ra duy nhất:** Hợp đồng `BotResult`.

---

## 5. LOGIC 3: QC CORE (AI RISK SUPERVISOR)

* **Mục tiêu:** Lõi suy luận tối cao. Tiếp nhận `MarketResult` + `BotResult` (đã bao gồm kết quả Monte Carlo từ Logic 2) để trả lời:
  > **“Bot này hiện có nguy hiểm không, nguy hiểm vì gì, và cần làm gì?”**
* **10 Chiều Phân Tích Rủi Ro Độc Lập:**
  1. *Market Alignment:* Xung đột vị thế vs xu hướng và biến động thị trường.
  2. *Performance Quality:* Tính bền vững của lợi nhuận, Expectancy, độ tin cậy mẫu lệnh.
  3. *Return / R Quality:* Phân tích phân phối tỷ suất sinh lời theo `RiskMeasurementMode`.
  4. *Drawdown Risk:* Tốc độ rơi sụt giảm vốn, thời gian chìm dưới nước, Loss clustering.
  5. *Tail Risk:* Diễn giải khách quan kết quả xác suất Monte Carlo & Bootstrap từ Logic 2.
  6. *Leverage / Exposure Risk:* Mức độ đòn bẩy thực tế và khoảng cách an toàn thanh lý.
  7. *Behavioral Risk:* Nhận diện hành vi tự sát (Averaging down, Martingale gấp thếp, Overtrading, Loss chasing).
  8. *Strategy Drift:* Độ lệch giữa chiến lược tự xưng (Declared) và thực tế quan sát (Observed).
  9. *Liquidity / Execution Risk:* Tương quan quy mô vị thế bot với độ sâu sổ lệnh và trượt giá.
  10. *Portfolio / Systemic Risk:* Mức độ tập trung một chiều và tương quan thị trường chung (BTC Beta).
* **Bộ Ba Chỉ Số Đánh Giá (Risk Triad):**
  * `Risk Score`: Điểm tổng hợp từ 0 (An toàn hoàn hảo) đến 100 (Cực đoan).
  * `Confidence`: Độ tin cậy dữ liệu (0 - 100%).
  * `Risk Trend`: Xu hướng rủi ro (`STABLE`, `ACCELERATING_RISK`, `DE_ESCALATING`).
* **Phân cấp trạng thái (Risk Tiers):** `HEALTHY`, `WATCH`, `ELEVATED`, `HIGH`, `CRITICAL`, `EMERGENCY`.
* **Đầu ra duy nhất:** Hợp đồng `BotRiskAssessment`.

---

## 6. CONTROL LAYER (TÁCH BIỆT KHỎI QC DECISION)

* **Mục tiêu:** Tiếp nhận `BotRiskAssessment` từ QC Core và chuyển thành quyết định can thiệp tài khoản cụ thể.
* **Hành vi kiểm soát:** `MONITOR`, `WARN`, `REDUCE` (giảm 30-50% vị thế), `BLOCK_NEW_TRADES`, `PAUSE`, `EMERGENCY_STOP`.
* **3 Chế độ thực thi:**
  * `READ_ONLY`: Ghi nhận nhật ký giám sát, phục vụ dashboard.
  * `ADVISORY`: Gửi webhook/cảnh báo cho đội ngũ quản trị.
  * `AUTOMATED`: Tự động gọi API sàn OKX để can thiệp vị thế.
* **Cơ chế Hysteresis:** Đặt thời gian làm nguội (Cooldown) tránh tình trạng đóng/mở lệnh chập chờn liên tục.

---

## 7. Nguyên Tắc Cốt Lõi Của Toàn Bộ Hệ Thống

1. **Logic 1 chỉ quan sát Market** → Trả `MarketResult`.
2. **Logic 2 quan sát Bot, giữ Ledger và chạy Monte Carlo / Simulation** → Trả `BotResult`.
3. **Logic 3 (QC Core) là nơi duy nhất suy luận** → Không tự bịa phân phối, chỉ kết hợp 2 nguồn dữ liệu để ra `BotRiskAssessment`.
4. **Tầng Control tách biệt** → Chuyển hóa phán quyết rủi ro thành lệnh can thiệp sàn OKX.
5. **Giá trị vượt trội:** Hệ thống không nhìn vào PnL xanh/đỏ nhất thời, mà nhìn vào **quỹ đạo rủi ro (Risk Trajectory)** để phát hiện sớm hiểm họa trước khi tài khoản bị cháy.
