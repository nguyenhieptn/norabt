"""Unit tests for Agent/backend/web/identity.py -- wallet-address
validation, `user_ref` derivation, and the on-disk per-user profile store
(atomic writes, dedup/trim of `analyzed`, path-traversal safety).

Every test that touches disk uses `tmp_path` via the `users_root` keyword
every store function accepts -- never this repo's real `Agent/data/users/`
directory.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from Agent.backend.web import identity

VALID_ADDRESS = "0x" + "aa17" + "00" * 17 + "ff"  # 42 chars, well-formed


@pytest.fixture(autouse=True)
def _clean_secret_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """`user_ref` is derived using NORABT_REPORT_URL_SECRET (see
    access.report_url_secret_bytes) -- start every test from the same
    (unset -> default) secret so a real Agent/.env on the machine running
    pytest can never change what these tests observe.
    """
    from Agent.backend.web import access

    monkeypatch.delenv(access.REPORT_URL_SECRET_ENV, raising=False)


# --------------------------------------------------------------------------- #
# Wallet address format validation
# --------------------------------------------------------------------------- #


def test_normalize_valid_address_lowercases_it() -> None:
    mixed_case = "0x" + "AA17" + "00" * 17 + "FF"
    assert identity.normalize_wallet_address(mixed_case) == mixed_case.lower()


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "aa17" + "00" * 17 + "ff",  # missing 0x prefix
        "0x" + "a" * 39,  # 39 hex chars, one short
        "0x" + "a" * 41,  # 41 hex chars, one over
        "0x" + "g" * 40,  # not hex
        "0x" + "12 34" + "0" * 34,  # embedded whitespace
        None,
        123,
    ],
)
def test_normalize_rejects_bad_format(bad) -> None:
    with pytest.raises(identity.InvalidWalletAddressError):
        identity.normalize_wallet_address(bad)


# --------------------------------------------------------------------------- #
# user_ref derivation
# --------------------------------------------------------------------------- #


def test_user_ref_is_stable_across_calls() -> None:
    ref1 = identity.user_ref(VALID_ADDRESS)
    ref2 = identity.user_ref(VALID_ADDRESS)
    assert ref1 == ref2


def test_user_ref_same_for_upper_and_lower_case_address() -> None:
    lower = VALID_ADDRESS
    upper = "0x" + VALID_ADDRESS[2:].upper()
    assert identity.user_ref(lower) == identity.user_ref(upper)


def test_user_ref_differs_for_different_addresses() -> None:
    other = "0x" + "bb17" + "00" * 17 + "ff"
    assert identity.user_ref(VALID_ADDRESS) != identity.user_ref(other)


def test_user_ref_changes_when_secret_env_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from Agent.backend.web import access

    ref_default = identity.user_ref(VALID_ADDRESS)
    monkeypatch.setenv(access.REPORT_URL_SECRET_ENV, "a-totally-different-secret")
    ref_changed = identity.user_ref(VALID_ADDRESS)
    assert ref_default != ref_changed


def test_user_ref_is_url_safe_and_has_no_underscore() -> None:
    ref = identity.user_ref(VALID_ADDRESS)
    assert identity.USER_REF_RE.match(ref)
    assert "_" not in ref
    for ch in ref:
        assert ch in "abcdefghijklmnopqrstuvwxyz234567"
    assert len(ref) == identity.USER_REF_LENGTH


# --------------------------------------------------------------------------- #
# Profile store: create / touch / record_analysis
# --------------------------------------------------------------------------- #


def test_get_or_create_profile_creates_new_profile(tmp_path: Path) -> None:
    profile = identity.get_or_create_profile(VALID_ADDRESS, users_root=tmp_path)
    assert profile["wallet_address"] == VALID_ADDRESS
    assert profile["user_ref"] == identity.user_ref(VALID_ADDRESS)
    assert profile["created_at_ms"] == profile["last_seen_ms"]
    assert profile["analyzed"] == []

    on_disk = json.loads(
        (tmp_path / profile["user_ref"] / "profile.json").read_text(encoding="utf-8")
    )
    assert on_disk["user_ref"] == profile["user_ref"]


def test_get_or_create_profile_second_call_touches_last_seen_not_created(
    tmp_path: Path,
) -> None:
    first = identity.get_or_create_profile(VALID_ADDRESS, users_root=tmp_path)
    # Force a later, distinguishable last_seen_ms so the assertion cannot
    # pass merely from two calls landing in the same millisecond.
    later_path = tmp_path / first["user_ref"] / "profile.json"
    stored = json.loads(later_path.read_text(encoding="utf-8"))
    stored["created_at_ms"] = 1_000
    stored["last_seen_ms"] = 1_000
    later_path.write_text(json.dumps(stored), encoding="utf-8")

    second = identity.get_or_create_profile(VALID_ADDRESS, users_root=tmp_path)
    assert second["created_at_ms"] == 1_000
    assert second["last_seen_ms"] > 1_000


def test_get_or_create_profile_matches_regardless_of_input_case(
    tmp_path: Path,
) -> None:
    """The whole point of lowercasing before hashing: logging in with
    different letter-casing of the SAME address must land on the SAME
    profile, not silently create a second, empty one."""
    upper = "0x" + VALID_ADDRESS[2:].upper()
    first = identity.get_or_create_profile(VALID_ADDRESS, users_root=tmp_path)
    second = identity.get_or_create_profile(upper, users_root=tmp_path)
    assert first["user_ref"] == second["user_ref"]
    assert len(list(tmp_path.iterdir())) == 1


def test_record_analysis_dedups_by_code_and_moves_to_end(tmp_path: Path) -> None:
    profile = identity.get_or_create_profile(VALID_ADDRESS, users_root=tmp_path)
    ref = profile["user_ref"]
    identity.record_analysis(ref, "CODE_A", "Bot A", "AN TOAN", users_root=tmp_path)
    identity.record_analysis(ref, "CODE_B", "Bot B", "RUI RO", users_root=tmp_path)
    updated = identity.record_analysis(
        ref, "CODE_A", "Bot A renamed", "CANH BAO", users_root=tmp_path
    )
    codes = [item["code"] for item in updated["analyzed"]]
    assert codes == ["CODE_B", "CODE_A"]
    assert updated["analyzed"][-1]["name"] == "Bot A renamed"
    assert updated["analyzed"][-1]["verdict"] == "CANH BAO"


def test_record_analysis_trims_to_max_history(tmp_path: Path) -> None:
    profile = identity.get_or_create_profile(VALID_ADDRESS, users_root=tmp_path)
    ref = profile["user_ref"]
    updated = None
    total = identity.MAX_ANALYZED_HISTORY + 10
    for i in range(total):
        updated = identity.record_analysis(
            ref, f"CODE{i:05d}", "n", "v", users_root=tmp_path
        )
    assert len(updated["analyzed"]) == identity.MAX_ANALYZED_HISTORY
    codes = [item["code"] for item in updated["analyzed"]]
    # The oldest 10 were dropped; the newest is always kept.
    assert "CODE00000" not in codes
    assert "CODE00009" not in codes
    assert f"CODE{total - 1:05d}" in codes


def test_record_analysis_returns_none_for_unknown_user_ref(tmp_path: Path) -> None:
    assert (
        identity.record_analysis("zzzzzzzzzz", "CODE_A", "n", "v", users_root=tmp_path)
        is None
    )


def test_has_analyzed() -> None:
    profile = {"analyzed": [{"code": "ABC"}, {"code": "DEF"}]}
    assert identity.has_analyzed(profile, "ABC") is True
    assert identity.has_analyzed(profile, "NOPE") is False
    assert identity.has_analyzed({}, "ABC") is False


# --------------------------------------------------------------------------- #
# Atomic writes
# --------------------------------------------------------------------------- #


def test_atomic_write_failure_leaves_original_file_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "u1" / "profile.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"ok": True}), encoding="utf-8")

    def boom(*_args, **_kwargs):
        raise RuntimeError("simulated crash mid-write")

    monkeypatch.setattr(identity.json, "dump", boom)
    with pytest.raises(RuntimeError):
        identity._write_json_atomic(path, {"ok": False})

    # Original content survives untouched, and no stray .tmp file is left.
    assert json.loads(path.read_text(encoding="utf-8")) == {"ok": True}
    leftovers = list(path.parent.iterdir())
    assert leftovers == [path]


def test_atomic_write_creates_parent_directories(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "deeper" / "profile.json"
    identity._write_json_atomic(path, {"hello": "world"})
    assert json.loads(path.read_text(encoding="utf-8")) == {"hello": "world"}


# --------------------------------------------------------------------------- #
# Lỗi 1/Lỗi 2 fix -- ProfileStoreError: an OPERATIONAL disk failure (a
# read-only `data/users` bind mount, a full disk, wrong permissions) must
# come out of the public `get_or_create_profile`/`record_analysis` API as
# this project-specific exception, never as a bare OSError -- see
# ProfileStoreError's own docstring for why app.py needs that distinction
# to turn it into a safe, generic Vietnamese message instead of leaking
# `str(OSError)` (an absolute container path, an errno, "Read-only file
# system") straight into an internet-facing response.
# --------------------------------------------------------------------------- #


def test_get_or_create_profile_wraps_oserror_as_profile_store_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError(30, "Read-only file system")

    monkeypatch.setattr(identity, "_write_json_atomic", boom)
    with pytest.raises(identity.ProfileStoreError) as excinfo:
        identity.get_or_create_profile(VALID_ADDRESS, users_root=tmp_path)
    # The original OSError is still reachable via __cause__ (Python's own
    # `raise ... from exc`) -- app.py's server-side log line relies on this
    # to show the FULL detail next to the incident code it hands the client.
    assert isinstance(excinfo.value.__cause__, OSError)


def test_record_analysis_wraps_oserror_as_profile_store_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = identity.get_or_create_profile(VALID_ADDRESS, users_root=tmp_path)
    ref = profile["user_ref"]

    def boom(*_args: object, **_kwargs: object) -> None:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(identity, "_write_json_atomic", boom)
    with pytest.raises(identity.ProfileStoreError) as excinfo:
        identity.record_analysis(ref, "CODE_X", "n", "v", users_root=tmp_path)
    assert isinstance(excinfo.value.__cause__, PermissionError)


def test_profile_store_error_never_wraps_a_non_oserror_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failure that is NOT an OSError (a programming bug in the write
    path itself) must propagate completely unchanged -- never relabeled as
    an operational storage incident, which would send an operator chasing
    disk/permissions for a bug that has nothing to do with either. Mirrors
    `test_atomic_write_failure_leaves_original_file_untouched` above, one
    layer up the call stack.
    """

    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("boom, not a disk problem")

    monkeypatch.setattr(identity, "_write_json_atomic", boom)
    with pytest.raises(RuntimeError):
        identity.get_or_create_profile(VALID_ADDRESS, users_root=tmp_path)


# --------------------------------------------------------------------------- #
# user_ref path-traversal safety -- the same discipline this project already
# applies elsewhere (Agent/backend/agent_server.py's _require_token,
# Agent/backend/web/data.py's validate_unique_code): a malicious user_ref
# must never escape `users_root`.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "malicious",
    [
        "../../../etc/passwd",
        "..%2f..%2fetc",
        "a/b",
        "/etc/passwd",
        "..",
        ".",
        "",
        "UPPERCASE1",  # wrong alphabet (uppercase)
        "short",  # wrong length
        "waaaaaaaaaytoolong",  # wrong length
        "abcdefgh_j",  # contains the forbidden separator
    ],
)
def test_load_profile_rejects_malicious_or_malformed_user_ref(
    tmp_path: Path, malicious: str
) -> None:
    assert identity.load_profile(malicious, users_root=tmp_path) is None
    # Nothing outside tmp_path was ever touched/created.
    assert list(tmp_path.iterdir()) == [] if tmp_path.exists() else True


def test_record_analysis_rejects_malicious_user_ref(tmp_path: Path) -> None:
    assert (
        identity.record_analysis(
            "../../../etc/passwd", "CODE_A", "n", "v", users_root=tmp_path
        )
        is None
    )


def test_profile_dir_never_escapes_users_root_for_malicious_ref(
    tmp_path: Path,
) -> None:
    with pytest.raises(identity.InvalidUserRefError):
        identity._profile_dir("../../escape", users_root=tmp_path)
