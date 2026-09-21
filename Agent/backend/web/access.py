"""Optional caller-identity gate for POST/GET /api/analyze.

READ THIS BEFORE WIRING THIS MODULE INTO ANYTHING ELSE: the token this
module checks is a SELF-ISSUED API key, not proof of any OKX identity.
`/api/analyze` is listed on the OKX AI Marketplace with `fee = 0`
(agentId 13753, sid 40700) -- and OKX's own marketplace protocol never
forwards ANY buyer identity to a fee=0 endpoint at all. The buyer-side
`a2mcp-probe` CLI only ever relays the PARAMETERS a human typed into it; it
carries no OKX-issued session, signature, or account id for this service to
check. So a request that presents a valid token here proves only "whoever
sent this request already knew a shared secret this operator handed out
out-of-band" -- exactly like `OKX_API_KEY` elsewhere in this project proves
"this process knows a secret", never "this process is user X on OKX". A
future reader must not treat a verified token as an authenticated OKX
identity; it is a doorman, not an ID check.

That doorman has exactly one job: keep a stranger who never received a
token from calling this CPU- and OKX-quota-expensive endpoint for free (see
`Agent/backend/web/data.py`'s module docstring for why that call is
expensive). It must NEVER influence what `WebDataService.analyze()`
computes -- see `Agent/backend/web/app.py`'s `api_analyze`, which checks a
token (when configured) BEFORE calling `service.analyze()`, but passes
nothing about the token into that call. Core scoring logic stays 100%
token-agnostic.

Deliberately has NO dependency on Starlette (or any web framework): reading
a token out of an HTTP request's headers/query/body is `app.py`'s job (it
has the `Request` object); this module only ever sees a plain string.

This module ALSO carries two features added for the wallet-address-login
flow (`Agent/backend/web/identity.py`'s own module docstring has the full
story on why that flow exists and what it deliberately does not verify):

  * The admin role below (`NORABT_ADMIN_TOKEN_SHA256`) can now fall back to
    `OKX_API_KEY` when that env var is unset -- see `_admin_token_hash`'s
    own comment for the project owner's explicit, simulated-account-only
    ruling on this.
  * `create_session_cookie`/`read_session` sign and verify the small,
    HttpOnly session cookie `POST /api/session` (app.py) issues after a
    caller presents either the admin key or a wallet address -- see those
    functions' own docstrings for the cookie's exact (deliberately narrow)
    contents.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# `"tok1:label1,tok2:label2"` -- see `_parse_tokens`. Empty/unset means OPEN
# MODE: every request passes, unchanged from this endpoint's behaviour
# before this module existed. That is the deliberate default (not "fail
# closed") for two reasons the task itself calls out: a fresh dev checkout
# must keep working with zero configuration, and flipping this on must
# never be able to silently lock a service that is already live in
# production out from under an operator who has not yet minted a token.
ACCESS_TOKENS_ENV = "NORABT_ACCESS_TOKENS"

# HMAC key shared by every derived-identifier feature in the web surface
# that needs to be stable, non-reversible, and centrally revocable:
#   * `Agent/backend/web/identity.py`'s `user_ref` (a wallet address ->
#     opaque per-user path segment).
#   * This module's own session cookie signature (`create_session_cookie`/
#     `read_session` below).
# Deliberately SEPARATE from ACCESS_TOKENS_ENV: rotating an ordinary access
# token (revoking one buyer) must not also invalidate every user's derived
# `user_ref` or force every logged-in session to re-authenticate, and
# rotating THIS secret is the one deliberate way to do both of those at
# once (e.g. after a suspected profile-store leak) -- see
# `report_url_secret_bytes`'s own docstring.
REPORT_URL_SECRET_ENV = "NORABT_REPORT_URL_SECRET"

# Fallback HMAC key when REPORT_URL_SECRET_ENV is unset -- mirrors
# data.py's DEFAULT_REPORT_BASE_URL in spirit (a fresh checkout must produce
# a WORKING, deterministic result with zero configuration) but carries none
# of that constant's "this is actively wrong to hand to a stranger" problem:
# an unconfigured secret only means every derived `user_ref`/session cookie
# is forgeable by anyone who reads this source file, which is no worse than
# the obscurity this feature already relies on for an operator who never
# sets a real secret. A real deployment SHOULD override this (see
# Agent/.env.example) -- changing it is also the supported way to
# invalidate every previously issued `user_ref`/session at once.
DEFAULT_REPORT_URL_SECRET = "norabt-default-report-ref-secret-change-me"

# How long GET /admin's "recent codes" registry keeps a bot code around
# after /api/analyze last produced a result for it -- see
# RecentCodeRegistry's own docstring for the full reachability story (in
# particular: a process restart clears this regardless of this TTL, which
# is the trade-off that actually matters in practice). A week is generous
# headroom over any realistic "let me check the admin page" delay while
# still bounding this process's memory to roughly one entry per bot code
# /api/analyze has EVER been asked about in the last week, not forever.
DEFAULT_RECENT_CODE_TTL_SECONDS = 7 * 24 * 3600.0

# Hard cap on how many distinct bot codes `RecentCodeRegistry` remembers at
# once, independent of the 7-day TTL above. Why a cap is needed at all: the
# TTL alone only bounds memory over a QUIET week -- it does nothing to bound
# a BUSY one, and this registry backs GET /admin's "phiên gần đây" listing
# (a code /api/analyze scored live but that has no assessment.json on disk
# at all, see admin_page.py's own docstring) for as long as this process
# runs. 2000 is generous headroom over any realistic week of manual/test
# traffic for this service (a handful of operators, not a high-volume
# public API) while keeping the registry's own memory bounded regardless.
MAX_REMEMBERED_CODES = 2000

_warned_unprotected = False
_warn_lock = threading.Lock()


def _token_repr(token: str) -> str:
    """A token-shaped value safe to put in a log line: the first 4
    characters plus the total length, NEVER the token itself. This is the
    exact "or" alternative the task calls for when no human-supplied label
    exists for a token (see `_parse_tokens`) -- long enough to tell two
    configured tokens apart in a log without ever reconstructing either of
    them from the log alone.
    """
    return f"{token[:4]}…(len={len(token)})"


def _parse_tokens(raw: str) -> Dict[str, str]:
    """`"tok1:label1,tok2:label2"` -> `{"tok1": "label1", "tok2": "label2"}`.

    A bare `"tok3"` with no `:label` gets `_token_repr(tok3)` as its label
    instead of an empty string -- so a label is ALWAYS something safe to
    log/display, never blank and never the raw token. Blank segments
    (leading/trailing/doubled commas) are silently skipped rather than
    raising: a trailing comma or stray whitespace in an ops-edited env var
    must not be able to break every request into this endpoint.

    The label carries no authority of its own -- see the module docstring's
    "Nhãn chỉ để ghi log và hiển thị" rule -- so two tokens accidentally
    sharing one label is harmless; two DIFFERENT tokens are still checked
    independently by `verify_token` regardless of their labels colliding.
    """
    tokens: Dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        token, _, label = part.partition(":")
        token = token.strip()
        if not token:
            continue
        tokens[token] = label.strip() or _token_repr(token)
    return tokens


def load_tokens() -> Dict[str, str]:
    """Read `ACCESS_TOKENS_ENV` at CALL TIME, not import time -- same
    pattern as `data.py`'s `report_base_url()` -- so a test can flip it with
    `monkeypatch.setenv`/`delenv` without ever needing to reload this
    module, and so an operator's env-var change takes effect on the next
    request rather than requiring extra plumbing to notice it.
    """
    return _parse_tokens(os.environ.get(ACCESS_TOKENS_ENV, ""))


def is_protected() -> bool:
    """False (open mode) exactly when no usable token is configured -- see
    `ACCESS_TOKENS_ENV`'s own docstring for why that, not fail-closed, is
    this endpoint's deliberate default.
    """
    return bool(load_tokens())


def warn_once_if_unprotected() -> None:
    """Log a ONE-TIME warning, at most once per process, that
    `/api/analyze` is running with no access-token protection at all.

    Called from `app.py`'s `create_app()` -- i.e. effectively "at startup"
    for a real deployment (one process, one `create_app()` call for its
    whole lifetime) -- so an operator who forgot to set
    `NORABT_ACCESS_TOKENS` sees this in their logs immediately rather than
    discovering it only when someone else finds the open endpoint first.
    Guarded by a lock + module-level flag (not just a flag) because
    `create_app()` can run concurrently with request handling in principle;
    the guard only needs to prevent this from spamming the log on every
    request, not anything stronger.
    """
    global _warned_unprotected
    if _warned_unprotected or is_protected():
        return
    with _warn_lock:
        if _warned_unprotected or is_protected():
            return
        _warned_unprotected = True
    logger.warning(
        "%s chưa được đặt -- /api/analyze đang KHÔNG có lớp bảo vệ token nào, "
        "bất kỳ ai biết URL cũng gọi được. Đây là chế độ mặc định (để không "
        "phá môi trường dev / không khoá chết một dịch vụ đang chạy) -- đặt "
        "biến này (dạng 'token:nhãn,token2:nhãn2') để bật bảo vệ.",
        ACCESS_TOKENS_ENV,
    )


def verify_token(token: Optional[str]) -> Optional[str]:
    """`None` for a missing/unknown token; the configured LABEL (never the
    token itself) for a match.

    Every candidate is compared with `hmac.compare_digest`, never `==`:
    Python's ordinary string `==` short-circuits at the FIRST differing
    character, so comparing against a wrong-but-close guess finishes faster
    than comparing against a wrong guess that happens to share a long
    correct prefix -- an attacker who can measure response time can exploit
    that difference to recover a valid token one byte at a time.
    `hmac.compare_digest` runs in time that depends only on the length of
    its inputs, never on WHERE they first differ, which closes that
    channel. This is checked once per configured token (not once overall),
    so a caller with a huge number of tokens configured leaks a little
    timing information about HOW MANY tokens are configured, never about
    the content of any of them -- an acceptable trade-off for a handful of
    operator-issued keys.

    Never logs the token itself, win or lose -- only the matched label on
    success, or a `_token_repr` (first 4 chars + length) of the REJECTED
    token on failure, per the task's own logging rule.
    """
    if not token:
        return None
    for candidate, label in load_tokens().items():
        if hmac.compare_digest(candidate, token):
            logger.debug("Access token valid (label=%s)", label)
            return label
    logger.warning("Access token rejected (%s)", _token_repr(token))
    return None


# --------------------------------------------------------------------------- #
# Admin role -- a SEPARATE, wider-privilege credential for the team's own
# quick manual testing (plug a bot code in, get an analysis, without the
# ordinary-token gate or its tight per-IP quota in the way). Deliberately
# additive, never a replacement for NORABT_ACCESS_TOKENS/verify_token above:
# an admin key is checked independently, in `app.py`'s `api_analyze`, and
# core scoring logic never learns whether a request was admin or not, same
# as for every ordinary token -- see this module's own docstring.
# --------------------------------------------------------------------------- #

# Holds the SHA-256 hex digest of the admin key, NEVER the key itself. Why a
# hash and not the raw key, unlike ACCESS_TOKENS_ENV above: a `.env` file
# gets copy-pasted between machines, pasted into a chat to ask for help, or
# caught in a screenshot far more often than anyone intends -- storing only
# the hash means a reader of that leaked config file still cannot call the
# endpoint with it (SHA-256 is one-way), whereas a leaked plaintext admin key
# would be immediately usable. See Agent/none/scripts/make_admin_token.py for the
# helper that produces this value, and Agent/.env.example for the operator
# guidance on choosing (and NOT reusing) the underlying secret.
ADMIN_TOKEN_SHA256_ENV = "NORABT_ADMIN_TOKEN_SHA256"

# A SHA-256 digest, hex-encoded, is always exactly 64 characters from
# `0-9a-f` -- uppercase is deliberately rejected (not lowercased and
# retried) because accepting it would mean two different env-var spellings
# ("ABCD..." and "abcd...") silently mean the same thing, which is exactly
# the kind of "did I paste it right?" ambiguity a security-sensitive value
# like this should never tolerate.
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

_warned_bad_admin_token_format = False
_admin_warn_lock = threading.Lock()


def _warn_once_bad_admin_token_format() -> None:
    """Mirrors `warn_once_if_unprotected` above: at most one log line per
    process, however many requests/tests end up calling this with a
    misconfigured value. A malformed `NORABT_ADMIN_TOKEN_SHA256` must never
    be treated as "close enough" -- see `_admin_token_hash`'s own docstring
    -- so this warning exists to make that silent fallback to "no admin"
    actually visible to whoever set the variable wrong.
    """
    global _warned_bad_admin_token_format
    if _warned_bad_admin_token_format:
        return
    with _admin_warn_lock:
        if _warned_bad_admin_token_format:
            return
        _warned_bad_admin_token_format = True
    logger.warning(
        "%s được đặt nhưng KHÔNG phải chuỗi SHA-256 hex 64 ký tự chữ thường "
        "hợp lệ -- coi như KHÔNG có vai admin nào được cấu hình (an toàn hơn "
        "nhiều so với âm thầm chấp nhận một giá trị rác rồi mở toang cổng). "
        "Dùng Agent/none/scripts/make_admin_token.py để sinh lại giá trị đúng.",
        ADMIN_TOKEN_SHA256_ENV,
    )


def _admin_token_hash() -> Optional[str]:
    """The configured admin hash, or `None` when no admin role is usable.

    Distinguishes the env var being ABSENT (the safe, silent default -- see
    `ADMIN_TOKEN_SHA256_ENV`'s own docstring, "không đặt biến -> không có
    admin, mọi thứ y như hiện tại") from it being PRESENT but not a valid
    64-char lowercase hex digest (an operator's typo, a half-pasted value, a
    raw key pasted here by mistake instead of its hash): the latter warns
    exactly once (`_warn_once_bad_admin_token_format`) precisely because
    silently falling back to "no admin" there, with no signal at all, would
    let an operator believe admin access is configured when it is not.
    Either way the return value is the same (`None`) -- only the LOGGING
    differs -- so callers never need their own absent-vs-malformed branch.

    OKX_API_KEY FALLBACK -- project owner's explicit ruling for THIS stage
    of the product (a simulated/demo OKX account; see Agent/.env.example's
    own comment on this env var for the tài khoản thật caveat): when
    `ADMIN_TOKEN_SHA256_ENV` is not set AT ALL (note: absent, not merely
    malformed -- a malformed value already warns and returns `None` above,
    and must NOT silently fall through to a different secret than the one
    the operator typed), the admin key becomes whatever `OKX_API_KEY` is
    currently set to. This reuses a secret the project already has lying
    around for a demo account instead of forcing an operator to mint a
    second one before the admin role is usable at all. `NORABT_ADMIN_TOKEN_SHA256`
    still WINS whenever it is set, precisely so this can be split into its
    own dedicated secret later with no code change -- only an env var
    added.

    The comparison this feeds (`verify_admin_token` below) always re-hashes
    the PRESENTED token and compares DIGESTS via `hmac.compare_digest`,
    never the raw `OKX_API_KEY` string itself -- so this fallback does not
    weaken the "never log/compare the raw secret" discipline the rest of
    this module already follows for the dedicated-hash path. `OKX_API_KEY`
    itself is read fresh from `os.environ` on every call (not cached, not
    read via `Agent.backend.infra.config.config`, whose attributes are
    fixed at process/import time) -- the same "read live" pattern this
    module's other env-backed functions already use, so a test can flip it
    with `monkeypatch.setenv`/`delenv` without reloading anything, and an
    operator's env change takes effect on the next request.
    """
    if ADMIN_TOKEN_SHA256_ENV in os.environ:
        raw = os.environ[ADMIN_TOKEN_SHA256_ENV].strip()
        if _SHA256_HEX_RE.match(raw):
            return raw
        _warn_once_bad_admin_token_format()
        return None
    okx_api_key = os.environ.get("OKX_API_KEY", "").strip()
    if okx_api_key:
        return hashlib.sha256(okx_api_key.encode("utf-8")).hexdigest()
    return None


def is_admin_configured() -> bool:
    """`True` exactly when a usable admin hash is configured -- the
    admin-role counterpart to `is_protected()` above, and the cheap
    short-circuit `app.py` uses to decide whether it is even worth trying to
    resolve an admin token out of a request at all.
    """
    return _admin_token_hash() is not None


def verify_admin_token(token: Optional[str]) -> bool:
    """`True` when `token` is the RAW admin key matching the configured
    hash, `False` for anything else (no admin configured, no token, or a
    wrong one) -- deliberately a plain bool, unlike `verify_token`'s label,
    because there is exactly one admin role, nothing to distinguish by name.

    Always re-hashes `token` and compares the DIGEST with
    `hmac.compare_digest`, never the raw strings -- this is what makes the
    stored value a genuine one-way hash instead of just an obfuscated copy
    of the key: presenting the hash itself as if it were the key hashes to
    a completely different digest and is correctly rejected (see the task's
    own required test for this). `hmac.compare_digest` (not `==`) for the
    same constant-time reasoning `verify_token` documents above -- a hash
    comparison is exactly as vulnerable to a timing side-channel as a raw
    token comparison would be.

    Never logs `token` in any form, win or lose -- unlike `verify_token`,
    which logs a `_token_repr` of a REJECTED ordinary token, this function
    logs nothing on failure at all: an admin key is meant to be a single
    shared team secret rather than one of several per-buyer tokens, so
    there is no "which configured admin key was this" label worth logging,
    and the task's own logging rule for this feature is unconditional
    ("khoá admin không được xuất hiện ... trong ... bất kỳ dòng log nào").
    """
    if not token:
        return False
    configured = _admin_token_hash()
    if configured is None:
        return False
    candidate = hashlib.sha256(token.encode("utf-8")).hexdigest()
    if hmac.compare_digest(candidate, configured):
        logger.debug("Admin access token valid")
        return True
    return False


def report_url_secret_bytes() -> bytes:
    """The HMAC key shared by `Agent/backend/web/identity.py`'s `user_ref`
    derivation and this module's own session-cookie signing (see
    `create_session_cookie`/`read_session` below) -- see
    `REPORT_URL_SECRET_ENV`'s own comment for why the two share one secret.
    Public (not a leading-underscore name) specifically so `identity.py` can
    import it directly rather than each module rolling its own copy of
    "read this env var, or fall back to the default" -- a second copy of
    that one-liner would be harmless today, but it is exactly the kind of
    thing that quietly drifts (a fixed typo applied to only one copy, a
    default changed in only one place) the next time either module is
    touched.
    """
    return os.environ.get(REPORT_URL_SECRET_ENV, DEFAULT_REPORT_URL_SECRET).encode(
        "utf-8"
    )


class RecentCodeRegistry:
    """The "sổ tra cứu nhỏ" `GET /admin` needs: a TTL-bounded set of bot
    codes `POST/GET /api/analyze` has recently produced a result for, so
    the admin listing page can show a code that was scored LIVE this
    session even though it has no `assessment.json` on disk at all (see
    `Agent/backend/web/admin_page.py`'s own module docstring, "recent_codes"
    -- that module is a pure renderer and never touches this class itself;
    `app.py`'s `admin_page` route is what reads `.codes()` and hands the
    result to it).

    Deliberately in-memory only, with NO persistence layer (no database,
    no file). This is a conscious trade-off, not an oversight: adding a
    second piece of durable state purely to remember "which codes were
    recently analyzed" would be a disproportionate amount of new
    infrastructure for what this feature needs. The cost is explicit and
    must stay visible to whoever operates this service: restarting the
    process (a deploy, a crash, `docker compose restart`, ...) empties this
    registry completely, so a code scored live just before a restart drops
    out of the admin page's "phiên gần đây" section until it is analyzed
    again -- it never disappears from `GET /api/bots`/disk-backed listings,
    which need no registry at all.

    Also bounded by `MAX_REMEMBERED_CODES` (see that constant's own
    comment for why the TTL alone is not enough): once that many DISTINCT
    codes are remembered, adding one more evicts whichever code is
    currently EARLIEST to expire, i.e. the oldest one that has not been
    re-analyzed since. In practice this only bites during an unusually busy
    stretch (many more than 2000 distinct codes analyzed within one TTL
    window); a quiet week never reaches the cap at all and behaves exactly
    as if it did not exist.
    """

    def __init__(
        self,
        ttl_seconds: float = DEFAULT_RECENT_CODE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        max_codes: int = MAX_REMEMBERED_CODES,
    ) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._max_codes = max_codes
        # An OrderedDict, not a plain dict: `remember` explicitly
        # `move_to_end`s a code on every call (including a refresh of one
        # already present), so iteration order is always "earliest to
        # expire first" -- every entry shares the same TTL, so the one
        # remembered/refreshed longest ago is also the one expiring
        # soonest. That invariant is what lets both eviction (below) and
        # TTL pruning (`codes()`) drop entries from the FRONT in O(1) each,
        # instead of scanning the whole registry for a minimum every time.
        self._expires_at: "OrderedDict[str, float]" = OrderedDict()
        self._lock = threading.Lock()

    def remember(self, code: str) -> None:
        with self._lock:
            self._expires_at[code] = self._clock() + self._ttl
            # Re-assigning an existing key does NOT move it in an
            # OrderedDict on its own -- move_to_end is required so a
            # re-analyzed code's later expiry is reflected in its
            # position too, keeping the "front = earliest to expire"
            # invariant true even for a code seen more than once.
            self._expires_at.move_to_end(code)
            while len(self._expires_at) > self._max_codes:
                # popitem(last=False) drops the FRONT entry (oldest /
                # earliest to expire) in O(1) -- see MAX_REMEMBERED_CODES
                # and this class's own docstring for what this means for
                # an operator once it actually triggers.
                self._expires_at.popitem(last=False)

    def codes(self) -> List[str]:
        """Every code currently remembered, pruning anything past its TTL
        first. Pruning here (on read) rather than on a timer is enough:
        this registry never grows unboundedly between reads because
        `GET /admin` -- the only reader -- calls this on every request.

        Prunes from the front and stops at the first still-live entry
        (rather than scanning every entry) -- safe because of the exact
        same "front = earliest to expire" invariant `remember` maintains:
        once one entry is not yet expired, nothing after it can be either.
        """
        now = self._clock()
        with self._lock:
            while self._expires_at:
                oldest_code = next(iter(self._expires_at))
                if self._expires_at[oldest_code] > now:
                    break
                del self._expires_at[oldest_code]
            return list(self._expires_at.keys())


# --------------------------------------------------------------------------- #
# Session cookie -- POST /api/session (app.py) issues this after a caller
# presents either the admin key or a wallet address (see
# `Agent/backend/web/identity.py`'s module docstring for the wallet-login
# flow this backs, including the accepted risk it deliberately does not
# eliminate). Every later request that carries this cookie is treated as
# "this browser is user X" (or "is admin") for exactly as long as the
# cookie is valid -- see `read_session` below for what that check actually
# verifies and, just as importantly, does NOT verify.
# --------------------------------------------------------------------------- #

# 8 hours, per the task's own explicit choice: long enough that a user
# opening a handful of report links across one sitting is never asked to
# re-enter their wallet address mid-session, short enough that a cookie
# copied out of a shared/borrowed browser does not stay usable indefinitely.
SESSION_TTL_SECONDS = 8 * 3600.0

# Name of the cookie itself -- one shared constant so app.py's Set-Cookie/
# delete-cookie calls and this module's own verification can never drift
# apart on the name they each use.
SESSION_COOKIE_NAME = "norabt_session"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    # `urlsafe_b64decode` requires its input padded to a multiple of 4
    # characters -- this function only ever unpads on the way out
    # (`_b64url_encode` above strips `=`), so it must re-pad on the way
    # back in. `-len(text) % 4` is 0/1/2/3 padding chars needed; `%` on a
    # negative Python int already returns a non-negative result, so this
    # never needs a separate "if already a multiple of 4" branch.
    padded = text + "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def create_session_cookie(
    *,
    user_ref: Optional[str] = None,
    is_admin: bool = False,
    ttl_seconds: float = SESSION_TTL_SECONDS,
    now_ms: Optional[int] = None,
) -> str:
    """Build the signed cookie VALUE for `Set-Cookie: norabt_session=...`.

    The cookie's payload is deliberately minimal -- `{"exp_ms": ..., "ref":
    user_ref}` for a user session, `{"exp_ms": ..., "admin": true}` for an
    admin one -- and, per the task's own hard requirement, NEVER contains
    the wallet address or the admin key itself, only the ALREADY-DERIVED
    `user_ref` (see identity.py's `user_ref`, itself non-reversible) or a
    bare boolean flag. A cookie is exactly the kind of value that ends up
    copied into a bug report, sits in a browser's local storage/dev tools,
    or gets logged by some unrelated piece of middleware somewhere on its
    trip through the network -- it must be safe to treat as semi-public
    exactly the way a `user_ref` already is (see identity.py's own
    docstring on why THAT is a one-way hash and not the address itself),
    never as safe as a value nobody but this server ever sees.

    Format: `base64url(json_payload) + "." + hex_hmac_sha256(same_key,
    that_base64url_string)`, mirroring the shape (if not the exact
    algorithm) of a JWT closely enough to be recognizable, without adding a
    JWT LIBRARY dependency this project does not otherwise need for one
    small, fixed-shape cookie. Signed with `report_url_secret_bytes()` --
    see that function's own docstring for why it is shared with
    `identity.py`'s `user_ref` derivation (one secret, one rotation lever
    for both).

    `now_ms`/`ttl_seconds` are injectable so a test can construct an
    already-expired (or about-to-expire) cookie deterministically instead
    of racing wall-clock time or sleeping.
    """
    exp_ms = int(now_ms if now_ms is not None else time.time() * 1000) + int(
        ttl_seconds * 1000
    )
    payload: Dict[str, Any] = {"exp_ms": exp_ms}
    if is_admin:
        payload["admin"] = True
    else:
        payload["ref"] = user_ref
    body = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        report_url_secret_bytes(), body.encode("ascii"), hashlib.sha256
    ).hexdigest()
    return f"{body}.{signature}"


def read_session(cookie_value: Optional[str]) -> Optional[Dict[str, Any]]:
    """Verify and decode a `norabt_session` cookie value, or `None` for
    anything missing, malformed, tampered with, or expired -- every one of
    those collapses to the same `None` (never a raised exception, never a
    distinguishable error) because every caller in app.py only ever has one
    reaction to "this is not a currently-valid session": treat the request
    as anonymous/logged-out.

    On success, returns `{"is_admin": bool, "user_ref": Optional[str]}` --
    always both keys, so a caller never has to guard against a missing key,
    only branch on `is_admin`.

    Verification order matters: the HMAC signature is checked FIRST, with
    `hmac.compare_digest` (constant-time, same reasoning as every other
    signature/token comparison in this module) -- only once the signature
    is confirmed to match does this even attempt to `json.loads` the
    payload. A cookie is client-supplied input; verifying the signature
    before parsing means a forged/corrupted cookie is rejected on the cheap
    string-compare path and never reaches the JSON parser at all.
    """
    if not cookie_value or "." not in cookie_value:
        return None
    body, _, signature = cookie_value.rpartition(".")
    if not body or not signature:
        return None
    expected = hmac.new(
        report_url_secret_bytes(), body.encode("ascii"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        payload = json.loads(_b64url_decode(body))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    exp_ms = payload.get("exp_ms")
    if not isinstance(exp_ms, (int, float)) or time.time() * 1000 > exp_ms:
        return None
    if payload.get("admin") is True:
        return {"is_admin": True, "user_ref": None}
    ref = payload.get("ref")
    if not isinstance(ref, str) or not ref:
        return None
    return {"is_admin": False, "user_ref": ref}
