# Agent — QC Risk Supervisor

> 📚 **Hệ thống Tài liệu Kỹ thuật Chuẩn BMAD:** Xem toàn diện tại [Agent/docs/readme.md](docs/readme.md) gồm:
> - **BMAD Story:** Quá trình & tiến độ phát triển hệ thống ([bmad/story/](docs/bmad/story/00_overview/STORY-00_SYSTEM_PROGRESSION_AND_STATUS.md))
> - **BMAD Spec:** Mô tả chi tiết bóc tách từng kỹ năng định lượng của hệ thống ([bmad/spec/](docs/bmad/spec/00_overview/SPEC-00_SPECIFICATION_INDEX.md))
> - **OKX AI Track Report:** Báo cáo đặc tả kỹ thuật đạt chuẩn OKX AI ([docs/OKX_AI_REPORT.md](docs/OKX_AI_REPORT.md))

Hệ thống đánh giá rủi ro bot theo kiến trúc đã chốt trong [docs/plan.md](docs/plan.md):

```text
Logic 1: Market observation   -> MarketResult
Logic 2: Bot/MCP analytics    -> BotResult
Logic 3: QC fusion            -> BotRiskAssessment
History                       -> AssessmentHistoryStore (risk trend qua các lần chạy)
Reporting                     -> Bảng xếp hạng cohort + kết luận + backlog dữ liệu
Control policy                -> ControlDecision (READ_ONLY)
```

## Cấu trúc dự án

```text
Agent/
├── backend/      mã nguồn: sources → market/mcp → qc → web + mcp server
├── frontend/     SPA (React/Vite) · dist/ là bản build app.py phục vụ
│                 · tokens.css là NGUỒN DUY NHẤT của bảng màu, cả hai phía đọc
├── docs/         tài liệu kỹ thuật + hồ sơ BMAD
│   └── bmad/
│       ├── spec/    mô tả chi tiết từng tính năng (ý tưởng → phạm vi → kỹ năng)
│       └── story/   tiến trình thiết kế/build/hoàn thiện theo từng giai đoạn
├── data/         dữ liệu đã crawl + kết quả chấm điểm (bước 1 → 2 → 3)
├── docker/       Dockerfile, docker-compose.yml, script vận hành
├── nginx/        template vhost + script cài đặt
├── none/         test/ và scripts/ — giữ lại nhưng không thuộc luồng chạy chính
├── .env          cấu hình thật (không vào git; xem .env.example)
└── readme.md
```

Tên project Docker khoá cứng là `norabt-agent` trong `docker/docker-compose.yml`
— không khoá thì Compose lấy tên thư mục làm tên project và mọi lần đổi chỗ
file sẽ đẻ ra một bộ container trùng tên.

## Chế độ vận hành: SNAPSHOT

Hệ thống không cần realtime. Dữ liệu crawl là chế độ chính thức:

- Freshness chấm theo **mốc dữ liệu của chính dataset** (anchor = observation mới nhất), không theo đồng hồ thực.
- Mỗi nguồn có ngân sách stale riêng ([quality.py](backend/infra/quality.py)): nến 1h khác order book, khác funding.
- Tuổi so với đồng hồ thực vẫn được ghi lại, nên một dataset cũ không bao giờ bị trình bày như dữ liệu live.

Ví dụ thực tế trong dataset: nến BTC coherent với anchor, nhưng `orderbook_l2` lệch ~550 ngày so với nến → vẫn bị đánh `STALE` và làm giảm confidence của lens thanh khoản.

## Lỗ hoãn nhận: chỉ số đóng lệnh không phải toàn bộ sự thật

Mọi chỉ số hiệu suất — win rate, profit factor, expectancy, MaxDD, và cả Monte Carlo — đều
tính **chỉ từ sổ lệnh đã đóng**. Một bot chỉ chốt lệnh thắng và ôm lệnh thua sẽ trông hoàn hảo.

[deferred_loss.py](backend/mcp/analytics/performance/deferred_loss.py) không đo bằng ngưỡng
tỉ lệ mà **đánh dấu sổ mở theo giá thị trường rồi tính lại chính các chỉ số đó**. Câu hỏi trở
thành một phép tính: *PF sẽ ra bao nhiêu nếu chốt hết lỗ đang mở?*

```text
HaveARestin      PF 11.09 → 0.16    SUSTAINABLE → LOSING
Bare-Payee-Fox   PF    —  → 1.03    SUSTAINABLE → FRAGILE
稳稳赚钱           PF    —  → 0.12    SUSTAINABLE → LOSING
```

### Vì sao không dùng tỉ lệ

Hai cách đo sai đã bị loại bỏ, cả hai đều tạo báo động giả:

**Chia cho lãi ròng.** Lãi ròng tiến về 0 khi thắng và thua gần bù nhau, nên tỉ lệ nổ tung vì
lý do không liên quan tới rủi ro. `goupenguin2` có lãi gộp 1,568 và lỗ gộp 969 → ròng chỉ 600,
đẩy tỉ lệ lên 3.8x trong khi PF chỉ đổi từ 1.62 xuống 1.40.

**So mức giảm tương đối.** "PF giảm hơn một nửa" bắt nhầm `RuiJie` (41.52 → 9.99) và `BestMax`
(4.73 → 2.08) — giảm mạnh về số nhưng kết luận không đổi, cả hai vẫn rất lời.

Cái đúng cần so là **kết luận có đổi hạng không**, dùng chính các ngưỡng mà lens hiệu suất
đang dùng: `LOSING < 1.0 ≤ FRAGILE < 1.3 ≤ SUSTAINABLE`. Bot chưa từng chốt lỗ được xếp
`SUSTAINABLE` vì hồ sơ của nó đọc lên là hoàn hảo.

| Trạng thái | Điều kiện |
|---|---|
| `NO_CLOSED_TRADES` | Chưa có lệnh đóng → không có chỉ số để bóp méo |
| `REPRESENTATIVE` | Không vị thế mở, lỗ mở dưới 1% vốn, hoặc hạng giữ nguyên |
| `PARTIAL` | Hạng giữ nguyên nhưng lỗ mở ≥ 10% vốn, hoặc chưa từng chốt lỗ |
| `UNREPRESENTATIVE` | Chốt hết thì **tụt hạng** |

### Hệ quả trong lõi

- **Lens hiệu suất** ngừng chấm theo PF/expectancy khi `UNREPRESENTATIVE`, cộng điểm theo tỷ
  lệ lỗ mở trên vốn, và đẩy PF/win-rate xuống mục "chỉ để tham khảo".
- **Monte Carlo** bị đánh `deferred_loss_bias`: phân phối lấy mẫu từ lệnh đã đóng nên thiếu
  đúng những khoản lỗ chưa ghi nhận. Tail risk hạ độ tin cậy 40% và nâng sàn điểm.
- **Veto**: tụt hạng xuống dưới hoà vốn, hoặc lỗ mở ≥ 15% vốn, thì sàn điểm rủi ro là 70.

Bảng báo cáo có cột `LỖ-MỞ`, dấu `!` chỉ xuất hiện khi kết luận thật sự đổi hạng.

## Nền vốn: một cơ sở duy nhất cho cả lịch sử và tương lai

Đây là chỗ dễ tạo ra số vô nghĩa nhất, nên được xử lý tập trung tại
[capital/equity_curve.py](backend/mcp/capital/equity_curve.py).

Weekly PnL của OKX cho cả `pnl` lẫn `pnlRatio`, nên `pnl / pnlRatio` dựng được **equity của từng tuần** — tức là cả một đường cong, không phải một con số.

- Giữ **toàn bộ** các tuần, kể cả tuần lỗ. Bỏ tuần lỗ sẽ làm đường cong chỉ đi lên và drawdown biến mất.
- Bỏ qua tuần có `|pnlRatio| < 0.01`: ratio được làm tròn 4 chữ số nên dưới ngưỡng này sai số vượt 0.5%. Mỗi điểm bị bỏ đều ghi lý do.
- Sụt vốn lịch sử tính theo **equity tại đúng thời điểm** của từng lệnh (`equity_at(close_time)`), không dùng một mẫu số chung cho cả lịch sử.
- Mô phỏng tương lai dùng **equity mới nhất** của chính đường cong đó.
- Không có đường cong → `CURRENT_AUM`: mô phỏng chạy trên AUM, còn drawdown phần trăm **bị giữ lại** thay vì bịa mẫu số.

Hệ quả: lịch sử và tương lai luôn cùng một `capital_basis`. Không còn cảnh MaxDD 100% đứng cạnh P(cháy) 0.2%.

Hai thứ được ghi rõ thay vì làm mượt đi:

- **Dòng tiền gộp** (nạp/rút). Dùng net sẽ triệt tiêu: một bot có 3.3 triệu USDT dòng tiền gộp nhưng net chỉ 9 nghìn.
- **`wiped_out`**: tuần có `pnlRatio = -1.0` nghĩa là tài khoản về 0. Đây là tín hiệu hạng nhất, đẩy thẳng chiều Drawdown lên 100.

Không có cổng kiểu "chỉ nhận vốn suy ra khi nó lớn hơn AUM 1.5 lần" — cổng một chiều như vậy chỉ làm rủi ro nhỏ đi.

## Vị thế mở

Dataset có hai schema vị thế và cả hai đều được đọc:

- Schema đầy đủ: `instId`, `direction`, `leverage`, `margin_usdt`, `entry_price`, `current_mark_price` → exposure quy được về từng instrument.
- Schema rút gọn: thiếu `instId` nhưng có `posSide`, `lever`, `margin`, `upl` → vẫn tính được chiều tổng, exposure gộp/ròng và đòn bẩy; chỉ phần quy về thị trường là `UNKNOWN`.

Khi **toàn bộ** vị thế thiếu `instId`, hệ thống đánh `instrument_withheld_upstream`: đã xác minh
OKX trả `instId` rỗng cho trader đó, nên crawl lại không sửa được. Backlog xếp nó vào nhóm
"upstream không công bố" chứ không phải "chưa thu thập".

Notional lấy từ `margin × leverage`, không nhân `position_size × price` vì hệ số hợp đồng khác nhau theo instrument (BTC 0.01, ETH 0.1).

Nếu margin cam kết vượt vốn báo cáo, hệ thống đánh dấu `MARGIN_EXCEEDS_CAPITAL` và **không** quy ra điểm rủi ro theo tỷ lệ vốn — vì không phân biệt được "đòn bẩy quá mức" với "số vốn sai".

## Nguyên tắc: chỉ dữ liệu công khai

Nếu có đủ dữ liệu tài khoản thì nhìn thẳng vào tài khoản là xong, không cần QC. Giá trị của
hệ thống này nằm ở chỗ **suy luận chặt chẽ từ dữ liệu công khai không đầy đủ**. Vì vậy:

> Không trả `UNKNOWN` khi bằng chứng công khai còn cho phép chặn khoảng, loại trừ hoặc
> đối chiếu chéo. Nói ra cái *xác định được*, kèm biên và độ tin cậy.

Tầng suy luận ở [inference/public_signals.py](backend/mcp/inference/public_signals.py), gồm
bốn thứ đã kiểm chứng trên dữ liệu thật:

**1. Giải mã thời gian từ `subPosId`.** Id của OKX là snowflake: `openTime = (id >> 25) + 1672502400000`.
Đối chiếu 326 lệnh có `openTime` công bố: **sai số tối đa 48 ms**. Nhờ đó 33 vị thế có
`openTime` rỗng vẫn xác định được giờ mở chính xác.

**2. Biến động giá ngụ ý.** `pnlRatio = (biến_động_giá × chiều − phí_khứ_hồi) × đòn_bẩy`.
Đảo ngược để lấy biến động giá của vị thế đang mở.

**3. Ước lượng phí từ chính sổ lệnh.** Phần dư giữa `biến_động × đòn_bẩy` và `pnlRatio` chính
là chi phí. Đo được ~0.09% khứ hồi — khớp với sai số median 1.77% ở đòn bẩy 20.

**4. Quy instrument bằng loại trừ.** Với vị thế thiếu `instId`: lấy giờ mở (1), biến động ngụ ý
(2), rồi kiểm từng instrument bot thực sự giao dịch xem giá của nó **có thể** tạo ra biến động
đó không. Kết quả là một trong bốn phán quyết, không bao giờ là phỏng đoán:

| Phán quyết | Nghĩa |
|---|---|
| `DETERMINED` | Đúng một ứng viên sống sót → quy được instrument |
| `NARROWED` | Nhiều ứng viên cùng khớp → giữ nguyên tập, không chọn bừa |
| `OUTSIDE_LEDGER_UNIVERSE` | Không ứng viên nào khớp → bot đang giữ instrument ngoài sổ lệnh gần đây |
| `INSUFFICIENT_EVIDENCE` | Thiếu giờ mở, tỷ lệ hoặc giá |

Trên bot `793739635259546051` (OKX giấu `instId` cả 33/33 vị thế): **23 xác định duy nhất,
0 mơ hồ, 10 ngoài sổ lệnh**. Exposure từ chỗ không quy được về đâu, giờ tách ra
SOL ~59k và HYPE ~52k USDT.

Suy luận chạy **tại thời điểm thu thập** vì cần giá đồng bộ với ảnh chụp vị thế, và được ghi
kèm phương pháp + tập ứng viên. Trong lõi, `attribution_source` luôn tách bạch `OBSERVED`
với `INFERRED`, và các lens dùng bằng chứng suy luận ở **độ tin cậy thấp hơn**.

**5. Sàn vốn từ margin.** Vốn không bao giờ nhỏ hơn tổng margin đang cam kết — một chặn dưới
luôn tính được, kể cả khi không dựng nổi đường cong equity.

## Thu thập dữ liệu bot

```bash
python3 -m Agent.none.scripts.crawl_bots --max-pages 5
```

Chỉ dùng endpoint **theo từng trader**: `public-weekly-pnl`, `public-current-subpositions`,
`public-subpositions-history` (phân trang bằng `after=<subPosId>`).

**Không dùng `public-lead-traders`.** Endpoint này bỏ qua tham số `uniqueCode` và trả về
bảng xếp hạng, nên lấy `ranks[0]` sẽ gán hồ sơ của trader khác. `public-stats` trả lỗi
`51000` cho các code này, nên `aum/pnl/pnlRatio/leadDays` không thể lấy theo từng trader —
chúng được mang sang từ snapshot cũ **của đúng `uniqueCode` đó** và đánh dấu
`LOCAL_SNAPSHOT_UNVERIFIED`.

Mỗi bot được ghi vào đúng một thư mục `cex/<symbol giao dịch chính>/bot/bot_<uniqueCode>`.
Nhãn venue trong báo cáo lấy theo **thị trường đã quy được**, không theo thư mục lưu — nhiều
bot nằm trong `dex/` nhưng thực chất giao dịch OKX CEX swap.

Crawler cũng lấy `tickers` một lần để có giá đồng bộ, rồi chạy quy-instrument cho các vị thế
thiếu `instId` ngay tại thời điểm chụp.

## Đối soát sổ lệnh: phân loại theo nguyên nhân

Một nhãn `MISMATCH` duy nhất gộp chung ba vấn đề khác hẳn nhau, nên nó được tách ra:

| Trạng thái | Nghĩa |
|---|---|
| `RECONCILED` | Lệch dưới 1% |
| `PARTIAL_LEDGER` | Sổ lệnh là tập con: chạm giới hạn trang, hoặc phủ ít hơn 90% `leadDays` |
| `IDENTITY_MISMATCH` | Các dòng lệnh mang `uniqueCode` của bot khác → **từ chối sổ lệnh**, đánh giá bot mà không có lịch sử |
| `UNVERIFIED_REFERENCE` | Cùng bot, phủ đủ, nhưng `pnl` đối chiếu có nguồn gốc chưa xác minh |
| `MISMATCH` | Cùng bot, phủ đủ, nguồn đã xác minh, nhưng số vẫn lệch |

Mọi dòng sub-position của OKX đều mang `uniqueCode`, nên sổ lệnh gán nhầm là **phát hiện được**
và không bao giờ được lọt qua im lặng.

## Bot được ghép với thị trường nào?

Không ghép theo tên thư mục. QC đọc **sổ lệnh thật**:

- `asset_context`: nơi snapshot được lưu.
- `primary_traded_symbol`: instrument chiếm tỷ trọng lớn nhất trong ledger.
- `symbol_exposure_share`: phân bổ giao dịch thực tế.
- Nếu sổ lệnh trống, thị trường lấy từ **vị thế đang mở**.
- Nếu không có dữ liệu thị trường cho instrument đó → `market = None`, các lens phụ thuộc thị trường trả `UNKNOWN`, không ghép thay thế.

## Nền vốn và rủi ro tương lai

Đây là điểm dễ tạo số vô nghĩa nên được tách bạch:

- **Lịch sử**: drawdown báo bằng **số tiền tuyệt đối**. Phần trăm chỉ xuất hiện khi dựng được vốn khởi điểm hợp lệ; AUM không thể trừ PnL lũy kế vì thiếu lịch sử nạp/rút.
- **Tương lai**: Monte Carlo đo trên **AUM hiện tại** (`capital_basis = CURRENT_AUM`) và trả thêm `p_ruin` — xác suất cháy sạch vốn hiện có. Drawdown mô phỏng bị chặn ở 100%.

## Lịch sử và xu hướng rủi ro

Mỗi lần chạy ghi một bản ghi vào `Agent/data/state/assessments/<bot_id>.json`. Lần chạy sau đọc bản ghi trước để tính `risk_trend`. Chạy lại cùng một snapshot không tạo bản ghi trùng vì `assessment_id` là hàm xác định của đầu vào.

## Ba báo cáo theo ba bước

Mỗi bước của kiến trúc có một báo cáo riêng, không gộp chung thành một bảng dày đặc.

```bash
python3 -m Agent.backend.run_report --report market   # Bước 1: chế độ thị trường
python3 -m Agent.backend.run_report --report bot      # Bước 2: đo từng bot theo asset
python3 -m Agent.backend.run_report --report qc       # Bước 3: xếp hạng rủi ro
python3 -m Agent.backend.run_report --report all      # cả ba, kèm backlog dữ liệu
```

**Bước 1 — thị trường.** Mỗi asset một dòng: chế độ thị trường viết thành câu tiếng Việt
(`Giảm, biến động bình thường`), thanh khoản, dòng tiền, ATR%, vị trí trong biên, chất lượng
dữ liệu, số bot đang giao dịch trên đó, và có đạt điều kiện giám sát hay không. Thị trường có
bot giao dịch được xếp lên đầu.

**Bước 2 — từng bot theo asset.** Thuần số liệu quan sát, **chưa có phán quyết**: số lệnh,
win rate, PF sổ sách và PF nếu chốt hết, sụt vốn, số vị thế, exposure, lỗ chưa chốt. Sắp theo
asset để so sánh các bot cùng đánh một thị trường.

**Bước 3 — xếp hạng.** Cột đúng như cần đọc:

```text
# | tên bot | trade | win% | asset | kết quả tính toán | score | xếp loại | nguyên nhân
```

Sắp theo score giảm dần. Mỗi bot có **hai lời giải thích tách bạch**:

**Vì sao rủi ro** — nguyên nhân thực chất, tiếng Việt với số cụ thể:
> *Đang ôm 88,537 USDT lỗ chưa chốt (68% vốn), chốt hết thì PF tụt từ 11.09 xuống 0.16; hành vi
> giao dịch nguy hiểm (điểm 100); ngược xu hướng thị trường (giảm).*

**Vì sao đúng số điểm đó** — [score_breakdown](backend/qc/schemas/risk_assessment.py) truy ngược
phép tính, kèm hai cột *đẩy điểm lên* và *kéo điểm xuống*:
> *Điểm 88.0 đến từ sàn veto 88, không phải bình quân: bình quân gia quyền 10 chiều chỉ 61.6.
> Veto kích hoạt bởi: hành vi giao dịch hủy hoại; chốt hết sổ mở thì profit factor chỉ còn 0.16.*
> ```
> + Hành vi giao dịch 100/100 (trọng số 1.2) đóng góp 12.6 điểm
> + Chất lượng hiệu suất 100/100 (trọng số 1.0) đóng góp 10.5 điểm
> − Rủi ro sụt vốn chỉ 15/100 (trọng số 1.1) kéo bình quân xuống
> − 1 chiều thiếu bằng chứng được tính trung tính 50 điểm
> ```

Tổng các `contribution` luôn bằng đúng `weighted_average`, nên phép tính kiểm chứng được; có
test ràng buộc điều đó. `decided_by` cho biết điểm đến từ `WEIGHTED_AVERAGE`, `VETO_FLOOR` hay
`EMERGENCY_OVERRIDE`.

Tùy chọn khác: `--venue CEX|DEX|ALL`, `--json`, `--no-detail`, `--as-of-ms`, `--mode SNAPSHOT|LIVE`.

Khi một bot có nhiều snapshot trùng, hệ thống chọn bản **giàu provenance nhất** (có đường cong vốn, vị thế quy được về instrument, sổ lệnh đối soát khớp) chứ không lấy bản đầu tiên theo thứ tự alphabet. Bản được dùng in ra ở dòng `Nguồn dùng để đánh giá`.

Dọn thư mục trùng:

```bash
python3 -m Agent.backend.run_prune           # chạy thử, không xoá
python3 -m Agent.backend.run_prune --apply   # xoá thật
```

Phần cuối báo cáo là **backlog dữ liệu**: mỗi mục thiếu đi kèm phạm vi, mô tả, các chiều đánh giá sẽ mở khóa và bot bị ảnh hưởng, sắp theo độ ưu tiên.

Đánh giá một bot đơn lẻ:

```bash
python3 -m Agent.backend.run_pipeline BTC --bot bot_top_performer --venue CEX
```

## Nguyên tắc dữ liệu

- Thiếu dữ liệu giữ nguyên `MISSING` / `STALE` / `UNKNOWN`, không quy về trung tính hay an toàn.
- Rủi ro đo được cao **không bị** hạ xuống `UNKNOWN` chỉ vì bằng chứng mỏng; `UNKNOWN` chỉ dùng khi độ phủ chiều đánh giá dưới 50% và điểm chưa cao.
- Độ tin cậy thấp thì hạ cấp **hành động đề xuất**, không che giấu tín hiệu rủi ro.

## Kiểm thử

```bash
python3 -m pytest -p no:asyncio Agent/none/test -q
```

## Quy mô thực tế trên OKX

Quét toàn bộ danh sách lead trader công khai (13 trang × 20) rồi đối chiếu bằng sổ lệnh thật:

| | Số lượng |
|---|---|
| Lead trader SWAP công khai | 260 |
| Có sổ lệnh (giao dịch gần đây) | 141 |
| Sổ lệnh rỗng | 119 |
| Giao dịch 1 trong 15 asset mục tiêu | **130** (92%) |
| Lấy 1 trong 15 asset làm thị trường chính | 108 |
| Giao dịch 1 trong 19 asset của dataset | **132** (94%) |

Phân bố rất lệch: BTC 52 bot lấy làm chính, ETH 38, SOL 5, phần còn lại là đuôi dài. Asset
ngoài 15 đáng chú ý: ZEC (7 bot), SNDK (7), XAU (3).

Crawl 132 bot tốn khoảng **8 phút** (6 request/bot, delay 0.6s); Monte Carlo 5.000 đường ×
500 lệnh cho toàn bộ chỉ mất vài giây vì đã vectorised theo batch.

## Phát hiện về dataset hiện tại

- Dataset đã được dọn về đúng **4 thư mục, mỗi bot một chỗ**, đặt theo instrument giao dịch chính.
- Tồn tại **2 schema sổ lệnh khác nhau**; cả hai đều đã được parse.
- `CryptoPanda` trước đây giữ sổ lệnh của `793739635259546051`; sự thật từ API là **0 lệnh đóng, 1 vị thế BTC**.
- Phân trang nâng lịch sử `maomao12345` từ 63 lên 164 lệnh và `對不起...` từ 100 lên 326 lệnh.
- AUM của mọi bot nhỏ hơn PnL lũy kế sổ lệnh. Trên OKX copy trading, `aum` là tiền của người copy chứ không phải vốn của lead trader — vốn thật phải dựng từ weekly PnL.
- `maomao12345` có tuần `pnlRatio = -1.0`: tài khoản **đã từng cháy sạch** rồi nạp lại lên 3.65 triệu USDT.

## Bán qua MCP / OKX AI Marketplace (x402)

`backend/agent_server.py` phơi 6 tool MCP (`assess_bot`, `get_market`...) qua chuẩn Model
Context Protocol. Mỗi lời gọi tool có thể bị tính phí vi mô qua **x402** (`backend/payments/x402.py`):
client gọi không kèm thanh toán → server trả HTTP 402 kèm yêu cầu giá → client ký thanh toán và
gọi lại → server xác minh THẬT bằng một lệnh gọi HTTP tới facilitator của OKX
(`web3.okx.com/api/v6/pay/x402/verify`), không tự nhận "đã trả tiền" nếu facilitator không xác nhận.

Tắt mặc định (`X402_ENABLED=false`, xem `.env.example`) — bật thiếu cấu hình ví/token nhận tiền
thì mọi lời gọi tool bị từ chối (fail-closed), không âm thầm chạy miễn phí. Thanh toán chốt trên
**X Layer** (`eip155:196`), ví nhận chỉ cần địa chỉ công khai, server không giữ private key của ai.

**Trạng thái (22/09/2026): CÒN ĐANG PHÁT TRIỂN, cố ý giữ TẮT.** Đã gọi thử một lần thật tới
facilitator OKX (`/api/v6/pay/x402/verify`) bằng credential thật lấy từ OKX Web3 Developer Portal —
key/secret/passphrase được OKX xác thực đúng (lỗi trả về là `30001 invalid params` do payload test
cố tình để trống, KHÁC hẳn mã lỗi xác thực sai `50111`) — nên phần *xác thực với facilitator* chạy
được thật. Nhưng chưa test được một lượt thanh toán 402 → ký → retry → verify đầy đủ (cần client
thật ký một payment payload hợp lệ), và địa chỉ hợp đồng USDC dùng cho `X402_ASSET_ADDRESS` mới tra
chéo 2 nguồn cho 2 kết quả khác nhau (xem cảnh báo trong `Agent/.env`), chưa xác nhận chắc chắn.
`X402_ENABLED` giữ nguyên `false` cho tới khi cả hai việc trên xong — mọi MCP tool hiện chạy
**miễn phí, không bị chặn thanh toán**, kể cả khi các biến `X402_*`/`OKX_X402_*` khác đã điền sẵn.

Chi tiết giao thức đầy đủ (đã xác minh bằng cách đọc trực tiếp SDK `okxweb3-app-x402` OKX công bố):
[`docs/okx_marketplace.md`](docs/okx_marketplace.md).

## Giới hạn còn lại

- Chưa có ingestion/reconciliation OKX REST + WebSocket; dữ liệu là snapshot crawl.
- Weekly PnL chỉ có 12 tuần và ratio làm tròn 4 chữ số, nên đường cong vốn thưa và một số tuần phải bỏ.
- Dòng tiền DEX suy ra từ 100 tick gần nhất nên chỉ phản ánh một cửa sổ rất ngắn.
- Thiếu order book và token-security cho phần lớn asset. DEX bị loại với lý do riêng `DEX_POOL_LIQUIDITY_NOT_COLLECTED` vì AMM không có sổ lệnh — cần TVL/reserve/route depth thay thế.
- Nến DEX thực chất là giá CEX benchmark (`price_benchmark`), không phải giá pool on-chain; điều này được ghi vào limitation.
- Chưa có persistence/audit history, API/UI, và chưa có adapter giao dịch OKX được phép.
- Tầng control chỉ ghi nhận: `READ_ONLY`/`ADVISORY` ghi log local, `AUTOMATED` bị từ chối.
