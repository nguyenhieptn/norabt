# Nội dung đăng ký ASP trên okx.ai

Soạn sẵn để dán vào form tại https://www.okx.ai/tutorial/asp — duyệt trong 24 giờ.
Thay `<DOMAIN>` bằng domain thật trước khi nộp.

**Trước khi nộp cần có**: Agentic Wallet (đăng nhập email/Google trên okx.ai) và
endpoint đã chạy được từ internet (xem `README.md`).

---

## Tên agent
```
OKX Bot Risk Supervisor
```

## Mô tả ngắn (dòng hiện trên thẻ)
```
Risk scoring for OKX lead traders from public data: 10,000 simulated scenarios
on the closed trade book, a two-axis verdict, and a plain-English explanation
of why.
```

## Mô tả đầy đủ
```
Give it the uniqueCode of an OKX lead trader and get back a risk assessment you
can check.

The system uses only OKX public data, computes only on CLOSED trades, and states
plainly what it could not measure instead of guessing.

What it measures:
- 10,000 simulated scenarios with a stationary bootstrap (Politis & Romano, 1994)
  on the bot's own trade book, producing profit/loss percentiles and tail risk
- Probabilistic Sharpe Ratio and Deflated Sharpe Ratio (Bailey & Lopez de Prado)
  to separate real edge from luck that comes from screening many candidates
- The gap between the closed book and the open book — this is what exposes the
  pattern of taking wins early and holding losses in the hope of a bounce
- Behaviour across market phases (trend and volatility)
- A two-axis verdict — drawdown high or low, quality good or weak — plus a
  separate risk score, quality score, and a written explanation

Guiding rule: missing data is never scored as safe. A bot that does not publish
its trade book can still be assessed, but with a HIGHER risk score and LOWER
confidence than a transparent bot showing the same surface numbers.

This is not investment advice. It places no orders and accesses no one's account.
```

## Danh mục
```
Trading & Finance
```

## Giá
```
Miễn phí (free endpoint — trả kết quả trực tiếp, không thương lượng)
```

## Dịch vụ 1 — Tra cứu bot

**Endpoint**: `POST https://<DOMAIN>/api/lookup`

**Tham số**: `code` — uniqueCode của lead trader trên OKX

```bash
curl -X POST https://<DOMAIN>/api/lookup \
  -H 'Content-Type: application/json' \
  -d '{"code":"EF1CC6F40E834D1A"}'
```

Trả về hồ sơ bot và danh sách asset kèm trạng thái hoạt động
(ĐANG GIAO DỊCH / CHỈ ĐANG ÔM / ĐÃ RỜI). Dưới 3 giây.

## Dịch vụ 2 — Phân tích rủi ro đầy đủ

**Endpoint**: `POST https://<DOMAIN>/api/analyze` (cũng nhận `GET` với `code`
trên query string, cùng handler — xem `serviceDescription` A2MCP bên dưới)

**Tham số**: `code` — uniqueCode của lead trader trên OKX

```bash
curl -X POST https://<DOMAIN>/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"code":"EF1CC6F40E834D1A"}'
```

Trả về BẢN TÓM TẮT gọn (điểm rủi ro, điểm chất lượng, xếp loại, các chỉ số
chính từ mô phỏng Monte Carlo, và lý do điểm rủi ro là do bình quân hay do một
veto quyết định) kèm `report_url` -- link tới trang HTML báo cáo đầy đủ (biểu
đồ, sở cứ từng chiều, breakdown chi tiết). Bản tóm tắt này dưới 5 KB; toàn bộ
dữ liệu chi tiết nằm ở trang `report_url`, không nằm trong JSON trả về. 8-15
giây tuỳ số lệnh.

### `serviceDescription` đăng ký A2MCP (agentId 13753, serviceId
`75cdccb8-939d-4347-84a9-ce7d38277065`)

Bản đang đăng ký trên OKX AI Marketplace thiếu tiêu đề bắt buộc cho từng dòng.
Hợp đồng dịch vụ A2MCP của OKX yêu cầu đúng bốn dòng đánh số, MỖI dòng có
tiêu đề trong ngoặc vuông ở đầu -- đây là nguồn dự phòng caller đọc khi
endpoint không tự trả được `requestSpec` trong thân lỗi của nó (xem
`Agent/backend/web/app.py`'s `_REQUEST_SPEC`), nên phải đúng định dạng, không
chỉ đúng nội dung. Thay khối bốn dòng cũ bằng khối sau khi cập nhật listing:

```
1. [Service Description] Returns a compact risk-assessment summary (score, verdict, key metrics) for an OKX copy-trading lead trader plus a report_url link to the full detailed report, computed only from public closed-trade data.
2. [Parameter Spec] code(string, required): the lead trader uniqueCode on OKX, e.g. EF1CC6F40E834D1A
3. [Request Method] POST
4. [Request Example] curl -X POST https://agent.expsolution.io/api/analyze -H "Content-Type: application/json" -d '{"code":"EF1CC6F40E834D1A"}'
```

**TUYỆT ĐỐI KHÔNG tự chạy lệnh cập nhật listing này trên OKX** -- đây là thay
đổi ra bên ngoài (đổi thông tin trên marketplace của OKX), chủ dự án phải
duyệt trước. Khối trên chỉ ghi lại đúng nội dung cần dán vào form khi được
phê duyệt.

## Dịch vụ 3 — Dashboard cho người xem

**Địa chỉ**: `https://<DOMAIN>/`

Giao diện web xem bằng mắt: danh sách bot xếp theo mức cần xử lý, phiếu chi tiết
từng bot, và ô tra cứu bất kỳ uniqueCode nào.

---

## Những điều cần nói đúng trong phần mô tả

OKX AI Agent Marketplace User Agreement cấm agent đưa ra lời khuyên đầu tư nếu
nhà cung cấp không có giấy phép tương ứng. Vì vậy phần mô tả trên:

- Gọi đúng tên sản phẩm là **đánh giá rủi ro**, không phải khuyến nghị mua bán
- Nêu rõ **không phải lời khuyên đầu tư**
- Nêu rõ **không đặt lệnh, không truy cập tài khoản người khác**

Giữ nguyên tinh thần này nếu chỉnh sửa lại câu chữ.

## Điểm cần theo dõi sau khi đăng

OKX có quyền gọi thử agent để kiểm định mà không trả phí (điều khoản "Sampling").
Endpoint phải chịu được việc đó — rate limit hiện đặt 5 lần/phút cho mỗi IP ở
`/api/analyze`, đủ rộng cho kiểm định nhưng vẫn chặn lạm dụng.
