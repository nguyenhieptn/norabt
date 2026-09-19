from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from Agent.backend.infra.config import config
from Agent.backend.qc.reporting.cohort import CohortAssessmentService


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "List (and optionally delete) duplicate-content snapshot folders, "
            "keeping the copy with the fullest provenance for each bot"
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete. By default, only prints what would be deleted.",
    )
    args = parser.parse_args()

    data_dir = Path(config.DATA_DIR)
    # 1/1 là CỐ Ý, không phải lệch khỏi tham số sản xuất: công cụ này chỉ
    # cần `duplicate_snapshots` để tìm ảnh chụp trùng, không đọc một con số
    # mô phỏng nào. Chạy 10.000 lượt ở đây là đốt vài phút cho kết quả bị
    # vứt đi. Đừng "sửa" cho khớp `PRODUCTION_SIMULATION_*`.
    report = CohortAssessmentService(persist_history=False).scan(
        simulation_iterations=1, simulation_horizon=1
    )

    removable: list[tuple[str, str]] = []
    for row in report.rows:
        if row.status != "EVALUATED" or row.duplicate_snapshots <= 1:
            continue
        for location in row.snapshot_locations:
            if location != row.selected_snapshot:
                removable.append((row.nick_name, location))

    if not removable:
        print("No duplicate folders to clean up.")
        return 0

    print(f"{'DELETE MODE' if args.apply else 'DRY RUN -- nothing deleted yet'}")
    print(
        f"Will {'delete' if args.apply else 'delete (if run with --apply)'} {len(removable)} folders:\n"
    )
    by_bot: dict[str, list[str]] = {}
    for nick, location in removable:
        by_bot.setdefault(nick, []).append(location)
    for nick, locations in by_bot.items():
        selected = next(
            row.selected_snapshot for row in report.rows if row.nick_name == nick
        )
        print(f"  {nick} -- keeping {selected}")
        for location in locations:
            print(f"      drop  {location}")

    if not args.apply:
        print(
            "\nRe-run with --apply to actually delete. The original data is still at /home/ubuntu/norabt/data."
        )
        return 0

    removed = 0
    for _, location in removable:
        venue, asset, folder = location.split("/")
        target = data_dir / venue.lower() / asset / "bot" / folder
        if target.is_dir():
            shutil.rmtree(target)
            removed += 1
    print(f"\nDeleted {removed} duplicate folders.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
