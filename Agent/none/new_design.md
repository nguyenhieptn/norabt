# BẢN THIẾT KẾ ĐỀ XUẤT LẠI GIAO DIỆN PHÂN TÍCH RỦI RO BOT (ANALYSIS RESULTS)
> **Mã dự án:** Nora - Risk Management System  
> **Đối tượng áp dụng:** Màn hình chi tiết Bot · Tab *Analysis Results* (Ví dụ case study: [`9A073DDF49603886`](https://agent.expsolution.io/#/admin?tab=bot&code=9A073DDF49603886))  
> **File lưu trữ:** `/home/ubuntu/norabt/Agent/new_design.md`  
> **Mục tiêu:** Tối ưu hóa cấu trúc luồng thông tin theo nguyên tắc **Kim tự tháp ngược (Inverted Pyramid)**: *Quan trọng nhất & Hành động ngay $\to$ Bằng chứng thị giác $\to$ Bóc tách chi tiết nguyên nhân $\to$ Dự báo tương lai & Thẩm định phương pháp luận*. Giải quyết triệt để các bất cập về trải nghiệm người dùng và sự thiếu hợp lý của cụm biểu đồ Monte Carlo.

---

## I. ĐÁNH GIÁ HIỆN TRẠNG & CÁC VẤN ĐỀ CỐT LÕI

### 1. Trật tự ưu tiên thông tin bị xáo trộn (Hierarchy Issues)
* **Khối học thuật bị đưa lên quá sớm:** Khối `QUANTITATIVE METHODOLOGY BASIS` (giải thích 10,000 scenarios, Stationary Bootstrap, Politis & Romano 1994, VaR/CVaR, Spearman $\rho = 0.64$) nằm ngay dưới điểm số tổng quan. Người dùng vào xem bot để biết **bot an toàn hay nguy hiểm và vì sao**, chứ không phải đọc bài báo khoa học. Việc đặt khối này ở vị trí đầu trang làm loãng các cảnh báo cụ thể của bot.
* **Biểu đồ vốn (Growth curve) bị đẩy xuống quá sâu:** Người dùng phải cuộn qua 10 thanh chiều rủi ro mới thấy được biểu đồ tăng trưởng vốn. Trong thẩm định trading, **biểu đồ vốn và cơ cấu thắng/thua là bằng chứng thị giác trực quan nhất** để người dùng kiểm chứng phán quyết.
* **Dữ liệu sống còn bị giấu sang tab khác:** Tab 1 kết luận bot nguy hiểm, nhưng 2 dữ liệu rủi ro thực tế nhất là **Vị thế mở đang gồng lỗ (Unrealised Loss)** và **Sụt giảm vốn chi tiết (Drawdown vs Capital)** lại bị đẩy sang Tab 3 (*Other & Position*).

### 2. Sự phân mảnh & trùng lặp giữa Mục 1 (Conclusion) và Mục 2 (Expert Assessment)
* **Mục 1 (Conclusion):** Nêu `Verdict: HIDDEN RISK`, `Lý do: extreme simulated tail risk; stress scenario ends in liquidation`.
* **Mục 2 (Expert Assessment):** Ngay bên dưới tiếp tục lặp lại thẻ `01 Quantitative Review: HIDDEN RISK, score 100/100, extreme simulated tail risk` và `02 Performance Profile: Investor should not allocate capital`.
* **Hậu quả:** Người dùng phải đọc lại 2 lần một thông điệp giống hệt nhau nhưng dưới hai định dạng khác nhau.

### 3. Các bất cập cốt tử của cụm Biểu đồ Monte Carlo hiện tại
1. **Biểu đồ thanh ngang phân vị (Outcome Percentiles P05 - P95) hiển thị số liệu phi thực tế:**
   - Hiện tại hiển thị: `P05: -3193.0%`, `P25: -2458.0%`, `P50: -1999.5%`...
   - *Bất hợp lý:* Trong thực tế tài chính, khi tài khoản mất **-100% vốn** là đã bị **cháy/thanh lý cưỡng bức (Liquidation / Ruin)**. Việc mô hình toán ngoại suy ra số âm tới `-3000%` do chia cho số vốn tham chiếu nhỏ mà không có cơ chế *Stop-out boundary (sàn phá sản)* khiến người dùng phổ thông hoang mang, không hiểu ý nghĩa, còn chuyên gia thì thấy biểu đồ thiếu thực tế.
2. **Biểu đồ cột nhóm xác suất có lãi (Probability of Profit by Horizon Chart) bị thừa thãi:**
   - Biểu đồ 3 cột đứng (Ngắn hạn - Trung hạn - Dài hạn) chiếm hẳn một dòng lớn nhưng chỉ hiển thị đúng 3 con số % có lãi.
   - Ngay bên dưới, bảng **Multi-horizon comparison** đã hiển thị cả 3 horizon kèm thanh tiến trình màu sắc, số lệnh, tỉ lệ thua và tỉ lệ cháy. Việc có thêm một biểu đồ cột đứng là hoàn toàn dư thừa.
3. **Quá nhiều hộp giải thích lý thuyết chiếm diện tích (Theory Bloat):**
   - Mỗi biểu đồ con trong Monte Carlo đều cõng thêm 1-2 đoạn văn lý thuyết thống kê, biến khu vực này thành một tài liệu học thuật thay vì một bảng điều khiển phân tích rủi ro thực chiến.

---

## II. BẢN THIẾT KẾ CẤU TRÚC MỚI (THE 4-TIER BLUEPRINT)

Cấu trúc trang *Analysis results* được tái thiết kế thành **4 tầng thông tin liền mạch**:

```
┌────────────────────────────────────────────────────────────────────────┐
│ TẦNG 1: TỔNG QUAN & PHÁN QUYẾT HÀNH ĐỘNG (5 GIÂY ĐẦU)                 │
│ • Hero Score Card (Risk 100 · Quality 33 · Conf 61%)                   │
│ • Action Verdict Banner (HIDDEN RISK - Khuyến nghị KHÔNG COPY)         │
│ • Quick Risk Metrics Strip (Vốn, Float PnL -22%, Max DD, Winrate 49%)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ TẦNG 2: BẰNG CHỨNG HIỆU SUẤT THỰC TẾ (15 GIÂY TIẾP THEO)               │
│ • Biểu đồ Vốn tích lũy (Cumulative Capital Curve) & Vết sụt sâu nhất   │
│ • Cơ cấu Thắng / Thua (Win/Loss Composition & Payoff Ratio)            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ TẦNG 3: BÓC TÁCH NGUYÊN NHÂN RỦI RO (1 - 2 PHÚT ĐÀO SÂU)               │
│ • Hợp nhất Nhận định & Nguyên nhân cốt lõi (Executive Root Cause)      │
│ • 10 Chiều rủi ro (Risk Dimensions) xếp theo thứ tự nghiêm trọng nhất  │
│ • Bằng chứng định lượng dạng Terminal (Quant Evidence Console)         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ TẦNG 4: MÔ PHỎNG TƯƠNG LAI & PHƯƠNG PHÁP LUẬN (STRESS TEST & AUDIT)     │
│ • Monte Carlo: Tái thiết kế thành BẢNG TẬP TRUNG CHỈ SỐ RỦI RO CỐT TỬ  │
│   (Loại bỏ biểu đồ rác, giới hạn chặn sàn -100% Cháy vốn)              │
│ • Ghi chú giới hạn dữ liệu (Data Limitations Accordion)                │
│ • Cơ sở lý thuyết & Phương pháp toán học (Ẩn mặc định / Modal popup)   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## III. CHI TIẾT THIẾT KẾ TỪNG TẦNG

### TẦNG 1: TỔNG QUAN & PHÁN QUYẾT HÀNH ĐỘNG (Executive Action Banner)
*Mục tiêu: Trong 5 giây đầu, người dùng biết chính xác bot này có an toàn không và phải làm gì.*

1. **Thẻ Điểm số Hero (Hero Scores):**
   - **Risk Score:** `100/100` (Màu đỏ `tone-danger` - Kích hoạt bởi Emergency Rule: Nguy cơ thanh lý tài khoản).
   - **Quality Score:** `33/100` (Đánh giá chất lượng lợi nhuận thấp).
   - **Confidence:** `61%` (Độ tin cậy dữ liệu trung bình - do lịch sử 225 lệnh).
2. **Banner Phán quyết & Hành động (Actionable Recommendation):**
   - Thay vì chỉ ghi "HIDDEN RISK" trừu tượng, hiển thị rõ ràng:
     > **PHÁN QUYẾT: RỦI RO ẨN CỰC KỲ CAO (VETO BỞI HỆ THỐNG)**  
     > **Khuyến nghị:** **TUYỆT ĐỐI KHÔNG COPY BOT NÀY.** Nếu đang theo dõi hoặc đã copy, hãy cân nhắc đóng vị thế ngay để tránh rủi ro thanh lý tài khoản.
3. **Thanh chỉ số rủi ro nhanh (Quick Risk Metrics Strip):**
   - Đặt 5 thông số cốt tử thành một hàng ngang nổi bật ngay dưới Banner:
     - **Vốn tham chiếu:** `~150,000 USDT`
     - **Lỗ thả nổi (Unrealised Loss):** `-22.0% vốn` *(Cảnh báo đỏ: Đang gồng lỗ vị thế mở)*
     - **Sụt giảm vốn sâu nhất (Max Drawdown):** `-464,516 USDT`
     - **Tỉ lệ thắng (Win Rate):** `49.3%`
     - **Mẫu dữ liệu:** `225 lệnh đã chốt`

---

### TẦNG 2: BẰNG CHỨNG HIỆU SUẤT THỰC TẾ (Visual Performance Reality)
*Mục tiêu: Đưa biểu đồ vốn lên ngay sau phán quyết để chứng minh bằng hình ảnh trực quan.*

1. **Biểu đồ Vốn tích lũy (Cumulative Capital Curve):**
   - Trục hoành: Thứ tự lệnh đóng (#1 $\to$ #225).
   - Trục tung: Lợi nhuận/Thua lỗ tích lũy (USDT).
   - Điểm nhấn thị giác: Đánh dấu rõ **Đỉnh cao nhất (Peak: +154,804 USDT)** và **Đáy sụt sâu nhất (Trough: -464,516 USDT)**.
   - Thấy ngay hiện tượng: Bot từng có lãi nhưng sau đó sụt giảm không phanh $\to$ Củng cố trực quan cho điểm rủi ro 100.
2. **Cơ cấu Thắng / Thua (Win/Loss Composition):**
   - Đặt song song (Grid 2 cột) với biểu đồ vốn.
   - Hiển thị trực quan tỉ lệ Lãi trung bình vs. Lỗ trung bình (Payoff Ratio).
   - Chỉ ra điểm yếu: *Mặc dù thắng 49% nhưng lệnh thua quá lớn ăn mòn toàn bộ tài khoản*.

---

### TẦNG 3: BÓC TÁCH NGUYÊN NHÂN RỦI RO (Root Cause Diagnostics)
*Mục tiêu: Trả lời câu hỏi "Tại sao bot lại bị chấm rủi ro 100?" một cách gãy gọn, không lặp từ.*

1. **Hợp nhất Nhận định chuyên gia & Lý do cốt lõi:**
   - Xóa bỏ sự tách rời giữa Section 1 và Section 2.
   - Tạo một khối thống nhất gồm:
     - **Core Strategy Thesis:** Tóm tắt phong cách đánh của bot (đánh lướt ETH nhưng không cắt lỗ, gồng vị thế mở lớn).
     - **3 Nguyên nhân kích hoạt Veto:**
       1. Vị thế mở đang chịu lỗ âm tới 22% vốn chưa chốt.
       2. Drawdown thực tế vượt quá mức vốn được ghi nhận.
       3. Stress scenario trong mô phỏng kết thúc bằng việc cháy sạch tài khoản.
2. **Ma trận 10 chiều rủi ro (Risk Dimension Matrix):**
   - **Tối ưu sắp xếp:** Tự động đẩy các chiều có điểm nguy hiểm nhất lên đầu:
     - 🔴 `Tail risk: 100 · CRITICAL` (Rủi ro thiên nga đen / sự kiện đuôi béo)
     - 🔴 `Drawdown risk: 100 · CRITICAL` (Mức độ sụt giảm vốn tàn khốc)
     - 🔴 `Leverage risk: 85 · HIGH`
     - 🟡 `Market alignment: 50 · MODERATE`
     - 🟢 `Liquidity risk: 20 · LOW`
   - Nhờ đó, người dùng nhìn vào là thấy ngay điểm nghẽn của bot mà không phải dò tìm trong 10 thanh bar.
3. **Bằng chứng định lượng (Quantitative Evidence Console):**
   - Giữ định dạng Terminal Monospace ấn tượng hiện tại với các số liệu đo lường cụ thể về độ lệch chuẩn, skewness, kurtosis, chuỗi thua lỗ lớn nhất.

---

### TẦNG 4: THIẾT KẾ LẠI CỤM MONTE CARLO SIMULATION

Hiện tại biểu đồ Monte Carlo bị lỗi số âm cực đoan (-3000%) và thừa biểu đồ cột. Dưới đây là **2 Phương án thiết kế lại**:

#### 💡 PHƯƠNG ÁN A: THAY THẾ TOÀN BỘ BIỂU ĐỒ BẰNG "BẢNG CHỈ SỐ RỦI RO ĐỊNH LƯỢNG" (Text/KPI Matrix - ĐƯỢC KHUYẾN NGHỊ CAO NHẤT)
*Lý do:* Người dùng tài chính khi đọc mô phỏng Monte Carlo chỉ cần 3 câu trả lời:
1. *Xác suất cháy sạch vốn là bao nhiêu?*
2. *Trong kịch bản xấu nhất tôi sẽ mất bao nhiêu tiền?*
3. *Càng chạy dài hạn thì bot này ăn hay lỗ?*

**Cấu trúc hiển thị của Phương án A:**

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 🎲 MÔ PHỎNG MONTE CARLO (10,000 KỊCH BẢN · BOOTSTRAP KHÔNG THAM SỐ)                    │
│ ⚠ Cảnh báo: Mô phỏng chỉ tính trên lệnh đã chốt, CHƯA TÍNH khoản lỗ 22% đang gồng dở   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. CÁC CHỈ SỐ SINH TỒN CỐT TỬ (SURVIVAL METRICS)                                      │
│ ┌──────────────────────────┬──────────────────────────┬──────────────────────────────┐ │
│ │ XÁC SUẤT CHÁY VỐN        │ MỨC SỤT GIẢM TỆ NHẤT     │ XÁC SUẤT CÓ LÃI (TRUNG VỊ)   │ │
│ │ (PROBABILITY OF RUIN)    │ (WORST SIMULATED DD)     │ (MEDIAN PROFIT CHANCE)       │ │
│ │          84.5%           │         -100.0%          │            18.2%             │ │
│ │ 🔴 Cực kỳ nguy hiểm      │ 🔴 Cháy toàn bộ vốn      │ 🔴 Lợi thế âm dài hạn        │ │
│ └──────────────────────────┴──────────────────────────┴──────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. KỊCH BẢN PHÂN VỊ LỢI NHUẬN (PERCENTILE SCENARIOS - ĐÃ CHẶN SÀN PHÁ SẢN)              │
│ • Kịch bản Rất Xấu (P05):   -100.0% (Tài khoản bị thanh lý hoàn toàn)                 │
│ • Kịch bản Xấu (P25):       -100.0% (Tài khoản bị thanh lý hoàn toàn)                 │
│ • Kịch bản Trung vị (P50):  -82.4%  (Tổn thất phần lớn vốn)                            │
│ • Kịch bản Khá (P75):       -34.1%  (Vẫn thua lỗ)                                      │
│ • Kịch bản Tốt nhất (P95):  +12.5%  (Chỉ 5% kịch bản đạt mức lợi nhuận khiêm tốn)      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. MA TRẬN ĐA KỲ HẠN (MULTI-HORIZON ANALYSIS)                                          │
│ Kỳ hạn          Số lệnh     Xác suất Lãi      Xác suất Lỗ     Xác suất Cháy Tài Khoản  │
│ ────────────────────────────────────────────────────────────────────────────────────── │
│ Ngắn hạn (Short)    50 trds     42.1%             57.9%             12.0%              │
│ Trung hạn (Medium) 225 trds     24.5%             75.5%             48.6%              │
│ Dài hạn (Long)     500 trds     18.2%             81.8%             84.5%              │
│                                                                                        │
│ 📌 NHẬN ĐỊNH: PERSISTENT NEGATIVE EDGE (LỢI THẾ ÂM TÍCH LŨY)                           │
│ Càng chạy dài hạn, tỉ lệ cháy tài khoản càng tăng vọt (12% -> 84.5%).                   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

**Ưu điểm vượt trội của Phương án A:**
* **Bỏ hoàn toàn số âm -3000% vô nghĩa:** Mọi phân vị lỗ sâu hơn 100% đều được chuẩn hóa thành `-100.0% (Cháy tài khoản / Ruin)`. Đây là chuẩn mực logic tài chính thực tế.
* **Loại bỏ biểu đồ cột trùng lặp:** Tích hợp trực tiếp dữ liệu Horizon vào bảng ma trận duy nhất, dễ đọc, dễ so sánh.
* **Tải trang siêu nhẹ:** Không tốn tài nguyên render SVG/Canvas, responsive hoàn hảo trên cả điện thoại.

---

#### 💡 PHƯƠNG ÁN B: THIẾT KẾ LẠI BIỂU ĐỒ TRỰC QUAN CHUẨN MỰC (Nếu vẫn muốn giữ Chart)
Nếu vẫn muốn giữ yếu tố đồ họa trực quan, cần khắc phục triệt để các lỗi của biểu đồ cũ như sau:

1. **Thay thế Diverging Bar bằng "Biểu đồ Nón Phân phối Xác suất" (Fan Chart / Box Plot):**
   - Giới hạn trục Y từ `-100%` đến `+50%` (Chặn sàn phá sản tại -100%).
   - Vẽ dải phân vị từ P05 đến P95 dưới dạng các vùng màu (Shaded Confidence Bands):
     - Vùng P05 - P25: Đỏ đậm (Kịch bản thảm họa)
     - Vùng P25 - P75: Vàng / Cam (Dải kỳ vọng phổ biến)
     - Vùng P75 - P95: Xanh lá (Kịch bản thuận lợi nhất)
   - Người dùng nhìn vào sẽ thấy ngay: Dải kỳ vọng nằm trọn vẹn ở phần âm, tiệm cận mức sập sàn -100%.
2. **Xóa hẳn biểu đồ cột "Probability of profit by horizon":**
   - Chỉ giữ lại bảng **Multi-horizon Table** có thanh progress bar mini tích hợp sẵn bên trong cell. Điều này loại bỏ hoàn toàn sự trùng lặp vô ích.
3. **Thêm đồng hồ đo rủi ro cháy vốn (Ruin Risk Gauge):**
   - Một Gauge hình bán nguyệt đo `Probability of Ruin: 84.5%` (Kim chỉ thẳng vào vùng đỏ kịch kim). Trực quan và gây ấn tượng cảnh báo mạnh mẽ gấp nhiều lần các thanh bar dài ngoằng.

---

### TẦNG PHỤ TRỢ: THẨM ĐỊNH HỌC THUẬT & PHƯƠNG PHÁP LUẬN (Methodology Footnote)
*Mục tiêu: Đảm bảo tính minh bạch khoa học nhưng không cản trở trải nghiệm của người dùng phổ thông.*

* Toàn bộ nội dung về:
  - Công thức Stationary Bootstrap (Politis & Romano 1994)
  - Kiểm định Sharpe nâng cao (PSR, DSR - Bailey & López de Prado)
  - Hệ số tương quan Spearman $\rho = 0.64$
  - 10 Ghi chú về dữ liệu mỏng và nạp/rút tiền bất thường
* **Cách bố trí:** Được gom gọn vào một **Accordion đóng/mở ở chân trang** mang tên:
  > `📐 Cơ sở Phương pháp luận Toán học & Thẩm định Định lượng (Nhấn để xem chi tiết ▾)`
* Người dùng thông thường không bị làm phiền, nhưng các kiểm toán viên rủi ro hoặc nhà đầu tư tổ chức vẫn có thể bấm ra xem đầy đủ chứng minh toán học.

---

## IV. BẢNG SO SÁNH TRƯỚC VÀ SAU KHI TỐI ƯU (BEFORE VS AFTER)

| Tiêu chí | Thiết kế Hiện tại | Thiết kế Đề xuất Mới |
| :--- | :--- | :--- |
| **Tốc độ ra quyết định (Time to Insight)** | **Chậm (> 45 giây):** Phải cuộn trang, đọc qua nhiều đoạn văn lý thuyết và lặp từ mới tìm thấy dữ liệu quan trọng. | **Tức thì (< 5 giây):** Thấy ngay Hero Score, Phán quyết Veto đỏ, và 5 chỉ số sống còn ngay tại màn hình đầu tiên. |
| **Bằng chứng trực quan (Visual Proof)** | Biểu đồ vốn nằm sâu tít bên dưới 10 thanh chiều rủi ro. | Biểu đồ vốn & Cơ cấu thắng/thua được đẩy lên Tầng 2, ngay sau phán quyết. |
| **Biểu đồ Monte Carlo** | • Số liệu âm cực đoan khó hiểu (-3193%).<br>• Biểu đồ cột Horizon lặp lại dữ liệu của bảng dưới.<br>• Quá nhiều chữ giải thích dài dòng. | • **Chuẩn hóa sàn cháy vốn tại -100%**.<br>• Thay thế bằng **Bảng chỉ số sinh tồn (Phương án A)** hoặc **Fan Chart chặn sàn (Phương án B)**.<br>• Tinh gọn, trực quan, không trùng lặp. |
| **Phân cấp thông tin (Hierarchy)** | Bị xáo trộn: Đưa lý thuyết học thuật lên trước các thông số rủi ro cụ thể của bot. | Chuẩn mực Kim tự tháp ngược: Phán quyết $\to$ Bằng chứng $\to$ Nguyên nhân $\to$ Dự báo & Học thuật. |
| **Tính hành động (Actionability)** | Chỉ có nhận định chung chung "Investor should not allocate capital". | Có khuyến nghị rõ ràng cho cả 2 tệp: Người định copy và Người đang lỡ copy bot. |

---

## V. LỘ TRÌNH TRIỂN KHAI KỸ THUẬT (TECHNICAL ROADMAP)

Để hiện thực hóa bản thiết kế này trên mã nguồn hiện tại của dự án:

1. **File Backend chính cần sửa:** `Agent/backend/web/report_page.py`
   - Điều chỉnh hàm `_render_tab_report()` để thay đổi trật tự render các section:
     ```python
     # Trật tự mới:
     sections = [
         _render_executive_action_banner(result),   # Tầng 1: Hero + Action + Quick KPI Strip
         _render_growth_section(result),             # Tầng 2: Biểu đồ vốn đưa lên trước!
         _render_unified_diagnostics(result),        # Tầng 3: Gộp Conclusion, Expert & 10 Dimensions
         _render_monte_carlo_redesigned(result),     # Tầng 4: Monte Carlo thiết kế mới (Chuẩn hóa -100%)
         _render_academic_methodology_footer(result) # Tầng phụ trợ: Accordion cuối trang
     ]
     ```
   - Cập nhật engine tính toán Monte Carlo để tự động chặn sàn phân vị tại `-100.0%` (Cap at -100% liquidation threshold) thay vì để tràn số âm `-3000%`.
   - Bỏ hàm `_render_horizon_probability_chart()` (biểu đồ cột 3 horizon thừa).
2. **File Frontend SPA:** `Agent/frontend/src/components/BotDetailView.jsx`
   - Đảm bảo cơ chế Accordion chân trang và các nút neo chuyển hướng (`#tang-truong`, `#monte-carlo`) cuộn mượt mà trong giao diện SPA.
   - Đồng bộ màu sắc và style của Quick Risk Strip với Design System hiện tại.

---
*Bản thiết kế được soạn thảo hoàn tất tại root dự án `Agent/new_design.md` để phục vụ công tác rà soát và triển khai.*
