# Đưa OKX Risk Supervisor MCP server lên OKX AI Marketplace (okx.ai)

Tài liệu khảo sát kỹ thuật + code cho việc bán 6 tool chấm điểm rủi ro
bot copy-trading (`Agent/backend/agent_server.py`) theo lượt gọi trên OKX AI
Marketplace, thanh toán qua chuẩn x402.

**Trạng thái hiện tại (đã cập nhật):** cổng thanh toán x402 đã được hiện
thực thật và nối vào `agent_server.py` (Phần 2), có test bao phủ đầy đủ, và
mặc định vẫn TẮT (`X402_ENABLED=false`). Cái **chưa** làm được, vì chưa có
credential thật và task này chủ động không được phép gọi mạng/đăng ký gì:
gọi facilitator OKX thật (mọi test đều mock), test trên X Layer
Testnet/Mock Merchant, và toàn bộ các bước hành chính (đăng ký ASP, tạo ví,
lấy API key thật) ở Phần 3. Mục Phần 4 (pháp lý) vẫn là phần quan trọng nhất
cần đọc trước khi thu tiền thật.

## Phần 1 -- Khảo sát kỹ thuật

### 1.1 SDK Python của OKX cho x402/service-seller: CÓ THẬT, cài được

Trang tài liệu OKX
(https://web3.okx.com/onchainos/dev-docs/payments/service-seller-sdk) nói có
SDK Python. Không chỉ tin lời tài liệu -- đã tải thật gói này về máy và đọc
mã nguồn bên trong:

```bash
pip download okxweb3-app-x402==0.1.1 --no-deps -d .
python3 -m zipfile -e okxweb3_app_x402-0.1.1-py3-none-any.whl .
```

**Kết quả xác nhận:**

- Tên gói PyPI thật: **`okxweb3-app-x402`**, bản mới nhất `0.1.1`
  (https://pypi.org/project/okxweb3-app-x402/). Cài bằng:
  ```bash
  pip install okxweb3-app-x402
  ```
- Gói này **import dưới tên module `x402`** (không phải `okxweb3_app_x402`)
  -- đây thực chất là **bản fork của OKX từ chính SDK x402 gốc** (cùng cấu
  trúc file với gói `x402`/`og-x402` của "x402 Foundation", cộng thêm 3 file
  riêng của OKX: `x402/http/okx_auth.py`, `x402/http/okx_facilitator_client.py`,
  `x402/mechanisms/evm/okx_signer.py`).
- **Cảnh báo tên trùng:** gói `x402` chính chủ (x402 Foundation,
  `pip install x402`) CŨNG import dưới tên module `x402`. Hai gói **không thể
  cài chung một môi trường** -- cài `okxweb3-app-x402` là cách duy nhất để có
  bản hỗ trợ facilitator OKX (`OKXFacilitatorClient`, `OKXAuthProvider`).
- Dependency bắt buộc của gói: `pydantic>=2.0.0`, `nest-asyncio>=1.6.0`,
  `typing-extensions>=4.0.0`. Muốn dùng FastAPI middleware, EVM signer, v.v.
  thì cài thêm qua extras: `pip install "okxweb3-app-x402[fastapi,evm]"`.
- Trạng thái: PyPI ghi "Development Status :: 3 - Alpha".

**Kết luận Q1: có SDK Python thật, cài được thật, đã tự tay tải và đọc mã
nguồn để xác minh (không chỉ tin theo văn bản OKX).**

### 1.2 Thư viện x402 độc lập (không phải của OKX)

Có, và đây mới là chuẩn gốc mà OKX fork ra:

- **`x402`** (PyPI, https://pypi.org/project/x402/) -- bản `2.22.0`, phát
  hành 4/9/2026, tác giả "x402 Foundation" (maintainer `erik_cb`, tiền thân
  từ Coinbase -- repo gốc từng ở `github.com/coinbase/x402`, nay chuyển sang
  `github.com/x402-foundation/x402`). Giấy phép MIT, hỗ trợ Python 3.10+.
  Cung cấp client/server/facilitator transport-agnostic, cả sync và async,
  hỗ trợ EVM/Solana/TON.
- **`og-x402`** (PyPI) -- cùng tác giả "x402 Foundation", bản `2.15.0`, có
  vẻ là một lần publish trước dưới tên khác (có thể do tranh chấp/đổi tên gói
  `x402` trên PyPI). Không có lý do dùng gói này thay vì `x402` chính thức.

**Đánh giá độ tin cậy:** đây KHÔNG phải một lib cộng đồng nhỏ lẻ -- nó là
SDK tham chiếu chính thức của chuẩn x402 (do chính tổ chức đứng sau chuẩn
này -- x402 Foundation, kế thừa từ Coinbase -- xuất bản), và OKX fork trực
tiếp từ nó để thêm phần facilitator riêng. Vẫn ở giai đoạn Alpha (tự khai
trên PyPI), interface có thể còn đổi. Có ví dụ Python thật trong chính repo
(xem 1.5).

### 1.3 Credential cần gì, và làm được gì khi CHƯA có

| Credential | Cần cho việc gì | Có thể phát triển/test khi chưa có? |
|---|---|---|
| Địa chỉ ví EVM nhận tiền (`payTo`) | Khai trong mọi `PaymentRequirements` | Không cần thật để dựng cấu trúc payload (dùng địa chỉ giả `0x000...AA` như trong test); cần thật để nhận tiền thật |
| Địa chỉ hợp đồng token (`asset`, ví dụ USDC trên X Layer) | Khai trong `PaymentRequirements.asset` | Tương tự -- giả lập được cho cấu trúc, cần thật để verify/settle thật |
| OKX Developer Portal API key/secret/passphrase | Ký request `OK-ACCESS-*` gọi facilitator OKX thật (`/api/v6/pay/x402/verify`, `/settle`) | **Không** -- không có cách nào gọi facilitator thật mà không có 3 giá trị này |
| Đăng ký ASP (Agentic Service Provider) tại okx.ai | Được list lên marketplace, được OKX route traffic tới | **Không** -- đây là bước hành chính, không có API để tự động hoá |
| Agentic Wallet | Ví ký giao dịch phía client khi test luồng thanh toán thật | **Không cần cho phía server** (server chỉ nhận tiền, không tự trả); cần nếu muốn tự đóng vai client để test end-to-end |

**Có thể làm được khi CHƯA có gì ở trên:** dựng đúng cấu trúc dữ liệu
`PaymentRequirements`/`PaymentRequired`/`PaymentPayload`, sinh đúng response
402 (header + body), decode đúng header client gửi lên -- tất cả những việc
này không cần credential thật, chỉ cần biết đúng *hình dạng* của giao thức
(xem 1.4). Đây chính xác là những gì `Agent/backend/payments/x402.py` làm.

**Testnet:** OKX cung cấp X Layer Testnet (network id `eip155:1952`, đổi từ
`eip155:196` là chuyển sang testnet), X Layer Faucet để lấy token test, và
một "Mock Merchant" mẫu để thử luồng mà không cần ví thật. Tài liệu OKX có
nhắc tới nhưng **chưa tự đi thử** (task yêu cầu không gọi API OKX cần xác
thực, không tạo ví) -- việc thử testnet thật để lại cho bước sau, có phê
duyệt riêng.

### 1.4 Giao thức 402 chính xác (đọc trực tiếp từ mã nguồn `okxweb3-app-x402`)

Phần này **không dựa vào mô tả trong tài liệu OKX** (mô tả bằng lời của
trang docs không nhất quán khi tra qua công cụ đọc trang, có lúc gọi sai
tên header) -- toàn bộ chi tiết dưới đây được trích trực tiếp từ code đã tải
về: `x402/http/constants.py`, `x402/http/utils.py`, `x402/schemas/payments.py`,
`x402/schemas/responses.py`, `x402/schemas/v1.py`.

**Header HTTP (giao thức V2, mặc định của bản fork OKX):**

| Header | Chiều | Nội dung |
|---|---|---|
| `PAYMENT-REQUIRED` | Server -> Client | base64(JSON của `PaymentRequired`) |
| `PAYMENT-SIGNATURE` | Client -> Server | base64(JSON của `PaymentPayload`) |
| `PAYMENT-RESPONSE` | Server -> Client (sau khi settle) | base64(JSON của `SettleResponse`) |

(Có bản V1 legacy dùng header `X-PAYMENT`/`X-PAYMENT-RESPONSE` với cấu trúc
JSON hơi khác -- `scheme`/`network` nằm ở top-level thay vì trong `accepted`,
và field tiền là `maxAmountRequired` thay vì `amount`. Module trong repo này
chỉ triển khai V2.)

**Bước 1 -- Server trả 402:**

```
HTTP/1.1 402 Payment Required
Content-Type: application/json
PAYMENT-REQUIRED: <base64 JSON>

{}
```

Base64 giải mã ra (`PaymentRequired`):

```json
{
  "x402Version": 2,
  "resource": {"url": "...", "description": "...", "mimeType": "application/json"},
  "accepts": [
    {
      "scheme": "exact",
      "network": "eip155:196",
      "asset": "<địa chỉ hợp đồng USDC trên X Layer>",
      "amount": "10000",
      "payTo": "<địa chỉ ví nhận tiền>",
      "maxTimeoutSeconds": 60,
      "extra": {}
    }
  ]
}
```

(`amount` là số nguyên ở đơn vị nhỏ nhất của token -- USDC 6 số thập phân
nên "10000" = 0.01 USDC = giá "$0.01".)

**Bước 2 -- Client trả tiền, gửi lại request với bằng chứng:**

```
GET /tool/assess_bot
PAYMENT-SIGNATURE: <base64 JSON>
```

Base64 giải mã ra (`PaymentPayload`):

```json
{
  "x402Version": 2,
  "payload": { "...tuỳ scheme, ví dụ chữ ký EIP-3009 cho scheme exact..." },
  "accepted": { "...chính là PaymentRequirements ở bước 1 mà client chọn..." }
}
```

**Bước 3 -- Server verify.** Theo mã nguồn, server gọi facilitator:

```
POST {facilitator_base_url}/verify   (hoặc /api/v6/pay/x402/verify với OKX)
Body: {"x402Version": 2, "paymentPayload": <PaymentPayload>, "paymentRequirements": <PaymentRequirements>}
```

trả về:

```json
{"isValid": true, "payer": "0x...", "invalidReason": null, "invalidMessage": null}
```

Gọi facilitator của OKX cần ký request bằng HMAC-SHA256 (đọc trực tiếp từ
`x402/http/okx_auth.py`):

```
prehash = timestamp + method + path + body
signature = base64(HMAC_SHA256(secret_key, prehash))
headers = {
  "OK-ACCESS-KEY": api_key,
  "OK-ACCESS-SIGN": signature,
  "OK-ACCESS-TIMESTAMP": timestamp,   # ISO UTC, ví dụ 2025-03-30T12:00:00.000Z
  "OK-ACCESS-PASSPHRASE": passphrase,
}
```

Endpoint OKX thật (từ `x402/http/okx_facilitator_client.py`):
`https://web3.okx.com/api/v6/pay/x402` + `/verify` hoặc `/settle`, bọc trong
envelope `{code, data, msg}` kiểu chuẩn OKX (code != 0 nghĩa là lỗi).

**Bước 4 -- Server settle** (nếu verify hợp lệ): `POST .../settle` với cùng
body cộng `syncSettle: true/false`, nhận về `SettleResponse
{success, transaction, network, payer, ...}`, mã hoá vào header
`PAYMENT-RESPONSE` gửi kèm response 200 thật.

### 1.5 Ví dụ code phía server (đã tìm được, có link thật)

- FastAPI: https://github.com/x402-foundation/x402/tree/main/examples/python/servers/fastapi
- Flask: https://github.com/x402-foundation/x402/tree/main/examples/python/servers/flask
- Client (requests): https://github.com/coinbase/x402/tree/main/examples/python/clients/requests
- Client (httpx): https://github.com/coinbase/x402/tree/main/examples/python/clients/httpx
- README tổng quan chuẩn (kèm link `specs/`): https://github.com/coinbase/x402/blob/main/README.md

(Repo `coinbase/x402` và `x402-foundation/x402` có vẻ là cùng một dự án ở
hai thời điểm/tên tổ chức khác nhau -- cả hai URL trên còn truy cập được tại
thời điểm khảo sát.)

Ví dụ OKX minh hoạ trong tài liệu service-seller-sdk (FastAPI, route
`GET /weather` giá `"$0.1"` trên `eip155:196`):

```python
from x402.http import OKXFacilitatorClient, OKXFacilitatorConfig
from x402.http.middleware.fastapi import PaymentMiddlewareASGI
from x402.mechanisms.evm.exact.server import ExactEvmScheme
from x402.server import x402ResourceServer
```

---

## Phần 2 -- Khung code đã dựng (cập nhật: verify thật + nối vào agent_server.py)

File chạm tới trong lượt này: `Agent/backend/payments/x402.py` (sửa),
`Agent/backend/agent_server.py` (sửa), `Agent/test/test_payments.py`,
`Agent/test/test_agent_server.py`, tài liệu này. Không đụng
`sources/*`, `mcp/service.py`, `market/service.py`, `live/*`,
`run_report.py`, `run_compare.py`, `qc/*`, và không đụng
`Agent/backend/okx/client.py`/`credentials.py` (chỉ *import*, xem dưới).

- **Mặc định vẫn TẮT**: cờ `X402_ENABLED`, mặc định `false`. Toàn bộ 520 test
  có sẵn của dự án (không set biến này) chạy y hệt trước khi có tính năng
  này -- đã xác nhận lại bằng `python3 -m pytest Agent/test -q` sau khi làm
  xong (561 passed = 520 cũ + test x402 mới).
- **Không dependency bắt buộc mới**: vẫn chỉ thư viện chuẩn
  (`base64`, `json`, `dataclasses`, `decimal`, `hashlib`, `threading`, `time`)
  cộng với `Agent.backend.okx.client.OkxClient` đã có sẵn trong repo (xem
  mục "Tái dùng chữ ký OK-ACCESS-*" dưới đây).
- **`TOOL_PRICING`**: không đổi, dict giá cho đúng 6 tool (xem bảng giá).
- **`build_payment_requirements()` / `build_402_response()`**: không đổi
  logic, vẫn dựng đúng cấu trúc `PaymentRequirements`/`PaymentRequired`.
- **`PaymentPayload.decode_header()`**: không đổi -- parse thuần cú pháp.

### `verify_payment()` -- giờ là xác minh THẬT

Gọi facilitator OKX thật qua HTTP (`POST {facilitator_base_url}/api/v6/pay/x402/verify`),
ký request bằng HMAC-SHA256 `OK-ACCESS-*` **tái dùng nguyên `Agent/backend/okx/client.py`**:
`x402.py` dựng một `OkxClient(credentials=OkxCredentials(api_key=OKX_X402_API_KEY, ...,
simulated=False), base_url=X402_FACILITATOR_BASE_URL)` rồi gọi `.post(...)` --
không có một dòng HMAC/prehash nào được viết lại trong `x402.py`. `simulated=False`
được set cứng vì facilitator không phải sàn demo trading của OKX; cờ
`OKX_SIMULATED` (dùng cho trading key) không được phép rò vào đây.

Thứ tự kiểm tra trong `verify_payment(payment_signature_header, requirements, settings=None, facilitator_client=None)`:

1. `X402_ENABLED` tắt -> `RuntimeError`.
2. Thiếu `PAYMENT-SIGNATURE` header -> `ValueError`.
3. Header không giải mã được thành `PaymentPayload` hợp lệ -> `ValueError`
   (thuần cú pháp, không chứng minh gì về thanh toán).
4. Thiếu bất kỳ biến nào trong `X402_PAY_TO_ADDRESS`, `X402_ASSET_ADDRESS`,
   `OKX_X402_API_KEY`, `OKX_X402_API_SECRET`, `OKX_X402_API_PASSPHRASE`
   -> **`X402ConfigError`** (subclass `RuntimeError`). **Không có đường nào
   từ đây quay lại coi như đã trả tiền.**
5. So khớp cục bộ `payload.accepted` (những gì client khai đã trả) với
   `requirements` (những gì server này thực sự yêu cầu cho lần gọi này) --
   `scheme`/`network`/`asset`/`amount`/`payTo` phải khớp tuyệt đối. Sai bất kỳ
   trường nào -> trả về `VerifyResult(is_valid=False, invalid_reason=
   "requirements_mismatch", ...)`, **không gọi facilitator** (đỡ một lượt
   mạng cho một request rõ ràng sai, và đảm bảo facilitator không thể "cho
   qua" một giao dịch mà chính server đã biết là sai giá/sai ví).
6. Kiểm tra chống phát lại (xem mục riêng dưới) -- nếu fingerprint của
   payload đã dùng rồi -> `VerifyResult(is_valid=False, invalid_reason="replay")`.
7. Gọi facilitator thật (hoặc `facilitator_client` được inject cho test).
   Bắt các lỗi từ `OkxClient`:
   - `OkxTransportError` (mạng lỗi/timeout, sau khi `OkxClient` đã tự retry) ->
     **`X402FacilitatorError`**.
   - `OkxApiError` (facilitator trả lỗi ở tầng envelope OKX, `code != "0"`) ->
     **`X402FacilitatorError`**.
   - `OkxCredentialsMissing` (phòng thủ, lẽ ra không thể xảy ra vì bước 4 đã
     chặn) -> `X402ConfigError`.
8. Parse response. Chấp nhận cả hai hình dạng: `{isValid, ...}` trực tiếp,
   hoặc bọc trong envelope OKX `{code, data: {isValid, ...}, msg}` (tài liệu
   OKX không nói rõ `/verify` dùng hình dạng nào -- xem mục "Điểm chưa chắc
   chắn" bên dưới). `isValid` bắt buộc phải là `bool` thật (không chấp nhận
   chuỗi/số truthy). Không parse được -> **`X402FacilitatorError`**.
9. `isValid: false` -> trả `VerifyResult(is_valid=False, invalid_reason=...,
   invalid_message=...)` y nguyên từ facilitator (hết hạn, sai chữ ký, v.v.).
10. `isValid: true` -> ghi nhận fingerprint vào replay guard (atomic, khoá
    lại một lần nữa để tránh race hai request cùng payload chạy song song),
    trả `VerifyResult(is_valid=True, payer=...)`.

**Duy nhất bước 10 tạo ra `is_valid=True`, và nó chỉ chạy được sau một cuộc
gọi HTTP thật (hoặc `facilitator_client` giả lập trong test) trả lời
`isValid: true`.** Mọi nhánh khác raise hoặc trả `is_valid=False`. Test
`test_verify_payment_exhaustive_branches_never_fake_a_paid_result` trong
`Agent/test/test_payments.py` duyệt qua từng nhánh này và khẳng định điều đó.

### Chống phát lại (replay) -- GIỚI HẠN ĐÃ BIẾT

`x402.py` giữ một cache fingerprint (SHA-256 của toàn bộ `PaymentPayload`,
canonical JSON) trong bộ nhớ tiến trình (`_used_payment_fingerprints`, khoá
bằng `threading.Lock`, TTL 1 giờ). Một payload đã verify thành công không
verify lại được lần hai trong cùng tiến trình.

**Đây KHÔNG phải một hàng rào chống phát lại đầy đủ cho production:**
- Chỉ trong bộ nhớ một tiến trình -- nếu chạy nhiều worker (nhiều process,
  nhiều máy) hoặc restart server, cache mất, phát lại giữa các worker/khi
  restart **không bị chặn**.
- Cần một kho dùng chung (Redis, một bảng DB khoá theo fingerprint, TTL) cho
  bất kỳ triển khai multi-worker/multi-instance thật nào trước khi thu tiền
  thật -- **chưa làm trong lượt này**, ghi rõ ở đây để không ai tưởng nhầm
  đây là xong.
- `reset_replay_guard_for_tests()` chỉ dùng cho test, không được gọi từ
  code production.

### Nối vào `agent_server.py`

Mỗi trong 6 tool (`list_assets`, `list_bots`, `list_assessed_bots`,
`get_assessment`, `assess_bot`, `get_market`) giờ nhận thêm tham số
`ctx: Context` (SDK `mcp.server.mcpserver.Context`) và gọi
`_require_payment(ctx, "<tool_name>")` làm dòng đầu tiên trong thân hàm.

`_require_payment()`:
- **No-op tuyệt đối** khi `X402_ENABLED` không phải `"true"` -- không đụng
  `ctx`, không đọc thêm biến môi trường nào khác, không gọi mạng. Đây là lý
  do 520 test cũ không cần sửa gì.
- Khi bật: build `PaymentRequirements` cho tool đó; nếu ví/token server chưa
  cấu hình -> `ToolError` (từ chối, không chạy tool "miễn phí" vì server cấu
  hình dở dang).
- Đọc header `PAYMENT-SIGNATURE` từ `ctx.headers` (xem mục SDK dưới đây).
  Không có -> `ToolError` tiếng Việt, nêu đúng giá của tool đó, kèm giá trị
  base64 `PAYMENT-REQUIRED` thật (xem "Giới hạn kỹ thuật của SDK" ngay dưới
  để hiểu vì sao giá trị này nằm trong text lỗi thay vì một header HTTP
  402 thật).
- Có header -> gọi `x402.verify_payment()`. Bất kỳ exception nào từ đó
  (`RuntimeError`/`ValueError`/`X402ConfigError`/`X402FacilitatorError`) ->
  `ToolError` bọc lại, tool KHÔNG chạy.
- `verify_payment()` trả `is_valid=False` -> `ToolError` nêu
  `invalid_reason`/`invalid_message`, tool KHÔNG chạy.
- `verify_payment()` trả `is_valid=True` -> `_require_payment()` return bình
  thường (không raise gì), thân hàm tool chạy tiếp như cũ.

### Giới hạn kỹ thuật của SDK (`mcp` 2.2.0) -- đọc trước khi tưởng "402 thật"

Đã đọc trực tiếp mã nguồn SDK cài trong môi trường này
(`/home/ubuntu/anaconda3/lib/python3.14/site-packages/mcp/`) để trả lời hai
câu hỏi task đặt ra, không đoán:

**1. Tool handler có đọc được HTTP header của request không? CÓ.**
`mcp.server.mcpserver.Context.headers` (`mcp/server/mcpserver/context.py`)
là một property đọc `self.request_context.request.headers`. Với transport
HTTP (`streamable-http`), `request` chính là đối tượng `starlette.requests.Request`
thật (gán ở `mcp/server/_streamable_http_modern.py:297` và
`mcp/server/streamable_http.py:250` qua `ServerMessageMetadata(request_context=request)`,
đọc lại ở `mcp/server/runner.py:_make_context`), nên `ctx.headers.get("PAYMENT-SIGNATURE")`
hoạt động thật, case-insensitive (kế thừa từ `Headers` của Starlette). Với
stdio, `request` là `None` nên `ctx.headers` là `None` -- **x402 không có ý
nghĩa qua stdio** vì không có khái niệm header; khi bật `X402_ENABLED=true`
mà gọi qua stdio, mọi tool trả phí sẽ luôn bị từ chối vì không thể đọc được
`PAYMENT-SIGNATURE` (fail-closed, không phải một lỗi).

Cách khai báo: thêm tham số `ctx: Context` (import từ `mcp.server.mcpserver`)
vào chữ ký hàm tool -- SDK tự phát hiện qua type hint
(`find_context_parameter`, `mcp/server/mcpserver/utilities/context_injection.py`)
và **loại tham số này khỏi JSON schema** của tool
(`Tool.from_function`'s `skip_names`, `mcp/server/mcpserver/tools/base.py`) --
đã tự kiểm chứng bằng cách in `input_schema` sau khi sửa: `ctx` không xuất
hiện, danh sách tham số bắt buộc với AI caller không đổi.

**2. Tool handler có đặt được HTTP status code / header tuỳ ý cho response
`tools/call` không? KHÔNG -- đã xác nhận bằng cách đọc mã nguồn, không đoán.**

Bằng chứng cụ thể:
- `mcp/server/mcpserver/server.py:_handle_call_tool` (dòng ~428-447): khi
  tool raise `ToolError`, hàm này **bắt lại và trả về `CallToolResult(...,
  is_error=True)`** -- đây là một **kết quả JSON-RPC thành công**
  (`JSONRPCResponse`), không phải `JSONRPCError`.
- `mcp/server/_streamable_http_modern.py:_write` (transport 2026-07-28) chỉ
  tra HTTP status từ bảng cố định `ERROR_CODE_HTTP_STATUS`
  (`mcp/shared/inbound.py`, chỉ map vài mã lỗi JSON-RPC cấp giao thức như
  parse-error/invalid-params sang 400/404) khi message là `JSONRPCError`;
  với `JSONRPCResponse` (trường hợp của mọi lỗi tool, kể cả `ToolError`),
  status luôn là `_OK_STATUS = 200`.
- Transport `streamable-http` "cũ" (`mcp/server/streamable_http.py`) cũng
  không có cơ chế nào khác cho việc này.
- Không có API nào trên `Context` để set response header/status -- đã tìm
  trong `Context`, `BaseContext`, `ServerRequestContext`, không có.

**Kết luận: không có cách nào từ bên trong một tool handler của SDK `mcp`
2.2.0 để khiến response `tools/call` mang HTTP status 402 hay một header
`PAYMENT-REQUIRED` thật.** Mọi `CallToolResult` -- lỗi hay không -- đều đi
kèm HTTP 200.

**Phương án thay thế đã chọn:** nhúng nguyên giá trị base64 của
`PAYMENT-REQUIRED` (y hệt những gì lẽ ra nằm trong header HTTP thật) vào
trong text của `ToolError`, cùng với giá tiền viết rõ bằng tiếng Việt. Một
client tuân thủ x402 có thể parse chuỗi `PAYMENT-REQUIRED=<base64>` ra khỏi
message lỗi và xử lý y như đã nhận được header thật. Đây là cách tiếp cận
gần nhất có thể làm được trong giới hạn của SDK hiện tại, **không phải**
một header HTTP 402 chuẩn -- đã đo bằng test thật
(`test_http_transport_rejects_unpaid_call_when_x402_enabled` trong
`Agent/test/test_agent_server.py`, gọi qua HTTP transport thật, không mock).

Phương án khác đã cân nhắc và **không chọn**: thêm tham số `payment` vào
input schema của mỗi tool (client set giá trị này thay vì header). Bị loại
vì: (a) làm `payment` xuất hiện như một tham số nghiệp vụ trong schema mà
AI caller nhìn thấy, dễ nhầm là một phần logic của tool; (b) `ctx.headers`
đã đọc header thật được (xác nhận ở mục 1), nên hướng client -> server không
cần fallback này -- chỉ hướng server -> client (402 challenge) mới cần một
giải pháp thay thế, và nhúng vào message lỗi giữ nguyên được cả hai hướng
cùng dùng header, thay vì mỗi hướng một cơ chế khác nhau.

### Điểm CHƯA CHẮC CHẮN trong đặc tả (ghi rõ theo yêu cầu, không đoán)

1. **Hình dạng response của `/verify`**: tài liệu OKX không nói rõ liệu
   endpoint này trả `{isValid, ...}` trực tiếp hay bọc trong envelope chuẩn
   OKX `{code, data, msg}` như mọi REST endpoint v5 khác. `x402.py` chấp
   nhận cả hai (xem `_extract_verify_verdict`), nhưng chưa có cách xác nhận
   thật vì chưa có credential để gọi facilitator thật.
2. **Hạn dùng (expiry) của payload**: `PaymentRequirements` không có trường
   timestamp phát hành, và `payload.payload` (phần đặc thù theo scheme, ví
   dụ chữ ký EIP-3009) là một blob không rõ cấu trúc với module này.
   `verify_payment()` **không tự parse/kiểm tra hạn dùng cục bộ** -- việc đó
   giao hoàn toàn cho facilitator qua `invalidReason` (ví dụ `"expired"`).
3. **Timeout/retry khi gọi facilitator**: tái dùng nguyên cấu hình
   `OKX_HTTP_TIMEOUT_SECONDS`/`OKX_HTTP_MAX_RETRIES` của `OkxClient` (mặc
   định 10s, 2 lần retry) vì chưa có lý do cụ thể để tách riêng cho
   facilitator -- có thể cần điều chỉnh khi có số liệu thật.
4. **Đặt tên biến môi trường merchant**: task gợi ý ví dụ
   `X402_MERCHANT_KEY/SECRET/PASSPHRASE`; lượt code trước đã đặt tên
   `OKX_X402_API_KEY/API_SECRET/API_PASSPHRASE` (khác `OKX_API_KEY` trading,
   đã có lý do rõ trong code + đã có test tham chiếu tên này). Lượt này
   **giữ nguyên tên cũ** thay vì đổi, để tránh phá vỡ test/tài liệu đã có
   một cách không cần thiết -- đây là quyết định tự đưa ra, ghi rõ ở đây
   để review nếu cần đổi tên.

Test: `Agent/test/test_payments.py` (59 test) + phần x402 trong
`Agent/test/test_agent_server.py` (test `_require_payment`, và 2 test qua
HTTP transport thật `test_http_transport_rejects_unpaid_call_when_x402_enabled`
/ `test_http_transport_runs_normally_when_x402_disabled`), bao phủ toàn bộ
danh sách "Test bắt buộc" của task này. Facilitator không bao giờ được gọi
thật trong test -- luôn qua `facilitator_client=` (test_payments.py) hoặc
`monkeypatch.setattr(x402, "verify_payment", ...)` (test_agent_server.py).

---

## Phần 3 -- Checklist lên marketplace

| # | Việc cần làm | Trạng thái | Ghi chú |
|---|---|---|---|
| 1 | Server có tool để bán (6 MCP tool) | **Đã có** | `Agent/backend/agent_server.py` |
| 2 | Server chạy được qua HTTP (không chỉ stdio) | **Đã có** | OKX yêu cầu HTTP để marketplace gọi từ xa |
| 3 | Tự host server (bắt buộc theo OKX) | **Chưa** | Cần server public, có domain/SSL, người vận hành tự chịu trách nhiệm |
| 4 | Cấu trúc dữ liệu giá + payload 402 | **Đã có** | `Agent/backend/payments/x402.py` |
| 5 | Verify thanh toán thật (gọi facilitator) | **Đã có code, chưa test được với credential thật** | `verify_payment()` gọi facilitator OKX thật qua `OkxClient`; test dùng `facilitator_client=` giả lập vì chưa có `OKX_X402_API_KEY/SECRET/PASSPHRASE` thật -- **chưa từng gọi mạng thật tới facilitator** |
| 6 | Nối `x402.py` vào `agent_server.py` | **Đã xong** | `_require_payment()`, xem Phần 2. 402 challenge nhúng trong `ToolError` message (không phải header HTTP thật) -- xem "Giới hạn kỹ thuật của SDK" |
| 6b | Chống phát lại (replay) | **Có, giới hạn** | Chỉ in-memory một tiến trình -- xem mục riêng ở Phần 2, cần nâng cấp lên kho dùng chung trước khi chạy multi-worker thật |
| 7 | Đăng ký ASP tại okx.ai | **Chưa -- cần người thật** | https://www.okx.ai/tutorial/asp (duyệt trong 24h theo tài liệu) |
| 8 | Tạo Agentic Wallet (ví nhận tiền) | **Chưa -- cần người thật** | Chưa tìm ra link portal cụ thể trong khảo sát này; xuất hiện trong docs OKX như một bước riêng, cần tra thêm khi đến bước này |
| 9 | Lấy API key/secret/passphrase từ OKX Developer Portal (biến `OKX_X402_API_KEY/API_SECRET/API_PASSPHRASE`) | **Chưa -- cần người thật** | Định dạng giống hệt OKX Trade API (`OK-ACCESS-*` HMAC-SHA256) nhưng đây là bộ key khác, không dùng chung với `OKX_API_KEY` hiện có trong `Agent/.env.example` |
| 9b | Ví/token nhận tiền (`X402_PAY_TO_ADDRESS`, `X402_ASSET_ADDRESS`) | **Chưa -- cần người thật** | Địa chỉ ví EVM thật trên X Layer + địa chỉ hợp đồng USDC (hoặc token OKX chỉ định) |
| 10 | Test trên X Layer Testnet + Mock Merchant | **Chưa** | Cần phê duyệt riêng trước khi chạy (theo ràng buộc "Heavy Run Approval" đã ghi trong bộ nhớ dự án) |
| 11 | Nâng cấp replay guard lên kho dùng chung (Redis/DB) nếu chạy multi-worker | **Chưa** | Xem mục "Chống phát lại" ở Phần 2 |
| 12 | Rà soát pháp lý §9.3 OKX API Agreement | **Chưa -- xem Phần 4, KHÔNG được bỏ qua** | |

---

## Bảng giá đề xuất cho 6 tool

| Tool | Giá đề xuất | Lý do |
|---|---|---|
| `list_assets` | $0.001 | Chỉ liệt kê thư mục dưới `data/`, không tính toán gì |
| `list_bots` | $0.001 | Đọc `overview.json` đã crawl sẵn cho một asset |
| `list_assessed_bots` | $0.001 | Đọc `data/assessment/index.json` |
| `get_assessment` | $0.002 | Đọc `assessment.json` một bot -- rẻ về compute nhưng đây mới là *sản phẩm thật* (bản khuyến nghị tiếng Việt đầy đủ) nên định giá nhỉnh hơn nhóm liệt kê |
| `get_market` | $0.005 | Chạy sống Logic 1 (chuẩn hoá dữ liệu market đã crawl), đo thật ~0.1 giây, không mô phỏng |
| `assess_bot` | $0.05 | Chạy sống toàn bộ Logic 1→2→3 kèm Monte Carlo bootstrap, đo thật 1.5-4.76 giây (xem `Agent/docs/mcp_server.md`) -- đắt nhất, gấp 10-50 lần nhóm đọc cache |

Đây là **giá đề xuất dựa trên chi phí compute tương đối**, chưa tính đến
biên lợi nhuận, phí facilitator, hay mức giá cạnh tranh trên marketplace --
cần điều chỉnh khi có dữ liệu thị trường thật.

---

## Phần 4 -- CẢNH BÁO PHÁP LÝ (đọc trước khi làm tiếp bất cứ điều gì)

**OKX API Agreement, điều §9.3, cấm dùng OKX API Services để vận hành
"signal service" hoặc "strategy marketplace" khi chưa có sự chấp thuận
bằng văn bản (written approval) từ OKX.**

Sản phẩm đang thăm dò ở đây -- bán quyền truy cập vào một dịch vụ *chấm điểm
rủi ro bot copy-trading dựa trên dữ liệu OKX* -- nằm rất gần, nếu không muốn
nói là trùng, với định nghĩa "signal service" trong điều khoản đó: nó đọc dữ
liệu từ OKX (qua `Agent/backend/okx/client.py` và crawler), phân tích, rồi
bán bản khuyến nghị hành động ("EMERGENCY_STOP", xếp loại AN TOÀN/NGUY HIỂM,
...) cho người trả tiền.

**Điểm quan trọng nhất, nói thẳng để không ai đọc nhầm:** đăng ký làm ASP và
được duyệt list lên okx.ai (mục "Marketplace mở cho developer" trong tài
liệu OKX) là một quy trình **hoàn toàn khác** với việc xin chấp thuận theo
§9.3. Không có bất kỳ văn bản nào của OKX (trong toàn bộ tài liệu đã khảo
sát ở Phần 1) nói rằng việc list một dịch vụ lên OKX AI Marketplace tự động
thoả mãn yêu cầu "written approval" của §9.3. Đây là **giả định KHÔNG được
kiểm chứng** -- và là giả định nguy hiểm nếu ai đó mặc nhiên coi nó là đúng.

Trước khi đưa dịch vụ này lên marketplace và thu tiền thật, cần:

1. Đọc lại toàn văn OKX API Agreement hiện hành (điều khoản có thể đã đổi
   số mục kể từ lần khảo sát này) để xác nhận đúng nội dung và phạm vi của
   §9.3.
2. Liên hệ OKX (qua kênh Developer Portal hoặc kênh ASP) để hỏi thẳng: việc
   đăng ký ASP + list lên okx.ai có cấu thành "written approval" cho mục
   đích của điều khoản này hay không, và xin xác nhận bằng văn bản riêng
   nếu câu trả lời không rõ ràng.
3. Không coi việc "được duyệt ASP trong 24h" (một quy trình có vẻ mang tính
   tự động/nhanh) là bằng chứng đã qua được vòng rà soát pháp lý nghiêm túc
   mà §9.3 có lẽ dự định yêu cầu.

Không có nội dung nào trong Phần 1-3 của tài liệu này thay thế cho bước rà
soát pháp lý trên -- việc dựng code (Phần 2) chỉ là chuẩn bị kỹ thuật, hoàn
toàn độc lập với việc dự án có được phép vận hành mô hình kinh doanh này hay
không.
