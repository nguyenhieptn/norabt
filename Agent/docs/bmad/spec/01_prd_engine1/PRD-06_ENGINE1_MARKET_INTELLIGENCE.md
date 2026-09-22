# PRD-06: ENGINE 1 MARKET INTELLIGENCE

> **Document ID:** PRD-06
> **Type:** PRD
> **Status:** PARTIAL
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Source of truth for:** Hợp nhất bằng chứng thành trạng thái thị trường
> **Supersedes:** Legacy PRD content removed; this document is the active source of truth.

## 1. Purpose and boundary

Xây dựng market intelligence từ regime, price structure, volatility, order flow, derivatives, benchmark, breadth và liquidity mà chưa đưa ra lệnh giao dịch.

## 2. Current baseline

- Các analyzer riêng đã tồn tại nhưng full evaluator nhận nhiều primitive/default và chưa chạy live.
- CVD hiện suy từ volume/close khi thiếu trade-side data; cần gắn estimation source.
- BTC/breadth/sentiment defaults có thể trông như observed values.

## 3. Target behavior

- Per-instrument intelligence có source applicability/confidence.
- Market-wide breadth và sentiment tổng hợp từ cùng universe snapshot.
- Measured và estimated evidence được phân biệt.
- Mỗi kết luận có reason codes.

## 4. Inputs

- Regime assessment.
- Normalized price/flow/derivatives/book/benchmark evidence.
- Data quality và cohort identity.

## 5. Processing and policy rules

- Không action recommendation trong intelligence.
- Không dùng CEX metrics cho DEX khi không applicable.
- Estimate phải có estimator/version/confidence.
- Market-wide statistics dùng cùng as-of cutoff.

## 6. Required outputs

- `MarketIntelligence` per item.
- `MarketOverview` toàn cohort.
- Supporting/contradicting reason codes.

## 7. Error, missing, stale and fallback behavior

- Source error phải có typed status và thời điểm; không trả dữ liệu cũ như dữ liệu mới.
- Missing và not-applicable là hai trạng thái khác nhau.
- Fallback phải giữ origin, age, synthetic flag và confidence penalty đến report cuối.
- Không được suy ra `LOW`, `APPROVED`, neutral ratio hoặc zero risk chỉ vì không có dữ liệu.

## 8. Acceptance criteria

- **AC-6.1:** Mọi field chỉ rõ measured/estimated/missing.
- **AC-6.2:** Market overview và per-item result cùng assessment ID.
- **AC-6.3:** Reason codes giải thích status/sentiment/volatility.
- **AC-6.4:** Missing source làm giảm confidence thay vì tạo neutral value.

## 9. Child stories

- [06.1 PRICE_STRUCTURE_AND_RANGE_LOCATION](../../story/06_market_intelligence/STORY-06.1_PRICE_STRUCTURE_AND_RANGE_LOCATION.md) — `PARTIAL`
- [06.2 TREND_STATE_AND_STRENGTH](../../story/06_market_intelligence/STORY-06.2_TREND_STATE_AND_STRENGTH.md) — `TARGET`
- [06.3 REALIZED_AND_RELATIVE_VOLATILITY](../../story/06_market_intelligence/STORY-06.3_REALIZED_AND_RELATIVE_VOLATILITY.md) — `TARGET`
- [06.4 CVD_AND_FLOW_BIAS](../../story/06_market_intelligence/STORY-06.4_CVD_AND_FLOW_BIAS.md) — `PARTIAL`
- [06.5 ORDERBOOK_IMBALANCE_AND_ABSORPTION](../../story/06_market_intelligence/STORY-06.5_ORDERBOOK_IMBALANCE_AND_ABSORPTION.md) — `PARTIAL`
- [06.6 FUNDING_OI_AND_POSITIONING_INTERPRETATION](../../story/06_market_intelligence/STORY-06.6_FUNDING_OI_AND_POSITIONING_INTERPRETATION.md) — `PARTIAL`
- [06.7 BTC_BENCHMARK_BETA_AND_CORRELATION](../../story/06_market_intelligence/STORY-06.7_BTC_BENCHMARK_BETA_AND_CORRELATION.md) — `PARTIAL`
- [06.8 MARKET_BREADTH_AND_SENTIMENT_STATE](../../story/06_market_intelligence/STORY-06.8_MARKET_BREADTH_AND_SENTIMENT_STATE.md) — `TARGET`
- [06.9 CEX_LIQUIDITY_AND_SLIPPAGE_EVIDENCE](../../story/06_market_intelligence/STORY-06.9_CEX_LIQUIDITY_AND_SLIPPAGE_EVIDENCE.md) — `PARTIAL`
- [06.10 DEX_MARKET_INTELLIGENCE_APPLICABILITY](../../story/06_market_intelligence/STORY-06.10_DEX_MARKET_INTELLIGENCE_APPLICABILITY.md) — `TARGET`
- [06.11 MARKET_INTELLIGENCE_FUSION](../../story/06_market_intelligence/STORY-06.11_MARKET_INTELLIGENCE_FUSION.md) — `PARTIAL`

## 10. Verification evidence required

- Source path hoặc official specification cho từng current claim.
- Repeatable test/command, fixture hoặc dataset version, environment và timestamp.
- Expected result, actual result và evidence location.
- Mọi mismatch phải ghi `KNOWN GAP`; không được tự mark verified.

## 11. Known gaps

- Full runtime fusion chưa có.
- Sentiment/breadth contract chưa đầy đủ.
- CVD provenance chưa rõ.

## 12. Traceability

- Root scope: [PRD-01](PRD-01_ENGINE1_SCOPE_AND_SUCCESS.md)
- Completion gates: [PRD-10](PRD-10_ENGINE1_VERIFICATION_AND_DEFINITION_OF_DONE.md)
- Official OKX API index used for CEX verification: [https://www.okx.com/docs-v5/en/](https://www.okx.com/docs-v5/en/)
