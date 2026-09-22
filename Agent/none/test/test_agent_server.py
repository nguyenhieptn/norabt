"""Contract tests for the MCP tool surface, not for the services it wraps.

Every service behind these tools (pipeline, market/bot observation, the
assessment store) already has its own test file; duplicating their logic here
would just be slower assertions on the same numbers. What is unique to this
file, and therefore worth testing directly, is the tool boundary itself: input
validation against a hostile AI caller, Vietnamese fail-closed error text, and
the stateless contract on `assess_bot`.

`MCPServer.call_tool()` is a plain coroutine, so tests drive it with
`asyncio.run()` rather than pulling in pytest-asyncio -- the rest of this
project's tests are synchronous and there is no `asyncio_mode` configured, so
adding an async test runner here would be a project-wide config change no
other test asked for.

The transport tests at the bottom (`test_http_transport_...`,
`test_stdio_transport_...`) are a different kind of test from everything
above: instead of calling `srv.mcp.call_tool()` in-process, they spawn
`python3 -m Agent.backend.scripts.agent_server` as a real subprocess and drive it
with a real `mcp` client (`streamable_http_client`/`stdio_client` +
`ClientSession`), because the thing being verified -- that the CLI's
`--transport` wiring actually serves a remote client, not just that the
`MCPServer` object has the right tools registered -- can only be shown by
going through the wire protocol. Each HTTP run gets its own OS-assigned port
(`_free_port()`) so the test suite can run this file's tests concurrently
with itself, or with an already-running server on the CLI's own default
port, without colliding.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import socket
import subprocess
import sys
import time
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Tuple

import pytest

from Agent.backend.scripts import agent_server as srv
from Agent.backend.infra.config import config
from Agent.backend.external.payments import x402
from mcp.server.mcpserver.exceptions import ToolError

DATA_DIR = Path(config.DATA_DIR)

# Repo root: tests must run the server the same way the docs tell an operator
# to (`cd /home/ubuntu/norabt && python3 -m Agent.backend.scripts.agent_server`),
# since `Agent.backend...` imports only resolve with the repo root on
# sys.path / as cwd.
REPO_ROOT = Path(__file__).resolve().parents[3]

# Upper bound on how long a freshly spawned server gets to start accepting
# connections. Generous enough to absorb a slow CI machine, but bounded so a
# genuinely broken server fails the test in seconds, not by hanging the run.
_STARTUP_TIMEOUT_S = 10.0

# A bot known to be in data/assessment/index.json as of this writing (see
# Agent/data/assessment/dex/WBTC/bot/King_GG__.../assessment.json). If the
# report is regenerated and this cohort changes, this constant is the one
# place to update.
ASSESSED_UNIQUE_CODE = "811997770117827919"
# This bot's assessment.json still stores the retired single-axis "NGUY
# HIỂM" label in khuyen_nghi.ket_luan (written before the two-axis
# relabeling), but list_assessed_bots/get_assessment now always recompute
# the label from cham_diem.risk_score/quality_score/hidden_risk_flags
# instead of trusting that stored string (see verdict.label_from_scores).
# This bot's own risk_score is 100.0 (>= DANGEROUS_RISK) and it carries a
# hidden_risk_flags entry (an open loss at 43% of capital), so hidden risk
# overrides both axes: the recomputed label is "RỦI RO BỊ CHE", not
# whichever of the 4 old buckets the file happens to still say.
ASSESSED_VERDICT = "HIDDEN RISK"

# Real, on-disk bot used by the one live-pipeline test below -- same fixture
# `conftest.py` calls `bot_top`, so it is known to be a complete, reconciled
# ledger and not a defect case that would make the timing or the assertions
# flaky.
REAL_BOT_ASSET = "MU"
REAL_BOT_FOLDER = "bot_BB3398A957270A39"
REAL_BOT_VENUE = "CEX"


def _call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke a tool the same way the MCP runtime does, and unwrap its JSON text."""
    result = asyncio.run(srv.mcp.call_tool(name, arguments))
    assert not result.is_error
    return json.loads(result.content[0].text)


def _call_raises(name: str, arguments: Dict[str, Any]) -> ToolError:
    with pytest.raises(ToolError) as excinfo:
        asyncio.run(srv.mcp.call_tool(name, arguments))
    return excinfo.value


# ---------------------------------------------------------------------------
# list_assets
# ---------------------------------------------------------------------------


def test_list_assets_returns_known_asset_with_venue():
    payload = _call("list_assets", {})
    assert isinstance(payload, dict)
    by_name = {row["asset"]: row["venues"] for row in payload["assets"]}
    assert "CEX" in by_name.get("BTC", [])


# ---------------------------------------------------------------------------
# list_bots
# ---------------------------------------------------------------------------


def test_list_bots_returns_folder_nick_and_code():
    payload = _call(
        "list_bots", {"asset": REAL_BOT_ASSET, "venue_type": REAL_BOT_VENUE}
    )
    assert payload["asset"] == REAL_BOT_ASSET
    folders = {row["bot_folder_name"] for row in payload["bots"]}
    assert REAL_BOT_FOLDER in folders
    sample = next(r for r in payload["bots"] if r["bot_folder_name"] == REAL_BOT_FOLDER)
    assert sample["nick_name"] and sample["unique_code"]


@pytest.mark.parametrize(
    "asset",
    ["../../etc", "..", "a/b", "a\\b", "MU/../../etc"],
)
def test_list_bots_rejects_path_traversal_in_asset(asset):
    error = _call_raises("list_bots", {"asset": asset, "venue_type": "CEX"})
    assert "asset" in str(error)


def test_list_bots_rejects_unknown_venue():
    error = _call_raises("list_bots", {"asset": "MU", "venue_type": "XXX"})
    assert "CEX" in str(error) and "DEX" in str(error)


def test_list_bots_unknown_asset_names_the_gap():
    error = _call_raises("list_bots", {"asset": "KHONGTONTAI", "venue_type": "CEX"})
    message = str(error)
    assert "KHONGTONTAI" in message
    assert "crawl" in message.lower()


# ---------------------------------------------------------------------------
# list_assessed_bots
# ---------------------------------------------------------------------------


def test_list_assessed_bots_without_filter_returns_everything():
    payload = _call("list_assessed_bots", {})
    assert payload["count"] == len(payload["bots"])
    assert payload["count"] > 0


def test_list_assessed_bots_filters_by_verdict():
    all_bots = _call("list_assessed_bots", {})
    filtered = _call("list_assessed_bots", {"verdict": ASSESSED_VERDICT})
    assert filtered["count"] > 0
    assert filtered["count"] < all_bots["count"]
    assert all(row["verdict"] == ASSESSED_VERDICT for row in filtered["bots"])


def test_list_assessed_bots_verdict_is_case_insensitive():
    lower = _call("list_assessed_bots", {"verdict": ASSESSED_VERDICT.lower()})
    proper = _call("list_assessed_bots", {"verdict": ASSESSED_VERDICT})
    assert lower["count"] == proper["count"]
    # Echoed back canonical, not the caller's casing -- a typo'd verdict must
    # never look like it introduced a fifth category.
    assert lower["verdict_filter"] == ASSESSED_VERDICT


def test_list_assessed_bots_rejects_unknown_verdict():
    error = _call_raises("list_assessed_bots", {"verdict": "KHONG HOP LE"})
    assert "HIDDEN RISK" in str(error)


# ---------------------------------------------------------------------------
# get_assessment
# ---------------------------------------------------------------------------


def test_get_assessment_returns_the_full_narrative():
    payload = _call("get_assessment", {"unique_code": ASSESSED_UNIQUE_CODE})
    assert payload["bot"]["unique_code"] == ASSESSED_UNIQUE_CODE
    narrative = payload["recommendation"]["text_full"]
    assert isinstance(narrative, str) and len(narrative) > 0
    assert payload["recommendation"]["verdict"] == ASSESSED_VERDICT


def test_get_assessment_unknown_code_is_a_readable_message_not_a_traceback():
    error = _call_raises("get_assessment", {"unique_code": "MA_KHONG_TON_TAI"})
    message = str(error)
    assert "MA_KHONG_TON_TAI" in message
    assert "Traceback" not in message
    assert "QC" in message


@pytest.mark.parametrize("unique_code", ["../../etc", "..", "a/b"])
def test_get_assessment_rejects_path_traversal(unique_code):
    _call_raises("get_assessment", {"unique_code": unique_code})


# ---------------------------------------------------------------------------
# assess_bot -- validation is fast; only one test below runs the real pipeline
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "asset,folder,venue",
    [
        ("../../etc", "bot_x", "CEX"),
        ("MU", "../../etc", "CEX"),
        ("MU", "bot_x", "XXX"),
    ],
)
def test_assess_bot_rejects_hostile_input_before_running_pipeline(asset, folder, venue):
    _call_raises(
        "assess_bot", {"asset": asset, "bot_folder_name": folder, "venue_type": venue}
    )


def test_assess_bot_missing_bot_is_fail_closed_not_empty():
    # _find_bot_dir fails fast (a directory check), so this stays cheap even
    # though it goes through the real pipeline entry point.
    error = _call_raises(
        "assess_bot",
        {"asset": "MU", "bot_folder_name": "bot_khong_ton_tai", "venue_type": "CEX"},
    )
    assert "bot_khong_ton_tai" in str(error)


def test_assess_bot_runs_live_pipeline_and_writes_no_state_file():
    """The one test in this file that runs the real Monte Carlo pipeline.

    Kept singular deliberately: the pipeline takes seconds, not milliseconds,
    and every other assess_bot behaviour (validation, missing-bot errors) is
    covered above without paying that cost.
    """
    state_dir = DATA_DIR / "state"
    before = sorted(
        p.relative_to(state_dir) for p in state_dir.rglob("*") if p.is_file()
    )

    payload = _call(
        "assess_bot",
        {
            "asset": REAL_BOT_ASSET,
            "bot_folder_name": REAL_BOT_FOLDER,
            "venue_type": REAL_BOT_VENUE,
        },
    )

    after = sorted(
        p.relative_to(state_dir) for p in state_dir.rglob("*") if p.is_file()
    )
    assert before == after, "assess_bot must be stateless (persist_history=False)"

    assert payload["asset"] == REAL_BOT_ASSET
    assert 0.0 <= payload["risk_score"] <= 100.0
    assert payload["verdict"]
    assert payload["risk_tier"]
    assert isinstance(payload["dimensions"], dict)
    assert isinstance(payload["warnings"], list)


# ---------------------------------------------------------------------------
# get_market
# ---------------------------------------------------------------------------


def test_get_market_returns_full_result():
    payload = _call("get_market", {"symbol": "BTC", "venue_type": "CEX"})
    assert payload["symbol"] == "BTC"
    assert payload["venue_type"] == "CEX"
    assert 0.0 <= payload["data_quality_score"] <= 1.0


@pytest.mark.parametrize("symbol", ["../../etc", "..", "a/b"])
def test_get_market_rejects_path_traversal(symbol):
    _call_raises("get_market", {"symbol": symbol, "venue_type": "CEX"})


def test_get_market_rejects_unknown_venue():
    _call_raises("get_market", {"symbol": "BTC", "venue_type": "XXX"})


def test_get_market_unknown_symbol_is_a_readable_message_not_empty():
    error = _call_raises("get_market", {"symbol": "KHONGTONTAI", "venue_type": "CEX"})
    assert "KHONGTONTAI" in str(error)


# ---------------------------------------------------------------------------
# Server wiring
# ---------------------------------------------------------------------------


def test_all_six_tools_are_registered():
    tools = asyncio.run(srv.mcp.list_tools())
    names = {tool.name for tool in tools}
    assert names == {
        "list_assets",
        "list_bots",
        "list_assessed_bots",
        "get_assessment",
        "assess_bot",
        "get_market",
    }


_ALL_TOOL_NAMES = {
    "list_assets",
    "list_bots",
    "list_assessed_bots",
    "get_assessment",
    "assess_bot",
    "get_market",
}


# ---------------------------------------------------------------------------
# Transport CLI: --transport http actually serves a remote MCP client, and
# the plain `python3 -m Agent.backend.scripts.agent_server` (stdio) invocation the
# docs and existing .mcp.json configs rely on still works unchanged.
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Ask the OS for a currently-unused TCP port, then release it.

    There is a small window between this close() and the server's own bind()
    where another process could grab the same port, but that is the standard
    trade-off for giving each test its own port without parsing the server's
    stdout for the one it actually chose -- acceptable here because the tests
    run on a single local machine, not a shared/contended CI port range.
    """
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_until_listening(host: str, port: int, timeout_s: float) -> bool:
    """Poll a TCP connect instead of sleeping a fixed amount: fast on a healthy
    server, and bounded so a broken one fails the test instead of hanging it."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with closing(socket.create_connection((host, port), timeout=0.2)):
                return True
        except OSError:
            time.sleep(0.05)
    return False


@contextmanager
def _running_http_server(
    host: str = "127.0.0.1", env: Optional[Dict[str, str]] = None
) -> Iterator[Tuple[str, int]]:
    """Spawn the real CLI entry point with --transport http and yield (host, port).

    `env=None` (the default, used by every pre-existing caller) inherits the
    full parent environment, same as omitting the argument to `Popen`
    entirely -- so this parameter is purely additive. Passing an explicit
    dict (built from `dict(os.environ)` plus overrides) is what the x402
    tests below use to turn `X402_ENABLED` on/off for one subprocess without
    touching this pytest process's own environment.

    Always terminates the subprocess on the way out, including when the test
    body raises, so a failing assertion never leaks a listening server behind
    it for the next test (or the next CI job) to trip over.
    """
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "Agent.backend.scripts.agent_server",
            "--transport",
            "http",
            "--host",
            host,
            "--port",
            str(port),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
    )
    try:
        if not _wait_until_listening(host, port, _STARTUP_TIMEOUT_S):
            proc.terminate()
            try:
                out, _ = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                out, _ = proc.communicate(timeout=5)
            pytest.fail(
                f"agent_server --transport http did not start listening on "
                f"{host}:{port} within {_STARTUP_TIMEOUT_S}s. Output:\n{out}"
            )
        yield host, port
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)


def test_http_transport_serves_a_real_mcp_client():
    """The important test: a real client, over the wire, not `call_tool()` in-process."""
    with _running_http_server() as (host, port):
        url = f"http://{host}:{port}/mcp"

        async def _run() -> None:
            from mcp.client.session import ClientSession
            from mcp.client.streamable_http import streamable_http_client

            async with streamable_http_client(url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    assert {tool.name for tool in tools.tools} == _ALL_TOOL_NAMES

                    result = await session.call_tool("list_assets", {})
                    assert not result.is_error
                    payload = json.loads(result.content[0].text)
                    assert isinstance(payload["assets"], list)
                    assert payload["assets"]

        asyncio.run(_run())


def test_http_transport_host_0_0_0_0_prints_a_warning():
    """Binding every interface must never be silent -- see agent_server.main()."""
    port = _free_port()
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "Agent.backend.scripts.agent_server",
            "--transport",
            "http",
            "--host",
            "0.0.0.0",
            "--port",
            str(port),
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        assert _wait_until_listening("127.0.0.1", port, _STARTUP_TIMEOUT_S)
    finally:
        proc.terminate()
        try:
            out, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate(timeout=5)
    assert "CẢNH BÁO" in out
    assert "0.0.0.0" in out


def test_stdio_transport_still_serves_a_real_mcp_client():
    """Regression check: the plain, argument-less invocation (stdio, the
    default) must keep working exactly as existing .mcp.json configs expect."""

    async def _run() -> None:
        from mcp.client.session import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "Agent.backend.scripts.agent_server"],
            cwd=str(REPO_ROOT),
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert {tool.name for tool in tools.tools} == _ALL_TOOL_NAMES

                result = await session.call_tool("list_assets", {})
                assert not result.is_error
                payload = json.loads(result.content[0].text)
                assert isinstance(payload["assets"], list)

    asyncio.run(asyncio.wait_for(_run(), timeout=_STARTUP_TIMEOUT_S))


# ---------------------------------------------------------------------------
# x402 payment gating (Agent.backend.external.payments.x402, wired via
# agent_server._require_payment). Every test in this section explicitly
# turns X402_ENABLED on: none of the 520+ tests above this line ever touch
# that flag, which is exactly what proves the default (off) path is
# byte-identical to before this feature existed.
# ---------------------------------------------------------------------------


class _FakeCtx:
    """Duck-typed stand-in for `mcp.server.mcpserver.Context`.

    `_require_payment()` only ever reads `.headers` off whatever it is
    given (see `srv._read_ctx_headers`), so a real SDK `Context` -- which
    needs a full `ServerRequestContext`/`ServerSession` to construct -- is
    unnecessary for testing the gate itself. `headers=None` reproduces what
    the SDK's stdio transport (and its own placeholder `Context()`, built
    when `MCPServer.call_tool()` is called with no `context=`) look like
    from `_require_payment`'s point of view.
    """

    def __init__(self, headers: Optional[Dict[str, str]] = None) -> None:
        self.headers = headers


def _payment_header_for(tool_name: str, **payload_overrides: str) -> str:
    """Build a well-formed PAYMENT-SIGNATURE header for `tool_name`, using
    whatever X402_* env vars are currently set (mirrors exactly what
    `agent_server._require_payment` itself would build server-side, so the
    client's `accepted` block matches the server's `requirements` and the
    local mismatch check in `verify_payment()` does not reject it before the
    facilitator mock even runs)."""
    settings = x402.X402Settings.from_env()
    requirements = x402.build_payment_requirements(tool_name, settings)
    payload = {
        "x402Version": 2,
        "payload": {"signature": "0xdeadbeef", **payload_overrides},
        "accepted": requirements.to_dict(),
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


@pytest.fixture
def x402_env(monkeypatch: pytest.MonkeyPatch):
    """Turn x402 ON with a fully-configured wallet/asset + facilitator
    credential set. `monkeypatch` reverts every env var on teardown, and the
    replay guard (process-wide, in-memory state -- see
    `x402.reset_replay_guard_for_tests` docstring) is cleared on both sides
    so no fingerprint leaks between tests."""
    monkeypatch.setenv("X402_ENABLED", "true")
    monkeypatch.setenv(
        "X402_PAY_TO_ADDRESS", "0x000000000000000000000000000000000000AA"
    )
    monkeypatch.setenv("X402_ASSET_ADDRESS", "0x000000000000000000000000000000000000BB")
    monkeypatch.setenv("OKX_X402_API_KEY", "merchant-key")
    monkeypatch.setenv("OKX_X402_API_SECRET", "merchant-secret")
    monkeypatch.setenv("OKX_X402_API_PASSPHRASE", "merchant-pass")
    x402.reset_replay_guard_for_tests()
    yield
    x402.reset_replay_guard_for_tests()


def test_x402_disabled_by_default_in_this_test_environment():
    """Canary: if this ever fails, every test above this section may have
    been silently running with payment gating on."""
    assert x402.is_x402_enabled() is False


def test_require_payment_is_a_no_op_when_disabled(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("X402_ENABLED", raising=False)
    # Must not raise, and must not even look at ctx (None would crash any
    # code path that tried to read .headers off it without checking first).
    srv._require_payment(None, "list_assets")
    srv._require_payment(_FakeCtx(headers={}), "assess_bot")


def test_call_tool_unaffected_when_disabled(monkeypatch: pytest.MonkeyPatch):
    """End-to-end through the real dispatch entrypoint, not just the gate
    function in isolation -- confirms adding `ctx: Context` to every tool's
    signature did not change the disabled-path behavior those tools had
    before this feature existed."""
    monkeypatch.delenv("X402_ENABLED", raising=False)
    payload = _call("list_assets", {})
    assert isinstance(payload["assets"], list)


@pytest.mark.parametrize(
    "tool_name,expected_price",
    [
        ("list_assets", "$0.001"),
        ("list_bots", "$0.001"),
        ("list_assessed_bots", "$0.001"),
        ("get_assessment", "$0.002"),
        ("get_market", "$0.005"),
        ("assess_bot", "$0.05"),
    ],
)
def test_require_payment_402_names_the_right_price_per_tool(
    x402_env, tool_name, expected_price
):
    with pytest.raises(ToolError) as excinfo:
        srv._require_payment(_FakeCtx(headers={}), tool_name)
    message = str(excinfo.value)
    assert expected_price in message
    assert x402.PAYMENT_REQUIRED_HEADER in message
    # The embedded value must itself decode to the real wire shape a client
    # would need to pay against -- not just a price mentioned in prose.
    b64_value = message.rsplit(f"{x402.PAYMENT_REQUIRED_HEADER}=", 1)[1].strip()
    decoded = json.loads(base64.b64decode(b64_value))
    assert decoded["accepts"][0]["extra"]["toolName"] == tool_name
    assert decoded["accepts"][0]["extra"]["usdPrice"] == expected_price


def test_require_payment_rejects_when_ctx_headers_raises(x402_env):
    """Simulates the SDK's own placeholder `Context()` (built by
    `MCPServer.call_tool()` when called with no `context=`, exactly what
    this file's `_call()`/`_call_raises()` helpers do): its `.headers`
    property raises `ValueError` because no real request is attached. The
    gate must treat that the same as "no headers supplied", not crash with
    an unrelated exception."""

    class _RaisingHeaders:
        @property
        def headers(self):
            raise ValueError("Context is not available outside of a request")

    with pytest.raises(ToolError, match="Payment is required"):
        srv._require_payment(_RaisingHeaders(), "list_assets")


def test_require_payment_rejects_when_server_wallet_not_configured(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("X402_ENABLED", "true")
    monkeypatch.delenv("X402_PAY_TO_ADDRESS", raising=False)
    monkeypatch.delenv("X402_ASSET_ADDRESS", raising=False)
    with pytest.raises(ToolError, match="cấu hình ví"):
        srv._require_payment(_FakeCtx(headers={}), "list_assets")


def test_require_payment_rejects_missing_merchant_credentials(
    x402_env, monkeypatch: pytest.MonkeyPatch
):
    """Thiếu credential merchant (OKX_X402_API_*) -> phải ném lỗi, không bao
    giờ cho tool chạy, kể cả khi client đã gửi một PAYMENT-SIGNATURE hợp lệ
    về mặt cấu trúc."""
    header = _payment_header_for("list_assets")
    monkeypatch.setenv("OKX_X402_API_KEY", "")
    monkeypatch.setenv("OKX_X402_API_SECRET", "")
    monkeypatch.setenv("OKX_X402_API_PASSPHRASE", "")

    with pytest.raises(ToolError, match="Xác minh thanh toán thất bại"):
        srv._require_payment(
            _FakeCtx(headers={x402.PAYMENT_SIGNATURE_HEADER: header}), "list_assets"
        )


def test_require_payment_facilitator_error_is_refused_not_passed_through(
    x402_env, monkeypatch: pytest.MonkeyPatch
):
    header = _payment_header_for("list_assets")

    def _boom(*args, **kwargs):
        raise x402.X402FacilitatorError("facilitator không trả lời")

    monkeypatch.setattr(x402, "verify_payment", _boom)

    with pytest.raises(ToolError, match="Xác minh thanh toán thất bại"):
        srv._require_payment(
            _FakeCtx(headers={x402.PAYMENT_SIGNATURE_HEADER: header}), "list_assets"
        )


def test_require_payment_denied_verdict_is_refused(
    x402_env, monkeypatch: pytest.MonkeyPatch
):
    header = _payment_header_for("list_assets")
    monkeypatch.setattr(
        x402,
        "verify_payment",
        lambda *a, **k: x402.VerifyResult(
            is_valid=False, invalid_reason="expired", invalid_message="hết hạn"
        ),
    )

    with pytest.raises(ToolError, match="Invalid payment") as excinfo:
        srv._require_payment(
            _FakeCtx(headers={x402.PAYMENT_SIGNATURE_HEADER: header}), "list_assets"
        )
    assert "expired" in str(excinfo.value)


def test_require_payment_allows_the_call_when_verified(
    x402_env, monkeypatch: pytest.MonkeyPatch
):
    header = _payment_header_for("list_assets")
    monkeypatch.setattr(
        x402,
        "verify_payment",
        lambda *a, **k: x402.VerifyResult(is_valid=True, payer="0xabc"),
    )

    # Must not raise: this is the "verify đạt -> tool chạy" branch.
    srv._require_payment(
        _FakeCtx(headers={x402.PAYMENT_SIGNATURE_HEADER: header}), "list_assets"
    )


def test_call_tool_runs_and_returns_real_data_after_payment_verified(
    x402_env, monkeypatch: pytest.MonkeyPatch
):
    """Full path through the real dispatch entrypoint: gate passes, tool body
    runs, real result comes back -- not just that the gate function itself
    doesn't raise."""
    header = _payment_header_for("list_assets")
    monkeypatch.setattr(
        x402,
        "verify_payment",
        lambda *a, **k: x402.VerifyResult(is_valid=True, payer="0xabc"),
    )
    ctx = _FakeCtx(headers={x402.PAYMENT_SIGNATURE_HEADER: header})

    result = asyncio.run(srv.mcp.call_tool("list_assets", {}, context=ctx))

    assert not result.is_error
    payload = json.loads(result.content[0].text)
    assert isinstance(payload["assets"], list)
    assert payload["assets"]


def test_call_tool_refuses_without_payment_over_the_normal_entrypoint(x402_env):
    """No context at all -- exactly what a caller who forgot to pay produces
    (the SDK builds its placeholder Context internally). Goes through
    `MCPServer.call_tool()`, not `_require_payment()` directly."""
    with pytest.raises(ToolError, match="Payment is required"):
        asyncio.run(srv.mcp.call_tool("list_assets", {}))


# ---------------------------------------------------------------------------
# x402 over the real HTTP wire -- the "chứng minh" (proof) scenario: a real
# subprocess server, a real MCP client, no in-process mocking at all. The
# facilitator itself is still never called for real (no PAYMENT-SIGNATURE
# header is sent, so verify_payment() is never reached), but everything
# from the client's TCP connection through JSON-RPC dispatch to
# `_require_payment` is exercised for real.
# ---------------------------------------------------------------------------


def test_http_transport_rejects_unpaid_call_when_x402_enabled():
    env = dict(os.environ)
    env.update(
        {
            "X402_ENABLED": "true",
            "X402_PAY_TO_ADDRESS": "0x000000000000000000000000000000000000AA",
            "X402_ASSET_ADDRESS": "0x000000000000000000000000000000000000BB",
        }
    )
    with _running_http_server(env=env) as (host, port):
        url = f"http://{host}:{port}/mcp"

        async def _run() -> None:
            from mcp.client.session import ClientSession
            from mcp.client.streamable_http import streamable_http_client

            async with streamable_http_client(url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool("list_assets", {})
                    assert result.is_error
                    text = result.content[0].text
                    assert "Payment is required" in text
                    assert "$0.001" in text
                    assert x402.PAYMENT_REQUIRED_HEADER in text

        asyncio.run(_run())


def test_http_transport_runs_normally_when_x402_disabled():
    """Same server, same tool call, x402 simply never turned on -- the
    control case for the test above."""
    env = dict(os.environ)
    env.pop("X402_ENABLED", None)
    with _running_http_server(env=env) as (host, port):
        url = f"http://{host}:{port}/mcp"

        async def _run() -> None:
            from mcp.client.session import ClientSession
            from mcp.client.streamable_http import streamable_http_client

            async with streamable_http_client(url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool("list_assets", {})
                    assert not result.is_error
                    payload = json.loads(result.content[0].text)
                    assert isinstance(payload["assets"], list)

        asyncio.run(_run())
