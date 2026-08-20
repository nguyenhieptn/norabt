# Yêu cầu UI — Luồng Chiến thuật → Backtest → Kết quả

> Tài liệu đặc tả theo phương pháp BMAD (Business context → Method → Acceptance → Delivery).
> Mỗi Story có tiêu chí nghiệm thu đo được và ghi chú kỹ thuật bám vào code thật của dự án.

| | |
|---|---|
| **Phiên bản** | 1.0 — 2026-08-19 |
| **Phạm vi** | Cổng Nora Lab (`/lab`, port 18088) và Monitor (port 18001) |
| **Người dùng đích** | Trader định lượng, người quản lý bot, ban lãnh đạo xem báo cáo |
| **Trạng thái hệ thống** | Đã chạy được backtest end-to-end; thiếu tầng trình bày kết quả |

---

## 1. Bối cảnh (Business)

### 1.1 Vấn đề đang gặp

Hệ thống có **150+ trang UI** trải trên 4 cổng, backtest chạy được từ giao diện, dữ liệu lưu đầy đủ
(bảng `lab_results` có **39 cột/lệnh**, `lab_track_balance` có **854.585 điểm** cho một lần chạy).
Nhưng khi backtest kết thúc, **không có màn hình nào trả lời được câu hỏi đầu tiên của người dùng**:

> *"Chạy xong rồi, lãi bao nhiêu? Chiến thuật này tốt hay không?"*

Bằng chứng cụ thể — backtest `account 3379` (25 coin, 3 giờ 29 phút, 9.601 lệnh):

| Số liệu | Giá trị | Lấy được từ đâu |
|---|---|---|
| Tổng PnL | **+18.852 USDT** | ❌ Phải truy vấn SQL thủ công |
| Winrate | **26,3%** | ❌ Phải truy vấn SQL thủ công |
| Coin lãi nhất | SUI +5.485 · ETH +5.130 · XRP +5.078 | ❌ Phải truy vấn SQL thủ công |
| Bậc DCA sâu nhất | **phase 0** (không nhồi lệnh!) | ❌ Phải truy vấn SQL thủ công |

Riêng con số cuối là một **phát hiện quan trọng bị bỏ lỡ**: chiến thuật được kỳ vọng chạy DCA
nhưng thực tế không nhồi bậc nào. Nếu UI hiển thị sẵn, người dùng đã phát hiện ngay ngày đầu.

### 1.2 Bốn loại chiến lược cần phục vụ

UI phải phù hợp với **cả 4 loại**, không chỉ DCA:

| Loại | Số chiến thuật | Chỉ báo cốt lõi | Nhu cầu hiển thị đặc thù |
|---|---|---|---|
| **DCA Long** | 215 | `rsi_wma`, `low`, `matched_price` | Bậc nhồi lệnh (phase), giá vốn trung bình |
| **Trend Following** | 151 | `price_ema9` × `price_wma45` | Hai đường giao cắt trên biểu đồ |
| **Band Trading** | 117 | `atr`, `kup*`, `klo*` (Keltner) | Dải trên/dưới bao quanh giá |
| **BUSD / MACD** | 108 | `BUSD_*_MACDh_p1..p3`, `stable_time` | Dòng tiền stablecoin, histogram |

Tổng 726 bản ghi nhưng chỉ **282 khung logic khác nhau** — phần lớn là biến thể sinh từ Optimization.

### 1.3 Mục tiêu

| Mục tiêu | Đo bằng |
|---|---|
| Xem được kết quả backtest **không cần SQL** | 0 truy vấn thủ công để trả lời 6 câu hỏi cốt lõi |
| Kiểm chứng tín hiệu **bằng mắt** cho cả 4 loại | Vẽ được chỉ báo đặc thù của từng loại lên biểu đồ |
| So sánh nhiều lần chạy | Đặt cạnh nhau ≥ 2 account trong một màn hình |
| Đối chiếu backtest với giao dịch thật 2024 | Nối `lab_results` ↔ `history_results_2024` |

### 1.4 Sáu câu hỏi cốt lõi UI phải trả lời ngay

1. Lần chạy này lãi/lỗ bao nhiêu, winrate bao nhiêu?
2. Coin nào kéo lãi, coin nào kéo lỗ?
3. Vốn có lúc nào suýt cháy không?
4. Chiến thuật có chạy đúng như thiết kế không (bậc DCA, hướng lệnh)?
5. Lệnh vào ra có khớp tín hiệu chỉ báo không?
6. So với lần chạy trước / so với thật thì hơn kém thế nào?

---

## 2. Hiện trạng kỹ thuật (Method)

### 2.1 Luồng hiện tại

```
[Chiến thuật]                [Backtest]                    [Kết quả]
Strategy ─┐                                            ┌─ Lab Result (bảng 39 cột)
          ├─> Campaign ─> Lab Account ─> engine ─┐     ├─ Account Risk (biểu đồ vốn)
Strategy  │   (gắn coin)   (nút Start)   lab_     │     ├─ Bot RUIN (rủi ro cháy)
Group ────┤                              account ─┼────┤
          │                                       │     ├─ Chart (nến + điểm vào lệnh)
Optimization ─> sinh hàng loạt biến thể ──────────┘     └─ Opt Result (xếp hạng tham số)
```

### 2.2 Những gì đã có

| Thành phần | Trạng thái |
|---|---|
| Chạy backtest từ UI | ✅ Hoạt động (Redis → lab_server → node → engine) |
| Bảng kết quả từng lệnh | ✅ `Lab Result` — 39 cột |
| Biểu đồ vốn/rủi ro | ✅ `Account Risk` — Wallet/Margin/Unrealize/Invest |
| Sinh chiến thuật tự động | ✅ `Optimization` — grid-search, có Start/Stop/Resume |
| Chart chỉ báo | ⚠️ Mới có ở **dòng lệnh**, chưa lên UI |
| Lịch sử giao dịch thật 2024 | ✅ Bảng `history_results_2024` (13.357 lệnh) |

### 2.3 Những gì thiếu / hỏng

| Vấn đề | Mức độ | Ghi chú |
|---|---|---|
| Không có màn hình tổng kết | 🔴 Chặn | Nguồn gốc của toàn bộ tài liệu này |
| `ChartView` trong portal **chết** | 🔴 Chặn | Đọc MySQL `coin_crawler` — database không tồn tại |
| Không so sánh được nhiều lần chạy | 🟠 | Mỗi account xem riêng lẻ |
| Chart chỉ báo chỉ chạy bằng lệnh | 🟠 | Đã làm xong backend, thiếu nút bấm |
| Dataset thiếu cột `price_wma*` | 🟡 | Chart tự tính được; engine thì chưa |

### 2.4 Ràng buộc bắt buộc tuân thủ

| Ràng buộc | Chi tiết |
|---|---|
| **Tài nguyên** | Toàn hệ thống ≤ 12 cores / ≤ 14 GB RAM. Server còn ~13,5 GB (dịch vụ khác chiếm 17,5 GB) |
| **DB dùng chung** | MySQL `14.225.16.78` dùng chung với production — chỉ được **thêm bảng mới**, không sửa bảng cũ |
| **Truy vấn nặng** | `lab_results` có **2.873 account**; mọi truy vấn phải lọc theo `lab_result_account` (đã có index) |
| **PHP memory** | Portal giới hạn 512 MB — không trả về toàn bộ bản ghi, phải phân trang hoặc tổng hợp phía SQL |
| **Nạp code** | Sửa `coin_service/api/` hoặc `Console/` xong **phải restart `lab_client`** |

---

## 3. Epic và Story

### Bản đồ epic

| Epic | Tên | Ưu tiên | Story | Ước lượng |
|---|---|---|---|---|
| **E1** | Màn hình tổng kết backtest | P0 | S1.1 – S1.4 | 5 ngày |
| **E2** | Chart chỉ báo trên giao diện | P0 | S2.1 – S2.3 | 4 ngày |
| **E3** | So sánh & đối chiếu | P1 | S3.1 – S3.2 | 3 ngày |
| **E4** | Hoàn thiện luồng sinh chiến thuật | P2 | S4.1 – S4.2 | 3 ngày |

---

## EPIC 1 — Màn hình tổng kết backtest (P0)

> **Mục tiêu**: Chạy xong backtest, bấm một nút là thấy toàn cảnh — không cần SQL, không cần Excel.

### Story S1.1 — API tổng hợp kết quả

**Là** hệ thống, **tôi cần** một API trả về số liệu tổng hợp của một account,
**để** giao diện hiển thị ngay mà không phải tải hàng nghìn bản ghi.

**Tiêu chí nghiệm thu**

- [ ] `POST /admin/lab_account/summary` nhận `{id: <account_id>}`
- [ ] Trả về trong **≤ 3 giây** với account có 10.000 lệnh
- [ ] Cấu trúc trả về:
  ```json
  {
    "tong_quan": { "so_lenh": 9601, "pnl": 18852.15, "winrate": 26.3,
                   "so_coin": 25, "phase_sau_nhat": 0, "thoi_gian_chay": "3h29m" },
    "von":       { "ban_dau": 10000, "cuoi_ky": 28852, "cao_nhat": 80715,
                   "thap_nhat": 6870, "sut_giam_max_pct": 31.3 },
    "lai_lo":    { "lai_tb_khi_thang": 5.95, "lo_tb_khi_thua": -164.18, "ty_le_lai_lo": 0.036 },
    "theo_coin": [ { "symbol": "SUIUSDT", "so_lenh": 363, "pnl": 5484.7, "winrate": 28.1 } ],
    "theo_thang":[ { "thang": "2025-01", "so_lenh": 412, "pnl": 1203.5 } ],
    "canh_bao":  [ "Chien thuat khong nhoi DCA bac nao (phase max = 0)" ]
  }
  ```
- [ ] Toàn bộ tính bằng SQL `GROUP BY`, **không** kéo bản ghi về PHP
- [ ] Account không có kết quả → trả `{"result": true, "data": null}`, không lỗi

**Ghi chú kỹ thuật**

- Controller: `coins/app/Http/Controllers/Admin/Lab_accountController.php`
- Cột PnL đúng là **`lab_result_realpnl`** (không phải `lab_result_pnl` — cột đó không tồn tại)
- Sụt giảm vốn tối đa lấy từ `lab_track_balance` (`lab_track_bl_balance`), lọc theo `lab_track_bl_account`
- Cảnh báo tự sinh khi: `MAX(phase)=0` với chiến thuật DCA · `MAX(invest) > 5×` vốn · winrate < 20%

**Tasks**
1. Viết truy vấn tổng hợp, đo thời gian trên account 3379 (9.601 lệnh)
2. Thêm index nếu cần (`lab_result_account` đã có)
3. Viết hàm sinh cảnh báo
4. Trả JSON, test qua fetch từ trình duyệt đã đăng nhập

---

### Story S1.2 — Giao diện thẻ tổng quan

**Là** người dùng, **tôi cần** thấy ngay 6 con số quan trọng nhất sau khi backtest xong,
**để** biết có đáng đào sâu tiếp hay bỏ đi.

**Tiêu chí nghiệm thu**

- [ ] Nút **"Tổng kết"** xuất hiện trên mỗi hàng ở `Lab Account` (cạnh Log/Trades)
- [ ] Mở ra hộp thoại với hàng thẻ số liệu:
  `Tổng PnL` · `Winrate` · `Số lệnh` · `Số coin` · `Sụt giảm tối đa` · `Bậc DCA sâu nhất`
- [ ] PnL dương hiện màu xanh, âm hiện màu đỏ, kèm dấu `+`/`−` rõ ràng
- [ ] Dải cảnh báo màu hổ phách khi có bất thường (ví dụ *"Chiến thuật không nhồi DCA bậc nào"*)
- [ ] Số liệu căn cột thẳng hàng (`font-variant-numeric: tabular-nums`)
- [ ] Đang tải hiện khung xương, lỗi hiện thông báo kèm nút thử lại

**Ghi chú kỹ thuật**

- Trang: `coins/resources/simulation/pages/admin/Lab_accountView.js`
- Các nút hiện tại là `DIV.button`, không phải thẻ `<button>` — theo đúng quy ước sẵn có
- Dùng component `p-dialog` của PrimeReact như các hộp thoại khác trong trang

---

### Story S1.3 — Bảng phân rã theo coin

**Là** người dùng, **tôi cần** biết coin nào kéo lãi, coin nào kéo lỗ,
**để** quyết định loại bỏ coin xấu khỏi danh mục.

**Tiêu chí nghiệm thu**

- [ ] Bảng trong cùng hộp thoại tổng kết: `Coin · Số lệnh · Winrate · PnL · Lãi TB · Lỗ TB`
- [ ] Mặc định sắp theo PnL giảm dần; bấm tiêu đề để đổi cách sắp
- [ ] Có thanh mức độ trực quan trong ô PnL (dài ngắn theo giá trị)
- [ ] Bấm vào một coin → mở luôn chart của coin đó (nối sang Story S2.2)
- [ ] Bảng cuộn ngang được, không làm vỡ bố cục trang

---

### Story S1.4 — Xuất báo cáo

**Là** người quản lý, **tôi cần** xuất kết quả ra file,
**để** gửi cho ban lãnh đạo mà không cần cấp quyền truy cập hệ thống.

**Tiêu chí nghiệm thu**

- [ ] Nút **"Xuất CSV"** trong hộp thoại tổng kết
- [ ] Xuất 2 file: `tong_hop` (theo coin) và `chi_tiet` (từng lệnh)
- [ ] File mở đúng tiếng Việt trong Excel (mã hoá `utf-8-sig`)
- [ ] Tái sử dụng logic `coin_service/export_excel.py` (đã ghi vào `data/exports/`)

---

## EPIC 2 — Chart chỉ báo trên giao diện (P0)

> **Mục tiêu**: Soi bằng mắt xem lệnh vào có khớp tín hiệu không — cho **cả 4 loại** chiến lược.
> Backend đã xong ở dòng lệnh, epic này đưa lên UI.

### Story S2.1 — API sinh chart theo yêu cầu

**Là** hệ thống, **tôi cần** API nhận tham số chỉ báo và sinh chart,
**để** người dùng chọn được chỉ báo muốn xem mà không cần gõ lệnh.

**Tiêu chí nghiệm thu**

- [ ] `POST /admin/lab_account/genChart` nhận `{id, symbol, day, indicator, frame}`
- [ ] Gọi `manage.py backtest_chart` qua node (giống cơ chế nút Start hiện có)
- [ ] Chạy dưới giới hạn tài nguyên `taskset -c 8-11 nice -n 10`
- [ ] Trả về đường dẫn file HTML trong `frontend/build/plot/`
- [ ] Sinh xong ≤ 60 giây cho một ngày dữ liệu

**Ghi chú kỹ thuật**

- Lệnh đã hỗ trợ sẵn: `--indicator`, `--frame`, `--days`, `--indicator list`
- ⚠️ Có **2 file trùng tên** `backtest_chart.py`; Django nạp bản trong **`Backtest/`**
- Chart tự tính được `price_wma*`, `rsi_wma*`… nếu dataset chưa có, và tự nới cửa sổ dữ liệu

---

### Story S2.2 — Bảng chọn chỉ báo theo loại chiến lược

**Là** người dùng, **tôi cần** chọn nhanh bộ chỉ báo phù hợp với loại chiến lược đang xem,
**để** không phải nhớ tên 252 cột dữ liệu.

**Tiêu chí nghiệm thu**

- [ ] Hộp thoại chọn: **Coin** (danh sách coin có lệnh) · **Ngày** · **Khung** (1m/4h) · **Bộ chỉ báo**
- [ ] Bộ chỉ báo dựng sẵn, đặt tên theo loại chiến lược:
  | Nhãn hiển thị | Preset | Vẽ gì |
  |---|---|---|
  | DCA — RSI & bậc nhồi | `dca` | `price_ema9` + panel `rsi`, `rsi_wma45` |
  | Bám xu hướng — EMA×WMA | `macross` | `price_ema9` × `price_wma45` |
  | Biên độ — Keltner | `keltner9` | `kup9_1`, `klo9_1` + panel `atr` |
  | Tất cả | `all` | Gộp các đường chính |
  | Tự chọn… | (nhập tay) | Ô nhập tên cột, có gợi ý |
- [ ] Chọn "Tự chọn" hiện ô nhập kèm **gợi ý từ 252 cột có sẵn**
- [ ] Ngày mặc định là ngày có nhiều lệnh nhất của coin đó
- [ ] Chart hiện trong khung nhúng ngay trong hộp thoại

---

### Story S2.3 — Đánh dấu điểm vào lệnh trên chart

**Là** người dùng, **tôi cần** thấy rõ lệnh vào ở đâu và kết cục ra sao,
**để** đối chiếu với tín hiệu chỉ báo.

**Tiêu chí nghiệm thu**

- [ ] Điểm vào lệnh: tam giác đỏ, nhãn `Long:TP` / `Short:ST` (TP chốt lãi, ST cắt lỗ, W chờ, C huỷ)
- [ ] Điểm khớp: vuông xanh, nhãn `Buy` / `Sell`
- [ ] Rê chuột hiện: giá, khối lượng, PnL, bậc phase
- [ ] Có thanh trượt thời gian để phóng to đoạn cần xem

> **Trạng thái**: Backend đã hoàn thành và kiểm chứng bằng dữ liệu thật
> (`drawPositionOnChart()` trong `backtest_chart.py`). Story này chỉ còn phần nối vào UI.

---

## EPIC 3 — So sánh & đối chiếu (P1)

### Story S3.1 — So sánh nhiều lần chạy

**Là** trader, **tôi cần** đặt kết quả nhiều lần chạy cạnh nhau,
**để** biết thay đổi tham số có làm tốt lên không.

**Tiêu chí nghiệm thu**

- [ ] Chọn 2–5 account bằng ô đánh dấu ở `Lab Account`, bấm **"So sánh"**
- [ ] Bảng đối chiếu: PnL · Winrate · Số lệnh · Sụt giảm tối đa · Tỷ lệ lãi/lỗ
- [ ] Ô tốt nhất mỗi hàng được làm nổi bật
- [ ] Biểu đồ đường vốn của các lần chạy chồng lên nhau, mỗi lần một màu

---

### Story S3.2 — Đối chiếu backtest với giao dịch thật 2024

**Là** ban lãnh đạo, **tôi cần** biết chiến thuật từng chạy thật nay còn hiệu quả không,
**để** quyết định có bật lại hay không.

**Tiêu chí nghiệm thu**

- [ ] Màn hình đặt cạnh nhau: **Thật 2024** ↔ **Backtest 2025**
- [ ] Nối bằng bảng `history_strategy_map_2024` (id gốc 56–60 ↔ id mới 904–908)
- [ ] Hiển thị: số lệnh · winrate · PnL · tỷ lệ lãi/lỗ của cả hai bên
- [ ] Ghi rõ **khoảng thời gian khác nhau** để tránh so sánh khập khiễng

**Ghi chú kỹ thuật**

- Bảng lịch sử: `history_results_2024` (13.357 lệnh, 57 cột nguyên gốc, chỉ đọc)
- Truy vấn mẫu có sẵn: `data/exports/chien_thuat_cu/TRUY_VAN_MAU.sql`
- Số liệu đối chiếu: thật 2024 tổng **+127 USDT**; backtest 2025 **+18.852 USDT**

---

## EPIC 4 — Hoàn thiện luồng sinh chiến thuật (P2)

### Story S4.1 — Trực quan hoá tiến độ Optimization

**Tiêu chí nghiệm thu**
- [ ] Thanh tiến độ dựa trên `lab_opt_processed` / tổng số tổ hợp
- [ ] Ước tính thời gian còn lại
- [ ] Bảng kết quả tự làm mới, hiện tổ hợp tốt nhất hiện tại

### Story S4.2 — Chuyển kết quả tối ưu thành chiến thuật chạy thật

**Tiêu chí nghiệm thu**
- [ ] Từ `Opt Result`, chọn một dòng → nút **"Tạo chiến thuật"**
- [ ] Tự tạo bản ghi trong `lab_strategies` với tham số của dòng đó
- [ ] Tự đặt nhóm và ghi chú nguồn gốc (từ bản tối ưu nào)
- [ ] ⚠️ Bắt buộc set `lab_campaign_active_budget = 100` khi tạo campaign —
      thiếu trường này backtest **hỏng âm thầm** (đã gặp thực tế)

---

## 4. Thứ tự triển khai (Delivery)

```
Tuần 1  ├── S1.1 API tổng hợp          ← nền tảng, làm trước
        └── S1.2 Thẻ tổng quan          ← có giá trị ngay
Tuần 2  ├── S1.3 Bảng theo coin
        ├── S1.4 Xuất CSV
        └── S2.1 API sinh chart
Tuần 3  ├── S2.2 Bảng chọn chỉ báo      ← mở khoá cả 4 loại chiến lược
        └── S2.3 Nối điểm vào lệnh
Tuần 4  ├── S3.1 So sánh nhiều lần chạy
        └── S3.2 Đối chiếu thật vs backtest
Sau đó  └── E4 khi có nhu cầu chạy Optimization thường xuyên
```

## 5. Rủi ro

| Rủi ro | Ảnh hưởng | Cách xử lý |
|---|---|---|
| Truy vấn tổng hợp chậm trên bảng 2.873 account | Timeout UI | Lọc theo `lab_result_account` (có index), tổng hợp bằng SQL |
| Sinh chart chiếm CPU | Ảnh hưởng backtest đang chạy | Ghim `taskset -c 8-11 nice -n 10`, xếp hàng tối đa 1 chart/lần |
| Sửa nhầm bảng của production | Hỏng hệ thống thật | Chỉ thêm bảng mới, luôn chạy thử trước khi ghi |
| Sửa code không có hiệu lực | Mất thời gian dò | Nhớ restart `lab_client` sau mỗi lần sửa |
| Dataset thiếu cột cho loại chiến lược mới | Chart trống | Chart đã tự tính; muốn **chạy** thì phải process lại dataset |

## 6. Định nghĩa hoàn thành

Một Story được coi là xong khi:

1. Chạy đúng trên **dữ liệu thật** (không phải dữ liệu giả)
2. Kiểm chứng qua trình duyệt thật ở `http://103.141.141.24:18088`
3. Không có lỗi JavaScript, không có phản hồi HTTP ≥ 400
4. Không vượt giới hạn tài nguyên (≤ 12 cores / ≤ 14 GB)
5. Không tác động tới hệ thống production dùng chung
6. Ghi lại thay đổi vào tài liệu dự án

---

## Phụ lục — Số liệu tham chiếu

| Hạng mục | Giá trị thực tế (2026-08-19) |
|---|---|
| Nến đã crawl | 79,43 triệu (94 coin, 2025-01-01 → nay) |
| Dataset backtest | `backtest_data_1m_strategy810` — 25 coin, 252 cột chỉ báo |
| Backtest mẫu | Account 3379 — 9.601 lệnh, +18.852 USDT, 3h29m |
| Kho chiến thuật | 726 bản ghi = 638 có logic + 88 container → **282 logic gốc** |
| Lịch sử thật | 13.357 lệnh (10/03/2024 – 17/12/2024), tổng +127 USDT |
| Sức chứa server | Còn ~13,5 GB RAM → tối đa **4 backtest song song** |
