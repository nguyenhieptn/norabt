# MCP Server: Risk Supervisor cho AI Agent

`Agent/backend/agent_server.py` đóng gói 3 bước chấm điểm rủi ro bot copy-trading
OKX (market observation → bot/MCP analytics → QC fusion) thành 6 MCP tool, để
Claude Code, OKX Agent Trade Kit hoặc bất kỳ MCP client nào gọi trực tiếp thay vì
đọc JSON tay.

File này đặt tên `agent_server.py` (không phải `mcp_server.py`) để không gây
nhầm lẫn với package nội bộ `Agent/backend/mcp/` (Logic 2, không liên quan gì
tới giao thức MCP).

## Chạy server

Luôn chạy từ thư mục gốc repo (`/home/ubuntu/norabt`), vì import trong dự án là
`Agent.backend...`:

```bash
cd /home/ubuntu/norabt
python3 -m Agent.backend.agent_server
```

Mặc định server dùng **stdio transport** — không mở cổng mạng, giao tiếp qua
stdin/stdout theo chuẩn MCP local. Một MCP client (Claude Code, Claude
Desktop, ...) tự khởi động và tắt tiến trình này, người dùng không cần chạy
tay trừ khi debug.

Cài dependency trước nếu môi trường chưa có:

```bash
python3 -m pip install -r Agent/requirements.txt
```

### stdio hay HTTP: dùng cái nào

Server hỗ trợ hai transport qua cờ `--transport`:

| Transport | Khi nào dùng | Ai chạy tiến trình |
|---|---|---|
| `stdio` (mặc định) | Client và server chạy **cùng một máy** — Claude Code, Claude Desktop chạy trên máy dev/máy chủ này. Không mở cổng mạng nào, không cần lo xác thực từ xa. | Client tự spawn và tắt tiến trình qua `.mcp.json`/`claude mcp add`. |
| `http` (streamable HTTP) | Client ở **máy khác**, ví dụ đưa agent lên OKX AI Marketplace — chính OKX cũng yêu cầu HTTP (`claude mcp add onchainos-mcp https://... -t http`), stdio không làm được việc này vì cần chung máy. | Người vận hành tự khởi động và giữ tiến trình chạy (systemd, docker, ...); nhiều client có thể kết nối tới cùng một server. |

Nói ngắn gọn: **còn dùng trên máy mình thì giữ stdio (mặc định, không đổi gì
cả)**; **muốn agent gọi được từ xa/lên marketplace thì mới chuyển sang
`--transport http`**.

## Chạy HTTP (streamable HTTP transport)

```bash
cd /home/ubuntu/norabt
python3 -m Agent.backend.agent_server --transport http
# hoặc chỉ định host/port:
python3 -m Agent.backend.agent_server --transport http --host 127.0.0.1 --port 8765
```

Mặc định `--host 127.0.0.1` (chỉ máy này gọi được) và `--port 8765`. Đây là
lựa chọn **an toàn theo mặc định**: server này trả về đánh giá rủi ro và sẽ
sớm gắn thanh toán, nên không tự mở ra mọi interface mạng.

Muốn public ra ngoài (ví dụ đứng sau reverse proxy để đưa lên marketplace),
người vận hành phải tự khai `--host 0.0.0.0`. Khi đó server in ra một **cảnh
báo tiếng Việt** trên stderr, vì server chưa có cơ chế xác thực:

```bash
python3 -m Agent.backend.agent_server --transport http --host 0.0.0.0 --port 8765
```

```
CẢNH BÁO: server đang lắng nghe trên MỌI interface mạng (0.0.0.0) và CHƯA có
cơ chế xác thực -- bất kỳ máy nào truy cập được cổng 8765 đều gọi được toàn bộ
tool. Chỉ dùng khi đã có reverse proxy/tường lửa/xác thực đáng tin cậy phía
trước; nếu không, hãy dùng --host 127.0.0.1 (mặc định) hoặc một địa chỉ nội bộ.
```

Về mặt kỹ thuật, `--transport http` gọi `MCPServer.run(transport=
"streamable-http", host=..., port=...)` của SDK `mcp` — hàm này tự dựng một
Starlette app rồi phục vụ bằng `uvicorn` (cả hai đã là dependency có sẵn của
`mcp`, không cài thêm gì). Cờ CLI dùng chữ `http` (không phải
`streamable-http` như tên transport nội bộ của SDK) để khớp với cách
`claude mcp add ... -t http` gọi tên transport.

### Cắm HTTP server vào Claude Code (client ở xa)

```bash
claude mcp add okx-risk-supervisor http://<host>:<port>/mcp -t http
```

Đường dẫn mặc định là `/mcp` (ví dụ `http://127.0.0.1:8765/mcp` khi chạy local
để thử). Cách này dùng khi client và server **không** ở cùng máy — nếu vẫn
đang chạy trên cùng máy thì cách `claude mcp add ... -- python3 -m
Agent.backend.agent_server` (stdio, xem bên dưới) vẫn đơn giản hơn.

## Cắm vào Claude Code

Cách 1 — dùng lệnh `claude mcp add` (khuyến nghị, tự ghi vào cấu hình MCP của
Claude Code):

```bash
claude mcp add okx-risk-supervisor -- python3 -m Agent.backend.agent_server
```

Chạy lệnh này từ `/home/ubuntu/norabt` để Claude Code ghi đúng working
directory, hoặc thêm `--cwd /home/ubuntu/norabt` nếu chạy từ nơi khác.

Cách 2 — khai báo tay trong `.mcp.json` ở gốc repo:

```json
{
  "mcpServers": {
    "okx-risk-supervisor": {
      "command": "python3",
      "args": ["-m", "Agent.backend.agent_server"],
      "cwd": "/home/ubuntu/norabt"
    }
  }
}
```

## Bảng tool

| Tool | Tham số | Tốc độ | Việc nó làm |
|---|---|---|---|
| `list_assets` | *(không)* | Nhanh (đọc thư mục) | Liệt kê asset có dữ liệu crawl, kèm venue CEX/DEX |
| `list_bots` | `asset`, `venue_type` | Nhanh (đọc `overview.json`) | Liệt kê bot của một asset: folder name, nick name, unique code |
| `list_assessed_bots` | `verdict` (tùy chọn) | Nhanh (đọc `data/assessment/index.json`) | Liệt kê bot đã QC chấm điểm, lọc theo xếp loại nếu cần |
| `get_assessment` | `unique_code` | Nhanh (đọc `assessment.json`) | Đọc điểm số + **bản khuyến nghị đầy đủ (tiếng Anh)** của một bot đã chấm |
| `assess_bot` | `asset`, `bot_folder_name`, `venue_type` (mặc định `CEX`) | **Chậm** — chạy pipeline thật (~1.5-5 giây, xem đo lường bên dưới) | Chạy Logic 1→2→3 sống cho một bot, không ghi lịch sử ra đĩa |
| `get_market` | `symbol`, `venue_type` (mặc định `CEX`) | Nhanh (~0.1 giây) | Chạy Logic 1 sống: chuẩn hoá dữ liệu market đã crawl thành `MarketResult` đầy đủ |

`venue_type` chỉ nhận `CEX` hoặc `DEX` (không phân biệt hoa/thường ở input,
nhưng lỗi và log luôn dùng chữ hoa). `verdict` chỉ nhận một trong SÁU giá trị
hệ thống thật sự sinh ra (xem `VALID_VERDICTS` trong
`Agent/backend/agent_server.py` — nguồn duy nhất):

| Nhãn | Nghĩa |
|---|---|
| `DRAWDOWN: LOW · QUALITY: GOOD` | sụt vốn thấp, chất lượng tốt |
| `DRAWDOWN: LOW · QUALITY: WEAK` | sụt vốn thấp nhưng chất lượng yếu |
| `DRAWDOWN: HIGH · QUALITY: GOOD` | chất lượng tốt nhưng sụt vốn cao |
| `DRAWDOWN: HIGH · QUALITY: WEAK` | sụt vốn cao và chất lượng yếu |
| `HIDDEN RISK` | số liệu bề mặt che rủi ro — cờ ưu tiên, đè lên hai trục |
| `INSUFFICIENT EVIDENCE` | bằng chứng quá mỏng để kết luận |

Nhãn là HAI TRỤC (sụt vốn × chất lượng), không phải một thang bốn bậc: một
bot có thể chất lượng tốt mà vẫn sụt vốn cao, và thang một chiều cũ
(`AN TOÀN`/`TIỀM NĂNG`/`TIỀM ẨN`/`NGUY HIỂM`) đã bị bỏ — không còn sinh ra ở
đâu trong hệ thống.

### Đo tốc độ thật (yêu cầu nghiệm thu)

Đo trực tiếp trên dữ liệu có sẵn trong `Agent/data/` (không qua giao thức MCP,
đo thời gian gọi thẳng `RiskSupervisionPipeline.run()` /
`MarketService.get_market_result()` mà `assess_bot`/`get_market` gọi bên
trong):

| Bot / symbol | Tool | Thời gian |
|---|---|---|
| `MU / bot_BB3398A957270A39` (CEX) | `assess_bot` | 3.47s |
| `ETH / bot_F6476365DB0D09A3` (CEX) | `assess_bot` | 4.76s |
| `BTC / bot_E5513524191E576E` (CEX) | `assess_bot` | 1.55s |
| `BTC` (CEX) | `get_market` | 0.10s |
| `ETH` (CEX) | `get_market` | 0.10s |

`assess_bot` chạy 1.5-5 giây tùy số lượng lệnh trong sổ (Monte Carlo bootstrap
+ toàn bộ các lens QC), **dưới ngưỡng 60 giây** nên không cần cache hay chạy
nền — giữ nguyên như yêu cầu. `get_market` luôn dưới 0.2 giây vì chỉ đọc và
chuẩn hoá file JSON đã crawl sẵn, không mô phỏng.

## Nguyên tắc an toàn

- **Fail-closed**: bot/asset/symbol chưa có dữ liệu → lỗi nói rõ
  đang thiếu gì (ví dụ: "Asset X chưa có dữ liệu bot trên CEX ... cần crawl
  trước"), không bao giờ trả danh sách rỗng giả vờ là "không có rủi ro".
- **Không tool nào tự crawl.** Thiếu dữ liệu là lỗi, không phải lý do để tự
  động chạy crawler (crawler có rate limit, mất nhiều phút, phải chạy tay).
- **Input được coi là không tin cậy**: `asset`, `bot_folder_name`,
  `venue_type`, `symbol`, `unique_code` đều bị whitelist ký tự
  (`A-Za-z0-9_.-`) và chặn `..`, `/`, `\` trước khi chạm tới bất kỳ đường dẫn
  file nào.
- **`assess_bot` không ghi file.** Gọi với `persist_history=False`, nên gọi
  lặp lại nhiều lần (agent thử nhiều kịch bản) không làm phình
  `data/state/assessments/`.

## Ví dụ hỏi-đáp thực tế

**Câu hỏi:** "Trong các bot đã chấm điểm, bot nào đang nguy hiểm?"

AI agent gọi `list_assessed_bots(verdict="HIDDEN RISK")`, nhận về danh sách
kèm `unique_code`. Sau đó gọi `get_assessment(unique_code=...)` cho từng bot
để lấy bản khuyến nghị đầy đủ. Ví dụ THẬT, chép từ
`data/assessment/dex/WBTC/bot/King_GG__811997770117827919/assessment.json`
(schema `bot_assessment.v3`):

```json
{
  "schema_version": "bot_assessment.v3",
  "bot": {
    "nick_name": "King_GG",
    "unique_code": "811997770117827919",
    "slot": "DEX/WBTC",
    "rank_in_cohort": 1
  },
  "recommendation": {
    "verdict": "HIDDEN RISK",
    "action": "EMERGENCY_STOP",
    "quality_score": 59.6,
    "risk_score": 100.0,
    "confidence": 60.3,
    "reasons": "The surface numbers hide risk: unrealised loss equals 43% of capital",
    "text": ["... (các đoạn giải thích đầy đủ) ..."]
  },
  "expert_assessment": "... (đoạn nhận định do mô hình ngôn ngữ viết) ..."
}
```

AI agent đọc thẳng `recommendation.text` (danh sách đoạn văn) hoặc
`expert_assessment` để trả lời người dùng, không cần tự diễn giải các con số
thô. **Toàn bộ chuỗi trả về là TIẾNG ANH** — sản phẩm phục vụ marketplace
toàn cầu; các khoá tiếng Việt của schema v1/v2 (`khuyen_nghi`, `ket_luan`,
`diem_rui_ro`, `text_full`...) đã bị đổi tên và không còn tồn tại.

**Câu hỏi mang tính giả định:** "Nếu bot Y chạy đến hôm nay thì rủi ro thế
nào?" — khi bot chưa có trong `data/assessment/index.json` (chưa qua batch
report), agent gọi `assess_bot(asset="MU", bot_folder_name="bot_...",
venue_type="CEX")` để chạy trực tiếp, chấp nhận chờ vài giây.
