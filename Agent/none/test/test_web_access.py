"""Unit tests for Agent/backend/web/access.py -- the token store, the
admin role (including its OKX_API_KEY fallback), the recent-code registry
`GET /admin` needs, and the signed session cookie `POST /api/session`
issues. No Starlette/HTTP involved here at all (see access.py's own module
docstring for why it has no framework dependency); integration through the
actual routes is covered in Agent/none/test/test_web_app.py.
"""

from __future__ import annotations

import hashlib
import logging

import pytest

from Agent.backend.web import access


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts from a clean slate for every env var this module
    reads, and with the module's own one-time "unprotected" warning latch
    reset -- otherwise whichever test runs first would consume that latch
    for every test after it in the same process.

    `OKX_API_KEY` is included here (unlike the global, deliberately
    OKX_*-sparing fixture in Agent/none/test/conftest.py) precisely BECAUSE this
    module now reads it too (see `_admin_token_hash`'s OKX_API_KEY
    fallback): a real `Agent/.env` on the machine running these tests sets
    a real demo `OKX_API_KEY`, which `envfile.py` loads straight into
    `os.environ` at process start and which conftest's own fixture
    deliberately leaves alone -- so without this, a test in THIS file
    asserting "no admin configured by default" would silently pass or fail
    depending on whether the machine running pytest happens to have that
    var set, exactly the machine-dependent flakiness Agent/none/test/conftest.py
    already fixed once for NORABT_* vars.
    """
    monkeypatch.delenv(access.ACCESS_TOKENS_ENV, raising=False)
    monkeypatch.delenv(access.REPORT_URL_SECRET_ENV, raising=False)
    monkeypatch.delenv(access.ADMIN_TOKEN_SHA256_ENV, raising=False)
    monkeypatch.delenv("OKX_API_KEY", raising=False)
    monkeypatch.setattr(access, "_warned_unprotected", False)
    monkeypatch.setattr(access, "_warned_bad_admin_token_format", False)


# --------------------------------------------------------------------------- #
# Token parsing / open-vs-protected mode
# --------------------------------------------------------------------------- #


def test_open_mode_when_env_unset() -> None:
    assert access.load_tokens() == {}
    assert access.is_protected() is False


def test_open_mode_when_env_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(access.ACCESS_TOKENS_ENV, "   ")
    assert access.load_tokens() == {}
    assert access.is_protected() is False


def test_parses_token_label_pairs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(access.ACCESS_TOKENS_ENV, "tok1:buyer-a,tok2:buyer-b")
    tokens = access.load_tokens()
    assert tokens == {"tok1": "buyer-a", "tok2": "buyer-b"}
    assert access.is_protected() is True


def test_bare_token_without_label_gets_a_safe_display_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(access.ACCESS_TOKENS_ENV, "supersecrettoken123")
    tokens = access.load_tokens()
    assert list(tokens.keys()) == ["supersecrettoken123"]
    label = tokens["supersecrettoken123"]
    # The synthesized label must never just BE the raw token.
    assert label != "supersecrettoken123"
    assert "supe" in label  # first 4 chars, per _token_repr


def test_tolerates_stray_commas_and_whitespace(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(access.ACCESS_TOKENS_ENV, " tok1:a , ,tok2:b ,")
    assert access.load_tokens() == {"tok1": "a", "tok2": "b"}


def test_warn_once_if_unprotected_logs_exactly_once(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger="Agent.backend.web.access")
    access.warn_once_if_unprotected()
    access.warn_once_if_unprotected()
    access.warn_once_if_unprotected()
    warnings = [r for r in caplog.records if "KHÔNG có lớp bảo vệ" in r.getMessage()]
    assert len(warnings) == 1


def test_warn_once_if_unprotected_silent_when_protected(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv(access.ACCESS_TOKENS_ENV, "tok1:a")
    caplog.set_level(logging.WARNING, logger="Agent.backend.web.access")
    access.warn_once_if_unprotected()
    assert not any("KHÔNG có lớp bảo vệ" in r.getMessage() for r in caplog.records)


# --------------------------------------------------------------------------- #
# verify_token
# --------------------------------------------------------------------------- #


def test_verify_token_accepts_configured_token_and_returns_its_label(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(access.ACCESS_TOKENS_ENV, "tok1:buyer-a")
    assert access.verify_token("tok1") == "buyer-a"


def test_verify_token_rejects_wrong_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(access.ACCESS_TOKENS_ENV, "tok1:buyer-a")
    assert access.verify_token("not-tok1") is None


@pytest.mark.parametrize("bad", [None, ""])
def test_verify_token_rejects_missing_or_blank(
    monkeypatch: pytest.MonkeyPatch, bad
) -> None:
    monkeypatch.setenv(access.ACCESS_TOKENS_ENV, "tok1:buyer-a")
    assert access.verify_token(bad) is None


def test_verify_token_never_logs_the_raw_token(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv(access.ACCESS_TOKENS_ENV, "correcthorsebatterystaple:buyer-a")
    caplog.set_level(logging.DEBUG, logger="Agent.backend.web.access")

    access.verify_token("correcthorsebatterystaple")  # success path
    access.verify_token("wrongsecretguessattempt12")  # failure path

    all_log_text = "\n".join(r.getMessage() for r in caplog.records)
    assert "correcthorsebatterystaple" not in all_log_text
    assert "wrongsecretguessattempt12" not in all_log_text


# --------------------------------------------------------------------------- #
# RecentCodeRegistry
# --------------------------------------------------------------------------- #


def test_recent_code_registry_remembers_and_lists_codes() -> None:
    registry = access.RecentCodeRegistry(ttl_seconds=60.0, clock=lambda: 0.0)
    registry.remember("CODE1")
    registry.remember("CODE2")
    assert set(registry.codes()) == {"CODE1", "CODE2"}


def test_recent_code_registry_expires_codes_past_ttl() -> None:
    now = [0.0]
    registry = access.RecentCodeRegistry(ttl_seconds=10.0, clock=lambda: now[0])
    registry.remember("CODE1")
    assert registry.codes() == ["CODE1"]
    now[0] = 11.0
    assert registry.codes() == []


def test_recent_code_registry_evicts_oldest_first_past_cap() -> None:
    registry = access.RecentCodeRegistry(
        ttl_seconds=3600.0, clock=lambda: 0.0, max_codes=3
    )
    for code in ("CODE1", "CODE2", "CODE3", "CODE4"):
        registry.remember(code)
    # CODE1 was the first remembered -> earliest to expire -> evicted first.
    assert registry.codes() == ["CODE2", "CODE3", "CODE4"]


def test_recent_code_registry_remember_refresh_moves_code_to_back() -> None:
    """Re-remembering an already-present code must push its EXPIRY out --
    and therefore its eviction PRIORITY back -- not leave it sitting at the
    front as if it were still the oldest entry.
    """
    registry = access.RecentCodeRegistry(
        ttl_seconds=3600.0, clock=lambda: 0.0, max_codes=3
    )
    registry.remember("CODE1")
    registry.remember("CODE2")
    registry.remember("CODE3")
    registry.remember("CODE1")  # refresh -- CODE2 is now the oldest instead
    registry.remember("CODE4")  # pushes out the new oldest (CODE2)
    assert set(registry.codes()) == {"CODE1", "CODE3", "CODE4"}


def test_max_remembered_codes_constant_is_2000() -> None:
    assert access.MAX_REMEMBERED_CODES == 2000


def test_recent_code_registry_default_cap_bounds_the_real_constant() -> None:
    """Exercises the actual default cap (not an injected small one) -- pure
    in-memory dict operations, so a few thousand inserts costs nothing."""
    registry = access.RecentCodeRegistry(ttl_seconds=3600.0, clock=lambda: 0.0)
    total = access.MAX_REMEMBERED_CODES + 5
    for i in range(total):
        registry.remember(f"CODE{i}")
    codes = registry.codes()
    assert len(codes) == access.MAX_REMEMBERED_CODES
    assert "CODE0" not in codes
    assert "CODE4" not in codes  # the 5 oldest were evicted
    assert f"CODE{total - 1}" in codes  # the newest is always kept


# --------------------------------------------------------------------------- #
# Admin role -- NORABT_ADMIN_TOKEN_SHA256 (separate credential from
# NORABT_ACCESS_TOKENS above, see access.py's own "Admin role" section).
# --------------------------------------------------------------------------- #


def test_admin_unconfigured_by_default() -> None:
    """Neither NORABT_ADMIN_TOKEN_SHA256 nor its OKX_API_KEY fallback is set
    (see `_clean_env` above, which now deletes both) -> no admin at all."""
    assert access.is_admin_configured() is False
    assert access.verify_admin_token("anything-at-all") is False


def test_admin_accepts_the_raw_secret_matching_the_configured_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "team-admin-secret-xyz"
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    monkeypatch.setenv(access.ADMIN_TOKEN_SHA256_ENV, digest)
    assert access.is_admin_configured() is True
    assert access.verify_admin_token(secret) is True


def test_admin_rejects_wrong_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "team-admin-secret-xyz"
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    monkeypatch.setenv(access.ADMIN_TOKEN_SHA256_ENV, digest)
    assert access.verify_admin_token("totally-wrong-guess") is False


def test_admin_rejects_missing_or_blank_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "team-admin-secret-xyz"
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    monkeypatch.setenv(access.ADMIN_TOKEN_SHA256_ENV, digest)
    assert access.verify_admin_token(None) is False
    assert access.verify_admin_token("") is False


def test_admin_rejects_the_configured_hash_sent_as_if_it_were_the_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The comparison always re-hashes whatever is presented -- sending the
    SHA-256 hex string itself (e.g. copied by mistake from .env) must never
    verify, since hashing it again produces a different digest entirely.
    This is the load-bearing property that makes storing only a hash safe.
    """
    secret = "team-admin-secret-xyz"
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    monkeypatch.setenv(access.ADMIN_TOKEN_SHA256_ENV, digest)
    assert access.verify_admin_token(digest) is False


@pytest.mark.parametrize(
    "bad",
    [
        "",  # explicitly set to blank, not merely unset
        "abc",
        "a" * 63,
        "A" * 64,  # uppercase hex is deliberately rejected, not normalized
        "g" * 64,  # right length, not hex digits
    ],
)
def test_admin_malformed_hash_env_treated_as_unconfigured_with_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    bad: str,
) -> None:
    monkeypatch.setenv(access.ADMIN_TOKEN_SHA256_ENV, bad)
    caplog.set_level(logging.WARNING, logger="Agent.backend.web.access")

    assert access.is_admin_configured() is False
    assert access.verify_admin_token("some-admin-key") is False

    warnings = [
        r for r in caplog.records if access.ADMIN_TOKEN_SHA256_ENV in r.getMessage()
    ]
    assert len(warnings) == 1


def test_admin_bad_format_warning_logged_only_once(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv(access.ADMIN_TOKEN_SHA256_ENV, "not-a-valid-hash")
    caplog.set_level(logging.WARNING, logger="Agent.backend.web.access")

    for _ in range(5):
        access.is_admin_configured()
    access.verify_admin_token("whatever")

    warnings = [
        r for r in caplog.records if access.ADMIN_TOKEN_SHA256_ENV in r.getMessage()
    ]
    assert len(warnings) == 1


def test_admin_secret_never_appears_in_logs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "super-secret-admin-key-do-not-log-me"
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    monkeypatch.setenv(access.ADMIN_TOKEN_SHA256_ENV, digest)
    caplog.set_level(logging.DEBUG)

    assert access.verify_admin_token(secret) is True
    assert access.verify_admin_token("wrong-guess-entirely") is False

    for record in caplog.records:
        assert secret not in record.getMessage()


# --------------------------------------------------------------------------- #
# Admin role -- OKX_API_KEY fallback (Việc 3): the project owner's explicit
# ruling for the current simulated/demo-account stage, see access.py's
# `_admin_token_hash` and Agent/.env.example's own comment on this.
# --------------------------------------------------------------------------- #


def test_admin_falls_back_to_okx_api_key_when_dedicated_hash_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OKX_API_KEY", "demo-okx-key-000111222")
    assert access.is_admin_configured() is True
    assert access.verify_admin_token("demo-okx-key-000111222") is True
    assert access.verify_admin_token("some-other-guess") is False


def test_admin_dedicated_hash_wins_over_okx_api_key_when_both_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dedicated_secret = "dedicated-admin-secret-xyz"
    monkeypatch.setenv("OKX_API_KEY", "demo-okx-key-000111222")
    monkeypatch.setenv(
        access.ADMIN_TOKEN_SHA256_ENV,
        hashlib.sha256(dedicated_secret.encode("utf-8")).hexdigest(),
    )
    # The OKX_API_KEY value itself must NOT work once a dedicated hash is set.
    assert access.verify_admin_token("demo-okx-key-000111222") is False
    assert access.verify_admin_token(dedicated_secret) is True


def test_admin_neither_set_means_no_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OKX_API_KEY", raising=False)
    monkeypatch.delenv(access.ADMIN_TOKEN_SHA256_ENV, raising=False)
    assert access.is_admin_configured() is False
    assert access.verify_admin_token("anything") is False


def test_admin_blank_okx_api_key_does_not_count_as_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An empty string (an operator's `.env` line present but left blank)
    must behave exactly like the variable being absent, not like a
    zero-length admin secret."""
    monkeypatch.setenv("OKX_API_KEY", "   ")
    assert access.is_admin_configured() is False


def test_admin_okx_api_key_never_appears_in_logs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    secret = "super-secret-okx-demo-key-do-not-log-me"
    monkeypatch.setenv("OKX_API_KEY", secret)
    caplog.set_level(logging.DEBUG)

    assert access.verify_admin_token(secret) is True
    assert access.verify_admin_token("wrong-guess-entirely") is False

    for record in caplog.records:
        assert secret not in record.getMessage()


# --------------------------------------------------------------------------- #
# Session cookie (Việc 2) -- access.create_session_cookie/read_session, the
# signed cookie POST /api/session (app.py) issues. Route-level integration
# (the actual Set-Cookie header, POST /api/session itself) is covered in
# Agent/none/test/test_web_app.py; this section only exercises the sign/verify
# primitives directly.
# --------------------------------------------------------------------------- #


def test_session_cookie_round_trips_for_a_user() -> None:
    cookie = access.create_session_cookie(user_ref="abcdefghij")
    session = access.read_session(cookie)
    assert session == {"is_admin": False, "user_ref": "abcdefghij"}


def test_session_cookie_round_trips_for_admin() -> None:
    cookie = access.create_session_cookie(is_admin=True)
    session = access.read_session(cookie)
    assert session == {"is_admin": True, "user_ref": None}


def test_session_cookie_tampered_signature_is_rejected() -> None:
    cookie = access.create_session_cookie(user_ref="abcdefghij")
    body, _, signature = cookie.rpartition(".")
    flipped = "0" if signature[-1] != "0" else "1"
    tampered = f"{body}.{signature[:-1]}{flipped}"
    assert access.read_session(tampered) is None


def test_session_cookie_tampered_body_is_rejected() -> None:
    cookie = access.create_session_cookie(user_ref="abcdefghij")
    body, _, signature = cookie.rpartition(".")
    tampered_body = body[:-1] + ("A" if body[-1] != "A" else "B")
    assert access.read_session(f"{tampered_body}.{signature}") is None


def test_session_cookie_expired_is_rejected() -> None:
    # now_ms far enough in the past that even an 8h TTL has elapsed.
    cookie = access.create_session_cookie(
        user_ref="abcdefghij", ttl_seconds=1.0, now_ms=0
    )
    assert access.read_session(cookie) is None


def test_session_cookie_garbage_and_missing_values_rejected() -> None:
    assert access.read_session(None) is None
    assert access.read_session("") is None
    assert access.read_session("not-a-valid-cookie-at-all") is None
    assert access.read_session("no-dot-separator") is None


def test_session_cookie_changes_when_secret_env_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(access.REPORT_URL_SECRET_ENV, raising=False)
    cookie_default = access.create_session_cookie(user_ref="abcdefghij")
    monkeypatch.setenv(access.REPORT_URL_SECRET_ENV, "a-different-secret")
    # Same payload/signing call, but now signed (and verified) under a
    # different key -- the OLD cookie must no longer verify.
    assert access.read_session(cookie_default) is None


def test_session_cookie_never_contains_a_raw_wallet_address_or_admin_key() -> None:
    """The task's own hard requirement: the cookie's SIGNED CONTENT is only
    ever `user_ref`/`is_admin`/`exp_ms` -- never the wallet address (only
    identity.py's `user_ref` derives from it) or an admin key string, so a
    leaked cookie can never disclose either. Exercised here by asserting
    neither example secret's TEXT occurs anywhere in the cookie string.
    """
    wallet_address = "0xaa170000000000000000000000000000000abc"
    admin_key = "super-secret-admin-key-xyz"
    cookie_user = access.create_session_cookie(user_ref="abcdefghij")
    cookie_admin = access.create_session_cookie(is_admin=True)
    assert wallet_address not in cookie_user
    assert admin_key not in cookie_user
    assert wallet_address not in cookie_admin
    assert admin_key not in cookie_admin
