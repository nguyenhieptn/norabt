# PRD-04: DATA QUALITY, PROVENANCE VÀ STATE

> **Document ID:** PRD-04
> **Type:** PRD
> **Status:** PARTIAL
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Source of truth for:** Tính đúng, truy nguyên và khả năng tái tạo assessment
> **Supersedes:** Legacy PRD content removed; this document is the active source of truth.

## 1. Purpose and boundary

Định nghĩa lớp chất lượng bắt buộc giữa OKX adapters và Engine 1 để hệ thống không nhầm missing, stale, synthetic hoặc sai units thành bằng chứng tốt.

## 2. Current baseline

- CEX candles/tickers đã có canonical normalizer và typed provenance/quality models; remaining evidence feeds chưa migrate hết.
- `backend/data` là authoritative StateBus/FileStorage/PriceActionMatrix; duplicate `backend/cache`, `backend/gateway` và `backend/wallet` đã được loại bỏ.
- New assessments carry schema/methodology/as-of/provenance; legacy snapshot compatibility remains a migration concern.

## 3. Target behavior

- Mọi observation có provenance envelope.
- Một normalization/versioning policy, một bounded state contract và một assessment storage contract.
- Quality/completeness/freshness ảnh hưởng eligibility và confidence.
- Assessment có thể tái tạo từ immutable input references.

## 4. Inputs

- Raw payload + source metadata.
- Normalization rules.
- Freshness thresholds.
- State retention/version policy.

## 5. Processing and policy rules

- Không overwrite source lineage bằng derived value.
- Fallback/synthetic/stale flags được giữ đến report.
- Duplicate/out-of-order/gap không được âm thầm bỏ qua.
- Bounded-memory được mô tả đúng; không claim zero-allocation khi chưa đo.

## 6. Required outputs

- `ObservationEnvelope[T]`.
- `DataQuality` và reason codes.
- Versioned candle/evidence/assessment state.
- Reproducibility manifest.

## 7. Error, missing, stale and fallback behavior

- Source error phải có typed status và thời điểm; không trả dữ liệu cũ như dữ liệu mới.
- Missing và not-applicable là hai trạng thái khác nhau.
- Fallback phải giữ origin, age, synthetic flag và confidence penalty đến report cuối.
- Không được suy ra `LOW`, `APPROVED`, neutral ratio hoặc zero risk chỉ vì không có dữ liệu.

## 8. Acceptance criteria

- **AC-4.1:** Mọi input Engine 1 có quality state.
- **AC-4.2:** Chỉ một authoritative Redis schema.
- **AC-4.3:** Assessment ID liên kết universe, methodology và input snapshots.
- **AC-4.4:** Restart/recovery không làm mất semantics freshness.

## 9. Child stories

- [04.1 RAW_OBSERVATION_ENVELOPE](../story/STORY-04.1_RAW_OBSERVATION_ENVELOPE.md) — `TARGET`
- [04.2 NORMALIZATION_AND_UNITS](../story/STORY-04.2_NORMALIZATION_AND_UNITS.md) — `PARTIAL`
- [04.3 FRESHNESS_AND_STALENESS](../story/STORY-04.3_FRESHNESS_AND_STALENESS.md) — `TARGET`
- [04.4 MISSING_AND_FALLBACK_SEMANTICS](../story/STORY-04.4_MISSING_AND_FALLBACK_SEMANTICS.md) — `TARGET`
- [04.5 DEDUP_GAP_AND_ORDERING](../story/STORY-04.5_DEDUP_GAP_AND_ORDERING.md) — `TARGET`
- [04.6 BOUNDED_CANDLE_STATE](../story/STORY-04.6_BOUNDED_CANDLE_STATE.md) — `PARTIAL`
- [04.7 ASSESSMENT_STATE_STORAGE](../story/STORY-04.7_ASSESSMENT_STATE_STORAGE.md) — `PARTIAL`
- [04.8 SNAPSHOT_AND_REPRODUCIBILITY](../story/STORY-04.8_SNAPSHOT_AND_REPRODUCIBILITY.md) — `TARGET`
- [04.9 DATA_QUALITY_SCORE](../story/STORY-04.9_DATA_QUALITY_SCORE.md) — `TARGET`

## 10. Verification evidence required

- Source path hoặc official specification cho từng current claim.
- Repeatable test/command, fixture hoặc dataset version, environment và timestamp.
- Expected result, actual result và evidence location.
- Mọi mismatch phải ghi `KNOWN GAP`; không được tự mark verified.

## 11. Known gaps

- Legacy duplicate infrastructure packages have been removed; repository integration evidence is still incomplete.
- Không có common observation envelope.
- Current defaults che giấu missing evidence.

## 12. Traceability

- Root scope: [PRD-01](PRD-01_ENGINE1_SCOPE_AND_SUCCESS.md)
- Completion gates: [PRD-10](PRD-10_ENGINE1_VERIFICATION_AND_DEFINITION_OF_DONE.md)
- Official OKX API index used for CEX verification: [https://www.okx.com/docs-v5/en/](https://www.okx.com/docs-v5/en/)
