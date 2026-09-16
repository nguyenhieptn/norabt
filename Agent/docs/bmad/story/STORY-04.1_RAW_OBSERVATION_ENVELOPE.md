# STORY-04.1: RAW OBSERVATION ENVELOPE

> **Document ID:** STORY-04.1
> **Type:** STORY
> **Status:** TARGET
> **Scope:** TARGET
> **Evidence as of:** 2026-09-12
> **Parent PRD:** [PRD-04](../prd/PRD-04_DATA_QUALITY_PROVENANCE_AND_STATE.md)
> **Source of truth for:** Bọc mọi raw observation bằng provenance nhất quán.
> **Supersedes:** Related fragment in legacy BMAD documents

## 1. Purpose and boundary

Bọc mọi raw observation bằng provenance nhất quán.

Story này chỉ sở hữu behavior trên. Nó không tự mở rộng sang data acquisition, scoring, reporting hoặc execution ngoài phần được nêu rõ.

## 2. Current baseline

Relevant current paths: `backend/domain/models.py`, `backend/data/`, `backend/adapters/storage/`.

- Status `TARGET` phản ánh mức evidence hiện có, không phải tiến độ marketing.
- Code comment hoặc file tồn tại không đủ để đổi thành `CURRENT-VERIFIED`; cần evidence tại Section 9.

## 3. Inputs

- Raw payload và request/connection context.

## 4. Processing rules

- Ghi source_id/type, endpoint/channel, identity, event/observed/received times, schema version, request ID, raw digest.
- Không sửa raw payload trước digest.

## 5. Output contract

- `ObservationEnvelope[T]`.

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

- **AC-4.1.1:** Envelope schema validation pass.
- **AC-4.1.2:** Có thể truy raw source từ assessment reason.

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
