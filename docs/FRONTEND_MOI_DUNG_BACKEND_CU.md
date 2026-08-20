# Frontend mới trên backend cũ

> Mục tiêu: viết lại giao diện, dùng API portal hiện có làm nguồn dữ liệu.
> Vừa có UI dùng được ngay, vừa hiểu trọn dữ liệu trước khi làm backend mới.

| | |
|---|---|
| Ngày | 2026-08-19 |
| Backend | Portal Laravel 5.5 hiện tại (`http://103.141.141.24:18088`) |
| Phạm vi | Chỉ luồng backtest: chiến thuật → chạy → kết quả → biểu đồ |

---

## 1. Xác thực — đơn giản hơn tưởng

Portal dùng **JWT**, không phải session. Guard `jwt` đọc token theo thứ tự:

```
1. cookie  'token'
2. query   ?token=...
3. body    { "token": "..." }
```

### Luồng đăng nhập

```
POST /captcha              → { data: { img: "<img src=data:image/png;base64,...>" } }
POST /guest/login/login    → { username, password: base64(mật khẩu), captcha }
                           → { result: true, data: { token: "eyJ0eXAiOiJKV1Qi..." } }
```

Lưu ý:
- Mật khẩu phải **mã hoá base64** trước khi gửi (frontend cũ dùng `btoa()`)
- Ảnh captcha trả về dạng thẻ `<img>` base64, không phải URL
- Token JWT chứa sẵn: `authen_id`, `authen_username`, `authen_email`, `authen_group`, `exp`

### Ý nghĩa cho frontend mới

**Không cần** CSRF token, không cần cookie session, không cần proxy cùng gốc.
Chỉ cần lưu JWT (localStorage) rồi gửi kèm mỗi lần gọi. Frontend chạy độc lập ở cổng khác được.

---

## 2. Bản đồ API — đã đo thực tế

### 2.1 Dùng tốt

| Chức năng | Điểm cuối | Thời gian | Dung lượng | Bản ghi |
|---|---|---:|---:|---:|
| Danh sách tài khoản | `POST /admin/lab_account/read` | 174 ms | 2,5 MB | 3.151 |
| Nhãn hiển thị tài khoản | `POST /admin/lab_account/mapping` | 151 ms | 26 KB | 16 khoá |
| Campaign của 1 tài khoản | `POST /admin/lab_campaigns/read` | 117 ms | 17 KB | 25 |
| Danh sách chiến thuật | `POST /admin/lab_strategies/read` | 831 ms | 5,4 MB | 726 |
| Nhãn chiến thuật | `POST /admin/lab_strategies/mapping` | 301 ms | 1 KB | 4 khoá |
| Danh sách tối ưu | `POST /admin/lab_optimization/read` | 214 ms | 778 KB | 526 |
| Chạy backtest | `POST /admin/lab_account/pysimulate1m` | — | — | `{id}` |
| Dừng backtest | `POST /admin/lab_account/kill` | — | — | `{id}` |
| Xem log chạy | `POST /admin/lab_account/getLog` | ~1 s | 8 KB | chuỗi |

### 2.2 Dùng được nhưng **phải cẩn thận**

| Chức năng | Điểm cuối | Vấn đề |
|---|---|---|
| Kết quả từng lệnh | `POST /admin/lab_results/read` | **21,7 MB** cho 1 tài khoản (9.601 lệnh) — quá nặng để tải thẳng |
| Kết quả có phân trang | `POST /admin/lab_results/filter` | Trả gọn 44 KB nhưng **mất 3,1 giây**, và có đọc sang `coin_crawler` |

### 2.3 ❌ Hỏng — không dùng được

| Điểm cuối | Triệu chứng | Nguyên nhân |
|---|---|---|
| `/admin/lab_track_balance/read` | 500 sau 5 giây | Không lọc → cố tải **854.585 bản ghi** → tràn bộ nhớ PHP 512 MB |
| `/admin/lab_opt_result/read` | 500 sau **24 giây** | Không lọc → **102.860 bản ghi** → tràn bộ nhớ |
| `/admin/chart/view` (trang cũ) | Không có dữ liệu | Đọc MySQL `coin_crawler` — database không tồn tại |

> **Bài học quan trọng nhất**: API cũ **không có phân trang mặc định**.
> Gọi `read` mà không truyền bộ lọc là kéo cả bảng về. Frontend mới **bắt buộc**
> luôn truyền điều kiện lọc, không bao giờ gọi trần.

---

## 3. Ba vấn đề phải giải quyết

### 3.1 Dữ liệu quá lớn

| Bảng | Số bản ghi | Nếu tải thẳng |
|---|---:|---|
| `lab_results` (1 tài khoản) | 9.601 | 21,7 MB |
| `lab_track_balance` | 854.585 | Tràn bộ nhớ |
| `lab_opt_result` | 102.860 | Tràn bộ nhớ |
| `lab_account` | 3.151 | 2,5 MB |
| `lab_strategies` | 726 | 5,4 MB |

**Cách xử lý:**

| Trường hợp | Giải pháp |
|---|---|
| Danh sách tài khoản/chiến thuật | Tải một lần khi mở app, nhớ tạm trong bộ nhớ (React Query) |
| Danh sách lệnh | Dùng `filter` có phân trang, **không** dùng `read` |
| Đường vốn | Lấy mẫu thưa — 854 nghìn điểm không cần vẽ hết, lấy ~2.000 điểm là đủ mượt |
| Thống kê tổng hợp | **Không tính ở frontend** — xem mục 3.2 |

### 3.2 Không có API thống kê

Đây là hạn chế lớn nhất. Backend cũ **không có** endpoint trả tổng PnL, winrate, phân rã theo coin/nhánh.

Ba lựa chọn:

| Cách | Ưu | Nhược |
|---|---|---|
| **A. Tính ở frontend** | Không đụng backend | Phải tải 21,7 MB, trình duyệt xử lý 9.601 bản ghi — chậm và tốn RAM |
| **B. Thêm 1 endpoint vào portal cũ** | Nhanh (≈80 dòng PHP), tính bằng SQL | Phải sửa hệ cũ |
| **C. Dịch vụ phụ đứng cạnh** | Không sửa hệ cũ, là bước đệm sang backend mới | Thêm một tiến trình phải vận hành |

**Khuyến nghị: C** — dựng một dịch vụ nhỏ (FastAPI, ~200 dòng) chỉ làm thống kê,
đọc thẳng MySQL. Vừa giải quyết ngay, vừa **chính là mầm của `stats/` trong hệ thống mới**.
Khi backend mới hoàn thiện, phần này bê nguyên sang.

### 3.3 Không có biểu đồ dùng được

- `lab_track_balance/read` hỏng → không vẽ được đường vốn
- Chart nến của portal chết vì thiếu database

**Cách xử lý**: gọi `backtest_chart` (Python, đã nâng cấp vẽ được chỉ báo) qua dịch vụ phụ ở mục 3.2,
trả về HTML rồi nhúng vào trang bằng iframe.

---

## 4. Cấu trúc frontend đề xuất

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts            Gọi HTTP, tự gắn JWT, xử lý lỗi tập trung
│   │   ├── auth.ts              Đăng nhập, captcha, lưu/xoá token
│   │   ├── lab.ts               Bọc các endpoint portal cũ
│   │   ├── stats.ts             Gọi dịch vụ thống kê phụ
│   │   └── types.ts             Kiểu dữ liệu suy từ phản hồi thật
│   │
│   ├── pages/
│   │   ├── Login.tsx            Đăng nhập + captcha
│   │   ├── Accounts.tsx         Danh sách lần chạy, nút chạy/dừng, tiến độ
│   │   ├── AccountDetail.tsx    ⭐ Tổng kết + phân rã + danh sách lệnh
│   │   ├── Strategies.tsx       Danh sách chiến thuật, lọc theo nhóm/loại
│   │   ├── StrategyDetail.tsx   Xem cấu trúc điều kiện dạng cây
│   │   ├── Chart.tsx            Chọn coin/ngày/chỉ báo, nhúng biểu đồ
│   │   └── Optimize.tsx         Danh sách tối ưu, tiến độ, xếp hạng
│   │
│   ├── components/
│   │   ├── stats/
│   │   │   ├── SummaryCards.tsx     6 thẻ số liệu chính
│   │   │   ├── FlowBreakdown.tsx    ⭐ Phân rã theo nhánh logic
│   │   │   ├── SymbolTable.tsx      Bảng theo coin, sắp xếp được
│   │   │   ├── BehaviorPanel.tsx    Phân bố phase, kết cục, thời gian giữ
│   │   │   └── InsightBanner.tsx    Cảnh báo tự động
│   │   ├── table/
│   │   │   ├── DataTable.tsx        Bảng chung: lọc, sắp xếp, phân trang
│   │   │   └── VirtualTable.tsx     Bảng ảo hoá cho danh sách dài
│   │   ├── chart/
│   │   │   ├── EquityChart.tsx      Đường vốn (dữ liệu đã lấy mẫu thưa)
│   │   │   └── ChartFrame.tsx       Khung nhúng biểu đồ HTML
│   │   ├── strategy/
│   │   │   ├── ConditionTree.tsx    Hiển thị điều kiện JSON dạng cây dễ đọc
│   │   │   └── StrategyBadge.tsx    Nhãn loại chiến lược
│   │   └── ui/                      Nút, thẻ, hộp thoại, form
│   │
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useAccounts.ts
│   │   ├── useRunStats.ts
│   │   └── usePolling.ts        Hỏi tiến độ định kỳ khi đang chạy
│   │
│   ├── lib/
│   │   ├── format.ts            Định dạng tiền, phần trăm, thời lượng
│   │   ├── downsample.ts        Lấy mẫu thưa cho biểu đồ
│   │   └── strategy-parser.ts   Đọc JSON chiến thuật, nhận diện loại
│   │
│   ├── App.tsx
│   └── main.tsx
├── vite.config.ts
└── package.json
```

---

## 5. Các màn hình và dữ liệu tương ứng

### 5.1 Đăng nhập
`POST /captcha` → hiện ảnh · `POST /guest/login/login` → lưu JWT

### 5.2 Danh sách lần chạy
| Cần | Lấy từ |
|---|---|
| Danh sách tài khoản | `lab_account/read` + lọc theo nhóm |
| Nhãn hiển thị (tên DB, node…) | `lab_account/mapping` |
| Trạng thái đang chạy | `lab_account_running` trong bản ghi |
| Tiến độ | Cột trạng thái dạng `"1,855438"` — phần sau là tổng số nến |
| Nút chạy / dừng | `pysimulate1m` / `kill` |
| Xem log | `getLog`, hỏi lại mỗi 5 giây khi đang chạy |

⚠️ Nút chạy sẽ **giết tiến trình đang chạy** của cùng tài khoản — cần hỏi xác nhận rõ ràng.

### 5.3 Chi tiết một lần chạy ⭐
| Phần | Nguồn dữ liệu |
|---|---|
| 6 thẻ tổng quan | Dịch vụ thống kê phụ (mục 3.2) |
| Phân rã theo nhánh | Dịch vụ thống kê phụ — `GROUP BY flow` |
| Bảng theo coin | Dịch vụ thống kê phụ — `GROUP BY symbol` |
| Hành vi vào/ra | Dịch vụ thống kê phụ — phân bố `phase`, `status`, `interval` |
| Danh sách lệnh | `lab_results/filter` có phân trang |
| Đường vốn | Dịch vụ thống kê phụ (lấy mẫu thưa từ `lab_track_balance`) |
| Biểu đồ nến | Dịch vụ phụ gọi `backtest_chart` → HTML → nhúng iframe |

### 5.4 Chiến thuật
| Cần | Lấy từ |
|---|---|
| Danh sách | `lab_strategies/read` (5,4 MB — tải một lần rồi nhớ tạm) |
| Nhóm | `lab_strategies/getGroup` |
| Nội dung điều kiện | Cột `lab_strategy_content` (JSON) |
| Nhận diện loại | Đọc cột `column` trong JSON: có `kup*` → Band · `price_wma45` → Trend · `BUSD_*` → dòng tiền · còn lại → DCA |
| Hiển thị điều kiện | Dựng cây từ mảng lồng: mảng ngoài là HOẶC, mảng trong là VÀ |

### 5.5 Biểu đồ
Chọn coin (từ danh sách lệnh) · ngày (mặc định ngày nhiều lệnh nhất) · khung (1m/4h) ·
bộ chỉ báo (`dca` · `macross` · `keltner` · `all` · tự chọn) → nhúng HTML.

### 5.6 Tối ưu
`lab_optimization/read` cho danh sách. ⚠️ **Không** gọi `lab_opt_result/read` trần —
phải lọc theo `lab_opt_result_optimization`, nếu không tràn bộ nhớ.

---

## 6. Dịch vụ thống kê phụ (khuyến nghị)

Một tiến trình FastAPI nhỏ, đọc thẳng MySQL, không đụng portal cũ.

```
stats-service/
├── main.py              FastAPI, CORS cho frontend
├── db.py                Kết nối MySQL (chỉ đọc)
├── queries/
│   ├── overview.py      Tổng PnL, winrate, vốn, sụt giảm tối đa
│   ├── by_flow.py       ⭐ GROUP BY flow
│   ├── by_symbol.py     GROUP BY symbol
│   ├── behavior.py      Phân bố phase / status / thời gian giữ
│   ├── equity.py        Đường vốn đã lấy mẫu thưa
│   └── insight.py       Sinh cảnh báo tự động
├── chart.py             Gọi backtest_chart, trả đường dẫn HTML
└── requirements.txt
```

Ước lượng **~200–250 dòng**. Điểm cuối:

```
GET /runs/{id}/overview
GET /runs/{id}/by-flow
GET /runs/{id}/by-symbol
GET /runs/{id}/behavior
GET /runs/{id}/equity?points=2000
GET /runs/{id}/insights
POST /runs/{id}/chart      { symbol, day, frame, indicator }
```

**Giá trị kép**: giải quyết ngay vấn đề thống kê, đồng thời chính là bản nháp của
module `stats/` trong hệ thống mới — sau này bê nguyên sang.

---

## 7. Công nghệ đề xuất

| Hạng mục | Chọn | Lý do |
|---|---|---|
| Khung | React 18 + TypeScript + Vite | Build nhanh, nhẹ; hệ cũ dùng CRA build mất vài phút |
| Gọi dữ liệu | TanStack Query | Nhớ tạm, tự hỏi lại, quản lý trạng thái tải/lỗi |
| Bảng | TanStack Table | Ảo hoá cho danh sách 9.601 lệnh |
| Biểu đồ | Lightweight Charts hoặc uPlot | Nhẹ hơn Highcharts nhiều, đủ cho đường vốn |
| Biểu đồ nến chỉ báo | Nhúng HTML từ `backtest_chart` | Đã có sẵn, không viết lại |
| Giao diện | Tailwind + shadcn/ui | Dựng nhanh, không phụ thuộc theme trả phí như hệ cũ |
| Định tuyến | React Router | — |

**Không dùng lại** PrimeReact + theme Atlantis của hệ cũ: theme trả phí, thiếu file `designer/`,
phải vá bằng repo mã nguồn mở mới compile được.

---

## 8. Lộ trình

| GĐ | Nội dung | Xong khi |
|---|---|---|
| **F1** | Khung app + đăng nhập + gọi API | Đăng nhập được, gọi `lab_account/read` ra danh sách |
| **F2** | Màn hình danh sách lần chạy | Chạy/dừng/xem log được từ giao diện mới |
| **F3** | Dịch vụ thống kê phụ | Trả đủ 4 nhóm thống kê trong ≤ 2 giây |
| **F4** | Màn hình chi tiết ⭐ | Thấy tổng quan + phân rã nhánh + bảng coin |
| **F5** | Danh sách lệnh + đường vốn | Phân trang mượt với 9.601 lệnh |
| **F6** | Biểu đồ chỉ báo | Chọn bộ chỉ báo, xem được cả 4 loại chiến lược |
| **F7** | Chiến thuật + tối ưu | Xem cấu trúc điều kiện dạng cây |

**F3 là chốt chặn**: chưa có dịch vụ thống kê thì F4 không làm được,
mà F4 chính là màn hình có giá trị nhất.

---

## 9. Rủi ro

| Rủi ro | Cách giảm |
|---|---|
| Gọi API trần làm sập portal (tràn bộ nhớ) | Lớp `client.ts` **bắt buộc** có bộ lọc, chặn gọi trần ngay từ code |
| Portal cũ chậm (`filter` 3,1 giây) | Nhớ tạm bằng TanStack Query, hiện khung xương khi tải |
| Bấm nhầm nút chạy làm mất kết quả | Hộp thoại xác nhận ghi rõ "sẽ xoá kết quả cũ" |
| Cấu trúc dữ liệu cũ khó hiểu | Viết `types.ts` từ phản hồi thật, không đoán |
| Phình phạm vi | Chỉ làm luồng backtest, không đụng testnet/exchange |

---

## Phụ lục — Số liệu đo thực tế

| Điểm cuối | Mã | Thời gian | Dung lượng | Bản ghi |
|---|---:|---:|---:|---:|
| `lab_account/read` | 202 | 174 ms | 2.545 KB | 3.151 |
| `lab_account/mapping` | 202 | 151 ms | 26 KB | 16 khoá |
| `lab_campaigns/read` (lọc) | 202 | 117 ms | 17 KB | 25 |
| `lab_strategies/read` | 202 | 831 ms | 5.544 KB | 726 |
| `lab_strategies/mapping` | 202 | 301 ms | 1 KB | 4 khoá |
| `lab_results/read` (lọc) | 202 | 1.281 ms | **21.689 KB** | 9.601 |
| `lab_results/filter` (lọc) | 202 | 3.108 ms | 44 KB | 3 khoá |
| `lab_optimization/read` | 202 | 214 ms | 778 KB | 526 |
| `lab_track_balance/read` | **500** | 5.031 ms | — | tràn bộ nhớ |
| `lab_opt_result/read` | **500** | 24.046 ms | — | tràn bộ nhớ |
