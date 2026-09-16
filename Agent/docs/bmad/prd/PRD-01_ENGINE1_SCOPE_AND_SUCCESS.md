# PRD-01: ENGINE 1 — PHẠM VI, GIÁ TRỊ VÀ ĐIỀU KIỆN THÀNH CÔNG

> **Document ID:** PRD-01
> **Type:** PRD
> **Status:** DRAFT
> **Scope:** TARGET
> **Evidence as of:** 2026-09-12
> **Source of truth for:** Định nghĩa sản phẩm Engine 1 và ranh giới hoàn thành
> **Supersedes:** Legacy PRD content removed; this document is the active source of truth.

## 1. Purpose and boundary

Khóa một định nghĩa duy nhất: Engine 1 là lõi Regime được mở rộng thành hệ thống đánh giá thị trường và rủi ro. Nó biến dữ liệu OKX đã chuẩn hóa thành bức tranh thị trường, đánh giá từng nơi, điểm phù hợp/rủi ro, bảng xếp hạng và báo cáo có thể kiểm toán.

## 2. Current baseline

- Các calculator regime/risk và model `MarketRiskState` đã tồn tại.
- Canonical candle application path hiện gọi full Engine 1 assessment; live operational evidence vẫn chưa đủ để mark verified.
- Output hiện có nội dung TradePlan/action text; đây là derived/legacy concern, không phải lõi sản phẩm.

## 3. Target behavior

- Trả lời market đang ở regime nào và bằng chứng nào dẫn đến kết luận.
- Đánh giá status, sentiment, volatility, flow, liquidity, tail risk và uncertainty cho từng CEX instrument hoặc DEX pool/token đủ điều kiện.
- Xếp hạng riêng CEX và DEX sau eligibility gate; cho biết nơi đáng quan sát và nơi bất lợi, không biến rank thành lệnh.
- Xuất list, comparison table, statistics và per-item detail từ cùng immutable assessment snapshot.

## 4. Inputs

- Normalized OKX observations có provenance/quality.
- Universe versioned theo cohort CEX/DEX.
- Methodology version và threshold/weight set.
- Optional external evidence phải gắn source khác OKX.

## 5. Processing and policy rules

- Engine 1 không gọi network, không đọc/ghi Redis/file và không biết endpoint OKX.
- Missing/stale/fallback không được tự biến thành neutral hoặc favorable.
- Mọi score/rank phải deterministic và có methodology version.
- Assessment không bảo đảm lợi nhuận, không phải execution authorization.

## 6. Required outputs

- `MarketAssessmentReport` machine-readable.
- `MarketRiskAssessment` cho từng identity.
- `RankedAssessmentRow[]` theo cohort.
- Human-readable list/table/statistics.
- Coverage, missingness, freshness và limitation report.

## 7. Error, missing, stale and fallback behavior

- Source error phải có typed status và thời điểm; không trả dữ liệu cũ như dữ liệu mới.
- Missing và not-applicable là hai trạng thái khác nhau.
- Fallback phải giữ origin, age, synthetic flag và confidence penalty đến report cuối.
- Không được suy ra `LOW`, `APPROVED`, neutral ratio hoặc zero risk chỉ vì không có dữ liệu.

## 8. Acceptance criteria

- **AC-1.1:** Phạm vi và non-goals không mâu thuẫn trong bất kỳ active doc nào.
- **AC-1.2:** Một snapshot tạo được market overview, per-item result, rank, table và statistics có cùng `assessment_id`.
- **AC-1.3:** Mọi kết luận có reason codes, provenance coverage và confidence.
- **AC-1.4:** Tất cả gate PRD-10 pass trước khi đổi trạng thái thành DONE.

## 9. Child stories

- PRD root; liên kết PRD-02 đến PRD-10.

## 10. Verification evidence required

- Source path hoặc official specification cho từng current claim.
- Repeatable test/command, fixture hoặc dataset version, environment và timestamp.
- Expected result, actual result và evidence location.
- Mọi mismatch phải ghi `KNOWN GAP`; không được tự mark verified.

## 11. Known gaps

- Chưa có contract report cuối cùng.
- Chưa có full live integration.
- Chưa có CEX Top 50 proof và DEX Top 50 discovery proof.

## 12. Traceability

- Root scope: [PRD-01](PRD-01_ENGINE1_SCOPE_AND_SUCCESS.md)
- Completion gates: [PRD-10](PRD-10_ENGINE1_VERIFICATION_AND_DEFINITION_OF_DONE.md)
- Official OKX API index used for CEX verification: [https://www.okx.com/docs-v5/en/](https://www.okx.com/docs-v5/en/)
