"""Tests for Agent/backend/web/snapshot.py in isolation, with no real Redis
server involved anywhere: every test either leaves
`NORABT_SNAPSHOT_REDIS_URL` unset (the "feature off" default) or sets it to
a throwaway value and monkeypatches `snapshot._get_client` to return a small
in-memory fake instead of a real `redis.asyncio.Redis` -- this module's own
job is exactly to make Redis's *failure modes* (down, corrupt, slow) never
surprising, so those are exactly what these tests simulate.

Route-level integration (GET /bot/<code> actually using this module through
`app.py`'s `_bot_report_response`) is covered separately in
Agent/none/test/test_web_app.py -- this file only exercises snapshot.py's own
public functions.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import pytest

from Agent.backend.web import snapshot

# --------------------------------------------------------------------------- #
# Fake async Redis client -- just enough surface (get/setex/ping) for
# snapshot.py to talk to, with each test controlling exactly what it does.
# --------------------------------------------------------------------------- #


class _FakeRedisClient:
    def __init__(
        self,
        *,
        raise_on: Optional[str] = None,
        exc: Optional[Exception] = None,
    ) -> None:
        self.store: Dict[str, str] = {}
        # Which method call ("get", "setex", "ping", or None) should raise
        # `exc` -- simulates a dead/unreachable Redis without ever touching
        # a real socket.
        self.raise_on = raise_on
        self.exc = exc or ConnectionError("simulated redis outage")
        self.get_calls = 0
        self.setex_calls = 0
        self.ping_calls = 0

    async def get(self, key: str):
        self.get_calls += 1
        if self.raise_on == "get":
            raise self.exc
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.setex_calls += 1
        if self.raise_on == "setex":
            raise self.exc
        self.store[key] = value

    async def ping(self):
        self.ping_calls += 1
        if self.raise_on == "ping":
            raise self.exc
        return True


def _configure(
    monkeypatch: pytest.MonkeyPatch, client: Optional[_FakeRedisClient]
) -> None:
    """Turn the feature on (a throwaway URL -- never actually dialled,
    since `_get_client` is patched below to skip real connection setup
    entirely) and inject `client` as whatever `_get_client()` returns."""
    monkeypatch.setenv(snapshot.ENV_VAR_REDIS_URL, "redis://fake-host:6379")
    monkeypatch.setattr(snapshot, "_get_client", lambda: client)


def run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------- #
# Unconfigured (default) -- guaranteed zero Redis interaction
# --------------------------------------------------------------------------- #


def test_unconfigured_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(snapshot.ENV_VAR_REDIS_URL, raising=False)
    assert snapshot.is_configured() is False


def test_unconfigured_get_snapshot_never_touches_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(snapshot.ENV_VAR_REDIS_URL, raising=False)

    def _boom() -> None:
        raise AssertionError("_get_client() must never be called when unconfigured")

    monkeypatch.setattr(snapshot, "_get_client", _boom)
    assert run(snapshot.get_snapshot("ABC")) is None


def test_unconfigured_set_snapshot_is_a_silent_noop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(snapshot.ENV_VAR_REDIS_URL, raising=False)

    def _boom() -> None:
        raise AssertionError("_get_client() must never be called when unconfigured")

    monkeypatch.setattr(snapshot, "_get_client", _boom)
    run(snapshot.set_snapshot("ABC", {"status": "FULL"}, 1_700_000_000_000))


def test_unconfigured_ping_returns_false_without_a_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(snapshot.ENV_VAR_REDIS_URL, raising=False)
    monkeypatch.setattr(
        snapshot,
        "_get_client",
        lambda: (_ for _ in ()).throw(AssertionError("must not be called")),
    )
    assert run(snapshot.ping()) is False


# --------------------------------------------------------------------------- #
# Write then read -- the ordinary cache-hit path
# --------------------------------------------------------------------------- #


def test_set_then_get_round_trips(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeRedisClient()
    _configure(monkeypatch, client)

    result = {"status": "FULL", "code": "BB3398A957270A39", "risk": 42}
    run(snapshot.set_snapshot("BB3398A957270A39", result, 1_700_000_000_123))

    fetched = run(snapshot.get_snapshot("BB3398A957270A39"))
    assert fetched is not None
    assert fetched["result"] == result
    assert fetched["snapshot_at_ms"] == 1_700_000_000_123


def test_key_uses_agent_report_namespace(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeRedisClient()
    _configure(monkeypatch, client)
    run(snapshot.set_snapshot("CODE123", {"status": "FULL"}, 1))
    assert list(client.store.keys()) == ["agent:report:CODE123"]
    assert snapshot.snapshot_key("CODE123") == "agent:report:CODE123"
    assert snapshot.snapshot_key("CODE123").startswith(snapshot.KEY_PREFIX)


def test_db_index_is_forced_to_one_regardless_of_url_path() -> None:
    # _build_client must ignore any db segment already in the URL and force
    # REDIS_DB_INDEX -- see that function's own docstring for why (nora's
    # own data lives in db0 of the same shared instance).
    for url in (
        "redis://host:6379/0",
        "redis://host:6379",
        "redis://host:6379/5",
    ):
        client = snapshot._build_client(url)
        try:
            assert (
                client.connection_pool.connection_kwargs.get("db")
                == snapshot.REDIS_DB_INDEX
            )
        finally:
            # Never actually connects (from_url does no I/O), but close the
            # pool object cleanly anyway.
            pass
    assert snapshot.REDIS_DB_INDEX == 1


# --------------------------------------------------------------------------- #
# Missing / expired snapshot -- ordinary cache miss
# --------------------------------------------------------------------------- #


def test_missing_key_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeRedisClient()
    _configure(monkeypatch, client)
    assert run(snapshot.get_snapshot("NEVER_WRITTEN")) is None
    assert client.get_calls == 1


# --------------------------------------------------------------------------- #
# Redis down -- THE most important behaviour this module exists for
# --------------------------------------------------------------------------- #


def test_get_snapshot_swallows_connection_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = _FakeRedisClient(raise_on="get", exc=ConnectionError("redis is down"))
    _configure(monkeypatch, client)
    with caplog.at_level(logging.WARNING, logger="Agent.backend.web.snapshot"):
        result = run(snapshot.get_snapshot("ANYCODE"))
    assert result is None
    assert any("read failed" in r.getMessage() for r in caplog.records)


def test_set_snapshot_swallows_connection_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = _FakeRedisClient(raise_on="setex", exc=ConnectionError("redis is down"))
    _configure(monkeypatch, client)
    with caplog.at_level(logging.WARNING, logger="Agent.backend.web.snapshot"):
        run(snapshot.set_snapshot("ANYCODE", {"status": "FULL"}, 1))
    assert any("write failed" in r.getMessage() for r in caplog.records)
    # Never logs the snapshot's own content, only key/size (task's explicit
    # "không log nội dung snapshot" requirement).
    assert not any("FULL" in r.getMessage() for r in caplog.records)


def test_ping_returns_false_on_connection_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeRedisClient(raise_on="ping", exc=ConnectionError("redis is down"))
    _configure(monkeypatch, client)
    assert run(snapshot.ping()) is False


def test_get_client_build_failure_is_swallowed(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv(snapshot.ENV_VAR_REDIS_URL, "redis://fake-host:6379")
    monkeypatch.setattr(snapshot, "_client_state", {"client": None, "url": None})

    def _boom(url: str):
        raise RuntimeError("malformed url")

    monkeypatch.setattr(snapshot, "_build_client", _boom)
    with caplog.at_level(logging.WARNING, logger="Agent.backend.web.snapshot"):
        assert run(snapshot.get_snapshot("X")) is None
    assert any("failed to build redis client" in r.getMessage() for r in caplog.records)


# --------------------------------------------------------------------------- #
# Corrupt / garbage stored value -- treated exactly like "no snapshot"
# --------------------------------------------------------------------------- #


def test_corrupt_json_value_treated_as_no_snapshot(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = _FakeRedisClient()
    client.store[snapshot.snapshot_key("BADCODE")] = "{not valid json"
    _configure(monkeypatch, client)
    with caplog.at_level(logging.WARNING, logger="Agent.backend.web.snapshot"):
        result = run(snapshot.get_snapshot("BADCODE"))
    assert result is None
    assert any("not valid JSON" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize(
    "raw",
    [
        json.dumps([1, 2, 3]),
        json.dumps({"result": "not-a-dict", "snapshot_at_ms": 1}),
        json.dumps({"result": {"status": "FULL"}, "snapshot_at_ms": "not-an-int"}),
        json.dumps({"only_result": {"status": "FULL"}}),
        "null",
        "42",
    ],
)
def test_unexpected_shape_treated_as_no_snapshot(
    monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    client = _FakeRedisClient()
    client.store[snapshot.snapshot_key("WEIRDCODE")] = raw
    _configure(monkeypatch, client)
    assert run(snapshot.get_snapshot("WEIRDCODE")) is None


# --------------------------------------------------------------------------- #
# Oversized payload -- skip the write, never crash
# --------------------------------------------------------------------------- #


def test_oversized_payload_is_not_written(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    client = _FakeRedisClient()
    _configure(monkeypatch, client)
    huge_result = {"status": "FULL", "warnings": ["x" * 1000] * 600}
    with caplog.at_level(logging.WARNING, logger="Agent.backend.web.snapshot"):
        run(snapshot.set_snapshot("HUGECODE", huge_result, 1))
    assert client.setex_calls == 0
    assert client.store == {}
    assert any("over the" in r.getMessage() for r in caplog.records)


def test_reasonable_payload_is_written(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeRedisClient()
    _configure(monkeypatch, client)
    run(snapshot.set_snapshot("SMALLCODE", {"status": "FULL"}, 1))
    assert client.setex_calls == 1


def test_setex_uses_the_documented_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeRedisClient()
    _configure(monkeypatch, client)
    captured: Dict[str, Any] = {}

    async def _setex(key: str, ttl: int, value: str):
        captured["ttl"] = ttl

    client.setex = _setex  # type: ignore[assignment]
    run(snapshot.set_snapshot("TTLCODE", {"status": "FULL"}, 1))
    assert captured["ttl"] == snapshot.SNAPSHOT_TTL_SECONDS == 86400


# --------------------------------------------------------------------------- #
# ping() -- healthz's building block
# --------------------------------------------------------------------------- #


def test_ping_true_when_configured_and_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeRedisClient()
    _configure(monkeypatch, client)
    assert run(snapshot.ping()) is True
