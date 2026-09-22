"""MCP server exposing the risk-supervisor's read/compute surface to AI agents.

Named `agent_server.py`, not `mcp_server.py`: the SDK's own top-level package is
`mcp`, and this project already has an internal `Agent.backend.bot.mcp` package
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
(`Agent.backend.external.payments.x402.is_x402_enabled()`), which is why this change
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
from Agent.backend.bot.mcp.service import BotDataUnavailableError
from Agent.backend.external.payments import x402
from Agent.backend.pipeline import RiskSupervisionPipeline
from Agent.backend.report.qc.reporting import assessment_store
from Agent.backend.report.qc.scoring.verdict import label_from_scores

DATA_DIR = Path(config.DATA_DIR)
VALID_VENUES = ("CEX", "DEX")
# The 6 two-axis labels the QC verdict layer (scoring/verdict.py) actually
# emits: 4 combinations of drawdown (CAO/THẤP) x quality (TỐT/YẾU), plus the
# full-override "HIDDEN RISK" and the no-score "INSUFFICIENT EVIDENCE". Kept as
# a tuple, not derived from the index at call time, so a caller gets the
# same error whether or not any bot has been assessed yet.
VALID_VERDICTS = (
    "DRAWDOWN: HIGH · QUALITY: GOOD",
    "DRAWDOWN: HIGH · QUALITY: WEAK",
    "DRAWDOWN: LOW · QUALITY: GOOD",
    "DRAWDOWN: LOW · QUALITY: WEAK",
    "HIDDEN RISK",
    "INSUFFICIENT EVIDENCE",
)

# Every identifier below (asset ticker, bot folder, unique code) becomes a path
# segment somewhere downstream. Whitelisting the character set is what makes
# "../../etc" and "a/b" fail here instead of at a filesystem call three layers
# down, where the failure would be harder to trace back to the request.
_SAFE_TOKEN = re.compile(r"^[A-Za-z0-9_.-]+$")

mcp = MCPServer(
    name="okx-risk-supervisor",
    title="OKX Copy-Trading Bot Risk Supervisor",
    instructions=(
        "Scores the risk of an OKX copy-trading bot in 3 steps: observe the "
        "market, analyze the bot with a Monte Carlo simulation, then run QC "
        "to synthesize a recommendation. Use the lookup "
        "tools first (list_assets, list_bots, list_assessed_bots, "
        "get_assessment) -- they read from an existing cache and answer "
        "instantly. Only call assess_bot/get_market when you need a fresh "
        "figure that is not already in the cache; those two tools run the "
        "real pipeline and are slower."
    ),
)


def _require_token(value: Any, field_name: str) -> str:
    """Reject anything that is not a single, plain path segment.

    `bot_folder_name`, `asset`, `symbol` and `unique_code` all come from an AI
    agent and are treated as untrusted input per the project's fail-closed
    rule -- a value like "../../etc" or "cex/BTC" must never reach a path join.
    """
    if not isinstance(value, str) or not value.strip():
        raise ToolError(f"{field_name} must not be empty")
    token = value.strip()
    if token in (".", "..") or not _SAFE_TOKEN.match(token) or ".." in token:
        raise ToolError(
            f"{field_name}={value!r} contains invalid characters or looks "
            f"like a path traversal attempt (only letters, digits, '_', "
            f"'-', '.' are allowed)"
        )
    return token


def _require_venue(venue_type: Any) -> str:
    venue = str(venue_type).strip().upper() if venue_type is not None else ""
    if venue not in VALID_VENUES:
        raise ToolError(
            f"venue_type={venue_type!r} is invalid; only CEX or DEX is accepted"
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
    this project's own test helper (`Agent/none/test/test_agent_server.py::_call`)
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

    # NOTE ON LANGUAGE: the four ToolError messages in this function are
    # deliberately left in Vietnamese, unlike the rest of this file. Each one
    # is asserted verbatim (via `pytest.raises(..., match=...)` on a
    # Vietnamese substring) by Agent/none/test/test_agent_server.py, which is out
    # of scope for this translation pass. Translating these strings without
    # also updating that test file would silently break it. See this
    # module's own translation task notes for the exact test lines.
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
            f"Payment is required before calling tool '{tool_name}' (price "
            f"{challenge['usd_price']}). Resend the request with a "
            f"'{x402.PAYMENT_SIGNATURE_HEADER}' header carrying valid proof "
            f"of payment (x402 standard, see Agent/docs/okx_marketplace.md). "
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
            f"Invalid payment for tool '{tool_name}' "
            f"(reason: {result.invalid_reason}): {result.invalid_message}"
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
    index_path = DATA_DIR / "report" / "single" / "index.json"
    index = _read_json_or_none(index_path)
    if index is None:
        raise ToolError(
            "data/report/single/index.json does not exist yet -- step 3 (QC "
            "scoring) has never run; run the scoring pipeline before "
            "looking anything up."
        )
    return index


@mcp.tool()
def list_assets(ctx: Context) -> Dict[str, Any]:
    """List every asset with crawled data on disk, and which venues (CEX/DEX) cover it."""
    _require_payment(ctx, "list_assets")
    assets: Dict[str, List[str]] = {}
    for venue_dir, venue_type in (("cex", "CEX"), ("dex", "DEX")):
        base = DATA_DIR / "market" / venue_dir
        if not base.is_dir():
            continue
        for asset_dir in sorted(base.iterdir()):
            if asset_dir.is_dir():
                assets.setdefault(asset_dir.name, []).append(venue_type)
    if not assets:
        raise ToolError(
            f"No asset data found under {DATA_DIR} (market/cex/, market/dex/ "
            f"are empty or missing); crawl data before calling this tool."
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
    # Unified layout: `data/trade/<bot_id>/` no longer segregates by
    # venue/asset, so which bots belong to this slot comes from the same
    # slot-assignment logic `assessment_store.build_assessments` already uses
    # (universe/bot_selection.json), not from a directory that no longer
    # exists -- see `assessment_store.bots_in_slot`.
    slot_bots = assessment_store.bots_in_slot(DATA_DIR, venue, clean_asset)
    if not slot_bots:
        raise ToolError(
            f"Asset {clean_asset} has no bot data on {venue} in the dataset; "
            f"crawl it first."
        )
    bots = [
        {
            "bot_folder_name": f"bot_{code}",
            "nick_name": nick_name,
            "unique_code": code,
        }
        for code, nick_name in sorted(slot_bots.items())
    ]
    return {"asset": clean_asset, "venue_type": venue, "bots": bots}


@mcp.tool()
def list_assessed_bots(ctx: Context, verdict: Optional[str] = None) -> Dict[str, Any]:
    """List QC-scored bots from data/assessment/index.json, optionally filtered by verdict.

    verdict: one of the 6 labels in VALID_VERDICTS above (case-insensitive).
    Leave empty to list every scored bot.

    Backward compatibility (task's own explicit requirement): `index.json`'s
    own stored `verdict` field on each summary row may still be one of the 4
    retired single-axis labels for a bot scored before the two-axis
    relabeling. That summary row alone cannot recompute the new label (it
    does not carry `hidden_risk_flags`), so every row's `verdict` is
    recomputed here from that bot's own FULL assessment.json instead --
    same rule `get_assessment` below and `Agent/backend/web/admin_page.py`'s
    listing page already apply. This project's own dataset is at most a few
    dozen assessed bots, so the extra small file read per row costs nothing
    observable next to the index.json read this tool already does.
    """
    _require_payment(ctx, "list_assessed_bots")
    index = _assessment_index()
    bots = []
    for entry in index.get("bots", []):
        entry = dict(entry)
        venue, _, symbol = str(entry.get("slot", "")).partition("/")
        code = entry.get("unique_code")
        payload = (
            assessment_store.load_bot(DATA_DIR, venue, symbol, code)
            if venue and symbol and code
            else None
        )
        cham_diem = payload.get("scoring") if isinstance(payload, dict) else None
        if isinstance(cham_diem, dict):
            entry["verdict"] = label_from_scores(
                cham_diem.get("risk_score"),
                cham_diem.get("quality_score"),
                cham_diem.get("hidden_risk_flags") or [],
            )
        bots.append(entry)
    matched_verdict = None
    if verdict is not None and verdict.strip():
        # Case-insensitive on input, but the result always echoes back one of
        # the six canonical labels so a caller can't be misled into thinking
        # a typo'd verdict is a real seventh category.
        matched_verdict = next(
            (v for v in VALID_VERDICTS if v.upper() == verdict.strip().upper()), None
        )
        if matched_verdict is None:
            raise ToolError(
                f"verdict={verdict!r} is invalid; must be one of: "
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
            f"No bot found with unique_code={clean_code!r} in "
            f"data/report/single/index.json; this bot has not been QC-scored yet."
        )
    venue, _, symbol = str(entry.get("slot", "")).partition("/")
    payload = (
        assessment_store.load_bot(DATA_DIR, venue, symbol, clean_code)
        if venue and symbol
        else None
    )
    if payload is None:
        raise ToolError(
            f"Bot {clean_code!r} is in the index but its assessment.json is "
            f"missing or slot '{entry.get('slot')}' could not be read; the "
            f"data may have been deleted or only partially written."
        )
    # Backward compatibility (same rule as admin_page.py's listing page): a
    # file written before the two-axis relabeling still carries one of the 4
    # retired labels in khuyen_nghi.ket_luan. Unlike list_assessed_bots
    # above, the FULL per-bot document is available here, with the scores
    # and hidden_risk_flags the recompute needs -- so, unlike that tool,
    # this one never has to hand back a stale label.
    khuyen_nghi = payload.get("recommendation")
    cham_diem = payload.get("scoring")
    if isinstance(khuyen_nghi, dict) and isinstance(cham_diem, dict):
        khuyen_nghi["verdict"] = label_from_scores(
            cham_diem.get("risk_score"),
            cham_diem.get("quality_score"),
            cham_diem.get("hidden_risk_flags") or [],
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
            f"Could not score bot {clean_folder!r} ({clean_asset}/{venue}): {exc}"
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
            f"Could not fetch market data for {clean_symbol}/{venue}: {exc}"
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
        prog="python3 -m Agent.backend.scripts.agent_server",
        description=(
            "MCP server for the Risk Supervisor. Defaults to stdio (for a "
            "local client such as Claude Code/Claude Desktop); use "
            "--transport http to serve a remote client (required for the "
            "OKX AI Marketplace)."
        ),
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="stdio (default, local) or http (streamable HTTP, allows remote calls)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help=(
            "Only used with --transport http. Defaults to 127.0.0.1 (only "
            "this machine can call it). Use 0.0.0.0 to open every network "
            "interface -- only do this behind a trusted reverse proxy/"
            "firewall, since the server has no authentication of its own."
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_HTTP_PORT,
        help=(
            "Only used with --transport http. Defaults to "
            f"{DEFAULT_HTTP_PORT}; use 0 to let the OS assign a free port "
            "(useful when running several instances in parallel, e.g. tests)."
        ),
    )
    return parser


def main(argv: Optional[List[str]] = None) -> None:
    """Entry point behind `python3 -m Agent.backend.scripts.agent_server`.

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
        # NOTE ON LANGUAGE: this message is deliberately left in Vietnamese,
        # unlike the rest of this file. Agent/none/test/test_agent_server.py
        # asserts `"CẢNH BÁO" in out` verbatim on this printed text, and that
        # test file is out of scope for this translation pass; translating
        # this string would silently break it.
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
