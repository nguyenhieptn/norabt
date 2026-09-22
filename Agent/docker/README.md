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
  `Agent/data/market/cache/candles` (cache nến agent-web tự ghi) và
  `Agent/data/report` (kết quả chấm điểm, hồ sơ người dùng do wallet-address
  identity tạo, và mã lượt-dùng ẩn danh — xem Bước 3.5 dưới đây). Đừng nới
  thêm quyền ghi ra ngoài hai nhánh đó — batch report/crawler ghi phần còn
  lại của `Agent/data` từ NGOÀI container, agent-web chỉ nên đọc lại.
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
`Agent/docker/.dockerignore` và `Agent/docker/Dockerfile`) — nó chỉ nằm trên
host và được `docker compose` đọc làm biến môi trường lúc `up`.

**Kiểm tra:**

```bash
test -s Agent/.env && echo "OK: file tồn tại và không rỗng"
stat -c "%a %n" Agent/.env   # kỳ vọng: 600 Agent/.env
```

### Bước 2 — Kiểm cú pháp cấu hình Docker

```bash
docker compose -f Agent/docker/docker-compose.yml config
```

Lệnh này **không build, không chạy gì** — chỉ parse YAML + `Agent/.env` và in
ra cấu hình đã resolve. Nếu báo lỗi thiếu `Agent/.env`, quay lại Bước 1.

**Kiểm tra:** lệnh thoát mã 0, phần `ports:` in ra đúng `127.0.0.1:8770`.

### Bước 2.5 — Build frontend (SPA)

`Agent/backend/web/app.py` phục vụ `/` bằng file build sẵn
`Agent/frontend/dist/index.html` (+ `/assets/*` từ `Agent/frontend/dist/assets/`) --
KHÔNG build từ source lúc container khởi động, và Docker image (Bước 3 dưới
đây) hoàn toàn không chứa Node/npm hay `Agent/frontend/` (xem
`Agent/docker/Dockerfile`'s allow-list COPY). Frontend phải được build **trên
host, trước** khi build/chạy container -- kết quả nằm dưới `Agent/frontend/dist/`, thư
mục docker-compose.yml **đã** bind-mount read-only vào container
(`../frontend/dist:/app/Agent/frontend/dist:ro`, xem Bước 4 dưới đây) nên không cần sửa
docker-compose.yml gì thêm cho việc này. Mount trỏ ĐÚNG HAI đường
(`frontend/dist` và `frontend/tokens.css`) chứ không mount cả
`Agent/frontend/`: thư mục đó chứa `node_modules` 47 MB mà container không
bao giờ cần.

```bash
cd Agent/frontend
npm install          # một lần, hoặc mỗi khi package.json đổi -- không cần taskset
bash build.sh         # BẮT BUỘC dùng script này, KHÔNG gõ tay "npm run build"
```

**Vì sao bắt buộc qua `build.sh` chứ không gõ tay `npm run build`:** máy này
chạy 15 site production khác (xem mục "0. Trước khi bắt đầu" ở trên) dưới
ràng buộc cứng ≤12 core/≤14GB RAM cho TOÀN BỘ phần việc, không riêng
agent-web. `build.sh` bọc đúng lệnh:

```bash
taskset -c 0-3 env NODE_OPTIONS=--max-old-space-size=2560 npm run build
```

-- ép Vite/esbuild chỉ dùng tối đa 4 lõi (không phải cả 24) và trần heap
2.5GB, cùng chính sách tài nguyên `nora/build_frontend.sh` đã áp dụng cho
frontend `nora/`. Không sourcemap trong bundle production (xem
`Agent/frontend/vite.config.js`'s `build.sourcemap: false`) -- giảm cả thời
gian build lẫn dung lượng `Agent/frontend/dist/`.

**Kiểm tra:**

```bash
ls Agent/frontend/dist/index.html Agent/frontend/dist/assets/
# Kỳ vọng: index.html + ít nhất một file .js và một file .css trong assets/.
grep -o -- '--verdict-danger:[^;]*;' Agent/frontend/dist/assets/*.css
# Kỳ vọng: in ra đúng giá trị hiện có trong Agent/frontend/tokens.css -- xác nhận
# @import cross-project (Agent/frontend/src/styles/global.css ->
# Agent/frontend/tokens.css) đã được Vite bundle vào đúng, không âm thầm rỗng.
```

Frontend chưa build (checkout mới) không làm container lỗi khởi động --
`/` trả trang fallback tối giản ("Chưa build frontend"), `/assets/*` trả 404
per-file thay vì crash (xem `_dashboard_response`/`StaticFiles(check_dir=
False)` trong `Agent/backend/web/app.py`).

**Design token dùng chung (Việc 3):** `Agent/frontend/tokens.css` là NGUỒN DUY
NHẤT của màu 6 nhãn kết luận hai trục (bốn tổ hợp
`DRAWDOWN: LOW/HIGH × QUALITY: GOOD/WEAK`, cờ `HIDDEN RISK`, và trạng thái
trung tính `INSUFFICIENT EVIDENCE`), thang chữ, khoảng cách và bán kính bo
góc.
Hai phía đọc file NÀY, không phía nào chép giá trị:

- `Agent/backend/web/report_page.py` đọc file này TẠI RUNTIME (một file
  read + regex nhỏ trên các dòng `--name: value;`, không thêm dependency
  Python nào) để dựng `VERDICT_COLOR` và để nhúng nguyên văn nội dung CSS
  của file vào `<style>` của mỗi trang báo cáo render ra -- xem module đó,
  `_load_verdict_color`/`_design_tokens_css_text`.
- SPA (`Agent/frontend/src/styles/global.css`) `@import` THẲNG file này qua
  đường dẫn tương đối trong cùng một thư mục dự án
  (`../../tokens.css`, tính từ `frontend/src/styles/`) -- không sinh code,
  không copy file. `tokens.css` trước đây nằm ở `Agent/web/`, một thư mục
  anh em; nay đã gộp vào `Agent/frontend/` nên `@import` không còn xuyên
  biên dự án nữa.

Sửa một màu ở `Agent/frontend/tokens.css` là đổi cả hai nơi cùng lúc -- không
cần sửa thêm gì trong `report_page.py`/SPA.

**Gộp hai trang admin (Việc 3 -- lượt sửa "một hàm, ba nơi gọi"):**
`GET /admin` không còn tự render HTML danh sách bot nữa (module
`Agent/backend/web/admin_page.py` đã bị xoá) -- giờ chỉ còn KIỂM TRA QUYỀN
rồi chuyển hướng (302) sang màn hình admin của SPA (`/#/admin`), màn hình
danh sách DUY NHẤT còn lại. Người không có quyền vẫn nhận đúng 404 chung
như trước (không chuyển hướng người lạ). Toàn bộ biểu đồ tổng quan (tròn
phân bố xếp loại, cột phân bố điểm rủi ro, cột lý do veto, các ô số lớn)
trang cũ từng có đã được chuyển sang `Agent/frontend/src/components/
AdminOverview.jsx`, tính lại hoàn toàn phía trình duyệt từ dữ liệu
`GET /api/bots` (không gọi thêm endpoint nào khác).

### Bước 3 — Build image

```bash
docker compose -f Agent/docker/docker-compose.yml build
```

Build context là `Agent/` (không phải repo root, không phải `Agent/docker/`)
— xem comment đầu `Agent/docker/Dockerfile` nếu cần đổi cấu trúc thư mục sau
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

### Bước 3.5 — Tạo thư mục ghi-được cho data/report **[NGƯỜI THẬT]**

`docker-compose.yml` mount `../data/report:/app/Agent/data/report:rw` (xem
comment ngay tại dòng đó). `data/report/` có ĐÚNG HAI nhánh con —
`single/` (mọi thứ về một bot) và `multi/` (đánh giá multi-bot correlation,
xem `Agent/backend/pipeline_portfolio.py`) — và CẢ BA nhánh ghi-được cũ đều
nằm trong `single/`: `Agent/backend/report/qc/reporting/assessment_store.py`
ghi `data/report/single/<bot_id>/latest.json`,
`Agent/backend/web/identity.py` ghi `data/report/single/users/<user_ref>/
profile.json` mỗi khi có người khai địa chỉ ví qua `POST /api/session`, và
`Agent/backend/web/usage_ref.py` (Việc 2) ghi `data/report/single/
usage_refs/<ref>.json` mỗi khi `POST`/`GET /api/analyze` phân tích thành
công cho một caller KHÔNG đăng nhập (chính là luồng OKX) — cả `users/` và
`usage_refs/` nằm trong `single/` vì hiện tại cả hai chỉ phục vụ luồng
phân tích một-bot, chưa có gì tương đương cho portfolio. Thư mục
`data/report/` **phải tồn tại trên host VÀ thuộc đúng uid/gid trước khi
`docker compose up` lần đầu** —
nếu chưa có, Docker tự tạo nó lúc mount và gán quyền root, còn container
lại chạy bằng `user: "1000:1000"` (xem `docker-compose.yml`) nên vẫn không
ghi được vào thư mục root vừa tạo đó, tái diễn đúng lỗi "read-only
filesystem" mà nhánh mount này định sửa. ĐÃ CẮN THẬT một lần: khi đường
dẫn host đổi theo kiến trúc mới mà `docker-compose.yml` không đồng bộ
theo, Docker tự tạo lại đường dẫn CŨ (`Agent/data/users`,
`Agent/data/usage_refs`, `Agent/data/cache`) thuộc quyền root lúc container
khởi động lại — luôn `grep "\.\./data/" Agent/docker/docker-compose.yml`
đối chiếu với cấu trúc `Agent/data/` thật trên host sau bất kỳ lần đổi tên
thư mục nào trong `data/`.

```bash
mkdir -p Agent/data/report
touch Agent/data/report/.gitkeep
# Nếu uid chạy `docker compose up` KHÔNG PHẢI 1000 (kiểm bằng `id -u`),
# đổi chủ thư mục cho khớp user: "1000:1000" trong docker-compose.yml:
#   sudo chown 1000:1000 Agent/data/report
```

**Kiểm tra:**

```bash
stat -c "%u:%g %a %n" Agent/data/report
# Kỳ vọng: uid:gid khớp đúng "1000:1000" (hoặc uid/gid thật sự chạy
# container, nếu docker-compose.yml's user: đã được đổi khỏi mặc định).
```

### Bước 4 — Chạy container

```bash
docker compose -f Agent/docker/docker-compose.yml up -d
```

**Kiểm tra:**

```bash
docker compose -f Agent/docker/docker-compose.yml ps
# Cột STATUS: "starting" trong ~20s đầu (start_period), sau đó "healthy".

curl -s http://127.0.0.1:8770/healthz | python3 -m json.tool
# Kỳ vọng {"status": "ok", "uptime_seconds": ..., "snapshot": "disabled",
# "bots_on_disk": <N>, "okx_public_reachable": true|false}. "bots_on_disk"
# xác nhận mount Agent/data:ro đã đúng -- <N> phải bằng đúng số thư mục có
# latest.json trong Agent/data/report/ ở thời điểm chạy (đếm bằng
#   find Agent/data/report -maxdepth 2 -name latest.json | wc -l
# ). Đừng ghi cứng một con số vào đây: dataset lớn dần theo mỗi đợt chấm
# điểm, và một con số cũ chỉ làm người đọc tưởng là hỏng. "snapshot": "disabled" là
# đúng ở bước này (NORABT_SNAPSHOT_REDIS_URL chưa cấu hình) -- xem Bước 11
# nếu muốn bật bộ đệm snapshot Redis cho GET /bot/<code>.

curl -s http://127.0.0.1:8770/api/bots | python3 -c "import json,sys; print(json.load(sys.stdin)['count'])"
# Kỳ vọng: 30

curl -sI http://127.0.0.1:8770/ | head -1
# Kỳ vọng: HTTP 200 -- trang SPA thật nếu Bước 2.5 đã build, trang fallback
# tối giản ("Chưa build frontend") nếu chưa -- KHÔNG BAO GIỜ 500 dù trường
# hợp nào.
ASSET_JS=$(ls Agent/frontend/dist/assets/*.js 2>/dev/null | head -1)
[ -n "$ASSET_JS" ] && curl -sI "http://127.0.0.1:8770/assets/$(basename "$ASSET_JS")" | head -1
# Kỳ vọng (khi đã build): HTTP 200, content-type javascript.

curl -s -X POST http://127.0.0.1:8770/api/session \
  -H 'Content-Type: application/json' \
  -d '{"identity":"0xaa17d42f8b35f4f2216651c2e83b6405f1b4d5ca"}' -i
# Kỳ vọng: HTTP 200, JSON {"status":"OK","role":"user","user_ref":"...",...}
# kèm header "set-cookie:" -- xác nhận mount Bước 3.5 ở trên đã ghi được
# (nếu vẫn read-only, đây trả 500 với thông báo chung "chưa lưu được hồ
# sơ" + mã sự cố, xem Agent/backend/web/identity.py's ProfileStoreError).
ls Agent/data/report/single/users/*/profile.json
# Kỳ vọng: thấy đúng 1 file profile.json vừa được request ở trên tạo ra
# TRÊN HOST (container ghi qua mount rw, không phải bên trong container).
```

Nếu `bots_on_disk` là `null` (`status: "degraded"`) → xem bảng sự cố, mục
"agent không lên" / mount sai đường dẫn. Nếu `POST /api/session` báo lỗi
"chưa lưu được hồ sơ" → quay lại Bước 3.5, kiểm tra quyền thư mục
`Agent/data/report`.

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
  `Agent/nginx/nginx-agent.conf.template` để biết vì sao (vòng lặp
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

Giai đoạn A dùng `Agent/nginx/nginx-agent.conf.template` — CHỈ cổng 80,
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
sed 's/<DOMAIN>/agent.expsolution.io/g' Agent/nginx/nginx-agent.conf.template \
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
# trả 200 -- SPA build thật nếu Bước 2.5 đã chạy, hoặc trang fallback tối
# giản "Chưa build frontend" nếu chưa, xem docstring của
# _dashboard_response trong Agent/backend/web/app.py). "/api/...",
# "/bot/<code>", "/assets/...", "/admin", "/{userref}_{code}" và "/healthz"
# cũng phải được proxy tới agent-web (route thật, xem cuối create_app trong
# Agent/backend/web/app.py, VÀ danh sách location tương ứng ở đầu
# Agent/nginx/nginx-agent.conf.template -- hai danh sách này PHẢI khớp
# nhau, xem lời nhắc ở đầu file template đó) -- bất kỳ đường dẫn nào KHÁC
# những route đó mới phải ra 404 ngay tại nginx (thử:
# curl -I https://agent.expsolution.io/xyz).
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
docker compose -f Agent/docker/docker-compose.yml up -d --build agent-web
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
docker compose -f Agent/docker/docker-compose.yml up -d --build agent-web
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
cảnh báo đầu `Agent/nginx/nginx-agent-phase-b-full-strict.conf.template`).

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
  Agent/nginx/nginx-agent-phase-b-full-strict.conf.template \
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
(`sed 's/<DOMAIN>/.../' Agent/nginx/nginx-agent.conf.template`) đè lại
lên `/etc/nginx/sites-available/agent.expsolution.io`, `nginx -t`, reload —
đối xứng với 10.4.

### Bước 11 — Bật bộ đệm snapshot Redis cho `GET /bot/<code>` (tuỳ chọn)

Hoàn toàn TẮT theo mặc định (`NORABT_SNAPSHOT_REDIS_URL` để trống trong
`Agent/.env`) — bỏ qua bước này thì `GET /bot/<code>`/`GET /<userref>_<code>`
chạy y hệt như trước khi tính năng này tồn tại: mỗi lần mở link đều chấm
điểm lại từ đầu. Xem `Agent/backend/web/snapshot.py`'s module docstring cho
đầy đủ lý do thiết kế ("bộ đệm, không phải kho dữ liệu chính thức").

**Redis dùng cho bộ đệm này là `agent-redis` -- RIÊNG của agent, KHÔNG PHẢI
`norabt-redis`** của dự án "nora" đang chạy sẵn trên máy (6 container khác +
MySQL/MongoDB/PHP-FPM). Từng thử trỏ thẳng vào `norabt-redis` qua
`host.docker.internal:host-gateway` nhưng đo được trên chính hạ tầng này là
KHÔNG BAO GIỜ tới được: `norabt-redis` chạy `network_mode: host` và Redis
bên trong chỉ bind `127.0.0.1` (loopback CỦA HOST) — container agent-web ở
mạng bridge riêng (`deploy_default`) luôn bị kernel từ chối kết nối ngay
(`ConnectionRefusedError`, không phải treo/timeout), bất kể
`extra_hosts:host-gateway` có khai báo đúng cách mấy. Mở thêm bind cho
`norabt-redis` để nhận kết nối từ bridge network là đổi cấu hình vận hành
của Redis dùng chung với dự án khác — không nên làm chỉ để phục vụ agent.
Giải pháp chốt: `docker-compose.yml` khai báo sẵn service `agent-redis`
(image `redis:7-alpine`, cùng mạng bridge mặc định với agent-web, không
publish cổng ra host, tắt lưu bền, trần `maxmemory 128mb`) — xem mục 5 bên
dưới cho đầy đủ số đo/quyết định thiết kế.

```bash
# 11.1. docker-compose.yml đã khai báo sẵn service `agent-redis` và
#       `agent-web`'s `depends_on: agent-redis (condition: service_healthy)`
#       -- không cần sửa gì thêm ở bước này. `depends_on` chỉ quyết định THỨ
#       TỰ khởi động; nếu agent-redis chết sau khi cả hai đã lên, agent-web
#       vẫn tiếp tục chạy bình thường (xem comment trong file).

# 11.2. Agent/.env đã có sẵn (mặc định của checkout này):
#   NORABT_SNAPSHOT_REDIS_URL=redis://agent-redis:6379
cd Agent/docker && docker compose up -d

# 11.3. Xác nhận qua /healthz -- kỳ vọng "snapshot": "ok" (không phải
#       "disabled"/"unreachable"):
curl -s http://127.0.0.1:8770/healthz | python3 -m json.tool
```

**Redis chết thì trang vẫn sống** — đây là bài kiểm thử quan trọng nhất của
thiết kế fail-open (`docker stop norabt-agent-redis` rồi thử
`GET /bot/<code>`): trang vẫn trả HTTP 200 đầy đủ nội dung, `/healthz` báo
trung thực `"unreachable"`, không request nào lỗi. `docker start
norabt-agent-redis` lại là xong, không cần restart agent-web.

### Bước 12 — Bật "nhận định chuyên môn" do LLM viết (tuỳ chọn)

Hoàn toàn TẮT theo mặc định (`NORABT_NARRATIVE_BACKEND` để trống trong
`Agent/.env`) — bỏ qua bước này thì trường `narrative` trong `/api/analyze`
và trên `GET /bot/<code>` luôn là `null`, và
`Agent/backend/qc/reporting/narrative.py` không bao giờ spawn một tiến
trình con nào. Xem docstring đầu file đó cho đầy đủ thiết kế (nguyên tắc
bất di bất dịch: engine giữ toàn bộ con số/phán quyết, LLM chỉ diễn đạt,
mọi đầu ra đi qua 3 cổng kiểm trước khi được dùng).

**Chi phí thật, đã đo trên chính máy chủ dự án** trước khi bật: mỗi lượt
sinh nhận định gọi `claude` CLI, tốn 8–17 giây (trung vị ~14s) và ~0,05 USD
hạn mức Claude thật của chủ dự án — không phải hạn mức OKX, không phải
tiền của người dùng cuối. Bật tính năng này nghĩa là chấp nhận trả chi phí
đó cho MỖI lượt phân tích FULL mới (không phải mỗi lượt xem lại — xem
"sinh một lần" bên dưới).

**`claude` CLI chỉ tồn tại TRÊN HOST, không cài vào image** — binary đo
được là một file ELF 64-bit tự chứa ~224MB, không cần Node hay runtime nào
khác, sống tại `~/.local/share/claude/versions/<phiên bản>` với
`~/.local/bin/claude` là symlink trỏ tới bản đang dùng. `docker-compose.yml`
mount CẢ THƯ MỤC `versions/` (không phải một file phiên bản cụ thể) cộng
đúng một file `~/.claude/.credentials.json` vào container, cả hai chỉ-đọc
— xem comment ngay trong file đó cho đầy đủ lý do. Không cần sửa gì trong
`docker-compose.yml` để dùng đúng đường dẫn đo được trên máy chủ dự án
này; chỉ cần khi đường dẫn đó khác trên một máy khác, ghi đè bằng biến môi
trường của SHELL đang chạy `docker compose` (không phải trong `Agent/.env`
— hai cơ chế khác nhau, xem comment trong `docker-compose.yml`):

```bash
export NORABT_CLAUDE_VERSIONS_DIR="$(dirname "$(readlink -f "$(which claude)")")"
cd Agent/docker && docker compose up -d
```

**Không cần làm gì khi Claude Code tự cập nhật** — đây chính là lý do mount
cả thư mục thay vì một file phiên bản cụ thể: `narrative.py`'s
`resolve_claude_binary()` tự quét `/opt/claude/versions` bên trong
container, chọn bản SEMVER CAO NHẤT đang có (so sánh từng phần dưới dạng
số nguyên, không so chuỗi — tránh đúng bẫy "2.1.9" bị coi lớn hơn "2.1.10"
nếu so bằng ký tự), cache kết quả 45 giây. Một bản `claude` mới trên HOST
(thêm file, trỏ lại symlink) được container nhận trong vòng chưa tới một
phút, KHÔNG CẦN restart container, KHÔNG CẦN sửa cấu hình. `GET /healthz`
cho biết ngay container đang chạy bản nào (xem Bước 12.2 dưới đây) — đây
là cách xác nhận nhanh nhất sau một lần Claude Code tự cập nhật, thay vì
phải đoán.

```bash
# 12.1. Thêm vào Agent/.env:
#   NORABT_NARRATIVE_BACKEND=cli
cd Agent/docker && docker compose up -d

# 12.2. Xác nhận qua /healthz -- kỳ vọng "narrative": "ok (claude X.Y.Z)"
#       với X.Y.Z là phiên bản cao nhất hiện có trong
#       ~/.local/share/claude/versions trên host. "binary_missing" nghĩa
#       là thư mục versions rỗng hoặc không mount được (kiểm bằng
#       `docker exec norabt-agent-web ls -la /opt/claude/versions`).
#       "no_credentials" nghĩa là mount .credentials.json thiếu hoặc
#       không đọc được (kiểm bằng
#       `docker exec norabt-agent-web ls -la /opt/claude-home/.claude/`).
curl -s http://127.0.0.1:8770/healthz | python3 -m json.tool

# 12.3. Xác nhận bằng một bot thật:
curl -s -X POST http://127.0.0.1:8770/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"code":"<uniqueCode thật>"}' | python3 -c \
  'import json,sys; print(json.load(sys.stdin)["narrative"])'
# Kỳ vọng: một đoạn văn tiếng Việt (không phải null, không phải câu văn
# bản mẫu "Hệ thống chưa sinh được..." -- câu đó nghĩa là cổng kiểm đã
# chặn hoặc CLI lỗi/timeout, xem log container để biết lý do cụ thể).
```

**Sinh một lần, không sinh lại mỗi lượt xem** — narrative được tính CÙNG
LÚC với phân tích (`_analyze_full`), rồi nằm trong đúng lớp cache
`WebDataService` và snapshot Redis (Bước 11, nếu đã bật) mà phân tích đó
vốn đã dùng — mở lại cùng một link trong TTL cache không gọi Claude thêm
lần nào. Chỉ `?refresh=1` mới ép sinh lại (và tốn thêm một lượt chi phí
thật ở trên).

**LLM lỗi thì trang vẫn sống** — cùng triết lý fail-open như Redis ở Bước
11: `claude` CLI timeout, trả lỗi, hay đầu ra không qua được cổng kiểm đều
chỉ khiến `narrative` là một câu văn bản mẫu tĩnh, KHÔNG BAO GIỜ làm hỏng
phần còn lại của `/api/analyze`/`GET /bot/<code>` — nhưng LUÔN được ghi
log với lý do cụ thể (cổng nào, số/từ nào), nên `docker logs` là nơi cần
xem nếu tính năng này liên tục trả về câu văn bản mẫu thay vì nhận định
thật.

**Giới hạn đã biết, không giấu**: thông tin xác thực trong
`.credentials.json` có hạn, và được một PHIÊN `claude` chạy TRÊN HOST tự
làm mới — container chỉ gắn file này chỉ-đọc nên KHÔNG THỂ tự làm mới nó.
Nếu lâu ngày không ai chạy `claude` trên host, token có thể hết hạn; lúc
đó `GET /healthz` vẫn báo `"narrative": "ok (claude X.Y.Z)"` (file vẫn còn
đó, vẫn đọc được) NHƯNG mọi lượt sinh nhận định thật sẽ âm thầm trượt về
câu văn bản mẫu — `/healthz` không có cách nào phát hiện việc này mà
không tự gọi `claude` (việc probe liveness tuyệt đối không được làm, vì sẽ
tốn hạn mức thật mỗi lần orchestrator poll). Cách phát hiện thật: thỉnh
thoảng chạy lại đúng lệnh kiểm ở Bước 12.3 bằng một bot thật, hoặc theo
dõi `docker logs` cho dòng "narrative: backend ... reported a failure".

## 2. Vận hành hằng ngày

**Xem log ứng dụng (stdout/stderr container, đã giới hạn 10MB x 5 file):**

```bash
docker compose -f Agent/docker/docker-compose.yml logs -f --tail=200 agent-web
```

**Xem log nginx riêng của vhost này** (không lẫn log của container/dịch vụ
khác trên máy):

```bash
sudo tail -f /var/log/nginx/agent-expsolution-access.log
sudo tail -f /var/log/nginx/agent-expsolution-error.log
```

**Khởi động lại (không build lại):**

```bash
docker compose -f Agent/docker/docker-compose.yml restart agent-web
```

**Build lại sau khi đổi code** (`Agent/backend/**`) hoặc `requirements.txt`:

```bash
docker compose -f Agent/docker/docker-compose.yml up -d --build
```

**Xem tài nguyên thực tế đang dùng** (đối chiếu với trần `cpus: 2`/`mem_limit: 2g`):

```bash
docker stats norabt-agent-web --no-stream
```

**Gỡ bỏ sạch:**

```bash
# 1. Dừng và xoá container + network riêng của project này (KHÔNG đụng 6
#    container khác trên host -- chúng không cùng project Compose này).
docker compose -f Agent/docker/docker-compose.yml down

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
| **Agent không lên** — `docker compose ps` báo "unhealthy" hoặc container liên tục restart | `docker compose logs agent-web` — thường là lỗi import (thiếu package), lỗi mount (`Agent/data` không tồn tại trên host), hoặc `/healthz` trả `"status": "degraded"` (đọc `Agent/data` lỗi) | Nếu lỗi import: `docker compose build --no-cache agent-web` rồi thử lại. Nếu mount lỗi: kiểm tra `ls Agent/data` trên host có tồn tại và đọc được không, đường dẫn trong `docker-compose.yml` (`../data`) đúng tương đối với vị trí file compose (`Agent/docker/`) chưa. |
| **Container "healthy" nhưng healthz báo `okx_public_reachable: false`** | Đây KHÔNG phải lỗi của container — xem dòng "OKX chặn IP" bên dưới | Không cần khởi động lại container, việc đó không sửa được vấn đề bên ngoài này. |
| **502 Bad Gateway từ nginx** | nginx nhận request nhưng không nối được tới `127.0.0.1:8770` | `curl http://127.0.0.1:8770/healthz` trực tiếp trên host (bỏ qua nginx). Nếu cũng lỗi: xem mục "Agent không lên". Nếu curl trực tiếp OK nhưng qua nginx vẫn 502: `sudo nginx -t`, kiểm tra `proxy_pass http://127.0.0.1:8770;` trong vhost có đúng cổng không, và container có đang thật sự publish đúng `127.0.0.1:8770` không (`docker compose ps` cột PORTS). |
| **404 ở mọi route kể cả `/` và `/api/...`** | Vhost sai thứ tự location, hoặc domain match sai (`server_name` không khớp) | `sudo nginx -T \| grep -A5 "server_name agent.expsolution.io"` để xem nginx thực sự nạp vhost nào cho domain này (có thể một vhost `default_server` khác đang giành request trước). |
| **`ERR_TOO_MANY_REDIRECTS` / trình duyệt báo "redirected you too many times"** | Vhost Giai đoạn B (có `return 301 https`) đang chạy trong khi Cloudflare vẫn ở Flexible — Cloudflare → origin:80 → 301 → Cloudflare → origin:80 → 301 → ... vô hạn | Kiểm tra Cloudflare dashboard SSL/TLS mode ngay. Nếu vẫn Flexible: hoặc đổi sang Full (strict) ngay (nếu origin đã có cert thật, xem Bước 10.1), hoặc lùi lại vhost về Giai đoạn A (`Agent/nginx/nginx-agent.conf.template`, xem cuối Bước 10) để dừng vòng lặp trước, rồi làm lại đúng thứ tự. |
| **Cloudflare trả lỗi 526 "Invalid SSL certificate" hoặc 525 "SSL handshake failed"** | Cloudflare đang ở Full (strict) nhưng origin không có cert hợp lệ ở cổng 443 (chưa làm Bước 10, hoặc cert hết hạn/sai domain) | `curl -vI https://127.0.0.1 --resolve agent.expsolution.io:443:127.0.0.1` trên host để xem lỗi TLS thật từ origin. Nếu origin chưa có vhost 443: đổi Cloudflare tạm về Flexible cho tới khi làm xong Bước 10, hoặc hoàn tất Bước 10 ngay. |
| **Chứng chỉ TLS của ORIGIN hết hạn / trình duyệt báo not secure dù đã ở Giai đoạn B** | certbot's cron/timer gia hạn tự động đã ngừng chạy, hoặc renew thất bại (thường do nginx đang down lúc renew làm HTTP-01 challenge fail) — CHỈ áp dụng sau khi đã làm Bước 10, Giai đoạn A không có chứng chỉ origin để hết hạn | `sudo certbot certificates` xem ngày hết hạn thật. `sudo certbot renew --dry-run` để xem lỗi cụ thể. `systemctl status certbot.timer` (hoặc `snap.certbot.renew.timer`) xem timer có active không. Renew thủ công: `sudo certbot renew && sudo systemctl reload nginx`. |
| **OKX chặn IP / trả lỗi liên tục** (`healthz` báo `okx_public_reachable: false` kéo dài, hoặc `/api/analyze` luôn lỗi 502) | IP `103.141.141.24` bị OKX rate-limit hoặc chặn (khác hẳn lỗi mạng cục bộ) | Kiểm tra trực tiếp từ host: `curl -s https://www.okx.com/api/v5/public/time` — nếu cũng lỗi/timeout từ chính host (không qua container) thì đúng là OKX/mạng phía OKX có vấn đề, không phải lỗi ở agent-web. Việc này nằm ngoài khả năng tự sửa của container — theo dõi `Agent/backend/okx/probe.py`'s `check_public_access()` để có chẩn đoán chi tiết hơn (mã lỗi OKX cụ thể), và cân nhắc giãn tần suất gọi nếu do rate-limit. |
| **Hết dung lượng cache nến** (`Agent/data/market/cache/candles` phình to, hoặc container báo lỗi ghi đĩa) | Cache nến 1H tích luỹ theo số lượng asset từng được `/api/analyze` tra cứu — không tự dọn | `du -sh Agent/data/market/cache/candles` để xem kích thước thật. An toàn để xoá bớt/xoá sạch thư mục này bất cứ lúc nào (`rm -rf Agent/data/market/cache/candles/*` trên host, container không cần restart) — đây chỉ là cache, `LiveMarketDataSource` (xem `Agent/backend/external/sources/market_source.py`) tự tải lại từ OKX khi thiếu, không mất dữ liệu gốc nào. |
| **`POST /api/session` báo "Hệ thống tạm thời chưa lưu được hồ sơ" (HTTP 500, kèm một mã sự cố 8 ký tự)** | `Agent/data/report` chưa được tạo trước khi `docker compose up` (nên Docker tự tạo nó thuộc quyền root — xem Bước 3.5), hoặc sai uid/gid, hoặc host hết dung lượng đĩa. Thông báo trả về CỐ Ý không nêu chi tiết (đường dẫn, mã lỗi OS) để tránh lộ cấu trúc nội bộ ra ngoài — xem `Agent/backend/web/identity.py`'s `ProfileStoreError` | `docker compose logs agent-web \| grep "mã sự cố đó"` (copy đúng mã 8 ký tự người dùng báo lại) để xem chi tiết đầy đủ (loại lỗi, traceback) mà `Agent/backend/web/app.py`'s `_log_incident` đã ghi kèm đúng mã đó. Rồi kiểm `stat -c "%u:%g %a %n" Agent/data/report` và `df -h` trên host, sửa theo Bước 3.5. |
| **`/api/analyze` trả về nhưng `report_url`/dòng "xem chi tiết trực quan" bị THIẾU cho một caller ẩn danh (không đăng nhập, không phải admin)** | `Agent/data/report` chưa được tạo trước khi `docker compose up` (giống hệt lỗi ở dòng trên nhưng cho Việc 2's usage-ref store thay vì profile), nên `usage_ref.mint_usage_ref` không ghi được và request rơi vào nhánh lỗi 500 chung (`_log_incident`) — KHÔNG BAO GIỜ lộ mã bot thật `/bot/<code>` ra thay thế | `docker compose logs agent-web \| grep "mã sự cố đó"`, rồi kiểm `stat -c "%u:%g %a %n" Agent/data/report` và `df -h`, sửa theo Bước 3.5. |
| **Log đầy đĩa** | Log container đã bị giới hạn (`max-size: 10m`, `max-file: 5` → tối đa 50MB, xem `docker-compose.yml`) nhưng log nginx riêng của vhost thì chưa có giới hạn riêng ở đây | Kiểm tra `/etc/logrotate.d/nginx` trên host đã bao gồm pattern `/var/log/nginx/*.log` (mặc định Ubuntu là vậy — vhost mới đặt tên `agent-expsolution-*.log` nên khớp pattern này tự động). Nếu không, thêm một block logrotate riêng cho hai file này. |
| **`docker compose config` báo lỗi thiếu `Agent/.env`** | Bước 1 (tạo `Agent/.env`) chưa làm, hoặc chạy lệnh từ sai thư mục | Quay lại Bước 1. Lệnh `docker compose -f Agent/docker/docker-compose.yml ...` chạy được từ bất kỳ thư mục nào (đường dẫn `-f` là tuyệt đối/tương đối tới file, `env_file: ../.env` bên trong luôn tính tương đối theo vị trí `docker-compose.yml`, không theo thư mục đang đứng khi gõ lệnh). |
| **`/healthz` báo `"snapshot": "unreachable"` dù đã làm Bước 11** | `agent-redis` chưa healthy/chưa chạy, hoặc `NORABT_SNAPSHOT_REDIS_URL` bị sửa sai khỏi giá trị mặc định `redis://agent-redis:6379` | `docker compose ps agent-redis` xem container có "healthy" không; `docker compose logs agent-redis` nếu không. Nếu container ổn nhưng vẫn `unreachable`: kiểm tra `Agent/.env`'s `NORABT_SNAPSHOT_REDIS_URL` đúng `redis://agent-redis:6379` (không phải `host.docker.internal` hay `127.0.0.1` -- đó là địa chỉ SAI cho service riêng này). KHÔNG phải lỗi cần "sửa" gấp trong lúc chẩn đoán -- tính năng fail-open, mọi request vẫn chấm điểm trực tiếp như hôm nay, không ai bị ảnh hưởng. |

## 4. Cách ly với các dịch vụ khác trên máy

- **Cổng:** chỉ `127.0.0.1:8770` (container) + `443`/`80` (nginx, dùng
  chung với mọi vhost khác trên máy nhưng qua `server_name` riêng, không
  đụng cấu hình vhost nào khác). Không mở thêm cổng nào khác.
- **Tài nguyên:** trần cứng `cpus: 2` / `mem_limit: 2g` cho agent-web và
  `mem_limit: 192m` (`maxmemory 128mb`) cho `agent-redis` (xem lý do chi
  tiết trong `docker-compose.yml`) — cả hai cộng lại vẫn nằm trong ngân sách
  ≤12 core/≤14GB của toàn dự án, để lại dư địa cho 6 container Docker khác
  (fms-frontend, fms-backend, fms-mongodb, giapha-db, nora-tg-bot,
  nora-vault-sync) và MySQL/MongoDB/PHP-FPM chạy trực tiếp trên host.
- **Mạng Docker:** không khai báo `networks:` dùng chung trong
  `docker-compose.yml` — Compose tự tạo network riêng (`deploy_default`) cho
  project này, không tham gia network của bất kỳ container nào khác đang
  chạy. `agent-redis` (service riêng cho tính năng snapshot, Bước 11) sống
  trên CHÍNH mạng `deploy_default` này, không publish cổng nào ra host, nên
  chỉ `agent-web` gọi được tới nó — không đổi gì về cách ly mạng tổng thể
  của service `agent-web`, và không đụng tới `norabt-redis`
  (`network_mode: host`) của dự án nora.
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
  Hệ quả: `Agent/docker/.dockerignore` không được Docker tự động áp dụng
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
- **Snapshot Redis (Bước 11) -- thiết kế và số đo hạ tầng thật**: xem
  `Agent/backend/web/snapshot.py`'s module docstring cho hợp đồng đầy đủ
  ("bộ đệm, không phải kho dữ liệu chính thức"). Tóm tắt các con số/quyết
  định đã đo trên chính server này trước khi chốt thiết kế:
  - **Vì sao không dùng chung `norabt-redis`**: `redis-cli config get bind`
    trên `norabt-redis` (`redis:7-alpine`, chạy `network_mode: host`, dùng
    CHUNG với dự án "nora" — đã có 88 khoá `candles:*`/`state:*`/
    `universe:*` ở db0) trả về `127.0.0.1` — Redis CHỈ nhận kết nối trên
    loopback CỦA HOST. Đã kiểm chứng trực tiếp (một container trên mạng
    `deploy_default` gọi thẳng tới địa chỉ gateway của chính mạng đó ở cổng
    6379) rằng kết nối bị từ chối ngay (`ConnectionRefusedError`, không
    phải treo/timeout) — nghĩa là `extra_hosts:
    host.docker.internal:host-gateway` một mình nó KHÔNG đủ để agent-web
    (mạng bridge riêng) với tới Redis này, và mở thêm bind cho
    `norabt-redis` là đổi cấu hình vận hành của dự án khác — không nên làm.
  - **Giải pháp: `agent-redis` riêng của agent** — service mới trong
    `docker-compose.yml`, `redis:7-alpine`, cùng mạng bridge mặc định với
    agent-web (không `network_mode: host`, không publish cổng ra host —
    một Redis không mật khẩu mà mở ra host là mời người lạ vào).
    `--save "" --appendonly no` tắt hoàn toàn RDB/AOF: snapshot là bộ đệm
    tái tạo được, mất là chấm điểm lại, không phải mất dữ liệu gốc — tắt
    lưu bền nghĩa là không có file ảnh nào đọng trên đĩa và mỗi lần khởi
    động lại là một cache sạch. `--maxmemory 128mb --maxmemory-policy
    allkeys-lru` + `mem_limit: 192m` ở cấp container chặn trần bộ nhớ, nằm
    gọn trong ràng buộc cứng của dự án (≤12 core/≤14GB RAM toàn hệ thống).
    `agent-web`'s `depends_on: agent-redis (condition: service_healthy)`
    chỉ quyết định thứ tự khởi động — không biến Redis thành phụ thuộc
    cứng, agent-web vẫn chạy bình thường nếu agent-redis chết sau đó.
  - db1 riêng (`REDIS_DB_INDEX` trong snapshot.py) + tiền tố khoá riêng
    (`agent:report:`) + `SNAPSHOT_MAX_BYTES` (512KB/khoá) + TTL 24h
    (`SNAPSHOT_TTL_SECONDS`) vẫn được giữ nguyên trên `agent-redis` dù giờ
    đây là instance riêng — không còn là điều kiện sống còn để tách khỏi 88
    khoá của nora (đã tách hẳn bằng một Redis instance khác), nhưng vẫn là
    lớp phòng thủ rẻ nếu `NORABT_SNAPSHOT_REDIS_URL` lỡ bị trỏ sai. snapshot.py
    không bao giờ gọi `FLUSHDB`/`FLUSHALL`/`KEYS *`.
  - Mọi timeout Redis trong snapshot.py
    (`REDIS_CONNECT_TIMEOUT_SECONDS`/`REDIS_SOCKET_TIMEOUT_SECONDS`, 0.5s)
    vẫn giữ nguyên để bảo vệ trước tình huống Redis tồn tại, kết nối được,
    nhưng treo/nghẽn mạng — không riêng gì tình huống "connection refused"
    từng đo được với `norabt-redis`.
