# Phân tích: Hệ thống Backtest độc lập

> Bước phân tích — chưa triển khai. Mục đích: đánh giá tính khả thi, vạch kiến trúc và
> trả lời câu hỏi trọng tâm của sếp: *"thống kê thế nào để **nhìn thấy được chiến lược**"*.

| | |
|---|---|
| Ngày | 2026-08-19 |
| Yêu cầu | Hệ thống mới, **chỉ có backtest**: sinh chiến thuật → backtest → kết quả → biểu đồ + thống kê bảng |
| Trạng thái | Phân tích, chưa viết code |

---

## 1. Đánh giá hiện trạng

### 1.1 Hệ thống hiện tại nặng cỡ nào

| Thành phần | Số file | Số dòng | Cần cho backtest? |
|---|---:|---:|---|
| UI Admin + Exchange (React) | 731 | 109.498 | ❌ Không |
| UI Lab (React) | 568 | 76.677 | ⚠️ Một phần nhỏ |
| Portal backend (PHP/Laravel 5.5) | 455 | 69.133 | ⚠️ Một phần nhỏ |
| Pipeline dữ liệu (Python) | 336 | 41.325 | ✅ Phần crawl + process |
| Engine backtest (Python) | 127 | 16.802 | ✅ Có |
| **Tổng** | **2.217** | **313.435** | |

**Lõi backtest thực sự chỉ ~9.600 dòng** (`Console/Phoenix/Lab_v1/` + `Lab/`) —
tức **3% tổng khối lượng**. 97% còn lại là giao dịch thật, testnet, cảnh báo, quản trị người dùng,
biểu đồ thị trường… những thứ hệ thống backtest thuần **không cần**.

### 1.2 Gánh nặng của hệ thống cũ

| Vấn đề | Bằng chứng |
|---|---|
| Laravel 5.5 quá cũ | Không chạy được trên PHP 8.4, phải dựng Docker PHP 7.4 riêng |
| DB dùng chung với production | Bật node local làm cron production spam Telegram; mọi thay đổi đều rủi ro |
| Cấu hình rải rác, hỏng âm thầm | `active_budget = NULL` làm backtest dừng sau 26 giây mà không báo lỗi rõ |
| Code trùng lặp | 2 file `backtest_chart.py` trùng tên; 3 file `*View_old*` |
| Phụ thuộc chết | `ChartView` đọc MySQL `coin_crawler` — database không tồn tại |
| Model không khớp schema | `lab_account_server`, `lab_account_group` có trong bảng nhưng thiếu trong model Django |

### 1.3 Tài sản đáng mang sang

| Tài sản | Giá trị | Ghi chú |
|---|---|---|
| **Engine tính toán** | ⭐⭐⭐⭐⭐ | 9.600 dòng đã kiểm chứng qua 13.357 lệnh thật |
| **Dữ liệu nến** | ⭐⭐⭐⭐⭐ | 79,43 triệu nến 1m (2025 → nay), 252 cột chỉ báo |
| **Kho chiến thuật** | ⭐⭐⭐⭐ | 726 bản ghi = 282 logic gốc, 4 loại chiến lược |
| **Lịch sử thật 2024** | ⭐⭐⭐⭐ | 13.357 lệnh để đối chiếu |
| **Bộ sinh biểu đồ** | ⭐⭐⭐ | `backtest_chart.py` — vừa nâng cấp, vẽ được chỉ báo |
| Portal PHP | ⭐ | Nên bỏ |
| UI React cũ | ⭐ | Nên viết lại |

**Kết luận**: nên **xây mới phần vỏ, giữ nguyên phần lõi**. Không viết lại engine —
đó là 9.600 dòng logic tài chính đã được kiểm chứng bằng tiền thật.

---

## 2. Câu hỏi trọng tâm: thống kê thế nào để *nhìn thấy chiến lược*?

Đây là phần quan trọng nhất của tài liệu.

### 2.1 Vì sao bảng PnL thông thường là chưa đủ

Backtest `account 3379` cho kết quả tổng: **+18.852 USDT, winrate 26,3%**.
Nhìn con số này, người dùng không biết được gì ngoài "có lãi".

Nhưng khi tách theo **luồng logic** bên trong chiến thuật:

| Luồng | Số lệnh | Thời gian giữ TB | Winrate | PnL |
|---|---:|---:|---:|---:|
| `SHORT-4h` | 4.804 | 40,2 giờ | 29,6% | **+51.307** |
| `LONG-4h` | 4.797 | 31,3 giờ | 23,0% | **−32.455** |

**Chiến lược này kiếm tiền hoàn toàn từ nhánh SHORT và mất tiền ở nhánh LONG.**
Nếu tắt nhánh LONG, kết quả từ +18.852 thành **+51.307** — gấp 2,7 lần.

Đó chính là "nhìn thấy chiến lược": không chỉ biết *lãi bao nhiêu* mà biết
***bộ phận nào của chiến lược tạo ra tiền, bộ phận nào đốt tiền***.

### 2.2 Dữ liệu đã có sẵn để làm việc đó

Bảng `lab_results` lưu 39 cột mỗi lệnh, trong đó nhóm cột **hé lộ hành vi chiến lược**:

| Cột | Cho biết |
|---|---|
| `lab_result_flow` | **Nhánh logic nào** trong chiến thuật đã kích hoạt |
| `lab_result_phase` | Bậc nhồi lệnh (DCA vào tới bậc mấy) |
| `lab_result_status` | Kết cục: chốt lãi / cắt lỗ / hết hạn / huỷ |
| `lab_result_interval` | Thời gian giữ lệnh (scalping hay swing) |
| `lab_result_start_reason` | **Toàn bộ điều kiện kích hoạt + giá trị thực của từng chỉ báo** |
| `lab_result_btc_wma45_1d/1w` | Bối cảnh thị trường chung lúc vào lệnh |
| `lab_result_matched_ema5` | Giá trị chỉ báo tại thời điểm khớp |
| `lab_result_params` | Tham số áp dụng cho lệnh đó |

**Cột `start_reason` là mỏ vàng.** Ví dụ một bản ghi thật:

```
high(0)[0.002376] > kup17_05(0)[0.0023733]
  AND atr(0)[0.0000676] > 0
  AND kup17_05(0) − klo17_05(0)[0.0000676] > 0
  AND min(close/atr [35.08], close/(kup−klo) [35.08], 80)[35.08] > 0
```

Nó ghi lại **điều kiện nào đúng và giá trị bao nhiêu** tại đúng khoảnh khắc vào lệnh.
Nghĩa là hoàn toàn thống kê được: *"khi chiến lược vào lệnh, ATR trung bình là bao nhiêu?
Giá vượt dải Keltner bao nhiêu phần trăm? Khối lượng tính ra bao nhiêu?"*

**Hạn chế hiện tại**: lưu dạng chuỗi ~800 ký tự, phải phân tích cú pháp mới dùng được.
→ Hệ thống mới nên lưu **có cấu trúc** (JSON) ngay từ đầu.

### 2.3 Khung thống kê 6 tầng đề xuất

Mỗi tầng trả lời một câu hỏi sâu hơn về chiến lược:

#### Tầng 1 — Tổng quan *(chiến lược lãi hay lỗ?)*
`Tổng PnL · Winrate · Số lệnh · Số coin · Vốn cuối kỳ · Sụt giảm tối đa`

#### Tầng 2 — Phân rã theo nhánh logic ⭐ *(bộ phận nào tạo ra tiền?)*
Nhóm theo `flow`: mỗi nhánh LONG/SHORT/DCA-phase có PnL, winrate, thời gian giữ riêng.
**Đây là tầng quan trọng nhất — chính là ví dụ SHORT lãi/LONG lỗ ở trên.**

#### Tầng 3 — Hành vi vào–ra lệnh *(chiến lược cư xử thế nào?)*
| Chỉ số | Ý nghĩa |
|---|---|
| Phân bố bậc `phase` | DCA có thật sự nhồi lệnh không, tới bậc mấy |
| Phân bố `status` | Bao nhiêu % chốt lãi / cắt lỗ / hết hạn |
| Lãi TB khi thắng ÷ Lỗ TB khi thua | Ăn lớn thua nhỏ hay ngược lại |
| Phân bố thời gian giữ lệnh | Lướt sóng hay giữ dài |

Ví dụ thật từ 3379: lãi TB **+250,82** / lỗ TB **−86,93** → tỷ lệ 2,9:1 (ăn lớn thua nhỏ),
nhưng **73% lệnh đóng bằng cắt lỗ** và **bậc DCA sâu nhất = 0** (không nhồi lệnh lần nào).

#### Tầng 4 — Bối cảnh kích hoạt ⭐ *(chiến lược phản ứng với cái gì?)*
Thống kê giá trị chỉ báo tại thời điểm vào lệnh, lấy từ `start_reason`:
- ATR trung bình lúc vào lệnh (biến động cao hay thấp)
- Khoảng cách giá tới dải Keltner
- RSI / trạng thái BTC lúc đó
- **Phân bố các giá trị này giữa lệnh thắng và lệnh thua** → tìm ra ngưỡng lọc tốt hơn

#### Tầng 5 — Theo chiều thời gian và thị trường
- PnL theo tháng → chiến lược hợp thị trường tăng hay giảm
- PnL theo coin → coin nào kéo lãi/lỗ
- PnL theo giờ trong ngày → có phụ thuộc phiên giao dịch không

#### Tầng 6 — So sánh
- Nhiều lần chạy đặt cạnh nhau
- Backtest 2025 ↔ giao dịch thật 2024
- Các biến thể tham số từ Optimization

### 2.4 Nguyên tắc thiết kế rút ra

| Nguyên tắc | Lý do |
|---|---|
| **Lưu bối cảnh có cấu trúc, không phải chuỗi** | `start_reason` hiện phải phân tích cú pháp mới dùng được |
| **Mọi thống kê phải tách được theo `flow`** | Đây là chỗ lộ ra bộ phận nào của chiến lược hiệu quả |
| **Ghi lại chỉ số ngay khi backtest kết thúc** | Engine đã tính 11 chỉ số rồi ném đi (chỉ gửi Telegram) |
| **Mỗi con số phải bấm được để xem chi tiết** | Từ tổng quan → nhánh → lệnh → biểu đồ |
| **Cảnh báo tự động khi chiến lược chạy sai thiết kế** | Ví dụ "DCA nhưng phase max = 0" |

---

## 3. Kiến trúc đề xuất

### 3.1 Nguyên tắc

```
GIỮ NGUYÊN          VIẾT MỚI              BỎ HẲN
─────────────       ─────────────         ─────────────
Engine tính toán    API (FastAPI)         Portal PHP/Laravel
Dữ liệu nến Mongo   UI (React)            Testnet / Exchange
Bộ sinh biểu đồ     DB kết quả riêng      Cảnh báo Telegram
Kho chiến thuật     Lớp thống kê          Quản trị người dùng
```

### 3.2 Sơ đồ

```
┌──────────────────────────────────────────────────────────┐
│  UI mới (React + Vite)                                   │
│  Chiến thuật · Backtest · Kết quả · Biểu đồ · So sánh    │
└───────────────────────┬──────────────────────────────────┘
                        │ REST/JSON
┌───────────────────────┴──────────────────────────────────┐
│  API mới (FastAPI, Python)                               │
│  • Quản lý chiến thuật, chạy backtest, hàng đợi          │
│  • Lớp thống kê 6 tầng ← phần giá trị nhất               │
│  • Sinh biểu đồ theo yêu cầu                             │
└───────────────────────┬──────────────────────────────────┘
                        │ gọi trực tiếp (không qua Redis/socket)
┌───────────────────────┴──────────────────────────────────┐
│  Engine (mang nguyên từ hệ thống cũ, gỡ phụ thuộc Django)│
└───────┬──────────────────────────────┬───────────────────┘
        │                              │
┌───────┴────────┐            ┌────────┴──────────┐
│ MongoDB        │            │ PostgreSQL riêng   │
│ nến + chỉ báo  │            │ chiến thuật, lệnh, │
│ (đã có 79,43M) │            │ thống kê           │
└────────────────┘            └────────────────────┘
```

### 3.3 Vì sao chọn như vậy

| Quyết định | Lý do |
|---|---|
| **FastAPI thay Laravel** | Cùng ngôn ngữ với engine → gọi trực tiếp, bỏ được tầng Redis + socket + node |
| **DB riêng, không dùng chung** | Xoá bỏ toàn bộ rủi ro với production; tự do đổi schema |
| **PostgreSQL thay MySQL** | Truy vấn thống kê phức tạp (window function, CTE) mạnh hơn hẳn |
| **Giữ MongoDB cho nến** | 79,43 triệu nến đã có, không lý do gì chuyển |
| **Bỏ Redis/socket** | Cơ chế node phân tán chỉ cần khi chạy nhiều máy; một máy thì gọi thẳng |
| **React + Vite** | Nhẹ hơn CRA nhiều, phù hợp giới hạn tài nguyên |

### 3.4 Schema kết quả — điểm khác biệt cốt lõi

Bảng lệnh của hệ thống mới bổ sung **cột bối cảnh có cấu trúc**:

```sql
CREATE TABLE trade (
  id, run_id, symbol, flow, phase, side,
  enter_time, enter_price, exit_time, exit_price,
  qty, pnl, pnl_pct, status, hold_seconds,
  -- ĐIỂM MỚI: bối cảnh lúc vào lệnh, dạng JSON truy vấn được
  entry_context JSONB,   -- {"atr":0.000068, "kup17_05":0.00237, "close_vs_kup":1.0011, "rsi":58.3}
  exit_reason   TEXT,
  strategy_id, campaign_id
);
CREATE INDEX ON trade USING GIN (entry_context);
```

Có `entry_context` dạng JSONB thì thống kê Tầng 4 chỉ là một câu truy vấn:

```sql
-- Khi thắng và khi thua, ATR khác nhau thế nào?
SELECT pnl > 0 AS thang,
       ROUND(AVG((entry_context->>'atr')::numeric), 6) AS atr_tb,
       COUNT(*)
FROM trade WHERE run_id = 1 GROUP BY 1;
```

Đây là thứ hệ thống cũ **không làm được** vì bối cảnh lưu dạng chuỗi 800 ký tự.

---

## 4. Đánh giá rủi ro

| Rủi ro | Mức | Cách giảm |
|---|---|---|
| Gỡ engine khỏi Django phức tạp hơn dự tính | 🔴 Cao | Engine có 23 chỗ gọi ORM trên 8 bảng — làm lớp truy cập dữ liệu trung gian, không sửa logic tính toán |
| Kết quả hệ thống mới lệch hệ thống cũ | 🔴 Cao | Chạy song song cùng account, so từng lệnh cho tới khi khớp 100% |
| Tài nguyên server | 🟠 | Chỉ còn ~13,5 GB RAM; hệ mới phải nhẹ hơn hệ cũ, không chạy song song hai hệ lâu dài |
| Mất tính năng chưa nhận ra | 🟠 | Rà từng màn hình Lab hiện tại, lập danh sách trước khi bỏ |
| Phình phạm vi | 🟠 | Ghi rõ **chỉ backtest** — không testnet, không giao dịch thật, không cảnh báo |

### Điểm cần đặc biệt lưu ý

Engine gọi ORM Django ở **23 chỗ**, đụng **8 bảng** (`LabAccount`, `LabCampaigns`, `LabResults`,
`LabOrder`, `LabTrackBalance`, `LabEventLogs`, `LabOptimization`, `LabOptResult`).
Đây là phần khó nhất khi tách. Nhưng logic tính toán tài chính (khớp lệnh, tính PnL, DCA,
thanh lý) **không đụng ORM** — nên tách được mà không phải viết lại phần khó nhất.

---

## 5. Lộ trình đề xuất

| Giai đoạn | Nội dung | Kết quả kiểm chứng |
|---|---|---|
| **G1** | Gỡ engine khỏi Django, chạy độc lập | Chạy 1 backtest cho ra kết quả **giống hệt** hệ cũ |
| **G2** | DB mới + ghi kết quả kèm `entry_context` | Bảng `trade` có bối cảnh JSON truy vấn được |
| **G3** | API + lớp thống kê 6 tầng | Trả đủ 6 tầng trong ≤ 3 giây |
| **G4** | UI: chiến thuật → chạy → kết quả | Chạy trọn luồng không cần dòng lệnh |
| **G5** | Biểu đồ + so sánh nhiều lần chạy | Vẽ được chỉ báo của cả 4 loại chiến lược |
| **G6** | Chuyển dữ liệu cũ + đối chiếu | Kết quả khớp lịch sử thật 2024 |

**Cột mốc quyết định là G1**: nếu engine chạy độc lập cho kết quả trùng khớp hệ cũ,
mọi giai đoạn sau chỉ là xây vỏ. Nếu không tách được, phải xem lại toàn bộ hướng đi.

---

## 6. Kết luận và khuyến nghị

### Nên làm — nhưng theo hướng "thay vỏ, giữ lõi"

**Lý do ủng hộ:**
- Lõi backtest chỉ chiếm 3% code; 97% còn lại là gánh nặng không cần thiết
- Hệ cũ có nhiều điểm hỏng cấu trúc (Laravel 5.5, DB dùng chung, cấu hình hỏng âm thầm)
- Yêu cầu "thống kê nhìn thấy chiến lược" **đòi hỏi thay đổi cách lưu dữ liệu** — vá hệ cũ sẽ chắp vá

**Điều kiện bắt buộc:**
- **Không viết lại engine** — 9.600 dòng logic đã kiểm chứng bằng tiền thật
- **Không chạm vào hệ cũ** cho tới khi hệ mới chứng minh cho kết quả trùng khớp
- **Giữ đúng phạm vi**: chỉ backtest

### Ba việc phải làm đúng ngay từ đầu

1. **Lưu bối cảnh vào lệnh dạng có cấu trúc** — nếu bỏ qua, sau này lại rơi vào đúng vấn đề của `start_reason` hiện tại
2. **Mọi thống kê tách được theo nhánh logic** — đây là chỗ lộ ra bộ phận nào của chiến lược hiệu quả
3. **Ghi lại chỉ số ngay khi backtest xong** — đừng để engine tính rồi ném đi như hiện nay

---

## Phụ lục — Số liệu dùng trong phân tích

| Hạng mục | Giá trị |
|---|---|
| Tổng code hệ thống hiện tại | 313.435 dòng / 2.217 file |
| Lõi backtest | ~9.600 dòng (3%) |
| Engine gọi ORM | 23 chỗ, 8 bảng |
| Dữ liệu nến | 79,43 triệu nến 1m, 252 cột chỉ báo |
| Backtest mẫu (3379) | 9.601 lệnh, +18.852 USDT, WR 26,3%, 3h29m |
| — nhánh SHORT-4h | 4.804 lệnh, +51.307, WR 29,6%, giữ 40,2h |
| — nhánh LONG-4h | 4.797 lệnh, −32.455, WR 23,0%, giữ 31,3h |
| — lãi/lỗ TB mỗi lệnh | +250,82 / −86,93 |
| — kết cục | 73% cắt lỗ, 26% chốt lãi |
| — bậc DCA sâu nhất | 0 (không nhồi lệnh) |
| Kho chiến thuật | 726 bản ghi → 282 logic gốc, 4 loại |
| Lịch sử thật | 13.357 lệnh (2024), +127 USDT |
