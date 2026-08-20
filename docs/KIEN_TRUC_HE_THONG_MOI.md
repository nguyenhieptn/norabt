# Kiến trúc hệ thống Backtest mới — `nora/`

> Thiết kế chi tiết. Phạm vi: **chỉ backtest** — sinh chiến thuật → chạy → kết quả → biểu đồ & thống kê.
> Không testnet, không giao dịch thật, không cảnh báo, không quản trị người dùng phức tạp.

| | |
|---|---|
| Phiên bản | 1.0 — 2026-08-19 |
| Nguyên tắc | Giữ nguyên lõi tính toán (5.111 dòng đã kiểm chứng), viết mới toàn bộ phần vỏ |
| Công nghệ | Python 3.11 · FastAPI · PostgreSQL · MongoDB · React + Vite |

---

## 1. Cây thư mục đầy đủ

```
nora/
├── backend/
│   ├── core/                       ⭐ LÕI — mang từ hệ cũ, không viết lại logic
│   │   ├── __init__.py
│   │   ├── engine/                 Máy chạy backtest
│   │   │   ├── account.py          Điều phối 1 lần chạy, vòng lặp thời gian, thanh lý
│   │   │   ├── campaign.py         Máy trạng thái lệnh (11 trạng thái), tính PnL
│   │   │   ├── campaign_1m.py      Khớp lệnh trên khung 1 phút
│   │   │   └── liquidation.py      Kiểm tra cháy tài khoản (tách khỏi account.py)
│   │   ├── strategy/               Chiến lược & diễn giải điều kiện
│   │   │   ├── loader.py           Nạp chiến thuật, gộp container, áp tham số
│   │   │   ├── evaluator.py        compare / and / or — bộ diễn giải điều kiện
│   │   │   ├── element.py          Lấy giá trị: frame · event · calculate · min · max
│   │   │   ├── schema.py           Định nghĩa cấu trúc JSON chiến thuật (pydantic)
│   │   │   └── presets/            4 mẫu chiến lược dựng sẵn
│   │   │       ├── dca.json
│   │   │       ├── trend_following.json
│   │   │       ├── band_trading.json
│   │   │       └── busd_macd.json
│   │   ├── indicator/              Chỉ báo kỹ thuật
│   │   │   ├── basic.py            ema · wma · sma · rma · rsi · atr
│   │   │   ├── keltner.py          kup/klo = ema ± h × atr
│   │   │   ├── macd.py             macd · signal · histogram
│   │   │   └── registry.py         Bảng tra tên cột → hàm tính (dùng cho chart tự tính)
│   │   ├── model/                  Kiểu dữ liệu thuần (dataclass, KHÔNG phụ thuộc DB)
│   │   │   ├── account.py          Cấu hình một lần chạy
│   │   │   ├── campaign.py         Một cặp coin–chiến thuật
│   │   │   ├── trade.py            Một lệnh + bối cảnh vào lệnh
│   │   │   ├── order.py            Một lần khớp (một lệnh có nhiều order khi DCA)
│   │   │   └── enums.py            TradeStatus · Side · ExitReason
│   │   ├── money.py                ⭐ Công thức tiền — tách riêng để kiểm thử độc lập
│   │   └── resource_guard.py       Chặn trần RAM/CPU, gc, tạm nghỉ khi thiếu bộ nhớ
│   │
│   ├── data/                       Truy cập dữ liệu nến (đọc)
│   │   ├── candle_repo.py          Đọc nến + chỉ báo từ MongoDB
│   │   ├── cache.py                Nhớ tạm theo khối ngày, tránh đọc lại
│   │   └── warmup.py               Lấy thêm nến quá khứ cho chỉ báo lookback dài
│   │
│   ├── db/                         Lưu trữ kết quả (ghi)
│   │   ├── session.py              Kết nối PostgreSQL, quản lý phiên
│   │   ├── models.py               Bảng: strategy · run · campaign · trade · order · equity
│   │   ├── repository/             Mỗi bảng một lớp truy cập
│   │   │   ├── strategy_repo.py
│   │   │   ├── run_repo.py
│   │   │   ├── trade_repo.py
│   │   │   └── equity_repo.py
│   │   ├── migrations/             Phiên bản schema (alembic)
│   │   └── seed.py                 Nạp 4 chiến lược mẫu + dữ liệu demo
│   │
│   ├── backtest/                   Điều phối một lần chạy
│   │   ├── runner.py               Gọi core.engine, ghi kết quả qua db.repository
│   │   ├── queue.py                Hàng đợi — tối đa N lần chạy song song
│   │   ├── progress.py             Báo tiến độ (nến đã xử lý / tổng)
│   │   └── validator.py            ⭐ Kiểm tra cấu hình TRƯỚC khi chạy
│   │
│   ├── optimize/                   Sinh & quét tổ hợp tham số
│   │   ├── generator.py            Nở dải tham số: INPUT · SETS · EXPRESSIONS
│   │   ├── worker_pool.py          Đa tiến trình, số worker theo RAM còn trống
│   │   ├── scheduler.py            Chia lô, tiếp tục được khi dừng giữa chừng
│   │   └── ranker.py               Xếp hạng kết quả theo tiêu chí chọn
│   │
│   ├── stats/                      ⭐ Lớp thống kê 6 tầng — giá trị cốt lõi
│   │   ├── overview.py             T1: tổng PnL · winrate · vốn · sụt giảm tối đa
│   │   ├── by_flow.py              T2: phân rã theo nhánh logic ← lộ ra chiến lược
│   │   ├── behavior.py             T3: phân bố phase · kết cục · thời gian giữ · tỷ lệ lãi/lỗ
│   │   ├── context.py              T4: giá trị chỉ báo lúc vào lệnh, thắng vs thua
│   │   ├── timeline.py             T5: theo tháng · theo coin · theo giờ
│   │   ├── compare.py              T6: nhiều lần chạy · backtest vs lịch sử thật
│   │   └── insight.py              Sinh nhận xét tự động ("nhánh LONG đang lỗ, cân nhắc tắt")
│   │
│   ├── chart/                      Sinh biểu đồ
│   │   ├── builder.py              Dựng khung biểu đồ nhiều tầng
│   │   ├── overlay.py              Đường phủ lên giá: ema · wma · keltner
│   │   ├── panel.py                Khung riêng: atr · rsi · macd
│   │   ├── markers.py              Điểm vào/thoát lệnh kèm nhãn kết cục
│   │   └── presets.py              Bộ chỉ báo theo loại chiến lược
│   │
│   ├── api/                        Tầng HTTP
│   │   ├── main.py                 Khởi tạo FastAPI, CORS, xử lý lỗi
│   │   ├── deps.py                 Phụ thuộc dùng chung (phiên DB, phân trang)
│   │   ├── routes/
│   │   │   ├── strategy.py         CRUD chiến thuật, kiểm tra cú pháp
│   │   │   ├── run.py              Tạo/chạy/dừng backtest, xem tiến độ
│   │   │   ├── result.py           6 tầng thống kê, danh sách lệnh
│   │   │   ├── chart.py            Sinh biểu đồ theo yêu cầu
│   │   │   ├── optimize.py         Tạo/chạy/xếp hạng tối ưu
│   │   │   └── data.py             Coin có sẵn, khoảng thời gian, cột chỉ báo
│   │   └── schema/                 Kiểu vào/ra (pydantic)
│   │
│   ├── config.py                   Cấu hình một chỗ: DB, giới hạn tài nguyên, đường dẫn
│   ├── cli.py                      Chạy bằng dòng lệnh (không cần UI)
│   ├── tests/
│   │   ├── test_money.py           ⭐ Kiểm thử công thức tiền
│   │   ├── test_evaluator.py       Kiểm thử bộ diễn giải điều kiện
│   │   ├── test_indicator.py       So chỉ báo với giá trị dựng sẵn
│   │   ├── test_engine.py          Chạy chiến thuật mẫu, so kết quả kỳ vọng
│   │   └── test_parity.py          ⭐ So kết quả với hệ cũ — cột mốc quyết định
│   ├── pyproject.toml
│   └── README.md
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Strategies.tsx      Danh sách + soạn chiến thuật
│   │   │   ├── StrategyEditor.tsx  Soạn điều kiện trực quan, xem trước JSON
│   │   │   ├── Runs.tsx            Danh sách lần chạy, trạng thái, tiến độ
│   │   │   ├── RunDetail.tsx       ⭐ 6 tầng thống kê của một lần chạy
│   │   │   ├── Chart.tsx           Biểu đồ nến + chỉ báo + điểm vào lệnh
│   │   │   ├── Optimize.tsx        Khai dải tham số, theo dõi tiến độ
│   │   │   ├── OptimizeResult.tsx  Bảng xếp hạng tổ hợp
│   │   │   └── Compare.tsx         So sánh nhiều lần chạy
│   │   ├── components/
│   │   │   ├── stats/              Thẻ số liệu · bảng phân rã · dải cảnh báo
│   │   │   ├── chart/              Bọc thư viện biểu đồ
│   │   │   ├── strategy/           Bộ soạn điều kiện, chọn chỉ báo
│   │   │   └── ui/                 Nút · bảng · hộp thoại · form
│   │   ├── api/                    Lớp gọi API (sinh kiểu từ OpenAPI)
│   │   ├── hooks/
│   │   ├── types/
│   │   └── App.tsx
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
│
├── data/                           Dữ liệu vận hành (không đưa vào git)
│   ├── mongo/                      Nến + chỉ báo
│   ├── postgres/                   Kết quả backtest
│   ├── charts/                     HTML biểu đồ đã sinh
│   ├── exports/                    CSV xuất ra
│   └── logs/
│
├── scripts/
│   ├── setup.sh                    Dựng môi trường lần đầu
│   ├── migrate_data.py             Chuyển chiến thuật + kết quả từ hệ cũ
│   ├── crawl_klines.py             Crawl nến Binance (mang từ hệ cũ)
│   ├── build_dataset.py            Tính chỉ báo, dựng dataset backtest
│   └── verify_parity.py            ⭐ So từng lệnh giữa hệ mới và hệ cũ
│
├── docker-compose.yml              Postgres + Mongo, có giới hạn tài nguyên
├── .env.example
└── README.md
```

---

## 2. Mô tả từng module

### 2.1 `core/` — Lõi tính toán ⭐

Nguyên tắc: **thuần Python, không biết gì về database, không biết gì về HTTP.**
Nhận dữ liệu vào bằng dataclass, trả kết quả ra bằng dataclass. Nhờ vậy kiểm thử được độc lập.

#### `core/engine/account.py`
Điều phối một lần chạy backtest.

| Trách nhiệm | Chi tiết |
|---|---|
| Nạp cấu hình | Danh sách campaign, khoảng thời gian, vốn, đòn bẩy |
| Vòng lặp thời gian | Duyệt từng khối ngày → từng nến → từng campaign |
| Gọi campaign | Mỗi nến gọi `campaign.run()` cho từng cặp coin |
| Kiểm tra thanh lý | Sau mỗi nến, tính tổng lỗ chưa thực hiện |
| Ghi kết quả | Gọi callback do `backtest/runner.py` truyền vào |

*Nguồn: `Lab_v1/AccountImp.py` (1.417 dòng) — bỏ phần Telegram, phần ghi MySQL trực tiếp.*

#### `core/engine/campaign.py`
Máy trạng thái của một lệnh. **Đây là phần phức tạp nhất.**

```
ENTER_WAITTING → PENDING → MATCHED ─┬→ TAKEPROFIT
                                    ├→ STOPLOSS
                    MATCHED_PART ───┤
                    PHASE_PENDING ──┤   (DCA vào thêm bậc)
                                    └→ CANCLE
```

| Hàm | Việc |
|---|---|
| `check_order()` | Duyệt các nhánh chiến thuật, xét điều kiện, quyết định vào lệnh |
| `monitor_pending()` | Lệnh chờ khớp — theo dõi giá có chạm không |
| `monitor_matched()` | Lệnh đã khớp — theo dõi chốt lãi, cắt lỗ, nhồi bậc DCA |
| `make_order()` | Tính khối lượng, tạo bản ghi lệnh |
| `calculate_match_price()` | Tính giá khớp theo quy tắc trong chiến thuật |

*Nguồn: `Lab_v1/CampaignImp.py` (1.866 dòng) + `CampaignImp1m.py` (829 dòng).*

#### `core/money.py` ⭐
Tách riêng toàn bộ công thức tiền để kiểm thử được bằng con số tay:

```python
def commission(price, qty, fee_pct) -> float
def pnl(side, entry_price, current_price, qty) -> float
def real_pnl(pnl, commission) -> float
def profit_pct_on_budget(real_pnl, budget) -> float
def profit_pct_on_invest(real_pnl, invest) -> float
def weighted_avg_price(orders) -> float      # giá vốn DCA
def is_profit(pnl, commission) -> bool       # quyết định TAKEPROFIT/STOPLOSS
```

> **Vì sao tách**: ở hệ cũ, công thức nằm rải trong `CampaignImp.py`. Tách ra thì
> `test_money.py` kiểm được từng công thức bằng số cụ thể, và khi nghi ngờ kết quả
> chỉ cần soi một file 80 dòng thay vì 1.866 dòng.

#### `core/strategy/evaluator.py`
Bộ diễn giải điều kiện — 3 hàm đệ quy:

```
compare(element, data)      →  so sánh 2 giá trị, 6 toán tử = > < >= <= !=
compare_and(conditions)     →  mảng trong: mọi điều kiện phải đúng
compare_or(conditions)      →  mảng ngoài: một điều kiện đúng là đủ
```

Cấu trúc điều kiện của chiến thuật là mảng lồng: `[[[a,'>',b], [c,'<',d]]]` nghĩa là `(a>b AND c<d)`.

*Nguồn: `Helper/function_v1.py` (327 dòng).*

#### `core/strategy/element.py`
Lấy giá trị cho một vế so sánh. 5 kiểu:

| Kiểu | Ví dụ | Nghĩa |
|---|---|---|
| `frame` | `{"frame":"4h","column":"kup9_1","index":0}` | Lấy cột từ nến |
| `event` | `{"type":"event","column":"profit"}` | Lấy từ lệnh đang mở |
| `calculate` | `{"type":"calculate","number_1":…,"logic":"/","number_2":…}` | Bốn phép tính |
| `min` / `max` | `{"type":"min","numbers":[…]}` | Nhỏ nhất / lớn nhất |
| số / chuỗi | `55`, `"budget"` | Hằng số hoặc biến dựng sẵn |

Hỗ trợ thêm: `percent` (nhân %), `subtract` (trừ cột khác), `symbol` (lấy của coin khác — ví dụ BTC).

### 2.2 `data/` — Đọc nến

| File | Việc |
|---|---|
| `candle_repo.py` | Truy vấn MongoDB, lọc theo symbol + khoảng thời gian, trả DataFrame |
| `cache.py` | Nhớ tạm theo khối ngày — engine duyệt tuần tự nên tỷ lệ trúng cache cao |
| `warmup.py` | Chỉ báo chu kỳ dài (WMA45 trên 4h ≈ 8 ngày) cần nến quá khứ; module này tự tính lượng cần lấy thêm |

### 2.3 `db/` — Lưu kết quả

Dùng PostgreSQL riêng, **không dùng chung với bất kỳ hệ thống nào**.

#### Schema

```sql
-- Chiến thuật
CREATE TABLE strategy (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT,                      -- dca | trend | band | busd | custom
  content JSONB NOT NULL,         -- định nghĩa điều kiện
  params  JSONB,                  -- takeprofit, stoploss, timelife, margin…
  parent_id BIGINT REFERENCES strategy(id),   -- container chứa chiến thuật con
  weight INT, slot INT,           -- vị trí trong container
  note TEXT, created_at TIMESTAMPTZ DEFAULT now()
);

-- Một lần chạy backtest
CREATE TABLE run (
  id BIGSERIAL PRIMARY KEY,
  name TEXT, dataset TEXT,
  start_at TIMESTAMPTZ, end_at TIMESTAMPTZ,      -- khoảng dữ liệu
  balance NUMERIC, margin_type TEXT, leverage NUMERIC,
  status TEXT,                    -- queued | running | done | failed | stopped
  progress INT, total INT,
  started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ,
  -- ⭐ chỉ số tổng hợp, ghi ngay khi chạy xong (hệ cũ tính rồi ném đi)
  summary JSONB,                  -- {pnl, winrate, max_dd, max_invest, avg_hold…}
  config JSONB
);

-- Cặp coin – chiến thuật trong một lần chạy
CREATE TABLE run_campaign (
  id BIGSERIAL PRIMARY KEY,
  run_id BIGINT REFERENCES run(id) ON DELETE CASCADE,
  symbol TEXT, strategy_id BIGINT REFERENCES strategy(id),
  budget NUMERIC, active_budget NUMERIC DEFAULT 100,   -- ⭐ mặc định 100, không cho NULL
  side TEXT, priority INT
);

-- Từng lệnh
CREATE TABLE trade (
  id BIGSERIAL PRIMARY KEY,
  run_id BIGINT REFERENCES run(id) ON DELETE CASCADE,
  campaign_id BIGINT REFERENCES run_campaign(id),
  symbol TEXT, flow TEXT,         -- ⭐ nhánh logic — chìa khoá thống kê tầng 2
  side TEXT, phase INT,           -- bậc DCA
  enter_time TIMESTAMPTZ, enter_price NUMERIC,
  matched_time TIMESTAMPTZ, matched_price NUMERIC, matched_qty NUMERIC,
  exit_time TIMESTAMPTZ, exit_price NUMERIC,
  budget NUMERIC, invest NUMERIC, margin NUMERIC,
  pnl NUMERIC, commission NUMERIC, real_pnl NUMERIC,
  profit_pct NUMERIC, hold_seconds INT,
  status TEXT, exit_reason TEXT,
  entry_context JSONB,            -- ⭐ giá trị chỉ báo lúc vào lệnh
  exit_context  JSONB
);
CREATE INDEX ON trade (run_id, symbol);
CREATE INDEX ON trade (run_id, flow);
CREATE INDEX ON trade USING GIN (entry_context);

-- Các lần khớp trong một lệnh (DCA nhiều bậc → nhiều order)
CREATE TABLE trade_order (
  id BIGSERIAL PRIMARY KEY,
  trade_id BIGINT REFERENCES trade(id) ON DELETE CASCADE,
  time TIMESTAMPTZ, side TEXT, price NUMERIC, qty NUMERIC,
  commission NUMERIC, pnl NUMERIC, phase INT
);

-- Đường vốn theo thời gian
CREATE TABLE equity (
  run_id BIGINT REFERENCES run(id) ON DELETE CASCADE,
  time TIMESTAMPTZ,
  balance NUMERIC, margin_balance NUMERIC,
  unrealized NUMERIC, invest NUMERIC
);
CREATE INDEX ON equity (run_id, time);

-- Tối ưu hoá
CREATE TABLE optimization (
  id BIGSERIAL PRIMARY KEY,
  name TEXT, base_run_id BIGINT REFERENCES run(id),
  params JSONB,                   -- dải tham số cần quét
  workers INT, status TEXT,
  total INT, processed INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE optimization_result (
  id BIGSERIAL PRIMARY KEY,
  optimization_id BIGINT REFERENCES optimization(id) ON DELETE CASCADE,
  params JSONB, run_id BIGINT REFERENCES run(id),
  summary JSONB, rank INT
);
```

**Ba điểm khác biệt cốt lõi so với hệ cũ:**

| | Hệ cũ | Hệ mới |
|---|---|---|
| Bối cảnh vào lệnh | Chuỗi 800 ký tự phải phân tích cú pháp | `entry_context` JSONB truy vấn thẳng |
| Chỉ số tổng hợp | Tính xong gửi Telegram rồi mất | `run.summary` ghi vào DB |
| `active_budget` | Cho phép NULL → backtest chết lặng lẽ | `DEFAULT 100`, ràng buộc NOT NULL |

### 2.4 `backtest/` — Điều phối

#### `backtest/validator.py` ⭐
Kiểm tra **trước khi chạy**, chặn mọi lỗi hỏng âm thầm đã gặp:

| Kiểm tra | Lý do |
|---|---|
| `active_budget` có giá trị > 0 | Hệ cũ NULL → khối lượng 0 → dừng sau 26 giây |
| Chiến thuật parse được, mọi cột tồn tại trong dataset | Tránh chạy 3 tiếng rồi phát hiện thiếu cột |
| Khoảng thời gian có dữ liệu cho mọi coin | Tránh coin trống làm lệch kết quả |
| Vốn ÷ số campaign đủ đặt lệnh tối thiểu | Tránh khối lượng làm tròn về 0 |
| RAM còn trống ≥ 2,5 GB × số lần chạy | Tránh tràn bộ nhớ |

Trả về danh sách cảnh báo, chặn chạy nếu có lỗi nghiêm trọng.

#### `backtest/queue.py`
Hàng đợi giới hạn số lần chạy song song. Mặc định **4** (đo thực tế: mỗi lần chạy ~2,25 GB RAM,
server còn ~13,5 GB). Mỗi tiến trình được gán dải CPU riêng để không giành nhau.

### 2.5 `optimize/` — Đa luồng

Mô hình lấy từ hệ cũ (`multiprocessing.Process` + `Manager` + `Lock`), cải tiến:

| Thành phần | Việc |
|---|---|
| `generator.py` | Nở dải tham số. 3 kiểu: **INPUT** (danh sách giá trị), **SETS** (bộ đi kèm), **EXPRESSIONS** (công thức từ tham số khác) |
| `worker_pool.py` | Số worker = min(người dùng chọn, RAM cho phép, số CPU−2). Bộ nhớ nến dùng chung qua `Manager` |
| `scheduler.py` | Chia lô, ghi tổ hợp đã xong → **dừng giữa chừng chạy lại được** |
| `ranker.py` | Xếp hạng theo tiêu chí chọn: PnL · winrate · PnL/sụt-giảm · tỷ lệ lãi-lỗ |

### 2.6 `stats/` — Thống kê 6 tầng ⭐

Đây là phần **quyết định hệ thống mới có giá trị hơn hệ cũ hay không**.

| Module | Tầng | Trả lời câu hỏi |
|---|---|---|
| `overview.py` | 1 | Lãi hay lỗ? Bao nhiêu? |
| `by_flow.py` | 2 | **Bộ phận nào của chiến lược tạo ra tiền?** |
| `behavior.py` | 3 | Chiến lược cư xử thế nào? (bậc DCA, kết cục, thời gian giữ) |
| `context.py` | 4 | **Chiến lược phản ứng với điều kiện thị trường nào?** |
| `timeline.py` | 5 | Hợp thị trường nào? Coin nào? Giờ nào? |
| `compare.py` | 6 | Hơn kém lần chạy trước / so với thật? |

Ví dụ tầng 2 — thứ hệ cũ không có:

```sql
SELECT flow, COUNT(*) AS so_lenh,
       ROUND(AVG(hold_seconds)/3600, 1) AS gio_giu_tb,
       ROUND(SUM(real_pnl), 2) AS pnl,
       ROUND(100.0 * SUM((real_pnl > 0)::int) / COUNT(*), 1) AS winrate
FROM trade WHERE run_id = $1 GROUP BY flow ORDER BY pnl DESC;
```

Trên dữ liệu thật cho ra: `SHORT-4h +51.307` / `LONG-4h −32.455` — nhìn phát biết ngay
nhánh LONG đang đốt tiền.

`insight.py` sinh nhận xét tự động từ các tầng trên:
- *"Nhánh LONG-4h lỗ 32.455 trên 4.797 lệnh — cân nhắc tắt nhánh này"*
- *"Chiến thuật khai báo DCA nhưng bậc sâu nhất = 0, điều kiện nhồi lệnh chưa từng chạm"*
- *"73% lệnh đóng do lãi không đủ bù phí, không phải do chạm ngưỡng cắt lỗ"*

### 2.7 `chart/` — Biểu đồ

| File | Việc |
|---|---|
| `builder.py` | Dựng khung nhiều tầng: giá ở trên, các chỉ báo khác đơn vị ở dưới |
| `overlay.py` | Đường phủ lên giá — cùng đơn vị: `price_ema*`, `price_wma*`, `kup*`, `klo*` |
| `panel.py` | Khung riêng — khác đơn vị: `atr`, `rsi`, `macd` |
| `markers.py` | Tam giác đỏ = vào lệnh (nhãn `Long:TP`), vuông xanh = khớp lệnh |
| `presets.py` | Bộ dựng sẵn theo loại: `dca` · `macross` · `keltner` · `all` |

Chỉ báo không có trong dataset thì **tự tính** qua `core/indicator/registry.py`
(WMA/EMA/SMA từ `close` hoặc `rsi`), tự nới cửa sổ dữ liệu theo chu kỳ lớn nhất.

### 2.8 `api/` — Tầng HTTP

| Nhóm | Điểm cuối chính |
|---|---|
| Chiến thuật | `GET/POST/PUT /strategies` · `POST /strategies/validate` · `GET /strategies/presets` |
| Chạy | `POST /runs` · `POST /runs/{id}/start` · `POST /runs/{id}/stop` · `GET /runs/{id}/progress` |
| Kết quả | `GET /runs/{id}/stats/{tang}` · `GET /runs/{id}/trades` · `GET /runs/{id}/equity` · `GET /runs/{id}/export` |
| Biểu đồ | `POST /runs/{id}/chart` · `GET /data/columns` |
| Tối ưu | `POST /optimizations` · `GET /optimizations/{id}/results` |

Tự sinh tài liệu OpenAPI → frontend sinh kiểu TypeScript, không viết tay.

### 2.9 `frontend/`

| Trang | Nội dung |
|---|---|
| `Strategies` | Danh sách, lọc theo loại, nhân bản, xoá |
| `StrategyEditor` | Soạn điều kiện trực quan (chọn khung/cột/toán tử), xem trước JSON, kiểm tra cú pháp |
| `Runs` | Danh sách lần chạy, trạng thái, tiến độ, nút chạy/dừng |
| `RunDetail` ⭐ | 6 tầng thống kê xếp theo thẻ, mỗi con số bấm được để xem sâu hơn |
| `Chart` | Chọn coin/ngày/khung/bộ chỉ báo, xem biểu đồ nhúng |
| `Optimize` | Khai dải tham số, chọn số worker, theo dõi tiến độ |
| `OptimizeResult` | Bảng xếp hạng, bấm một dòng để tạo thành chiến thuật |
| `Compare` | Chọn nhiều lần chạy, đặt cạnh nhau, đường vốn chồng nhau |

---

## 3. Luồng dữ liệu

```
① Soạn chiến thuật
   UI StrategyEditor → POST /strategies → strategy_repo → bảng strategy

② Tạo lần chạy
   UI Runs → POST /runs → validator kiểm tra → bảng run (status=queued)

③ Chạy
   queue lấy job → runner
     ├─ strategy/loader nạp chiến thuật (gộp container, áp tham số)
     ├─ data/candle_repo đọc nến theo khối ngày (có cache + warmup)
     ├─ core/engine/account vòng lặp thời gian
     │    └─ core/engine/campaign mỗi nến, mỗi coin
     │         ├─ strategy/evaluator xét điều kiện
     │         ├─ core/money tính khối lượng, phí, PnL
     │         └─ ⭐ ghi entry_context khi vào lệnh
     ├─ ghi trade + trade_order + equity theo lô
     └─ chạy xong → tính summary → cập nhật run

④ Xem kết quả
   UI RunDetail → GET /runs/{id}/stats/* → stats/* truy vấn tổng hợp bằng SQL

⑤ Xem biểu đồ
   UI Chart → POST /runs/{id}/chart → chart/builder → HTML → nhúng vào trang

⑥ Tối ưu
   UI Optimize → POST /optimizations
     → generator nở tổ hợp → scheduler chia lô
     → worker_pool chạy song song (mỗi worker một run)
     → ranker xếp hạng → bảng optimization_result
```

---

## 4. Ánh xạ từ hệ cũ sang hệ mới

| Hệ cũ | Dòng | Hệ mới | Cách xử lý |
|---|---:|---|---|
| `Lab_v1/AccountImp.py` | 1.417 | `core/engine/account.py` + `liquidation.py` | Giữ logic, bỏ Telegram và ghi MySQL trực tiếp |
| `Lab_v1/CampaignImp.py` | 1.866 | `core/engine/campaign.py` + `core/money.py` | Tách công thức tiền ra file riêng |
| `Lab_v1/CampaignImp1m.py` | 829 | `core/engine/campaign_1m.py` | Giữ nguyên |
| `Helper/function_v1.py` | 327 | `core/strategy/evaluator.py` + `element.py` | Tách phần so sánh và phần lấy giá trị |
| `Lab/function.py` | 420 | `core/strategy/loader.py` | Bỏ phần truy vấn Django |
| `Lab/Optimization.py` | 252 | `optimize/*` | Tách generator · pool · scheduler · ranker |
| `helper/Indicator.py` | — | `core/indicator/*` | Giữ nguyên công thức |
| `backtest_chart.py` | 1.364 | `chart/*` | Tách builder · overlay · panel · markers |
| `ResourceGuard.py` | — | `core/resource_guard.py` | Giữ nguyên |
| 8 lớp `*Wrapper` | — | `db/repository/*` | **Viết lại** — chỗ thay đổi lớn nhất |
| Portal PHP/Laravel | 69.133 | — | **Bỏ** |
| UI React cũ | 186.175 | `frontend/` | **Viết lại** |

**Tổng ước lượng**: giữ ~5.100 dòng lõi, viết mới ~3.000 dòng backend + ~4.000 dòng frontend.

---

## 5. Công nghệ và lý do

| Hạng mục | Chọn | Lý do |
|---|---|---|
| Ngôn ngữ backend | Python 3.11 | Cùng ngôn ngữ với lõi — gọi trực tiếp, bỏ được Redis + socket + node |
| Web framework | FastAPI | Tự sinh OpenAPI, kiểu dữ liệu chặt, async cho tiến độ |
| DB kết quả | PostgreSQL 16 | JSONB + GIN index cho `entry_context`; window function cho thống kê |
| DB nến | MongoDB | Đã có 79,43 triệu nến, không lý do gì chuyển |
| Đa tiến trình | `multiprocessing` | Engine nặng CPU, GIL cản luồng; mô hình này hệ cũ đã dùng tốt |
| Frontend | React 18 + Vite + TypeScript | Vite build nhanh, nhẹ hơn CRA nhiều (hệ cũ build mất vài phút) |
| Biểu đồ | Plotly hoặc Lightweight Charts | Plotly đã dùng và chạy tốt; Lightweight nhẹ hơn nếu cần realtime |
| Triển khai | Docker Compose | Postgres + Mongo có giới hạn tài nguyên rõ ràng |

---

## 6. Ràng buộc tài nguyên áp vào kiến trúc

| Ràng buộc | Thể hiện trong kiến trúc |
|---|---|
| ≤ 12 cores, ≤ 14 GB RAM | `queue.py` giới hạn 4 lần chạy song song; mỗi tiến trình ghim dải CPU riêng |
| Server còn ~13,5 GB | `resource_guard.py` chặn chạy khi RAM khả dụng < 2,5 GB/job |
| Mỗi backtest ~2,25 GB | `cache.py` nhớ tạm theo khối ngày rồi giải phóng, không giữ toàn bộ nến |
| Engine gần như đơn luồng | Không cố song song hoá bên trong một lần chạy; song song ở mức nhiều lần chạy |
| Sinh biểu đồ tốn CPU | Xếp hàng, tối đa 1 biểu đồ cùng lúc, ghim `nice` thấp |

---

## 7. Kiểm thử — cột mốc quyết định

### `tests/test_parity.py` ⭐

Đây là bài kiểm tra **quyết định toàn bộ dự án**:

1. Lấy một account đã chạy ở hệ cũ (ví dụ 3379 — 9.601 lệnh)
2. Chạy đúng chiến thuật đó, đúng khoảng thời gian, đúng dataset trên hệ mới
3. So **từng lệnh**: thời gian vào, giá khớp, khối lượng, PnL, kết cục

**Tiêu chuẩn đạt**: sai lệch PnL tổng < 0,01%, số lệnh trùng khớp 100%.

Chưa đạt bài này thì **không được đụng vào hệ cũ**, không được coi hệ mới là nguồn sự thật.

### Các bài kiểm thử khác

| Bài | Kiểm gì |
|---|---|
| `test_money.py` | Từng công thức tiền bằng số tính tay |
| `test_evaluator.py` | Điều kiện AND/OR lồng nhau, đủ 6 toán tử |
| `test_indicator.py` | So EMA/WMA/RSI/ATR/Keltner với giá trị dựng sẵn |
| `test_engine.py` | Chạy 4 chiến lược mẫu, so kết quả kỳ vọng |

---

## 8. Lộ trình

| GĐ | Nội dung | Xong khi |
|---|---|---|
| **G1** | `core/` chạy độc lập + `test_parity` | Kết quả trùng khớp hệ cũ 100% |
| **G2** | `db/` + `backtest/runner` ghi kèm `entry_context` | Chạy xong có đủ dữ liệu trong Postgres |
| **G3** | `stats/` 6 tầng + `api/` | Trả đủ 6 tầng trong ≤ 3 giây |
| **G4** | `frontend/` luồng chính | Chạy trọn luồng không cần dòng lệnh |
| **G5** | `chart/` + `optimize/` | Vẽ được chỉ báo cả 4 loại; quét tham số đa tiến trình |
| **G6** | `scripts/migrate_data.py` | Chuyển 726 chiến thuật + lịch sử thật sang hệ mới |

**G1 là cột mốc sinh tử.** Mọi thứ sau đó chỉ là xây vỏ quanh một lõi đã được chứng minh.
