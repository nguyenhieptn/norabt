# Kiểm định ngoài mẫu: điểm rủi ro có dự báo được kết quả xấu trong tương lai không?

**Câu hỏi gốc (từ sếp của dự án):** "sau khi phân tích ra được score thì sở cứ
ở đâu, lý luận nào để đánh giá được điều đó?"

Tài liệu này trả lời phần còn thiếu: phương pháp chấm điểm (stationary
bootstrap Politis & Romano 1994; PSR/DSR/MinTRL Bailey & López de Prado
2012/2014) đã có sở cứ học thuật, nhưng **chưa ai chứng minh bằng số liệu
rằng điểm rủi ro chấm trên quá khứ thực sự đoán trúng điều tệ xảy ra sau đó**.
Đây là phép đo trực tiếp cho khoảng trống đó, trên dữ liệu bot thật đang có
trên đĩa.

## Trả lời thẳng

Với **36 bot** đủ điều kiện (≥ 80 lệnh đã chốt) chấm điểm bằng đúng
`RiskSupervisionPipeline` sản phẩm trên 60% lệnh đầu (theo thời gian) và đo
kết quả thật trên 40% lệnh sau:

- **Có tín hiệu thật, ở mức vừa phải, cho sụt vốn và "sập"**: điểm rủi ro
  tương quan thuận với sụt vốn tối đa ở nửa sau (Spearman ρ = **0,64**,
  khoảng tin cậy bootstrap 95% = **[0,39; 0,80]**, không chứa 0) và với việc
  có "sập" hay không (ρ = **0,41**, CI 95% = **[0,21; 0,59]**, không chứa 0).
  Cả hai đều vượt xa mốc so sánh ngẫu nhiên (kiểm định hoán vị p = 0,000 và
  p = 0,013).
- **Chưa có bằng chứng cho lợi nhuận và tỉ lệ thắng**: tương quan với PnL
  nửa sau (ρ = 0,205, CI 95% = **[-0,20; 0,54]**) và với tỉ lệ thắng nửa sau
  (ρ = -0,161, CI 95% = **[-0,48; 0,17]**) đều có khoảng tin cậy **chứa số
  0** → **chưa kết luận được** có tương quan thật hay không, không phải "có
  xu hướng nhẹ".
- Nói cách khác: bằng chứng hiện có cho thấy thang điểm làm đúng việc nó
  được thiết kế để làm — **cảnh báo nguy cơ sụt vốn/sập**, chứ **không** phải
  một công cụ dự báo bot nào sẽ lãi hay lỗ nhiều hơn. Đừng đọc điểm cao là
  "bot này sẽ thua lỗ"; hãy đọc là "bot này có xác suất sụt vốn mạnh cao
  hơn".
- Cỡ mẫu (35-36 bot) nhỏ, cùng một giai đoạn thị trường, và các bot không
  độc lập với nhau (xem mục Giới hạn) — đây là bằng chứng đáng chú ý, không
  phải kết luận chắc chắn.

## 1. Bối cảnh và câu hỏi

Điểm rủi ro (`risk_score`, 0-100, **cao = rủi ro cao hơn**, xem
`Agent/backend/qc/scoring/fusion.py`) được tổng hợp có trọng số từ 10 lăng
kính (drawdown, tail risk, đòn bẩy, hành vi, ...). Phương pháp thống kê nền
(bootstrap, PSR/DSR) đã công bố và đúng chuẩn, nhưng một công thức đúng chuẩn
học thuật vẫn có thể không dự báo được gì trên dữ liệu thật. Câu hỏi cần trả
lời trực tiếp: **điểm rủi ro chấm trên dữ liệu quá khứ có dự báo được kết quả
xấu ở tương lai không?**

## 2. Phương pháp

### 2.1 Dữ liệu và bộ lọc

- Nguồn: `Agent/data/<cex|dex>/<asset>/bot/<bot_folder>/{overview.json,
  trade_list.json}` — đúng bố cục `FileBotDataSource` đọc
  (`Agent/backend/sources/bot_source.py`).
- Bộ lọc: **61** thư mục bot có đủ 2 file, cả 61 đọc/parse được bằng đúng
  `TradeLedgerManager.parse_trade_list_with_diagnostics` sản phẩm dùng
  (`Agent/backend/mcp/trades/ledger.py`) — không viết lại logic đọc ledger.
- Ngưỡng lọc: **≥ 80 lệnh đã chốt** → còn lại **36/61 bot**. Chỉ dùng lệnh đã
  chốt (`closed_trades`), không bao giờ dùng vị thế đang mở, đúng ràng buộc
  chung của dự án.
- Lưu ý: mục tiêu "mỗi nửa ≥ 40 lệnh" trong đề bài không khớp tuyệt đối với
  tỉ lệ chia 60/40 ở đúng ngưỡng 80 lệnh (0,4 × 80 = 32, không phải 40); script
  làm đúng theo cả hai con số cụ thể được giao (ngưỡng 80, tỉ lệ 60%) thay vì
  tự ý nâng ngưỡng lên 100. Hệ quả thực tế: 1 bot ở biên (81 lệnh) chỉ còn 25
  lệnh ở nửa sau do các lệnh trùng mốc thời gian dồn về phía "train" (xem
  2.2) — vẫn đủ để tính chỉ số, nhưng là mẫu nhỏ nhất trong 36 bot.

### 2.2 Chia theo thời gian, không chia ngẫu nhiên

Mỗi bot: sắp lệnh theo thời gian đóng (`close_time`), cắt ở mốc mà lệnh thứ
`round(0,6 × N)` đóng — mọi lệnh đóng **tại hoặc trước** mốc đó vào nửa
"train" (nửa đầu, để chấm điểm), mọi lệnh đóng **sau** mốc đó vào nửa "test"
(nửa sau, để đo kết quả thật, **không đụng vào lúc chấm điểm**).

Chia ngẫu nhiên là sai ở bài toán này: nó để một lệnh đóng sau mốc cắt lọt
vào nửa dùng để chấm điểm hoàn toàn do may rủi — tức để tương lai rò vào lúc
chấm, đúng thứ rò rỉ mà phép kiểm định này cần loại trừ (xem docstring của
`Agent/backend/research/splitting.py`). Lệnh trùng mốc thời gian với lệnh cắt
luôn được gộp hết về nửa "train" để không bao giờ có lệnh nửa sau đóng trước
lệnh nửa đầu — bất biến này (`max(train.close_time) <= min(test.close_time)`)
có test riêng (`Agent/none/test/test_research_splitting.py`).

### 2.3 Chấm điểm nửa đầu — dùng đúng đường chấm điểm sản phẩm

`RiskSupervisionPipeline.run()` (`Agent/backend/pipeline.py`) không nhận
sổ lệnh làm tham số — nó đọc thẳng `overview.json`/`trade_list.json` từ đĩa.
Để chấm điểm "sản phẩm sẽ nói gì nếu chỉ biết N lệnh đầu" mà **không sửa một
dòng logic chấm điểm nào**, `Agent/backend/research/shadow_scoring.py` dựng
một thư mục dữ liệu "bóng" (symlink) giống hệt `Agent/data` ở mọi thứ
(market, universe, mọi bot khác), chỉ riêng 2 file JSON của bot đang xét được
thay bằng bản đã cắt:

1. **`trade_list.json`**: chỉ giữ các dòng có thời gian đóng ≤ mốc cắt — lọc
   bằng đúng hàm `TradeLedgerManager._timestamp_ms` sản phẩm dùng để đọc thời
   gian đóng của một dòng, không đọc lại `closeTime/uTime/close_time` bằng
   công thức chép tay. `open_positions` bị khoá về rỗng: đúng ràng buộc "vị
   thế đang mở không được tính là kết quả", và ảnh chụp vị thế mở duy nhất
   trong dữ liệu này là ảnh chụp tại **thời điểm crawl** — tức là **sau** mốc
   cắt, dùng nó sẽ để lộ trạng thái tương lai vào điểm chấm nửa đầu.
2. **`overview.json`**: `weekly_pnl_history` bị cắt tại đúng mốc đó. Chuỗi
   này nuôi đường vốn (`CapitalResolver`/`EquityCurveBuilder`,
   `Agent/backend/mcp/capital/equity_curve.py`), là thứ lăng kính "Rủi ro sụt
   vốn" đo `max_dd_pct` dựa vào. Không cắt chuỗi này thì sụt vốn ở các tuần
   *sau* mốc cắt sẽ rò thẳng vào điểm chấm nửa đầu — đúng loại rò rỉ mà toàn
   bộ phép kiểm định này tồn tại để loại trừ.
3. `RiskSupervisionPipeline` được gọi với `history` là một
   `AssessmentHistoryStore` rỗng trong thư mục tạm và `persist_history=False`
   — điểm chấm nửa đầu không bao giờ đọc "đánh giá trước đó" tính từ sổ
   lệnh đầy đủ thật (sẽ rò tương lai vào so sánh độ trôi chiến lược), và
   không bao giờ ghi vào lịch sử đánh giá thật của sản phẩm.

**Những gì KHÔNG lùi được về đúng thời điểm cắt (giới hạn đã biết, không che
giấu):** dữ liệu thị trường (nến, sổ lệnh, open interest) chỉ có bản crawl
mới nhất, không có ảnh chụp theo từng mốc cắt riêng của từng bot — nên lăng
kính "Đồng thuận thị trường" và "Thanh khoản/Khớp lệnh" nhìn điều kiện thị
trường hiện tại, không phải điều kiện đúng lúc cắt. Các trường AUM/PnL/PnLRatio
đơn lẻ trong `overview.json` cũng được giữ nguyên (là số "hiện tại"), nhưng
không lăng kính nào đọc trực tiếp các trường này để chấm điểm — chỉ dùng cho
một chuỗi trạng thái đối chiếu, không phải input của điểm số — nên không tạo
thêm rò rỉ vào điểm số.

### 2.4 Đo kết quả thật ở nửa sau

Tính trực tiếp từ lệnh nửa sau (`Agent/backend/research/outcomes.py`), không
mô phỏng: tổng PnL và PnL/vốn tham chiếu, sụt vốn lớn nhất (đỉnh-đáy trên
đường PnL luỹ kế) tuyệt đối và theo %, tỉ lệ thắng, chuỗi thua liên tiếp dài
nhất (đánh dấu riêng ≥5 và ≥10), và **"sập"** = sụt vốn nửa sau ≥ 30% vốn
tham chiếu (ngưỡng có thể đổi bằng `--collapse-drawdown-pct`).

**Vốn tham chiếu dùng để tính %** là chính con số `reference_capital` mà
`RiskSupervisionPipeline` đã tự resolve khi chấm điểm nửa đầu
(`result.bot_result.current_state.reference_capital`) — cùng một con số sản
phẩm dùng để tính rủi ro theo vốn, không phải một con số tự tính riêng. 1/36
bot không resolve được vốn tham chiếu nào (không có đường vốn tuần khả dụng
và AUM báo cáo bằng 0) → 3/4 chỉ số phần trăm của bot đó là "không xác định",
không bị coi là 0.

### 2.5 Kiểm định thống kê

Tự cài trên nền numpy, không thêm scipy
(`Agent/backend/research/statistics.py`):

- **Spearman**: Pearson trên hạng (hạng trung bình khi có trùng giá trị).
- **Bootstrap 95%**: lấy mẫu lại **theo bot** (cặp risk_score/kết quả), có
  hoàn lại, 2000 lần, phân vị 2,5%/97,5%; seed cố định (mặc định 42) để chạy
  lại ra đúng số cũ.
- **Mốc so sánh ngẫu nhiên**: xáo trộn nhãn kết quả 2000 lần, tính lại tương
  quan mỗi lần, p-value hai phía = tỉ lệ lần xáo trộn cho |ρ| ≥ |ρ quan sát
  được|.

## 3. Kết quả

### 3.1 Số bot đưa vào

| Bước | Số bot |
|---|---|
| Thư mục có đủ overview.json + trade_list.json | 61 |
| Đọc/parse ledger thành công | 61 |
| ≥ 80 lệnh đã chốt (ngưỡng lọc) | 36 |
| Chấm điểm nửa đầu + đo nửa sau thành công | **36** (0 lỗi khi chạy) |
| Có vốn tham chiếu khả dụng (dùng cho 3/4 chỉ số) | 35 |

### 3.2 Tương quan hạng Spearman (risk_score nửa đầu × kết quả thật nửa sau)

| Chỉ số kết quả (nửa sau) | n | ρ (Spearman) | CI bootstrap 95% | p (hoán vị, 2 phía) | Kết luận |
|---|---|---|---|---|---|
| Sụt vốn lớn nhất, % | 35 | **0,640** | [0,386; 0,802] | 0,000 | CI không chứa 0 — có tín hiệu |
| Có "sập" hay không (0/1) | 35 | **0,407** | [0,205; 0,591] | 0,013 | CI không chứa 0 — có tín hiệu |
| PnL, % vốn tham chiếu | 35 | 0,205 | [-0,195; 0,539] | 0,241 | CI chứa 0 — **chưa kết luận được** |
| Tỉ lệ thắng, % | 36 | -0,161 | [-0,480; 0,167] | 0,361 | CI chứa 0 — **chưa kết luận được** |

Dấu dương ở hai chỉ số đầu đúng hướng mong đợi: điểm rủi ro càng cao thì sụt
vốn/khả năng sập ở tương lai càng lớn. Dấu của PnL và tỉ lệ thắng **không**
đáng tin (CI chứa 0), không nên diễn giải theo bất kỳ hướng nào.

### 3.3 Bảng theo nhóm điểm rủi ro

| Nhóm risk_score | n | PnL% trung vị (nửa sau) | Sụt vốn % trung vị (nửa sau) | Tỉ lệ "sập" |
|---|---|---|---|---|
| < 30 | 22 | +3,4% | 1,3% | 0% (0/21 có dữ liệu) |
| 30 – 50 | 4 | +14,2% | 4,1% | 0% (0/4) |
| 50 – 70 | **0** | — | — | — |
| ≥ 70 | 10 | +21,5% | 9,0% | 30% (3/10) |

**Nhóm 50–70 trống hoàn toàn** — không phải thiếu dữ liệu, mà vì `risk_score`
phân bố **lưỡng cực**: 26/36 bot nằm rải trong [15,2; 35,9], còn 10/36 bot bị
"veto floor" của `RiskFusionEngine` ép thẳng lên 85,0 (hành vi giao dịch hủy
hoại hoặc rủi ro đuôi cực đoan), cộng 1 bot ở 88,0 và 1 bot ở 100,0 (kịch bản
stress dẫn tới thanh lý). Đọc bảng này như **hai cụm** — "chấm liên tục, có
vẻ an toàn" và "đã bị chặn cứng vì vi phạm một quy tắc cụ thể" — chứ không
phải một thang đều từ thấp lên cao. Nhóm ≥70 có tỉ lệ sập 30% so với 0% ở hai
nhóm dưới — đây chính là phần đóng góp chính vào tương quan sụt vốn/sập ở
mục 3.2.

### 3.4 Một ca đáng chú ý (không phải lỗi tính toán)

`CEX/BTC/bot_828556126433358780`: risk_score = 100,0 (mức cao nhất), vốn tham
chiếu tại mốc cắt chỉ ≈ 2.732 USDT (rất nhỏ), PnL nửa sau +5.843,6%, sụt vốn
nửa sau 239,4% (vượt quá 100% vì đường PnL luỹ kế tụt xuống sâu hơn cả vốn
tham chiếu tại một thời điểm), đã "sập" theo định nghĩa ở trên. Đây là bot
tương ứng với vốn quy mô rất nhỏ nhưng PnL tuyệt đối dao động lớn — % trở nên
cực đoan không phải vì tính sai, mà vì mẫu số nhỏ. Đây chính là lý do báo cáo
dùng **tương quan hạng (Spearman)**, vốn không nhạy với ngoại lai kiểu này,
thay vì tương quan Pearson trên giá trị thô.

### 3.5 Bảng đầy đủ 36 bot (sắp theo risk_score giảm dần)

> **Ghi chú về cột `verdict`.** Bảng dưới đây chép nguyên nhãn mà hệ thống
> SINH RA TẠI THỜI ĐIỂM CHẠY nghiên cứu này: thang một chiều bốn bậc
> `NGUY HIỂM` / `TIỀM ẨN` / `TIỀM NĂNG` / `AN TOÀN`. Thang đó **đã bị thay**
> bằng nhãn hai trục (`DRAWDOWN: LOW/HIGH × QUALITY: GOOD/WEAK`, cộng cờ
> `HIDDEN RISK` và `INSUFFICIENT EVIDENCE`) — xem `VALID_VERDICTS` trong
> `Agent/backend/agent_server.py`. Cột này KHÔNG được cập nhật theo thang
> mới, và cố ý như vậy: sửa lại số liệu của một lượt đo đã chạy xong thì
> bảng sẽ không còn là hồ sơ của chính lượt đo đó nữa. Mọi con số thống kê
> trong báo cáo (Spearman, khoảng tin cậy, p-value) tính trên `risk_score`
> — cột liên tục, không đổi qua lần đổi nhãn — nên kết luận không bị ảnh
> hưởng.

| Bot | train/test | risk_score | verdict | PnL% nửa sau | Sụt vốn% nửa sau | Sập? |
|---|---|---|---|---|---|---|
| CEX/BTC/bot_828556126433358780 | 300/198 | 100.0 | NGUY HIỂM | +5843.6% | 239.4% | CÓ |
| CEX/BTC/bot_819848249304757406 | 191/127 | 88.0 | NGUY HIỂM | +5.9% | 6.4% | không |
| CEX/BTC/bot_811997770117827919 | 161/107 | 85.0 | NGUY HIỂM | +91.4% | 18.6% | không |
| CEX/ETH/bot_0EAF7292CE2FAAC2 | 127/85 | 85.0 | NGUY HIỂM | +3.6% | 7.9% | không |
| CEX/ETH/bot_821382564224395312 | 91/61 | 85.0 | NGUY HIỂM | -34.2% | 65.3% | CÓ |
| CEX/ETH/bot_9C2CB3B2306B28EA | 300/200 | 85.0 | NGUY HIỂM | -18.7% | 46.0% | CÓ |
| CEX/ETH/bot_CA1C48E543EF7A95 | 187/123 | 85.0 | NGUY HIỂM | +28.6% | 9.7% | không |
| CEX/ETH/bot_F6476365DB0D09A3 | 99/64 | 85.0 | NGUY HIỂM | +74.8% | 1.5% | không |
| CEX/XAU/bot_FE701D3CB0AC0E8F | 95/64 | 85.0 | NGUY HIỂM | +50.6% | 6.2% | không |
| DEX/WBTC/bot_58D7D205FB591484 | 141/94 | 85.0 | NGUY HIỂM | +14.4% | 8.3% | không |
| CEX/BTC/bot_35F888C7BB441B2B | 260/173 | 35.9 | AN TOÀN | +31.3% | 4.9% | không |
| CEX/ETH/bot_6F262ADB3B44266C | 249/166 | 35.4 | AN TOÀN | +28.8% | 3.3% | không |
| CEX/ETH/bot_241CFF1D95076351 | 301/201 | 32.3 | AN TOÀN | -7.6% | 14.3% | không |
| CEX/SNDK/bot_26E8167F37D30564 | 56/37 | 30.4 | TIỀM NĂNG | -0.4% | 1.4% | không |
| CEX/BTC/bot_2DE3E8FEAC245B9C | 326/212 | 29.6 | TIỀM NĂNG | -1.8% | 2.4% | không |
| CEX/BTC/bot_80DBF719B37B6213 | 74/49 | 28.9 | TIỀM ẨN | +3.6% | 2.5% | không |
| CEX/ETH/bot_952071415C9BAD06 | 317/212 | 27.6 | TIỀM NĂNG | +0.1% | 0.0% | không |
| CEX/ETH/bot_9A073DDF49603886 | 128/85 | 27.5 | TIỀM NĂNG | N/A | N/A | ? |
| CEX/XAU/bot_F76CC883269E6FFB | 299/200 | 27.1 | TIỀM NĂNG | +2.4% | 9.2% | không |
| CEX/BTC/bot_31F3288F9B90B496 | 298/199 | 25.9 | TIỀM ẨN | +0.4% | 0.7% | không |
| CEX/TSLA/bot_2A276DA355BBBDBC | 173/115 | 25.2 | TIỀM NĂNG | +11.1% | 9.5% | không |
| CEX/PUMP/bot_C84F6F6717746BD4 | 299/200 | 24.9 | TIỀM NĂNG | +3.4% | 0.2% | không |
| CEX/BTC/bot_28AEEA33C8C78CC9 | 309/191 | 24.6 | TIỀM ẨN | +7.8% | 1.0% | không |
| CEX/HYPE/bot_793739635259546051 | 198/132 | 24.5 | TIỀM ẨN | +6.1% | 2.9% | không |
| CEX/SNDK/bot_72AFDC179D66D034 | 197/131 | 23.8 | TIỀM ẨN | +0.3% | 2.5% | không |
| CEX/ETH/bot_F1344E1B7AE2D41F | 101/68 | 22.8 | TIỀM NĂNG | +2.1% | 10.1% | không |
| CEX/BTC/bot_818313090499674879 | 55/36 | 22.3 | TIỀM ẨN | +32.4% | 3.2% | không |
| DEX/SOL/bot_EF1CC6F40E834D1A | 180/120 | 19.3 | TIỀM ẨN | +6.1% | 0.3% | không |
| CEX/ETH/bot_A0EDF7F0D96A7E8C | 80/54 | 18.9 | TIỀM NĂNG | +10.4% | 1.3% | không |
| CEX/LIT/bot_44570B03F5CBCEDE | 49/32 | 18.3 | TIỀM ẨN | +14.2% | 0.0% | không |
| CEX/ETH/bot_74F7C7A53CD18275 | 117/78 | 17.9 | TIỀM NĂNG | -4.8% | 5.0% | không |
| CEX/ETH/bot_53AEED5A8E4EBBB2 | 87/58 | 17.1 | TIỀM NĂNG | +3.2% | 0.1% | không |
| DEX/WETH/bot_59F6D70B76C31DE5 | 71/48 | 17.0 | TIỀM ẨN | +2.0% | 0.3% | không |
| CEX/BTC/bot_EA315ECC2A50F8B6 | 124/83 | 16.7 | TIỀM NĂNG | +7.6% | 0.3% | không |
| CEX/SNDK/bot_1DEAF15FD2D91832 | 179/119 | 16.2 | TIỀM ẨN | +0.1% | 0.2% | không |
| CEX/BTC/bot_722BE7E081829BB1 | 56/25 | 15.2 | TIỀM NĂNG | +26.2% | 3.0% | không |

(`?` = bot không có vốn tham chiếu khả dụng, không tính được PnL%/sụt vốn%/sập.
Bảng đầy đủ dạng máy đọc được kèm mọi trường — bao gồm `quality_score`, điểm
10 lăng kính, `cutoff_ms` — nằm trong file JSON script tạo ra khi chạy với
`--out-json`, xem mục 5.)

## 4. Giới hạn và các nguồn thiên lệch chưa loại trừ được

Cỡ mẫu chỉ 35-36 bot — mọi con số trên là **tín hiệu đáng chú ý ở cỡ mẫu
nhỏ**, không phải kết luận chắc chắn. Cụ thể:

1. **Sống sót (survivorship)**: dữ liệu chỉ có bot còn được OKX liệt kê tại
   thời điểm crawl. Bot đã bị gỡ/dừng hẳn trước đó — có thể là chính những ca
   "sập" nặng nhất — không nằm trong 61 thư mục nguồn. Tương quan đo được ở
   đây nhiều khả năng là **cận dưới** của tương quan thật, không phải giá trị
   đã đủ.
2. **Cùng một giai đoạn thị trường**: mốc cắt của 36 bot đều rơi trong một
   cửa sổ crawl hiện tại, không trải qua nhiều chu kỳ thị trường khác nhau.
   Nếu giai đoạn "nửa sau" trùng một pha cụ thể (tăng hay giảm giá chung), số
   liệu phản ánh một phần đặc điểm của pha đó, không chỉ đặc điểm của thang
   điểm.
3. **Các bot không độc lập với nhau**: nhiều bot cùng giao dịch một tài sản
   trong cùng khung thời gian (11/36 bot là BTC, nhiều bot ETH) — kết quả của
   chúng cùng chịu ảnh hưởng của một đường giá chung. Cỡ mẫu "hiệu dụng" nhỏ
   hơn con số 35-36 danh nghĩa, nên khoảng tin cậy báo cáo có thể lạc quan
   hơn thực tế.
4. **Dữ liệu thị trường không lùi theo mốc cắt** (mục 2.3) — lăng kính đồng
   thuận thị trường/thanh khoản nhìn điều kiện hiện tại, không phải điều kiện
   đúng lúc cắt của từng bot.
5. **1/36 bot không có vốn tham chiếu** → 3/4 chỉ số outcome của bot đó là
   "không xác định", không tính là 0 hay bỏ khỏi kiểm định một cách ngầm.
6. **Ngưỡng lọc và tỉ lệ chia chưa khớp tuyệt đối** (mục 2.1): ở biên ngưỡng
   80 lệnh, nửa sau có thể chỉ còn ~25-32 lệnh, thấp hơn mục tiêu ≥40 nêu
   trong đề bài.
7. **Phân bố risk_score lưỡng cực** (mục 3.3): bảng theo nhóm nên đọc như hai
   cụm tách biệt (dưới ngưỡng veto / đã bị veto), không phải một thang liên
   tục 0-100 đều tay.
8. Kết quả này đo **`risk_score`** — trục "rủi ro". `quality_score` (trục
   "tốt/xấu về hiệu suất") là một trục khác, **chưa được kiểm định ở đây**;
   nếu cần trả lời "điểm chất lượng có dự báo được lợi nhuận tương lai
   không", đó là một câu hỏi kế tiếp, không phải câu hỏi bài này trả lời.

## 5. Chạy lại để tự kiểm chứng

```bash
cd /home/ubuntu/norabt
python3 -m Agent.none.scripts.validate_out_of_sample --out-json /tmp/oos_results.json
```

Tham số mặc định dùng cho kết quả trong báo cáo này: `--min-trades 80
--train-fraction 0.6 --collapse-drawdown-pct 30 --seed 42
--bootstrap-resamples 2000 --permutations 2000 --simulation-iterations 2000
--simulation-horizon 200`. Script chỉ đọc `Agent/data` (không gọi mạng, không
ghi gì vào đó), in tiến độ theo từng bot, và chạy **tuần tự trên 1 tiến
trình** — không cần song song hoá ở quy mô 36 bot (chạy hết trong ~246 giây
trên 1 nhân CPU, nằm rất xa dưới trần ≤12 nhân/≤14GB của máy này). Cùng seed
sẽ cho lại đúng khoảng tin cậy bootstrap và p-value hoán vị đã nêu ở trên.
`methodology_version` của mọi điểm số trong lần chạy này là `qc_fusion.v1`
(`Agent/backend/qc/scoring/fusion.py`) — nếu công thức chấm điểm sản phẩm đổi
version, kết quả kiểm định này cần chạy lại.

## 6. Mã nguồn

- `Agent/backend/research/splitting.py` — chia theo thời gian, không rò rỉ.
- `Agent/backend/research/outcomes.py` — chỉ số kết quả thật từ lệnh đã chốt.
- `Agent/backend/research/statistics.py` — Spearman, bootstrap CI, mốc hoán vị.
- `Agent/backend/research/dataset.py` — đọc + parse ledger bằng đúng parser
  sản phẩm.
- `Agent/backend/research/shadow_scoring.py` — điểm nối vào
  `RiskSupervisionPipeline` thật (thư mục dữ liệu "bóng", xem mục 2.3).
- `Agent/none/scripts/validate_out_of_sample.py` — script chạy đầu-cuối.
- `Agent/none/test/test_research_splitting.py`,
  `Agent/none/test/test_research_outcomes.py`,
  `Agent/none/test/test_research_statistics.py` — test cho phần logic thuần.
