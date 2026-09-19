"""CLI for the live incremental poller.

    python3 -m Agent.backend.run_live --once
    python3 -m Agent.backend.run_live --watch
    python3 -m Agent.backend.run_live --watch --interval 60
    python3 -m Agent.backend.run_live --bot <uniqueCode>

Kept deliberately thin: all the polling/merge/scoring logic lives in
`Agent.backend.live.poller`, this file only wires up argv, picks which bots
to watch, and prints a final Vietnamese summary -- the network task this
project's other tools already insist on making visible, never silent.
"""

from __future__ import annotations

import argparse
import signal
import sys
import threading
import time

from Agent.backend.live.poller import LivePoller
from Agent.backend.live.store import load_bot_targets


def _select_targets(bot_code: str | None):
    targets = load_bot_targets()
    if not bot_code:
        return targets
    wanted = bot_code[len("bot_") :] if bot_code.startswith("bot_") else bot_code
    matched = [t for t in targets if t.unique_code == wanted]
    if not matched:
        codes = ", ".join(t.unique_code for t in targets)
        raise SystemExit(
            f"Bot '{bot_code}' not found among the 30 bots being watched. "
            f"Valid codes: {codes}"
        )
    return matched


def _summarize(changes) -> str:
    ok = [c for c in changes if c.ok]
    failed = [c for c in changes if not c.ok]
    stale = [c for c in changes if c.stale]
    moved = [c for c in changes if c.ok and c.changed]
    rescored = [c for c in moved if c.rescore is not None]
    tier_changed = [c for c in rescored if c.rescore.tier_changed]
    lines = [
        f"Total {len(changes)} bots: {len(ok)} fetched successfully, {len(failed)} failed"
        f" ({len(stale)} STALE).",
        f"Position changes: {len(moved)} bots; successfully rescored: {len(rescored)} bots.",
    ]
    if tier_changed:
        lines.append(f"TIER CHANGED: {len(tier_changed)} bots:")
        for change in tier_changed:
            outcome = change.rescore
            lines.append(
                f"  - {change.target.name} ({change.target.unique_code}): "
                f"{outcome.old_tier} -> {outcome.new_tier}"
            )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Update the positions of 30 copy-trading bots in real time"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--once", action="store_true", help="scan exactly one round then exit (default)"
    )
    mode.add_argument(
        "--watch", action="store_true", help="run continuously until Ctrl+C"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="seconds between rounds when using --watch (default 60s)",
    )
    parser.add_argument(
        "--bot", default=None, help="watch only one bot by uniqueCode"
    )
    args = parser.parse_args(argv)

    targets = _select_targets(args.bot)
    poller = LivePoller(targets=targets)

    if args.watch:
        stop_event = threading.Event()

        def _handle_sigint(signum, frame):  # noqa: ARG001 - signal handler signature
            print("\nStop signal received, finishing the current round then exiting...")
            stop_event.set()

        signal.signal(signal.SIGINT, _handle_sigint)
        poller.run_forever(args.interval, stop_event=stop_event)
        return 0

    started = time.monotonic()
    changes = poller.poll_once()
    elapsed = time.monotonic() - started
    print(f"\n================ DONE (took {elapsed:.1f}s) ================")
    print(_summarize(changes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
