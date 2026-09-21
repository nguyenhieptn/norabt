# STORY-02.9: LIQUIDATION EVIDENCE

> **Document ID:** STORY-02.9
> **Type:** STORY
> **Status:** BLOCKED
> **Scope:** TARGET
> **Evidence as of:** 2026-09-12
> **Parent PRD:** [PRD-02](../../spec/01_prd_engine1/PRD-02_OKX_CEX_DATA_FOUNDATION.md)
> **Source of truth for:** Xác minh liquidation source và giới hạn dùng trong Engine 1.
> **Supersedes:** Related fragment in legacy BMAD documents

## 1. Purpose and boundary

Xác minh liquidation source và giới hạn dùng trong Engine 1.

Story này chỉ sở hữu behavior trên. Nó không tự mở rộng sang data acquisition, scoring, reporting hoặc execution ngoài phần được nêu rõ.

## 2. Current baseline

Relevant current paths: `backend/ingestor/screener.py`, `backend/ingestor/ws_streamer.py`, `backend/ingestor/deep_analytics.py`, `backend/core/engine_1/orderbook_l2.py`.

- Status `BLOCKED` phản ánh mức evidence hiện có, không phải tiến độ marketing.
- Code comment hoặc file tồn tại không đủ để đổi thành `CURRENT-VERIFIED`; cần evidence tại Section 9.

## 2.1 Official OKX source contract

- Candidate source: public WebSocket liquidation-orders channel.
- Documentation: [https://www.okx.com/docs-v5/en/#public-data-websocket-liquidation-orders-channel](https://www.okx.com/docs-v5/en/#public-data-websocket-liquidation-orders-channel).
- Status remains `BLOCKED` until delivery semantics, market coverage, fields and suitability for cluster analysis are verified.

## 3. Inputs

- Official liquidation-orders channel nếu available.

## 4. Processing rules

- Xác minh fields, delivery semantics, scope và retention.
- Không suy diễn cluster price nếu source chỉ là event stream không đầy đủ.
- Nếu unsupported, trả `SOURCE_UNAVAILABLE`.

## 5. Output contract

- `LiquidationEvidence | UnsupportedEvidence`.

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

- **AC-2.9.1:** Official source citation bắt buộc.
- **AC-2.9.2:** Không có source thì Engine 1 confidence giảm, không fake values.

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
