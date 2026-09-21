# STORY-02.1: INSTRUMENT AND CONTRACT METADATA

> **Document ID:** STORY-02.1
> **Type:** STORY
> **Status:** PARTIAL
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Parent PRD:** [PRD-02](../../spec/01_prd_engine1/PRD-02_OKX_CEX_DATA_FOUNDATION.md)
> **Source of truth for:** Đồng bộ metadata instrument/contract trước mọi conversion.
> **Supersedes:** Related fragment in legacy BMAD documents

## 1. Purpose and boundary

Đồng bộ metadata instrument/contract trước mọi conversion.

Story này chỉ sở hữu behavior trên. Nó không tự mở rộng sang data acquisition, scoring, reporting hoặc execution ngoài phần được nêu rõ.

## 2. Current baseline

Relevant current paths: `backend/ingestor/screener.py`, `backend/ingestor/ws_streamer.py`, `backend/ingestor/deep_analytics.py`, `backend/core/engine_1/orderbook_l2.py`.

- Status `PARTIAL` phản ánh mức evidence hiện có, không phải tiến độ marketing.
- Code comment hoặc file tồn tại không đủ để đổi thành `CURRENT-VERIFIED`; cần evidence tại Section 9.

## 2.1 Official OKX source contract

- Endpoint: `GET /api/v5/public/instruments?instType=SWAP`.
- Documentation: [https://www.okx.com/docs-v5/en/#public-data-rest-api-get-instruments](https://www.okx.com/docs-v5/en/#public-data-rest-api-get-instruments).
- Access class: public read; REST limits are endpoint-specific and generally scoped by IP.
- Required fields must be confirmed against the live schema before `CURRENT-VERIFIED`: `instId`, `instType`, `state`, currencies, contract value/multiplier, tick/lot/min sizes and listing/expiry fields.

## 3. Inputs

- Public `GET /api/v5/public/instruments?instType=SWAP`.
- Fields: instId, instType, state, baseCcy/quoteCcy/settleCcy, ctVal, ctMult, ctValCcy, tickSz, lotSz, minSz, listTime, expTime.

## 4. Processing rules

- Chỉ `state=live` và policy-supported settlement được eligible.
- Tạo canonical instrument ID; lưu raw units và conversion lineage.
- Không nhân volume với price khi chưa biết semantics `volCcy24h`/contract value.

## 5. Output contract

- `InstrumentSpec` versioned theo observed_at.
- Reason `UNSUPPORTED_CONTRACT` hoặc `METADATA_STALE`.

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

- **AC-2.1.1:** Fixture linear/inverse contracts cho conversion đúng.
- **AC-2.1.2:** Delisted/suspended instrument bị loại trước universe.

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
