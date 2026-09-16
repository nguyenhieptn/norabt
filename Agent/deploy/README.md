# Triển khai agent-web — runbook

Dịch vụ: `Agent/backend/web/app.py` (Starlette/uvicorn) — dashboard + API JSON
giám sát rủi ro bot copy-trading OKX. Đóng gói bằng Docker, publish ra
`127.0.0.1:8770` trên host, đứng sau nginx tại domain dự kiến
`agent.expsolution.io`.

Tài liệu này viết cho người vận hành đọc lúc nửa đêm khi có sự cố — mỗi bước
đều có lệnh kiểm tra ngay sau nó, và bước nào bắt buộc cần người thật thao
tác (không tự động hoá được, hoặc cố ý không để AI tự chạy) đều được đánh dấu
rõ **[NGƯỜI THẬT]**.

## 0. Trước khi bắt đầu — những gì đã đúng sẵn, đừng đổi

- Container publish `127.0.0.1:8770` — **không bao giờ** đổi thành
  `"8770:8770"` hay `"0.0.0.0:8770:8770"` trong `docker-compose.yml`. Cổng
  8770 lộ thẳng ra internet nghĩa là bỏ qua toàn bộ TLS/rate-limit/kiểm soát
  route mà nginx đang lo, trong khi server Starlette phía sau chưa có xác
  thực riêng của nó.
- `Agent/data` mount **chỉ-đọc**, trừ hai nhánh con **đọc-ghi**:
  `Agent/data/cache/candles` (cache nến agent-web tự ghi) và
  `Agent/data/users` (hồ sơ người dùng do wallet-address identity tạo, xem
  Bước 3.5 dưới đây). Đừng nới thêm quyền ghi ra ngoài hai nhánh đó — batch
  report/crawler ghi phần còn lại của `Agent/data` từ NGOÀI container,
  agent-web chỉ nên đọc lại.
- Giới hạn tài nguyên `cpus: 2` / `mem_limit: 2g` trong `docker-compose.yml`
  nằm trong ràng buộc cứng ≤12 core/≤14GB của toàn dự án trên máy 24 core/30GB
  đang chạy 6 container khác + MySQL/MongoDB/PHP-FPM/nginx. Xem comment ngay
  trong file đó để biết vì sao 2 core/2GB là đủ trước khi đổi con số.
- `agent.expsolution.io` đã có DNS trỏ về Cloudflare với **proxy BẬT** (mây
  cam), không phải "DNS only" — xem Bước 5 để hiểu hệ quả (TLS phía khách
  đã hợp lệ sẵn, chặng Cloudflare↔origin hiện là HTTP trần). Vhost nginx vì
  vậy phải cài theo đúng hai giai đoạn ở Bước 6 và Bước 10 — cài nhầm bản
  Giai đoạn B (có redirect 80→443) trước khi Cloudflare chuyển sang Full
  (strict) sẽ tạo vòng lặp redirect vô hạn và làm domain chết ngay.

## 1. Thứ tự triển khai

### Bước 1 — Tạo file bí mật `Agent/.env` **[NGƯỜI THẬT]**

```bash
cp Agent/.env.example Agent/.env
chmod 600 Agent/.env
$EDITOR Agent/.env   # điền OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSPHRASE
```

File này **không bao giờ** được copy vào Docker image (xem
`Agent/deploy/.dockerignore` và `Agent/deploy/Dockerfile`) — nó chỉ nằm trên
host và được `docker compose` đọc làm biến môi trường lúc `up`.

**Kiểm tra:**

```bash
test -s Agent/.env && echo "OK: file tồn tại và không rỗng"
stat -c "%a %n" Agent/.env   # kỳ vọng: 600 Agent/.env
```

### Bước 2 — Kiểm cú pháp cấu hình Docker

```bash
docker compose -f Agent/deploy/docker-compose.yml config
```

Lệnh này **không build, không chạy gì** — chỉ parse YAML + `Agent/.env` và in
ra cấu hình đã resolve. Nếu báo lỗi thiếu `Agent/.env`, quay lại Bước 1.

**Kiểm tra:** lệnh thoát mã 0, phần `ports:` in ra đúng `127.0.0.1:8770`.

### Bước 3 — Build image

```bash
docker compose -f Agent/deploy/docker-compose.yml build
```

Build context là `Agent/` (không phải repo root, không phải `Agent/deploy/`)
— xem comment đầu `Agent/deploy/Dockerfile` nếu cần đổi cấu trúc thư mục sau
này.

**Kiểm tra:**

```bash
docker images norabt-agent-web
# Kỳ vọng thấy đúng 1 dòng, tag "latest", kích thước vài trăm MB (base
# python:3.12-slim + numpy/pydantic/mcp/redis, KHÔNG chứa Agent/data).
docker run --rm norabt-agent-web:latest python3 -c "import os; print(os.listdir('/app/Agent'))"
# Kỳ vọng: ['requirements.txt', 'backend', 'data'] -- 'data' chỉ là thư mục
# rỗng chờ mount, KHÔNG có 'test', KHÔNG có '.env'.
```

### Bước 3.5 — Tạo thư mục ghi-được cho hồ sơ người dùng **[NGƯỜI THẬT]**

`docker-compose.yml` mount `../data/users:/app/Agent/data/users:rw` (xem
comment ngay tại dòng đó) để `Agent/backend/web/identity.py` ghi
`data/users/<user_ref>/profile.json` mỗi khi có người khai địa chỉ ví qua
`POST /api/session`. Thư mục này **phải tồn tại trên host VÀ thuộc đúng
uid/gid trước khi `docker compose up` lần đầu** — nếu chưa có, Docker tự
tạo nó lúc mount và gán quyền root, còn container lại chạy bằng
`user: "1000:1000"` (xem `docker-compose.yml`) nên vẫn không ghi được vào
thư mục root vừa tạo đó, tái diễn đúng lỗi "read-only filesystem" mà nhánh
mount này định sửa.

```bash
mkdir -p Agent/data/users
touch Agent/data/users/.gitkeep
# Nếu uid chạy `docker compose up` KHÔNG PHẢI 1000 (kiểm bằng `id -u`),
# đổi chủ thư mục cho khớp user: "1000:1000" trong docker-compose.yml:
#   sudo chown 1000:1000 Agent/data/users
```

**Kiểm tra:**

```bash
stat -c "%u:%g %a %n" Agent/data/users
# Kỳ vọng: uid:gid khớp đúng "1000:1000" (hoặc uid/gid thật sự chạy
# container, nếu docker-compose.yml's user: đã được đổi khỏi mặc định).
```

### Bước 4 — Chạy container

```bash
docker compose -f Agent/deploy/docker-compose.yml up -d
```

**Kiểm tra:**

```bash
docker compose -f Agent/deploy/docker-compose.yml ps
# Cột STATUS: "starting" trong ~20s đầu (start_period), sau đó "healthy".

curl -s http://127.0.0.1:8770/healthz | python3 -m json.tool
# Kỳ vọng {"status": "ok", "uptime_seconds": ..., "bots_on_disk": 30,
# "okx_public_reachable": true|false}. "bots_on_disk": 30 xác nhận mount
# Agent/data:ro đã đúng (30 là số bot đã chấm điểm sẵn trong dataset hiện
# tại, xem Agent/backend/web/data.py).

curl -s http://127.0.0.1:8770/api/bots | python3 -c "import json,sys; print(json.load(sys.stdin)['count'])"
# Kỳ vọng: 30

curl -s -X POST http://127.0.0.1:8770/api/session \
  -H 'Content-Type: application/json' \
  -d '{"identity":"0xaa17d42f8b35f4f2216651c2e83b6405f1b4d5ca"}' -i
# Kỳ vọng: HTTP 200, JSON {"status":"OK","role":"user","user_ref":"...",...}
# kèm header "set-cookie:" -- xác nhận mount Bước 3.5 ở trên đã ghi được
# (nếu vẫn read-only, đây trả 500 với thông báo chung "chưa lưu được hồ
# sơ" + mã sự cố, xem Agent/backend/web/identity.py's ProfileStoreError).
ls Agent/data/users/*/profile.json
# Kỳ vọng: thấy đúng 1 file profile.json vừa được request ở trên tạo ra
# TRÊN HOST (container ghi qua mount rw, không phải bên trong container).
```

Nếu `bots_on_disk` là `null` (`status: "degraded"`) → xem bảng sự cố, mục
"agent không lên" / mount sai đường dẫn. Nếu `POST /api/session` báo lỗi
"chưa lưu được hồ sơ" → quay lại Bước 3.5, kiểm tra quyền thư mục
`Agent/data/users`.

### Bước 5 — DNS **[đã làm xong, chỉ cần hiểu hệ quả]**

Bản ghi DNS `agent.expsolution.io` **đã được thêm sẵn** ở Cloudflare, nhưng
KHÔNG phải "DNS only" như runbook cũ từng giả định — đã đo trực tiếp:

```
agent.expsolution.io         → 104.21.43.253 / 172.67.192.70  (IP Cloudflare,
                                không phải IP origin 103.141.141.24)
Proxy status thực tế         → BẬT (mây cam)
https://agent.expsolution.io → HTTP 200, header "server: cloudflare", có cf-ray
                                TLS đã do Cloudflare cấp — chứng chỉ công khai
                                hợp lệ sẵn, trình duyệt thấy ổ khoá bình thường
                                NGAY CẢ KHI origin chưa có chứng chỉ riêng.
SSL/TLS mode ở Cloudflare     → Flexible (suy ra từ: gốc :80 trả 200, gốc :443
                                trả 502 → Cloudflare đang nối origin qua :80)
```

Hệ quả cần nhớ trong suốt phần còn lại của tài liệu này:

- Chặng khách ↔ Cloudflare: HTTPS thật, chứng chỉ hợp lệ, không cần làm gì
  thêm để có ổ khoá xanh.
- Chặng Cloudflare ↔ origin (máy này): HTTP TRẦN qua cổng 80, cho tới khi
  làm xong "Nâng cấp lên Giai đoạn B" ở cuối tài liệu này.
- **Không được** cài một vhost tự động redirect 80→443 trong lúc Cloudflare
  còn ở Flexible — xem khối cảnh báo lớn ở đầu
  `Agent/deploy/nginx-agent.conf.template` để biết vì sao (vòng lặp
  redirect vô hạn, site chết ngay).

**Kiểm tra (chỉ đọc, không đổi gì):**

```bash
dig +short agent.expsolution.io
# Kỳ vọng: 1-2 IP của Cloudflare (104.x/172.x...), KHÔNG phải 103.141.141.24
# -- nếu ra đúng 103.141.141.24 nghĩa là ai đó đã tắt proxy (chuyển DNS only),
# đọc lại mục "Phương án thay thế" ở cuối Bước 6 trước khi tiếp tục.
curl -sI https://agent.expsolution.io/ | grep -i '^server:\|^cf-ray:'
# Kỳ vọng: thấy "server: cloudflare" và một dòng "cf-ray:" -- xác nhận vẫn
# đang qua proxy Cloudflare.
```

Nếu chủ dự án muốn đơn giản hoá bằng cách bỏ Cloudflare proxy, xem "Phương
án thay thế: tắt proxy Cloudflare" ở cuối Bước 6 — **không tự làm việc đó**,
đây là quyết định của chủ dự án vì nó đánh đổi mất lớp chống DDoS và lộ IP
origin thật.

### Bước 6 — Cài vhost nginx GIAI ĐOẠN A **[NGƯỜI THẬT — cần sudo]**

Giai đoạn A dùng `Agent/deploy/nginx-agent.conf.template` — CHỈ cổng 80,
KHÔNG có redirect sang HTTPS (chủ ý, vì Cloudflare đang Flexible — xem Bước
5). Dịch vụ chạy được ngay sau bước này, qua HTTPS thật do Cloudflare cấp ở
biên.

```bash
# 1. Thêm 3 dòng limit_req_zone/limit_conn_zone (in ở cuối file template)
#    vào khối http{} của /etc/nginx/nginx.conf -- MỘT LẦN, áp dụng chung cho
#    mọi vhost trên máy này, không riêng agent-web. Khối real_ip_header/
#    set_real_ip_from thì KHÔNG thêm vào đây -- nó đã nằm sẵn trong chính
#    server{} của template (cấp server, có chủ ý, xem comment trong file
#    template vì sao không đặt ở cấp http trên máy có 15 site khác).
sudo $EDITOR /etc/nginx/nginx.conf

# 2. Sinh vhost từ template, thay <DOMAIN>
sed 's/<DOMAIN>/agent.expsolution.io/g' Agent/deploy/nginx-agent.conf.template \
  | sudo tee /etc/nginx/sites-available/agent.expsolution.io >/dev/null

# 3. Bật vhost
sudo ln -s /etc/nginx/sites-available/agent.expsolution.io /etc/nginx/sites-enabled/
```

**Kiểm tra:**

```bash
sudo nginx -t
# Kỳ vọng: "syntax is ok" / "test is successful" -- KHÔNG cần cảnh báo gì
# về ssl_certificate vì Giai đoạn A không có khối 443. Nếu báo lỗi khác,
# ĐỪNG reload nginx, sửa lỗi trước.
sudo systemctl reload nginx

curl -sI -H 'Host: agent.expsolution.io' http://127.0.0.1/
# Kỳ vọng: HTTP 200 (proxy trực tiếp tới agent-web, bỏ qua Cloudflare để
# kiểm tra riêng tầng nginx/origin).
curl -sI https://agent.expsolution.io/
# Kỳ vọng: HTTP 200 qua Cloudflare -- KHÔNG còn "Welcome to nginx!" mặc định,
# KHÔNG có ERR_TOO_MANY_REDIRECTS.
curl -s https://agent.expsolution.io/healthz | python3 -m json.tool
```

**Phương án thay thế: tắt proxy Cloudflare (đơn giản hơn, đánh đổi bảo mật)**
— nếu chủ dự án thấy việc quản lý hai giai đoạn phức tạp hơn cần thiết, có
thể đổi Cloudflare DNS record của `agent` sang "DNS only" (mây xám). Khi đó:

- Runbook nguyên bản kiểu cũ (`certbot --nginx`, redirect 80→443 luôn bật)
  hoạt động đúng nguyên bản, không cần hai file template này nữa.
- Đổi lại: mất lớp chống DDoS/WAF của Cloudflare, và IP origin thật
  (`103.141.141.24`) bị lộ trực tiếp cho bất kỳ ai tra `dig`.
- Khối `real_ip_header`/`set_real_ip_from` trong template lúc đó trở thành
  thừa (vô hại nếu để nguyên — chỉ ảnh hưởng khi kết nối đến từ đúng dải IP
  Cloudflare, việc này sẽ không còn xảy ra) nhưng nên gỡ bỏ để tránh gây
  hiểu lầm cho người đọc sau.

Đây là lựa chọn của chủ dự án, không tự ý đổi proxy status trên Cloudflare.

### Bước 7 — Xác nhận Giai đoạn A chạy ổn định qua Cloudflare **[NGƯỜI THẬT]**

Không có "cấp chứng chỉ TLS" ở bước này nữa — Cloudflare đã cấp TLS hợp lệ
ở biên từ Bước 5, trước cả khi origin có vhost. Bước này chỉ xác nhận toàn
bộ route thật đều sống qua domain công khai:

```bash
curl -I https://agent.expsolution.io/
# Kỳ vọng: HTTP/2 200 (route "/" được proxy nguyên vẹn tới agent-web, luôn
# trả 200 -- dashboard HTML thật nếu có, hoặc trang fallback tối giản nếu
# chưa có file dashboard, xem docstring của _dashboard_response trong
# Agent/backend/web/app.py). "/api/...", "/bot/<code>" và "/healthz" cũng
# phải được proxy tới agent-web (route thật, xem cuối create_app trong
# Agent/backend/web/app.py) -- bất kỳ đường dẫn nào KHÁC những route đó mới
# phải ra 404 ngay tại nginx (thử: curl -I https://agent.expsolution.io/xyz).
curl -s https://agent.expsolution.io/healthz | python3 -m json.tool
```

Giai đoạn A đủ để dịch vụ chạy công khai lâu dài nếu muốn — Phase B (mục
"Nâng cấp lên Giai đoạn B" ở cuối tài liệu) là TÙY CHỌN, chỉ cần khi muốn
đổi Cloudflare sang "Full (strict)" để mã hoá luôn cả chặng Cloudflare↔origin
(hiện đang là HTTP trần ở Flexible — chấp nhận được vì đây là traffic công
khai không có bí mật trong body ngoài mã bot, nhưng Full (strict) chặt hơn).

### Bước 8 — Bật `report_url` trong JSON của `/api/analyze` **[NGƯỜI THẬT]**

Chỉ làm bước này SAU KHI Bước 7 xác nhận `https://agent.expsolution.io/`
đã trả 200 thật qua HTTPS công khai — trước đó domain chưa chắc đã sống,
và một `report_url` trỏ tới domain chưa sống cũng tệ như không có domain.
**Không cần đợi Giai đoạn B** (origin có chứng chỉ riêng) — TLS phía khách
đã hợp lệ từ Cloudflare ngay từ Giai đoạn A, đó là tất cả những gì trình
duyệt của người dùng cuối quan tâm.

```bash
$EDITOR Agent/.env
# thêm dòng: NORABT_WEB_REPORT_BASE_URL=https://agent.expsolution.io
docker compose -f Agent/deploy/docker-compose.yml up -d --build agent-web
```

Chừng nào biến này còn để trống, JSON trả về từ `POST /api/analyze` CỐ Ý
không có khoá `report_url` — không phải lỗi, xem lý do đầy đủ (link
loopback/nội bộ là thông tin sai với agent của người lạ gọi từ OKX
Marketplace) trong comment của chính `NORABT_WEB_REPORT_BASE_URL` ở
`Agent/.env.example`.

**Kiểm tra:**

```bash
curl -s -X POST https://agent.expsolution.io/api/analyze \
  -H 'content-type: application/json' -d '{"code": "<một mã bot có thật>"}' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('report_url', 'KHÔNG CÓ report_url'))"
# Kỳ vọng: in ra "https://agent.expsolution.io/bot/<code>", không phải
# "KHÔNG CÓ report_url" và không phải một link 127.0.0.1/localhost.
curl -I https://agent.expsolution.io/bot/<code_vừa_dùng>
# Kỳ vọng: HTTP/2 200 -- đây chính là trang mà report_url trỏ tới.
```

### Bước 9 — Bật bảo vệ `/api/analyze` bằng token (tuỳ chọn) **[NGƯỜI THẬT]**

Mặc định (biến này để trống) `/api/analyze` đang MỞ HOÀN TOÀN: ai biết URL
cũng gọi được, không cần token. Bước này chỉ cần làm nếu muốn chặn người lạ
gọi endpoint tốn CPU/hạn mức OKX này miễn phí -- **không** làm bước này nếu
dịch vụ đang được để mở có chủ ý (ví dụ: đang thử nghiệm công khai trên OKX
AI Marketplace).

**Đọc kỹ trước khi bật:** token này KHÔNG PHẢI là xác thực OKX. `/api/analyze`
đăng ký trên OKX AI Marketplace với `fee = 0`, và OKX không gửi kèm bất kỳ
danh tính người mua nào tới một endpoint fee=0 -- xem comment đầy đủ trong
`Agent/.env.example` và trong `Agent/backend/web/access.py`'s module
docstring trước khi phát token cho bất kỳ ai với kỳ vọng sai về việc này.

```bash
$EDITOR Agent/.env
# thêm 2 dòng, ví dụ:
#   NORABT_ACCESS_TOKENS=abc123xyz:okx-marketplace-demo
#   NORABT_REPORT_URL_SECRET=<một chuỗi bí mật riêng, không dùng lại từ nơi khác>
docker compose -f Agent/deploy/docker-compose.yml up -d --build agent-web
```

**Kiểm tra:**

```bash
# Không token -- kỳ vọng 401, error_en chứa đúng cụm "authentication required".
curl -s -X POST https://agent.expsolution.io/api/analyze \
  -H 'content-type: application/json' -d '{"code": "<một mã bot có thật>"}' \
  | python3 -m json.tool

# Token đúng -- kỳ vọng 200, JSON có report_url NHƯ CŨ (trỏ /bot/<code>) VÀ
# thêm một dòng "Xem chi tiết trực quan..." trong report_markdown/text, lần
# này trỏ tới /r/<ref> thay vì /bot/<code> (xem access.py/app.py's
# api_analyze cho lý do -- đường dẫn mờ, không phải subdomain, vì hostname
# lộ ra ngoài qua SNI/DNS còn path thì nằm trong đường hầm TLS đã mã hoá).
curl -s -X POST https://agent.expsolution.io/api/analyze \
  -H 'content-type: application/json' \
  -H 'X-Access-Token: abc123xyz' \
  -d '{"code": "<một mã bot có thật>"}' | python3 -m json.tool
```

Chừng nào `NORABT_ACCESS_TOKENS` còn để trống, không có gì ở trên thay đổi
hành vi hiện tại của `/api/analyze` -- xem comment đầy đủ ở
`Agent/.env.example`.

### Bước 10 — Nâng cấp lên Giai đoạn B: mã hoá luôn chặng Cloudflare↔origin (tuỳ chọn) **[NGƯỜI THẬT — cần sudo]**

Chỉ làm bước này nếu muốn Cloudflare ↔ origin cũng chạy TLS thật (thay vì
HTTP trần như Giai đoạn A). Không bắt buộc — dịch vụ đã chạy tốt và an toàn
với người dùng cuối từ Bước 7. Làm **ĐÚNG THỨ TỰ** dưới đây, đảo thứ tự
10.3 và 10.4 sẽ gây vòng lặp redirect và sập dịch vụ ngay lập tức (xem
cảnh báo đầu `Agent/deploy/nginx-agent-phase-b-full-strict.conf.template`).

**10.1 — Cấp chứng chỉ cho origin, KHÔNG dùng plugin `certbot --nginx`:**

```bash
sudo certbot certonly --webroot -w /var/www/html -d agent.expsolution.io
```

Cố ý dùng `certonly --webroot`, không dùng `certbot --nginx -d ...`: plugin
`--nginx` tự ý sửa file vhost đang cài (kể cả tự thêm redirect 80→443 nếu
được hỏi/mặc định) — phá vỡ chính việc quản lý thứ tự hai giai đoạn mà tài
liệu này đang cố giữ chặt. `certonly --webroot` chỉ xin chứng chỉ, không
đụng gì tới nginx; request HTTP-01 đi qua đúng
`location /.well-known/acme-challenge/` mà Giai đoạn A đã có sẵn, và
Cloudflare (kể cả đang Flexible) chuyển tiếp cổng 80 nguyên vẹn nên bước
này chạy được mà không cần đổi gì ở Cloudflare trước.

**Kiểm tra:**

```bash
sudo certbot certificates | grep -A2 agent.expsolution.io
ls -la /etc/letsencrypt/live/agent.expsolution.io/
# Kỳ vọng: thấy fullchain.pem, privkey.pem thật.
```

**10.2 — Chuẩn bị vhost Giai đoạn B nhưng CHƯA bật:**

```bash
sed 's/<DOMAIN>/agent.expsolution.io/g' \
  Agent/deploy/nginx-agent-phase-b-full-strict.conf.template \
  > /tmp/agent-phase-b.conf
# Xem lại file này một lượt trước khi đi tiếp -- đặc biệt hai dòng
# ssl_certificate/ssl_certificate_key phải khớp đúng đường dẫn ở 10.1.
```

**10.3 — Đổi Cloudflare sang Full (strict) TRƯỚC** **[bắt buộc trước 10.4]**

Vào Cloudflare dashboard → domain `expsolution.io` → SSL/TLS → Overview →
đổi mode từ "Flexible" sang "Full (strict)". Đợi vài giây, xác nhận lại
trong dashboard là đã đổi xong.

**Kiểm tra ngay sau khi đổi (trước khi làm 10.4):**

```bash
curl -sI https://agent.expsolution.io/
# Kỳ vọng: vẫn HTTP 200 -- Cloudflare giờ nối origin qua HTTPS (cổng 443)
# bằng chính chứng chỉ vừa cấp ở 10.1, NHƯNG vhost 443 CHƯA được bật ở
# origin (còn ở Giai đoạn A, chỉ có cổng 80) -- nếu bước này ra lỗi (502
# hoặc trang lỗi Cloudflare "526 Invalid SSL certificate"), ĐỪNG làm 10.4,
# quay lại kiểm tra 10.1.
```

Nếu curl ở trên vẫn cư xử như đang còn Flexible (200 dù origin chưa mở 443,
tức Cloudflare có thể chưa kịp áp dụng thay đổi), đợi thêm rồi kiểm tra lại
— không sang 10.4 khi chưa chắc chắn Full (strict) đã có hiệu lực.

**10.4 — Chỉ bây giờ mới thay vhost sang Giai đoạn B:**

```bash
sudo cp /tmp/agent-phase-b.conf /etc/nginx/sites-available/agent.expsolution.io
sudo nginx -t
# Kỳ vọng: "syntax is ok" / "test is successful". Nếu lỗi, ĐỪNG reload --
# vhost cũ (Giai đoạn A) vẫn đang chạy trên đĩa qua sites-enabled, sửa lỗi
# rồi test lại.
sudo systemctl reload nginx
```

**Kiểm tra:**

```bash
curl -I https://agent.expsolution.io/
# Kỳ vọng: HTTP/2 200, vẫn đúng dashboard/route như trước (qua Cloudflare).
curl -sI -H 'Host: agent.expsolution.io' http://127.0.0.1/
# CHẠY TRÊN CHÍNH MÁY ORIGIN, gọi thẳng vào nginx qua loopback -- KHÔNG
# dùng `curl http://agent.expsolution.io/` để "gọi thẳng origin" vì DNS
# công khai của domain này trỏ về IP CLOUDFLARE (proxy bật), không phải
# 103.141.141.24 -- một curl như vậy vẫn đi QUA Cloudflare, không bypass
# được gì, dễ gây hiểu lầm khi đọc kết quả.
# Kỳ vọng: 301 Location: https://agent.expsolution.io/ -- xác nhận vhost
# origin (Giai đoạn B) đã tự redirect đúng.
curl -sI -H 'Host: agent.expsolution.io' https://127.0.0.1/ -k
# Tương tự nhưng qua cổng 443 loopback (-k vì cert origin ký cho tên miền
# thật, không phải 127.0.0.1) -- kỳ vọng HTTP 200, xác nhận vhost 443 của
# Giai đoạn B đã lên đúng bằng cert vừa cấp ở 10.1.
curl -IL https://agent.expsolution.io/
# Theo cả chuỗi qua Cloudflare thật -- xác nhận KHÔNG có vòng lặp (không
# thấy "Maximum (50) redirects followed" hay tương tự).
sudo certbot certificates | grep -A2 agent.expsolution.io
# Xác nhận certbot đã tự thêm timer gia hạn (systemctl status certbot.timer
# hoặc snap.certbot.renew.timer) -- renew tự chạy lại HTTP-01 qua chính
# location acme-challenge vẫn còn trong khối cổng 80 của Giai đoạn B.
```

Nếu sau này cần lùi lại Giai đoạn A (ví dụ Cloudflare bị đổi nhầm về lại
Flexible và trang bắt đầu lặp redirect): `sudo cp` file Giai đoạn A
(`sed 's/<DOMAIN>/.../' Agent/deploy/nginx-agent.conf.template`) đè lại
lên `/etc/nginx/sites-available/agent.expsolution.io`, `nginx -t`, reload —
đối xứng với 10.4.

## 2. Vận hành hằng ngày

**Xem log ứng dụng (stdout/stderr container, đã giới hạn 10MB x 5 file):**

```bash
docker compose -f Agent/deploy/docker-compose.yml logs -f --tail=200 agent-web
```

**Xem log nginx riêng của vhost này** (không lẫn log của container/dịch vụ
khác trên máy):

```bash
sudo tail -f /var/log/nginx/agent-expsolution-access.log
sudo tail -f /var/log/nginx/agent-expsolution-error.log
```

**Khởi động lại (không build lại):**

```bash
docker compose -f Agent/deploy/docker-compose.yml restart agent-web
```

**Build lại sau khi đổi code** (`Agent/backend/**`) hoặc `requirements.txt`:

```bash
docker compose -f Agent/deploy/docker-compose.yml up -d --build
```

**Xem tài nguyên thực tế đang dùng** (đối chiếu với trần `cpus: 2`/`mem_limit: 2g`):

```bash
docker stats norabt-agent-web --no-stream
```

**Gỡ bỏ sạch:**

```bash
# 1. Dừng và xoá container + network riêng của project này (KHÔNG đụng 6
#    container khác trên host -- chúng không cùng project Compose này).
docker compose -f Agent/deploy/docker-compose.yml down

# 2. Xoá image (tuỳ chọn, nếu không định deploy lại)
docker rmi norabt-agent-web:latest

# 3. Gỡ vhost nginx [NGƯỜI THẬT]
sudo rm /etc/nginx/sites-enabled/agent.expsolution.io
sudo rm /etc/nginx/sites-available/agent.expsolution.io
sudo nginx -t && sudo systemctl reload nginx

# 4. Thu hồi chứng chỉ origin [NGƯỜI THẬT, tuỳ chọn -- chỉ có gì để xoá nếu
#    đã từng làm Bước 10 (Nâng cấp lên Giai đoạn B); nếu vẫn đang ở Giai
#    đoạn A thì certbot sẽ báo không tìm thấy cert nào, bỏ qua bước này.
sudo certbot delete --cert-name agent.expsolution.io

# 5. Xoá bản ghi DNS A trên Cloudflare [NGƯỜI THẬT, tuỳ chọn]
```

`Agent/data` và `Agent/.env` trên host không bị đụng tới bởi bất kỳ lệnh nào
ở trên — dữ liệu và bí mật sống ngoài vòng đời của container.

## 3. Bảng sự cố thường gặp

| Triệu chứng | Chẩn đoán | Cách sửa |
|---|---|---|
| **Agent không lên** — `docker compose ps` báo "unhealthy" hoặc container liên tục restart | `docker compose logs agent-web` — thường là lỗi import (thiếu package), lỗi mount (`Agent/data` không tồn tại trên host), hoặc `/healthz` trả `"status": "degraded"` (đọc `Agent/data` lỗi) | Nếu lỗi import: `docker compose build --no-cache agent-web` rồi thử lại. Nếu mount lỗi: kiểm tra `ls Agent/data` trên host có tồn tại và đọc được không, đường dẫn trong `docker-compose.yml` (`../data`) đúng tương đối với vị trí file compose (`Agent/deploy/`) chưa. |
| **Container "healthy" nhưng healthz báo `okx_public_reachable: false`** | Đây KHÔNG phải lỗi của container — xem dòng "OKX chặn IP" bên dưới | Không cần khởi động lại container, việc đó không sửa được vấn đề bên ngoài này. |
| **502 Bad Gateway từ nginx** | nginx nhận request nhưng không nối được tới `127.0.0.1:8770` | `curl http://127.0.0.1:8770/healthz` trực tiếp trên host (bỏ qua nginx). Nếu cũng lỗi: xem mục "Agent không lên". Nếu curl trực tiếp OK nhưng qua nginx vẫn 502: `sudo nginx -t`, kiểm tra `proxy_pass http://127.0.0.1:8770;` trong vhost có đúng cổng không, và container có đang thật sự publish đúng `127.0.0.1:8770` không (`docker compose ps` cột PORTS). |
| **404 ở mọi route kể cả `/` và `/api/...`** | Vhost sai thứ tự location, hoặc domain match sai (`server_name` không khớp) | `sudo nginx -T \| grep -A5 "server_name agent.expsolution.io"` để xem nginx thực sự nạp vhost nào cho domain này (có thể một vhost `default_server` khác đang giành request trước). |
| **`ERR_TOO_MANY_REDIRECTS` / trình duyệt báo "redirected you too many times"** | Vhost Giai đoạn B (có `return 301 https`) đang chạy trong khi Cloudflare vẫn ở Flexible — Cloudflare → origin:80 → 301 → Cloudflare → origin:80 → 301 → ... vô hạn | Kiểm tra Cloudflare dashboard SSL/TLS mode ngay. Nếu vẫn Flexible: hoặc đổi sang Full (strict) ngay (nếu origin đã có cert thật, xem Bước 10.1), hoặc lùi lại vhost về Giai đoạn A (`Agent/deploy/nginx-agent.conf.template`, xem cuối Bước 10) để dừng vòng lặp trước, rồi làm lại đúng thứ tự. |
| **Cloudflare trả lỗi 526 "Invalid SSL certificate" hoặc 525 "SSL handshake failed"** | Cloudflare đang ở Full (strict) nhưng origin không có cert hợp lệ ở cổng 443 (chưa làm Bước 10, hoặc cert hết hạn/sai domain) | `curl -vI https://127.0.0.1 --resolve agent.expsolution.io:443:127.0.0.1` trên host để xem lỗi TLS thật từ origin. Nếu origin chưa có vhost 443: đổi Cloudflare tạm về Flexible cho tới khi làm xong Bước 10, hoặc hoàn tất Bước 10 ngay. |
| **Chứng chỉ TLS của ORIGIN hết hạn / trình duyệt báo not secure dù đã ở Giai đoạn B** | certbot's cron/timer gia hạn tự động đã ngừng chạy, hoặc renew thất bại (thường do nginx đang down lúc renew làm HTTP-01 challenge fail) — CHỈ áp dụng sau khi đã làm Bước 10, Giai đoạn A không có chứng chỉ origin để hết hạn | `sudo certbot certificates` xem ngày hết hạn thật. `sudo certbot renew --dry-run` để xem lỗi cụ thể. `systemctl status certbot.timer` (hoặc `snap.certbot.renew.timer`) xem timer có active không. Renew thủ công: `sudo certbot renew && sudo systemctl reload nginx`. |
| **OKX chặn IP / trả lỗi liên tục** (`healthz` báo `okx_public_reachable: false` kéo dài, hoặc `/api/analyze` luôn lỗi 502) | IP `103.141.141.24` bị OKX rate-limit hoặc chặn (khác hẳn lỗi mạng cục bộ) | Kiểm tra trực tiếp từ host: `curl -s https://www.okx.com/api/v5/public/time` — nếu cũng lỗi/timeout từ chính host (không qua container) thì đúng là OKX/mạng phía OKX có vấn đề, không phải lỗi ở agent-web. Việc này nằm ngoài khả năng tự sửa của container — theo dõi `Agent/backend/okx/probe.py`'s `check_public_access()` để có chẩn đoán chi tiết hơn (mã lỗi OKX cụ thể), và cân nhắc giãn tần suất gọi nếu do rate-limit. |
| **Hết dung lượng cache nến** (`Agent/data/cache/candles` phình to, hoặc container báo lỗi ghi đĩa) | Cache nến 1H tích luỹ theo số lượng asset từng được `/api/analyze` tra cứu — không tự dọn | `du -sh Agent/data/cache/candles` để xem kích thước thật. An toàn để xoá bớt/xoá sạch thư mục này bất cứ lúc nào (`rm -rf Agent/data/cache/candles/*` trên host, container không cần restart) — đây chỉ là cache, `LiveMarketDataSource` (xem `Agent/backend/sources/market_source.py`) tự tải lại từ OKX khi thiếu, không mất dữ liệu gốc nào. |
| **`POST /api/session` báo "Hệ thống tạm thời chưa lưu được hồ sơ" (HTTP 500, kèm một mã sự cố 8 ký tự)** | `Agent/data/users` chưa được tạo trước khi `docker compose up` (nên Docker tự tạo nó thuộc quyền root — xem Bước 3.5), hoặc sai uid/gid, hoặc host hết dung lượng đĩa. Thông báo trả về CỐ Ý không nêu chi tiết (đường dẫn, mã lỗi OS) để tránh lộ cấu trúc nội bộ ra ngoài — xem `Agent/backend/web/identity.py`'s `ProfileStoreError` | `docker compose logs agent-web \| grep "mã sự cố đó"` (copy đúng mã 8 ký tự người dùng báo lại) để xem chi tiết đầy đủ (loại lỗi, traceback) mà `Agent/backend/web/app.py`'s `_log_incident` đã ghi kèm đúng mã đó. Rồi kiểm `stat -c "%u:%g %a %n" Agent/data/users` và `df -h` trên host, sửa theo Bước 3.5. |
| **Log đầy đĩa** | Log container đã bị giới hạn (`max-size: 10m`, `max-file: 5` → tối đa 50MB, xem `docker-compose.yml`) nhưng log nginx riêng của vhost thì chưa có giới hạn riêng ở đây | Kiểm tra `/etc/logrotate.d/nginx` trên host đã bao gồm pattern `/var/log/nginx/*.log` (mặc định Ubuntu là vậy — vhost mới đặt tên `agent-expsolution-*.log` nên khớp pattern này tự động). Nếu không, thêm một block logrotate riêng cho hai file này. |
| **`docker compose config` báo lỗi thiếu `Agent/.env`** | Bước 1 (tạo `Agent/.env`) chưa làm, hoặc chạy lệnh từ sai thư mục | Quay lại Bước 1. Lệnh `docker compose -f Agent/deploy/docker-compose.yml ...` chạy được từ bất kỳ thư mục nào (đường dẫn `-f` là tuyệt đối/tương đối tới file, `env_file: ../.env` bên trong luôn tính tương đối theo vị trí `docker-compose.yml`, không theo thư mục đang đứng khi gõ lệnh). |

## 4. Cách ly với các dịch vụ khác trên máy

- **Cổng:** chỉ `127.0.0.1:8770` (container) + `443`/`80` (nginx, dùng
  chung với mọi vhost khác trên máy nhưng qua `server_name` riêng, không
  đụng cấu hình vhost nào khác). Không mở thêm cổng nào khác.
- **Tài nguyên:** trần cứng `cpus: 2` / `mem_limit: 2g` cho riêng container
  này (xem lý do chi tiết trong `docker-compose.yml`) — nằm trong ngân sách
  ≤12 core/≤14GB của toàn dự án, để lại dư địa cho 6 container Docker khác
  (fms-frontend, fms-backend, fms-mongodb, giapha-db, nora-tg-bot,
  nora-vault-sync) và MySQL/MongoDB/PHP-FPM chạy trực tiếp trên host.
- **Mạng Docker:** không khai báo `networks:` dùng chung trong
  `docker-compose.yml` — Compose tự tạo network riêng cho project này, không
  tham gia network của bất kỳ container nào khác đang chạy.
- **Volume:** chỉ mount `Agent/data` (đọc, trừ `cache/candles` và `users`
  đọc-ghi — xem Bước 3.5) của chính dự án này — không mount bất kỳ đường dẫn
  nào thuộc dự án khác.
- **Nếu agent-web hỏng/OOM-kill:** `restart: unless-stopped` tự khởi động
  lại nó; không dịch vụ nào khác trên host phụ thuộc vào agent-web nên việc
  nó down không lan sang MySQL/MongoDB/PHP-FPM hay 6 container kia.
- **Nếu một dịch vụ khác trên host bị OOM/quá tải:** `mem_limit`/`cpus` của
  agent-web là trần CỨNG do Docker cgroup ép — agent-web không thể "giành"
  vượt quá 2 core/2GB dù máy đang rảnh hay đang bận, nên nó không phải là
  nguyên nhân gây thiếu tài nguyên cho dịch vụ khác.

## 5. Ghi chú thiết kế (cho người đọc lại code sau này)

- **Base image `python:3.12-slim`, không phải 3.14** (dev machine chạy
  3.14): 3.12 có wheel nhị phân ổn định lâu năm cho numpy/pydantic-core/redis
  (đã xác minh trên PyPI trước khi chọn), trong khi 3.14 còn khá mới — một
  wheel thiếu cho dependency bắc cầu nào đó sẽ âm thầm build từ source trong
  image, cần thêm toolchain C/Rust mà bản thân dự án không cần. Không có
  syntax 3.13+/3.14-only nào trong `Agent/backend` (đã grep kiểm tra), nên hạ
  xuống 3.12 không mất gì về mặt chức năng.
- **Build context là `Agent/`**, không phải repo root: Dockerfile chỉ cần
  `Agent/backend` + `Agent/requirements.txt`, và việc giới hạn context giúp
  Docker daemon không phải nhận toàn bộ `nora/`, `.git`, v.v. ở repo root.
  Hệ quả: `Agent/deploy/.dockerignore` không được Docker tự động áp dụng
  (nó chỉ đọc `<context>/.dockerignore` = `Agent/.dockerignore`) — xem
  comment đầu file đó để biết vì sao đây không phải lỗ hổng (Dockerfile dùng
  allow-list COPY tường minh, không phải wildcard).
- **`/healthz` luôn trả HTTP 200`** kể cả khi `"status": "degraded"` — đúng
  quy ước "không bao giờ trả traceback thô, luôn JSON sạch" của toàn bộ
  `web/app.py`. Healthcheck của Docker (`docker-compose.yml`) vì vậy gate
  theo NỘI DUNG JSON, không theo mã HTTP.
- **`okx_public_reachable: false` không làm container "unhealthy"**: OKX
  chặn IP/rate-limit là điều kiện bên ngoài mà khởi động lại container không
  sửa được — để nó gây restart loop chỉ tổ làm ồn log mà không giải quyết gì.
