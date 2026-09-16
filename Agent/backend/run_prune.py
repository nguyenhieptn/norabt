from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from Agent.backend.infra.config import config
from Agent.backend.qc.reporting.cohort import CohortAssessmentService


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Liệt kê (và tuỳ chọn xoá) các thư mục snapshot trùng nội dung, "
            "giữ lại bản có provenance đầy đủ nhất cho mỗi bot"
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Thực sự xoá. Mặc định chỉ in ra những gì sẽ bị xoá.",
    )
    args = parser.parse_args()

    data_dir = Path(config.DATA_DIR)
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
        print("Không có thư mục trùng nào để dọn.")
        return 0

    print(f"{'CHẾ ĐỘ XOÁ' if args.apply else 'CHẠY THỬ — chưa xoá gì'}")
    print(
        f"Sẽ {'xoá' if args.apply else 'xoá (nếu chạy --apply)'} {len(removable)} thư mục:\n"
    )
    by_bot: dict[str, list[str]] = {}
    for nick, location in removable:
        by_bot.setdefault(nick, []).append(location)
    for nick, locations in by_bot.items():
        selected = next(
            row.selected_snapshot for row in report.rows if row.nick_name == nick
        )
        print(f"  {nick} — giữ lại {selected}")
        for location in locations:
            print(f"      bỏ  {location}")

    if not args.apply:
        print(
            "\nChạy lại với --apply để xoá thật. Dữ liệu gốc vẫn còn ở /home/ubuntu/norabt/data."
        )
        return 0

    removed = 0
    for _, location in removable:
        venue, asset, folder = location.split("/")
        target = data_dir / venue.lower() / asset / "bot" / folder
        if target.is_dir():
            shutil.rmtree(target)
            removed += 1
    print(f"\nĐã xoá {removed} thư mục trùng.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
