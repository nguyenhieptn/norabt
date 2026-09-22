# PRD-05: ENGINE 1 REGIME CORE

> **Document ID:** PRD-05
> **Type:** PRD
> **Status:** PARTIAL
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Source of truth for:** Lõi phân loại regime thuần toán học
> **Supersedes:** Legacy PRD content removed; this document is the active source of truth.

## 1. Purpose and boundary

Bóc tách lõi Engine 1: price regime, volatility regime, sustained range, multi-timeframe confluence và breakout/fakeout evidence.

## 2. Current baseline

- Có EMA/ATR/Keltner, sustained detector, micro/MTF classifier và breakout detector.
- Code đang dùng ATR-14/Keltner 1.5 trong full evaluator nhưng legacy path dùng multiplier 2.0; docs cũ nói ATR-20/dải kép.
- Macro resample chia chunk theo vị trí, chưa căn timestamp và nhận chunk chưa đủ.

## 3. Target behavior

- Một formula contract duy nhất.
- Regime taxonomy mutually exclusive và versioned.
- Timestamp-aligned multi-timeframe bars.
- Reason codes/confidence deterministic.

## 4. Inputs

- Closed, ordered OHLCV series có quality.
- Timeframe/calendar semantics.
- Versioned thresholds.
- Optional normalized flow confirmation.

## 5. Processing and policy rules

- Không network/storage/presentation/action policy trong regime core.
- Không dùng incomplete candle.
- Insufficient data trả explicit state.
- Threshold/formula thay đổi phải tăng methodology version.

## 6. Required outputs

- `RegimeAssessment` gồm micro, macro, confluence, volatility state, breakout state, confidence và reasons.

## 7. Error, missing, stale and fallback behavior

- Source error phải có typed status và thời điểm; không trả dữ liệu cũ như dữ liệu mới.
- Missing và not-applicable là hai trạng thái khác nhau.
- Fallback phải giữ origin, age, synthetic flag và confidence penalty đến report cuối.
- Không được suy ra `LOW`, `APPROVED`, neutral ratio hoặc zero risk chỉ vì không có dữ liệu.

## 8. Acceptance criteria

- **AC-5.1:** Golden fixtures xác nhận từng regime boundary.
- **AC-5.2:** Resample đúng UTC timeframe boundaries.
- **AC-5.3:** Cùng input/version cho cùng output.
- **AC-5.4:** ATR/Keltner/range contract khớp code được chọn làm authoritative.

## 9. Child stories

- [05.1 KELTNER_EMA](../../story/05_regime_core/STORY-05.1_KELTNER_EMA.md) — `CURRENT-UNVERIFIED`
- [05.2 TRUE_RANGE_AND_ATR](../../story/05_regime_core/STORY-05.2_TRUE_RANGE_AND_ATR.md) — `CURRENT-UNVERIFIED`
- [05.3 KELTNER_WIDTH_AND_VOLATILITY_STATE](../../story/05_regime_core/STORY-05.3_KELTNER_WIDTH_AND_VOLATILITY_STATE.md) — `PARTIAL`
- [05.4 SUSTAINED_RANGE](../../story/05_regime_core/STORY-05.4_SUSTAINED_RANGE.md) — `CURRENT-UNVERIFIED`
- [05.5 MICRO_REGIME_CLASSIFIER](../../story/05_regime_core/STORY-05.5_MICRO_REGIME_CLASSIFIER.md) — `PARTIAL`
- [05.6 TIMESTAMP_ALIGNED_MACRO_RESAMPLE](../../story/05_regime_core/STORY-05.6_TIMESTAMP_ALIGNED_MACRO_RESAMPLE.md) — `TARGET`
- [05.7 MULTI_TIMEFRAME_CONFLUENCE](../../story/05_regime_core/STORY-05.7_MULTI_TIMEFRAME_CONFLUENCE.md) — `PARTIAL`
- [05.8 BREAKOUT_AND_FAKEOUT](../../story/05_regime_core/STORY-05.8_BREAKOUT_AND_FAKEOUT.md) — `CURRENT-UNVERIFIED`
- [05.9 REGIME_HYSTERESIS](../../story/05_regime_core/STORY-05.9_REGIME_HYSTERESIS.md) — `PARTIAL`
- [05.10 REGIME_CONTRACT_AND_REASON_CODES](../../story/05_regime_core/STORY-05.10_REGIME_CONTRACT_AND_REASON_CODES.md) — `TARGET`

## 10. Verification evidence required

- Source path hoặc official specification cho từng current claim.
- Repeatable test/command, fixture hoặc dataset version, environment và timestamp.
- Expected result, actual result và evidence location.
- Mọi mismatch phải ghi `KNOWN GAP`; không được tự mark verified.

## 11. Known gaps

- Formula/taxonomy chưa reconcile.
- Test sustained-range hiện lỗi interface.
- Macro alignment chưa đúng.

## 12. Traceability

- Root scope: [PRD-01](PRD-01_ENGINE1_SCOPE_AND_SUCCESS.md)
- Completion gates: [PRD-10](PRD-10_ENGINE1_VERIFICATION_AND_DEFINITION_OF_DONE.md)
- Official OKX API index used for CEX verification: [https://www.okx.com/docs-v5/en/](https://www.okx.com/docs-v5/en/)
