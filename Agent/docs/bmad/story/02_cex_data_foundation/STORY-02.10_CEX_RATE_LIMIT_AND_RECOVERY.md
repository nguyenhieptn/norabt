# STORY-02.10: CEX RATE LIMIT AND RECOVERY

> **Document ID:** STORY-02.10
> **Type:** STORY
> **Status:** TARGET
> **Scope:** TARGET
> **Evidence as of:** 2026-09-12
> **Parent PRD:** [PRD-02](../../spec/01_prd_engine1/PRD-02_OKX_CEX_DATA_FOUNDATION.md)
> **Source of truth for:** Lập request/subscription budget cho Top 50.
> **Supersedes:** Related fragment in legacy BMAD documents

## 1. Purpose and boundary

Lập request/subscription budget cho Top 50.

Story này chỉ sở hữu behavior trên. Nó không tự mở rộng sang data acquisition, scoring, reporting hoặc execution ngoài phần được nêu rõ.

## 2. Current baseline

Relevant current paths: `backend/ingestor/screener.py`, `backend/ingestor/ws_streamer.py`, `backend/ingestor/deep_analytics.py`, `backend/core/engine_1/orderbook_l2.py`.

- Status `TARGET` phản ánh mức evidence hiện có, không phải tiến độ marketing.
- Code comment hoặc file tồn tại không đủ để đổi thành `CURRENT-VERIFIED`; cần evidence tại Section 9.

## 2.1 Official OKX source contract

- Reference: [https://www.okx.com/docs-v5/en/](https://www.okx.com/docs-v5/en/), in each endpoint section.
- Limits vary by endpoint and scope: public REST is generally IP-scoped, private REST user-scoped, and WebSocket connections/subscriptions connection/IP-scoped. Error `50011` represents rate-limit rejection in the current reference. No single global number may be applied to all feeds.

## 3. Inputs

- Endpoint-specific limits, universe size, refresh cadence.

## 4. Processing rules

- Token bucket theo endpoint scope; jitter ngoài mốc đồng loạt.
- Retry chỉ lỗi retryable, honor backoff; circuit-break repeated failures.
- Partial refresh giữ old data nhưng mark stale.
- Metrics cho 429/reconnect/gap.

## 5. Output contract

- `SourceHealth` và budget report.

Mọi output phải mang `schema_version`, `methodology_version` nếu có tính toán, `as_of`, availability/quality và reason codes phù hợp.

## 6. Failure, missing, stale and fallback behavior

- Malformed input: reject hoặc quarantine với typed reason; không coerce thành favorable value.
- Missing required evidence: trả `MISSING`, `UNKNOWN` hoặc `INSUFFICIENT_DATA` theo ngữ nghĩa.
- Stale evidence: giữ last observation để audit nhưng không trình bày là live.
- Fallback/synthetic evidence: luôn gắn nguồn và confidence penalty; policy có thể chuyển item sang `OBSERVE_ONLY` hoặc `EXCLUDED`.

## 7. Security and capability constraints

- Logic phân tích không được tự gọi order, transfer, withdrawal, wallet signing hoặc transaction broadcast.
- Secret/credential không xuất hiện trong state, log, report hoặc fixture.
- Rank, risk tier và assessment không phải authorization thực thi.

## 8. Acceptance criteria

- **AC-2.10.1:** Load test Top 50 không vượt limit.
- **AC-2.10.2:** 429 không gây loop nóng hoặc dữ liệu giả tươi.

## 9. Verification evidence required

| Evidence | Requirement |
|---|---|
| Source/spec | File path hiện có và, nếu liên quan OKX, official documentation URL đã kiểm tra |
| Fixtures | Happy path, boundary, malformed, missing và stale/fallback case |
| Repeatability | Command/test chạy lại được với expected/actual result |
| Context | Environment, dataset/fixture version, methodology version, timestamp |
| Traceability | Evidence link được ghi vào STORY-10 tương ứng trước khi mark verified |

## 10. Known gaps and out of scope

- Các behavior ngoài acceptance criteria thuộc story khác hoặc PRD khác.
- Nếu current code không khớp target contract, ghi gap; không sửa nghĩa tài liệu để hợp thức hóa code.
- Engine 2 và automatic control of trading agents không thuộc story này.
