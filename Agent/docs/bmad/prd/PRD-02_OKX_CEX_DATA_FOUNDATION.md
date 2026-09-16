# PRD-02: OKX CEX DATA FOUNDATION

> **Document ID:** PRD-02
> **Type:** PRD
> **Status:** PARTIAL
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Source of truth for:** Thu thập dữ liệu CEX OKX phục vụ Engine 1
> **Supersedes:** Legacy PRD content removed; this document is the active source of truth.

## 1. Purpose and boundary

Đặc tả riêng dữ liệu CEX cần lấy từ OKX, cách chọn universe và điều kiện để Top 50 khả thi mà không trộn logic DEX hoặc Engine 1.

## 2. Current baseline

- Có public tickers screener, REST candle warm-up, candle WebSocket, funding/OI/Rubik calls và orderbook calculator/fetcher.
- Runtime mặc định Top 50 qua một deterministic CEX refresh use case; live rate/resource evidence chưa hoàn tất.
- Warm-up và stream dùng cùng normalized confirmed-candle application path; fixture tests pass, live full-universe evidence còn thiếu.

## 3. Target behavior

- Catalog nguồn chính thức cho instruments, tickers, candles, trades/taker, books, funding, OI, positioning và liquidation.
- CEX Top 50 USDT SWAP có eligibility, units, rate budget, freshness và deterministic ranking.
- Backfill và stream tạo chuỗi closed-candle liên tục, deduplicated và timestamp-aligned.

## 4. Inputs

- OKX public REST/WebSocket payloads.
- Instrument metadata và contract value.
- Universe policy.
- Per-endpoint rate/freshness policy.

## 5. Processing and policy rules

- Chỉ official OKX source được ghi `source_type=OKX`.
- Không suy ra USD turnover nếu thiếu conversion lineage.
- BTC benchmark có thể luôn được quan sát nhưng không được giả là rank 1.
- Top 50 là TARGET/PARTIAL cho đến khi STORY-10.4 pass.

## 6. Required outputs

- Versioned CEX universe.
- Normalized CEX observation streams.
- Coverage/error/freshness state theo source và instrument.

## 7. Error, missing, stale and fallback behavior

- Source error phải có typed status và thời điểm; không trả dữ liệu cũ như dữ liệu mới.
- Missing và not-applicable là hai trạng thái khác nhau.
- Fallback phải giữ origin, age, synthetic flag và confidence penalty đến report cuối.
- Không được suy ra `LOW`, `APPROVED`, neutral ratio hoặc zero risk chỉ vì không có dữ liệu.

## 8. Acceptance criteria

- **AC-2.1:** Từng feed có endpoint/channel, permission, schema, units, event time, cadence, rate limit và source path.
- **AC-2.2:** Top 50 không vượt subscription/request budget đã tính.
- **AC-2.3:** Closed-candle invariant áp dụng cho warm-up và live.
- **AC-2.4:** Mất/gap/stale data được phát hiện và phản ánh vào quality.

## 9. Child stories

- [02.1 INSTRUMENT_AND_CONTRACT_METADATA](../story/STORY-02.1_INSTRUMENT_AND_CONTRACT_METADATA.md) — `PARTIAL`
- [02.2 CEX_UNIVERSE_DISCOVERY](../story/STORY-02.2_CEX_UNIVERSE_DISCOVERY.md) — `PARTIAL`
- [02.3 CEX_TOP50_SELECTION](../story/STORY-02.3_CEX_TOP50_SELECTION.md) — `PARTIAL`
- [02.4 CLOSED_CANDLE_BACKFILL](../story/STORY-02.4_CLOSED_CANDLE_BACKFILL.md) — `PARTIAL`
- [02.5 CLOSED_CANDLE_STREAM](../story/STORY-02.5_CLOSED_CANDLE_STREAM.md) — `PARTIAL`
- [02.6 ORDERBOOK_L2](../story/STORY-02.6_ORDERBOOK_L2.md) — `PARTIAL`
- [02.7 TRADES_AND_TAKER_FLOW](../story/STORY-02.7_TRADES_AND_TAKER_FLOW.md) — `PARTIAL`
- [02.8 FUNDING_OPEN_INTEREST_AND_POSITIONING](../story/STORY-02.8_FUNDING_OPEN_INTEREST_AND_POSITIONING.md) — `PARTIAL`
- [02.9 LIQUIDATION_EVIDENCE](../story/STORY-02.9_LIQUIDATION_EVIDENCE.md) — `BLOCKED`
- [02.10 CEX_RATE_LIMIT_AND_RECOVERY](../story/STORY-02.10_CEX_RATE_LIMIT_AND_RECOVERY.md) — `TARGET`

## 10. Verification evidence required

- Source path hoặc official specification cho từng current claim.
- Repeatable test/command, fixture hoặc dataset version, environment và timestamp.
- Expected result, actual result và evidence location.
- Mọi mismatch phải ghi `KNOWN GAP`; không được tự mark verified.

## 11. Known gaps

- Top 50 deterministic fixture pass; chưa có live sustained end-to-end evidence.
- Instrument contract metadata chưa nối vào volume conversion.
- Liquidation availability và exact semantics cần xác minh.

## 12. Traceability

- Root scope: [PRD-01](PRD-01_ENGINE1_SCOPE_AND_SUCCESS.md)
- Completion gates: [PRD-10](PRD-10_ENGINE1_VERIFICATION_AND_DEFINITION_OF_DONE.md)
- Official OKX API index used for CEX verification: [https://www.okx.com/docs-v5/en/](https://www.okx.com/docs-v5/en/)
