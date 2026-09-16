# STORY-03.8: CEX DEX CROSS MARKET COMPARISON

> **Document ID:** STORY-03.8
> **Type:** STORY
> **Status:** TARGET
> **Scope:** TARGET
> **Evidence as of:** 2026-09-12
> **Parent PRD:** [PRD-03](../prd/PRD-03_OKX_DEX_ONCHAIN_DATA_FOUNDATION.md)
> **Source of truth for:** So sánh giá/liquidity CEX và DEX có căn thời gian.
> **Supersedes:** Related fragment in legacy BMAD documents

## 1. Purpose and boundary

So sánh giá/liquidity CEX và DEX có căn thời gian.

Story này chỉ sở hữu behavior trên. Nó không tự mở rộng sang data acquisition, scoring, reporting hoặc execution ngoài phần được nêu rõ.

## 2. Current baseline

Relevant current paths: `backend/adapters/okx/`, `backend/mcp/server.py`, `backend/data/collectors/hybrid_universe.py`.

- Status `TARGET` phản ánh mức evidence hiện có, không phải tiến độ marketing.
- Code comment hoặc file tồn tại không đủ để đổi thành `CURRENT-VERIFIED`; cần evidence tại Section 9.

## 2.1 OKX source verification status

- Official OKX DEX/onchain documentation URL, endpoint schema, authentication class, limits and coverage must be recorded before this story can become `CURRENT-VERIFIED`.
- Current code paths under `backend/adapters/okx/`, `backend/mcp/server.py` and `backend/data/collectors/hybrid_universe.py` are implementation evidence only; they do not prove official discovery coverage.
- The current `/api/v5/dex/...` request strings and “500+ DEX/60+ chains” legacy claims remain unverified and must not be treated as product facts.

## 3. Inputs

- CEX instrument, chain token/pool mapping, synchronized observations.

## 4. Processing rules

- Xác minh asset equivalence.
- Normalize quote currency và as-of tolerance.
- Spread chỉ là observation; tính phí/gas/impact và không gọi arbitrage executable.

## 5. Output contract

- `CrossMarketComparison`.

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

- **AC-3.8.1:** Mapping mơ hồ bị reject.
- **AC-3.8.2:** Stale leg làm comparison invalid.

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
