"""CLI chẩn đoán: OKX connect được chưa, và tương tác được không.

    python3 -m Agent.backend.run_probe                       # public + private
    python3 -m Agent.backend.run_probe --copy-trading         # + dry-run copy trading
    python3 -m Agent.backend.run_probe --copy-trading --execute   # gọi thật (chỉ demo)

Chạy từ /home/ubuntu/norabt. Không gọi run_report.py (nặng, ~4 phút) -- công cụ
này chỉ gọi vài request public/private nhẹ, có nghỉ giữa các lần gọi để tôn
trọng giới hạn 5 request/2 giây của nhóm endpoint copytrading.
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict

from Agent.backend.infra.config import config
from Agent.backend.okx.probe import (
    LiveTradingRefused,
    check_private_access,
    check_public_access,
    probe_copy_trading,
)

_RULE_WIDTH = 78


def _rule(char: str = "=") -> str:
    return char * _RULE_WIDTH


def _section(title: str) -> None:
    print()
    print(_rule())
    print(title)
    print(_rule())


def _mark(ok: Any) -> str:
    if ok is True:
        return "✓"  # ✓
    if ok is False:
        return "✗"  # ✗
    return "?"


def _print_public(result: Dict[str, Any]) -> None:
    _section("[1] IS THE EXCHANGE REACHABLE? (public, no API key needed)")
    for check in result["checks"]:
        latency = (
            f"{check['latency_ms']:.0f} ms" if check["latency_ms"] is not None else "-"
        )
        print(
            f"{_mark(check['ok'])} {check['name']} -- {check['endpoint']} ({latency})"
        )
        if not check["ok"]:
            print(f"    ACTION NEEDED: {check['detail']}")

    skew = result["clock_skew_ms"]
    if skew is None:
        print(f"{_mark(None)} Clock skew vs the OKX server: could not measure.")
    else:
        ok = result["clock_skew_ok"]
        print(f"{_mark(ok)} Clock skew vs the OKX server: {skew:+.1f} ms")
        if not ok:
            print(
                "    ACTION NEEDED: skew is >= 30 seconds (30000 ms), OKX will "
                "reject every signed request (code 50102). Resync the system "
                "clock (NTP) before debugging any signature error."
            )

    status = result["status"]
    if status == "OK":
        print("CONCLUSION: the OKX exchange is reachable at the public level.")
    elif status == "LOI_MOT_PHAN":
        print(
            "CONCLUSION: partially reachable -- some public endpoints are failing (see above)."
        )
    else:
        print("CONCLUSION: OKX is NOT reachable (every public endpoint failed).")


def _print_private(result: Dict[str, Any]) -> None:
    _section("[2] CAN WE INTERACT? -- OKX KEY (private, read-only, no orders placed)")
    status = result["status"]
    if status == "CHUA_CAU_HINH":
        print(f"{_mark(False)} OKX key not configured.")
        print(f"    Missing environment variables: {', '.join(result['missing_fields'])}")
        print(
            "    ACTION NEEDED: fill in the variables above in Agent/.env (see Agent/.env.example)."
        )
        return

    env = result.get("environment", "?")
    if status == "OK":
        print(f"{_mark(True)} Key works on the {env} environment.")
        print(f"    {result['message_vi']}")
    elif status == "LOI_KET_NOI":
        print(f"{_mark(False)} Could not connect to OKX (environment {env}).")
        print(f"    ACTION NEEDED: {result['message_vi']}")
    else:  # LOI -- OKX answered and rejected the key
        print(f"{_mark(False)} OKX rejected the key (environment {env}).")
        print(f"    Error code: {result['error_code']} -- {result['message_vi']}")


def _print_copy_trading(result: Dict[str, Any], *, executed: bool) -> None:
    mode = "REAL CALL" if executed else "DRY-RUN (preview only, no network call)"
    _section(f"[3] COPY TRADING INTERACTION -- {mode}")
    status = result["status"]

    if status == "DRY_RUN":
        call = result["would_call"]
        print(f"Would call: {call['method']} {call['endpoint']}")
        print(f"Body: {call['body']}")
        print(f"Headers (secrets masked): {call['headers']}")
        print(f"{result['message_vi']}")
        return

    if status == "CHUA_CAU_HINH":
        print(f"{_mark(False)} OKX key not configured.")
        print(f"    Missing environment variables: {', '.join(result['missing_fields'])}")
        print(
            "    ACTION NEEDED: fill in the variables above in Agent/.env, then re-run with --execute."
        )
        return

    if status == "LOI_KET_NOI":
        print(f"{_mark(False)} Could not call OKX.")
        print(f"    ACTION NEEDED: {result['message_vi']}")
        return

    if status == "DEMO_KHONG_HO_TRO":
        print(f"{_mark(True)} Got an answer: {result['message_vi']}")
        print(f"    OKX error code: {result['code']} (raw msg: {result['raw_msg']!r})")
        return

    if status == "DEMO_CO_HO_TRO":
        print(f"{_mark(True)} Got an answer: {result['message_vi']}")
        print(f"    !!! {result['canh_bao']}")
        return

    if status == "MA_LOI_KHAC":
        print(f"{_mark(False)} {result['message_vi']}")
        return

    print(f"{_mark(False)} Unknown status: {result}")


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m Agent.backend.run_probe",
        description="Diagnose OKX connectivity and interaction capability.",
    )
    parser.add_argument(
        "--copy-trading",
        action="store_true",
        help="Also run probe_copy_trading (dry-run by default, no network call).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Call copy trading for real instead of dry-run (demo only).",
    )
    args = parser.parse_args(argv)
    if args.execute and not args.copy_trading:
        parser.error("--execute only makes sense together with --copy-trading")

    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S UTC")
    print(_rule())
    print("OKX CONNECTIVITY & INTERACTION DIAGNOSTIC")
    print(now)
    # Show a relative path for brevity (e.g. "Agent/.env") when run from the
    # repo root; fall back to the absolute path if a relative one can't be computed.
    try:
        env_file_display = os.path.relpath(config.ENV_FILE_PATH)
    except ValueError:
        env_file_display = config.ENV_FILE_PATH
    if config.ENV_FILE_LOADED:
        print(
            f"Config source: {env_file_display} "
            f"(loaded {config.ENV_FILE_VARS_LOADED} variables)"
        )
    else:
        print(
            f"Config source: {env_file_display} not found, using environment variables only"
        )
    print(_rule())

    public_result = check_public_access()
    _print_public(public_result)

    time.sleep(0.5)
    private_result = check_private_access()
    _print_private(private_result)

    exit_code = 0
    if public_result["status"] == "LOI":
        exit_code = 1

    if args.copy_trading:
        time.sleep(0.5)
        try:
            copy_result = probe_copy_trading(dry_run=not args.execute)
        except LiveTradingRefused as exc:
            _section("[3] COPY TRADING INTERACTION")
            print(f"{_mark(False)} REFUSED TO RUN: {exc}")
            return 2
        _print_copy_trading(copy_result, executed=args.execute)

    print()
    print(_rule())
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
