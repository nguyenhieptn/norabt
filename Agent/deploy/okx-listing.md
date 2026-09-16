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
Chấm điểm rủi ro lead trader OKX từ dữ liệu công khai: mô phỏng 10.000 kịch bản
trên sổ lệnh đã chốt, xếp 4 mức, kèm giải thích vì sao.
```

## Mô tả đầy đủ
```
Nhập uniqueCode của một lead trader OKX, nhận lại đánh giá rủi ro có cơ sở.

Hệ thống chỉ dùng dữ liệu công khai của OKX, chỉ tính trên LỆNH ĐÃ CHỐT, và
nói rõ những gì không đo được thay vì đoán.

Đo gì:
- Mô phỏng 10.000 kịch bản bằng stationary bootstrap (Politis & Romano 1994)
  trên chính sổ lệnh của bot, cho ra phân vị lãi/lỗ và rủi ro đuôi
- Probabilistic Sharpe Ratio và Deflated Sharpe Ratio (Bailey & López de Prado)
  để tách lợi thế thật khỏi may mắn do được chọn trong nhiều ứng viên
- Khoảng cách giữa sổ đã chốt và sổ đang mở — phát hiện mẫu chốt lời sớm, ôm lỗ chờ gỡ
- Phân tích hành vi theo pha thị trường
- Xếp loại: AN TOÀN / TIỀM NĂNG / TIỀM ẨN / NGUY HIỂM, kèm điểm chất lượng và
  điểm rủi ro riêng biệt, và một bản giải thích bằng văn bản

Nguyên tắc: thiếu dữ liệu không bao giờ được quy thành an toàn. Bot không công
khai sổ lệnh vẫn đánh giá được ở mức hạn chế, nhưng điểm rủi ro CAO HƠN và độ
tin cậy THẤP HƠN một bot minh bạch cùng số liệu bề mặt.

Không phải lời khuyên đầu tư. Không đặt lệnh, không truy cập tài khoản của ai.
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

Trả về điểm rủi ro, điểm chất lượng, xếp loại, kết quả mô phỏng Monte Carlo và
bản giải thích bằng văn bản. 8-15 giây tuỳ số lệnh.

### `serviceDescription` đăng ký A2MCP (agentId 13753, serviceId
`75cdccb8-939d-4347-84a9-ce7d38277065`)

Bản đang đăng ký trên OKX AI Marketplace thiếu tiêu đề bắt buộc cho từng dòng.
Hợp đồng dịch vụ A2MCP của OKX yêu cầu đúng bốn dòng đánh số, MỖI dòng có
tiêu đề trong ngoặc vuông ở đầu -- đây là nguồn dự phòng caller đọc khi
endpoint không tự trả được `requestSpec` trong thân lỗi của nó (xem
`Agent/backend/web/app.py`'s `_REQUEST_SPEC`), nên phải đúng định dạng, không
chỉ đúng nội dung. Thay khối bốn dòng cũ bằng khối sau khi cập nhật listing:

```
1. [Service Description] Returns a risk assessment for an OKX copy-trading lead trader, computed only from public closed-trade data.
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
