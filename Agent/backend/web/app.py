"""Starlette HTTP app for the OKX copy-trading risk-supervisor dashboard.

Built on Starlette + uvicorn only -- both already dependencies of the `mcp`
package this project depends on elsewhere (see agent_server.py's module
docstring, which documents the same fact for its own `--transport http`
mode), so nothing new is added to the project's dependency set.

Route surface:

    GET  /                  the SPA's built entry document
                             (Agent/web/dist/index.html, produced by
                             Agent/frontend/build.sh -- path is configurable,
                             see run_web.py's --dashboard/NORABT_WEB_DASHBOARD,
                             names kept from before the SPA replaced the old
                             hand-authored dashboard.html). A fresh checkout
                             that has not run the frontend build yet gets a
                             plain HTML fallback page instead of a crash --
                             see `_dashboard_response`.
    GET  /assets/*          the SPA's own JS/CSS bundle, served as static
                             files from the `assets/` directory next to
                             whichever index.html above is being served (see
                             `assets_dir` in create_app()). Not a Starlette
                             `Route` but a `Mount` (`starlette.staticfiles.
                             StaticFiles`) -- path-traversal-safe by that
                             library's own normalization, `check_dir=False`
                             so a missing build directory 404s per file
                             instead of crashing this app's startup.
    GET  /api/bots          the 30 pre-scored bots (data/assessment/**),
                             normalized (see `Agent/backend/web/data.py`'s
                             `bot_listing_row`) -- NOT the raw assessment.json
                             documents. This is the ONE place a raw document
                             is turned into a listing row; `GET /admin`
                             (below) is a redirect to the SPA that consumes
                             this same endpoint, never a second
                             normalization of its own.
    GET  /api/config        `{"admin_open_access": bool}` -- the one runtime
                             flag the SPA needs to know about BEFORE it can
                             decide whether to show its identity screen at
                             all (see `ADMIN_OPEN_ACCESS_ENV`'s own comment
                             and Agent/frontend/src/context/SessionContext.jsx).
                             Carries no secret and needs no access check of
                             its own: it only ever reveals whether the admin
                             listing is CURRENTLY unlocked for everyone, a
                             fact `GET /admin` itself already reveals for
                             free via its own 404-vs-redirect behaviour.
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
                             Response is the compact `bot_assessment_summary.v1`
                             shape (see `_analyze_summary_for_wire`): top-level
                             `status`/`code`/`name`/`verdict`/`verdict_basis`/
                             `risk`/`quality`/`confidence`/`limited_reason`/
                             `unavailable`/`text`,
                             plus `traded_symbol`, a flat `key_metrics` block
                             (closed-trade count, win rate, profit factor, max
                             drawdown, total PnL/ROI, and the Monte Carlo tail-
                             risk figures -- `None`, never fabricated, for
                             whatever could not be measured), `score_decided_by`/
                             `veto_reasons` (whether the risk score is an
                             ordinary weighted average or a veto/emergency
                             floor overrode it), and `warnings` (hidden-risk
                             flags + data limitations, merged into one
                             Vietnamese array). The old `evidence`/`mc`/`assets`
                             blocks (dimension-by-dimension breakdowns, raw
                             Monte Carlo output, per-asset ledger context) are
                             NOT included -- a measured real response ran
                             27 KB, 97%+ of it internal detail no marketplace
                             summary reader ever used; that full detail is
                             still one click away via `report_markdown`/
                             `report_url` below, and `GET /bot/<code>` renders
                             all of it (charts included) -- from an already-
                             scored bot's own `assessment.json` when one
                             exists, live via `service.analyze()` only
                             otherwise (see that route's own docstring) --
                             rather than going through this trim. `report_markdown` (a
                             ready-to-paste write-up) and `report_url`
                             (link to the GET /bot/<code> page below) -- see
                             data.py's build_report_markdown/build_report_url.
                             The per-IP rate limit (ANALYZE_RATE_LIMIT_*
                             below) is never charged for an empty/missing/
                             malformed `code`, a synonym conflict, an
                             oversized body (see ANALYZE_MAX_BODY_BYTES), or
                             a missing/invalid access token (see below) --
                             all of those get rejected first, for free. Every
                             OTHER syntactically valid `code` DOES cost one
                             unit of quota, even one already scored (Redis
                             snapshot or an on-disk `assessment.json` hit) --
                             see `ANALYZE_RATE_LIMIT_MAX_REQUESTS`'s own
                             comment for why this changed from "only a call
                             reaching `service.analyze()`" to this: the
                             response now commits to HTTP 200 (streaming, see
                             below) BEFORE it is known whether this call will
                             hit cache or run live, and a real 429 can only
                             ever be sent before that commit.

                             EVERY reply to a syntactically valid `code` --
                             FULL/LIMITED/NOT_FOUND/PENDING alike, whether
                             answered instantly from a cache/disk hit or
                             after a live `service.analyze()` run -- is sent
                             as a chunked stream that flushes one whitespace
                             byte THE MOMENT the request clears the gates
                             above, before any lookup (Redis snapshot, disk
                             `assessment.json`, or the live pipeline) even
                             starts (see `_analyze_body_stream`/
                             `_resolve_and_analyze`). This exists because a
                             lookup that is normally sub-second can, under
                             real load, be delayed several seconds by
                             threadpool/CPU contention from an UNRELATED
                             `service.analyze()` call still running in the
                             background from a previous PENDING reply --
                             measured live at 4.23s once -- and that delay
                             used to happen entirely BEFORE this endpoint had
                             sent a single byte. A "chưa từng chấm" call (or
                             any call whose lookup phase alone runs long) is
                             NEVER left waiting past
                             `ANALYZE_SYNC_DEADLINE_SECONDS` (8.0s, well
                             under the ~10s an OKX buyer CLI has been measured
                             to stop READING the response body at -- see that
                             constant's own comment for both measurements):
                             once that hard deadline hits, this endpoint
                             replies immediately with the SAME shape above,
                             `status: "PENDING"`, every scoring field `None`
                             (nothing fabricated), and `report_url` already
                             pointing at the eventual full result -- the
                             lookup-then-`service.analyze()` chain keeps
                             running in the background regardless, and a
                             later call for the same `code` (or opening
                             `report_url` itself) gets the real
                             FULL/LIMITED/NOT_FOUND result once it lands (see
                             `_analyze_body_stream`/`_resolve_and_analyze`/
                             `_pending_analyze_body`).

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
    GET  /api/analyze/status?code=... poll endpoint for the real progress
                             bar of an in-flight `/api/analyze` call (see
                             `api_analyze_status`'s own docstring for the
                             full JSON contract: state running/done/error/
                             unknown, real stage name/index/count/label, no
                             fabricated percentage -- plan_progress.md mục
                             B/D). Same access-token/admin gate as
                             `/api/analyze` above, but NEVER charged against
                             `ANALYZE_RATE_LIMIT_MAX_REQUESTS`/
                             `ADMIN_RATE_LIMIT_MAX_REQUESTS` -- meant to be
                             polled every 1.5-3s while a live analysis runs.
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

                             Both this route and GET /bot/<code> above read
                             from up to THREE sources, in order, before ever
                             falling back to a live `service.analyze()` (see
                             `_bot_report_response`'s own docstring for the
                             full contract): a fail-open Redis snapshot (see
                             Agent/backend/web/snapshot.py's module
                             docstring), then -- on a Redis miss -- this
                             exact bot's own already-scored `assessment.json`
                             on disk, if `run_report.py` has ever scored it
                             (see `data.py`'s `WebDataService.find_scored_report`).
                             Either of those HITS skips `service.analyze()`
                             entirely and renders the cached/on-disk result
                             stamped with ITS OWN capture time, never "now";
                             only a bot NEITHER source has ever seen falls
                             through to live analysis exactly as before
                             either existed, same rate limit as always. A
                             visible "Ảnh chụp lúc ..." line + "Phân tích
                             lại" link (`?refresh=1`, same query string on
                             either route) always shows what point in time
                             is being displayed -- marked as stale past 24h
                             old, since an on-disk assessment (unlike the
                             Redis tier, which expires itself by then) has
                             no built-in expiry -- and lets a reader force a
                             fresh analysis -- `?refresh=1` still spends the
                             same rate-limit quota an ordinary cache miss
                             would, so it can never be used to bypass it.
                             The Redis tier is entirely OFF by default
                             (NORABT_SNAPSHOT_REDIS_URL unset) and its own
                             failure NEVER surfaces as an error to a caller
                             of either route -- see snapshot.py's own
                             docstring for the full "buffer, not source of
                             truth" contract; the assessment.json tier
                             requires no configuration at all and simply has
                             nothing to read for a bot never scored.
    GET  /healthz           container/orchestrator liveness probe (see below)
    GET  /admin             Việc 3: no longer a second, server-rendered
                             listing page of its own -- that page
                             (`Agent/backend/web/admin_page.py`) was RETIRED
                             because it and the SPA's own `/#/admin` screen
                             were two independent implementations of the
                             same "show every scored bot" idea, each
                             re-deriving its own verdict label from the same
                             raw data (exactly the split that produced
                             Việc 1's bug: one of the two read a retired
                             field the other did not). This route is now a
                             plain redirect to the SPA's `/#/admin`, which is
                             the ONE listing screen left, and the ONE
                             consumer of `GET /api/bots`'s already-normalized
                             rows. Access control is UNCHANGED: gated by the
                             same admin key as /api/analyze's own admin role
                             (NORABT_ADMIN_TOKEN_SHA256, checked via
                             access.verify_admin_token) OR an admin session
                             cookie (see `_is_admin_request`), OR -- Việc 2's
                             own explicit, temporary decision -- unconditionally
                             when `NORABT_ADMIN_OPEN_ACCESS` is on (see
                             `ADMIN_OPEN_ACCESS_ENV`). The FAILURE mode is
                             unchanged too: a missing/wrong key (admin role
                             not configured, the default, and open access
                             off) is a single generic 404, NEVER 401/403 --
                             an admin route that answers "exists, but you're
                             not allowed" to a stranger has already told
                             them exactly where to point a brute-force
                             attempt, and a redirect target itself would be
                             exactly that same tell.

Every route is wrapped so it can never let a raw exception (and therefore a
Python traceback) reach the client: known outcomes (bad input, rate limit)
map to a specific HTTP status with a Vietnamese JSON body, and a final
`Exception` handler at the app level is the last line of defence for
anything unanticipated. `WebDataService.analyze()` itself already treats
NOT_FOUND/LIMITED as ordinary 200 results, per the task's own contract --
this module never re-wraps those as errors.
"""

from __future__ import annotations

import asyncio
import html
import ipaddress
import logging
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from Agent.backend.infra.config import config
from Agent.backend.qc.reporting import narrative
from Agent.backend.web import access, identity, snapshot, usage_ref
from Agent.backend.web import progress as analyze_progress
from Agent.backend.web.data import (
    InvalidCodeError,
    PerIpRateLimiter,
    WebDataService,
    build_report_markdown,
    build_report_url,
    detail_link_line,
    pending_result,
    report_base_url,
    report_url_is_usable,
    validate_unique_code,
)
from Agent.backend.web.report_page import render_bot_report_html

logger = logging.getLogger(__name__)

# Default location for the SPA's built entry document, overridable via
# run_web.py's --dashboard flag or the NORABT_WEB_DASHBOARD env var it reads
# -- the parameter/env var KEEP THEIR ORIGINAL NAMES (this module is the
# only file this task may edit; run_web.py, which imports
# `DEFAULT_DASHBOARD_PATH` and passes `dashboard_path=` unchanged, is not).
#
# Việc 2: this used to point at a hand-authored Agent/web/dashboard.html
# (now deleted). It now points at Agent/web/dist/index.html -- the file
# `Agent/frontend/build.sh` produces (see that script and
# Agent/frontend/vite.config.js's own `build.outDir`). Deliberately does not
# need to exist -- see _dashboard_response's fallback below -- so a fresh
# checkout that has not run the frontend build yet still serves a working
# API, and `/assets/*` (see `_assets_directory`/the `Mount` in create_app
# below) degrades to a plain 404 per file rather than refusing to start.
DEFAULT_DASHBOARD_PATH = Path(config.BASE_DIR) / "web" / "dist" / "index.html"

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
                "%s: skipping invalid CIDR range %r", TRUSTED_PROXIES_ENV, cidr
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


# Rate limit applied to POST /api/analyze specifically: each call MAY cost
# several seconds of CPU and several OKX requests (see data.py's module
# docstring), so this is deliberately much tighter than a generic API rate
# limit would be. `api_analyze` below still resolves/validates `code` BEFORE
# touching the limiter, so a probe/mistyped/conflicting `code` is still
# free -- that ordering matters specifically for the OKX a2mcp-probe CLI:
# its protocol always opens with an EMPTY probe request (no `code`) purely
# to discover a parameter is required, then asks a human for the bot code
# and probes again -- possibly several times if they mistype it, or once
# more on top of that if the CLI's own GET<->POST 405 fallback kicks in.
# None of those round trips cost this server any CPU or any OKX request, so
# none of them may consume this budget. A 429 is also a DEAD END for that
# CLI, not a "wait and retry" signal -- it treats a rate limit as a terminal
# failure, so charging quota for a probe or a mistyped code would cut the
# buyer out of the flow entirely instead of letting them be reprompted for
# the right code.
#
# ĐÃ ĐỔI (đo thật, project owner 2026-09-17): trước đây quota này CHỈ bị tính
# cho lượt gọi thật sự chạm tới service.analyze() -- một mã đã có sẵn trong
# Redis snapshot hay `assessment.json` trên đĩa (`find_scored_report`) trả
# lời NGAY, không đụng limiter. Cách đó buộc api_analyze phải tra cứu hai
# tầng đó XONG rồi mới biết có tính quota hay không -- và chính hai tra cứu
# "rẻ" đó là thứ đo được giãn ra tới 4.23s khi tranh threadpool với một
# service.analyze() nền khác (xem ANALYZE_SYNC_DEADLINE_SECONDS's comment),
# khiến byte đầu tiên gửi cho client trễ theo. Để byte đầu LUÔN bay đi ngay
# khi request tới (bất kể tải), toàn bộ ba tầng tra cứu (snapshot -> disk ->
# sống) giờ chạy BÊN TRONG generator streaming, SAU khi response đã cam kết
# 200 -- nghĩa là điểm duy nhất còn có thể trả 429 (trước khi cam kết đó)
# không còn biết trước lượt gọi này sẽ trúng cache hay phải chạy sống. Đánh
# đổi: một mã ĐÃ CHẤM sẵn (cache/disk hit) giờ CŨNG tốn một suất quota, dù
# bản thân nó rẻ -- chỉ probe rỗng, mã sai định dạng, và hai tham số đồng
# nghĩa xung đột nhau mới còn được miễn phí hoàn toàn (xem các nhánh phía
# trên `active_limiter.allow()` trong api_analyze).
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

# Đo thật (project owner, 2026-09-17) trên chính OKX CLI (`onchainos agent
# a2mcp-probe`): nó bỏ cuộc ở ĐÚNG ~10.1s dù endpoint vẫn đang chạy và sẽ trả
# HTTP 200 đầy đủ sau đó (32.4s trên một bot chưa từng chấm) -- không có
# tham số timeout nào cấu hình được từ phía service, và chuỗi
# `idle_timeout_ms` tìm thấy trong binary CLI gợi ý giới hạn đó là THỜI GIAN
# IM LẶNG trên kết nối (không có byte nào chảy qua), không phải tổng thời
# gian chờ -- xem `_analyze_body_stream` bên dưới cho cách khai thác đúng
# giả thuyết này (gửi một khoảng trắng đều đặn cho tới khi có kết quả thật,
# thay vì im lặng suốt 15-70s rồi mới gửi một cục JSON). 2.5s là một nửa
# ngưỡng ~10s CLI cắt, để một lần trễ mạng/GC bất thường vẫn còn dư dả biên
# độ trước khi CLI kết luận "im lặng quá lâu".
ANALYZE_HEARTBEAT_INTERVAL_SECONDS = 2.5

# Đo thật tiếp theo (project owner, 2026-09-17), chạy qua ĐÚNG CLI OKX thật
# (`okx_journey.sh`), không chỉ ở tầng HTTP: nhịp tim ở trên giữ được kết nối
# "sống" qua ngưỡng ~10s (bước probe không còn `endpoint_failure`), NHƯNG CLI
# đó chỉ thực sự ĐỌC THÂN phản hồi trong khoảng 10 giây đó -- quá hạn thì nó
# bỏ dở phần thân JSON dở dang (dù byte vẫn đang chảy) nhưng vẫn coi endpoint
# là "sống" và đi tiếp sang bước `confirm-free`, bước đó chỉ PHÁT LẠI kết quả
# đã lưu (không gọi lại endpoint) -- nên người mua nhận một `result` RỖNG dù
# không có lỗi nào được báo. Nhịp tim một mình vì vậy KHÔNG đủ, và còn nguy
# hiểm hơn lỗi cũ (trông như thành công mà rỗng, thay vì báo lỗi rõ ràng).
#
# Vì vậy `/api/analyze` phải tự chốt một hạn CỨNG, luôn dưới ~10s đó, để LUÔN
# trả một JSON HOÀN CHỈNH trước khi CLI ngừng đọc thân -- 8.0s, không phải
# 9.x, để chừa lại một biên độ ~2s cho: (1) độ trễ mạng giữa CLI và Cloudflare
# rồi tới nginx/uvicorn của service này (ngưỡng ~10s đo được là tại CLI, không
# phải tại service -- một phần thời gian đó đã bị hai chặng mạng ở giữa ăn
# mất), và (2) sai số đo đạc/GC-pause bất thường của chính lần đo 10.1s ở
# trên. Quá hạn này mà `_resolve_and_analyze` (snapshot Redis -> disk ->
# `service.analyze()` sống, OKX + Monte Carlo 10k + narrative tuỳ chọn) vẫn
# chưa xong thì `_analyze_body_stream` bên dưới trả về NGAY một JSON hoàn
# chỉnh, hình dạng y hệt (`_analyze_summary_for_wire`'s contract),
# `status="PENDING"` (xem data.py's `ANALYZE_STATUS_PENDING`) thay vì tiếp
# tục chờ -- KHÔNG BAO GIỜ huỷ tác vụ nền đang chạy: nó vẫn sống tiếp sau khi
# response này đã trả xong, tự ghi vào `WebDataService._analyze_cache`/Redis
# snapshot như một lượt phân tích bình thường (xem `_track_background_
# analyze_task` bên dưới cho lý do phải giữ một tham chiếu mạnh tới task đó).
#
# ĐO THẬT tiếp theo nữa (project owner, 2026-09-17), lý do hạn này giờ bao
# TRỌN VẸN cả `_resolve_and_analyze`, không chỉ riêng `service.analyze()`:
# ba lượt gọi `/api/analyze` liên tiếp trên cùng server thật đo được tổng
# thời gian 11.14s, 8.49s, và 9.09s/12.66s (hai lần cho cùng một mã) -- vượt
# hẳn hạn 8.0s tưởng chừng đã đủ. Mổ xẻ lần 12.66s: byte đầu tiên bay đi sau
# 4.23s, KHÔNG PHẢI sau ~0.0x s như thiết kế -- tức là 4.23s đó tiêu hết
# TRƯỚC KHI generator streaming này kịp chạy, vì khi đó `snapshot.
# get_snapshot`/`service.find_scored_report` (tưởng "rẻ", đo riêng chỉ
# 0.01s) còn chạy Ở NGOÀI generator, tranh threadpool/CPU với một
# `service.analyze()` khác đang chạy nền từ một lượt PENDING trước đó --
# đúng cảnh OKX thật sẽ liên tục tạo ra, không phải tình huống nhân tạo.
# Kết quả: đồng hồ hạn 8s chỉ bắt đầu chạy SAU 4.23s đó, nên tổng cộng
# ≈ 4.23 + 8 ≈ 12.7s, khớp con số đo được. Sửa: gộp CẢ BA TẦNG tra cứu vào
# MỘT task duy nhất (`_resolve_and_analyze`), chạy nó SAU byte đệm đầu tiên
# (`yield b" "`) của `_analyze_body_stream` -- để hạn cứng này bao trùm
# ĐÚNG TOÀN BỘ phần việc còn lại, không còn khoảng thời gian nào "trốn"
# ngoài đồng hồ trước khi generator bắt đầu tính giờ.
# Hạ từ 8.0 xuống 6.0 sau khi đo thật: truy vết từng chunk qua Cloudflare cho
# thấy cơ chế hạn chạy CHÍNH XÁC (hai lần đo độc lập: nhịp tim 2.5s, rồi thân
# JSON ra đúng 8.02s sau byte đầu, chỉ 10-20ms sau nhịp cuối). Nhưng khi có
# phân tích nền của lượt TRƯỚC còn chạy, tổng thời gian tới client vọt lên
# 11.9-18.1s dù byte đầu vẫn 0.31-0.33s. Với trần ~10s mà CLI OKX ngừng đọc
# thân, biên 2 giây là quá mỏng để hấp thụ phần dao động đó.
#
# 6.0 cho biên 4 giây. Đổi lại người dùng nhận PENDING sớm hơn ~2 giây trong
# những lượt lẽ ra kịp xong -- chấp nhận được, vì phân tích vẫn chạy tiếp ở
# nền và link chi tiết có đầy đủ ngay sau đó, còn một `result` RỖNG thì hỏng
# hẳn trải nghiệm mà lại trông như thành công.
ANALYZE_SYNC_DEADLINE_SECONDS = 6.0

# Câu tiếng Việt DUY NHẤT hiển thị cho trạng thái PENDING ở trên -- xem
# `ANALYZE_SYNC_DEADLINE_SECONDS`'s comment cho bối cảnh. Cố tình không nêu
# một con số giây cụ thể nào (kiểu "quay lại sau 30s") vì thời gian còn lại
# thật sự phụ thuộc bot (OKX fetch + Monte Carlo 10k có thể mất 15-70s tổng
# cộng, xem `_run_live_analyze`'s docstring) -- "vài chục giây" là khoảng đúng
# với đo thật đó mà không bịa một con số chính xác không giữ được lời hứa.
ANALYZE_PENDING_TEXT_VI = (
    "This bot is being analysed -- the scoring pipeline (OKX data + Monte "
    "Carlo simulation) is still running in the background and is NOT done "
    "yet. This is not the final result; there is no risk score/quality "
    "score to show yet. The full result will be available at report_url, "
    "usually within another few tens of seconds -- please reopen that link "
    "or call again in a few minutes."
)

# Đo thật tiếp theo (project owner, 2026-09-17), SAU KHI đã sửa lỗi
# "tra cứu chạy trước generator" ở trên: 4 mã CHƯA từng chấm gọi LIÊN TIẾP
# qua đúng domain thật vẫn cho một kết quả HỎNG ở lượt thứ 4 -- tổng 27.2s
# (byte đầu vẫn đúng, chỉ 0.427s) trong khi 3 lượt trước đó đều đạt (~8.3s
# hoặc nhanh hơn). Log container cho thấy nguyên nhân: mỗi response PENDING
# để lại một `_resolve_and_analyze` chạy nền (đúng thiết kế, xem
# `_track_background_analyze_task`) -- nhưng KHÔNG CÓ TRẦN nào giới hạn có
# bao nhiêu tác vụ nền như vậy được phép chạy CÙNG LÚC. Tới lượt gọi thứ 4,
# đã có 3 tác vụ nền (từ 3 lượt PENDING trước) đang chạy song song, mỗi tác
# vụ tự chiếm một luồng threadpool + chạy Monte Carlo 10k (CPU-nặng) + gọi
# OKX -- trên một máy chủ bị ép trần CỨNG ≤12 core CHO CẢ project (xem
# server-resource-limit trong bộ nhớ dự án) và đang chạy CHUNG với ~15 site
# production khác, ngần ấy việc CPU-nặng chạy đồng thời đủ để làm CHÍNH
# event loop (một luồng duy nhất, dùng chung cho MỌI request) bị đói CPU/GIL
# -- kết quả là đồng hồ hạn `ANALYZE_SYNC_DEADLINE_SECONDS` vẫn nổ ĐÚNG giờ
# NỘI BỘ (số byte đệm heartbeat đo được không đổi giữa lượt nhanh và lượt
# chậm) nhưng byte JSON cuối cùng bị TRỄ khi thật sự phát ra ngoài socket.
# Đây KHÔNG phải lỗi logic hạn cứng (thiết kế task -> yield đệm -> bấm giờ
# -> wait vẫn đúng) mà là THIẾU KIỂM SOÁT TẢI: số tác vụ nền tăng không giới
# hạn theo lưu lượng gọi thật.
#
# Trần CỨNG cho số `_run_live_analyze` được phép chạy ĐỒNG THỜI trong CÙNG
# một app instance (xem `_resolve_and_analyze`'s `live_analyze_in_flight`
# cho nơi áp dụng) -- 2, không phải 1 (sẽ coi MỌI request thứ hai trở đi là
# "quá tải" ngay cả khi máy còn dư sức, quá thận trọng) và không phải >=4
# (lặp lại đúng vấn đề vừa đo được ở trên với chỉ 3 tác vụ song song). Vượt
# trần này KHÔNG xếp hàng chờ (tránh "chờ vô hạn" -- xem
# `_resolve_and_analyze`'s docstring cho lý do chọn từ chối ngay thay vì
# hàng đợi) -- trả PENDING ngay lập tức, KHÔNG spawn thêm một
# `_run_live_analyze` nào, để tổng số tác vụ nền CPU-nặng không bao giờ vượt
# trần này dù lưu lượng gọi thật tăng cao tới đâu.
ANALYZE_MAX_CONCURRENT_LIVE_ANALYSES = 2

# Câu tiếng Việt DUY NHẤT hiển thị khi một lượt gọi bị từ chối vì chạm
# `ANALYZE_MAX_CONCURRENT_LIVE_ANALYSES` -- CỐ TÌNH khác `ANALYZE_PENDING_
# TEXT_VI` ở trên (dù cùng `status: "PENDING"`): câu đó nói "đang chạy nền",
# đúng cho trường hợp task ĐÃ được spawn và đang xử lý; câu này phải nói
# đúng sự thật NGƯỢC LẠI -- bot này CHƯA được bắt đầu phân tích, không có
# task nào đang chạy nền cho riêng nó, vì hệ thống đã đạt trần xử lý đồng
# thời. Nói sai thành "đang chạy nền" sẽ khiến người gọi tưởng cứ đợi/mở lại
# report_url là có kết quả, trong khi thực tế không có gì đang chạy để đợi.
ANALYZE_OVERLOADED_TEXT_VI = (
    "The system is currently processing too many other bot analyses at "
    "once (the concurrency cap has been reached) -- analysis of THIS bot "
    "has NOT started, and no task is running in the background for it. "
    "This is not the final result; there is no risk score/quality score to "
    "show yet. Please call /api/analyze again for this code in a few "
    "minutes once the system is less busy, or reopen the report_url link "
    "to have the system try analysing it again."
)

# Sửa lỗi treo >60s (đo thật, project owner 2026-09-17, xem plan_progress.md
# mục C): `GET /bot/<code>` ngay sau một `/api/analyze` vừa trả PENDING cho
# CÙNG mã trước đây luôn tự chạy MỘT LƯỢT PHÂN TÍCH THỨ HAI song song với
# tác vụ nền đã có (`live_analyze_tasks` bên dưới, gắn trong
# `_analyze_body_stream`) -- hai lượt cùng tranh threadpool/OKX/CPU khiến
# HTTP 000 sau >60s (đo thật: bot F76CC883269E6FFB). `_bot_report_response`
# giờ AWAIT đúng task đang bay của mã đó thay vì khởi động lượt thứ hai --
# hạn chờ dưới đây, không phải vô hạn: một task treo thật sự (hiếm, ví dụ
# OKX không bao giờ trả lời) không được phép giữ trang chi tiết chờ mãi,
# nên hết hạn này thì FAIL-OPEN về đúng hành vi cũ (tự chạy sống của riêng
# nó) thay vì trả lỗi.
#
# ĐÃ CHỈNH LẠI SAU LẦN ĐO KIỂM CHỨNG ĐẦU TIÊN (F.4, project owner
# 2026-09-17): 45s (ước tính ban đầu từ mẫu 5 bot trong progress.py, thấy
# FULL xong trong 4-32s) HOÁ RA quá thấp -- đo lại kịch bản hỏng thật trên
# CHÍNH bot F76CC883269E6FFB (bot gốc của báo cáo lỗi) cho thấy pipeline
# thật của NÓ mất 71.4s (registry's `elapsed_ms`), vượt hẳn 45s. Với hạn cũ,
# `_bot_report_response` fail-open ở giây 45 rồi tự chạy MỘT LƯỢT PHÂN TÍCH
# THỨ HAI (đúng thứ mục C định xoá bỏ), hai lượt tranh nhau OKX/CPU khiến
# tổng thời gian vẫn vượt 65s -- tái diễn gần như nguyên vẹn bug gốc, chỉ
# trễ hơn 45s thay vì ngay lập tức. 70s (không phải 45s): đủ để bao trọn cả
# outlier 71.4s vừa đo (chỉ thiếu 1.4s, coi là biên đo được, không phải số
# tuỳ tiện) trong ĐA SỐ trường hợp, đồng thời vẫn ngắn hơn ngưỡng nginx
# proxy_read_timeout 75s đã biết -- một task THẬT SỰ treo (không bao giờ
# xong) vẫn fail-open trước khi nginx tự cắt kết nối, giữ đúng tinh thần cũ.
BOT_REPORT_AWAIT_LIVE_TASK_TIMEOUT_SECONDS = 70.0

# Việc 2 -- project owner's explicit, temporary "bỏ bước nhập định danh"
# decision: when this env var is on, `GET /admin` serves (as a redirect to
# the SPA's own `/#/admin` listing, see `admin_page` below and Việc 3) with
# NO admin credential required at all, and the SPA itself (see
# Agent/frontend/src/context/SessionContext.jsx) skips its identity screen
# and goes straight to the admin listing. Defaults OFF (`false`) -- the
# exact same locked-behind-a-key behaviour this route always had -- because
# flipping it on means literally anyone on the internet who knows this
# server's address can see the full list of analyzed bots and their scores;
# see Agent/.env.example's own comment on this variable for the full
# consequence spelled out for whoever sets it. Read fresh from the
# environment on every call (same "read live, not once at import time"
# pattern as `access.is_protected()`/`data.py`'s `report_base_url()`), so a
# test can flip it with `monkeypatch.setenv`/`delenv` and an operator's env
# change takes effect on the next request with nothing else to keep in
# sync.
ADMIN_OPEN_ACCESS_ENV = "NORABT_ADMIN_OPEN_ACCESS"

_ADMIN_OPEN_ACCESS_TRUE_VALUES = {"true", "1", "yes", "on"}


def _admin_open_access() -> bool:
    """`True` only for a recognized "on" spelling of `ADMIN_OPEN_ACCESS_ENV`
    -- anything else (unset, blank, a typo) fails closed to `False`, the
    same locked-by-default posture this route already had before this
    variable existed. Deliberately NOT the "unrecognized value keeps the
    default" leniency `access._parse_tokens` uses elsewhere in this project:
    this flag's default is the SAFE side (locked), so an operator's typo
    must never accidentally turn INTO the exposed side.
    """
    raw = os.environ.get(ADMIN_OPEN_ACCESS_ENV, "").strip().lower()
    return raw in _ADMIN_OPEN_ACCESS_TRUE_VALUES


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

# Same reasoning/pattern as HEALTHZ_OKX_CACHE_TTL_SECONDS immediately above,
# applied to the snapshot Redis reachability probe GET /healthz also reports
# (see snapshot.ping()) -- an orchestrator polling every ~30s must not turn
# into 30s-interval Redis load of its own, and a hung/unreachable Redis must
# never make THIS route slow (snapshot.ping() already bounds a single call to
# well under a second, this cache just avoids paying that cost on every poll).
SNAPSHOT_HEALTHZ_CACHE_TTL_SECONDS = 20.0


def _start_background_rescore(code: str, data_dir: Any) -> None:
    """Chấm lại và ghi đè `assessment.json` của `code` ở một luồng nền.

    Không bao giờ ném ra ngoài: đây là việc làm-cho-đúng-về-sau, không phải
    một phần của phản hồi đang trả cho người dùng. Hỏng thì ghi log và để
    nguyên bản cũ trên đĩa.
    """

    def _run() -> None:
        try:
            # `rescore_one_bot_complete` chứ KHÔNG phải bản chỉ-chấm-điểm
            # trong assessment_store: bản kia không sinh lại đoạn nhận
            # định, nên người dùng bấm "Phân tích lại" sẽ nhận về một báo
            # cáo NGHÈO HƠN trước khi bấm -- số mới nhưng mất phần văn cho
            # tới lượt chấm hàng loạt kế tiếp.
            from Agent.backend.run_report import rescore_one_bot_complete

            written = rescore_one_bot_complete(Path(data_dir), code)
            if written:
                logger.info("norabt refresh: đã ghi đè %s", written)
            else:
                logger.warning(
                    "norabt refresh: không chấm lại được %s -- giữ nguyên bản cũ",
                    code,
                )
        except Exception:  # noqa: BLE001 - xem docstring
            logger.exception("norabt refresh: lỗi khi ghi đè bản chấm của %s", code)

    threading.Thread(
        target=_run, name=f"norabt-rescore-{code[:8]}", daemon=True
    ).start()


def _narrative_healthz_status() -> str:
    """`GET /healthz`'s `narrative` field -- one of `"disabled"`, `"ok"`
    (optionally suffixed with the resolved binary's version, e.g.
    `"ok (claude 2.1.270)"`, when it was found via the
    `NORABT_CLAUDE_VERSIONS_DIR` mount rather than a direct
    `NORABT_CLAUDE_BIN` override or a bare `"claude"` off PATH -- see
    `narrative.claude_binary_status`), `"binary_missing"`, or
    `"no_credentials"`.

    This exists because the narrative feature (Agent/backend/qc/reporting/
    narrative.py) fails CLOSED and SILENTLY by design: any transport
    failure degrades to a static fallback sentence rather than ever
    breaking `/api/analyze`/`GET /bot/<code>` (see that module's own
    docstring) -- exactly the behaviour that made a broken container mount
    (the `claude` binary/credentials living only on the HOST, see
    Agent/deploy/docker-compose.yml) invisible until someone actually
    diffed a response against the expected LLM prose. This field turns that
    silent degradation into something `docker exec .../healthz` (or an
    orchestrator dashboard) can show a human directly, without ever
    spending real Claude usage quota to find out -- see below.

    Deliberately CHEAP: only environment-variable reads, `os.access`, and
    (via `narrative.py`'s own cache) an occasional `os.listdir` of the
    mounted versions directory -- NEVER spawns the `claude` CLI itself, so
    polling this route on every orchestrator healthcheck interval (see
    docker-compose.yml) never costs a cent of the project owner's own
    Claude usage.

    Only meaningful for the `"cli"` backend -- the one actually wired to a
    real binary/credentials mount. The unset/invalid default and the
    unimplemented `"api"` backend both report `"disabled"` here: neither
    has a mount/binary/credentials contract this probe could check, and
    both already fall back to the static narrative sentence unconditionally
    regardless of what this field says.

    KNOWN BLIND SPOT, documented rather than hidden (see
    Agent/deploy/README.md): `"ok"` here only means the credentials FILE is
    present and readable, never that its token is still valid. That token
    is refreshed by a `claude` session running on the HOST -- a read-only
    container mount cannot refresh it -- so a host that has not run
    `claude` in a long time can show `"ok"` here while every real narrative
    call still quietly degrades to the fallback sentence. This route has no
    way to tell the difference without spawning the CLI, which it must
    never do.
    """
    backend_choice = os.environ.get(narrative.ENV_BACKEND, "").strip().lower()
    if backend_choice == "agy":
        # Trước đây mọi backend khác "cli" đều bị báo "disabled", kể cả khi
        # nó đang chạy tốt -- một điểm mù giám sát thật: người vận hành
        # nhìn /healthz sẽ tưởng tính năng đã tắt.
        return f"ok ({backend_choice})" if narrative.agy_status() == "ok" else narrative.agy_status()
    if backend_choice != "cli":
        return "disabled"
    status, version = narrative.claude_binary_status()
    if status == "binary_missing":
        return "binary_missing"
    if not narrative.claude_credentials_available():
        return "no_credentials"
    return f"ok (claude {version})" if version else "ok"


_FALLBACK_DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Frontend not built</title></head>
<body style="font-family: system-ui, sans-serif; max-width: 640px; margin: 3rem auto; padding: 0 1rem;">
<h1>Frontend not built</h1>
<p>Could not read the HTML file at: <code>{path}</code></p>
<p>Run <code>bash Agent/frontend/build.sh</code> to build the SPA (produces
<code>Agent/web/dist/index.html</code> and <code>Agent/web/dist/assets/</code>),
or set a different path via the CLI parameter <code>--dashboard</code>/the
environment variable <code>NORABT_WEB_DASHBOARD</code> when starting the
server. While waiting for the build, the JSON APIs below can still be used
directly:</p>
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
<html lang="en">
<head><meta charset="utf-8"><title>Report could not be generated</title></head>
<body style="font-family: system-ui, sans-serif; max-width: 640px; margin: 3rem auto; padding: 0 1rem;">
<h1>Could not generate bot report</h1>
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
        "An unexpected system error occurred. Please try again later; if "
        f"the error persists, please report incident code: {incident_code}."
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
    "location": "body.code (JSON) or query string ?code=...",
    "description": (
        "The uniqueCode of an OKX copy-trading bot -- hex or numeric, "
        "letters and digits only, up to 64 characters."
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
            "%s=%r is not a valid integer -- using default %d",
            MISSING_PARAM_STATUS_ENV,
            raw,
            DEFAULT_MISSING_PARAM_STATUS,
        )
        return DEFAULT_MISSING_PARAM_STATUS
    if value not in _ALLOWED_MISSING_PARAM_STATUSES:
        logger.warning(
            "%s=%d is not one of %s -- using default %d",
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
                "Missing required parameter 'code' (the uniqueCode of a bot "
                "on OKX) in the JSON body or query string -- example: "
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
                "Synonym parameter names for 'code' carry different values "
                f"('{first_key}'={first_value!r} differs from '{other_key}'={other_value!r}) "
                "-- please send only a single value."
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
    """
    if _admin_open_access():
        return True
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
                "Missing authentication token -- send it via the "
                "'X-Access-Token' header or a 'token' parameter in the "
                "query string/JSON body."
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
            "message": "Invalid authentication token.",
            "error_en": "invalid access token",
        },
        status_code=403,
    )


_BODY_TOO_LARGE_MESSAGE = (
    "Request body too large -- /api/analyze only needs a small JSON object "
    f"holding a bot code, capped at {ANALYZE_MAX_BODY_BYTES // 1024} KiB."
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


# --------------------------------------------------------------------------- #
# Compact wire shape for POST/GET /api/analyze -- measured on a real FULL
# response: the old shape (raw `evidence`/`mc`/`assets` handed back whole)
# ran 27,208 characters, of which `evidence.current_state` alone (a snapshot
# of the bot's currently OPEN positions -- not even part of this project's
# own analysis, which scores CLOSED trades only) was 9,519 -- 35% of the
# entire payload for a field the conclusion never touches. The project
# owner's own measured ruling: the reader of this JSON is a STRANGER's
# agent on the OKX AI Marketplace that re-summarizes it for ITS OWN user,
# never a human paging through the raw blob -- so the wire response should
# be the four numbers + verdict a summary actually needs, plus a link to
# the full HTML report (`report_url`, GET /bot/<code>) for anyone who wants
# the underlying evidence. `schema` names this shape explicitly so a future
# reshape can version it instead of silently breaking every existing caller.
#
# Critically, this is a WIRE-ONLY trim, same principle `_with_detail_link`
# above already relies on: `WebDataService.analyze()` (data.py) keeps
# computing and returning the FULL `evidence`/`mc`/`assets` blob
# unconditionally, and its TTL cache keeps storing that full object -- see
# `_full_result` there. `GET /bot/<code>` / `GET /<userref>_<code>` call
# `service.analyze()` directly (never through this function), so their
# charts and "chi tiết" `<details>` sections keep reading the untouched
# full object regardless of what this endpoint's own JSON response drops.
ANALYZE_SUMMARY_SCHEMA = "bot_assessment_summary.v1"

# A REGRESSION-WARNING threshold, not a protocol constraint: this exists so
# a future change that silently bloats the summary back toward the 27,208
# raw shape above gets caught by a test (test_analyze_full_response_stays_
# under_size_budget) instead of drifting unnoticed. It is NOT a reason to
# drop a field a reader actually needs -- that mistake already happened
# once here: `verdict_basis` (the "sở cứ ở đâu" sentence backing the
# verdict label, see VERDICT_BASIS_VI) was excluded from this summary to
# stay under an earlier, stricter 5,000-char cut, even though a real FULL
# response (with a usable report_url) already ran past 5,000 chars WITHOUT
# it. Cutting a load-bearing field to save ~200 bytes against a self-chosen
# number was the wrong trade -- so the number moved instead: 6,500 leaves
# headroom for `verdict_basis` plus normal per-bot variance in `text`/
# `warnings` length, while still keeping this response two orders of
# magnitude below the 27 KB internals dump it replaced. If a genuinely
# necessary field ever pushes past this again, raise the budget again --
# never drop the field to fit it.
#
# Raised from 6500 to 8000 when the optional `narrative` field
# (Agent/backend/qc/reporting/narrative.py) was added: that field is
# capped at MAX_NARRATIVE_CHARS (2000) characters by its own length gate,
# so the worst case is this old budget plus that cap plus a little JSON
# quoting/escaping overhead -- 8000 leaves comfortable headroom above that
# worst case while still keeping this response nowhere near the 27 KB
# shape it replaced. `narrative` is `None` (a few bytes) for the common
# "feature not configured" case and for LIMITED/NOT_FOUND, so this only
# actually gets exercised once an operator opts into the feature.
#
# Raised again, 8000 -> 9000, when `strategy_profile`
# (`_strategy_profile_from_evidence` below) was added: a compact handful of
# short enum strings/short lists (never the full `evidence.strategy`/
# `evidence.behavioral`, which stay dropped like the rest of `evidence`) --
# measured worst case (every optional sub-field present, `untested_phases`
# holding every phase name) adds well under 1000 chars, so 9000 keeps the
# same comfortable-headroom margin the 6500->8000 move above already
# established, never trading a necessary field away to stay under a
# self-chosen number.
ANALYZE_SUMMARY_SIZE_BUDGET_CHARS = 9000


def _strategy_profile_from_evidence(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """Compact `strategy_profile` for the wire summary -- Việc 2's own
    explicit request ("gọn, vài trường, không đổ cả schema"). Sourced from
    `evidence["strategy"]`/`evidence["behavioral"]` (`_full_result` in
    data.py, via `_strategy_evidence`/`_behavioral_evidence`), which this
    endpoint's summary otherwise drops entirely along with the rest of
    `evidence` -- so a buyer-side agent reading ONLY `/api/analyze`'s
    compact JSON still learns how the bot plays, not just its score.

    Every key is always present (`None`/`[]` when the underlying
    observation itself is `UNKNOWN`/empty), same "never silently drop a
    key" contract the rest of this summary already follows.
    """
    strategy = evidence.get("strategy")
    strategy = strategy if isinstance(strategy, dict) else {}
    behavioral = evidence.get("behavioral")
    behavioral = behavioral if isinstance(behavioral, dict) else {}
    return {
        "observed_profile": strategy.get("observed_profile"),
        "directional_bias": strategy.get("directional_bias"),
        "entry_style": strategy.get("entry_style"),
        "phase_coverage_pct": strategy.get("phase_coverage_pct"),
        "best_phase": strategy.get("best_phase"),
        "worst_phase": strategy.get("worst_phase"),
        "untested_phases": strategy.get("untested_phases") or [],
        "tested_in_downtrend": strategy.get("tested_in_downtrend"),
        "behavioral_risk_tier": behavioral.get("behavioral_risk_tier"),
        "phase_breakdown": strategy.get("phase_breakdown") or [],
    }


def _key_metrics_from_evidence(
    evidence: Dict[str, Any], mc: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Flatten the handful of numbers a reader of the compact summary
    actually needs out of the two deep blocks this endpoint used to hand
    back whole (`evidence.performance`, top-level `mc`).

    Every key below is ALWAYS present in the returned dict -- `None` when
    the source field itself is `None`/missing (LIMITED/NOT_FOUND, whose
    `evidence`/`mc` are `{}`/`None`; or a FULL bot whose Monte Carlo run
    could not produce a given figure), never fabricated and never silently
    dropped, so a caller can tell "not measured" apart from "measured as
    zero" (the project owner's own explicit requirement).
    """
    perf = evidence.get("performance")
    perf = perf if isinstance(perf, dict) else {}
    mc = mc if isinstance(mc, dict) else {}
    return {
        "closed_trades": perf.get("trade_count"),
        "win_rate_pct": perf.get("win_rate"),
        "profit_factor": perf.get("profit_factor"),
        "max_drawdown_pct": perf.get("max_drawdown_pct"),
        "total_pnl": perf.get("total_pnl"),
        "roi_pct": perf.get("roi_pct"),
        "p_ruin_pct": mc.get("p_ruin"),
        "p_loss_after_horizon_pct": mc.get("p_loss_after_horizon"),
        "p95_max_drawdown_pct": mc.get("p95_max_drawdown"),
        "probability_of_profit_pct": mc.get("probability_of_profit"),
        "simulation_iterations": mc.get("iterations"),
        "horizon_stability": mc.get("horizon_stability_label"),
        "inference_reliable": mc.get("inference_reliable"),
    }


def _score_governance_from_evidence(
    evidence: Dict[str, Any],
) -> Tuple[Optional[str], List[str]]:
    """`score_decided_by`/`veto_reasons` -- per the project owner, the single
    most important fact this summary must surface: whether the risk number
    is an ordinary weighted average of the 10 scored dimensions, or a
    veto/emergency floor overrode that average (see
    `Agent/backend/qc/schemas/risk_assessment.py`'s `ScoreBreakdown.decided_by`
    and `Agent/backend/qc/scoring/fusion.py`). Measured across this
    project's own scored cohort: roughly half of veto-decided bots would
    otherwise read as an unremarkable average to someone who only sees the
    final number -- so this is promoted out of the (now-dropped)
    `evidence.score_breakdown` to the top level rather than left for a
    reader to dig for.

    `decided_by` is `None` (not the fusion engine's own "WEIGHTED_AVERAGE"
    default) whenever there is no score breakdown to read from at all
    (LIMITED/NOT_FOUND) -- an explicit "not applicable", never a guess at
    what an unrun scoring pass would have said.
    """
    breakdown = evidence.get("score_breakdown")
    breakdown = breakdown if isinstance(breakdown, dict) else {}
    return breakdown.get("decided_by"), list(breakdown.get("veto_reasons") or [])


# The two literal, code-guaranteed line prefixes `_explanation_vi` (data.py)
# always uses -- and the ONLY place in the codebase that produces them --
# for a FULL result's hidden-risk-flags / data-limitations sentences (see
# its own "Cảnh báo ẩn: "/"Giới hạn dữ liệu: " lines). Matching on these
# literal prefixes (never position) lets `_split_text_for_wire` below pull
# the exact same, already-computed sentences into `warnings` without
# re-deriving them from `evidence` (which this response drops entirely) or
# guessing at new wording.
_HIDDEN_RISK_TEXT_PREFIX = "Hidden risk: "
_DATA_LIMITATION_TEXT_PREFIX = "Data limitation: "


def _split_text_for_wire(result: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Partition a result's own `text` narrative (data.py's
    `_explanation_vi`/`_not_found_result`/`_limited_fallback_result`/
    `assess_from_error`) into `(remaining_text, warning_lines)`.

    For a FULL result, `_explanation_vi` appends the hidden-risk-flags and
    data-limitations sentences LAST, and only when non-empty (see its own
    body) -- this moves exactly those two lines, verbatim, out of `text`
    and into the return value's second element, so the compact summary's
    `warnings` array carries them ONCE instead of `text` and `warnings`
    both repeating the same (sometimes large -- a bot flagged across many
    QC dimensions can run to a kilobyte here) prose. A LIMITED/NOT_FOUND
    result's own `text` never uses these two prefixes at all (see those
    functions), so for those statuses this is a no-op split -- every line
    stays in `remaining_text`, and `_analyze_warnings_vi` below sources
    their warnings from `limited_reason`/`text` directly instead.

    Only affects the WIRE `text` array this function's caller assembles.
    `report_markdown` is already a fully-rendered string by the time this
    runs (built from the ORIGINAL, unsplit `text` -- see
    `WebDataService.analyze`/`_with_detail_link`), and `GET /bot/<code>` /
    `GET /<userref>_<code>` call `service.analyze()` directly, never through
    this function -- so neither loses these lines.
    """
    remaining: List[str] = []
    warnings: List[str] = []
    for line in result.get("text") or []:
        if isinstance(line, str) and (
            line.startswith(_HIDDEN_RISK_TEXT_PREFIX)
            or line.startswith(_DATA_LIMITATION_TEXT_PREFIX)
        ):
            warnings.append(line)
        else:
            remaining.append(line)
    return remaining, warnings


def _analyze_warnings_vi(result: Dict[str, Any], text_warnings: List[str]) -> List[str]:
    """One flat Vietnamese array merging every "something is off" signal --
    so a summary-only reader learns WHY a `key_metrics` field is `None` or
    a number should be read with caution, without having to fetch the full
    evidence blob this response no longer carries.

    `text_warnings` (the hidden-risk-flags/data-limitations lines
    `_split_text_for_wire` above already pulled out of `text`) covers the
    FULL case. LIMITED/NOT_FOUND never produce those two lines at all, so
    they are covered separately here instead, straight from data this
    response already carries elsewhere (`limited_reason`, `text`) --
    deliberately never a freshly-worded sentence, so this can never say
    something the rest of the response does not already substantiate.
    """
    warnings = list(text_warnings)
    status = result.get("status")
    if status == "LIMITED":
        reason = result.get("limited_reason")
        if reason:
            warnings.append(reason)
    elif status == "NOT_FOUND":
        # `text` for a NOT_FOUND result is exactly the one Vietnamese
        # sentence explaining why (see data.py's `_not_found_result`) -- no
        # separate structured reason exists to pull from instead, and it is
        # short enough that duplicating it here (unlike the FULL case
        # above) never threatens the size budget.
        warnings.extend(result.get("text") or [])
    elif status == "FULL":
        # Việc 2d: nguyên tắc cốt lõi của dự án -- thiếu dữ liệu không bao
        # giờ được im lặng cho qua. `evidence.primary_share_pct` (Việc 2, xem
        # data.py's `assessment_to_analyze_result`/`_full_result`) là tỉ
        # trọng giá trị giao dịch của CHÍNH thị trường vừa được chấm; dưới
        # 60% nghĩa là các chiều phụ thuộc thị trường (market_alignment,
        # liquidity_execution, leverage_exposure) chỉ soi được một phần hoạt
        # động thật của bot -- phần còn lại CHƯA được chấm ở đây. `None`
        # (chưa đo được, hoặc file cũ ghi trước khi Việc 2 tồn tại) không
        # tạo cảnh báo -- im lặng ở đây là "không có gì để nói", không phải
        # "giấu thiếu sót".
        evidence = result.get("evidence")
        evidence = evidence if isinstance(evidence, dict) else {}
        share_pct = evidence.get("primary_share_pct")
        if isinstance(share_pct, (int, float)) and share_pct < 60:
            symbol = evidence.get("traded_symbol") or result.get("code") or "?"
            warnings.append(
                f"The scored market ({symbol}) accounts for only {share_pct:.0f}% of "
                "the bot's trading value -- the market_alignment, liquidity_execution "
                "and leverage_exposure dimensions are scored only on this share; the "
                "rest of the bot's activity has NOT been examined."
            )
    return warnings


def _string_list_for_wire(value):
    """Luôn trả về list[str] sạch -- dữ liệu cũ có thể thiếu khoá này."""
    if not isinstance(value, list):
        return []
    return [v for v in value if isinstance(v, str) and v.strip()]


# Câu giải thích đi kèm mỗi nhãn kết luận.
#
# Viết theo từ vựng chuẩn của tài chính định lượng (lỗ chưa thực hiện, đánh dấu
# theo giá thị trường, sụt vốn tối đa, kiểm định ngoài mẫu, chu kỳ thị trường)
# nhưng mỗi thuật ngữ đều được nói lại bằng lời thường ngay trong câu -- người
# đọc chuyên nghiệp nhận ra thuật ngữ, người đọc thường vẫn hiểu nghĩa, không ai
# phải tra từ điển.
VERDICT_MEANING_VI = {
    "HIDDEN RISK": (
        "Risk that has not yet shown up in the surface numbers. The "
        "published result has not been marked to market -- meaning the "
        "unrealised loss on open positions is not yet counted in -- or the "
        "order book has not been through enough market cycles to be "
        "tested. In that case neither the drawdown probability nor the "
        "quality score is trustworthy yet"
    ),
    "DRAWDOWN: HIGH · QUALITY: GOOD": (
        "The trading edge is well supported -- quality metrics, including a "
        "Sharpe ratio adjusted for sample length and for having been "
        "screened, all pass -- but the outcome distribution has a fat left "
        "tail: the probability of a deep max drawdown is higher than the "
        "group average"
    ),
    "DRAWDOWN: HIGH · QUALITY: WEAK": (
        "High probability of a deep drawdown, with no statistical evidence "
        "of a durable edge: the Sharpe ratio does not hold up once adjusted "
        "for sample length and for this bot having been picked out of many "
        "candidates"
    ),
    "DRAWDOWN: LOW · QUALITY: GOOD": (
        "Low probability of a deep drawdown and a trading edge that holds "
        "up after adjustment -- the most favourable risk/reward profile on "
        "this scale"
    ),
    "DRAWDOWN: LOW · QUALITY: WEAK": (
        "Both volatility and drawdown are low, but there is no statistical "
        "evidence of an edge yet: the expected return cannot be told apart "
        "from noise. Low risk does not mean profitable"
    ),
    "INSUFFICIENT EVIDENCE": (
        "The public sample has not yet reached the minimum length for a "
        "Sharpe ratio to be statistically meaningful (Minimum Track Record "
        "Length), so the system declares it missing rather than guessing"
    ),
}


def _verdict_reason_vi(verdict, hidden_flags):
    """Một câu đọc là hiểu, đi kèm nhãn kết luận.

    Nhãn "HIDDEN RISK" tự nó không nói được gì với người mua: bốn chữ đó
    không cho biết cái gì đang bị che. Với nhãn này, câu giải thích phải kèm
    ĐÚNG những dấu hiệu đã kích hoạt nó (ví dụ "lỗ chưa chốt bằng 43% vốn",
    "chốt hết sổ mở thì profit factor rơi từ 1.09 xuống 0.27") -- đó mới là
    phần thuyết phục, còn cái nhãn chỉ là cách gọi tên.
    """
    base = VERDICT_MEANING_VI.get(verdict)
    if base is None:
        return None
    flags = [f for f in (hidden_flags or []) if isinstance(f, str) and f.strip()]
    if flags:
        return f"{base}. Specifically: " + "; ".join(flags) + "."
    return base + "."


def _analyze_summary_for_wire(result: Dict[str, Any]) -> Dict[str, Any]:
    """Return the compact `bot_assessment_summary.v1` shape POST/GET
    /api/analyze actually responds with, built from `service.analyze()`'s
    full internal result -- see this section's own module-level comment for
    the size measurement and the "wire-only trim" guarantee.

    Every existing top-level key (`status`, `code`, `name`, `verdict`,
    `verdict_basis`, `risk`, `quality`, `confidence`, `limited_reason`,
    `unavailable`, `narrative`, `report_markdown`, and `report_url` when
    present) is copied through UNCHANGED -- `narrative`
    (Agent/backend/qc/reporting/narrative.py) is `None` unless the operator
    opted into the feature, a short static Vietnamese fallback sentence if
    it was attempted but degraded, or the gate-validated LLM paragraph
    otherwise; see `ANALYZE_SUMMARY_SIZE_BUDGET_CHARS`'s own comment for
    why this field's worst-case length was budgeted for here. Only
    `evidence`, `mc` and `assets` are dropped, and `text` is replaced by
    `_split_text_for_wire`'s own trimmed
    copy (see its docstring for why: FULL's hidden-risk/data-limitation
    sentences move into `warnings` instead of also staying duplicated here).
    `verdict_basis` (the sentence answering "sở cứ ở đâu" for the verdict
    label -- rho 0.64, 95% CI [0.39, 0.80], see
    `Agent/backend/qc/scoring/verdict.py`'s `VERDICT_BASIS_VI`) is kept for
    EVERY status, not just FULL: `_empty_result` (data.py) already sets it
    to `None` for LIMITED/NOT_FOUND, so the key is always present and never
    fabricated for a status that has no basis to report. It used to be
    dropped here to save ~200 bytes against an earlier, stricter size
    budget -- see `ANALYZE_SUMMARY_SIZE_BUDGET_CHARS` below for why that
    trade was wrong and got reverted. The derived
    `schema`/`traded_symbol`/`key_metrics`/`score_decided_by`/
    `veto_reasons`/`warnings` fields are added on top. Building a fresh
    top-level dict via `dict.items()` (rather than `dict(result)` followed
    by `del`) both keeps `result` itself completely unread-from-mutated and
    makes the drop list impossible to miss on a future key addition to
    `_full_result`: a new key there is copied through automatically unless
    explicitly excluded here.

    Must run AFTER `_with_detail_link` in api_analyze, not before: that
    function re-renders `report_markdown` from the FULL `evidence`/`mc`/
    `text` (its "## Số liệu chính"/"## Mô phỏng"/"## Vì sao" sections)
    whenever a session's detail link changes it, so this trim can only
    happen once that rendering is done -- trimming first would silently
    blank those sections out of `report_markdown` for a logged-in caller.
    """
    evidence = result.get("evidence")
    evidence = evidence if isinstance(evidence, dict) else {}
    mc = result.get("mc")
    decided_by, veto_reasons = _score_governance_from_evidence(evidence)
    remaining_text, text_warnings = _split_text_for_wire(result)
    summary = {
        key: value
        for key, value in result.items()
        # "evidence"/"mc"/"assets" are the raw internals this reshape exists
        # to drop (see this section's module-level comment). "verdict_basis"
        # is deliberately NOT in this exclusion list: it is the one sentence
        # answering "sở cứ ở đâu" for the verdict label above, and dropping
        # it to save space was the wrong trade (see
        # ANALYZE_SUMMARY_SIZE_BUDGET_CHARS's own comment) -- it is copied
        # through unchanged like every other top-level key, `None` for
        # LIMITED/NOT_FOUND (see data.py's `_empty_result`) exactly like
        # `verdict`/`risk`/`quality` already are for those statuses.
        if key not in ("evidence", "mc", "assets", "text")
    }
    summary["text"] = remaining_text
    summary["schema"] = ANALYZE_SUMMARY_SCHEMA
    summary["traded_symbol"] = evidence.get("traded_symbol")
    summary["key_metrics"] = _key_metrics_from_evidence(evidence, mc)
    summary["score_decided_by"] = decided_by
    summary["veto_reasons"] = veto_reasons
    hidden_flags = _string_list_for_wire(
        (evidence.get("score_breakdown") or {}).get("hidden_risk_flags")
    )
    summary["hidden_risk_flags"] = hidden_flags
    summary.setdefault("usage_contract_id", None)
    summary["verdict_reason"] = _verdict_reason_vi(summary.get("verdict"), hidden_flags)
    summary["strategy_profile"] = _strategy_profile_from_evidence(evidence)
    summary["warnings"] = _analyze_warnings_vi(result, text_warnings)
    return summary


def create_app(
    *,
    dashboard_path: Optional[Path] = None,
    data_service: Optional[WebDataService] = None,
    rate_limiter: Optional[PerIpRateLimiter] = None,
    admin_rate_limiter: Optional[PerIpRateLimiter] = None,
    users_root: Optional[Path] = None,
    usage_refs_root: Optional[Path] = None,
    now_fn: Callable[[], float] = time.time,
) -> Starlette:
    """Build the Starlette app. Every dependency is injectable so tests can
    swap in a `WebDataService` wired to fakes instead of real OKX/disk
    access (see Agent/test/test_web_app.py). `users_root` is the same kind
    of injectable default as `dashboard_path` above -- it overrides
    `Agent/backend/web/identity.py`'s `DEFAULT_USERS_ROOT` so tests never
    read/write this project's real `data/users/` directory. `usage_refs_root`
    is the exact same pattern for `Agent/backend/web/usage_ref.py`'s
    `DEFAULT_USAGE_REFS_ROOT` (Việc 2's anonymous-caller usage-ref store) --
    a separate knob, never folded into `users_root`, because the two stores
    are deliberately kept apart on disk (see usage_ref.py's own module
    docstring for why).

    `now_fn` is the wall-clock source used ONLY to stamp a freshly-computed
    `GET /bot/<code>`/`GET /<userref>_<code>` result with its
    `snapshot_at_ms` (see `_bot_report_response`/`Agent/backend/web/
    snapshot.py`) -- injectable so a test can pin it to a fixed value
    instead of depending on real wall-clock time (e.g. comparing two
    renders of the same code for byte-for-byte equality, where two real
    `time.time()` calls could legitimately land in different milliseconds).
    Defaults to the real clock, unchanged from this module's behaviour
    before this parameter existed.
    """
    service = data_service or WebDataService()
    # Tham chiếu MẠNH tới mọi task nền vượt hạn `ANALYZE_SYNC_DEADLINE_SECONDS`
    # -- xem `_track_background_analyze_task` bên dưới cho lý do bắt buộc
    # phải có tập hợp này (asyncio chỉ giữ weak reference tới Task, một task
    # không còn ai giữ có thể bị dọn giữa chừng bất cứ lúc nào). Sống theo
    # đúng vòng đời của app instance này (một `create_app()` = một service
    # thật, hoặc một app riêng cho mỗi test) -- không phải biến module-level
    # dùng chung, nên hai `create_app()` khác nhau (hai test) không bao giờ
    # thấy task nền của nhau.
    background_analyze_tasks: set = set()
    # Sửa lỗi treo >60s (plan_progress.md mục C, xem
    # `BOT_REPORT_AWAIT_LIVE_TASK_TIMEOUT_SECONDS`'s comment cho toàn bộ lý
    # do) -- map mã -> task `_resolve_and_analyze` ĐANG BAY cho đúng mã đó,
    # để `_bot_report_response` (GET /bot/<code>) có thể AWAIT nó thay vì tự
    # khởi động một lượt phân tích thứ hai song song. Gắn vào NGAY khi task
    # được tạo (`_analyze_body_stream` bên dưới), không chỉ khi
    # `ANALYZE_SYNC_DEADLINE_SECONDS` nổ -- khác `background_analyze_tasks`
    # ở trên (chỉ giữ tham chiếu MẠNH chống garbage-collect cho task VƯỢT
    # hạn), map này tồn tại để TRA CỨU theo mã, sống trong SUỐT vòng đời của
    # task (từ lúc tạo tới lúc xong), không chỉ phần vượt hạn. Tự dọn khi
    # task xong (xem done-callback tại nơi gắn) -- không bao giờ phình theo
    # thời gian sống của process. Hai `_analyze_body_stream` khác nhau cho
    # CÙNG một mã (hiếm, hai request gần như đồng thời) thì bản ghi sau ghi
    # đè bản ghi trước -- done-callback của task cũ chỉ tự xoá đúng bản ghi
    # của CHÍNH NÓ (kiểm tra danh tính bằng `is`), không bao giờ xoá nhầm
    # task mới hơn.
    live_analyze_tasks: Dict[str, "asyncio.Task[Dict[str, Any]]"] = {}
    # Đếm số `_run_live_analyze` (OKX + Monte Carlo 10k, CPU-nặng) đang THẬT
    # SỰ chạy đồng thời, app-instance này -- xem
    # `ANALYZE_MAX_CONCURRENT_LIVE_ANALYSES`'s comment cho toàn bộ lý do
    # trần này tồn tại, và `_resolve_and_analyze` cho nơi tăng/giảm nó.
    # Một `int` đơn giản, không phải `asyncio.Semaphore`: mọi lần đọc/so
    # sánh/tăng nó trong `_resolve_and_analyze` đều nằm giữa hai điểm
    # `await` (không có await nào xen giữa lúc kiểm tra và lúc tăng), nên
    # asyncio's cooperative scheduling (một luồng duy nhất, không bao giờ
    # ngắt ngang một đoạn code đồng bộ giữa chừng) tự đảm bảo không có race
    # condition nào giữa hai request tới gần như đồng thời -- không cần
    # khoá riêng.
    live_analyze_in_flight = 0
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
    # Việc 2: static JS/CSS bundle for the SPA, always the sibling `assets/`
    # directory next to whichever `index.html` this app instance is
    # serving -- Vite's own `build.outDir` (Agent/frontend/vite.config.js)
    # always emits exactly this layout (`dist/index.html` + `dist/assets/`),
    # so deriving this from `dash_path` rather than a second independent
    # default keeps a `--dashboard`/`NORABT_WEB_DASHBOARD` override
    # relocating BOTH files together instead of silently splitting them.
    assets_dir = dash_path.parent / "assets"
    users_dir = (
        Path(users_root) if users_root is not None else identity.DEFAULT_USERS_ROOT
    )
    usage_refs_dir = (
        Path(usage_refs_root)
        if usage_refs_root is not None
        else usage_ref.DEFAULT_USAGE_REFS_ROOT
    )
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
            bots = await run_in_threadpool(service.list_bot_rows)
        except Exception as exc:  # noqa: BLE001 - disk I/O; never bubble a traceback
            incident_code = _log_incident("GET /api/bots", exc)
            return _error_json(_generic_error_message(incident_code), 500)
        return JSONResponse({"bots": bots, "count": len(bots)})

    async def api_config(request: Request) -> Response:
        """GET /api/config -- see this module's own top-of-file docstring
        for the full contract. Never raises (a single env-var read), so
        this is deliberately not wrapped in the try/except every other
        route here uses for its own disk/network-touching work.
        """
        return JSONResponse({"admin_open_access": _admin_open_access()})

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

    def _finish_analyze_result(
        result: Dict[str, Any],
        scored_at_ms: Optional[int],
        code: str,
        request: Request,
        is_admin: bool,
    ) -> Dict[str, Any]:
        """Turn a raw scored `result` (from the Redis snapshot, a
        pre-scored `assessment.json`, or a fresh `service.analyze()` call --
        `api_analyze` itself no longer cares which) into the exact wire
        shape `POST /api/analyze` responds with: the detail link/usage-ref
        bookkeeping, the compact-summary trim, the 24h staleness warning,
        and the admin `access_level` marker.

        Deliberately kept a plain SYNCHRONOUS function (not `async def`) so
        every caller decides for itself how to run it -- see below for why
        that decision now always has to be "via `run_in_threadpool`", never
        directly on the event loop.

        KHÔNG "rẻ" như dòng docstring cũ ở đây từng khẳng định ("one small
        local file write... side-effect-light"): đo thật (project owner,
        2026-09-17) qua chính `okx_journey.sh` cho thấy tổng thời gian một
        lượt `/api/analyze` có thể giãn ra 12-21s dù byte đầu vẫn bay đi
        ngay và bản thân đồng hồ hạn `ANALYZE_SYNC_DEADLINE_SECONDS` vẫn nổ
        đúng giờ nội bộ (đếm byte đệm heartbeat xác nhận điều này) -- nguyên
        nhân là `usage_ref.mint_usage_ref` (gọi bên dưới, nhánh ẩn danh) tự
        gọi `_prune`, mà `_prune` (Agent/backend/web/usage_ref.py, file
        module này KHÔNG được sửa) quét (`glob`) VÀ ĐỌC TỪNG FILE trong
        toàn bộ thư mục usage-ref mỗi lần đúc một mã mới -- một thao tác
        I/O đồng bộ, phát triển tuyến tính theo số file tích luỹ (đo thật:
        88 file một lượt, con số CHỈ TĂNG theo lưu lượng thật), chạy TRỰC
        TIẾP trên event loop nếu gọi hàm này không qua threadpool. Vì
        process này chỉ có MỘT event loop dùng chung cho MỌI request đang
        xử lý đồng thời, một lượt gọi hàm này bị chặn đồng bộ vài trăm ms
        tới vài giây sẽ làm TRỄ luôn heartbeat/byte cuối cùng của MỌI
        request khác đang chờ trên cùng event loop đó -- kể cả những request
        đã tính toán xong và chỉ còn chờ được "gửi đi". Đây là bug thật,
        không phải giả thuyết: số byte đệm heartbeat đo được KHÔNG đổi giữa
        lượt trả nhanh (~8.0s) và lượt trả chậm (12-21s), chứng minh đồng hồ
        hạn nội bộ vẫn đúng giờ -- chỉ có việc PHÁT byte cuối cùng ra socket
        là bị trễ.

        SỬA (trong phạm vi CHỈ file này được phép động tới): mọi caller bên
        dưới giờ gọi hàm này qua `run_in_threadpool`, không bao giờ trực
        tiếp trên event loop nữa -- dời việc quét/đọc file đó sang một luồng
        threadpool riêng, giống hệt cách `service.analyze`/`service.
        find_scored_report` đã được đối xử trong cùng file này từ trước.
        Điều này không sửa được bản chất "quét toàn bộ thư mục mỗi lần đúc
        mã" của `_prune` (nằm ngoài phạm vi sửa của module này), nhưng loại
        bỏ đúng phần nguy hiểm nhất: một request TRỄ vì lý do RIÊNG của nó
        không còn kéo theo MỌI request khác cùng lúc bị trễ theo.
        """
        # Việc 1: sao một bản MỚI trước khi thêm bất kỳ khoá nào -- `result`
        # ở đây có thể là chính object `service._analyze_cache` đang giữ
        # (nhánh live), hoặc object Redis snapshot vừa parse (nhánh cache) --
        # KHÔNG BAO GIỜ được sửa trực tiếp lên object gốc đó (cùng lý do
        # `_with_detail_link` bên dưới đã tự sao chép cho chính nó): hai
        # caller khác nhau cùng trúng một cache trong TTL của nó phải mỗi
        # người thấy đúng `scored_at_ms`/`report_url` của RIÊNG lượt gọi của
        # họ, không phải bị người gọi trước ghi đè lên.
        result = dict(result)
        # `find_scored_report`'s reshape (assessment.json -> dict) không tự
        # gắn `report_markdown`/`report_url` như `service.analyze()` đã làm
        # cho nhánh live/snapshot -- gắn thêm ở đây để hình dạng JSON trả về
        # KHÔNG đổi một khoá nào giữa hai nhánh (test
        # test_analyze_from_disk_has_same_key_set_as_live khoá chặt điều
        # này).
        if "report_markdown" not in result:
            result["report_markdown"] = build_report_markdown(result)
        if report_url_is_usable() and "report_url" not in result:
            result["report_url"] = build_report_url(code)
        result["scored_at_ms"] = scored_at_ms

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
        #   * an admin-authenticated request (token OR admin session) -> the
        #     plain `/bot/<code>` link -- admin already has unrestricted
        #     access to that still-open route, so hiding it behind a
        #     usage-ref would add nothing (task's own explicit "Admin giữ
        #     /bot/<code>" instruction).
        #   * no session and not admin (Việc 2: this is the common case for
        #     the OKX Marketplace's own machine-to-machine callers -- OKX's
        #     onchainos CLI has been measured to forward ONLY
        #     `typedParams={"code": ...}` to this endpoint, no
        #     `confirmationId`, no identifying header at all, see this
        #     module's own top-of-file docstring) -> a freshly-minted,
        #     single-purpose usage ref (`usage_ref.mint_usage_ref`), never
        #     the guessable `/bot/<code>` and never a real user's `user_ref`
        #     either. A NEW ref every single successful call, even for the
        #     exact same `code` twice in a row -- "mỗi lượt dùng một mã
        #     riêng" is the task's own explicit requirement, not an
        #     accidental side effect of caching.
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
        # Mã hợp đồng sử dụng: định danh DUY NHẤT cho lượt dùng này.
        #
        # Dịch vụ đang miễn phí nên OKX không tạo đơn hàng, và đã đo được là
        # CLI của họ không chuyển `confirmationId` hay bất kỳ header định danh
        # nào xuống endpoint -- nghĩa là phía máy chủ không có cách nào biết ai
        # vừa gọi. Vì vậy mỗi lượt dùng tự sinh một mã riêng: nó vừa là phần
        # định danh trong đường dẫn ẩn, vừa là thứ người dùng giữ lại để đối
        # chiếu về sau, đúng vai trò một mã hợp đồng sử dụng. Mã mới cho MỖI
        # lượt, kể cả gọi lại cùng một bot, và mã chỉ mở đúng bot mà nó được
        # cấp cho.
        usage_contract_id: Optional[str] = None
        if report_url_is_usable():
            if session_user_ref:
                detail_url = f"{report_base_url()}/{session_user_ref}_{code}"
            elif is_admin:
                detail_url = build_report_url(code)
            else:
                minted_ref = usage_ref.mint_usage_ref(code, root=usage_refs_dir)
                detail_url = f"{report_base_url()}/{minted_ref}_{code}"
                usage_contract_id = minted_ref
        result = _with_detail_link(result, detail_url)

        # Compact-summary trim (project owner's measured ruling -- see
        # `_analyze_summary_for_wire`'s own module-level comment): must run
        # AFTER `_with_detail_link` above, since that function still needs
        # the FULL `evidence`/`mc` to re-render `report_markdown`'s
        # "Số liệu chính"/"Mô phỏng" sections. From here on `result` is the
        # `bot_assessment_summary.v1` wire shape -- `evidence`/`mc`/`assets`
        # are gone, replaced by `schema`/`traded_symbol`/`key_metrics`/
        # `score_decided_by`/`veto_reasons`/`warnings`. This is a NEW dict,
        # never the shared analyze_cache object itself (same non-mutation
        # guarantee `_with_detail_link` already relies on) -- so a later
        # GET /bot/<code> or GET /<userref>_<code> for the SAME cached code
        # still calls `service.analyze()` directly and gets the untouched
        # full object; nothing above ever altered it.
        result = _analyze_summary_for_wire(result)
        result["usage_contract_id"] = usage_contract_id

        # Việc 1: người mua trên OKX cần biết họ đang xem số liệu chấm điểm
        # LÚC NÀO -- `scored_at_ms` (đã gắn vào `result` trước
        # `_with_detail_link`/`_analyze_summary_for_wire` ở trên, nên sống
        # sót qua cả hai bước reshape đó như mọi khoá top-level khác) có thể
        # cũ hơn nhiều so với "vừa mới chấm" khi nó đến từ tầng
        # find_scored_report/snapshot phía trên (một `assessment.json` có
        # thể đã nằm trên đĩa hàng ngày, hàng tuần). Ngưỡng dùng lại đúng
        # `snapshot.SNAPSHOT_TTL_SECONDS` (24h) -- cùng ngưỡng "stale" trang
        # HTML `GET /bot/<code>`/`GET /<userref>_<code>` đã hiển thị cho
        # người dùng (xem `_bot_report_response`'s `is_stale`), để hai bề
        # mặt không tự mâu thuẫn nhau về "thế nào là cũ" cho cùng một bot.
        if (
            scored_at_ms is not None
            and int(now_fn() * 1000) - scored_at_ms
            > snapshot.SNAPSHOT_TTL_SECONDS * 1000
        ):
            result["warnings"] = list(result.get("warnings") or []) + [
                "This scored data is more than 24 hours old -- it may not "
                "reflect the bot's latest trading state."
            ]

        # `access_level: "admin"` is the one visible signal a caller gets
        # that their admin key actually worked (task's own requirement) --
        # ONLY added for an admin-authenticated request, never for an
        # ordinary token or open-mode caller, so every non-admin caller of
        # this same summary shape keeps seeing exactly the keys they always
        # have (see Agent/test/test_web_app.py's own ANALYZE_SUMMARY_KEYS
        # set). Built as a copy here rather than mutating `result` in
        # place, for the same reason as above: a different, non-admin
        # caller must never see this key leak into THEIR response for the
        # same cached code.
        if is_admin:
            result = dict(result)
            result["access_level"] = "admin"
        return result

    def _analyze_error_body(message: str) -> Dict[str, Any]:
        """Hình dạng JSON GIỐNG HỆT `_error_json` (`{"status": "ERROR",
        "message": ...}`) nhưng không kèm mã trạng thái HTTP -- dùng cho hai
        nhánh lỗi cực hiếm bên trong `_run_live_analyze` (InvalidCodeError
        gần như không thể xảy ra vì `validate_unique_code` đã lọc từ trước,
        và một Exception bất kỳ ở tầng "phòng thủ cuối cùng"). Một khi
        `_analyze_body_stream` đã bắt đầu phát nhịp tim, response coi như đã
        CHỐT HTTP 200 ở tầng giao thức (header đã gửi, không thể đổi status
        code giữa chừng) -- đây là đánh đổi có chủ đích để đổi lấy việc giữ
        kết nối sống qua ngưỡng ~10s CLI của OKX tự ý cắt (xem
        ANALYZE_HEARTBEAT_INTERVAL_SECONDS), không phải một sơ suất che
        giấu lỗi: `message` vẫn nói đúng sự thật, chỉ là gói trong thân JSON
        thay vì mã trạng thái.
        """
        return {"status": "ERROR", "message": message}

    async def _run_live_analyze(
        code: str, request: Request, is_admin: bool, force: bool = False
    ) -> Dict[str, Any]:
        """Toàn bộ phần việc NẶNG của nhánh "chưa từng chấm": gọi
        `service.analyze()` (OKX + Monte Carlo 10k + narrative tuỳ chọn,
        có thể mất 15-70s) rồi chạy tiếp `_finish_analyze_result`. Chỉ được
        gọi từ `_resolve_and_analyze` bên dưới (SAU khi snapshot Redis/
        `find_scored_report` trên đĩa đã đều MISS) -- tách riêng khỏi
        `api_analyze` để `_analyze_body_stream` có thể chạy toàn bộ chuỗi
        `_resolve_and_analyze` như MỘT task nền song song với vòng lặp phát
        nhịp tim, VÀ để nó có thể tiếp tục sống sau khi `_analyze_body_stream`
        đã bỏ cuộc chờ vì chạm `ANALYZE_SYNC_DEADLINE_SECONDS` (xem
        `_track_background_analyze_task` bên dưới) -- kết quả cuối cùng của
        lời gọi này vẫn tự chảy vào đúng chỗ `POST /api/analyze` một lượt
        gọi SAU đó đọc lại (`service._analyze_cache`, xem `WebDataService.
        analyze`'s docstring), không cần biết gì về việc response ĐẦU TIÊN
        đã trả PENDING hay chưa.

        SỬA (đo thật, project owner 2026-09-17): `service._analyze_cache`
        ở trên là cache TTL 180s NẰM TRONG PROCESS -- nhưng `GET /bot/<code>`/
        `GET /<userref>_<code>` (`_bot_report_response` bên dưới) không hề
        đọc nó. Đường đọc của trang chi tiết là snapshot Redis ->
        `find_scored_report` trên đĩa -> MỚI tới `service.analyze()` sống.
        Với một bot CHƯA từng chấm (không có assessment.json), snapshot
        Redis cũng chưa từng được ghi cho nó (`_bot_report_response` chỉ tự
        ghi snapshot SAU KHI chính nó chạy sống, xem hàm đó) -- nên một
        request `/api/analyze` vừa chấm xong bot này Ở NỀN không để lại dấu
        vết nào ở hai tầng đầu trang chi tiết đọc, và cú click đầu tiên vào
        `report_url` luôn rơi thẳng xuống nhánh sống, CHẠY LẠI toàn bộ
        pipeline từ đầu (đo thật: bot D387B5B1F098B82C, 69.9s dù nền đã
        xong ~90s trước đó, trong khi gọi lại `/api/analyze` cho đúng mã đó
        chỉ mất 0.326s nhờ trúng `_analyze_cache`). Ghi thẳng kết quả vừa
        chấm xong này vào snapshot Redis ngay dưới đây -- đúng khuôn/TTL
        `snapshot.py` tự định nghĩa (24h, không phải 180s của
        `_analyze_cache`), và đúng chỗ tầng ĐẦU TIÊN của `_bot_report_
        response` đã đọc -- là cách tối thiểu để kết quả nền "chảy" tới
        đúng đường trang chi tiết đi qua, thay vì phải chờ trùng ngẫu nhiên
        vào cửa sổ 180s của một cache khác hẳn.
        """
        try:
            # `progress=...`: xem plan_progress.md mục A/B -- mark() từng
            # chặng THẬT ("ledger"/"markets"/"scoring"/"decision"/
            # "narrative", xem pipeline.py/data.py cho nơi mỗi chặng thật sự
            # được bắn) vào registry của đúng `code` này, để `GET
            # /api/analyze/status` đọc lại được. Lambda chạy TRÊN worker
            # thread của threadpool (cùng thread chạy service.analyze()
            # chính nó), không phải trên event loop -- đúng lý do
            # `progress.py` phải tự khoá bằng `threading.Lock`, không dựa
            # vào asyncio's single-threaded scheduling.
            result = await run_in_threadpool(
                service.analyze,
                code,
                force,
                lambda stage: analyze_progress.mark(code, stage),
            )
        except InvalidCodeError as exc:
            # Safety net only: validate_unique_code above already rejects a
            # badly-formatted code the exact same way service.analyze()
            # itself would, so this should be unreachable in practice -- kept
            # in case the two checks ever drift apart from each other.
            return _analyze_error_body(str(exc))
        except Exception as exc:  # noqa: BLE001 - last line of defence, see module docstring
            incident_code = _log_incident("POST /api/analyze", exc)
            return _analyze_error_body(_generic_error_message(incident_code))
        # Việc 1: "thời điểm chấm" của nhánh live là lúc request này THẬT
        # SỰ chạy xong pipeline -- cùng cách `_bot_report_response` stamp
        # `snapshot_at_ms` ngay sau lời gọi `service.analyze` sống của nó
        # (dù bản thân service.analyze() có thể trả một kết quả vừa được
        # cache trong 180s gần nhất từ MỘT request khác -- không phân
        # biệt được, và không cần phân biệt, ở tầng này).
        scored_at_ms = int(now_fn() * 1000)
        # Ghi vào snapshot Redis NGAY TẠI ĐÂY -- xem docstring ở trên cho lý
        # do đầy đủ. `result` ở đây là dict ĐẦY ĐỦ `service.analyze()` vừa
        # trả (evidence/mc/assets nguyên vẹn, CHƯA qua `_finish_analyze_
        # result`/`_analyze_summary_for_wire` bên dưới cắt gọn cho JSON API)
        # -- đúng hình dạng `_bot_report_response`/`render_bot_report_html`
        # cần, và đúng hình dạng snapshot.py's `get_snapshot` mong đợi khi
        # đọc lại (xem `_bot_report_response`'s nhánh live, cũng ghi
        # nguyên `result` này chứ không phải bản đã cắt gọn).
        # `snapshot.set_snapshot` không bao giờ raise, tự bọc bởi timeout
        # ngắn của chính nó (0.5s connect + 0.5s socket, xem module
        # docstring) -- Redis chưa cấu hình hoặc đang chết chỉ khiến dòng
        # này thành no-op im lặng, không làm chậm hay hỏng response nào của
        # hàm này (đúng yêu cầu "hệ thống vẫn chạy khi Redis chết" đã có từ
        # trước, không đổi gì thêm ở đây).
        await snapshot.set_snapshot(code, result, scored_at_ms)
        # `run_in_threadpool` -- xem `_finish_analyze_result`'s docstring
        # (đo thật 2026-09-17) cho lý do hàm này không còn được gọi trực
        # tiếp trên event loop: nó có thể chặn đồng bộ vài giây (quét thư
        # mục usage-ref), điều đó không được phép làm TRỄ heartbeat/byte
        # cuối cùng của MỌI request khác đang chờ trên cùng event loop.
        return await run_in_threadpool(
            _finish_analyze_result, result, scored_at_ms, code, request, is_admin
        )

    async def _resolve_and_analyze(
        code: str, request: Request, is_admin: bool, refresh: bool = False
    ) -> Dict[str, Any]:
        """Toàn bộ phần việc PHÍA SAU byte đệm đầu tiên (`yield b" "`) của
        `_analyze_body_stream`: ba tầng tra cứu, ĐÚNG thứ tự
        `_bot_report_response` (GET /bot/<code>) đã dùng để sửa lỗi 504 của
        chính route đó -- snapshot Redis còn hạn (`snapshot.py`, TTL
        `snapshot.SNAPSHOT_TTL_SECONDS`) -> `assessment.json` đã chấm sẵn
        trên đĩa (`service.find_scored_report`) -> mới thật sự chạy sống
        (`_run_live_analyze`).

        ĐÃ CHUYỂN VÀO ĐÂY (không còn chạy trực tiếp trong `api_analyze` nữa,
        trước khi commit sang streaming) vì đo thật cho thấy hai tầng tưởng
        "rẻ" ở trên (đo riêng chỉ 0.01s) có thể bị giãn ra tới 4.23s khi
        tranh threadpool/CPU với một `service.analyze()` khác đang chạy nền
        từ một lượt PENDING trước đó -- xem `ANALYZE_SYNC_DEADLINE_SECONDS`'s
        comment cho phép đo đầy đủ. Gộp cả ba tầng vào MỘT hàm/MỘT task duy
        nhất để `_analyze_body_stream` chỉ cần bọc heartbeat/hạn cứng quanh
        đúng MỘT task -- hạn cứng đó nhờ vậy bao trùm TOÀN BỘ phần việc này,
        kể cả lúc tra cứu, không chỉ lúc chạy sống.

        Một hệ quả tất yếu (không phải sơ suất): vì `api_analyze` giờ phải
        commit sang streaming TRƯỚC khi biết lượt gọi này sẽ trúng cache hay
        phải chạy sống (xem `ANALYZE_RATE_LIMIT_MAX_REQUESTS`'s comment), một
        mã ĐÃ CHẤM sẵn (cache/disk hit) giờ cũng tốn một suất
        `active_limiter` -- không còn được miễn phí như trước.

        Đo thật TIẾP THEO (project owner, 2026-09-17), sau khi hai tầng
        tra cứu ở trên đã đúng giờ: nhánh "chạy sống" (`_run_live_analyze`)
        bên dưới giờ bị chặn thêm bởi `ANALYZE_MAX_CONCURRENT_LIVE_ANALYSES`
        -- xem hằng số đó cho toàn bộ phép đo (4 mã liên tiếp, mã thứ 4 mất
        27.2s vì đã có 3 tác vụ nền chạy song song từ 3 mã trước). CHỦ ĐÍCH
        chọn "từ chối ngay, không xếp hàng" thay vì một hàng đợi có giới
        hạn: một hàng đợi cần thêm state (vị trí trong hàng, khi nào tới
        lượt) và một cách riêng để hết hạn một request đã CHỜ QUÁ LÂU trong
        hàng mà chưa từng chạy -- hai vấn đề mới, trong khi mục tiêu ở đây
        chỉ đơn giản là "đừng chồng chất thêm việc CPU-nặng khi máy đã bận",
        không phải "đảm bảo mọi request cuối cùng đều được chạy sống". Từ
        chối ngay (giữ đúng tinh thần PENDING đã có sẵn -- không bịa một mã
        trạng thái mới) đơn giản hơn, không có gì để "chờ vô hạn" vì không
        có gì được xếp hàng cả.

        Cũng là nơi mở/chốt bản ghi thanh tiến độ THẬT của
        `Agent/backend/web/progress.py` (plan_progress.md mục B) -- `start()`
        ngay khi hàm này bắt đầu (dù rồi hoá ra là cache/disk hit hay phải
        chạy sống), `finish()`/`fail()` ở đúng chỗ hàm này return/raise, để
        `GET /api/analyze/status` luôn thấy một bản ghi nhất quán với những
        gì `_analyze_body_stream` đang thực sự chờ.
        """
        analyze_progress.start(code)
        if refresh:
            # XOÁ bản chụp cũ, không chỉ bỏ qua nó. Bỏ qua thôi thì bản cũ vẫn
            # nằm trong Redis với TTL 24h và được phục vụ lại ở lượt xem kế
            # tiếp -- đúng thứ người dùng vừa bấm "Phân tích lại" để thay thế.
            await snapshot.delete_snapshot(code)
        if not refresh:
            cached_snapshot = await snapshot.get_snapshot(code)
            if cached_snapshot is not None:
                # run_in_threadpool: xem _finish_analyze_result's docstring.
                result = await run_in_threadpool(
                    _finish_analyze_result,
                    cached_snapshot["result"],
                    cached_snapshot["snapshot_at_ms"],
                    code,
                    request,
                    is_admin,
                )
                analyze_progress.finish(code)
                return result
            scored = await run_in_threadpool(service.find_scored_report, code)
            if scored is not None:
                result, scored_at_ms = scored
                result = await run_in_threadpool(
                    _finish_analyze_result, result, scored_at_ms, code, request, is_admin
                )
                analyze_progress.finish(code)
                return result
        # Một mã CHƯA từng được chấm (bot lạ, chưa ai xem qua) hoặc refresh=True
        # thì rơi thẳng xuống nhánh "live" phía dưới
        nonlocal live_analyze_in_flight
        if live_analyze_in_flight >= ANALYZE_MAX_CONCURRENT_LIVE_ANALYSES:
            # Trần đã đầy -- KHÔNG gọi `_run_live_analyze` (không tăng
            # `live_analyze_in_flight`, không có task nền mới nào được
            # sinh ra cho mã này) -- xem `ANALYZE_OVERLOADED_TEXT_VI`'s
            # comment cho lý do câu chữ phải khác `ANALYZE_PENDING_TEXT_VI`.
            # Trả ngay, KHÔNG chờ tới `ANALYZE_SYNC_DEADLINE_SECONDS`: đằng
            # nào bot này cũng chưa bắt đầu chấm, chờ thêm chỉ tổ giữ kết
            # nối lâu hơn cần thiết mà không đổi được gì.
            #
            # Ghi nhận là "fail" (không phải "finish") trong registry tiến
            # độ: KHÔNG có gì thật sự chạy/xong cho mã này -- một client
            # đang poll status thấy "error" + thông báo quá tải đúng sự
            # thật hơn là "done" (ngụ ý có kết quả để xem).
            analyze_progress.fail(code, ANALYZE_OVERLOADED_TEXT_VI)
            return await run_in_threadpool(
                _finish_analyze_result,
                pending_result(code, [ANALYZE_OVERLOADED_TEXT_VI]),
                None,
                code,
                request,
                is_admin,
            )
        live_analyze_in_flight += 1
        try:
            result = await _run_live_analyze(code, request, is_admin, force=refresh)
            if refresh:
                # Chạy lại phải THAY THẾ bản cũ trên đĩa, không chỉ qua mặt
                # bộ đệm: `find_scored_report` đọc từ đĩa, nên nếu không ghi
                # đè thì sau khi đệm hết hạn hệ thống lại phục vụ đúng kết
                # quả cũ mà người dùng vừa cố ý chạy lại để thay.
                #
                # Chạy ở LUỒNG NỀN và SAU khi đã có kết quả: người dùng không
                # phải chờ thêm, và nếu lượt chấm lại hỏng thì bản cũ vẫn còn
                # nguyên -- xoá trước rồi hỏng sẽ làm bot biến mất khỏi
                # /api/bots (trang danh sách đọc từ đĩa).
                _start_background_rescore(code, service.data_dir)
        except Exception as exc:
            analyze_progress.fail(code, str(exc))
            raise
        else:
            analyze_progress.finish(code)
            return result
        finally:
            # LUÔN chạy dù `_run_live_analyze` thành công, raise, hay (không
            # xảy ra trong thiết kế này, vì task không bao giờ bị `.cancel()`
            # -- xem `_analyze_body_stream`'s comment) bị huỷ -- suất này
            # PHẢI được trả lại để một mã khác đang bị từ chối ở trên có cơ
            # hội chạy sống ở lượt gọi kế tiếp của nó.
            live_analyze_in_flight -= 1

    def _track_background_analyze_task(
        task: "asyncio.Task[Dict[str, Any]]", code: str
    ) -> None:
        """Giữ một tham chiếu MẠNH tới `task` sau khi `_analyze_body_stream`
        đã ngừng `await` nó (hạn cứng `ANALYZE_SYNC_DEADLINE_SECONDS` vừa
        nổ) -- BẮT BUỘC, không phải phòng xa thừa: tài liệu `asyncio.
        ensure_future`/`create_task` nói thẳng "Save a reference to the
        result of this function... A task that isn't referenced elsewhere
        may get garbage collected at any time, even before it's done" --
        vòng lặp heartbeat vốn là nơi giữ tham chiếu đó (biến local `task`
        của generator), một khi generator return (yield xong JSON PENDING)
        thì tham chiếu local đó biến mất, và task hoàn toàn có thể bị dọn
        GIỮA CHỪNG bởi garbage collector trước khi `service.analyze()` chạy
        xong -- kết quả nền sẽ không bao giờ được ghi vào cache, ngược hẳn
        yêu cầu "nền phải chạy tiếp tới khi xong, không rò luồng/tiến trình".

        `background_analyze_tasks` (tập hợp cấp `create_app()`, xem đầu hàm
        đó) là nơi giữ tham chiếu thay thế; `task.add_done_callback` tự dọn
        nó khỏi tập hợp ngay khi xong (thành công hay lỗi), nên tập hợp này
        không bao giờ phình theo thời gian sống của process -- chỉ chứa
        đúng những task đang thật sự chạy dở dang. Một exception bất ngờ
        (hiếm: ví dụ `_finish_analyze_result` bên trong `_resolve_and_
        analyze`/`_run_live_analyze` tự raise, thay vì trả
        `_analyze_error_body` như hai nhánh lỗi đã biết trước) được ghi vào
        log qua `_log_incident` giống mọi nhánh "phòng thủ cuối cùng" khác
        trong module này -- không có ai đang chờ HTTP response để trả lỗi
        cho, nên ghi log là tất cả những gì có thể làm ở đây.
        """
        background_analyze_tasks.add(task)

        def _on_done(finished: "asyncio.Task[Dict[str, Any]]") -> None:
            background_analyze_tasks.discard(finished)
            if finished.cancelled():
                return
            exc = finished.exception()
            if exc is not None:
                _log_incident(f"POST /api/analyze (background, code {code!r})", exc)

        task.add_done_callback(_on_done)

    async def _pending_analyze_body(
        code: str, request: Request, is_admin: bool
    ) -> Dict[str, Any]:
        """Thân JSON trả về NGAY khi `/api/analyze` chạm hạn cứng
        `ANALYZE_SYNC_DEADLINE_SECONDS` -- dù hạn đó nổ vì tra cứu
        snapshot/disk chậm hay vì chính `service.analyze()` chạy sống lâu
        (xem `_resolve_and_analyze`/`ANALYZE_SYNC_DEADLINE_SECONDS`'s
        comment cho toàn bộ bối cảnh). Dựng từ `pending_result` (data.py,
        cùng khuôn `_not_found_
        result`/`_limited_fallback_result`: mọi khoá chấm điểm đều `None`,
        không có gì để bịa) rồi chạy qua ĐÚNG `_finish_analyze_result` mà
        nhánh nhanh/nhánh live đều dùng -- KHÔNG viết một đường build JSON
        riêng cho nhánh này, để hình dạng cuối cùng (schema, report_url,
        report_markdown, detail-link theo session/admin/ẩn danh, ...)
        không thể lệch khỏi hợp đồng `_analyze_summary_for_wire` đã tài
        liệu hoá, dù trạng thái là PENDING hay FULL.

        `scored_at_ms=None`: bot này CHƯA được chấm xong ở thời điểm này --
        khác với FULL/LIMITED/NOT_FOUND (luôn có một mốc thời gian chấm
        thật), truyền `None` ở đây vừa đúng sự thật vừa tự động tắt cảnh
        báo "quá 24h" của `_finish_analyze_result` (điều kiện đó tự bỏ qua
        khi `scored_at_ms is None`) -- một kết quả còn chưa tồn tại thì
        không thể "cũ" được.
        """
        raw = pending_result(code, [ANALYZE_PENDING_TEXT_VI])
        # CHẠY THẲNG trên event loop, KHÔNG qua `run_in_threadpool`.
        #
        # Lý do phải khác nhánh FULL: nhánh PENDING chỉ dựng một thân JSON
        # rỗng điểm số, và phần đắt duy nhất trong `_finish_analyze_result`
        # là `usage_ref.mint_usage_ref` -- đo trực tiếp trong container: 7ms
        # với 101 file. 7ms trên event loop là không đáng kể.
        #
        # Ngược lại, đẩy nó qua threadpool đúng lúc hạn vừa nổ là tự chuốc
        # rủi ro: lúc đó threadpool đang gánh tới 2 `service.analyze` nền,
        # mỗi cái lại tự mở thêm luồng cho giải thị trường song song và dựng
        # pha, nên xin một slot có thể phải XẾP HÀNG. Đo thật qua Cloudflare:
        # cơ chế hạn chạy chính xác (truy vết từng chunk: nhịp tim 2.5s, thân
        # JSON ra đúng 8.02s sau byte đầu, chỉ 10-20ms sau nhịp cuối), nhưng
        # tổng thời gian vẫn vọt lên 11.9-18.1s trong những lượt có phân tích
        # nền chạy kèm -- phần dôi ra nằm đúng ở khâu phát thân JSON cuối,
        # tức SAU khi nội dung đã quyết định xong.
        #
        # Đây là nhánh phải ra nhanh bằng mọi giá: nếu nó trễ quá ~10s thì
        # CLI của OKX ngừng đọc thân và người mua nhận `result` RỖNG -- hỏng
        # hẳn nhưng lại trông như thành công.
        return _finish_analyze_result(raw, None, code, request, is_admin)

    async def _analyze_body_stream(code: str, request: Request, is_admin: bool, refresh: bool = False):
        """Sinh ra TOÀN BỘ thân response `POST /api/analyze` (mọi trạng thái
        -- FULL/LIMITED/NOT_FOUND/PENDING) theo từng khúc (chunked). Đây
        KHÔNG còn là nhánh riêng cho "chưa từng chấm" nữa -- xem
        `api_analyze` bên dưới: sau các cổng rẻ/bắt buộc (cỡ body, token,
        `code`, rate limit), MỌI lượt gọi hợp lệ đều đi qua generator này,
        kể cả một mã đã có sẵn trong Redis snapshot/`assessment.json` trên
        đĩa. Lý do (đo thật, project owner 2026-09-17): byte đầu tiên phải
        bay đi NGAY khi request tới, không phụ thuộc tải -- nhưng chính hai
        tra cứu "rẻ" đó (`snapshot.get_snapshot`/`service.find_scored_
        report`, thực hiện trong `_resolve_and_analyze` bên dưới) lại là thứ
        đo được bị threadpool/CPU của một `service.analyze()` nền khác làm
        giãn ra tới 4.23s -- nên chúng không còn được phép chạy TRƯỚC khi
        commit sang streaming nữa, phải chạy SAU byte đệm `yield b" "` đầu
        tiên này.

        Khoảng trắng gửi đi TRƯỚC khi thân JSON thật bắt đầu là hợp lệ theo
        chuẩn JSON (mọi bộ phân tích, kể cả `serde_json` trong CLI Rust của
        OKX, đều bỏ qua whitespace ở đầu tài liệu) -- nhưng chỉ ở ĐẦU: một
        khi thân JSON thật bắt đầu được yield (dù là kết quả FULL/LIMITED/
        NOT_FOUND thật sự xong kịp, hay thân PENDING vì chạm hạn), vòng lặp
        NGỪNG hẳn, không bao giờ chèn thêm gì xen giữa nữa.

        Nhịp tim một mình (giữ kết nối "sống" qua ngưỡng ~10s CLI tự ý cắt)
        là KHÔNG ĐỦ -- đo thật qua chính CLI OKX (xem
        `ANALYZE_SYNC_DEADLINE_SECONDS`'s comment) cho thấy CLI chỉ thật sự
        ĐỌC THÂN phản hồi trong ~10 giây đó, dù kết nối vẫn "sống": quá hạn
        thì CLI bỏ dở thân JSON dở dang mà không báo lỗi, người mua nhận
        `result` RỖNG. Vì vậy generator này tự chốt một hạn CỨNG
        (`ANALYZE_SYNC_DEADLINE_SECONDS`, luôn dưới ~10s đó) cho chính vòng
        lặp chờ, bắt đầu tính NGAY sau byte đệm đầu tiên -- bao trùm cả ba
        tầng tra cứu lẫn nhánh sống của `_resolve_and_analyze`, không chỉ
        riêng nhánh sống như trước: chạm hạn mà `task` vẫn chưa xong thì
        KHÔNG chờ thêm nữa -- trả ngay thân PENDING (`_pending_analyze_
        body`) và giao `task` cho `_track_background_analyze_task` để nó
        tiếp tục chạy độc lập với generator này (đã return).
        """
        analyze_progress.start(code)
        task: "asyncio.Task[Dict[str, Any]]" = asyncio.ensure_future(
            _resolve_and_analyze(code, request, is_admin, refresh=refresh)
        )
        # Sửa lỗi treo >60s (plan_progress.md mục C, xem
        # `BOT_REPORT_AWAIT_LIVE_TASK_TIMEOUT_SECONDS`'s comment) -- đăng ký
        # NGAY khi task được tạo, không chờ tới lúc hạn cứng nổ (khác
        # `_track_background_analyze_task` bên dưới, chỉ giữ tham chiếu
        # chống garbage-collect SAU khi hạn nổ): `_bot_report_response`
        # (GET /bot/<code>) cần thấy task này NGAY LẬP TỨC, kể cả khi nó
        # còn đang chạy tầng tra cứu rẻ đầu tiên, để không bao giờ tự khởi
        # động một lượt phân tích thứ hai song song cho cùng mã.
        live_analyze_tasks[code] = task

        def _clear_live_task(
            finished: "asyncio.Task[Dict[str, Any]]", _code: str = code
        ) -> None:
            # Chỉ xoá đúng bản ghi của CHÍNH task này -- nếu một
            # `_analyze_body_stream` khác cho CÙNG mã đã ghi đè bằng task
            # MỚI hơn trong lúc task này còn chạy (hiếm: hai request gần
            # như đồng thời), so sánh bằng `is` đảm bảo done-callback của
            # task CŨ không xoá nhầm task MỚI khỏi map.
            if live_analyze_tasks.get(_code) is finished:
                live_analyze_tasks.pop(_code, None)

        task.add_done_callback(_clear_live_task)
        yield b" "
        deadline_at = time.monotonic() + ANALYZE_SYNC_DEADLINE_SECONDS
        while True:
            remaining = deadline_at - time.monotonic()
            if task.done() or remaining <= 0:
                break
            await asyncio.wait(
                {task}, timeout=min(ANALYZE_HEARTBEAT_INTERVAL_SECONDS, remaining)
            )
            if not task.done():
                yield b" "
        if task.done():
            body = task.result()
        else:
            # Hạn cứng vừa nổ trước khi `task` xong -- KHÔNG huỷ nó
            # (`task.cancel()` sẽ giết luôn `service.analyze()` đang chạy
            # trong threadpool, đúng thứ yêu cầu nói KHÔNG được làm): giao
            # nó cho tập hợp tham chiếu-mạnh cấp app để nó chạy tiếp tới
            # khi xong, rồi trả PENDING ngay bây giờ.
            _track_background_analyze_task(task, code)
            body = await _pending_analyze_body(code, request, is_admin)
        # Dùng lại đúng `JSONResponse.render`/`.body` (qua việc dựng một
        # JSONResponse tạm) để bytes JSON trả về ở nhánh streaming này
        # GIỐNG HỆT bytes mà nhánh không-streaming (`return
        # JSONResponse(body)`) đã luôn trả -- không có hai cách mã hoá JSON
        # khác nhau cho cùng một nội dung.
        yield JSONResponse(body).body

    def _stream_live_analyze(
        code: str, request: Request, is_admin: bool, refresh: bool = False
    ) -> StreamingResponse:
        return StreamingResponse(
            _analyze_body_stream(code, request, is_admin, refresh=refresh),
            media_type="application/json",
        )

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

        # 4) Rate limit -- ĐÃ CHUYỂN LÊN ĐÂY (trước khi commit sang
        # streaming), khác với thứ tự cũ (chỉ tính quota SAU khi cả snapshot
        # Redis lẫn `assessment.json` trên đĩa đều MISS). Lý do: byte đầu
        # tiên của response giờ phải bay đi NGAY, TRƯỚC KHI generator kịp
        # biết lượt gọi này sẽ trúng cache hay phải chạy sống (ba tầng tra
        # cứu đó giờ nằm trong `_resolve_and_analyze`, chạy BÊN TRONG
        # generator streaming -- xem hàm đó và `_analyze_body_stream` bên
        # dưới cho lý do đầy đủ: hai tra cứu tưởng "rẻ" đó đo được bị giãn
        # ra tới 4.23s dưới tải, chính là lỗi cần sửa). Vì response ĐÃ cam
        # kết HTTP 200 ngay khi streaming bắt đầu (header đã gửi, không thể
        # đổi status code giữa chừng), 429 -- một mã trạng thái HTTP THẬT --
        # chỉ có thể còn được trả ở ĐÂY, TRƯỚC điểm commit đó. Đánh đổi (xem
        # `ANALYZE_RATE_LIMIT_MAX_REQUESTS`'s comment cho toàn bộ lý giải):
        # một mã ĐÃ CHẤM sẵn (cache/disk hit, vốn rẻ) giờ CŨNG tốn một suất
        # quota -- chỉ probe rỗng, mã sai định dạng, và hai tham số đồng
        # nghĩa xung đột (ba nhánh phía trên, luôn chạy trước bước này) mới
        # còn được miễn phí hoàn toàn.
        #
        # An admin-authenticated request uses `admin_limiter` -- a
        # SEPARATE PerIpRateLimiter instance with its own, wider budget
        # (see ADMIN_RATE_LIMIT_MAX_REQUESTS above) -- instead of
        # `limiter`, never both: this is a different, wider quota, not
        # an additional one on top of the ordinary one.
        client_host = resolve_client_ip(request)
        active_limiter = admin_limiter if is_admin else limiter
        if not active_limiter.allow(client_host):
            message = (
                "The admin key is calling /api/analyze too fast. The admin "
                "quota is wider than the ordinary one but NOT unlimited -- "
                "each scoring pass still costs several seconds of CPU and "
                "many OKX calls -- please wait a moment and try again."
                if is_admin
                else "You are calling /api/analyze too fast. Each scoring pass "
                "costs several seconds of CPU and many OKX calls, so the "
                "system limits calls per IP -- please wait a moment and try "
                "again."
            )
            # 429 vẫn giữ đúng mã trạng thái HTTP -- nhánh này luôn chạy
            # TRƯỚC khi commit sang streaming (`_stream_live_analyze` bên
            # dưới), nên không có gì bị "chốt 200" ở đây cả.
            return _error_json(message, 429)

        # 5) Commit sang streaming NGAY -- xem `_analyze_body_stream`/
        # `_resolve_and_analyze` cho toàn bộ phần việc còn lại (bộ đệm đầu
        # tiên -> snapshot Redis -> `assessment.json` trên đĩa -> chạy sống
        # nếu cần), giờ chạy hết BÊN TRONG generator đó, sau byte đệm đầu
        # tiên -- xem ANALYZE_HEARTBEAT_INTERVAL_SECONDS's comment cho lý
        # do/bằng chứng của cơ chế nhịp tim, và `_analyze_error_body`'s
        # docstring cho đánh đổi HTTP status mà bước commit này kéo theo.
        merged_params = await _merged_request_params(request)
        refresh = str(merged_params.get("refresh", "")).lower() in ("1", "true", "yes")
        return _stream_live_analyze(code, request, is_admin, refresh=refresh)

    async def api_analyze_status(request: Request) -> Response:
        """GET /api/analyze/status?code=... -- plan_progress.md mục B/D.

        Hợp đồng (mọi trường LUÔN có mặt, kể cả khi `None`):
            {
              "code": str,
              "state": "running" | "done" | "error" | "unknown",
              "stage": "ledger"|"markets"|"scoring"|"decision"|"narrative"|
                       "done" | null,
              "stage_index": int | null,   # 0..stage_count, xem dưới
              "stage_count": int,          # luôn 5 (progress.STAGE_COUNT)
              "stage_label": str | null,   # nhãn tiếng Việt sẵn của `stage`
              "elapsed_ms": int | null,    # đã trôi bao lâu từ lúc start()
              "error": str | null,
              "report_ready": bool,        # có snapshot/assessment.json để
                                            # GET /bot/<code> dùng ngay không
            }

        `state`:
          * "running" -- có task đang bay cho mã này (hoặc vừa mới bắt đầu,
            `stage`/`stage_index` còn `None`/0 nếu chưa qua chặng nào).
          * "done"    -- có bản ghi ĐÃ xong, HOẶC không có bản ghi nào
            (registry có TTL/trần, xem progress.py) nhưng `report_ready` là
            `true` -- một bot đã chấm sẵn từ trước (assessment.json/snapshot
            còn hạn) không cần "running" trước đó vẫn phải báo "done" đúng
            sự thật, không phải "unknown".
          * "error"   -- pipeline/registry ghi nhận lỗi cho mã này (bao gồm
            cả nhánh "quá tải" của `ANALYZE_MAX_CONCURRENT_LIVE_ANALYSES`,
            xem `_resolve_and_analyze`) -- `error` kèm thông báo tiếng Việt.
          * "unknown" -- KHÔNG có bản ghi nào VÀ KHÔNG có báo cáo sẵn -- mã
            này chưa từng được `/api/analyze` gọi tới (hoặc bản ghi progress
            của nó đã bị TTL/trần dọn từ lâu VÀ pipeline chưa từng ghi được
            gì) -- không phải "error", chỉ là "chưa biết gì cả".

        `stage_index`/`stage_count`/`stage_label` -- KHÔNG có trường phần
        trăm nào: đo thật (xem progress.py's bảng đo 5 chặng) cho thấy hai
        chặng nặng nhất ("ledger", "markets") có phương sai >2x giữa các bot
        thật (2.97x và 15.7x) -- vượt xa ngưỡng plan_progress.md mục A đặt
        ra cho việc còn được phép hiện %. Frontend hiện "Bước
        {stage_index}/{stage_count} · {stage_label}", không suy ra % từ bất
        kỳ phép tính nào trên các trường này.

        Cùng cổng access-token/admin như POST/GET /api/analyze (một mã ai
        đó vừa trả tiền/công sức phân tích không nên bị người lạ dò tiến độ
        tự do một khi NORABT_ACCESS_TOKENS đã bật) -- nhưng KHÔNG tiêu một
        suất `limiter`/`admin_limiter` nào: đây là endpoint POLL LẶP LẠI
        (mỗi 1.5-3s, xem AnalyzeFlow.jsx), tính quota y hệt /api/analyz sẽ
        khiến chính việc hiện thanh tiến độ ăn hết ngân sách trước khi phân
        tích kịp xong.
        """
        try:
            is_admin = await _is_admin_request(request)
            if not is_admin and access.is_protected():
                token = await _resolve_access_token(request)
                if not token:
                    return _missing_token_response()
                if access.verify_token(token) is None:
                    return _invalid_token_response()

            raw_code = request.query_params.get("code")
            try:
                code = validate_unique_code(raw_code)
            except InvalidCodeError as exc:
                return _invalid_param_response(str(exc))

            record = analyze_progress.get(code)
            cached_snapshot = await snapshot.get_snapshot(code)
            report_ready = cached_snapshot is not None
            scored_at_ms: Optional[int] = None
            if cached_snapshot is not None:
                scored_at_ms = cached_snapshot.get("snapshot_at_ms")
            if not report_ready:
                scored = await run_in_threadpool(service.find_scored_report, code)
                report_ready = scored is not None
                if scored is not None:
                    scored_at_ms = scored[1]

            if record is None:
                is_running = code in live_analyze_tasks
                return JSONResponse(
                    {
                        "code": code,
                        "state": "done"
                        if report_ready
                        else ("running" if is_running else "unknown"),
                        "stage": "done"
                        if report_ready
                        else ("ledger" if is_running else None),
                        "stage_index": (
                            analyze_progress.STAGE_COUNT
                            if report_ready
                            else (1 if is_running else None)
                        ),
                        "stage_count": analyze_progress.STAGE_COUNT,
                        "stage_label": (
                            analyze_progress.STAGE_LABELS_VI.get("done")
                            if report_ready
                            else (
                                analyze_progress.STAGE_LABELS_VI.get("ledger")
                                if is_running
                                else None
                            )
                        ),
                        "elapsed_ms": None,
                        "error": None,
                        "report_ready": report_ready,
                        "scored_at_ms": scored_at_ms,
                    }
                )

            return JSONResponse(
                {
                    "code": code,
                    "state": record["state"],
                    "stage": record["stage"],
                    "stage_index": record["stage_index"],
                    "stage_count": record["stage_count"],
                    "stage_label": record["stage_label"],
                    "elapsed_ms": record["elapsed_ms"],
                    "error": record["error"],
                    "report_ready": report_ready,
                    "scored_at_ms": scored_at_ms,
                }
            )
        except Exception as exc:  # noqa: BLE001 - last line of defence, see module docstring
            incident_code = _log_incident("GET /api/analyze/status", exc)
            return _error_json(_generic_error_message(incident_code), 500)

    async def _bot_report_response(
        code: str,
        client_host: str,
        *,
        is_admin: bool = False,
        refresh: bool = False,
        self_path: str,
    ) -> Response:
        """Shared body for GET /bot/<code> and GET /<userref>_<code> below --
        both ultimately render the exact same HTML report for a `code` that
        has already been resolved/validated by their respective callers,
        just reached through two different URLs: a guessable one
        (`bot_report`), and the obscure per-user one (`user_report`) that
        `/api/analyze`'s own `detail_url` above actually hands out to a
        logged-in user's session.

        Deliberately does NOT reuse the SPA `index` route serves (Việc 2,
        `Agent/frontend/`/`Agent/web/dist/`) -- that page is a client-side
        app with its own router and never renders a bot report itself; it
        only ever LINKS to this route (`window.location.href`) once a
        lookup+analyze flow finishes, then leaves the SPA entirely -- see
        `Agent/frontend/README.md`'s own "Vì sao trang chi tiết bot ...
        không được dựng lại trong SPA" section for the full reasoning
        (must render without JS, must work from a link a stranger opens
        cold, must not depend on the frontend having been built at all).

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

        `refresh`/`self_path` control a THREE-tier source order -- see
        `Agent/backend/web/snapshot.py`'s module docstring for the "cache,
        never source of truth" contract the first tier leans on, and
        `data.py`'s own "GET /bot/<code> ... without re-analyzing" section
        docstring for the second:

          * `refresh=True` (the "?refresh=1" link this same route renders,
            see below) skips BOTH tiers below outright and always
            re-analyzes live -- and, critically, is NOT exempt from
            `limiter`: the whole point of gating refresh behind the exact
            same budget as an ordinary cache-miss/`/api/analyze` call is
            that "?refresh=1" must never become a free bypass of that
            quota.
          * `refresh=False` (the ordinary case) first tries
            `snapshot.get_snapshot(code)` -- a cache HIT skips
            `service.analyze()` entirely (never charged against `limiter`,
            since nothing expensive ran) and renders the cached result
            stamped with ITS OWN capture time, not "now".
          * Still `refresh=False` and a Redis MISS (none, expired, or Redis
            unreachable/corrupt -- all indistinguishable to this route)
            tries `service.find_scored_report(code)` next: if `run_report.py`
            already scored this exact `code` (an `assessment.json` sits on
            disk for it), that already-computed verdict is reshaped and
            rendered directly -- again never charged against `limiter`,
            again stamped with ITS OWN capture time (`generated_at_ms` from
            the file, NOT "now"). THIS is the actual fix for the reported
            504: a `code` this project already scored used to fall all the
            way through to a live re-analysis (~70s: OKX fetch + 10k-run
            Monte Carlo + optional LLM narrative) on every single view,
            which is well past nginx's own `proxy_read_timeout 75s` under
            load. A code NEVER scored (a stranger's bot nobody has looked at
            yet) has no assessment.json to find, so this tier is a clean
            no-op for it and it still falls through to live analysis below,
            exactly as before this fix existed.
          * Only once BOTH of those come back empty does this fall through
            to the live-analysis path that existed before either cache did.
          * `self_path` (e.g. `/bot/<code>` or `/<userref>_<code>`) is this
            request's OWN url, without query string -- used to build the
            "Phân tích lại" link's `?refresh=1` target so it always points
            back at whichever of the two routes was actually used, never
            hard-coded to one of them.

        A Redis snapshot is only ever written AFTER a live analysis actually
        ran (never on a cache hit, and never for a `find_scored_report` hit
        either -- assessment.json is already durable on disk, there is
        nothing more to cache), and never blocks the response on Redis being
        healthy: `snapshot.set_snapshot` itself never raises and is bounded
        by its own short timeouts (see that module's docstring).

        The snapshot banner also marks a result as stale once its own
        `snapshot_at_ms` is more than `snapshot.SNAPSHOT_TTL_SECONDS` (24h)
        old -- the Redis tier can never actually be that old (its own TTL
        already expires it first), but an `assessment.json` on disk has no
        such expiry, and a batch run from days ago should say so plainly
        rather than silently look as fresh as one from a minute ago.
        """
        result: Optional[Dict[str, Any]] = None
        snapshot_at_ms: Optional[int] = None

        if not refresh:
            cached = await snapshot.get_snapshot(code)
            if cached is not None:
                result = cached["result"]
                snapshot_at_ms = cached["snapshot_at_ms"]
            if result is None:
                scored = await run_in_threadpool(service.find_scored_report, code)
                if scored is not None:
                    result, snapshot_at_ms = scored

        if result is None and not refresh:
            # Sửa lỗi treo >60s (plan_progress.md mục C -- xem
            # `BOT_REPORT_AWAIT_LIVE_TASK_TIMEOUT_SECONDS`'s comment cho toàn
            # bộ phép đo/lý do). Không có snapshot/assessment.json nào ở
            # trên, nhưng có thể ĐANG có một task `/api/analyze` khác bay
            # cho ĐÚNG mã này (vd. người dùng vừa bấm "Phân tích" rồi mở
            # ngay report_url trong lúc job nền chưa xong) -- nếu vậy, AWAIT
            # chính task đó thay vì tự khởi động lượt phân tích thứ hai
            # (nguyên nhân treo thật đã đo được). `asyncio.shield`: hạn chờ
            # ở ĐÂY hết hạn thì CHỈ future bọc ngoài bị huỷ, task gốc (chia
            # sẻ với `_analyze_body_stream`/`background_analyze_tasks`) tiếp
            # tục chạy bình thường, không bao giờ bị `.cancel()` từ nhánh
            # này -- đúng yêu cầu "không huỷ task nền" đã áp dụng cho toàn
            # bộ module này.
            existing_task = live_analyze_tasks.get(code)
            if existing_task is not None:
                try:
                    await asyncio.wait_for(
                        asyncio.shield(existing_task),
                        timeout=BOT_REPORT_AWAIT_LIVE_TASK_TIMEOUT_SECONDS,
                    )
                except Exception:  # noqa: BLE001 - hết hạn HOẶC task tự lỗi:
                    # fail-open cả hai trường hợp, xem docstring của khối
                    # này -- nhánh bên dưới tự chạy sống của riêng nó như
                    # hành vi TRƯỚC khi việc sửa này tồn tại.
                    pass
                else:
                    # Task vừa await xong: nếu đó là nhánh "chạy sống"
                    # (`_run_live_analyze`), nó đã tự ghi snapshot Redis
                    # TRƯỚC khi trả về (xem hàm đó) -- đọc lại đúng snapshot
                    # đó thay vì tin vào giá trị trả về của task (hình dạng
                    # ĐÃ bị `_finish_analyze_result`/`_analyze_summary_for_
                    # wire` cắt gọn cho JSON API, không đủ cho
                    # `render_bot_report_html`). Task hoá ra chỉ là
                    cached = await snapshot.get_snapshot(code)
                    if cached is not None:
                        result = cached["result"]
                        snapshot_at_ms = cached["snapshot_at_ms"]

        if result is None and not refresh:
            existing_task = live_analyze_tasks.get(code)
            if existing_task is not None and not existing_task.done():
                raw = pending_result(code, [ANALYZE_PENDING_TEXT_VI])
                return HTMLResponse(
                    render_bot_report_html(
                        raw,
                        is_admin=is_admin,
                        snapshot_at_ms=None,
                        refresh_url=f"{self_path}?refresh=1",
                        is_stale=False,
                    )
                )

        if result is None:
            # Same shared budget as POST /api/analyze -- charged ONLY when
            # this request is actually about to run the expensive,
            # OKX-touching scoring pipeline: a cache miss, an expired/
            # unreachable snapshot, or an explicit "?refresh=1". A cache HIT
            # above never reaches this branch at all, and "?refresh=1"
            # deliberately CANNOT skip past it either (task's own explicit
            # requirement -- otherwise refresh is just a quota bypass with
            # extra steps).
            if not limiter.allow(client_host):
                return HTMLResponse(
                    _report_error_html(
                        "You are viewing this report page too fast. This page "
                        "scores the bot directly (costs CPU + a shared OKX "
                        "call quota), so it shares its rate limit with "
                        "/api/analyze -- please wait a moment and try again."
                    ),
                    status_code=429,
                )

            try:
                # `force=refresh`: skips the in-process TTL cache read inside
                # `WebDataService.analyze()` (see that method's own docstring)
                # exactly the same way the branch above already skips the
                # Redis snapshot for `refresh=True`. Before this, "?refresh=1"
                # bypassed ONLY the Redis snapshot -- a second click within
                # `DEFAULT_ANALYZE_CACHE_TTL_SECONDS` (180s) of the first
                # still hit that in-process cache and silently replayed the
                # exact same result, with the same "generated at" stamp, as
                # if the button had done nothing (the reported bug this
                # fixes). The fresh result is still WRITTEN into that cache
                # below (`service.analyze`'s own contract), so the very next
                # view stays cheap.
                result = await run_in_threadpool(service.analyze, code, refresh)
            except Exception as exc:  # noqa: BLE001 - last line of defence, see module docstring
                incident_code = _log_incident(
                    "GET /bot or /<user_ref>_<code> report", exc
                )
                return HTMLResponse(
                    _report_error_html(_generic_error_message(incident_code)),
                    status_code=500,
                )
            # Stamped at the moment this fresh analysis finished -- shown on
            # the page (see report_page.py's snapshot banner) so a reader
            # always knows exactly what point in time they are looking at,
            # whether this ends up cached afterwards or not.
            snapshot_at_ms = int(now_fn() * 1000)
            await snapshot.set_snapshot(code, result, snapshot_at_ms)

        refresh_url = f"{self_path}?refresh=1"
        # See this function's own docstring's last paragraph: a Redis-backed
        # snapshot can never actually be this old (its own TTL already
        # expires it first), but an assessment.json read via
        # `find_scored_report` has no such expiry -- this is the one check
        # that keeps a days-old batch run from silently looking as fresh as
        # a just-computed one.
        is_stale = (
            snapshot_at_ms is not None
            and int(now_fn() * 1000) - snapshot_at_ms
            > snapshot.SNAPSHOT_TTL_SECONDS * 1000
        )
        return HTMLResponse(
            render_bot_report_html(
                result,
                is_admin=is_admin,
                snapshot_at_ms=snapshot_at_ms,
                refresh_url=refresh_url,
                is_stale=is_stale,
            ),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

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
        # "?refresh=1" -- see _bot_report_response's own docstring: skips the
        # snapshot cache and re-analyzes, still charged against the same
        # rate limit as an ordinary cache miss.
        refresh = request.query_params.get("refresh") == "1"
        return await _bot_report_response(
            code,
            client_host,
            is_admin=is_admin,
            refresh=refresh,
            self_path=f"/bot/{code}",
        )

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
            _report_error_html("This report page was not found."), status_code=404
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
        analyzed THIS code at least once through /api/analyze) -- checked
        FIRST, unchanged from before Việc 2. If, and only if, that fails,
        this same path segment is tried as a Việc 2 usage ref
        (`usage_ref.resolve_usage_ref`) instead: the anonymous-caller
        counterpart `/api/analyze` mints for a caller with no user session
        (see that function's own `detail_url` branch) -- format-identical
        to a real `user_ref` (both satisfy `identity.USER_REF_RE`) but
        stored in a completely separate on-disk table
        (`Agent/data/usage_refs/`, never `Agent/data/users/`), and only ever
        opens the ONE `code` it was minted for. Every other case -- bad
        format, no such profile AND no such usage ref, either one present
        but for a different `code` -- is the exact same generic 404
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
            already_analyzed = profile is not None and identity.has_analyzed(
                profile, code
            )
            if not already_analyzed and not usage_ref.resolve_usage_ref(
                raw_user_ref, code, root=usage_refs_dir
            ):
                return _generic_report_404()
        client_host = resolve_client_ip(request)
        refresh = request.query_params.get("refresh") == "1"
        return await _bot_report_response(
            code,
            client_host,
            is_admin=is_admin,
            refresh=refresh,
            self_path=f"/{raw_user_ref}_{code}",
        )

    async def admin_page(request: Request) -> Response:
        """GET /admin -- see this module's own top-of-file docstring for the
        full route-level contract (Việc 3: retired server-rendered listing,
        now a plain redirect to the SPA's own `/#/admin`).

        Two independent ways this can still 404 (never 401/403, and never a
        response that differs between them in any observable way -- see
        `_generic_report_404`'s own callers for why that
        indistinguishability is the entire point): the admin role is not
        configured at all (`NORABT_ADMIN_TOKEN_SHA256` unset, the default)
        AND open access is off, or the admin role IS configured but this
        request's token/session is missing/wrong (open access still off).
        `_admin_open_access()` short-circuits BOTH of those checks when on
        -- Việc 2's own explicit, temporary decision to let anyone in
        without a credential -- but never changes the 404 body itself for
        the cases where it stays off: a distinctly-worded 404 for this ONE
        path would itself be a signal that this path is special, defeating
        the "cannot tell this route exists" goal just as surely as a
        401/403 would.

        The redirect target (`/#/admin`) never carries a token/query string
        of its own: the SPA's session cookie (or, when open access is on,
        the lack of any gate at all on `GET /api/bots`) is what the admin
        listing itself relies on next, not anything this redirect could add.
        """
        if not (_admin_open_access() or await _is_admin_request(request)):
            return _generic_report_404()
        return RedirectResponse("/#/admin", status_code=302)

    # Process start time, captured once per app instance (matches module-level
    # `app = create_app()` below, so it tracks the actual server process
    # uptime, not the uptime of a request handler).
    started_at = time.monotonic()
    # Mutable holder for the cached OKX reachability result. A plain dict
    # (rather than a module-level global) so each create_app() call -- e.g.
    # each test -- gets its own independent cache instead of leaking state
    # across app instances.
    okx_health_cache: Dict[str, Any] = {"checked_at": None, "reachable": None}
    # Same per-app-instance, short-TTL-cached pattern as okx_health_cache
    # above, for the snapshot Redis reachability probe (see
    # SNAPSHOT_HEALTHZ_CACHE_TTL_SECONDS's own comment).
    snapshot_health_cache: Dict[str, Any] = {"checked_at": None, "status": None}

    async def healthz(request: Request) -> Response:
        """Liveness probe for an orchestrator (see docker-compose's
        `healthcheck:` block) and for a human at 2am deciding whether to
        restart the container.

        Deliberately reports independent facts rather than one boolean:

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
          * `snapshot`: one of `"disabled"` (NORABT_SNAPSHOT_REDIS_URL unset
            -- the default, matching "feature off" everywhere else in
            snapshot.py), `"ok"` (configured and PING succeeded), or
            `"unreachable"` (configured but PING failed/timed out). Also
            purely informational, never flips `status` -- see
            `Agent/backend/web/snapshot.py`'s module docstring: this cache
            is a buffer, so its own outage is, by design, never this
            process's problem to restart over. `GET /bot/<code>` already
            falls back to a live analysis on its own the moment this is
            anything but `"ok"`.
          * `narrative`: one of `"disabled"`, `"ok"` (optionally suffixed
            with a resolved version, e.g. `"ok (claude 2.1.270)"`),
            `"binary_missing"`, or `"no_credentials"` -- see
            `_narrative_healthz_status`'s own docstring for the full
            rationale (this exists specifically to make a broken
            container mount for the `claude` CLI/credentials VISIBLE
            instead of silently degrading every narrative to the static
            fallback sentence forever). Also purely informational, never
            flips `status` -- same reasoning as `snapshot`/
            `okx_public_reachable`: nothing about this ever spawns the
            `claude` CLI, so it never spends real usage quota, but it also
            never actually proves generation still works end to end (see
            that docstring's own "KNOWN BLIND SPOT" note).

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

        if not snapshot.is_configured():
            snapshot_status = "disabled"
        else:
            snap_checked_at = snapshot_health_cache["checked_at"]
            if (
                snap_checked_at is None
                or (now - snap_checked_at) >= SNAPSHOT_HEALTHZ_CACHE_TTL_SECONDS
            ):
                try:
                    snapshot_reachable = await snapshot.ping()
                except Exception:  # noqa: BLE001 - snapshot.ping() never raises, kept defensively anyway
                    snapshot_reachable = False
                snapshot_health_cache["checked_at"] = now
                snapshot_health_cache["status"] = (
                    "ok" if snapshot_reachable else "unreachable"
                )
            snapshot_status = snapshot_health_cache["status"]

        return JSONResponse(
            {
                "status": "ok" if bots_on_disk is not None else "degraded",
                "uptime_seconds": round(now - started_at, 1),
                "snapshot": snapshot_status,
                "narrative": _narrative_healthz_status(),
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
                "Missing 'identity' field in the JSON body -- send the admin "
                "key, or a wallet address shaped like '0x' + 40 hex "
                "characters. "
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
                "The 'identity' value does not match the admin key, and is "
                "not a valid wallet address either -- it must be exactly "
                "'0x' followed by 40 hex characters, e.g. "
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
                "The system temporarily could not save the profile, please "
                f"try again later (incident code: {incident_code}).",
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
        Route("/api/config", api_config, methods=["GET"]),
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
        # plan_progress.md mục B -- endpoint POLL cho thanh tiến độ THẬT của
        # lượt /api/analyze đang bay, xem `api_analyze_status`'s own
        # docstring cho hợp đồng JSON đầy đủ. Đăng ký TRƯỚC `/bot/{code}`
        # không quan trọng thứ tự ở đây (literal path khác hẳn), nhưng đặt
        # cạnh `/api/analyze` cho dễ đọc bảng route.
        Route("/api/analyze/status", api_analyze_status, methods=["GET"]),
        Route("/bot/{code}", bot_report, methods=["GET"]),
        # Việc 2: the SPA's own JS/CSS bundle (Agent/frontend/build.sh's
        # output, see `assets_dir` above). `check_dir=False` -- a fresh
        # checkout that has not run the frontend build yet must not crash
        # THIS APP'S STARTUP (Starlette's `StaticFiles.__init__` otherwise
        # raises `RuntimeError` for a missing directory at mount time) --
        # per-request behaviour for a missing directory/file both still
        # degrade to an ordinary 404 (see `StaticFiles.get_response`),
        # exactly like any other missing static asset. `StaticFiles` itself
        # already normalizes and rejects any path that would resolve
        # outside `assets_dir` (`..`-escapes, absolute-path overrides, ...)
        # -- see Agent/test/test_web_app.py's own directory-traversal tests,
        # required by this task, which check this holds rather than
        # assuming it.
        Mount("/assets", app=StaticFiles(directory=assets_dir, check_dir=False)),
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
        "Run `python3 -m Agent.backend.run_web` instead of this file "
        "directly to get the full set of CLI parameters (--host, --port, "
        "--dashboard).",
        file=sys.stderr,
    )
