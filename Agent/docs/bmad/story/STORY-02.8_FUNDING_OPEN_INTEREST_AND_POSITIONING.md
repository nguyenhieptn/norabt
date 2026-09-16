# STORY-02.8: FUNDING OPEN INTEREST AND POSITIONING

> **Document ID:** STORY-02.8
> **Type:** STORY
> **Status:** PARTIAL
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Parent PRD:** [PRD-02](../prd/PRD-02_OKX_CEX_DATA_FOUNDATION.md)
> **Source of truth for:** Chuẩn hóa funding, OI, delta-OI và long/short evidence.
> **Supersedes:** Related fragment in legacy BMAD documents

## 1. Purpose and boundary

Chuẩn hóa funding, OI, delta-OI và long/short evidence.

Story này chỉ sở hữu behavior trên. Nó không tự mở rộng sang data acquisition, scoring, reporting hoặc execution ngoài phần được nêu rõ.

## 2. Current baseline

Relevant current paths: `backend/ingestor/screener.py`, `backend/ingestor/ws_streamer.py`, `backend/ingestor/deep_analytics.py`, `backend/core/engine_1/orderbook_l2.py`.

- Status `PARTIAL` phản ánh mức evidence hiện có, không phải tiến độ marketing.
- Code comment hoặc file tồn tại không đủ để đổi thành `CURRENT-VERIFIED`; cần evidence tại Section 9.

## 2.1 Official OKX source contract

- Funding: `GET /api/v5/public/funding-rate` and funding-rate history/channel.
- Open interest: `GET /api/v5/public/open-interest`, OI channel and contract OI history statistics.
- Positioning: documented contract/top-trader long-short ratio endpoints.
- Documentation: [funding](https://www.okx.com/docs-v5/en/#public-data-rest-api-get-funding-rate), [OI](https://www.okx.com/docs-v5/en/#public-data-rest-api-get-open-interest), [OI history](https://www.okx.com/docs-v5/en/#trading-statistics-rest-api-get-contract-open-interest-history), [contract long-short ratio](https://www.okx.com/docs-v5/en/#trading-statistics-rest-api-get-contract-long-short-ratio).
- Access class, exact parameter names and rate limit are endpoint-specific and must be copied from the official section into implementation evidence; do not infer them from legacy docs.

## 3. Inputs

- Funding current/history, OI current/history, long-short statistics.

## 4. Processing rules

- Dùng event time và common cutoff.
- Tính delta/z-score trên series đủ mẫu; thiếu mẫu trả INSUFFICIENT_DATA.
- Giữ rate decimal khác percentage display.
- Không gọi ratio là “smart money” nếu source không xác định participant class.

## 5. Output contract

- `DerivativesEvidence` + sample/quality metadata.

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

- **AC-2.8.1:** No-data không thành funding=0.01% hay z=0.
- **AC-2.8.2:** Timestamp misalignment bị flag.

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
