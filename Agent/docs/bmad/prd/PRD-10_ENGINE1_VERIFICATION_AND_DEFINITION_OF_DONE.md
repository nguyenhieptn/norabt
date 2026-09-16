# PRD-10: ENGINE 1 VERIFICATION VÀ DEFINITION OF DONE

> **Document ID:** PRD-10
> **Type:** PRD
> **Status:** DRAFT
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Source of truth for:** Các gate bằng chứng để tuyên bố Engine 1 hoàn thành
> **Supersedes:** Legacy PRD content removed; this document is the active source of truth.

## 1. Purpose and boundary

Biến “Engine 1 ngon/done” thành quyết định dựa trên repeatable evidence thay vì tài liệu quảng bá hoặc một benchmark đơn lẻ.

## 2. Current baseline

- Backend compile pass; default unittest discovery hiện có 21 tests pass.
- Integration scripts phụ thuộc network/Redis và không nằm trong unittest discovery.
- Deterministic fixture evidence đã có cho Top 50, full assessment path, report consistency và static no-execution boundary; live/operational evidence vẫn thiếu.

## 3. Target behavior

- Mỗi completion dimension là một story/gate độc lập.
- Evidence gồm command, environment, fixture/dataset, expected/actual result, timestamp và methodology/commit.
- Final completion chỉ pass khi tất cả mandatory gates pass.

## 4. Inputs

- PRD acceptance criteria.
- Source/tests/benchmark artifacts.
- Top-50 feasibility decisions.
- Capability audit.

## 5. Processing and policy rules

- Docs completion không phải implementation completion.
- PARTIAL component không được tổng hợp thành DONE.
- Skipped test được ghi skipped, không pass.
- Không dùng production/institutional claim nếu chưa có operational evidence.

## 6. Required outputs

- Gate result records.
- Blocker list.
- Final `ENGINE1_DONE | NOT_DONE` decision với evidence links.

## 7. Error, missing, stale and fallback behavior

- Source error phải có typed status và thời điểm; không trả dữ liệu cũ như dữ liệu mới.
- Missing và not-applicable là hai trạng thái khác nhau.
- Fallback phải giữ origin, age, synthetic flag và confidence penalty đến report cuối.
- Không được suy ra `LOW`, `APPROVED`, neutral ratio hoặc zero risk chỉ vì không có dữ liệu.

## 8. Acceptance criteria

- **AC-10.1:** Mọi PRD requirement map tới story và evidence.
- **AC-10.2:** Các gate mandatory có kết quả repeatable.
- **AC-10.3:** Final decision không mâu thuẫn với bất kỳ gate nào.
- **AC-10.4:** Known limitations còn lại được nêu rõ.

## 9. Child stories

- [10.1 SCOPE_AND_CONTRACT_GATE](../story/STORY-10.1_SCOPE_AND_CONTRACT_GATE.md) — `DRAFT`
- [10.2 OKX_SOURCE_COVERAGE_GATE](../story/STORY-10.2_OKX_SOURCE_COVERAGE_GATE.md) — `DRAFT`
- [10.3 PROVENANCE_AND_QUALITY_GATE](../story/STORY-10.3_PROVENANCE_AND_QUALITY_GATE.md) — `DRAFT`
- [10.4 CEX_TOP50_GATE](../story/STORY-10.4_CEX_TOP50_GATE.md) — `DRAFT`
- [10.5 DEX_TOP50_DECISION_GATE](../story/STORY-10.5_DEX_TOP50_DECISION_GATE.md) — `BLOCKED`
- [10.6 FORMULA_AND_REGIME_CORRECTNESS_GATE](../story/STORY-10.6_FORMULA_AND_REGIME_CORRECTNESS_GATE.md) — `DRAFT`
- [10.7 FULL_PIPELINE_INTEGRATION_GATE](../story/STORY-10.7_FULL_PIPELINE_INTEGRATION_GATE.md) — `DRAFT`
- [10.8 SCENARIO_AND_GOLDEN_FIXTURE_GATE](../story/STORY-10.8_SCENARIO_AND_GOLDEN_FIXTURE_GATE.md) — `DRAFT`
- [10.9 RANKING_AND_REPORT_CONSISTENCY_GATE](../story/STORY-10.9_RANKING_AND_REPORT_CONSISTENCY_GATE.md) — `DRAFT`
- [10.10 DETERMINISM_AND_REPRODUCIBILITY_GATE](../story/STORY-10.10_DETERMINISM_AND_REPRODUCIBILITY_GATE.md) — `DRAFT`
- [10.11 OKX_NO_EXECUTION_BOUNDARY_GATE](../story/STORY-10.11_OKX_NO_EXECUTION_BOUNDARY_GATE.md) — `DRAFT`
- [10.12 OPERATIONAL_RESILIENCE_GATE](../story/STORY-10.12_OPERATIONAL_RESILIENCE_GATE.md) — `DRAFT`
- [10.13 PERFORMANCE_EVIDENCE_GATE](../story/STORY-10.13_PERFORMANCE_EVIDENCE_GATE.md) — `DRAFT`
- [10.14 DOCUMENTATION_TRACEABILITY_GATE](../story/STORY-10.14_DOCUMENTATION_TRACEABILITY_GATE.md) — `DRAFT`
- [10.15 FINAL_ENGINE1_COMPLETION_DECISION](../story/STORY-10.15_FINAL_ENGINE1_COMPLETION_DECISION.md) — `DRAFT`

## 10. Verification evidence required

- Source path hoặc official specification cho từng current claim.
- Repeatable test/command, fixture hoặc dataset version, environment và timestamp.
- Expected result, actual result và evidence location.
- Mọi mismatch phải ghi `KNOWN GAP`; không được tự mark verified.

## 11. Known gaps

- Hầu hết gate hiện chưa có durable evidence.
- Default deterministic test suite pass; live network/Redis scenarios chưa phải default tests.
- Agent tree hiện chưa được Git track.

## 12. Traceability

- Root scope: [PRD-01](PRD-01_ENGINE1_SCOPE_AND_SUCCESS.md)
- Completion gates: [PRD-10](PRD-10_ENGINE1_VERIFICATION_AND_DEFINITION_OF_DONE.md)
- Official OKX API index used for CEX verification: [https://www.okx.com/docs-v5/en/](https://www.okx.com/docs-v5/en/)
