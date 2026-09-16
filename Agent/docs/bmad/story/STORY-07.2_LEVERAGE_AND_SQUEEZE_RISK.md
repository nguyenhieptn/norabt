# STORY-07.2: LEVERAGE AND SQUEEZE RISK

> **Document ID:** STORY-07.2
> **Type:** STORY
> **Status:** PARTIAL
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Parent PRD:** [PRD-07](../prd/PRD-07_ENGINE1_RISK_SCORING_AND_RANKING.md)
> **Source of truth for:** Đánh giá tension/squeeze từ OI/funding/liquidation.
> **Supersedes:** Related fragment in legacy BMAD documents

## 1. Purpose and boundary

Đánh giá tension/squeeze từ OI/funding/liquidation.

Story này chỉ sở hữu behavior trên. Nó không tự mở rộng sang data acquisition, scoring, reporting hoặc execution ngoài phần được nêu rõ.

## 2. Current baseline

Relevant current paths: `backend/core/engine_1/quant_risk.py`, `risk_evaluator.py`, `liquidity_depth.py`, `action_verdict_generator.py`.

- Status `PARTIAL` phản ánh mức evidence hiện có, không phải tiến độ marketing.
- Code comment hoặc file tồn tại không đủ để đổi thành `CURRENT-VERIFIED`; cần evidence tại Section 9.

## 3. Inputs

- Aligned delta-OI z-score, funding, optional liquidation.

## 4. Processing rules

- LSI formula and sign interpretation versioned.
- Missing component => UNKNOWN/partial confidence.
- Do not assert imminent liquidation without evidence.

## 5. Output contract

- lsi,tension,squeeze_risk,reasons.

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

- **AC-7.2.1:** Long/short/neutral/missing fixtures.

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
