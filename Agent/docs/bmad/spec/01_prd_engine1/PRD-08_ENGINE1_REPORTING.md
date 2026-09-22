# PRD-08: ENGINE 1 LIST, TABLE VÀ STATISTICAL REPORTING

> **Document ID:** PRD-08
> **Type:** PRD
> **Status:** TARGET
> **Scope:** TARGET
> **Evidence as of:** 2026-09-12
> **Source of truth for:** Đầu ra dễ đọc và machine-readable từ cùng assessment snapshot
> **Supersedes:** Legacy PRD content removed; this document is the active source of truth.

## 1. Purpose and boundary

Định nghĩa đầu ra cuối cùng để user/sếp nắm bắt nhanh: market summary, ranked list, comparison table, statistics và chi tiết lý do/rủi ro.

## 2. Current baseline

- MCP trả structured dictionaries cho universe, assessment, ranked assessments, report và capability registry.
- Application report builder xuất list/table/statistics từ cùng universe snapshot; live coverage evidence còn thiếu.
- Executive report cũ chứa số live-looking không có provenance.

## 3. Target behavior

- Một machine-readable report contract làm source-of-truth.
- Human rendering là pure projection.
- List/table/statistics cùng snapshot, methodology và cohort.
- Hiển thị rõ coverage, quality, freshness, missingness và limitations.

## 4. Inputs

- Market overview.
- Per-item assessments.
- Ranked rows.
- Provenance/quality manifest.

## 5. Processing and policy rules

- Không hard-code market values trong spec như dữ liệu live.
- Không dùng emoji làm schema semantics.
- Formatter không tự tính risk/score.
- Human text không được mạnh hơn machine state.

## 6. Required outputs

- Report header.
- Regime summary.
- CEX/DEX ranked lists.
- Comparison table.
- Coverage/distribution/breadth/outlier/missingness statistics.
- Per-item evidence detail.

## 7. Error, missing, stale and fallback behavior

- Source error phải có typed status và thời điểm; không trả dữ liệu cũ như dữ liệu mới.
- Missing và not-applicable là hai trạng thái khác nhau.
- Fallback phải giữ origin, age, synthetic flag và confidence penalty đến report cuối.
- Không được suy ra `LOW`, `APPROVED`, neutral ratio hoặc zero risk chỉ vì không có dữ liệu.

## 8. Acceptance criteria

- **AC-8.1:** Mọi view có cùng assessment ID/as-of.
- **AC-8.2:** Bảng thể hiện eligibility, score breakdown, quality và reasons.
- **AC-8.3:** Statistics có denominator/coverage rõ.
- **AC-8.4:** JSON contract được schema-validate.

## 9. Child stories

- [08.1 ASSESSMENT_HEADER_AND_PROVENANCE](../../story/08_financial_reporting/STORY-08.1_ASSESSMENT_HEADER_AND_PROVENANCE.md) — `TARGET`
- [08.2 MARKET_REGIME_SUMMARY](../../story/08_financial_reporting/STORY-08.2_MARKET_REGIME_SUMMARY.md) — `TARGET`
- [08.3 RANKED_LIST_VIEW](../../story/08_financial_reporting/STORY-08.3_RANKED_LIST_VIEW.md) — `TARGET`
- [08.4 COMPARISON_TABLE_VIEW](../../story/08_financial_reporting/STORY-08.4_COMPARISON_TABLE_VIEW.md) — `TARGET`
- [08.5 PER_INSTRUMENT_DETAIL](../../story/08_financial_reporting/STORY-08.5_PER_INSTRUMENT_DETAIL.md) — `TARGET`
- [08.6 RISK_REASON_AND_INVALIDATION_VIEW](../../story/08_financial_reporting/STORY-08.6_RISK_REASON_AND_INVALIDATION_VIEW.md) — `TARGET`
- [08.7 UNIVERSE_COVERAGE_STATISTICS](../../story/08_financial_reporting/STORY-08.7_UNIVERSE_COVERAGE_STATISTICS.md) — `TARGET`
- [08.8 DISTRIBUTION_AND_QUANTILE_STATISTICS](../../story/08_financial_reporting/STORY-08.8_DISTRIBUTION_AND_QUANTILE_STATISTICS.md) — `TARGET`
- [08.9 BREADTH_CONCENTRATION_AND_OUTLIERS](../../story/08_financial_reporting/STORY-08.9_BREADTH_CONCENTRATION_AND_OUTLIERS.md) — `TARGET`
- [08.10 MISSINGNESS_FRESHNESS_AND_SOURCE_STATISTICS](../../story/08_financial_reporting/STORY-08.10_MISSINGNESS_FRESHNESS_AND_SOURCE_STATISTICS.md) — `TARGET`
- [08.11 MACHINE_READABLE_REPORT_CONTRACT](../../story/08_financial_reporting/STORY-08.11_MACHINE_READABLE_REPORT_CONTRACT.md) — `TARGET`
- [08.12 HUMAN_READABLE_RENDERING](../../story/08_financial_reporting/STORY-08.12_HUMAN_READABLE_RENDERING.md) — `TARGET`

## 10. Verification evidence required

- Source path hoặc official specification cho từng current claim.
- Repeatable test/command, fixture hoặc dataset version, environment và timestamp.
- Expected result, actual result và evidence location.
- Mọi mismatch phải ghi `KNOWN GAP`; không được tự mark verified.

## 11. Known gaps

- Chưa có universe report assembler.
- MCP output không khớp docs cũ.
- Chưa có golden report fixture.

## 12. Traceability

- Root scope: [PRD-01](PRD-01_ENGINE1_SCOPE_AND_SUCCESS.md)
- Completion gates: [PRD-10](PRD-10_ENGINE1_VERIFICATION_AND_DEFINITION_OF_DONE.md)
- Official OKX API index used for CEX verification: [https://www.okx.com/docs-v5/en/](https://www.okx.com/docs-v5/en/)
