# STORY-02.3: CEX TOP50 SELECTION

> **Document ID:** STORY-02.3
> **Type:** STORY
> **Status:** PARTIAL
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Parent PRD:** [PRD-02](../../spec/01_prd_engine1/PRD-02_OKX_CEX_DATA_FOUNDATION.md)
> **Source of truth for:** Chọn Top 50 CEX có khả năng phân tích tốt nhất, không chỉ token biến động mạnh.
> **Supersedes:** Related fragment in legacy BMAD documents

## 1. Purpose and boundary

Chọn Top 50 CEX có khả năng phân tích tốt nhất, không chỉ token biến động mạnh.

Story này chỉ sở hữu behavior trên. Nó không tự mở rộng sang data acquisition, scoring, reporting hoặc execution ngoài phần được nêu rõ.

## 2. Current baseline

Relevant current paths: `backend/ingestor/screener.py`, `backend/ingestor/ws_streamer.py`, `backend/ingestor/deep_analytics.py`, `backend/core/engine_1/orderbook_l2.py`.

- Status `PARTIAL` phản ánh mức evidence hiện có, không phải tiến độ marketing.
- Code comment hoặc file tồn tại không đủ để đổi thành `CURRENT-VERIFIED`; cần evidence tại Section 9.

## 2.1 Official OKX source contract

- Tickers endpoint: `GET /api/v5/market/tickers?instType=SWAP`.
- Documentation: [https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-tickers](https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-tickers).
- Access class: public read. Instrument eligibility comes from STORY-02.1/02.2; ticker volume units must be joined to contract metadata before an USD claim.

## 3. Inputs

- Eligible instruments.
- Normalized turnover, spread/depth, activity, freshness và quality.

## 4. Processing rules

- Eligibility trước scoring.
- Score components versioned; cap outlier; deterministic tie-break bằng instId.
- BTC được theo dõi như benchmark độc lập, không cưỡng ép rank 1.
- Nếu eligible <50, trả actual count và limitation.

## 5. Output contract

- `CexUniverseV1` tối đa 50 rows + score breakdown.

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

- **AC-2.3.1:** Top 50 deterministic.
- **AC-2.3.2:** Mỗi row có source/quality/as-of.
- **AC-2.3.3:** Runtime/rate budget được chứng minh ở STORY-10.4.

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
