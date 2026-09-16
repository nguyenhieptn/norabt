"""MCP server exposing the risk-supervisor's read/compute surface to AI agents.

Named `agent_server.py`, not `mcp_server.py`: the SDK's own top-level package is
`mcp`, and this project already has an internal `Agent.backend.mcp` package
(Logic 2 / bot observation, nothing to do with the protocol). Nobody puts
`Agent/backend` on `sys.path`, so the two `mcp` names never collide at import
time -- but a file called `mcp_server.py` sitting next to a `mcp/` package
would still mislead anyone reading the tree, so the module keeps a distinct
name.

Runtime note: the SDK installed here is `mcp` 2.x, where `FastMCP` was renamed
to `MCPServer` (`mcp.server.mcpserver.MCPServer`) -- the decorator-based
`@mcp.tool()` API the plan called "FastMCP" is the same shape, just under the
new name. `ToolError` (`mcp.server.mcpserver.exceptions`) is what carries a
message to the calling model: any other exception escaping a tool is reported
to the client only as "Error executing tool <name>", which would silence the
Vietnamese explanation this project exists to produce. Every anticipated
failure below is therefore raised as `ToolError`, never a bare exception.

Every tool here is read-only or explicitly stateless. The lookup tools parse
files this project already writes (`data/assessment/`, `data/<venue>/<asset>/
bot/`); the compute tools (`assess_bot`, `get_market`) call the same Logic
1-3 services the batch report uses, with `persist_history=False` on the
pipeline so an agent probing scenarios never writes to `data/state/`.

Transport note: `MCPServer.run()` accepts `transport="stdio"` (the default,
used by every local MCP client -- Claude Code, Claude Desktop -- which spawns
this process itself and talks over its stdin/stdout) or
`transport="streamable-http"` (the SDK's remote transport, needed once a
client can no longer share a machine with the server, e.g. the OKX AI
Marketplace). The CLI flag below exposes the latter as `--transport http`
rather than the SDK's own `streamable-http` spelling, since that is the value
`claude mcp add ... -t http` already expects. Streamable HTTP runs on
uvicorn/starlette, both of which `mcp` already depends on -- see
`run_streamable_http_async` in
`mcp/server/mcpserver/server.py` -- so no new dependency is pulled in.

Payment gating (x402): every tool below takes an extra `ctx: Context`
parameter, injected automatically by the SDK (never part of the tool's JSON
schema or of `arguments` -- see `mcp.server.mcpserver.tools.base.Tool.from_function`,
which special-cases a `Context`-annotated parameter) and passed straight to
`_require_payment()` as the first line of the tool body. That function is a
complete no-op -- it returns immediately, touching neither `ctx` nor any env
var beyond the flag itself -- unless `X402_ENABLED=true`
(`Agent.backend.payments.x402.is_x402_enabled()`), which is why this change
does not alter behavior for the 520 tests in this repo that predate x402 and
never set that flag. See `_require_payment()`'s own docstring for exactly
what it does when the flag is on, and Agent/docs/okx_marketplace.md for the
SDK limitation that shapes it (a tool handler cannot set the outer HTTP
status/headers of a `tools/call` response in this SDK version) and the
fallback this module uses instead.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from Agent.backend.infra.config import config
from Agent.backend.market.service import MarketDataUnavailableError, MarketService
from Agent.backend.mcp.service import BotDataUnavailableError
from Agent.backend.payments import x402
from Agent.backend.pipeline import RiskSupervisionPipeline
from Agent.backend.qc.reporting import assessment_store

DATA_DIR = Path(config.DATA_DIR)
VALID_VENUES = ("CEX", "DEX")
# The four labels the QC narrative generator (reasons.py) actually emits.
# Kept as a tuple, not derived from the index at call time, so a caller gets
# the same error whether or not any bot has been assessed yet.
VALID_VERDICTS = ("AN TOÀN", "TIỀM NĂNG", "TIỀM ẨN", "NGUY HIỂM")

# Every identifier below (asset ticker, bot folder, unique code) becomes a path
# segment somewhere downstream. Whitelisting the character set is what makes
# "../../etc" and "a/b" fail here instead of at a filesystem call three layers
# down, where the failure would be harder to trace back to the request.
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.-]+$")

mcp = MCPServer(
    name="okx-risk-supervisor",
    title="OKX Copy-Trading Bot Risk Supervisor",
    instructions=(
        "Chấm điểm rủi ro bot copy-trading OKX qua 3 bước: quan sát thị trường, "
        "phân tích bot + Monte Carlo, và QC tổng hợp thành khuyến nghị tiếng Việt. "
        "Dùng các tool tra cứu (list_assets, list_bots, list_assessed_bots, "
        "get_assessment) trước -- chúng đọc cache có sẵn và trả lời tức thì. "
        "Chỉ gọi assess_bot/get_market khi cần một con số mới chưa có trong cache; "
        "hai tool này chạy pipeline thật nên chậm hơn."
    ),
)


def _require_token(value: Any, field_name: str) -> str:
    """Reject anything that is not a single, plain path segment.

    `bot_folder_name`, `asset`, `symbol` and `unique_code` all come from an AI
    agent and are treated as untrusted input per the project's fail-closed
    rule -- a value like "../../etc" or "cex/BTC" must never reach a path join.
    """
    if not isinstance(value, str) or not value.strip():
        raise ToolError(f"{field_name} không được để trống")
    token = value.strip()
    if token in (".", "..") or not _SAFE_TOKEN.match(token) or ".." in token:
        raise ToolError(
            f"{field_name}={value!r} chứa ký tự không hợp lệ hoặc có dấu hiệu "
            f"path traversal (chỉ cho phép chữ, số, '_', '-', '.')"
        )
    return token


def _require_venue(venue_type: Any) -> str:
    venue = str(venue_type).strip().upper() if venue_type is not None else ""
    if venue not in VALID_VENUES:
        raise ToolError(
            f"venue_type={venue_type!r} không hợp lệ; chỉ nhận CEX hoặc DEX"
        )
    return venue


def _header_value(headers: Optional[Mapping[str, str]], name: str) -> Optional[str]:
    """Case-insensitive header lookup.

    At runtime, `ctx.headers` on the HTTP transports this feature targets is
    Starlette's own case-insensitive `Headers` object (see
    Agent/docs/okx_marketplace.md "Giới hạn kỹ thuật của SDK"), so `.get()`
    alone already resolves any casing there. The manual scan below is a
    safety net for a plain `dict` -- what this file's own tests build to
    simulate a request -- where `.get()` would otherwise be case-sensitive.
    """
    if not headers:
        return None
    value = headers.get(name)
    if value is not None:
        return value
    lowered = name.lower()
    for key, val in headers.items():
        if key.lower() == lowered:
            return val
    return None


def _read_ctx_headers(ctx: Optional[Context]) -> Optional[Mapping[str, str]]:
    """Best-effort read of the inbound request headers off `ctx`.

    `Context.headers` raises `ValueError` when the context was built with no
    real request attached -- true on stdio (no HTTP request exists at all)
    and also true for the placeholder `Context` that `MCPServer.call_tool()`
    builds when called directly with no `context=` argument, exactly what
    this project's own test helper (`Agent/test/test_agent_server.py::_call`)
    does. Both cases are treated identically to "this transport has no
    headers" (`None`), not as a crash: a payment gate that cannot see any
    headers must fail toward "no payment proof supplied", not toward an
    unrelated `ValueError` that has nothing to do with payment.
    """
    if ctx is None:
        return None
    try:
        return ctx.headers
    except ValueError:
        return None


def _resource_url(tool_name: str) -> str:
    return f"mcp://okx-risk-supervisor/{tool_name}"


def _require_payment(ctx: Optional[Context], tool_name: str) -> None:
    """Payment gate for one priced tool call -- the single choke point every
    tool below routes through before doing any real work.

    A complete no-op when x402 is disabled (`X402_ENABLED` is not "true",
    the default): returns immediately without touching `ctx`, `os.environ`
    beyond the flag itself, or the network. This is what guarantees the 520
    pre-existing tests (none of which set that env var) see byte-identical
    behavior to before this feature existed.

    When enabled, this function NEVER lets a call through without a
    facilitator-confirmed `VerifyResult(is_valid=True)` from
    `x402.verify_payment()` -- every other outcome raises `ToolError` with a
    Vietnamese message, and the tool body below never runs:

      - Server's own wallet/asset (`X402_PAY_TO_ADDRESS`/`X402_ASSET_ADDRESS`)
        not configured: refused. `X402_ENABLED=true` with incomplete server
        config must never fall back to "let it through".
      - No `PAYMENT-SIGNATURE` header on the request: refused with a message
        naming this tool's price and embedding the real base64
        PAYMENT-REQUIRED payload the client would need to decode and pay
        against. This is the documented fallback for a real limitation: `mcp`
        2.2.0 gives a tool handler no way to make the outer `tools/call` HTTP
        response carry a 402 status or a `PAYMENT-REQUIRED` header (every
        `CallToolResult` -- error or not -- rides a 200 OK; see
        Agent/docs/okx_marketplace.md for the SDK source evidence). Embedding
        the same payload in the error text is the closest equivalent
        reachable from inside a tool.
      - `x402.verify_payment()` raises (disabled -- unreachable here since
        this function already checked; missing/malformed header --
        unreachable, just checked non-empty; missing merchant/facilitator
        credentials; facilitator unreachable/timeout/malformed answer):
        refused, wrapping the original exception's message.
      - `x402.verify_payment()` returns `is_valid=False` (wrong amount/
        network/asset/payTo, replay, or the facilitator's own denial):
        refused, naming `invalid_reason`/`invalid_message`.
    """
    if not x402.is_x402_enabled():
        return
    settings = x402.X402Settings.from_env()

    try:
        requirements = x402.build_payment_requirements(tool_name, settings)
    except ValueError as exc:
        # Server-side config gap (no wallet/asset configured yet). Fail
        # closed -- X402_ENABLED=true with incomplete setup must refuse, not
        # silently run the tool for free.
        raise ToolError(
            f"x402 đang BẬT nhưng cấu hình ví/token nhận tiền chưa đầy đủ, "
            f"không thể tạo yêu cầu thanh toán cho tool '{tool_name}': {exc}"
        ) from exc

    headers = _read_ctx_headers(ctx)
    payment_header = _header_value(headers, x402.PAYMENT_SIGNATURE_HEADER)
    if not payment_header:
        challenge = x402.build_402_response(
            tool_name, _resource_url(tool_name), settings
        )
        header_b64 = challenge["headers"][x402.PAYMENT_REQUIRED_HEADER]
        raise ToolError(
            f"Cần thanh toán trước khi gọi tool '{tool_name}' (giá "
            f"{challenge['usd_price']}). Gửi lại yêu cầu kèm header "
            f"'{x402.PAYMENT_SIGNATURE_HEADER}' chứa bằng chứng thanh toán "
            f"hợp lệ (chuẩn x402, xem Agent/docs/okx_marketplace.md). "
            f"{x402.PAYMENT_REQUIRED_HEADER}={header_b64}"
        )

    try:
        result = x402.verify_payment(payment_header, requirements, settings)
    except (RuntimeError, ValueError) as exc:
        raise ToolError(
            f"Xác minh thanh toán thất bại, từ chối gọi tool '{tool_name}': {exc}"
        ) from exc

    if not result.is_valid:
        raise ToolError(
            f"Thanh toán không hợp lệ cho tool '{tool_name}' "
            f"(lý do: {result.invalid_reason}): {result.invalid_message}"
        )
    # result.is_valid is True here: a facilitator-confirmed payment. Fall
    # through and let the tool body below run.


def _read_json_or_none(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _assessment_index() -> Dict[str, Any]:
    index_path = DATA_DIR / "assessment" / "index.json"
    index = _read_json_or_none(index_path)
    if index is None:
        raise ToolError(
            "Chưa có data/assessment/index.json -- bước 3 (QC chấm điểm) chưa "
            "chạy lần nào, cần chạy pipeline chấm điểm trước khi tra cứu."
        )
    return index


@mcp.tool()
def list_assets(ctx: Context) -> Dict[str, Any]:
    """List every asset with crawled data on disk, and which venues (CEX/DEX) cover it."""
    _require_payment(ctx, "list_assets")
    assets: Dict[str, List[str]] = {}
    for venue_dir, venue_type in (("cex", "CEX"), ("dex", "DEX")):
        base = DATA_DIR / venue_dir
        if not base.is_dir():
            continue
        for asset_dir in sorted(base.iterdir()):
            if asset_dir.is_dir():
                assets.setdefault(asset_dir.name, []).append(venue_type)
    if not assets:
        raise ToolError(
            f"Không tìm thấy dữ liệu asset nào dưới {DATA_DIR} (cex/, dex/ trống "
            f"hoặc thiếu); cần crawl dữ liệu trước."
        )
    return {
        "assets": [
            {"asset": name, "venues": venues} for name, venues in sorted(assets.items())
        ]
    }


@mcp.tool()
def list_bots(asset: str, venue_type: str, ctx: Context) -> Dict[str, Any]:
    """List the bots crawled for one asset on one venue: folder name, nick name, unique code."""
    _require_payment(ctx, "list_bots")
    clean_asset = _require_token(asset, "asset").upper()
    venue = _require_venue(venue_type)
    bot_root = DATA_DIR / venue.lower() / clean_asset / "bot"
    if not bot_root.is_dir():
        raise ToolError(
            f"Asset {clean_asset} chưa có dữ liệu bot trên {venue} trong dataset "
            f"(thiếu thư mục {bot_root}); cần crawl trước."
        )
    bots = []
    for bot_dir in sorted(p for p in bot_root.iterdir() if p.is_dir()):
        overview = _read_json_or_none(bot_dir / "overview.json")
        if overview is None:
            # A folder without a readable overview.json is a partial crawl, not
            # a bot with an unknown identity -- skip it rather than fabricate one.
            continue
        bots.append(
            {
                "bot_folder_name": bot_dir.name,
                "nick_name": overview.get("nickName", "UNKNOWN"),
                "unique_code": overview.get("uniqueCode", "UNKNOWN"),
            }
        )
    if not bots:
        raise ToolError(
            f"Asset {clean_asset} trên {venue} có thư mục bot nhưng không bot nào "
            f"có overview.json hợp lệ; dữ liệu crawl có thể chưa hoàn tất."
        )
    return {"asset": clean_asset, "venue_type": venue, "bots": bots}


@mcp.tool()
def list_assessed_bots(ctx: Context, verdict: Optional[str] = None) -> Dict[str, Any]:
    """List QC-scored bots from data/assessment/index.json, optionally filtered by verdict.

    verdict: one of AN TOÀN / TIỀM NĂNG / TIỀM ẨN / NGUY HIỂM (case-insensitive).
    Leave empty to list every scored bot.
    """
    _require_payment(ctx, "list_assessed_bots")
    index = _assessment_index()
    bots = index.get("bots", [])
    matched_verdict = None
    if verdict is not None and verdict.strip():
        # Case-insensitive on input, but the result always echoes back one of
        # the four canonical labels so a caller can't be misled into thinking
        # a typo'd verdict is a real fifth category.
        matched_verdict = next(
            (v for v in VALID_VERDICTS if v.upper() == verdict.strip().upper()), None
        )
        if matched_verdict is None:
            raise ToolError(
                f"verdict={verdict!r} không hợp lệ; chỉ nhận một trong: "
                f"{', '.join(VALID_VERDICTS)}"
            )
        bots = [b for b in bots if b.get("verdict") == matched_verdict]
    return {"verdict_filter": matched_verdict, "count": len(bots), "bots": bots}


@mcp.tool()
def get_assessment(unique_code: str, ctx: Context) -> Dict[str, Any]:
    """Read one bot's full step-3 verdict: scores, tier, drivers, and the Vietnamese recommendation text."""
    _require_payment(ctx, "get_assessment")
    clean_code = _require_token(unique_code, "unique_code")
    index = _assessment_index()
    entry = next(
        (b for b in index.get("bots", []) if b.get("unique_code") == clean_code), None
    )
    if entry is None:
        raise ToolError(
            f"Không tìm thấy bot với unique_code={clean_code!r} trong "
            f"data/assessment/index.json; bot này chưa được QC chấm điểm."
        )
    venue, _, symbol = str(entry.get("slot", "")).partition("/")
    payload = (
        assessment_store.load_bot(DATA_DIR, venue, symbol, clean_code)
        if venue and symbol
        else None
    )
    if payload is None:
        raise ToolError(
            f"Bot {clean_code!r} có trong index nhưng file assessment.json bị "
            f"thiếu hoặc slot '{entry.get('slot')}' không đọc được; dữ liệu có "
            f"thể đã bị xoá hoặc ghi dở."
        )
    return payload


@mcp.tool()
def assess_bot(
    asset: str, bot_folder_name: str, ctx: Context, venue_type: str = "CEX"
) -> Dict[str, Any]:
    """Run the live risk pipeline (market -> bot analytics -> QC fusion) for one bot.

    Slower than the lookup tools (runs a fresh Monte Carlo simulation) and
    strictly stateless: it never writes to data/state/, so calling it
    repeatedly while exploring scenarios is safe.
    """
    _require_payment(ctx, "assess_bot")
    clean_asset = _require_token(asset, "asset").upper()
    clean_folder = _require_token(bot_folder_name, "bot_folder_name")
    venue = _require_venue(venue_type)
    # persist_history=False: an agent re-running the same bot to compare
    # scenarios must not accumulate rows in the real assessment history that
    # step 3's risk-trend logic reads on the next batch report.
    pipeline = RiskSupervisionPipeline(persist_history=False)
    try:
        result = pipeline.run(clean_asset, clean_folder, venue_type=venue)
    except (BotDataUnavailableError, MarketDataUnavailableError, ValueError) as exc:
        raise ToolError(
            f"Không thể chấm điểm bot {clean_folder!r} ({clean_asset}/{venue}): {exc}"
        ) from exc
    assessment = result.risk_assessment
    decision = result.control_decision
    return {
        "asset": clean_asset,
        "venue_type": venue,
        "bot_folder_name": clean_folder,
        "traded_symbol": result.traded_symbol,
        "market_available": result.market_available,
        "market_resolution": result.market_resolution,
        "universe_eligible": result.universe_eligible,
        "eligibility_reason": result.eligibility_reason,
        "risk_score": assessment.risk_score,
        "risk_tier": assessment.risk_tier.value,
        "risk_trend": assessment.risk_trend.value,
        "quality_score": assessment.quality_score,
        "confidence": assessment.confidence,
        "verdict": assessment.verdict,
        "verdict_reason": assessment.verdict_reason,
        "recommended_action": assessment.recommended_action,
        "suggested_reduction_pct": assessment.suggested_reduction_pct,
        "explanation": assessment.explanation,
        "hidden_risk_flags": assessment.hidden_risk_flags,
        "positive_factors": assessment.positive_factors,
        "limitations": assessment.limitations,
        "warnings": assessment.warnings,
        "dimensions": assessment.dimensions.model_dump(mode="json"),
        "score_breakdown": assessment.score_breakdown.model_dump(mode="json"),
        "control_action": decision.action.value,
        "control_reason": decision.reason,
    }


@mcp.tool()
def get_market(symbol: str, ctx: Context, venue_type: str = "CEX") -> Dict[str, Any]:
    """Run Logic 1 live: normalize crawled market data for one symbol into a full market snapshot."""
    _require_payment(ctx, "get_market")
    clean_symbol = _require_token(symbol, "symbol").upper()
    venue = _require_venue(venue_type)
    try:
        result = MarketService().get_market_result(clean_symbol, venue_type=venue)
    except (MarketDataUnavailableError, ValueError) as exc:
        raise ToolError(
            f"Không thể lấy dữ liệu thị trường {clean_symbol}/{venue}: {exc}"
        ) from exc
    return result.model_dump(mode="json")


# Default port for the HTTP transport. Arbitrary but fixed, so `--transport
# http` with no `--port` gives a repeatable address to point a client at;
# callers that need to avoid clashes (tests, several servers on one host)
# pass an explicit port, including 0 to let the OS pick a free one.
DEFAULT_HTTP_PORT = 8765


def _build_arg_parser() -> argparse.ArgumentParser:
    """CLI surface for choosing a transport; stdio needs none of this, so every flag is optional."""
    parser = argparse.ArgumentParser(
        prog="python3 -m Agent.backend.agent_server",
        description=(
            "MCP server cho Risk Supervisor. Mặc định stdio (dùng cho client "
            "local như Claude Code/Claude Desktop); dùng --transport http để "
            "phục vụ client ở xa (bắt buộc cho OKX AI Marketplace)."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="stdio (mặc định, local) hoặc http (streamable HTTP, cho phép gọi từ xa)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help=(
            "Chỉ dùng với --transport http. Mặc định 127.0.0.1 (chỉ máy này gọi "
            "được). Dùng 0.0.0.0 để mở ra mọi interface mạng -- chỉ làm vậy sau "
            "reverse proxy/tường lửa đáng tin cậy, vì server chưa có xác thực."
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_HTTP_PORT,
        help=(
            "Chỉ dùng với --transport http. Mặc định "
            f"{DEFAULT_HTTP_PORT}; dùng 0 để nhờ hệ điều hành cấp một cổng "
            "trống (hữu ích khi chạy nhiều instance song song, ví dụ test)."
        ),
    )
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """Entry point behind `python3 -m Agent.backend.agent_server`.

    Kept as a plain function (not inlined under `if __name__`) so a test can
    call it directly with an explicit `argv`, the same way a real CLI
    invocation would build one, instead of shelling out just to exercise
    argument parsing.
    """
    args = _build_arg_parser().parse_args(argv)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return
    if args.host == "0.0.0.0":
        # A hard requirement from the plan: binding every interface must never
        # happen silently, because this server already returns risk verdicts
        # and will soon carry payments, and it has no auth of its own yet.
        print(
            "CẢNH BÁO: server đang lắng nghe trên MỌI interface mạng (0.0.0.0) "
            "và CHƯA có cơ chế xác thực -- bất kỳ máy nào truy cập được cổng "
            f"{args.port} đều gọi được toàn bộ tool. Chỉ dùng khi đã có "
            "reverse proxy/tường lửa/xác thực đáng tin cậy phía trước; nếu "
            "không, hãy dùng --host 127.0.0.1 (mặc định) hoặc một địa chỉ nội bộ.",
            file=sys.stderr,
        )
    # "http" here is the CLI's own spelling (matching `claude mcp add -t http`);
    # the SDK's transport literal is "streamable-http".
    mcp.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
