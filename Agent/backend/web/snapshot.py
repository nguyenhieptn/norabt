"""Fail-open Redis cache layer for `GET /bot/<code>` / `GET /<userref>_<code>`
(see `Agent/backend/web/app.py`'s `_bot_report_response`).

CORE PRINCIPLE (this is the whole point of this module, not an incidental
detail): a snapshot stored here is a CACHE, never the record of truth.
`WebDataService.analyze()` remains the only authority on what a bot's report
actually says -- this module only remembers its last full output for a
while so a popular/shared link does not re-run the whole scoring pipeline
(several seconds of CPU + several OKX requests, see `data.py`'s module
docstring) on every single view. Two consequences follow directly, and both
are enforced everywhere in this module, not just at the edges:

  1. A link must NEVER die because a snapshot expired, is missing, or Redis
     itself is unreachable. Every public function below returns a plain
     `None`/no-op on ANY failure -- a bad connection, a timeout, a corrupt
     value, an oversized payload, Redis simply not being configured at all
     -- and NEVER raises. The caller (`app.py`) always has a well-defined
     fallback: compute the analysis live, exactly as it did before this
     module existed. This file is the ONLY place that ever needs to reason
     about what can go wrong with Redis; every other module just sees
     "cached value, or None".
  2. Nothing here is allowed to make a request slower than the
     no-cache baseline by more than a fraction of a second. See
     `REDIS_CONNECT_TIMEOUT_SECONDS`/`REDIS_SOCKET_TIMEOUT_SECONDS` below --
     a hung/unreachable Redis must fail fast, not hang the page.

DEPLOYMENT CONTEXT this module was written against (see
`Agent/docker/docker-compose.yml`/README for the full picture): this
connects to `agent-redis`, a Redis instance DEDICATED to this project alone
(its own `docker-compose.yml` service, not reachable from the host, no
persistence, 128MB `maxmemory`). It is deliberately NOT the same Redis as
`norabt-redis` -- the unrelated "nora" project's own instance, which keeps
88 keys (`candles:*`, `state:*`, `universe:*`) in its db0 under a separate
400MB cap. `norabt-redis` also runs `network_mode: host` and only binds
127.0.0.1, so a container on this project's own bridge network could never
reach it anyway -- `agent-redis` exists precisely so this module never has
to depend on, or touch, that other instance. Even so, this module keeps two
isolation layers that cost nothing and guard against future mistakes (e.g.
an operator pointing `NORABT_SNAPSHOT_REDIS_URL` at the wrong instance by
accident):

  * A dedicated DB index (`REDIS_DB_INDEX`, db1) keeps this project's keys
    off whatever happens to be in db0 of the configured instance.
  * A dedicated key prefix (`KEY_PREFIX`) on top of that, so `redis-cli
    --scan` output is unambiguous about ownership no matter which instance
    it is inspecting.
  * `SNAPSHOT_MAX_BYTES` bounds each individual key's size, and
    `SNAPSHOT_TTL_SECONDS` bounds how long it lives, together keeping this
    project's total footprint tiny and self-cleaning against `agent-redis`'s
    128MB `maxmemory` cap (`allkeys-lru` eviction, see docker-compose.yml).
  * This module never issues `FLUSHDB`, `FLUSHALL`, or a bare `KEYS *` --
    the only commands it ever sends are `GET`/`SETEX`/`PING` against keys it
    builds itself via `snapshot_key()`.

Configuration is entirely through `NORABT_SNAPSHOT_REDIS_URL`
(`ENV_VAR_REDIS_URL` below), read LIVE on every call (same "no import-time
snapshot of the environment" pattern `access.is_protected()`/
`data.py`'s `report_base_url()` already use elsewhere in this project) --
NOT `REDIS_URL` (that variable belongs to `Agent/backend/report/qc/**`'s own
project-"nora" pipeline against db0, and is out of scope for this module to
even read). Leaving `NORABT_SNAPSHOT_REDIS_URL` UNSET (the default) disables
this entire module: every function below becomes a guaranteed no-op that
never imports/constructs a Redis client and never makes a network call, so a
fresh checkout / a deployment that has not wired Redis up runs exactly as it
did before this module existed.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import urlsplit, urlunsplit

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

# Unset (default) -> feature disabled entirely, see module docstring.
ENV_VAR_REDIS_URL = "NORABT_SNAPSHOT_REDIS_URL"

# Snapshot lifetime. The report this caches is built from CLOSED trades and a
# WEEKLY-bucketed equity curve (see WebDataService.analyze/data.py) -- it does
# not meaningfully change minute to minute, so 24h comfortably covers one
# person's whole working session on a shared link without re-scoring on every
# reload, while still forcing at least one fresh rescan per day so a bot that
# genuinely changes behaviour cannot stay stale behind a permanently-warm
# cache indefinitely.
SNAPSHOT_TTL_SECONDS = 24 * 60 * 60

# Every key this module ever writes or reads is under this prefix -- see the
# module docstring's "DEPLOYMENT CONTEXT" section for why this still matters
# even on `agent-redis` (a dedicated instance): defense in depth against a
# misconfigured NORABT_SNAPSHOT_REDIS_URL ever pointing somewhere unexpected.
KEY_PREFIX = "agent:report:"

# This project uses db1 unconditionally so its keyspace can never collide
# with whatever lives in db0 of the configured instance (see module
# docstring), no matter what db index (if any) an operator's
# NORABT_SNAPSHOT_REDIS_URL happens to spell out in its path. See
# `_build_client` below for how this is enforced even against a URL that
# explicitly names a different db.
REDIS_DB_INDEX = 1

# Reject (skip, never write) a payload bigger than this. Cheap insurance
# against one abnormal bot (e.g. a runaway warnings/assets list) eating into
# `agent-redis`'s own 128MB `maxmemory` cap (see docker-compose.yml).
SNAPSHOT_MAX_BYTES = 512 * 1024

# Both a connect and a command timeout, deliberately short (well under a
# second): this cache must never be allowed to make a page noticeably slower
# than the no-cache baseline. A hung/unreachable Redis must fail fast, not
# hang the request -- see module docstring, point 2.
REDIS_CONNECT_TIMEOUT_SECONDS = 0.5
REDIS_SOCKET_TIMEOUT_SECONDS = 0.5


def snapshot_key(code: str) -> str:
    """The one place that turns a bot `code` into a Redis key -- every
    caller (get/set) goes through this, so the namespace can never drift
    between a write and a later read."""
    return f"{KEY_PREFIX}{code}"


def _redis_url() -> Optional[str]:
    """Read `NORABT_SNAPSHOT_REDIS_URL` live from the environment (never
    cached at import time -- see module docstring). Returns `None` for an
    unset or blank value, which is exactly what `is_configured()`/every
    public function below treats as "feature off"."""
    raw = os.environ.get(ENV_VAR_REDIS_URL, "").strip()
    return raw or None


def is_configured() -> bool:
    """Whether the snapshot feature is turned on at all. Exposed separately
    from `ping()` (see `app.py`'s `GET /healthz`) so that route can report
    the three-way `disabled`/`ok`/`unreachable` status the task requires
    without this module's connection details leaking into `app.py`."""
    return _redis_url() is not None


# Lazily-built client, cached per-process for as long as the configured URL
# does not change -- avoids paying a fresh TCP handshake for every single
# request (redis-py pools connections internally once a client exists), while
# `_redis_url()` being re-read on every `_get_client()` call still means
# flipping the env var/restarting with a new one takes effect without a
# stale client lingering. A plain module dict, not a class -- there is only
# ever one such client needed per process, unlike PerIpRateLimiter/
# WebDataService which are explicitly instantiated per `create_app()` call.
_client_state: Dict[str, Any] = {"client": None, "url": None}


def _build_client(url: str) -> "aioredis.Redis":
    """Construct a fresh `redis.asyncio.Redis` for `url`, forcing
    `REDIS_DB_INDEX` regardless of any database segment already present in
    `url`'s own path. `Redis.from_url` gives an explicit path segment
    (`redis://host:port/N`) priority over a `db=` keyword -- so a URL that
    happens to spell out a path (`/0`, or nothing at all defaulting to `/0`)
    would otherwise silently win over `db=REDIS_DB_INDEX` and put this
    project's keys in db0 of whatever instance the URL points at (see module
    docstring's "DEPLOYMENT CONTEXT" for why db0 is best left untouched even
    on a dedicated instance). Stripping the path here and passing
    `db=REDIS_DB_INDEX` explicitly makes that impossible no matter what an
    operator pastes into NORABT_SNAPSHOT_REDIS_URL.

    Building a client does no I/O by itself (redis-py connects lazily on the
    first real command), so this never blocks/raises for network reasons --
    only a genuinely malformed URL could raise here, which callers still
    guard against defensively.
    """
    parts = urlsplit(url)
    normalized = urlunsplit(
        (parts.scheme, parts.netloc, "", parts.query, parts.fragment)
    )
    return aioredis.Redis.from_url(
        normalized,
        db=REDIS_DB_INDEX,
        socket_connect_timeout=REDIS_CONNECT_TIMEOUT_SECONDS,
        socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
    )


def _get_client() -> Optional["aioredis.Redis"]:
    """Return the cached client for the currently-configured URL, building
    one if needed. Returns `None` when unconfigured, or in the (extremely
    unlikely, since `_build_client` does no I/O) case building one itself
    raises -- either way, every caller below treats `None` exactly like a
    failed Redis call: no snapshot, no crash.

    This is the one seam tests patch to inject a fake async client (see
    Agent/none/test/test_web_app.py's snapshot tests) instead of talking to a
    real Redis server.
    """
    url = _redis_url()
    if url is None:
        return None
    if _client_state["client"] is not None and _client_state["url"] == url:
        return _client_state["client"]
    try:
        client = _build_client(url)
    except Exception as exc:  # noqa: BLE001 - see module docstring, point 1
        logger.warning(
            "norabt snapshot: failed to build redis client (%s)", type(exc).__name__
        )
        return None
    _client_state["client"] = client
    _client_state["url"] = url
    return client


# --------------------------------------------------------------------------- #
# Public cache API -- get/set/ping. NONE of these ever raise; see module
# docstring, point 1.
# --------------------------------------------------------------------------- #


async def get_snapshot(code: str) -> Optional[Dict[str, Any]]:
    """Return `{"result": <full analyze() dict>, "snapshot_at_ms": <int>}`
    previously written by `set_snapshot(code, ...)`, or `None` if there is
    no USABLE snapshot for ANY reason: the feature is unconfigured, the key
    is missing/expired (Redis's own TTL, see `set_snapshot`), the connection
    failed or timed out, or the stored value fails to parse as the exact
    shape this module itself writes (corrupt data, a truncated write, a
    stale format from a future version of this module, ...).

    Every one of those is DELIBERATELY indistinguishable to the caller: the
    only thing `app.py` ever needs to know is "compute it live instead" --
    see module docstring for why a cache layer must never become a new way
    for this page to fail.
    """
    if not is_configured():
        return None
    client = _get_client()
    if client is None:
        return None
    key = snapshot_key(code)
    try:
        raw = await client.get(key)
    except Exception as exc:  # noqa: BLE001 - see module docstring, point 1
        logger.warning(
            "norabt snapshot: read failed for key=%s (%s)", key, type(exc).__name__
        )
        return None
    if raw is None:
        return None
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        payload = json.loads(raw)
    except Exception as exc:  # noqa: BLE001 - corrupt/garbage value, never crash
        logger.warning(
            "norabt snapshot: value for key=%s is not valid JSON (%s)",
            key,
            type(exc).__name__,
        )
        return None
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("result"), dict)
        or not isinstance(payload.get("snapshot_at_ms"), int)
    ):
        logger.warning("norabt snapshot: value for key=%s has an unexpected shape", key)
        return None
    return payload


async def set_snapshot(code: str, result: Dict[str, Any], snapshot_at_ms: int) -> None:
    """Store `result` (the full, un-trimmed dict `WebDataService.analyze()`
    returns) under `code`'s key, with `snapshot_at_ms` (caller-supplied so
    this module never has its own opinion about the clock -- see `app.py`'s
    injectable `now_fn`) alongside it. Uses `SETEX` so the TTL is applied
    atomically with the write -- there is never a moment where the key exists
    without an expiry attached.

    Never raises, and never logs the snapshot's own CONTENT -- only the key
    and byte size (task's own explicit requirement: this project's own bot
    analysis data is not something to leave sitting in a shared log stream).
    """
    if not is_configured():
        return
    key = snapshot_key(code)
    try:
        encoded = json.dumps(
            {"result": result, "snapshot_at_ms": snapshot_at_ms}, default=str
        )
    except Exception as exc:  # noqa: BLE001 - see module docstring, point 1
        logger.warning(
            "norabt snapshot: failed to serialize result for key=%s (%s)",
            key,
            type(exc).__name__,
        )
        return
    size = len(encoded.encode("utf-8"))
    if size > SNAPSHOT_MAX_BYTES:
        # Skip the write, not the request -- app.py still serves the page
        # from `result`, it just never gets cached this time (task's own
        # explicit "bỏ qua không ghi" instruction, protecting agent-redis's
        # own 128MB maxmemory cap from one abnormal bot).
        logger.warning(
            "norabt snapshot: payload for key=%s is %d bytes, over the %d-byte cap"
            " -- skipping write",
            key,
            size,
            SNAPSHOT_MAX_BYTES,
        )
        return
    client = _get_client()
    if client is None:
        return
    try:
        await client.setex(key, SNAPSHOT_TTL_SECONDS, encoded)
    except Exception as exc:  # noqa: BLE001 - see module docstring, point 1
        logger.warning(
            "norabt snapshot: write failed for key=%s (%s)", key, type(exc).__name__
        )
        return
    logger.info(
        "norabt snapshot: wrote key=%s size=%d bytes ttl=%ds",
        key,
        size,
        SNAPSHOT_TTL_SECONDS,
    )


async def delete_snapshot(code: str) -> bool:
    """Xoá bản chụp của `code`, trả `True` nếu thật sự có một khoá bị xoá.

    VÌ SAO CẦN: `?refresh=1` trước đây chỉ BỎ QUA bản chụp rồi chạy sống. Bản
    chụp cũ vẫn nằm trong Redis với TTL 24h, nên ngay lượt xem kế tiếp hệ
    thống lại phục vụ đúng kết quả cũ mà người dùng vừa cố ý chạy lại để
    thay thế -- công chạy lại bị vứt đi âm thầm, và tệ hơn là người dùng
    không có cách nào biết.

    Không bao giờ ném lỗi: Redis hỏng thì lượt chạy lại vẫn phải chạy được,
    cùng nguyên tắc với mọi hàm khác trong module này.
    """
    if not is_configured():
        return False
    client = _get_client()
    if client is None:
        return False
    key = snapshot_key(code)
    try:
        removed = await client.delete(key)
    except Exception as exc:  # noqa: BLE001 - xem docstring module, điểm 1
        logger.warning(
            "norabt snapshot: không xoá được key=%s (%s)", key, type(exc).__name__
        )
        return False
    if removed:
        logger.info("norabt snapshot: đã xoá bản chụp cũ key=%s trước khi chạy lại", key)
    return bool(removed)


async def ping() -> bool:
    """Cheap reachability probe for `GET /healthz` (see `app.py`, which wraps
    this in its own short-TTL cache, the same pattern already used for the
    OKX reachability check -- so a healthcheck polling every ~30s never
    itself becomes a source of load). Returns `False` for anything other
    than a genuine successful `PING` -- unconfigured, connection failure,
    timeout, an unexpected reply -- never raises.
    """
    if not is_configured():
        return False
    client = _get_client()
    if client is None:
        return False
    try:
        return bool(await client.ping())
    except Exception:  # noqa: BLE001 - see module docstring, point 1
        return False
