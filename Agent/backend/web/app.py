"""Starlette HTTP app for the OKX copy-trading risk-supervisor dashboard.

Built on Starlette + uvicorn only -- both already dependencies of the `mcp`
package this project depends on elsewhere (see agent_server.py's module
docstring, which documents the same fact for its own `--transport http`
mode), so nothing new is added to the project's dependency set.

Route surface:

    GET  /                  dashboard HTML (path is configurable, see run_web.py)
    GET  /api/bots          the 30 pre-scored bots (data/assessment/**)
    GET  /api/markets       the 15 pre-analysed assets (data/analysis/**)
    GET  /api/leaderboard   OKX lead-trader ranking, live + cached
    POST /api/lookup        {"code": "..."} -> cheap profile/asset-state lookup
                             (no scoring engine -- see WebDataService.lookup)
    GET/POST /api/analyze   {"code": "..."} (GET: query string only; POST:
                             query string merged with the JSON body, body
                             wins on conflict -- see _resolve_code_param) ->
                             score one bot live (expensive; the dashboard's
                             own flow is meant to call /api/lookup first,
                             then this only once a user opts in -- see
                             data.py's module docstring). GET is accepted
                             alongside POST specifically for the OKX AI
                             Marketplace's `a2mcp-probe` buyer-side CLI,
                             which probes with an empty body first and may
                             retry over GET on a 405 -- accepting both up
                             front removes that extra round trip entirely
                             (see _resolve_code_param's own docstring for the
                             full protocol rationale). Also accepts a small
                             set of case-insensitive synonym parameter names
                             for `code` (uniqueCode/unique_code/botId/bot_id/
                             botCode/bot_code) -- deliberately NOT bare `id`,
                             which is too generic a name to safely guess.
                             Response also carries `report_markdown` (a
                             ready-to-paste write-up) and `report_url`
                             (link to the GET /bot/<code> page below) -- see
                             data.py's build_report_markdown/build_report_url.
                             The per-IP rate limit (ANALYZE_RATE_LIMIT_*
                             below) is only ever charged for a request that
                             actually reaches `service.analyze()` -- an
                             empty/missing/malformed `code`, a synonym
                             conflict, an oversized body (see
                             ANALYZE_MAX_BODY_BYTES), or a missing/invalid
                             access token (see below) all get rejected
                             first, for free -- see api_analyze's own
                             ordering and comments for why.

                             OPTIONALLY gated by a self-issued access token
                             (NEVER an OKX-authenticated identity -- see
                             Agent/backend/web/access.py's module docstring
                             for why a fee=0 Marketplace endpoint like this
                             one cannot possibly receive one) whenever
                             NORABT_ACCESS_TOKENS is configured: missing
                             token -> 401 (`error_en` contains the exact
                             protocol phrase "authentication required"),
                             wrong token -> 403. Unconfigured (the default)
                             means open mode, unchanged from this endpoint's
                             behaviour before this gate existed. When the
                             caller's request also carries a valid, logged-in
                             USER session cookie (see POST /api/session
                             below -- an entirely separate, wallet-address-
                             based identity, orthogonal to this token gate)
                             AND `report_url_is_usable()`, the response gets
                             one extra "xem chi tiết trực quan" line (in both
                             `report_markdown` and `text`) pointing at that
                             user's own obscure `GET /<userref>_<code>` link
                             below, and this call is also recorded into that
                             user's profile (see
                             Agent/backend/web/identity.py's `record_analysis`)
                             so the link actually resolves afterwards. With
                             no user session (the machine-to-machine/OKX
                             Marketplace case this endpoint exists for in the
                             first place -- see access.py's module docstring)
                             the line instead points at the plain, guessable
                             `GET /bot/<code>` below, unchanged from before
                             this feature existed -- see `_with_detail_link`.

                             SEPARATELY, an admin key (see
                             `NORABT_ADMIN_TOKEN_SHA256`, checked via
                             access.verify_admin_token) always gets through
                             this gate regardless of whether
                             NORABT_ACCESS_TOKENS is on, on its own wider
                             (but still bounded, see ADMIN_RATE_LIMIT_*
                             above) per-IP quota, and the response gets an
                             extra `"access_level": "admin"` field so a
                             tester knows the admin path was actually taken.
                             Unconfigured (the default) changes nothing.
    POST /api/session       {"identity": "..."} -> a signed, HttpOnly session
                             cookie (see access.py's `create_session_cookie`/
                             `read_session`), 8h TTL. `identity` matching the
                             configured admin key -> an ADMIN session;
                             `identity` shaped like a `0x`+40-hex wallet
                             address -> a USER session for that address's
                             derived `user_ref` (creating/touching that
                             user's profile, see identity.py's
                             `get_or_create_profile`); anything else -> 400.
                             See identity.py's own module docstring for the
                             accepted, explicitly-warned-about risk this
                             wallet-address "login" carries, and for why the
                             cookie itself never contains the wallet address
                             or the admin key -- only the already-derived,
                             non-reversible `user_ref` (or a bare admin
                             flag).
    POST /api/session/logout clears the session cookie set above.
    GET  /bot/<code>        human-readable HTML report for one bot -- the
                             page `report_url` above points at for a
                             SESSIONLESS caller (machine-to-machine, admin);
                             a caller with a logged-in USER session instead
                             gets `report_url` pointing at their own
                             `/<userref>_<code>` below, matching the
                             "xem chi tiết trực quan" line verbatim -- see
                             `_with_detail_link`'s own comment on why the two
                             must never diverge. This route itself is
                             intentionally left UNCHANGED/ungated by the
                             access-token gate either way (see `bot_report`'s
                             own docstring for why). Same `code` validation
                             as /api/analyze, same rate limit (it runs the
                             same scoring pipeline).
    GET  /<userref>_<code>  the SAME report page as GET /bot/<code> above,
                             reached through a logged-in user's own obscure
                             `user_ref` instead of a guessable bot code --
                             see `user_report` below. Opens only when the
                             (userref, code) pair is on record in that
                             user's profile (i.e. that user's own session
                             already analyzed this exact `code` at least
                             once -- see identity.py's `has_analyzed`), or
                             the viewer is admin; anything else, INCLUDING a
                             `userref` that fails format validation, is the
                             exact same generic 404 -- never distinguishing
                             why, for the same reasons the former `/r/<ref>`
                             route (removed; see this module's git history)
                             already documented. Replaces that route
                             entirely -- there is only ever one report-link
                             mechanism live at a time.
    GET  /healthz           container/orchestrator liveness probe (see below)
    GET  /admin             admin-only listing page across every bot this
                             process has an opinion about (pre-scored on
                             disk + analyzed live this session) -- see
                             `admin_page` below. Gated by the SAME admin key
                             as /api/analyze's own admin role
                             (NORABT_ADMIN_TOKEN_SHA256, checked via
                             access.verify_admin_token), but the FAILURE mode
                             is deliberately different: a missing/wrong key
                             (or the admin role simply not being configured
                             at all, the default) is a single generic 404,
                             NEVER 401/403 -- an admin route that answers
                             "exists, but you're not allowed" to a stranger
                             has already told them exactly where to point a
                             brute-force attempt. This route also never
                             costs a single OKX request or runs the scoring
                             pipeline -- it only reads the SAME pre-scored
                             `data/assessment/**` files GET /api/bots already
                             serves, through a short-TTL cache so a human
                             refreshing this page does not re-walk that
                             whole directory tree on every load.

Every route is wrapped so it can never let a raw exception (and therefore a
Python traceback) reach the client: known outcomes (bad input, rate limit)
map to a specific HTTP status with a Vietnamese JSON body, and a final
`Exception` handler at the app level is the last line of defence for
anything unanticipated. `WebDataService.analyze()` itself already treats
NOT_FOUND/LIMITED as ordinary 200 results, per the task's own contract --
this module never re-wraps those as errors.
"""

from __future__ import annotations

import html
import ipaddress
import logging
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Route

from Agent.backend.infra.config import config
from Agent.backend.web import access, identity
from Agent.backend.web.admin_page import render_admin_page_html
from Agent.backend.web.data import (
    InvalidCodeError,
    PerIpRateLimiter,
    WebDataService,
    build_report_markdown,
    build_report_url,
    detail_link_line,
    report_base_url,
    report_url_is_usable,
    validate_unique_code,
)
from Agent.backend.web.report_page import render_bot_report_html

logger = logging.getLogger(__name__)

# Default location for the dashboard HTML file, overridable via run_web.py's
# --dashboard flag or the NORABT_WEB_DASHBOARD env var it reads. Deliberately
# does not need to exist -- see _dashboard_response's fallback below -- so a
# fresh checkout with no dashboard authored yet still serves a working API.
DEFAULT_DASHBOARD_PATH = Path(config.BASE_DIR) / "web" / "dashboard.html"

# --------------------------------------------------------------------------- #
# Client IP resolution -- shared by every route that feeds `PerIpRateLimiter`
# (api_analyze, bot_report, user_report/_bot_report_response below).
#
# WHY THIS EXISTS: this app runs behind nginx inside Docker (see
# Agent/deploy/docker-compose.yml). `request.client.host` -- what Starlette
# sees as the TCP peer -- is therefore ALWAYS the reverse proxy's own
# address (loopback or the Docker bridge network), never the real caller's
# IP. Using it directly for `PerIpRateLimiter` collapses every distinct
# caller on the internet into ONE shared bucket: one caller making 5 calls
# exhausts ANALYZE_RATE_LIMIT_MAX_REQUESTS for every other caller behind the
# same proxy too. This must be fixed before this endpoint is reachable from
# a real domain -- see this module's own docstring on why the rate limiter
# exists at all (bounding CPU/OKX-quota cost per caller, not per proxy hop).
# --------------------------------------------------------------------------- #

# CIDR ranges this app trusts to hand it an accurate `X-Real-IP`/
# `X-Forwarded-For`. Loopback (this container talking to itself, e.g. a
# healthcheck or a dev box with no proxy at all) plus the three RFC1918
# private ranges Docker's bridge networks draw addresses from (see
# Agent/deploy/docker-compose.yml) -- i.e. "the nginx container sitting
# directly in front of this one", never a public address. Overridable via
# NORABT_TRUSTED_PROXIES for a deployment with a differently-addressed
# proxy layer; see Agent/.env.example for the operator-facing warning
# against ever widening this to a public range.
TRUSTED_PROXIES_ENV = "NORABT_TRUSTED_PROXIES"
DEFAULT_TRUSTED_PROXY_CIDRS = (
    "127.0.0.0/8",
    "::1/128",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "10.0.0.0/8",
)

_IpAddress = Union[ipaddress.IPv4Address, ipaddress.IPv6Address]
_IpNetwork = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


def _parse_ip(value: str) -> Optional[_IpAddress]:
    """`None` for anything that is not a single, plain IP address --
    covers a blank string, free text, and a comma-separated list handed to
    this by mistake (e.g. an `X-Forwarded-For`-shaped value read as if it
    were `X-Real-IP`). Never raises: this only ever sees attacker- or
    misconfigured-proxy-controlled input, so a malformed value must degrade
    to "ignore this header", not crash the request.
    """
    try:
        return ipaddress.ip_address(value.strip())
    except ValueError:
        return None


def _trusted_proxy_networks() -> List[_IpNetwork]:
    """Read `TRUSTED_PROXIES_ENV` at call time (same "live, not import-time"
    pattern as `access.load_tokens()`), so a test can flip it with
    `monkeypatch.setenv`/`delenv` and an operator's change takes effect on
    the next request. Blank/unset both fall back to
    `DEFAULT_TRUSTED_PROXY_CIDRS` UNCHANGED -- a deliberately explicit
    override (a non-blank value) REPLACES the default set entirely rather
    than extending it, so an operator who sets this cannot end up with a
    wider trusted set than they typed by accident.
    """
    raw = os.environ.get(TRUSTED_PROXIES_ENV, "").strip()
    cidrs = (
        DEFAULT_TRUSTED_PROXY_CIDRS
        if not raw
        else [part.strip() for part in raw.split(",") if part.strip()]
    )
    networks: List[_IpNetwork] = []
    for cidr in cidrs:
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            logger.warning(
                "%s: bỏ qua dải CIDR không hợp lệ %r", TRUSTED_PROXIES_ENV, cidr
            )
    return networks


def _peer_is_trusted_proxy(peer_ip: str) -> bool:
    parsed = _parse_ip(peer_ip)
    if parsed is None:
        return False
    return any(parsed in network for network in _trusted_proxy_networks())


def resolve_client_ip(request: Request) -> str:
    """The IP `PerIpRateLimiter` should charge this request against --
    shared by every route below that rate-limits per caller.

    THE ANTI-SPOOFING RULE THAT MATTERS MOST: forwarded-IP headers
    (`X-Real-IP`, `X-Forwarded-For`) are read ONLY when the direct TCP peer
    (`request.client.host`) is itself a trusted proxy (see
    `_peer_is_trusted_proxy`/`TRUSTED_PROXIES_ENV` above). If this trusted a
    header from ANY peer unconditionally, a stranger on the open internet
    could defeat the per-IP rate limit entirely just by sending a fresh
    random `X-Real-IP` on every request -- the exact "gộp cả internet vào
    một rổ" bug this function fixes would simply be replaced by an equally
    broken "every request gets its own private rổ, limiting nothing".

    From a trusted peer, `X-Real-IP` wins when present (nginx's own config
    sets it to the already-resolved real client IP -- see
    Agent/deploy/README.md's nginx block); otherwise the FIRST entry of
    `X-Forwarded-For` is used (the address closest to the original client,
    since each proxy hop only ever APPENDS to that list). A header present
    but not a parseable IP (garbage, blank, a stray trailing comma) is
    treated as if it were entirely absent and this falls straight back to
    the raw peer IP -- NEVER cascades from a malformed `X-Real-IP` into
    trying `X-Forwarded-For` instead, so a half-broken proxy config fails
    closed (one shared bucket, safe) rather than in some other
    unpredictable way.

    No `request.client` at all (some ASGI test harnesses never set one)
    keeps returning the literal `"unknown"` this app already used before
    this function existed -- `PerIpRateLimiter` still works, just as one
    shared bucket for that case, exactly as before.
    """
    if request.client is None:
        return "unknown"
    peer = request.client.host
    if not _peer_is_trusted_proxy(peer):
        return peer

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        parsed = _parse_ip(real_ip)
        return str(parsed) if parsed is not None else peer

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_hop = forwarded_for.split(",")[0]
        parsed = _parse_ip(first_hop)
        return str(parsed) if parsed is not None else peer

    return peer


# Rate limit applied to POST /api/analyze specifically: each call costs
# several seconds of CPU and several OKX requests (see data.py's module
# docstring), so this is deliberately much tighter than a generic API rate
# limit would be. Charged ONLY for a call that actually reaches
# service.analyze() -- see api_analyze below, which now resolves/validates
# `code` BEFORE touching the limiter. That ordering matters specifically for
# the OKX a2mcp-probe CLI: its protocol always opens with an EMPTY probe
# request (no `code`) purely to discover a parameter is required, then asks
# a human for the bot code and probes again -- possibly several times if
# they mistype it, or once more on top of that if the CLI's own GET<->POST
# 405 fallback kicks in. None of those round trips cost this server any CPU
# or any OKX request, so none of them may consume this budget. A 429 is
# also a DEAD END for that CLI, not a "wait and retry" signal -- it treats
# a rate limit as a terminal failure, so charging quota for a probe or a
# mistyped code would cut the buyer out of the flow entirely instead of
# letting them be reprompted for the right code.
ANALYZE_RATE_LIMIT_MAX_REQUESTS = 5
ANALYZE_RATE_LIMIT_WINDOW_SECONDS = 60.0

# Separate, wider budget for a caller authenticated as admin (see
# access.verify_admin_token) -- NOT an exemption. Deliberately NOT unlimited:
# every call still costs the same several seconds of CPU and several OKX
# requests as an ordinary call (see ANALYZE_RATE_LIMIT_MAX_REQUESTS above),
# so if the admin key ever leaked, an unlimited caller behind it could still
# take this whole service down. 60/min is generous enough that a human
# manually testing bot codes one at a time will never notice a limit exists,
# while still bounding the worst case to "one request roughly per second".
# Same 60-second window as the ordinary limit, tracked in its own
# `PerIpRateLimiter` instance (see create_app()) so an admin caller's usage
# never shares -- and therefore never starves, or is starved by -- an
# ordinary token's own ANALYZE_RATE_LIMIT_MAX_REQUESTS budget.
ADMIN_RATE_LIMIT_MAX_REQUESTS = 60
ADMIN_RATE_LIMIT_WINDOW_SECONDS = 60.0

# Max accepted size of a POST /api/analyze (or /api/lookup-shaped) request
# body, enforced BEFORE the body is read/parsed. A valid body is nothing
# more than a small JSON object holding one bot code (see _CODE_PARAM_SCHEMA
# below), so 64 KiB is already wildly generous headroom over anything a real
# caller would ever send. This exists to replace a protection the rate
# limiter used to provide only by accident: when `limiter.allow()` ran
# first, an oversized body was implicitly capped by however few requests
# the limiter allowed through before parsing ever happened. Now that the
# limiter runs LAST (see ANALYZE_RATE_LIMIT_MAX_REQUESTS above), that
# incidental protection is gone, so this explicit size guard takes its
# place -- see _enforce_max_body_size.
ANALYZE_MAX_BODY_BYTES = 64 * 1024

# GET /admin -- how long the pre-scored bot listing (Agent/data/assessment/**,
# read via service.list_bots()) is reused before being re-read off disk. That
# read walks the ENTIRE assessment tree (see list_scored_bots's own glob),
# which is cheap once but must not happen on every single page load/refresh
# a human does while poking at this page -- 45s is comfortably inside the
# 30-60s window the task itself asks for: long enough that a human clicking
# around (sorting, going to a bot's detail page, coming back) never
# re-triggers the scan, short enough that a batch report that just finished
# writing new assessment.json files shows up within under a minute without
# anyone having to restart this process.
ADMIN_BOTS_CACHE_TTL_SECONDS = 45.0

# GET /healthz -- see the handler built inside create_app() for the full
# rationale. The OKX check reuses the exact endpoint okx/probe.py's own
# check_public_access() already uses to answer "connect được sàn chưa?",
# so a second, differently-shaped probe of the same fact isn't invented here.
HEALTHZ_OKX_CHECK_PATH = "/api/v5/public/time"

# How long a "was OKX's public endpoint reachable" result is reused before
# checking again. This route is meant to be polled often by an orchestrator
# (docker-compose's `healthcheck:` in Agent/deploy/docker-compose.yml runs it
# every ~30s) -- without a cache, every poll would cost one extra OKX request
# purely for a liveness probe, competing with the same shared rate budget
# POST /api/analyze and GET /api/leaderboard already have to ration (see
# ANALYZE_RATE_LIMIT_* above and data.py's TokenBucket).
HEALTHZ_OKX_CACHE_TTL_SECONDS = 20.0

_FALLBACK_DASHBOARD_HTML = """<!doctype html>
<html lang="vi">
<head><meta charset="utf-8"><title>Dashboard chưa sẵn sàng</title></head>
<body style="font-family: system-ui, sans-serif; max-width: 640px; margin: 3rem auto; padding: 0 1rem;">
<h1>Chưa tìm thấy trang dashboard</h1>
<p>Không đọc được file HTML tại: <code>{path}</code></p>
<p>Đặt đường dẫn đúng qua tham số CLI <code>--dashboard</code> hoặc biến môi
trường <code>NORABT_WEB_DASHBOARD</code> khi khởi động server, hoặc dùng trực
tiếp các API JSON bên dưới trong lúc chờ dashboard:</p>
<ul>
<li><code>GET /api/bots</code></li>
<li><code>GET /api/markets</code></li>
<li><code>GET /api/leaderboard</code></li>
<li><code>POST /api/lookup</code> — body <code>{{"code": "..."}}</code></li>
<li><code>POST /api/analyze</code> — body <code>{{"code": "..."}}</code></li>
</ul>
</body>
</html>
"""


def _dashboard_response(path: Path) -> HTMLResponse:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        # Missing/unreadable dashboard file must never crash the route --
        # see the task's own requirement 7 ("đừng crash"). 200, not 404: the
        # server itself is working fine, only the optional HTML asset is
        # absent, and the JSON API underneath is fully usable regardless.
        return HTMLResponse(_FALLBACK_DASHBOARD_HTML.format(path=path))
    return HTMLResponse(content)


_REPORT_ERROR_HTML = """<!doctype html>
<html lang="vi">
<head><meta charset="utf-8"><title>Không tạo được báo cáo</title></head>
<body style="font-family: system-ui, sans-serif; max-width: 640px; margin: 3rem auto; padding: 0 1rem;">
<h1>Không tạo được báo cáo bot</h1>
<p>{message}</p>
</body>
</html>
"""


def _report_error_html(message: str) -> str:
    # `message` here is always a string this module itself wrote (a
    # Vietnamese error sentence, an InvalidCodeError message, or `str(exc)`
    # from a caught exception) -- html.escape it anyway on principle: an
    # unexpected exception's text is not something this module fully
    # controls the contents of either.
    return _REPORT_ERROR_HTML.format(message=html.escape(message))


def _error_json(message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        {"status": "ERROR", "message": message}, status_code=status_code
    )


# --------------------------------------------------------------------------- #
# Lỗi 2 fix -- unanticipated-error responses must never leak internals
# (absolute container paths, OS errno text, exception type names,
# tracebacks) to an internet-facing caller. Every generic
# `except Exception as exc:` branch below USED TO interpolate `str(exc)`
# straight into the JSON/HTML body -- which is exactly how a plain
# `OSError` from a read-only bind mount ended up handing out the literal
# path `/app/Agent/data/users` to whoever called POST /api/session (see
# identity.py's `ProfileStoreError` for the write-side half of this same
# fix). The exception's own detail still needs to reach a human who can
# act on it -- it now goes to the SERVER LOG ONLY, tagged with a short
# random incident code that also appears in the (generic, Vietnamese)
# response body, so an operator can grep the log for the exact code a user
# reports back.
# --------------------------------------------------------------------------- #


def _new_incident_code() -> str:
    """8 lowercase-hex characters (32 bits from `secrets`, a CSPRNG) -- long
    enough that two unrelated errors essentially never collide in a log a
    human is grepping through, short enough to read aloud or paste into a
    support message. Not a security token (nothing is gated on it, see
    `_log_incident` below) -- just a correlation id, hence `secrets` for
    convenient hex formatting rather than for any confidentiality property.
    """
    return secrets.token_hex(4)


def _log_incident(context: str, exc: BaseException) -> str:
    """Log the FULL detail of an unanticipated exception (type, message,
    traceback via `exc_info`) server-side, tagged with a fresh incident
    code, and return that code so the caller can fold it into the generic
    Vietnamese message actually shown to the client. `context` is a short,
    developer-facing tag (e.g. "POST /api/session") -- never anything
    derived from user input -- identifying which route/step failed, purely
    to make the log line greppable; it is never shown to the client.
    """
    code = _new_incident_code()
    logger.error(
        "incident %s (%s): %s: %s", code, context, type(exc).__name__, exc, exc_info=exc
    )
    return code


def _generic_error_message(incident_code: str) -> str:
    """The ONE Vietnamese sentence every unanticipated-error branch below
    now shows a client -- no path, no exception type, no OS errno, ever.
    The incident code lets a user's bug report be matched back to the full
    detail `_log_incident` above already wrote to the server log.
    """
    return (
        "Đã xảy ra lỗi hệ thống ngoài dự kiến. Vui lòng thử lại sau; nếu vẫn "
        f"gặp lỗi, vui lòng báo lại mã sự cố: {incident_code}."
    )


# GET/POST /api/analyze's structured 400 for a MISSING `code` (task's Việc 4,
# extended for GET+synonyms below).
#
# Why this exists in ADDITION to the plain Vietnamese message every other
# 400 in this module already carries: the OKX AI Marketplace side lets a
# buyer's CLI ("a2mcp-probe") "probe" a paid/free agent service before
# calling it. Per that CLI's own routing table (recovered from its binary --
# see the task this module implements), when a probe's own request is
# rejected, the CLI scans the response text for a small set of English
# substrings (e.g. "missing required parameter") to decide whether to ask a
# human for input (`input_required`) or treat the call as a hard failure. A
# structured body describing the exact parameter (name/type/required/
# meaning/example) additionally lets that probe ask the right question
# directly instead of guessing from this service's free-text marketplace
# description. This is answered only for a MISSING/wrong-type `code` (see
# _resolve_code_param/api_analyze below) -- a non-empty string that merely
# fails format validation (bad characters, a path-traversal attempt, too
# long) goes through _invalid_param_response instead (Việc 4's OTHER branch),
# never this one.
_CODE_PARAM_SCHEMA: Dict[str, Any] = {
    "name": "code",
    "type": "string",
    "required": True,
    "location": "body.code (JSON) hoặc query string ?code=...",
    "description": (
        "uniqueCode của bot copy-trading trên OKX -- dạng hex hoặc số, chỉ "
        "chữ và số, tối đa 64 ký tự."
    ),
    # Same example value as `_REQUEST_SPEC`/Agent/deploy/okx-listing.md's own
    # `[Request Example]` line below -- this is the code the OKX listing
    # itself advertises, so a reviewer who copy-pastes that listing's curl
    # command gets a request that matches this endpoint's own self-reported
    # example, not a different bot code. Verified live: EF1CC6F40E834D1A is
    # a real bot (status=FULL, name "RuiJie", 373 closed orders).
    "example": "EF1CC6F40E834D1A",
}

# `requestSpec` -- the exact shape the OKX a2mcp-probe CLI itself uses to
# describe a request when a schema cannot be pulled from a probe response
# (per the task's own reverse-engineering of that CLI). Included on both
# error branches below (missing AND invalid-value) so a caller falls back
# to this instead of ever having to parse `serviceDescription`'s free text
# (see Agent/deploy/okx-listing.md, which now ALSO carries the same spec in
# its required "[Parameter Spec]" line as a second, static fallback for
# whichever surface a given caller reads first).
_REQUEST_SPEC: Dict[str, Any] = {
    "method": "POST",
    "carrier": "body",
    "required": ["code"],
    "fields": [
        {
            "name": "code",
            "type": "string",
            "required": True,
            "description": _CODE_PARAM_SCHEMA["description"],
            "example": "EF1CC6F40E834D1A",
        }
    ],
}

# Env var letting an operator move the missing-parameter status code without
# a redeploy (task's own reasoning: the real domain is not DNS-live yet, so
# whether the OKX a2mcp-probe CLI actually accepts 400 for its own
# `input_required` classification cannot be confirmed end-to-end today --
# see Agent/deploy/okx-listing.md/this module's docstring). Only these three
# codes are meaningful to that CLI's own documented state machine (200 "it
# worked anyway", 400 "structured client error", 422 "unprocessable input");
# anything else is almost certainly a typo and must not silently change this
# route's contract, hence the fall-back-to-400-with-a-warning below rather
# than passing an arbitrary value through.
MISSING_PARAM_STATUS_ENV = "NORABT_A2MCP_MISSING_PARAM_STATUS"
DEFAULT_MISSING_PARAM_STATUS = 400
_ALLOWED_MISSING_PARAM_STATUSES = (200, 400, 422)


def _missing_param_status() -> int:
    """Read `MISSING_PARAM_STATUS_ENV` at call time (like data.py's own
    `report_base_url()`) so a test can flip it with monkeypatch.setenv
    without reloading this module. Never raises and never returns anything
    outside `_ALLOWED_MISSING_PARAM_STATUSES` -- an unset/unparsable/
    out-of-range value falls back to `DEFAULT_MISSING_PARAM_STATUS` with a
    logged warning, per the task's own instruction.
    """
    raw = os.environ.get(MISSING_PARAM_STATUS_ENV)
    if raw is None:
        return DEFAULT_MISSING_PARAM_STATUS
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        logger.warning(
            "%s=%r không phải số nguyên hợp lệ -- dùng mặc định %d",
            MISSING_PARAM_STATUS_ENV,
            raw,
            DEFAULT_MISSING_PARAM_STATUS,
        )
        return DEFAULT_MISSING_PARAM_STATUS
    if value not in _ALLOWED_MISSING_PARAM_STATUSES:
        logger.warning(
            "%s=%d không thuộc %s -- dùng mặc định %d",
            MISSING_PARAM_STATUS_ENV,
            value,
            _ALLOWED_MISSING_PARAM_STATUSES,
            DEFAULT_MISSING_PARAM_STATUS,
        )
        return DEFAULT_MISSING_PARAM_STATUS
    return value


def _missing_code_response() -> JSONResponse:
    return JSONResponse(
        {
            "status": "ERROR",
            "message": (
                "Thiếu tham số bắt buộc 'code' (uniqueCode của bot trên OKX) "
                "trong body JSON hoặc query string -- ví dụ: "
                '{"code": "EF1CC6F40E834D1A"}.'
            ),
            "error": {
                "type": "MISSING_PARAMETER",
                "params": [_CODE_PARAM_SCHEMA],
            },
            # `error_en` is a PROTOCOL string, not prose for a human: it is
            # the exact, lowercase substring
            # (src/commands/agent_commerce/a2mcp_probe/probe.rs's own
            # matching table, recovered from the CLI binary) the OKX
            # a2mcp-probe CLI scans an error response for to classify it as
            # `input_required` and switch into its parameter-collection
            # flow instead of giving up. It must NEVER be translated,
            # reworded, or recapitalized -- doing so would silently break
            # that classification for every buyer using the official CLI.
            "error_en": "missing required parameter: code",
            "requestSpec": _REQUEST_SPEC,
        },
        status_code=_missing_param_status(),
    )


def _invalid_param_response(message: str) -> JSONResponse:
    """400 for a `code` that IS present but rejected -- either it fails
    `validate_unique_code`'s own format check (bad characters, path
    traversal, too long), or two synonym parameter names (Việc 2) carried
    two different values and this module refuses to silently pick one.

    `error_en` is deliberately "invalid parameter value", NOT "missing
    required parameter": per the task's own CLI reverse-engineering, those
    two English substrings route the OKX a2mcp-probe CLI down two different
    paths -- "missing" makes it go ask a human for the parameter again,
    which is the WRONG reaction to a value that was already supplied and
    rejected. Like `_missing_code_response`'s `error_en`, this exact
    lowercase phrase is protocol, not prose -- never translate/recapitalize.
    """
    return JSONResponse(
        {
            "status": "ERROR",
            "message": message,
            "error_en": "invalid parameter value",
            "requestSpec": _REQUEST_SPEC,
        },
        status_code=400,
    )


# Case-insensitive synonym parameter names api_analyze accepts for `code`
# (task's Việc 2), stored already-lowercased so lookup is a plain membership
# test against a lowercased incoming key -- see _resolve_code_param.
# Deliberately EXCLUDES bare "id": it is generic enough that a caller
# sending an unrelated identifier (a job id, an order id, ...) would get
# silently -- and wrongly -- reinterpreted as a bot code, which the task
# calls out as worse than just rejecting it as missing.
_CODE_PARAM_ALIASES = frozenset(
    {"code", "uniquecode", "unique_code", "botid", "bot_id", "botcode", "bot_code"}
)


def _lower_string_keys(mapping: Any) -> Dict[str, Any]:
    """`{"Code": "x", 1: "y"}` -> `{"code": "x"}` -- non-dict input (a JSON
    body that parsed to a list/number/string, see _resolve_code_param) and
    non-string keys both become "nothing here", never an exception.
    """
    if not isinstance(mapping, dict):
        return {}
    return {
        key.lower(): value for key, value in mapping.items() if isinstance(key, str)
    }


async def _merged_request_params(request: Request) -> Dict[str, Any]:
    """Query string + (POST) JSON body merged into one case-lowered dict,
    body values winning over query values on a key collision.

    Factored out of `_resolve_code_param` so it can ALSO back
    `_resolve_access_token` below: both need exactly the same "what counts
    as a request parameter, and which of query/body wins" rules (the
    OKX a2mcp-probe CLI, and the OKX Marketplace parameter-carrier
    mechanism generally, can only ever forward ordinary parameters -- see
    `_resolve_access_token`'s own docstring for why an access token has to
    be accepted as one too, not just as a header). Having one shared
    primitive means there is exactly one place that decides this, instead
    of two independent body-parsing passes that could silently drift apart
    (e.g. one accepting a synonym shape the other doesn't).

    A missing/empty body, one that fails to parse as JSON, or one that
    parses to something other than a JSON OBJECT (a bare list/number/
    string) is treated as "no parameters from the body" -- NOT a parse
    error -- per the task's explicit instruction for `_resolve_code_param`;
    the same leniency is simply inherited here for every caller.

    Calling `request.json()` more than once per request (once from here for
    `code`, once again for `token`) is cheap, not double I/O: Starlette's
    own `Request.json()`/`.body()` cache their result on the `Request`
    object after the first read, and `_enforce_max_body_size` above already
    primed that cache (`request._body`) before either caller ever runs.
    """
    query_lower = _lower_string_keys(dict(request.query_params))
    merged: Dict[str, Any] = dict(query_lower)
    if request.method == "POST":
        try:
            body: Any = await request.json()
        except Exception:
            body = None
        merged.update(_lower_string_keys(body if isinstance(body, dict) else {}))
    return merged


async def _resolve_code_param(request: Request) -> Tuple[Optional[Any], Optional[str]]:
    """Extract the `code` parameter for GET/POST /api/analyze (task's Việc 1
    + Việc 2).

    Sources, in increasing priority (see `_merged_request_params`):
      1. The query string -- always read, for both GET and POST, since a
         POST that also carries a query string is legal HTTP and the task
         explicitly asks for the two to be merged.
      2. The JSON body -- POST only.
      3. When the same key (case-insensitively) is set by both, the body
         value wins (task's own "body thắng" rule).

    Every key is matched against `_CODE_PARAM_ALIASES` case-insensitively.
    If more than one DISTINCT alias key is present (e.g. both `code` and
    `botId` in the same request) their values must agree; if they do not,
    this returns `(None, <Vietnamese conflict message>)` so the caller can
    answer with `_invalid_param_response` instead of silently preferring
    one -- the task is explicit that guessing here would be worse than
    rejecting.

    Returns `(value, conflict_message)`. `conflict_message` is `None` in
    the normal case; `value` is then either the resolved parameter value
    (any JSON type -- api_analyze itself still checks it is a non-blank
    string before treating it as usable, exactly as before this task) or
    `None` when no alias key was present at all (a plain missing parameter,
    indistinguishable from before this task's synonym support existed).
    """
    merged = await _merged_request_params(request)
    candidates: List[Tuple[str, Any]] = [
        (key, value) for key, value in merged.items() if key in _CODE_PARAM_ALIASES
    ]
    if not candidates:
        return None, None

    first_key, first_value = candidates[0]
    for other_key, other_value in candidates[1:]:
        if str(other_value).strip() != str(first_value).strip():
            return None, (
                "Các tên tham số đồng nghĩa của 'code' mang giá trị khác nhau "
                f"('{first_key}'={first_value!r} khác '{other_key}'={other_value!r}) "
                "-- vui lòng chỉ gửi một giá trị duy nhất."
            )
    return first_value, None


async def _resolve_access_token(request: Request) -> Optional[str]:
    """Extract the caller-supplied access token for /api/analyze's optional
    auth gate (see `Agent/backend/web/access.py`'s module docstring for
    what this token is, and pointedly is NOT, proof of).

    Sources, in priority order:
      1. The `X-Access-Token` header.
      2. A `token` key in the merged query-string/JSON-body parameters (see
         `_merged_request_params`) -- REQUIRED in addition to the header,
         not merely a convenience: the OKX a2mcp-probe CLI on the buyer
         side, and the OKX Marketplace parameter-carrier mechanism it runs
         on, can only ever forward PARAMETERS a human typed into it, never
         an arbitrary custom HTTP header -- exactly the same constraint
         `_resolve_code_param`'s own docstring documents for `code`'s
         synonym parameter names. Without this fallback, nobody using the
         official buyer-side tooling could ever supply a token at all.

    Returns `None` for "no token supplied" -- indistinguishable from an
    empty-string token, which is deliberate: an empty token can never be a
    real configured one (see `access._parse_tokens`, which skips blank
    segments), so treating it as "missing" rather than "wrong" produces the
    more accurate 401 instead of a 403.
    """
    header_token = request.headers.get("x-access-token")
    if header_token:
        return header_token
    merged = await _merged_request_params(request)
    token = merged.get("token")
    return token if isinstance(token, str) and token else None


async def _is_admin_request(request: Request) -> bool:
    """Whether `request` carries a valid admin credential -- the one check
    shared by `GET /admin`, `GET /bot/<code>` and `GET /<userref>_<code>`
    (see `admin_page`, `bot_report`, `user_report` below). Deliberately
    simpler than `api_analyze`'s own inline admin handling: those three
    routes only ever need a plain yes/no ("show the ADMIN banner / allow
    this page or not"), never the "admin bypasses the ordinary token gate"
    interaction `api_analyze` also has to resolve.

    Two INDEPENDENT ways to satisfy this, either sufficient on its own:

      1. The same admin API key `api_analyze` already accepts (header/query/
         body, see `_resolve_access_token`), checked via
         `access.verify_admin_token`. `access.is_admin_configured()`
         short-circuits this branch to a no-op at zero cost when neither
         `NORABT_ADMIN_TOKEN_SHA256` nor `OKX_API_KEY` is set (see that
         function's own docstring) -- these routes then behave exactly as
         they did before this task, for every caller, with no token ever
         even looked at.
      2. A valid ADMIN session cookie (see `POST /api/session`,
         `access.read_session`) -- the browsing-session counterpart to (1)
         for a human who already "logged in" as admin once instead of
         supplying the raw key on every single request. Checked
         unconditionally (not gated behind `is_admin_configured()`):
         `read_session` already re-verifies the cookie's own HMAC signature
         on every call, so a request with no cookie at all costs one dict
         lookup (`request.cookies.get(...)` returning `None`) before
         `read_session` short-circuits on that `None`.
    """
    if access.is_admin_configured():
        token = await _resolve_access_token(request)
        if token and access.verify_admin_token(token):
            return True
    session = access.read_session(request.cookies.get(access.SESSION_COOKIE_NAME))
    return bool(session and session.get("is_admin"))


def _missing_token_response() -> JSONResponse:
    """401 for /api/analyze when access-token protection is enabled (see
    access.is_protected) and the caller supplied no token at all -- via
    neither the `X-Access-Token` header nor a `token` parameter.

    `error_en` carries the exact, lowercase, protocol-shaped phrase
    "authentication required" -- see the task's own instruction that this
    string is what an automated caller (present or future) scans for to
    classify this response as "you forgot to authenticate", the same
    mechanism `_missing_code_response`'s `error_en` already serves for a
    missing `code`. Never translate/recapitalize it once anything comes to
    depend on the literal string.
    """
    return JSONResponse(
        {
            "status": "ERROR",
            "message": (
                "Thiếu token xác thực -- gửi kèm qua header 'X-Access-Token' "
                "hoặc tham số 'token' trong query string/body JSON."
            ),
            "error_en": "authentication required",
        },
        status_code=401,
    )


def _invalid_token_response() -> JSONResponse:
    """403 for /api/analyze when access-token protection is enabled and the
    caller DID supply a token, but it matches none of the tokens configured
    in NORABT_ACCESS_TOKENS.

    401 vs 403 here follows ordinary HTTP convention: 401 ("who are you?")
    for no credential at all (`_missing_token_response` above), 403 ("I
    checked who you claim to be, and it's not allowed") for a credential
    that was actually checked and rejected.
    """
    return JSONResponse(
        {
            "status": "ERROR",
            "message": "Token xác thực không hợp lệ.",
            "error_en": "invalid access token",
        },
        status_code=403,
    )


_BODY_TOO_LARGE_MESSAGE = (
    "Nội dung request quá lớn -- /api/analyze chỉ cần một object JSON nhỏ "
    f"chứa mã bot, giới hạn tối đa {ANALYZE_MAX_BODY_BYTES // 1024} KiB."
)


async def _enforce_max_body_size(request: Request) -> Optional[Response]:
    """Reject an oversized POST body with 413 -- BEFORE it is read/parsed.

    This must run first, ahead of `_resolve_code_param` (which is what
    actually calls `request.json()`): now that the rate limiter no longer
    runs before parameter resolution (see api_analyze/ANALYZE_RATE_LIMIT_*
    above), it no longer incidentally caps body size either, so this is the
    sole guard against a large/hostile body.

    `Content-Length`, when present and a plain integer, is trusted for a
    reject-without-reading-a-single-byte fast path. When it is absent (most
    notably a chunked request, which by definition carries no
    Content-Length) or unparsable, the body is instead streamed and counted
    by hand, bailing out with 413 the instant the running total crosses the
    limit -- so a chunked request can never ride around this guard the way
    it would around a Content-Length-only check.
    """
    if request.method != "POST":
        return None

    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError:
            declared_size = None
        if declared_size is not None:
            if declared_size > ANALYZE_MAX_BODY_BYTES:
                return _error_json(_BODY_TOO_LARGE_MESSAGE, 413)
            return None

    # No trustworthy Content-Length -- read the body ourselves, bounded, so
    # a chunked (or otherwise header-less) request can't buffer more than
    # ANALYZE_MAX_BODY_BYTES worth of data into memory before this fires.
    total = 0
    chunks: List[bytes] = []
    async for chunk in request.stream():
        total += len(chunk)
        if total > ANALYZE_MAX_BODY_BYTES:
            return _error_json(_BODY_TOO_LARGE_MESSAGE, 413)
        chunks.append(chunk)
    # Cache the body exactly like Starlette's own Request.body() would (it
    # checks `hasattr(self, "_body")` before ever touching the stream again)
    # so _resolve_code_param's later `request.json()` call reuses these
    # already-read bytes instead of trying to re-read a consumed stream.
    request._body = b"".join(chunks)  # noqa: SLF001 - see docstring above
    return None


async def _unhandled_exception(request: Request, exc: Exception) -> Response:
    """App-level last line of defence: whatever a route handler's own
    try/except missed still comes out as clean Vietnamese JSON, never a
    bare traceback (see this module's own docstring and the task's
    requirement 6). Lỗi 2 fix: the response body is now the one generic
    sentence from `_generic_error_message` plus an incident code -- never
    `str(exc)` -- while the full exception (type, message, traceback) goes
    to the server log via `_log_incident`, tagged with that same code.
    """
    incident_code = _log_incident(f"{request.method} {request.url.path}", exc)
    return _error_json(_generic_error_message(incident_code), 500)


def _with_detail_link(
    result: Dict[str, Any], detail_url: Optional[str]
) -> Dict[str, Any]:
    """Return a COPY of `result` with the "xem chi tiết trực quan" line
    (task's Việc 4) appended to `text` and folded into a freshly-rendered
    `report_markdown` -- WITHOUT ever mutating `result` in place.

    Why a copy is mandatory here, not an optimization: `result` can be the
    EXACT SAME dict object `WebDataService`'s own TTL cache is holding onto
    (a cache HIT returns the identical object every time, see
    `WebDataService.analyze`'s own comment on this), and `detail_url` is a
    property of THIS ONE request -- whether it came from a logged-in user's
    session (pointing at that user's own `/<userref>_<code>` link) or not
    (falling back to the plain `/bot/<code>`) -- not a property of the
    underlying analysis. Two different callers hitting the cache for the
    same `code` within its TTL window must each see the correct link for
    THEIR OWN request:
      * Mutating `result["text"]` in place (e.g. `.append(...)`) would grow
        the SHARED cached list by one more line on every single request
        that lands on the cache, compounding without bound.
      * Reusing a `report_markdown` string rendered for one caller's own
        `userref` link would leak that link into every other caller's
        response for the same code until the cache entry expires.
    Building a shallow copy -- new top-level dict, new `text` list, and one
    fresh Markdown render -- costs a few string operations per request;
    the whole point of the TTL cache is to skip the OKX-network/CPU-heavy
    part of `analyze()`, not this.

    `detail_url=None` means the on/off rule this line shares with
    `report_url` (`report_url_is_usable()`, see data.py) says not to show a
    link this time -- `result` is returned completely unchanged (not even
    copied), so this is a true no-op for the common case where the report
    base URL is not configured to a public host.
    """
    if not detail_url:
        return result
    updated = dict(result)
    text = list(updated.get("text") or [])
    text.append(detail_link_line(detail_url))
    updated["text"] = text
    # Rendered from the ORIGINAL `result` (whose `text` has NOT gained the
    # link line above) plus `detail_url` as its own parameter -- so the
    # link appears exactly once in the rendered Markdown (as the final line
    # `build_report_markdown` itself appends after the disclaimer), never a
    # second time inside the "## Vì sao" section that same function already
    # builds FROM `result["text"]`.
    updated["report_markdown"] = build_report_markdown(result, detail_url=detail_url)
    # Việc 4 fix: keep the JSON `report_url` key in lockstep with the very
    # link line just appended to `text`/`report_markdown` above -- both must
    # point at the SAME URL for the SAME response, never two different ones.
    #
    # WHY THIS WAS WRONG BEFORE: `result["report_url"]` is set exactly once,
    # inside `WebDataService.analyze()` (data.py), unconditionally to the
    # plain `build_report_url(code)` (i.e. always `/bot/<code>`) -- and that
    # dict is then cached and REUSED byte-for-byte across every caller who
    # hits the TTL cache for the same `code` (see analyze()'s own docstring).
    # It therefore cannot know, and must not be made to know, about any one
    # caller's session -- exactly like `report_markdown`'s ORIGINAL value a
    # few lines above, which is why this function already exists to patch a
    # PER-REQUEST copy instead of mutating the shared cache entry. `caller`
    # (api_analyze) always derives `detail_url` as EITHER the user's own
    # obscure `/<userref>_<code>` link (session present) OR
    # `build_report_url(code)` itself (no session) -- so when there is no
    # session, this assignment is a same-value overwrite (harmless); when
    # there IS one, it corrects `report_url` to match the obscure link this
    # response already advertises in `text`/`report_markdown`, instead of
    # leaking the guessable `/bot/<code>` link right next to it.
    #
    # Only ever touches a key that was ALREADY present -- never ADDS
    # `report_url` when `report_url_is_usable()` said no (see analyze()'s own
    # comment on why the key is omitted entirely, not set to `None`, in that
    # case): `detail_url` is `None` whenever `report_url_is_usable()` is
    # False (see api_analyze), and the `if not detail_url` guard at the top
    # of this function already returns early for that case -- so this line
    # only ever runs once `report_url_is_usable()` already said yes, and
    # `result["report_url"]` is therefore guaranteed to already be present.
    if "report_url" in updated:
        updated["report_url"] = detail_url
    return updated


def _without_closed_trade_series(result: Dict[str, Any]) -> Dict[str, Any]:
    """Return a COPY of `result` with `evidence.closed_trade_series`
    removed -- the per-trade chart data `WebDataService.analyze()` always
    computes and attaches (see data.py's `_full_result`/
    `_closed_trade_series_from_bot_result`) so its own TTL cache never has
    to key on anything beyond `code`, but which the OKX AI Marketplace's
    `/api/analyze` JSON response must never include: the project owner's
    own explicit ruling is that this response stays a compact
    report+recommendation, not a raw dump of a bot's whole trade history
    (potentially hundreds of rows).

    Mandatory-copy, same reasoning as `_with_detail_link` right below --
    `result` can be the EXACT SAME dict object `WebDataService`'s TTL cache
    is holding onto (a cache hit returns that identical object every time),
    and `GET /bot/<code>` / `GET /<userref>_<code>` later call `service.analyze(code)`
    again for the SAME cached entry expecting the FULL series to still be
    there so their equity-curve chart can render. Deleting the key in place
    here would permanently blind every later HTML view of this bot to its
    own chart, for as long as the cache entry lives, the instant anyone
    called the JSON API for it first. So this always builds a fresh
    top-level dict, and -- only when `evidence` actually carries the key --
    a fresh `evidence` dict too, rather than ever mutating either the
    original `result` or its nested `evidence` dict.

    A LIMITED/NOT_FOUND result (whose `evidence` shape never has this key
    at all -- see `_full_result` vs `_limited_fallback_result`/
    `_not_found_result`/`assess_from_error`) is returned as a fresh
    top-level copy too, for the same "never hand back the cached object
    itself" guarantee, just with `evidence` left exactly as it was (nothing
    to strip).
    """
    updated = dict(result)
    evidence = updated.get("evidence")
    if isinstance(evidence, dict) and "closed_trade_series" in evidence:
        updated["evidence"] = {
            key: value
            for key, value in evidence.items()
            if key != "closed_trade_series"
        }
    return updated


def create_app(
    *,
    dashboard_path: Optional[Path] = None,
    data_service: Optional[WebDataService] = None,
    rate_limiter: Optional[PerIpRateLimiter] = None,
    admin_rate_limiter: Optional[PerIpRateLimiter] = None,
    ref_registry: Optional[access.RecentCodeRegistry] = None,
    users_root: Optional[Path] = None,
) -> Starlette:
    """Build the Starlette app. Every dependency is injectable so tests can
    swap in a `WebDataService` wired to fakes instead of real OKX/disk
    access (see Agent/test/test_web_app.py). `users_root` is the same kind
    of injectable default as `dashboard_path` above -- it overrides
    `Agent/backend/web/identity.py`'s `DEFAULT_USERS_ROOT` so tests never
    read/write this project's real `data/users/` directory.
    """
    service = data_service or WebDataService()
    limiter = rate_limiter or PerIpRateLimiter(
        max_requests=ANALYZE_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=ANALYZE_RATE_LIMIT_WINDOW_SECONDS,
    )
    # A SEPARATE PerIpRateLimiter instance, not a second bucket inside the
    # same one -- see ADMIN_RATE_LIMIT_MAX_REQUESTS's own comment for why an
    # admin caller must have an independent budget from ordinary callers.
    admin_limiter = admin_rate_limiter or PerIpRateLimiter(
        max_requests=ADMIN_RATE_LIMIT_MAX_REQUESTS,
        window_seconds=ADMIN_RATE_LIMIT_WINDOW_SECONDS,
    )
    dash_path = (
        Path(dashboard_path) if dashboard_path is not None else DEFAULT_DASHBOARD_PATH
    )
    users_dir = (
        Path(users_root) if users_root is not None else identity.DEFAULT_USERS_ROOT
    )
    # The "sổ tra cứu nhỏ" GET /admin's own "phiên gần đây" section reads --
    # see access.RecentCodeRegistry's own docstring for exactly what it is
    # and the restart-loses-entries trade-off it documents. One per app
    # instance (like `okx_health_cache` below), not a module-level global,
    # so each `create_app()` call -- each test included -- gets an
    # independent registry instead of leaking codes across app instances.
    refs = ref_registry or access.RecentCodeRegistry()
    # One-time "this endpoint has no access-token protection" log line --
    # see access.warn_once_if_unprotected's own docstring for why this is
    # the right place to call it (effectively "at startup" for a real
    # deployment) and why it never fires more than once per process even
    # though tests call create_app() many times.
    access.warn_once_if_unprotected()

    async def index(request: Request) -> Response:
        try:
            return _dashboard_response(dash_path)
        except Exception as exc:  # noqa: BLE001 - never let the index route 500-traceback
            incident_code = _log_incident("GET / (dashboard)", exc)
            return _error_json(_generic_error_message(incident_code), 500)

    async def api_bots(request: Request) -> Response:
        try:
            bots = await run_in_threadpool(service.list_bots)
        except Exception as exc:  # noqa: BLE001 - disk I/O; never bubble a traceback
            incident_code = _log_incident("GET /api/bots", exc)
            return _error_json(_generic_error_message(incident_code), 500)
        return JSONResponse({"bots": bots, "count": len(bots)})

    async def api_markets(request: Request) -> Response:
        try:
            markets = await run_in_threadpool(service.list_markets)
        except Exception as exc:  # noqa: BLE001
            incident_code = _log_incident("GET /api/markets", exc)
            return _error_json(_generic_error_message(incident_code), 500)
        return JSONResponse({"markets": markets, "count": len(markets)})

    async def api_leaderboard(request: Request) -> Response:
        try:
            rows = await run_in_threadpool(service.leaderboard)
        except Exception as exc:  # noqa: BLE001 - OKX call; never bubble a traceback
            incident_code = _log_incident("GET /api/leaderboard", exc)
            return _error_json(_generic_error_message(incident_code), 502)
        return JSONResponse({"leaderboard": rows, "count": len(rows)})

    async def api_lookup(request: Request) -> Response:
        # No per-IP rate limit here (unlike api_analyze below): lookup() is
        # deliberately cheap (at most 3 OKX requests, no scoring engine --
        # see WebDataService.lookup's own docstring) and is meant to be
        # called on every keystroke-driven search, which the tight
        # ANALYZE_RATE_LIMIT_* budget above would make unusable for.
        try:
            body: Any = await request.json()
        except Exception:
            body = None
        code = body.get("code") if isinstance(body, dict) else None
        try:
            result: Dict[str, Any] = await run_in_threadpool(service.lookup, code)
        except InvalidCodeError as exc:
            return _error_json(str(exc), 400)
        except Exception as exc:  # noqa: BLE001 - last line of defence, see module docstring
            incident_code = _log_incident("POST /api/lookup", exc)
            return _error_json(_generic_error_message(incident_code), 500)
        return JSONResponse(result)

    async def api_analyze(request: Request) -> Response:
        # 1) Body-size guard FIRST, before anything reads/parses the body --
        # see ANALYZE_MAX_BODY_BYTES/_enforce_max_body_size above for why
        # this now has to be explicit instead of an accidental side effect
        # of the rate limiter running first.
        oversized_response = await _enforce_max_body_size(request)
        if oversized_response is not None:
            return oversized_response

        # 1.5) Access-token gate -- see access.py's module docstring for
        # what this token proves (a self-issued key, never an OKX-buyer
        # identity -- a fee=0 Marketplace endpoint like this one is never
        # handed one) and for why it exists at all (keeping a stranger who
        # never received a token from calling this CPU/OKX-quota-expensive
        # endpoint for free). Placed here, before code resolution/format
        # validation/the rate limiter, so an unauthenticated caller is
        # rejected before this route does ANY other work -- and, like every
        # other rejection branch above the limiter in this handler, must
        # NEVER itself consume ANALYZE_RATE_LIMIT_MAX_REQUESTS: a stranger
        # hammering this endpoint with no/a wrong token must never be able
        # to exhaust a legitimate, correctly-authenticated caller's own
        # quota just because they happen to share a source IP (NAT,
        # corporate proxy, ...).
        #
        # `access.is_protected()` re-reads NORABT_ACCESS_TOKENS on every
        # call (same "read live, not once at import time" pattern as
        # `report_base_url()` in data.py), so flipping that env var takes
        # effect on the next request with no separate flag to keep in sync.
        # `token` itself is only ever used by the gate check right below --
        # the detail-link section further down derives its link from a
        # SESSION cookie instead (see access.read_session), entirely
        # independent of whether an ordinary access token was presented.
        token: Optional[str] = None
        is_admin = False
        # Admin check runs BEFORE, and independently of, the ordinary
        # NORABT_ACCESS_TOKENS gate below -- see access.py's own "Admin
        # role" section docstring: the whole point is a key that gets
        # through the gate REGARDLESS of whether ordinary-token protection
        # is on. `is_admin_configured()` is the same cheap short-circuit
        # `is_protected()` already provides for the ordinary gate: when
        # NORABT_ADMIN_TOKEN_SHA256 is unset (the default), this branch
        # never even resolves a token from the request, so an unconfigured
        # admin role costs this route nothing and changes nothing.
        if access.is_admin_configured():
            admin_candidate = await _resolve_access_token(request)
            if admin_candidate and access.verify_admin_token(admin_candidate):
                is_admin = True
                # Deliberately NOT stored in `token`: `token` only feeds the
                # ordinary NORABT_ACCESS_TOKENS gate below, never the
                # detail-link section further down -- that section derives
                # its link purely from a SESSION cookie now (see
                # access.read_session), which an admin API key is not.
                # Leaving `token` as `None` here means the ordinary gate
                # below is simply skipped for this already-authenticated
                # admin request (see the `if not is_admin and
                # access.is_protected()` guard right below), same as before
                # this comment was last touched.
        if not is_admin and access.is_protected():
            token = await _resolve_access_token(request)
            if not token:
                return _missing_token_response()
            if access.verify_token(token) is None:
                return _invalid_token_response()

        # 2) Resolve `code` from query string + (size-bounded) body.
        code, conflict_message = await _resolve_code_param(request)
        if conflict_message is not None:
            # Two synonym parameter names disagreed (Việc 2) -- a value WAS
            # supplied, just an ambiguous one, so this is Việc 4's branch,
            # never the missing-parameter one (see _resolve_code_param's own
            # docstring for why silently picking one would be wrong here).
            # Lỗi 1: this is also a branch that must NEVER cost rate-limit
            # quota -- see the comment on the limiter call further below.
            return _invalid_param_response(conflict_message)
        # Missing/null/wrong-type/blank `code` gets the structured 400 above
        # (Việc 4, "missing" branch) -- also free of charge against the rate
        # limiter, same reasoning as the conflict branch just above.
        if not isinstance(code, str) or not code.strip():
            return _missing_code_response()

        # 3) Format-validate BEFORE the rate limiter (Lỗi 1's actual fix).
        #
        # This is the exact same check service.analyze() runs internally
        # (see data.py's validate_unique_code), just performed here first so
        # a badly-formatted code is rejected at zero quota cost too, instead
        # of only after already being charged against the limiter below.
        #
        # Why the ordering matters: the OKX a2mcp-probe CLI's own protocol
        # always opens with an EMPTY probe request (no `code` at all) purely
        # to discover that a parameter is required, then asks a human for
        # the bot code and probes again -- possibly more than once if they
        # mistype it, and potentially once more on top of that if the CLI's
        # own GET<->POST 405 fallback kicks in. None of those round trips
        # spend a single second of CPU or a single OKX request, so none of
        # them may be charged against ANALYZE_RATE_LIMIT_MAX_REQUESTS, which
        # exists purely to protect the genuinely expensive service.analyze()
        # call further below. Worse, a 429 here is a DEAD END for that CLI,
        # not a "wait and retry" signal -- it treats a rate limit as a
        # terminal failure -- so charging quota for a probe or a mistyped
        # code would cut the buyer out of the flow entirely instead of
        # letting the CLI simply reprompt them for the right code.
        try:
            validate_unique_code(code)
        except InvalidCodeError as exc:
            return _invalid_param_response(str(exc))

        # 4) Only NOW does this request touch the rate limiter -- everything
        # above this line is guaranteed to be a request that is about to
        # actually call the expensive service.analyze() below.
        #
        # An admin-authenticated request uses `admin_limiter` -- a SEPARATE
        # PerIpRateLimiter instance with its own, wider budget (see
        # ADMIN_RATE_LIMIT_MAX_REQUESTS above) -- instead of `limiter`, never
        # both: this is a different, wider quota, not an additional one on
        # top of the ordinary one.
        client_host = resolve_client_ip(request)
        active_limiter = admin_limiter if is_admin else limiter
        if not active_limiter.allow(client_host):
            message = (
                "Khoá admin gọi /api/analyze quá nhanh. Hạn mức admin rộng "
                "hơn khoá thường nhưng KHÔNG miễn hoàn toàn -- mỗi lần chấm "
                "điểm vẫn tốn vài giây CPU và nhiều lượt gọi OKX -- vui lòng "
                "đợi một chút rồi thử lại."
                if is_admin
                else "Bạn gọi /api/analyze quá nhanh. Mỗi lần chấm điểm tốn vài giây "
                "CPU và nhiều lượt gọi OKX, nên hệ thống giới hạn số lần gọi "
                "theo IP -- vui lòng đợi một chút rồi thử lại."
            )
            return _error_json(message, 429)
        try:
            result: Dict[str, Any] = await run_in_threadpool(service.analyze, code)
        except InvalidCodeError as exc:
            # Safety net only: validate_unique_code above already rejects a
            # badly-formatted code the exact same way service.analyze()
            # itself would, so this should be unreachable in practice -- kept
            # in case the two checks ever drift apart from each other.
            return _invalid_param_response(str(exc))
        except Exception as exc:  # noqa: BLE001 - last line of defence, see module docstring
            incident_code = _log_incident("POST /api/analyze", exc)
            return _error_json(_generic_error_message(incident_code), 500)

        # Lỗi 2 fix: strip the chart-only evidence.closed_trade_series field
        # from the JSON this route hands back, WITHOUT mutating the shared
        # analyze_cache entry `result` may be -- see
        # _without_closed_trade_series's own docstring. Done up front, before
        # _with_detail_link/admin handling below, so every later step in
        # this handler already works off a private copy, never the cached
        # object itself.
        result = _without_closed_trade_series(result)

        # `code` was just scored live -- remember it for GET /admin's
        # "phiên gần đây" section regardless of who called this or how (see
        # access.RecentCodeRegistry's own docstring); this is a plain
        # listing convenience, independent of the session/link logic below.
        refs.remember(code)

        # Việc 4: exactly one extra "xem chi tiết trực quan" line, appended
        # to BOTH `report_markdown` and `text` -- gated by the EXACT SAME
        # rule `report_url` itself already uses (`report_url_is_usable()`,
        # reused rather than reimplemented, per the task's own instruction
        # that a second copy of that rule would only risk drifting from the
        # first). The link shape depends on whether THIS request carries a
        # valid, logged-in USER session cookie (see POST /api/session,
        # access.read_session) -- an identity orthogonal to the ordinary/
        # admin access-token gate above:
        #   * a real user session -> the obscure, per-user
        #     `/<userref>_<code>` link (never the guessable `/bot/<code>`,
        #     so a response handed to a logged-in user doesn't itself hand
        #     out an unauthenticated backdoor to the same content) -- AND
        #     this exact (userref, code) pair is recorded into that user's
        #     profile (see identity.record_analysis) so the link this
        #     response just handed out actually resolves afterwards.
        #   * no session (this is the common case for the OKX Marketplace's
        #     own machine-to-machine callers, and for an admin-authenticated
        #     request, which already has full access via /bot/<code>) ->
        #     the plain `/bot/<code>` link, exactly as before this feature
        #     existed.
        session = access.read_session(request.cookies.get(access.SESSION_COOKIE_NAME))
        session_user_ref = (
            session.get("user_ref") if session and not session.get("is_admin") else None
        )
        if session_user_ref:
            identity.record_analysis(
                session_user_ref,
                code,
                result.get("name"),
                result.get("verdict"),
                users_root=users_dir,
            )
        detail_url: Optional[str] = None
        if report_url_is_usable():
            detail_url = (
                f"{report_base_url()}/{session_user_ref}_{code}"
                if session_user_ref
                else build_report_url(code)
            )
        result = _with_detail_link(result, detail_url)

        # `access_level: "admin"` is the one visible signal a caller gets
        # that their admin key actually worked (task's own requirement) --
        # ONLY added for an admin-authenticated request, never for an
        # ordinary token or open-mode caller, so LEGACY_ANALYZE_KEYS and
        # every existing consumer of this response keep seeing exactly the
        # keys they always have (see Agent/test/test_web_app.py's own
        # LEGACY_ANALYZE_KEYS set). Built as a copy here rather than
        # mutating `result` in place, for the exact same cache-sharing
        # reason `_with_detail_link` above already documents: `result` can
        # still be the identical dict object WebDataService's TTL cache
        # holds (when `detail_url` was falsy, `_with_detail_link` returned
        # that object unchanged rather than copying it), and a different,
        # non-admin caller must never see this key leak into THEIR response
        # for the same cached code.
        if is_admin:
            result = dict(result)
            result["access_level"] = "admin"
        return JSONResponse(result)

    async def _bot_report_response(
        code: str, client_host: str, *, is_admin: bool = False
    ) -> Response:
        """Shared body for GET /bot/<code> and GET /<userref>_<code> below --
        both ultimately render the exact same HTML report for a `code` that
        has already been resolved/validated by their respective callers,
        just reached through two different URLs: a guessable one
        (`bot_report`), and the obscure per-user one (`user_report`) that
        `/api/analyze`'s own `detail_url` above actually hands out to a
        logged-in user's session.

        Deliberately does NOT reuse Agent/web/dashboard.html: that page is a
        client-side SPA that renders an embedded, pre-baked list of bots and
        has no logic to read a bot code out of its own URL (adding that is
        out of scope here -- this task may only touch this module and
        data.py, not the dashboard HTML/JS).

        The actual page is built by `render_bot_report_html` (see
        `Agent/backend/web/report_page.py`), NOT by re-rendering
        `report_markdown` inside a `<pre>` -- that was this route's
        behaviour before that module existed, and is now gone. There are
        two separate outputs for the same `result` dict, for two separate
        audiences, and both have to do their own escaping of untrusted
        OKX-sourced text (a bot's `nick_name` above all):
          * `result["report_markdown"]` (see data.py's
            `build_report_markdown`) -- a Markdown string embedded in the
            `/api/analyze` JSON body, meant for a machine/CLI to read or
            paste elsewhere.
          * `render_bot_report_html(result)` -- a full HTML document meant
            for a human's browser, with its own inline SVG charts and
            collapsible sections, escaping every untrusted value itself via
            `html.escape(..., quote=True)` (see report_page.py's module
            docstring).
        Neither derives its escaping from the other, so a change to how one
        of them escapes/handles a field is NOT automatically safe for the
        other -- whoever edits one must check the other still holds up
        (report_page.py has its own extensive test suite in
        test_report_page.py; this module's own tests below cover the route
        wiring, not the page internals).

        `is_admin` only ever changes whether `render_bot_report_html` adds
        its ADMIN navigation strip -- see that function's own docstring for
        the "navigation only, never the analysis" rule this route relies on
        without re-checking it itself.
        """
        # Same shared budget as POST /api/analyze -- this route runs the
        # exact same expensive, OKX-touching scoring pipeline (see
        # WebDataService.analyze), just reached by a GET instead of a POST.
        if not limiter.allow(client_host):
            return HTMLResponse(
                _report_error_html(
                    "Bạn xem trang báo cáo này quá nhanh. Trang này chấm điểm "
                    "bot trực tiếp (tốn CPU + hạn mức gọi OKX dùng chung), "
                    "nên dùng chung giới hạn tần suất với /api/analyze -- "
                    "vui lòng đợi một chút rồi thử lại."
                ),
                status_code=429,
            )

        try:
            result: Dict[str, Any] = await run_in_threadpool(service.analyze, code)
        except Exception as exc:  # noqa: BLE001 - last line of defence, see module docstring
            incident_code = _log_incident("GET /bot or /<user_ref>_<code> report", exc)
            return HTMLResponse(
                _report_error_html(_generic_error_message(incident_code)),
                status_code=500,
            )
        return HTMLResponse(render_bot_report_html(result, is_admin=is_admin))

    async def bot_report(request: Request) -> Response:
        """GET /bot/<code> -- the page `report_url` in /api/analyze's own
        response always points at (see data.py's build_report_url).

        Deliberately left UNCHANGED/ungated by the access-token gate above
        (task's own explicit instruction: "Giữ nguyên tuyến /bot/{code} như
        cũ"), even once NORABT_ACCESS_TOKENS is configured -- this route
        stays reachable by anyone who can guess or already has a `code`,
        same as before this task. `/<userref>_<code>` below (reached
        through `detail_url` once a caller is logged in) exists precisely
        so `/api/analyze` never has to hand a logged-in user a link to this
        still-open route as its "recommended" one.
        """
        raw_code = request.path_params.get("code")
        try:
            code = validate_unique_code(raw_code)
        except InvalidCodeError as exc:
            return HTMLResponse(_report_error_html(str(exc)), status_code=400)
        client_host = resolve_client_ip(request)
        is_admin = await _is_admin_request(request)
        return await _bot_report_response(code, client_host, is_admin=is_admin)

    def _generic_report_404() -> HTMLResponse:
        """The one, deliberately unhelpful 404 body shared by `user_report`
        below and `admin_page` further down -- see either call site's own
        comment for why NEVER distinguishing "wrong format" from "not on
        record" from "admin role not configured" is the actual point, not
        an oversight: a distinctly-worded 404 for any one of those cases
        would itself be a signal to a stranger probing this path that they
        are close, which a single generic body never gives away.
        """
        return HTMLResponse(
            _report_error_html("Không tìm thấy trang báo cáo này."), status_code=404
        )

    async def user_report(request: Request) -> Response:
        """GET /<userref>_<code> -- the obscure-path counterpart to GET
        /bot/<code> above, and the link `/api/analyze` actually hands out
        (see `detail_url` in `api_analyze`) to a caller with a logged-in
        USER session. Replaces the former token-derived `/r/<ref>` route
        entirely (see this module's own top-of-file docstring) -- wallet-
        address sessions (`Agent/backend/web/identity.py`) are now the one
        and only mechanism behind this "obscure per-caller report link"
        feature.

        WHY A PATH SEGMENT, NOT A SUBDOMAIN (e.g.
        `<code>.<userref>.agent.expsolution.io`): a hostname leaks out of
        the encrypted tunnel TWICE before a single application byte is even
        sent -- once in the TLS ClientHello's SNI extension, which travels
        in the clear on the wire even under TLS 1.3 absent ECH (which this
        deployment does not run), and again in every DNS query needed to
        resolve it, visible to the resolver, every network on the path, and
        -- via passive DNS logging -- more or less permanently afterwards.
        A URL PATH, by contrast, is carried only inside the HTTP request
        line, which is already inside that encrypted tunnel by the time it
        is sent. So putting the identifier in the path is MORE private than
        a subdomain, not less, despite a subdomain looking more "hidden" at
        a glance. Separately, and just as decisive on its own: a two-label
        subdomain shape like `<code>.<userref>.agent.expsolution.io` cannot
        even get a certificate -- Let's Encrypt only issues wildcards one
        label deep (`*.agent.expsolution.io`), never `*.*.agent.expsolution.io`.

        Starlette's own route pattern (`/{user_ref}_{code}`, see the routes
        list below) matches ANY single path segment containing at least one
        `_` -- it does not, and cannot, enforce `user_ref`'s exact
        length/alphabet or `code`'s own shape by itself (see
        `USER_REF_RE`/`validate_unique_code`), so both are re-validated
        here, strictly, BEFORE either is used for anything -- a `user_ref`
        that fails that check is never even passed to
        `identity.load_profile` (which validates again internally, but the
        task's own instruction is to reject early, not merely defensively).

        Access rule, in order: an admin caller (token OR admin session, see
        `_is_admin_request`) always gets in. Otherwise, this exact
        (user_ref, code) pair must be on record in that user's own profile
        (`identity.has_analyzed` -- i.e. a session for THIS user_ref already
        analyzed THIS code at least once through /api/analyze). Every other
        case -- bad format, no such profile, profile exists but never
        analyzed this code -- is the exact same generic 404
        (`_generic_report_404`), never distinguishing which, for the same
        probing-resistance reason the former `/r/<ref>` route documented.
        """
        raw_user_ref = request.path_params.get("user_ref") or ""
        raw_code = request.path_params.get("code") or ""
        is_admin = await _is_admin_request(request)
        if not identity.USER_REF_RE.match(raw_user_ref):
            return _generic_report_404()
        try:
            code = validate_unique_code(raw_code)
        except InvalidCodeError:
            return _generic_report_404()
        if not is_admin:
            profile = identity.load_profile(raw_user_ref, users_root=users_dir)
            if profile is None or not identity.has_analyzed(profile, code):
                return _generic_report_404()
        client_host = resolve_client_ip(request)
        return await _bot_report_response(code, client_host, is_admin=is_admin)

    # Short-TTL cache backing GET /admin's own disk read (see
    # ADMIN_BOTS_CACHE_TTL_SECONDS's own comment). A plain dict, not a class,
    # for the same reason `okx_health_cache` below is one: one per
    # `create_app()` call (so tests never leak state across app instances),
    # holding just enough to answer "is this still fresh".
    admin_bots_cache: Dict[str, Any] = {"loaded_at": None, "bots": []}

    async def _cached_scored_bots() -> List[Dict[str, Any]]:
        """`service.list_bots()` (a full walk of `data/assessment/**`, see
        that method's own docstring), reused for
        `ADMIN_BOTS_CACHE_TTL_SECONDS` before reading again. Runs the actual
        disk I/O through `run_in_threadpool` (never blocking the event loop
        the whole app shares) EITHER way -- on a cache hit this still costs
        nothing but a dict lookup, but the threadpool hop only happens on a
        miss, which is the branch that could actually block.
        """
        now = time.monotonic()
        loaded_at = admin_bots_cache["loaded_at"]
        if loaded_at is not None and (now - loaded_at) < ADMIN_BOTS_CACHE_TTL_SECONDS:
            return admin_bots_cache["bots"]
        bots = await run_in_threadpool(service.list_bots)
        admin_bots_cache["loaded_at"] = now
        admin_bots_cache["bots"] = bots
        return bots

    async def admin_page(request: Request) -> Response:
        """GET /admin -- see this module's own docstring for the route-level
        contract. Two independent reasons this can 404, both folded into the
        SAME response (never 401/403, and never a response that differs
        between them in any observable way -- see this function's own
        comments below for why that indistinguishability is the entire
        point): the admin role is not configured at all
        (`NORABT_ADMIN_TOKEN_SHA256` unset, the default), or it IS configured
        but this request's token is missing/wrong. Reuses the exact same
        generic 404 body `user_report` already answers an unknown/
        unauthorized (user_ref, code) pair with (see `_generic_report_404`),
        rather than inventing a differently-worded one here -- a
        distinctly-worded 404 for this ONE path would itself be a signal
        that this path is special, defeating the "cannot tell this route
        exists" goal just as surely as a 401/403 would.
        """
        if not await _is_admin_request(request):
            return _generic_report_404()
        try:
            bots = await _cached_scored_bots()
        except Exception as exc:  # noqa: BLE001 - disk I/O; never bubble a traceback
            incident_code = _log_incident("GET /admin", exc)
            return HTMLResponse(
                _report_error_html(_generic_error_message(incident_code)),
                status_code=500,
            )
        sort = request.query_params.get("sort") or ""
        html_out = render_admin_page_html(
            bots,
            refs.codes(),
            sort=sort,
            current_query=dict(request.query_params),
        )
        return HTMLResponse(html_out)

    # Process start time, captured once per app instance (matches module-level
    # `app = create_app()` below, so it tracks the actual server process
    # uptime, not the uptime of a request handler).
    started_at = time.monotonic()
    # Mutable holder for the cached OKX reachability result. A plain dict
    # (rather than a module-level global) so each create_app() call -- e.g.
    # each test -- gets its own independent cache instead of leaking state
    # across app instances.
    okx_health_cache: Dict[str, Any] = {"checked_at": None, "reachable": None}

    async def healthz(request: Request) -> Response:
        """Liveness probe for an orchestrator (see docker-compose's
        `healthcheck:` block) and for a human at 2am deciding whether to
        restart the container.

        Deliberately reports two independent facts rather than one boolean:

          * `bots_on_disk`: can this process actually read its data mount?
            A `None` here (the read itself raised) means something is
            fundamentally broken -- wrong mount, permissions, corrupted
            volume -- and is the one condition this route treats as
            "degraded", because restarting the container/checking the mount
            is a sensible reaction to it.
          * `okx_public_reachable`: is the *external* OKX API reachable right
            now? This is informational only and never flips `status` --
            OKX rate-limiting or blocking this server's IP is a real
            operational problem (see the README's troubleshooting table),
            but restarting this container cannot fix it, so a healthcheck
            that restarted on every OKX hiccup would just create restart
            loops for a condition restarting cannot resolve.

        Never raises: like every other route in this module, an unexpected
        failure here still comes back as clean JSON (see this module's own
        docstring), which matters especially for a route whose entire job is
        to be a reliable target for automated polling.
        """
        try:
            bots_on_disk: Optional[int] = await run_in_threadpool(
                lambda: len(service.list_bots())
            )
        except Exception:  # noqa: BLE001 - disk I/O; never bubble a traceback
            bots_on_disk = None

        now = time.monotonic()
        checked_at = okx_health_cache["checked_at"]
        if checked_at is None or (now - checked_at) >= HEALTHZ_OKX_CACHE_TTL_SECONDS:
            try:
                # Reaches into WebDataService's own (private) OkxClient
                # instead of building a second one: this task's scope only
                # allows adding a route here, not a new public accessor on
                # WebDataService, and reusing the existing client keeps this
                # check injectable in tests the same way every OKX-touching
                # route above already is (via create_app(data_service=...)).
                # public_get() never sends auth headers (see OkxClient's own
                # docstring), so this can never leak or depend on credentials.
                await run_in_threadpool(
                    service._client.public_get, HEALTHZ_OKX_CHECK_PATH
                )
                okx_reachable = True
            except Exception:  # noqa: BLE001 - any failure just means "not reachable"
                okx_reachable = False
            okx_health_cache["checked_at"] = now
            okx_health_cache["reachable"] = okx_reachable

        return JSONResponse(
            {
                "status": "ok" if bots_on_disk is not None else "degraded",
                "uptime_seconds": round(now - started_at, 1),
                "bots_on_disk": bots_on_disk,
                "okx_public_reachable": okx_health_cache["reachable"],
            }
        )

    def _session_cookie_kwargs() -> Dict[str, Any]:
        """Shared `Set-Cookie` flags for the session cookie POST
        /api/session issues: `HttpOnly` (never readable by page JS -- this
        cookie carries no secret an XSS payload would gain from reading it
        anyway, per `create_session_cookie`'s own docstring, but there is no
        reason to allow it), `SameSite=Lax` (sent on ordinary top-level
        navigation, withheld from cross-site embeds/POSTs -- the standard,
        least-surprising default for a same-site session cookie with no
        cross-site use case), and `Secure` exactly when this deployment's
        own public report base URL (`report_base_url()`) is `https`. That
        last part is READ LIVE, not hardcoded true: a dev/test box with no
        public HTTPS endpoint configured must still be able to log in over
        plain http -- browsers silently DROP a `Secure` cookie sent over
        http, which would make login completely unusable there -- while a
        real deployment (always `https`, per Agent/.env.example's own
        guidance) gets the stronger flag automatically, with no separate
        env var to keep in sync with `NORABT_WEB_REPORT_BASE_URL`.
        """
        return {
            "httponly": True,
            "samesite": "lax",
            "secure": urlsplit(report_base_url()).scheme == "https",
            "path": "/",
        }

    def _set_session_cookie(response: Response, cookie_value: str) -> None:
        response.set_cookie(
            access.SESSION_COOKIE_NAME,
            cookie_value,
            max_age=int(access.SESSION_TTL_SECONDS),
            **_session_cookie_kwargs(),
        )

    async def api_session(request: Request) -> Response:
        """POST /api/session -- see this module's own top-of-file docstring
        for the full route contract. `{"identity": "..."}`'s value is
        checked against the admin key FIRST, then as a wallet address --
        never the other way around, and never both accepted at once, so a
        value that happens to satisfy neither gets exactly one, unambiguous
        400 explaining both accepted shapes (task's own explicit
        requirement) rather than two different error messages depending on
        which check ran first.
        """
        try:
            body: Any = await request.json()
        except Exception:
            body = None
        raw_identity = body.get("identity") if isinstance(body, dict) else None
        if not isinstance(raw_identity, str) or not raw_identity.strip():
            return _error_json(
                "Thiếu trường 'identity' trong body JSON -- gửi khoá admin, "
                "hoặc địa chỉ ví dạng '0x' + 40 ký tự hex. "
                + identity.WALLET_DISCLAIMER_VI,
                400,
            )
        candidate = raw_identity.strip()

        if access.is_admin_configured() and access.verify_admin_token(candidate):
            response: Response = JSONResponse({"status": "OK", "role": "admin"})
            _set_session_cookie(response, access.create_session_cookie(is_admin=True))
            return response

        try:
            wallet_address = identity.normalize_wallet_address(candidate)
        except identity.InvalidWalletAddressError:
            return _error_json(
                "Giá trị 'identity' không khớp khoá admin, và cũng không "
                "phải địa chỉ ví hợp lệ -- cần đúng '0x' theo sau bởi 40 ký "
                "tự hex, ví dụ "
                "'0x1234567890abcdef1234567890abcdef12345678'. "
                + identity.WALLET_DISCLAIMER_VI,
                400,
            )
        try:
            profile = identity.get_or_create_profile(
                wallet_address, users_root=users_dir
            )
        except identity.ProfileStoreError as exc:
            # Lỗi 1/Lỗi 2 fix: a read-only/full/wrong-permission
            # `data/users` mount (see Agent/deploy/docker-compose.yml's own
            # mount comment) must never surface as a raw OSError string to
            # an internet-facing caller. This is a MORE SPECIFIC message
            # than the generic `_generic_error_message` every other
            # unanticipated-error branch in this module falls back to,
            # because an operator staring at the log line this writes
            # (tagged with the same incident code) benefits from knowing
            # immediately "this was a profile-store write failure", not
            # just "something unanticipated happened".
            incident_code = _log_incident("POST /api/session (profile store)", exc)
            return _error_json(
                "Hệ thống tạm thời chưa lưu được hồ sơ, vui lòng thử lại sau "
                f"(mã sự cố: {incident_code}).",
                500,
            )
        except Exception as exc:  # noqa: BLE001 - last line of defence, see module docstring
            # Same defensive catch-all every other route in this module
            # already has: ANY other failure here (not the specific
            # ProfileStoreError above) still gets the one generic Vietnamese
            # message + incident code, never a leaked exception detail.
            incident_code = _log_incident("POST /api/session", exc)
            return _error_json(_generic_error_message(incident_code), 500)
        response = JSONResponse(
            {
                "status": "OK",
                "role": "user",
                "user_ref": profile["user_ref"],
                "note": identity.WALLET_DISCLAIMER_VI,
            }
        )
        _set_session_cookie(
            response, access.create_session_cookie(user_ref=profile["user_ref"])
        )
        return response

    async def api_session_logout(request: Request) -> Response:
        """POST /api/session/logout -- clears whatever cookie POST
        /api/session set. Never inspects the cookie's own contents first
        (nothing here needs to know who, if anyone, was logged in);
        deleting a cookie that was never set, or is already invalid/
        expired, is a harmless no-op from the browser's point of view.
        """
        response = JSONResponse({"status": "OK"})
        response.delete_cookie(access.SESSION_COOKIE_NAME, path="/")
        return response

    routes = [
        Route("/", index, methods=["GET"]),
        Route("/api/bots", api_bots, methods=["GET"]),
        Route("/api/markets", api_markets, methods=["GET"]),
        Route("/api/leaderboard", api_leaderboard, methods=["GET"]),
        Route("/api/lookup", api_lookup, methods=["POST"]),
        Route("/api/session", api_session, methods=["POST"]),
        Route("/api/session/logout", api_session_logout, methods=["POST"]),
        # GET added alongside POST for the OKX a2mcp-probe CLI's own
        # GET<->POST 405 fallback (see the module docstring's route table
        # and _resolve_code_param) -- accepting both up front means that
        # fallback, and the extra round trip + 405-string-matching it
        # depends on, is never actually needed.
        Route("/api/analyze", api_analyze, methods=["GET", "POST"]),
        Route("/bot/{code}", bot_report, methods=["GET"]),
        Route("/healthz", healthz, methods=["GET"]),
        # Deliberately looks like any other route to Starlette's router --
        # the "cannot tell this exists" property lives entirely in
        # `admin_page`'s own generic-404 response, never in the routing
        # table itself.
        Route("/admin", admin_page, methods=["GET"]),
        # Obscure-path counterpart to /bot/{code} -- see user_report's own
        # docstring for why a path segment (not a subdomain) and why this
        # deliberately looks like any other single-segment path to nginx.
        # MUST be registered LAST: Starlette matches routes in list order,
        # and this pattern (`{user_ref}_{code}`, a single path segment
        # containing at least one "_") would otherwise be free to shadow
        # any other ONE-segment route added above it in the future (today:
        # "/admin", "/healthz") before that route's own literal match is
        # ever tried -- every route above is a strictly different literal
        # path or has more than one segment, so ordering does not change
        # today's behaviour, but keeping this one last is what keeps that
        # true automatically as routes are added, without anyone having to
        # re-reason about Starlette's matching order each time. See
        # Agent/test/test_web_app.py's own route-conflict tests, one per
        # sibling route, for the actual proof this holds.
        Route("/{user_ref}_{code}", user_report, methods=["GET"]),
    ]
    return Starlette(
        routes=routes, exception_handlers={Exception: _unhandled_exception}
    )


# A module-level default app so `uvicorn Agent.backend.web.app:app` also
# works directly; run_web.py builds its own via create_app() so CLI flags
# (--dashboard, --host, --port) can actually take effect.
app = create_app()


if __name__ == "__main__":  # pragma: no cover - convenience only, see run_web.py
    print(
        "Chạy `python3 -m Agent.backend.run_web` thay vì file này trực tiếp "
        "để có đầy đủ tham số CLI (--host, --port, --dashboard).",
        file=sys.stderr,
    )
