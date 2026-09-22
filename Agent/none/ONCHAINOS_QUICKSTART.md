# Quickstart: Dùng Nora Risk Agent

## Cách 1 — Qua AI Agent (AGY / Codex)

1. Cài OnchainOS: 
px -y @okxweb3/onchainos-installer install
2. Đăng nhập ví OKX: onchainos wallet login
3. Prompt vào AGY:

> **Dùng Agent SID 40700 trên OnchainOS kiểm tra bot OKX mã EF1CC6F40E834D1A**

Thay EF1CC6F40E834D1A bằng mã bot cần kiểm tra. AGY tự chạy và trả kết quả.

---

## Cách 2 — Qua Terminal

1. Cài OnchainOS: 
px -y @okxweb3/onchainos-installer install
2. Đăng nhập ví OKX: onchainos wallet login
3. Chạy:

`ash
bash run-nora.sh EF1CC6F40E834D1A
`

---

## Kết quả trả về

- 🟢 **PASS** — An toàn.
- 🟡 **HIDDEN RISK** — Rủi ro tiềm ẩn.
- 🔴 **REJECT** — Nguy hiểm.

Kèm link báo cáo chi tiết (biểu đồ, Monte Carlo 10.000 kịch bản).

---

**Agent SID:** 40700 · **Agent ID:** 13753

