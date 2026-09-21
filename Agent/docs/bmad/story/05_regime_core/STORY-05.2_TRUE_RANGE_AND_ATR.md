# STORY-05.2: TRUE RANGE AND ATR

> **Document ID:** STORY-05.2
> **Type:** STORY
> **Status:** CURRENT-UNVERIFIED
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Parent PRD:** [PRD-05](../../spec/01_prd_engine1/PRD-05_ENGINE1_REGIME_CORE.md)
> **Source of truth for:** Định nghĩa True Range và Wilder ATR.
> **Supersedes:** Related fragment in legacy BMAD documents

## 1. Purpose and boundary

Định nghĩa True Range và Wilder ATR.

Story này chỉ sở hữu behavior trên. Nó không tự mở rộng sang data acquisition, scoring, reporting hoặc execution ngoài phần được nêu rõ.

## 2. Current baseline

Relevant current paths: `backend/core/engine_1/`, `backend/data/ring_buffer/matrix.py`.

- Status `CURRENT-UNVERIFIED` phản ánh mức evidence hiện có, không phải tiến độ marketing.
- Code comment hoặc file tồn tại không đủ để đổi thành `CURRENT-VERIFIED`; cần evidence tại Section 9.

## 3. Inputs

- High/low/previous close series.

## 4. Processing rules

- TR=max(H-L,|H-prevC|,|L-prevC|).
- Wilder smoothing and seed documented.
- Resolve ATR-14 vs ATR-20 before verified status.

## 5. Output contract

- ATR series/latest.

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

- **AC-5.2.1:** Gap/open fixtures match reference.
- **AC-5.2.2:** Period mismatch remains known gap until decision.

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
