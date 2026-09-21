# STORY-02.6: ORDERBOOK L2

> **Document ID:** STORY-02.6
> **Type:** STORY
> **Status:** PARTIAL
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Parent PRD:** [PRD-02](../../spec/01_prd_engine1/PRD-02_OKX_CEX_DATA_FOUNDATION.md)
> **Source of truth for:** Thu orderbook đủ tin cậy để đánh giá depth/imbalance/slippage.
> **Supersedes:** Related fragment in legacy BMAD documents

## 1. Purpose and boundary

Thu orderbook đủ tin cậy để đánh giá depth/imbalance/slippage.

Story này chỉ sở hữu behavior trên. Nó không tự mở rộng sang data acquisition, scoring, reporting hoặc execution ngoài phần được nêu rõ.

## 2. Current baseline

Relevant current paths: `backend/ingestor/screener.py`, `backend/ingestor/ws_streamer.py`, `backend/ingestor/deep_analytics.py`, `backend/core/engine_1/orderbook_l2.py`.

- Status `PARTIAL` phản ánh mức evidence hiện có, không phải tiến độ marketing.
- Code comment hoặc file tồn tại không đủ để đổi thành `CURRENT-VERIFIED`; cần evidence tại Section 9.

## 2.1 Official OKX source contract

- REST: `GET /api/v5/market/books`; WebSocket: order-book channels.
- Documentation: [https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-order-book](https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-order-book) and [WS order book](https://www.okx.com/docs-v5/en/#order-book-trading-market-data-ws-order-book-channel).
- Access class: public read/subscription. Depth, update mode, sequence/checksum support and limits depend on selected channel and must be captured in implementation evidence.

## 3. Inputs

- Official order-book REST/WS source.
- Instrument contract metadata.

## 4. Processing rules

- Xác định snapshot/update mode, depth levels và sequence/checksum policy.
- Convert size sang notional bằng contract spec.
- Tính depth theo price band, không nhầm bid/ask direction.
- Mark stale nếu book age vượt threshold.

## 5. Output contract

- `OrderBookSnapshot`, depth bands, spread, imbalance + quality.

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

- **AC-2.6.1:** Known book fixture cho đúng notional/depth.
- **AC-2.6.2:** Sequence gap làm quality invalid.

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
