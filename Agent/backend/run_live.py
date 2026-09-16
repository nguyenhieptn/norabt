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
            f"Không tìm thấy bot '{bot_code}' trong 30 bot đang theo dõi. "
            f"Các mã hợp lệ: {codes}"
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
        f"Tổng {len(changes)} bot: {len(ok)} lấy được dữ liệu, {len(failed)} lỗi"
        f" ({len(stale)} STALE).",
        f"Đổi vị thế: {len(moved)} bot; chấm lại thành công: {len(rescored)} bot.",
    ]
    if tier_changed:
        lines.append(f"ĐỔI XẾP LOẠI: {len(tier_changed)} bot:")
        for change in tier_changed:
            outcome = change.rescore
            lines.append(
                f"  - {change.target.name} ({change.target.unique_code}): "
                f"{outcome.old_tier} -> {outcome.new_tier}"
            )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Cập nhật vị thế 30 bot copy-trading theo thời gian thực"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--once", action="store_true", help="quét đúng 1 vòng rồi thoát (mặc định)"
    )
    mode.add_argument(
        "--watch", action="store_true", help="chạy liên tục cho tới khi Ctrl+C"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="giây giữa hai vòng khi dùng --watch (mặc định 60s)",
    )
    parser.add_argument(
        "--bot", default=None, help="chỉ theo dõi đúng 1 bot theo uniqueCode"
    )
    args = parser.parse_args(argv)

    targets = _select_targets(args.bot)
    poller = LivePoller(targets=targets)

    if args.watch:
        stop_event = threading.Event()

        def _handle_sigint(signum, frame):  # noqa: ARG001 - signal handler signature
            print("\nĐã nhận tín hiệu dừng, kết thúc vòng hiện tại rồi thoát...")
            stop_event.set()

        signal.signal(signal.SIGINT, _handle_sigint)
        poller.run_forever(args.interval, stop_event=stop_event)
        return 0

    started = time.monotonic()
    changes = poller.poll_once()
    elapsed = time.monotonic() - started
    print(f"\n================ HOÀN TẤT (mất {elapsed:.1f}s) ================")
    print(_summarize(changes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
