# Phương Pháp Tính Toán Điểm Số NoraBT (Scoring Methodology)

> **Phiên bản:** `qc_fusion.v1`  
> **Mục tiêu:** Đánh giá rủi ro và chất lượng bot giao dịch định lượng bằng toán học xác suất tất định (deterministic), không phụ thuộc vào suy diễn cảm tính.

---

## 1. Kiến Trúc 2 Trục Độc Lập (Two-Axis Architecture)

Kiểm định ngoài mẫu (Out-of-sample validation trên 36 bot) chứng minh:
- Điểm rủi ro tương quan chặt chẽ với **mức sụt vốn tương lai** (Spearman $\rho = 0.64$, 95% CI $[0.39, 0.80]$).
- Điểm rủi ro **KHÔNG** dự báo lợi nhuận tương lai ($\rho = 0.205$, 95% CI $[-0.195, 0.539]$ — chứa giá trị 0).

Do đó, hệ thống tách bạch tuyệt đối thành 2 trục độc lập:

```text
               Chất lượng (Quality Score)
                     TỐT (>= 65)
                          ▲
   SỤT VỐN: THẤP          │          SỤT VỐN: CAO
   CHẤT LƯỢNG: TỐT        │          CHẤT LƯỢNG: TỐT
                          │
◄─────────────────────────┼─────────────────────────► Rủi ro / Sụt vốn (Risk Score)
THẤP (< 70)               │               CAO (>= 70)
   SỤT VỐN: THẤP          │          SỤT VỐN: CAO
   CHẤT LƯỢNG: YẾU        │          CHẤT LƯỢNG: YẾU
                          ▼
                     YẾU (< 65)
```

> **Quyền phủ quyết tuyệt đối (Full Override):**  
> Nhãn **`HIDDEN RISK`** sẽ ghi đè toàn bộ 2 trục nếu bot có dấu hiệu che giấu rủi ro (gồng lỗ không cắt, lọc lịch sử lệnh). Khi đó, cả điểm rủi ro lẫn điểm chất lượng bề mặt đều không còn đáng tin cậy.

---

## 2. Trục Rủi Ro — `risk_score` (Thang 0 – 100)

Điểm đo lường mức độ nguy hiểm và nguy cơ sụt vốn nghiêm trọng của bot (điểm càng cao càng rủi ro).

### 2.1. 10 Lăng Kính Đánh Giá (Risk Dimensions)

Mỗi lăng kính đánh giá độc lập một khía cạnh và cho ra điểm số $0 - 100$ cùng trọng số $W_i$:

| Lăng Kính | Trọng số ($W_i$) | Nội dung đo lường |
| :--- | :---: | :--- |
| **1. `market_alignment`** | 1.0 | Độ lệch pha giữa vị thế bot và xu hướng thị trường thực tế |
| **2. `performance_quality`** | 1.0 | Tỷ lệ thắng, Profit Factor, tỷ số R:R thực tế trên sổ lệnh |
| **3. `return_r_quality`** | 1.0 | Tỷ suất lợi nhuận tương quan với rủi ro đã nhận lãnh |
| **4. `drawdown_risk`** | 1.2 | Độ sâu và chu kỳ chìm trong sụt vốn (underwater curve) |
| **5. `tail_risk`** | 1.5 | Rủi ro đuôi qua mô phỏng Monte Carlo (VaR 95%, CVaR, DSR, PSR) |
| **6. `leverage_exposure`** | 1.2 | Đòn bẩy thực tế, tỷ lệ ký quỹ và độ lớn vị thế mở |
| **7. `behavioral_risk`** | 1.4 | Mẫu hành vi độc hại: Martingale, nhồi lệnh gồng lỗ, DCA âm, revenge |
| **8. `strategy_drift`** | 1.1 | Độ bền bỉ khi thị trường đổi pha (uptrend / downtrend / sideways) |
| **9. `liquidity_execution`**| 0.8 | Thanh khoản cặp coin, độ sâu sổ lệnh và rủi ro trượt giá |
| **10. `portfolio_risk`** | 0.8 | Rủi ro tương quan tài sản và độ tập trung danh mục |

### 2.2. Điểm Trung Bình Có Trọng Số
$$\text{Score}_{\text{base}} = \frac{\sum_{i \in \text{Applicable}} (\text{Score}_i \times W_i)}{\sum_{i \in \text{Applicable}} W_i}$$
*(Các chiều thiếu bằng chứng `UNKNOWN` được tính trung tính 50 điểm, không kéo lệch điểm số).*

### 2.3. Sàn Phủ Quyết Cứng (Veto Floors)
Nếu phát hiện dấu hiệu đặc biệt nguy hiểm, điểm rủi ro cuối cùng sẽ bị **áp mức sàn tối thiểu** (không để điểm trung bình che mờ rủi ro):

1. **Hành vi độc hại (`behavioral_risk` $\ge 85$):** Áp sàn rủi ro tối thiểu **$88.0$**.
2. **Rủi ro đuôi cực đoan (`tail_risk` $\ge 85$):** Áp sàn rủi ro tối thiểu **$85.0$**.
3. **Đánh ngược xu hướng với đòn bẩy cao (`market_alignment` $\ge 85$ và `leverage` $\ge 70$):** Áp sàn rủi ro tối thiểu **$85.0$**.
4. **Bóp méo sổ lệnh do gồng lỗ (`deferred_loss`):** Khi lỗ thả nổi $\ge 15\%$ vốn hoặc việc đóng vị thế sẽ biến bot thành thua lỗ $\rightarrow$ Áp sàn rủi ro tối thiểu **$70.0$**.
5. **Cháy tài khoản khi Stress Test (`stress_verdict == LIQUIDATED`):** Áp điểm tối đa **$100.0$** (kích hoạt `EMERGENCY_STOP`).

### 2.4. Phân Cấp Rủi Ro (Risk Tiers)
- **EMERGENCY** ($100$ điểm do cháy tài khoản ở stress test) $\rightarrow$ Khuyến nghị: `EMERGENCY_STOP` (Cắt 100%).
- **CRITICAL** ($\ge 80$ điểm) $\rightarrow$ Khuyến nghị: `PAUSE` hoặc `REDUCE` 50%.
- **HIGH** ($\ge 65$ điểm) $\rightarrow$ Khuyến nghị: `REDUCE` 30%.
- **ELEVATED** ($\ge 45$ điểm) $\rightarrow$ Khuyến nghị: `BLOCK_NEW_TRADES`.
- **WATCH** ($\ge 30$ điểm) $\rightarrow$ Khuyến nghị: `WARN`.
- **HEALTHY** ($< 30$ điểm) $\rightarrow$ Khuyến nghị: `MONITOR`.
- **UNKNOWN** (Bằng chứng $< 50\%$ và điểm $< 65$).

---

## 3. Trục Chất Lượng — `quality_score` (Thang 0 – 100)

Đo lường năng lực giao dịch thực chất, ngăn việc bot "ngồi yên không làm gì" được xếp hạng cao vì ít rủi ro.

### 3.1. 5 Cấu Phần Chất Lượng

$$\text{Quality Score} = \frac{\sum (\text{Component Score}_k \times \text{Weight}_k)}{\sum \text{Weight}_k}$$

| Cấu Phần | Trọng Số | Cách tính chi tiết |
| :--- | :---: | :--- |
| **`profitability`** | 1.3 | Tính trên Profit Factor sau khi tính cả lỗ thả nổi (`marked_profit_factor`):<br>• $\ge 3.0$: 100đ &nbsp;|&nbsp; $\ge 2.0$: 85đ &nbsp;|&nbsp; $\ge 1.5$: 70đ &nbsp;|&nbsp; $\ge 1.2$: 55đ &nbsp;|&nbsp; $\ge 1.0$: 35đ &nbsp;|&nbsp; $< 1.0$: 0đ |
| **`consistency`** | 1.0 | Yêu cầu $\ge 30$ lệnh:<br>• Expectancy $> 0$: 80đ (ngược lại 10đ)<br>• Cộng/trừ điều chỉnh theo Sharpe ratio: $[-20, +20]$đ |
| **`drawdown_control`**| 1.1 | Đo khả năng giữ mức sụt vốn tối đa không bị vỡ:<br>• $\le 5\%$: 100đ &nbsp;|&nbsp; $\le 10\%$: 85đ &nbsp;|&nbsp; $\le 20\%$: 65đ &nbsp;|&nbsp; $\le 35\%$: 40đ &nbsp;|&nbsp; $\le 60\%$: 15đ |
| **`honesty`** | 1.2 | Tỷ lệ giữa PF thực tế (sau khi mark-to-market) và PF quảng cáo trên lệnh đã chốt:<br>• Tỷ lệ $\ge 0.9$: 100đ &nbsp;|&nbsp; $\ge 0.7$: 80đ &nbsp;|&nbsp; $\ge 0.5$: 55đ &nbsp;|&nbsp; $\ge 0.3$: 30đ<br>• **Nếu bot chưa bao giờ chốt 1 lệnh lỗ nào:** Phạt cố định còn **10đ**. |
| **`robustness`** | 0.9 | Độ bao phủ $\ge 30\%$ các pha thị trường:<br>• Xuất phát 100đ, trừ điểm nếu phụ thuộc $> 40\%$ vào 1 pha sóng.<br>• Trừ 12đ cho mỗi pha thị trường bị lỗ.<br>• Trừ 25đ nếu bot chưa từng chạy qua pha thị trường giảm (downtrend). |

---

## 4. Hệ Thống Phán Quyết (Verdicts) & Cờ Ẩn (Hidden Risk)

### 4.1. Điều Kiện Kích Hoạt `HIDDEN RISK`
Chỉ cần thỏa mãn **bất kỳ 1 điều kiện** nào sau đây, bot lập tức bị gán nhãn `HIDDEN RISK`:
1. Đóng toàn bộ vị thế mở khiến Profit Factor chuyển từ có lãi ($\ge 1.0$) sang lỗ ($< 1.0$).
2. Bot có $\ge 20$ lệnh nhưng chưa từng chốt lỗ bất kỳ lệnh nào.
3. Lỗ thả nổi (unrealised loss) đang gánh $\ge 20\%$ vốn tài khoản.
4. Trên $70\%$ tổng lợi nhuận chỉ đến từ một pha thị trường duy nhất.
5. Chưa từng trải qua pha downtrend (với bot $\ge 20$ lệnh).
6. Mức sụt vốn vượt quá số vốn ghi nhận (drawdown capped).

### 4.2. Phân Loại 2 Trục (Nếu không dính Hidden Risk)
- **`DRAWDOWN: HIGH · QUALITY: GOOD`**: `risk_score` $\ge 70.0$ và `quality_score` $\ge 65.0$.
- **`DRAWDOWN: HIGH · QUALITY: WEAK`**: `risk_score` $\ge 70.0$ và `quality_score` $< 65.0$.
- **`DRAWDOWN: LOW · QUALITY: GOOD`**: `risk_score` $< 70.0$ và `quality_score` $\ge 65.0$.
- **`DRAWDOWN: LOW · QUALITY: WEAK`**: `risk_score` $< 70.0$ và `quality_score` $< 65.0$.
- **`INSUFFICIENT EVIDENCE`**: Dữ liệu không đủ để tính toán tin cậy.
