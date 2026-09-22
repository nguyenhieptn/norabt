# PRD-09: OKX INTERACTION VÀ AGENT INTERFACE

> **Document ID:** PRD-09
> **Type:** PRD
> **Status:** PARTIAL
> **Scope:** CURRENT + TARGET
> **Evidence as of:** 2026-09-12
> **Source of truth for:** Ranh giới quyền hạn khi tương tác OKX và cung cấp assessment cho Agent
> **Supersedes:** Legacy PRD content removed; this document is the active source of truth.

## 1. Purpose and boundary

Trả lời chính xác “tương tác được trên OKX” nghĩa là gì: public read, authenticated read, local side effects và các execution/asset-movement capability bị cấm.

## 2. Current baseline

- Có public OKX reads và HMAC signing primitives.
- MCP chỉ gọi read-only query/report services; không còn direct OKX network, wallet hoặc storage write trong server.
- Không tìm thấy caller đặt/sửa/hủy lệnh, chuyển/rút tài sản hoặc ký/broadcast DEX transaction.

## 3. Target behavior

- Capability registry cho từng adapter/tool.
- Read-only least-privilege credential policy.
- Structured Engine 1 query cho MCP/UI/other agents.
- Negative tests chứng minh execution boundary.

## 4. Inputs

- OKX endpoint/method inventory.
- Credential permission model.
- MCP tool registry.
- Engine 1 report repository.

## 5. Processing and policy rules

- Authentication không đồng nghĩa trade authorization.
- Quote/route không phải execution.
- MCP consumer không nâng quyền ngoài registered tools.
- Future execution cần PRD/security review/explicit approval riêng.

## 6. Required outputs

- Capability matrix.
- Registered read-only query tools.
- Audit events cho live read/local write.
- Denied capability evidence.

## 7. Error, missing, stale and fallback behavior

- Source error phải có typed status và thời điểm; không trả dữ liệu cũ như dữ liệu mới.
- Missing và not-applicable là hai trạng thái khác nhau.
- Fallback phải giữ origin, age, synthetic flag và confidence penalty đến report cuối.
- Không được suy ra `LOW`, `APPROVED`, neutral ratio hoặc zero risk chỉ vì không có dữ liệu.

## 8. Acceptance criteria

- **AC-9.1:** Mỗi tool ghi cache-read/live-read/auth-read/local-write class.
- **AC-9.2:** Không active endpoint POST trade/transfer/withdraw.
- **AC-9.3:** Production target dùng read-only keys và method/path allowlist.
- **AC-9.4:** Agent đọc assessment nhưng không điều khiển tài khoản trong scope.

## 9. Child stories

- [09.1 PUBLIC_READ_CAPABILITY](../../story/09_agent_interface_and_mcp/STORY-09.1_PUBLIC_READ_CAPABILITY.md) — `PARTIAL`
- [09.2 AUTHENTICATED_READ_CAPABILITY](../../story/09_agent_interface_and_mcp/STORY-09.2_AUTHENTICATED_READ_CAPABILITY.md) — `TARGET`
- [09.3 LOCAL_NON_TRADING_SIDE_EFFECTS](../../story/09_agent_interface_and_mcp/STORY-09.3_LOCAL_NON_TRADING_SIDE_EFFECTS.md) — `PARTIAL`
- [09.4 CEX_EXECUTION_DENY_BOUNDARY](../../story/09_agent_interface_and_mcp/STORY-09.4_CEX_EXECUTION_DENY_BOUNDARY.md) — `TARGET`
- [09.5 ASSET_MOVEMENT_DENY_BOUNDARY](../../story/09_agent_interface_and_mcp/STORY-09.5_ASSET_MOVEMENT_DENY_BOUNDARY.md) — `TARGET`
- [09.6 DEX_QUOTE_VS_EXECUTION_BOUNDARY](../../story/09_agent_interface_and_mcp/STORY-09.6_DEX_QUOTE_VS_EXECUTION_BOUNDARY.md) — `PARTIAL`
- [09.7 OKX_CREDENTIAL_AND_PERMISSION_POLICY](../../story/09_agent_interface_and_mcp/STORY-09.7_OKX_CREDENTIAL_AND_PERMISSION_POLICY.md) — `PARTIAL`
- [09.8 MCP_TOOL_CAPABILITY_REGISTRY](../../story/09_agent_interface_and_mcp/STORY-09.8_MCP_TOOL_CAPABILITY_REGISTRY.md) — `PARTIAL`
- [09.9 STRUCTURED_ENGINE1_QUERY](../../story/09_agent_interface_and_mcp/STORY-09.9_STRUCTURED_ENGINE1_QUERY.md) — `TARGET`
- [09.10 CAPABILITY_NEGATIVE_TESTS](../../story/09_agent_interface_and_mcp/STORY-09.10_CAPABILITY_NEGATIVE_TESTS.md) — `TARGET`

## 10. Verification evidence required

- Source path hoặc official specification cho từng current claim.
- Repeatable test/command, fixture hoặc dataset version, environment và timestamp.
- Expected result, actual result và evidence location.
- Mọi mismatch phải ghi `KNOWN GAP`; không được tự mark verified.

## 11. Known gaps

- Public endpoint prefix allowlist và authenticated GET-only allowlist đã có; cần mở rộng negative runtime evidence.
- Private account observer chưa complete.
- MCP server đã tách khỏi fetch/write; compatibility tool names chỉ chiếu read-only structured state.

## 12. Traceability

- Root scope: [PRD-01](PRD-01_ENGINE1_SCOPE_AND_SUCCESS.md)
- Completion gates: [PRD-10](PRD-10_ENGINE1_VERIFICATION_AND_DEFINITION_OF_DONE.md)
- Official OKX API index used for CEX verification: [https://www.okx.com/docs-v5/en/](https://www.okx.com/docs-v5/en/)
