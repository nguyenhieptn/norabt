# PRD-03: OKX DEX VÀ ONCHAIN DATA FOUNDATION

> **Document ID:** PRD-03
> **Type:** PRD
> **Status:** BLOCKED
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Source of truth for:** DEX/onchain discovery, quote, liquidity và security evidence
> **Supersedes:** Legacy PRD content removed; this document is the active source of truth.

## 1. Purpose and boundary

Đặc tả DEX/token/pool data độc lập với CEX, đồng thời trả lời trung thực liệu có thể xây Top 50 đa DEX từ OKX hay chưa.

## 2. Current baseline

- Có DEX quote và token-risk request paths.
- Local/hard-coded DEX discovery trong `HybridUniverseCollector` đã bị vô hiệu hóa; capability trả `BLOCKED` với zero synthetic rows.
- DEX quote/security không còn được MCP expose; compatibility gateways trả `BLOCKED/UNVERIFIED` và không tạo favorable defaults.

## 3. Target behavior

- Canonical chain-qualified token/pool identity.
- Verified OKX discovery source với pagination/coverage hoặc tuyên bố rõ không khả dụng.
- DEX cohort ranking dựa trên liquidity, volume, routeability, security, freshness và data quality.
- Quote luôn tách khỏi build/sign/broadcast transaction.

## 4. Inputs

- Official OKX DEX/onchain responses đã verify.
- Chain/token metadata và decimals.
- Pool liquidity/volume/security/route observations.
- Rate/freshness/coverage policy.

## 5. Processing and policy rules

- Không dùng symbol đơn lẻ làm identity.
- Local/hard-coded records phải `is_synthetic=true` và không được xếp như live observation.
- Không gắn `APPROVED` khi security API thiếu dữ liệu.
- Không gộp score CEX/DEX nếu chưa có normalization được duyệt.

## 6. Required outputs

- Versioned DEX universe hoặc explicit `UNSUPPORTED`.
- Normalized token/pool/quote/security evidence.
- DEX Top 50 feasibility decision.
- DEX assessment cohort riêng.

## 7. Error, missing, stale and fallback behavior

- Source error phải có typed status và thời điểm; không trả dữ liệu cũ như dữ liệu mới.
- Missing và not-applicable là hai trạng thái khác nhau.
- Fallback phải giữ origin, age, synthetic flag và confidence penalty đến report cuối.
- Không được suy ra `LOW`, `APPROVED`, neutral ratio hoặc zero risk chỉ vì không có dữ liệu.

## 8. Acceptance criteria

- **AC-3.1:** Discovery source và coverage được chứng minh trước khi công bố DEX Top 50.
- **AC-3.2:** Quote xử lý decimals theo token metadata.
- **AC-3.3:** Mọi pool/token có chain-qualified identity và observed_at.
- **AC-3.4:** Execution paths nằm ngoài phạm vi và bị cấm.

## 9. Child stories

- [03.1 CHAIN_AND_TOKEN_IDENTITY](../story/STORY-03.1_CHAIN_AND_TOKEN_IDENTITY.md) — `TARGET`
- [03.2 DEX_UNIVERSE_DISCOVERY](../story/STORY-03.2_DEX_UNIVERSE_DISCOVERY.md) — `BLOCKED`
- [03.3 DEX_TOP50_SELECTION](../story/STORY-03.3_DEX_TOP50_SELECTION.md) — `BLOCKED`
- [03.4 POOL_LIQUIDITY_AND_VOLUME](../story/STORY-03.4_POOL_LIQUIDITY_AND_VOLUME.md) — `BLOCKED`
- [03.5 DEX_QUOTE_AND_ROUTE](../story/STORY-03.5_DEX_QUOTE_AND_ROUTE.md) — `PARTIAL`
- [03.6 TOKEN_SECURITY_AUDIT](../story/STORY-03.6_TOKEN_SECURITY_AUDIT.md) — `PARTIAL`
- [03.7 CHAIN_AND_SMART_CONTRACT_RISK](../story/STORY-03.7_CHAIN_AND_SMART_CONTRACT_RISK.md) — `TARGET`
- [03.8 CEX_DEX_CROSS_MARKET_COMPARISON](../story/STORY-03.8_CEX_DEX_CROSS_MARKET_COMPARISON.md) — `TARGET`
- [03.9 DEX_FALLBACK_AND_UNVERIFIED_DATA](../story/STORY-03.9_DEX_FALLBACK_AND_UNVERIFIED_DATA.md) — `TARGET`
- [03.10 DEX_TOP50_FEASIBILITY_GATE](../story/STORY-03.10_DEX_TOP50_FEASIBILITY_GATE.md) — `BLOCKED`

## 10. Verification evidence required

- Source path hoặc official specification cho từng current claim.
- Repeatable test/command, fixture hoặc dataset version, environment và timestamp.
- Expected result, actual result và evidence location.
- Mọi mismatch phải ghi `KNOWN GAP`; không được tự mark verified.

## 11. Known gaps

- Official DEX Top 50 discovery chưa xác minh.
- Historical generated DEX files có thể còn trên disk nhưng production code không đọc/xếp hạng chúng.
- Coverage security và pool metrics chưa được đo.

## 12. Traceability

- Root scope: [PRD-01](PRD-01_ENGINE1_SCOPE_AND_SUCCESS.md)
- Completion gates: [PRD-10](PRD-10_ENGINE1_VERIFICATION_AND_DEFINITION_OF_DONE.md)
- Official OKX API index used for CEX verification: [https://www.okx.com/docs-v5/en/](https://www.okx.com/docs-v5/en/)
