# PRD-07: ENGINE 1 RISK, ELIGIBILITY, SCORING VÀ RANKING

> **Document ID:** PRD-07
> **Type:** PRD
> **Status:** PARTIAL
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Source of truth for:** Đánh giá nơi phù hợp/bất lợi bằng risk-aware ranking
> **Supersedes:** Legacy PRD content removed; this document is the active source of truth.

## 1. Purpose and boundary

Biến market/risk evidence thành eligibility, risk tier, component scores, weighted assessment score và cohort ranking có thể giải thích.

## 2. Current baseline

- Có VaR/CVaR, LSI, liquidity/security risk và entry-favorability logic.
- Fallback risk có favorable constants; score/weights và rank contract hoàn chỉnh chưa tồn tại.
- Current code trộn risk assessment với Long/Short/TradePlan policy.

## 3. Target behavior

- Risk fusion có UNKNOWN và precedence rõ.
- Eligibility chạy trước scoring.
- Versioned, deterministic weighted score với missing/quality penalty.
- CEX và DEX ranking riêng, có stable tie-break và reasons.

## 4. Inputs

- Market intelligence.
- Risk evidence theo cohort.
- Data quality.
- Versioned eligibility/weight policy.

## 5. Processing and policy rules

- VETO/UNKNOWN semantics không bị score che lấp.
- Rank không phải buy/sell/order.
- Không so trực tiếp CEX và DEX nếu scale chưa calibrated.
- Không gọi vị trí là “safe”; dùng risk tier + uncertainty.

## 6. Required outputs

- `RiskAssessment`.
- `EligibilityDecision`.
- `ScoreBreakdown`.
- `RankedAssessmentRow[]`.

## 7. Error, missing, stale and fallback behavior

- Source error phải có typed status và thời điểm; không trả dữ liệu cũ như dữ liệu mới.
- Missing và not-applicable là hai trạng thái khác nhau.
- Fallback phải giữ origin, age, synthetic flag và confidence penalty đến report cuối.
- Không được suy ra `LOW`, `APPROVED`, neutral ratio hoặc zero risk chỉ vì không có dữ liệu.

## 8. Acceptance criteria

- **AC-7.1:** Mỗi component score trace tới input evidence.
- **AC-7.2:** Missing/stale penalties deterministic.
- **AC-7.3:** Tie-break ổn định.
- **AC-7.4:** Scenario tests bao phủ favorable, unfavorable, veto và unknown.

## 9. Child stories

- [07.1 FAT_TAIL_VAR_AND_CVAR](../../story/07_risk_scoring_and_ranking/STORY-07.1_FAT_TAIL_VAR_AND_CVAR.md) — `CURRENT-UNVERIFIED`
- [07.2 LEVERAGE_AND_SQUEEZE_RISK](../../story/07_risk_scoring_and_ranking/STORY-07.2_LEVERAGE_AND_SQUEEZE_RISK.md) — `PARTIAL`
- [07.3 CEX_LIQUIDITY_RISK](../../story/07_risk_scoring_and_ranking/STORY-07.3_CEX_LIQUIDITY_RISK.md) — `PARTIAL`
- [07.4 DEX_TOKEN_AND_CONTRACT_RISK](../../story/07_risk_scoring_and_ranking/STORY-07.4_DEX_TOKEN_AND_CONTRACT_RISK.md) — `PARTIAL`
- [07.5 DEX_POOL_AND_ROUTE_RISK](../../story/07_risk_scoring_and_ranking/STORY-07.5_DEX_POOL_AND_ROUTE_RISK.md) — `TARGET`
- [07.6 DATA_UNCERTAINTY_RISK](../../story/07_risk_scoring_and_ranking/STORY-07.6_DATA_UNCERTAINTY_RISK.md) — `TARGET`
- [07.7 RISK_TIER_FUSION](../../story/07_risk_scoring_and_ranking/STORY-07.7_RISK_TIER_FUSION.md) — `PARTIAL`
- [07.8 ELIGIBILITY_GATE](../../story/07_risk_scoring_and_ranking/STORY-07.8_ELIGIBILITY_GATE.md) — `TARGET`
- [07.9 SCORE_COMPONENT_NORMALIZATION](../../story/07_risk_scoring_and_ranking/STORY-07.9_SCORE_COMPONENT_NORMALIZATION.md) — `TARGET`
- [07.10 WEIGHTED_ASSESSMENT_SCORE](../../story/07_risk_scoring_and_ranking/STORY-07.10_WEIGHTED_ASSESSMENT_SCORE.md) — `TARGET`
- [07.11 CEX_RANKING](../../story/07_risk_scoring_and_ranking/STORY-07.11_CEX_RANKING.md) — `TARGET`
- [07.12 DEX_RANKING](../../story/07_risk_scoring_and_ranking/STORY-07.12_DEX_RANKING.md) — `BLOCKED`
- [07.13 RANK_STABILITY_AND_TIEBREAK](../../story/07_risk_scoring_and_ranking/STORY-07.13_RANK_STABILITY_AND_TIEBREAK.md) — `TARGET`

## 10. Verification evidence required

- Source path hoặc official specification cho từng current claim.
- Repeatable test/command, fixture hoặc dataset version, environment và timestamp.
- Expected result, actual result và evidence location.
- Mọi mismatch phải ghi `KNOWN GAP`; không được tự mark verified.

## 11. Known gaps

- Chưa có cross-sectional ranker.
- Risk defaults cần sửa semantics.
- Action policy chưa tách khỏi core.

## 12. Traceability

- Root scope: [PRD-01](PRD-01_ENGINE1_SCOPE_AND_SUCCESS.md)
- Completion gates: [PRD-10](PRD-10_ENGINE1_VERIFICATION_AND_DEFINITION_OF_DONE.md)
- Official OKX API index used for CEX verification: [https://www.okx.com/docs-v5/en/](https://www.okx.com/docs-v5/en/)
