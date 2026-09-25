# Quickstart: Dùng Nora Risk Agent

Nora có **2 chế độ chạy**, dùng chung một tham số `code`:

| Chế độ | Nhập | Kết quả |
|---|---|---|
| **Single** — 1 bot | 1 mã bot | Báo cáo rủi ro của bot đó |
| **Multi** — danh mục 2–8 bot | 2–8 mã bot, cách nhau bằng dấu phẩy hoặc khoảng trắng | Một báo cáo chung cho cả danh mục: tương quan giữa các bot, Monte Carlo chung (joint), đóng góp của từng bot |

Đủ 2 mã trở lên thì hệ thống tự chạy chế độ Multi, không cần tham số khác.

---

## Cách 1 — Qua AI Agent (AGY / Codex)

1. Cài OnchainOS: `npx -y @okxweb3/onchainos-installer install`
2. Đăng nhập ví OKX: `onchainos wallet login`
3. Prompt vào AGY:

**Single — 1 bot**

> **Dùng Agent SID 40700 trên OnchainOS kiểm tra bot OKX mã EF1CC6F40E834D1A**

**Multi — danh mục nhiều bot (2–8 mã)**

> **Dùng Agent SID 40700 trên OnchainOS kiểm tra danh mục gồm các bot OKX mã 35F888C7BB441B2B, 6F262ADB3B44266C**

Thay các mã trên bằng mã bot cần kiểm tra. AGY tự chạy và trả kết quả.

---

## Cách 2 — Qua Terminal (máy nào cũng chạy được, không cần mã nguồn)

1. Cài OnchainOS: `npx -y @okxweb3/onchainos-installer install`
2. Đăng nhập ví OKX: `onchainos wallet login`
3. Gọi Agent SID 40700 qua OKX (thay `code` bằng mã cần kiểm tra):

```bash
# 3a. Gửi yêu cầu -> OKX trả về một confirmationId
onchainos agent a2mcp-probe probe \
  --routing-json '{"schemaVersion":1,"serviceSnapshot":{"serviceType":"A2MCP","endpoint":"https://agent.expsolution.io/api/analyze","serviceId":40700}}' \
  --params-json '{"code":"EF1CC6F40E834D1A"}'

# 3b. Xác nhận (dịch vụ miễn phí) -> nhận kết quả
onchainos agent a2mcp-probe confirm-free --confirmation-id <confirmationId> --yes
```

**Multi — danh mục 2–8 bot:** chỉ đổi `--params-json`, các mã cách nhau bằng dấu phẩy:

```bash
--params-json '{"code":"35F888C7BB441B2B,6F262ADB3B44266C"}'
```

> Đã có mã nguồn repo: `bash Agent/docker/run-nora.sh <mã> [mã ...]` chạy gộp 3a + 3b, và tự tra endpoint bằng `onchainos agent service-detail --sid 40700 --agentic-id 13753`.

---

## Kết quả trả về

- 🟢 **PASS** — An toàn.
- 🟡 **HIDDEN RISK** — Rủi ro tiềm ẩn.
- 🔴 **REJECT** — Nguy hiểm.

Kèm link báo cáo chi tiết (biểu đồ, Monte Carlo 10.000 kịch bản):

- **Single:** `https://agent.expsolution.io/bot/<mã bot>`
- **Multi:** `https://agent.expsolution.io/portfolio/<mã danh mục>` — thêm phần tương quan giữa các bot, Monte Carlo chung (joint) và đóng góp của từng bot. Bot ẩn sổ lệnh vẫn được tính qua PnL công khai theo ngày.

---

**Agent SID:** 40700 · **Agent ID:** 13753
