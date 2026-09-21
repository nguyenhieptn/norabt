# Agent frontend (SPA)

Vite + React SPA phục vụ 3 màn hình phía trước của agent-web (định danh,
tra cứu/phân tích cho `user`, danh sách + tra cứu/phân tích cho `admin`).
Build ra `Agent/frontend/dist/`, được `Agent/backend/web/app.py` phục vụ tại `/`
(+ `/assets/*` cho bundle JS/CSS) -- xem `Agent/docker/README.md`'s "Bước
2.5 -- Build frontend" cho quy trình build/triển khai đầy đủ.

## Chạy dev

```bash
npm install
npm run dev
```

## Build production

**KHÔNG chạy `npm run build` trực tiếp.** Luôn dùng:

```bash
bash build.sh
```

`build.sh` ép `taskset -c 0-3` + `NODE_OPTIONS=--max-old-space-size=2560` --
máy triển khai chạy 15 site production khác dưới ràng buộc cứng ≤12
core/≤14GB RAM cho toàn bộ phần việc, không riêng agent-web (xem
`Agent/docker/README.md`). Không sourcemap trong bundle (xem
`vite.config.js`'s `build.sourcemap: false`).

## Cấu trúc

```
src/
  main.jsx                  entrypoint -- HashRouter (xem lý do dưới đây)
  App.jsx                   routes ("/", "/user", "/admin") + header đăng xuất
  context/SessionContext.jsx  trạng thái đăng nhập (role/user_ref), gương
                               sessionStorage, nguồn xác thực THẬT vẫn là
                               cookie HttpOnly server-side, đây chỉ là tiện
                               ích hiển thị UI
  api/client.js              fetch wrapper dùng chung, không nuốt thông báo
                               lỗi tiếng Việt của máy chủ
  pages/
    IdentityPage.jsx          "/" -- nhập ví/khoá admin (màn hình 1)
    UserHome.jsx               "/user" -- luồng tra cứu+phân tích (màn hình 2)
    AdminHome.jsx               "/admin" -- danh sách bot + tra cứu+phân tích
                                (màn hình 3)
  components/
    AnalyzeFlow.jsx            luồng 2 bước dùng chung: lookup -> thẻ tóm tắt
                                -> xác nhận -> analyze -> điều hướng sang
                                trang chi tiết server-render
    BotSummaryCard.jsx          thẻ tóm tắt bot (tên/AUM/PnL/hạng/số người
                                copy/danh sách tài sản kèm trạng thái)
  styles/global.css            @import Agent/frontend/tokens.css (xem dưới) + CSS
                                thuần cho toàn bộ SPA
```

## Vì sao dùng `HashRouter`, không phải `BrowserRouter`

`app.py` chỉ có ĐÚNG MỘT route thật phục vụ SPA (`GET /`, xem
`Agent/backend/web/app.py`). Mọi route khác (`/api/*`, `/bot/<code>`,
`/admin` -- một trang HTML server-render KHÁC, không phải route SPA cùng
tên, xem dưới --, `/{userref}_{code}`, `/healthz`, `/assets/*`) là route
thật của Starlette, và nginx (`Agent/nginx/nginx-agent*.conf.template`) cố
ý 404 mọi đường dẫn KHÁC danh sách đó để chặn dò quét. Nếu SPA dùng
`BrowserRouter` (URL thật kiểu `/user`, `/admin`), một F5 (hard refresh)
trên `/user` sẽ đi thẳng tới nginx trước khi JS kịp chạy -- và `/user` không
nằm trong danh sách được phép, nên sẽ 404 ngay tại nginx, KHÔNG BAO GIỜ tới
được `index.html`. `HashRouter` giữ toàn bộ trạng thái điều hướng sau dấu
`#` (`/#/user`, `/#/admin`), phần này KHÔNG BAO GIỜ được gửi lên server --
một F5 trên `/#/user` luôn luôn request lại đúng `/`, nhận `index.html`,
rồi JS tự đọc lại phần hash để hiện đúng màn hình.

## Vì sao `/admin` (SPA) và `/admin` (server) là hai thứ khác nhau

`GET /admin` là một route THẬT của `app.py` (`admin_page.py`, HTML render
sẵn phía server, có chủ đích KHÔNG sắp xếp/lọc bằng JavaScript -- xem module
đó). Route SPA `/#/admin` chỉ tồn tại phía client (sau dấu `#`, không bao
giờ chạm nginx/app.py như một path riêng) và hiển thị MỘT MÀN HÌNH KHÁC:
danh sách có tìm/lọc/sắp phía trình duyệt theo đúng yêu cầu của việc này,
cộng ô chạy phân tích trực tiếp. Hai trang không tranh chấp nhau vì SPA
không bao giờ điều hướng bằng URL thật `/admin` -- click vào một dòng bot
trong danh sách SPA đưa thẳng người dùng sang `/bot/<code>` (trang chi tiết
server-render), không phải sang `/admin` (server).

## Vì sao trang chi tiết bot (`/bot/<code>`, `/{userref}_{code}`) không được
## dựng lại trong SPA

Cố tình giữ nguyên server-render, SPA chỉ **dẫn link** sang (sau khi lookup
+ analyze thành công, điều hướng bằng `window.location.href`, rời khỏi SPA
hoàn toàn). Lý do: trang đó là tài liệu một người lạ có thể mở thẳng từ một
link nằm trong JSON `/api/analyze` (ví dụ dán vào Slack, hoặc một agent khác
trên OKX AI Marketplace tự mở) -- phải hiện ngay, in được, và **không phụ
thuộc JS chạy được hay không, không phụ thuộc build frontend đã chạy hay
chưa**. Một SPA-only route cho trang đó sẽ vi phạm cả ba yêu cầu này cùng
lúc.

## Design token dùng chung (Việc 3)

`src/styles/global.css` `@import "../../tokens.css"` thẳng file
`Agent/frontend/tokens.css` -- KHÔNG copy, KHÔNG code-gen. Đây là file DUY NHẤT
khai màu 4 bậc xếp loại (NGUY HIỂM/TIỀM ẨN/TIỀM NĂNG/AN TOÀN + trạng thái
trung tính), thang chữ, khoảng cách, bán kính -- phía Python
(`Agent/backend/web/report_page.py`) đọc CHÍNH file này lúc runtime (một
file read + regex nhỏ, xem module đó), không phải một bản chép tay riêng.
Sửa một giá trị trong `Agent/frontend/tokens.css` là đổi cả SPA lẫn trang
report/admin server-render cùng lúc, không cần sửa gì ở đây.

`@import` xuyên biên hai dự án (trước đây `Agent/frontend/` gọi vào `Agent/web/` khi hai
thư mục anh em, không lồng nhau) hoạt động bình thường dưới `vite build`
production vì đó là một lần resolve file lúc BUILD (Vite dùng
postcss-import/rollup xử lý `@import` CSS khi build), không phải một request
`server.fs.allow` của dev server -- giới hạn đó chỉ áp dụng khi chạy
`vite dev`, mà quy trình bắt buộc của dự án này (`build.sh`) chỉ chạy
`vite build`, chưa từng chạy dev server trong triển khai thật.

## Phụ thuộc

Chỉ `react` + `react-dom` + `react-router-dom` (runtime) và `vite` +
`@vitejs/plugin-react` (build) -- không thư viện UI, không thư viện biểu
đồ (biểu đồ đã có phía server, xem `report_page.py`'s inline SVG).
