"""Wallet-address-based user identity for the OKX A2MCP web surface.

WHY THIS MODULE EXISTS -- the constraint that forced this design: this
service is listed on the OKX AI Marketplace with `fee = 0`, and the project
owner has independently verified that at `fee = 0` OKX creates no
task/order at all and forwards NO buyer identity whatsoever to this
endpoint (see `Agent/backend/web/access.py`'s module docstring for the same
finding from the token side). There is therefore no protocol-level way for
this service to know which OKX user is calling it. The owner's accepted
answer, after being warned about the consequence spelled out below, is:
the user SELF-DECLARES their wallet address once (at "purchase" time) and
again every session (to "log back in"), and this module is what turns that
self-declared address into a stable per-user identity and an on-disk
profile -- nothing more.

ACCEPTED, NOT REVISITED, RISK: a wallet address is public on-chain data.
Anyone who knows another person's address can type it in here and be
treated as that person -- there is no signature, no proof of ownership,
just a self-declared string. The owner was told this and chose to ship
anyway for this stage of the product; every user-facing message this
module (and its callers) produce around wallet-address entry must say so
plainly, per the project's own instruction -- see `WALLET_DISCLAIMER_VI`
below, which every caller that surfaces a wallet-address-related message to
a user is expected to fold in.

WHY THE URL/PROFILE KEY IS A DERIVED HASH, NEVER THE RAW ADDRESS ITSELF:
the address is this user's identity, and identities leak sideways through
channels that were never designed to carry secrets -- a link pasted into a
chat and forwarded, a browser's own history/autocomplete, an HTTP
`Referer` header sent to a third party when a report page links out
anywhere. None of those leaks care whether the string they carry is
"supposed" to be private; a URL segment is exactly as exposed as the
channel it travels through. Deriving a one-way, per-address `user_ref` (see
`user_ref` below) means every one of those leaks exposes only an opaque
token tied to OKX_API_KEY-style "whoever holds this out-of-band knowledge",
never the address itself -- so a leaked report link never hands out a
user's wallet identity, even though the link's own access control (see
`load_profile`/callers in app.py) is honest that the wallet address itself
was never verified to begin with.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from Agent.backend.infra.config import config
from Agent.backend.web.access import report_url_secret_bytes

# One sentence every caller that surfaces a wallet-address-related message
# (the /api/session error/success bodies in app.py, today) must fold into
# its own Vietnamese text -- see this module's own docstring for why the
# project owner accepted this risk instead of eliminating it. Kept as one
# shared constant, not re-typed at each call site, so the wording can never
# drift between the places that show it.
WALLET_DISCLAIMER_VI = (
    "The wallet address is a self-declared identifier -- the system has NOT "
    "verified ownership of this wallet (no signature, no proof of ownership)."
)

# --------------------------------------------------------------------------- #
# Wallet address validation
# --------------------------------------------------------------------------- #

# `0x` + exactly 40 hex characters -- the standard EVM address shape. Case is
# intentionally NOT part of this check (see `normalize_wallet_address`
# below): EVM addresses are case-INsensitive at the protocol level (the
# mixed-case form some wallets display is an optional EIP-55 checksum
# convention, not a different address), so validating case here would
# reject perfectly valid input for no security benefit.
_WALLET_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


class InvalidWalletAddressError(ValueError):
    """A caller-supplied wallet address failed format validation. Maps to
    HTTP 400 wherever this is raised through app.py, never 500 -- this is
    untrusted user input, not a server error.
    """


def normalize_wallet_address(raw: Any) -> str:
    """Validate `raw` as a `0x` + 40-hex-char EVM address and return it
    LOWERCASED.

    Lowercasing BEFORE any hashing/storage is load-bearing, not cosmetic:
    `0xAA17...` and `0xaa17...` are the exact same on-chain address (EVM
    addresses are case-insensitive; the mixed-case form is only an optional
    EIP-55 checksum display convention), so if this module ever derived two
    different `user_ref`s for the same address typed in two different
    letter cases, a user who logged in once with one casing and again with
    the other would silently land on a brand-new, empty profile instead of
    their own -- an unrecoverable "lost my history" bug from the user's own
    point of view, for a input difference that means nothing on-chain.
    Every caller (session creation, `user_ref` derivation) MUST route
    through this function first, never hash/store a caller-supplied address
    as typed.
    """
    if not isinstance(raw, str):
        raise InvalidWalletAddressError(
            "The wallet address must be a text string: '0x' followed by 40 hex characters"
        )
    candidate = raw.strip()
    if not _WALLET_ADDRESS_RE.match(candidate):
        raise InvalidWalletAddressError(
            "The wallet address is not in the right format -- it must be "
            "exactly '0x' followed by 40 hex characters (0-9, a-f), e.g. "
            "'0x1234567890abcdef1234567890abcdef12345678'. The system does "
            "NOT guess or auto-correct the address -- please paste it again exactly."
        )
    return candidate.lower()


# --------------------------------------------------------------------------- #
# user_ref derivation
# --------------------------------------------------------------------------- #

# Length of the derived `user_ref`. 10 characters of base32 (5 bits/char) is
# 50 bits of the underlying HMAC digest -- far more than enough to make
# guessing one by brute force pointless for this feature's actual threat
# model (an obscure, hard-to-guess path segment; see this module's own
# docstring for what it is and is not defending against), while keeping the
# `<user_ref>_<code>` URL short. Kept as a named constant because app.py's
# route pattern and every test that hand-builds a `user_ref`-shaped string
# must agree with it exactly.
USER_REF_LENGTH = 10

# Base32's alphabet, lowercased, is `[a-z2-7]` -- no digits 0/1/8/9 (dropped
# by base32 specifically because they are easily confused with O/I/B/g in
# some fonts) and, crucially for this project, NO UNDERSCORE: `user_ref` and
# `code` are joined as `<user_ref>_<code>` in a single URL path segment (see
# app.py's new report route), so `user_ref` itself must never be able to
# contain the separator it sits next to -- otherwise splitting that segment
# back into its two parts would be ambiguous. Anchored full-match, exact
# length: this is also the whitelist a `user_ref` taken from an untrusted
# URL path segment is checked against before it is ever used to build a
# filesystem path (see `_profile_dir` below) -- the same
# validate-before-it-touches-a-path-join discipline
# `Agent/backend/scripts/agent_server.py`'s `_require_token`/`_SAFE_TOKEN` and
# `Agent/backend/web/data.py`'s `validate_unique_code` already use elsewhere
# in this project.
USER_REF_RE = re.compile(rf"^[a-z2-7]{{{USER_REF_LENGTH}}}$")


def user_ref(wallet_address: str) -> str:
    """Derive the opaque, URL-safe, non-reversible `user_ref` this module's
    on-disk profile store is keyed by.

    `wallet_address` is lowercased again here (belt and suspenders on top
    of `normalize_wallet_address`'s own lowercasing -- see that function's
    docstring for why case must never affect the result) so this function
    is safe to call directly with any already-known-valid address without
    every caller having to remember to normalize first.

    HMAC-SHA256(NORABT_REPORT_URL_SECRET, lowercased address), encoded as
    lowercase base32 and truncated to `USER_REF_LENGTH` characters:

      * STABLE: a pure function of (secret, address) -- the same address
        under the same secret always derives the same `user_ref`, with no
        state persisted anywhere to make that true (mirrors
        `access.py`'s -- now removed -- `build_report_ref`'s reasoning for
        the same property).
      * NON-REVERSIBLE: HMAC-SHA256 cannot be inverted, so a `user_ref`
        leaking (in a URL, a log line, ...) never discloses the wallet
        address it was derived from -- see this module's own docstring for
        why that matters here specifically (a user's wallet address IS
        their identity).
      * URL-SAFE AND SEPARATOR-FREE: base32's alphabet is `[A-Z2-7]`
        (lowercased here to `[a-z2-7]`) -- no `_`, `+`, `/`, or `=` padding
        survives the truncation, so this can be dropped straight into a
        URL path segment, or joined with a bot `code` via `_`, with no
        percent-encoding and no ambiguity about where the separator is.
      * SECRET-ROTATABLE: reusing `NORABT_REPORT_URL_SECRET` (see
        `access.py`) rather than a dedicated secret means rotating that one
        env var -- already documented as "invalidates every previously
        issued report link" -- ALSO reassigns every user a new `user_ref`
        at once, which is the correct, if blunt, way to fully sever this
        service's derived identifiers from every wallet address it has
        ever seen (e.g. after a suspected profile-store leak).
    """
    lowered = wallet_address.strip().lower()
    digest = hmac.new(
        report_url_secret_bytes(), lowered.encode("utf-8"), hashlib.sha256
    ).digest()
    encoded = base64.b32encode(digest).decode("ascii").rstrip("=").lower()
    return encoded[:USER_REF_LENGTH]


class InvalidUserRefError(ValueError):
    """A `user_ref` taken from an untrusted source (a URL path segment)
    failed `USER_REF_RE`'s format check. Never let a value that fails this
    reach a path join -- see `_profile_dir` below, the sole place this
    module turns a `user_ref` into a filesystem path.
    """


def _validate_user_ref(raw: Any) -> str:
    if not isinstance(raw, str) or not USER_REF_RE.match(raw):
        raise InvalidUserRefError(
            f"Invalid user_ref: it must be exactly {USER_REF_LENGTH} lowercase "
            "base32 characters (a-z, 2-7)"
        )
    return raw


# --------------------------------------------------------------------------- #
# On-disk profile store: data/users/<user_ref>/profile.json
# --------------------------------------------------------------------------- #

# Default root for every user's profile directory. Computed once at import
# time from `config.DATA_DIR`, exactly like `Agent/backend/web/app.py`'s own
# `DEFAULT_DASHBOARD_PATH` -- callers that need a different root (every test
# in this project that touches disk) override it via the `users_root`
# keyword every function below accepts, the same injectable-default pattern
# `WebDataService.__init__`'s own `data_dir` parameter already uses.
DEFAULT_USERS_ROOT = Path(config.DATA_DIR) / "report" / "users"

# Hard cap on how many `analyzed` entries a single profile keeps, most
# recent first survival. Unbounded growth here would mean a single very
# active user's profile.json grows forever, costing more to read/write/
# atomically-replace on every single future analysis for them specifically.
# 200 is generous headroom over any realistic manual usage pattern for this
# dashboard (a human clicking "analyze" bot-by-bot) while keeping the file
# small enough that a rewrite is always cheap -- there is no product
# requirement to keep a user's FULL lifetime history, only their recent one
# (old report links for a trimmed-off code simply stop resolving, same
# trade-off `access.py`'s `RecentCodeRegistry` already documents for its own
# cap).
MAX_ANALYZED_HISTORY = 200


def _profile_dir(user_ref_value: str, *, users_root: Path = DEFAULT_USERS_ROOT) -> Path:
    """Turn a `user_ref` into its profile directory, validating FIRST.

    This is the ONE place in this module that joins an untrusted-origin
    string (a `user_ref` may arrive straight from a URL path segment, see
    app.py's new report route) onto a filesystem path -- every other
    function below goes through this, so there is exactly one choke point
    to audit for path-traversal safety, matching the project's existing
    precedent (`Agent/backend/scripts/agent_server.py`'s `_require_token`,
    `Agent/backend/web/data.py`'s `validate_unique_code`).

    `USER_REF_RE`'s anchored `^[a-z2-7]{10}$` match means a value containing
    `/`, `..`, `%2f`, or any character outside `[a-z2-7]` is rejected by
    `_validate_user_ref` BEFORE it ever reaches `Path.__truediv__` below --
    so this can never construct a path outside `users_root`, regardless of
    what a hostile caller puts in the raw string.
    """
    validated = _validate_user_ref(user_ref_value)
    return Path(users_root) / validated


def _profile_path(
    user_ref_value: str, *, users_root: Path = DEFAULT_USERS_ROOT
) -> Path:
    return _profile_dir(user_ref_value, users_root=users_root) / "profile.json"


class ProfileStoreError(RuntimeError):
    """Raised by `get_or_create_profile`/`record_analysis` below when the
    on-disk profile store cannot be written to for an OPERATIONAL reason --
    a read-only filesystem, a full disk, or wrong permissions on
    `users_root`. See `Agent/docker/docker-compose.yml`'s mount comment for
    the concrete incident this guards against: `Agent/data` is bind-mounted
    read-only except for a couple of writable sub-paths, and a
    misconfigured or not-yet-created `data/users/` on the host reproduces
    exactly this (`[Errno 30] Read-only file system`).

    WHY WRAP `OSError` AT ALL, RATHER THAN LETTING IT BUBBLE UP: app.py's
    own last-line-of-defence exception handler used to interpolate a caught
    exception's `str()` straight into the JSON body sent back to an
    internet-facing caller -- for a bare `OSError` that means the absolute
    in-container path, the OS errno, and words like "Read-only file
    system" all leaking to whoever is probing this endpoint. Raising this
    project-specific exception instead gives app.py a type it can catch ON
    PURPOSE and turn into one short, generic Vietnamese message plus an
    incident code (see app.py's `_log_incident`), while the ORIGINAL
    `OSError` stays attached via `__cause__` (Python's own `raise ... from
    exc`) for whoever reads the server log next to that same incident code.

    Deliberately caught ONLY at the `get_or_create_profile`/
    `record_analysis` call sites, not inside `_write_json_atomic` itself:
    a bug inside the write path (e.g. `json.dump` choking on a
    non-serializable value) is a PROGRAMMING error, not an "operational
    disk problem", and must keep surfacing as whatever exception it
    actually is -- see
    `test_atomic_write_failure_leaves_original_file_untouched` in
    test_web_identity.py, which pins a `RuntimeError` from a patched
    `json.dump` propagating UNCHANGED out of `_write_json_atomic` -- not
    get relabeled as a storage incident that would mislead an operator
    into checking disk/permissions for a bug that has nothing to do with
    either.
    """


def _write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    """Write `data` to `path` as JSON, atomically.

    WHY THIS EXISTS: this store can be written concurrently -- two requests
    for the same user (a session touch and a just-finished analysis, or two
    browser tabs) can race to update the same `profile.json`. Writing
    directly to `path` (open, write, close) leaves a window where a crash,
    an out-of-disk-space error, or simply another process reading the file
    mid-write sees a truncated/corrupt JSON document -- which would then
    make EVERY future read of this profile fail, permanently, until someone
    notices and repairs the file by hand.

    The fix is the standard POSIX atomic-replace pattern: write the full
    new content to a TEMPORARY file in the SAME directory (same filesystem
    -- required for `os.replace` to be atomic; a temp dir on a different
    mount would silently degrade to copy+delete, which is not atomic), then
    `os.replace(tmp, path)`. `os.replace` is a single filesystem-level
    rename: any reader either sees the complete OLD file or the complete
    NEW one, never a partial write, and never raises if `path` does not
    exist yet (unlike `os.rename` on some platforms) -- which is exactly
    the "first time this user is seen" case `get_or_create_profile` below
    needs. If anything fails between the temp file being created and the
    replace happening, the `finally` block below removes the temp file and
    the ORIGINAL `path` is left completely untouched -- a failed write can
    never corrupt or truncate an existing good profile.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=".profile-", suffix=".json.tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _now_ms() -> int:
    return int(time.time() * 1000)


def load_profile(
    user_ref_value: str, *, users_root: Path = DEFAULT_USERS_ROOT
) -> Optional[Dict[str, Any]]:
    """Read `<users_root>/<user_ref>/profile.json`, or `None` when it does
    not exist, `user_ref_value` fails format validation, or the file on
    disk is not valid JSON (a torn write from BEFORE this module's atomic
    write discipline existed, or manual tampering) -- every one of those
    is treated as "no profile", never a raised exception, since every
    caller of this function (app.py's session/report routes) already has a
    single well-defined "not found" response to fall back to.
    """
    try:
        path = _profile_path(user_ref_value, users_root=users_root)
    except InvalidUserRefError:
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def get_or_create_profile(
    wallet_address_raw: Any, *, users_root: Path = DEFAULT_USERS_ROOT
) -> Dict[str, Any]:
    """`POST /api/session`'s "tạo user khi mua / khớp khi dùng lại" step.

    Validates + normalizes `wallet_address_raw` (raises
    `InvalidWalletAddressError` for a bad format -- callers map that to
    HTTP 400), derives its `user_ref`, then either:

      * the profile does not exist yet -> create it, with
        `created_at_ms == last_seen_ms == now`, an empty `analyzed` list;
      * it already exists -> update `last_seen_ms` to now, WITHOUT ever
        touching `created_at_ms` (the whole point of that field is to
        record when this identity was first seen, which by definition
        never changes again) or `analyzed` (a session touch alone is not
        an analysis).

    Either branch writes the result back atomically (see
    `_write_json_atomic`) before returning it, so the returned dict always
    matches what is now on disk.
    """
    wallet_address = normalize_wallet_address(wallet_address_raw)
    ref = user_ref(wallet_address)
    now = _now_ms()
    existing = load_profile(ref, users_root=users_root)
    if existing is not None:
        existing["last_seen_ms"] = now
        # `wallet_address`/`user_ref` are re-asserted (not merely trusted
        # from the old file) so a profile written by a future version of
        # this module with a different key set still self-heals on the
        # next touch, rather than a stale copy propagating forever.
        existing["wallet_address"] = wallet_address
        existing["user_ref"] = ref
        existing.setdefault("analyzed", [])
        profile = existing
    else:
        profile = {
            "user_ref": ref,
            "wallet_address": wallet_address,
            "created_at_ms": now,
            "last_seen_ms": now,
            "analyzed": [],
        }
    # Translate an OPERATIONAL disk failure (read-only mount, full disk,
    # bad permissions on users_root) into ProfileStoreError HERE, at the
    # public API boundary -- see that class's own docstring for why this is
    # the right place (not inside _write_json_atomic itself) and why only
    # OSError, never any other exception type, is caught.
    try:
        _write_json_atomic(_profile_path(ref, users_root=users_root), profile)
    except OSError as exc:
        raise ProfileStoreError(
            "could not write the user profile to disk (users_root may be "
            "read-only, full, or have the wrong permissions)"
        ) from exc
    return profile


def record_analysis(
    user_ref_value: str,
    code: str,
    name: Optional[str],
    verdict: Optional[str],
    *,
    users_root: Path = DEFAULT_USERS_ROOT,
) -> Optional[Dict[str, Any]]:
    """Append one `{code, name, at_ms, verdict}` entry to this user's
    `analyzed` history -- called from `POST /api/analyze` in app.py once a
    logged-in user's session has scored a bot, and the thing that makes
    `GET /<user_ref>_<code>` (app.py's new report route) subsequently
    answer 200 for that exact pair.

    Deduplicates by `code`: an entry for a code the user already analyzed
    before is REPLACED (dropped, then re-appended at the end) rather than
    duplicated, so re-analyzing the same bot moves it to the "most
    recent" end of the list instead of growing it with stale copies. The
    list is then trimmed to the `MAX_ANALYZED_HISTORY` most recent entries
    -- see that constant's own comment for why a cap exists at all.

    Returns the updated profile, or `None` if no profile exists for
    `user_ref_value` (or it fails format validation) -- this is a defensive
    no-op, not an error: every caller only ever reaches this with a
    `user_ref` that came from a session this process itself just verified
    (see `access.read_session`), so a missing profile here would mean the
    on-disk file was deleted out from under a live session, an operational
    anomaly this function is not in a position to repair (it does not have
    the wallet address needed to recreate the profile from scratch).
    """
    profile = load_profile(user_ref_value, users_root=users_root)
    if profile is None:
        return None
    analyzed: List[Dict[str, Any]] = [
        item
        for item in (profile.get("analyzed") or [])
        if isinstance(item, dict) and item.get("code") != code
    ]
    analyzed.append(
        {"code": code, "name": name, "at_ms": _now_ms(), "verdict": verdict}
    )
    # Keep only the MOST RECENT `MAX_ANALYZED_HISTORY` entries -- the list is
    # built oldest-first (append-only above), so the tail is the newest.
    if len(analyzed) > MAX_ANALYZED_HISTORY:
        analyzed = analyzed[-MAX_ANALYZED_HISTORY:]
    profile["analyzed"] = analyzed
    profile["last_seen_ms"] = _now_ms()
    # Same OSError -> ProfileStoreError translation as get_or_create_profile
    # above, and for the same reason -- see ProfileStoreError's docstring.
    try:
        _write_json_atomic(
            _profile_path(user_ref_value, users_root=users_root), profile
        )
    except OSError as exc:
        raise ProfileStoreError(
            "could not write the user's analysis history to disk "
            "(users_root may be read-only, full, or have the wrong permissions)"
        ) from exc
    return profile


def has_analyzed(profile: Dict[str, Any], code: str) -> bool:
    """Whether `profile["analyzed"]` already records `code` -- the exact
    check `GET /<user_ref>_<code>` (app.py) uses to decide whether this
    (user_ref, code) pair may be viewed. A plain helper rather than inline
    list comprehension at every call site, so the "what counts as a match"
    rule lives in exactly one place.
    """
    return any(
        isinstance(item, dict) and item.get("code") == code
        for item in (profile.get("analyzed") or [])
    )
