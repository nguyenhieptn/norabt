"""Fill missing aum/pnl/winRatio on already-crawled bots from the ranking snapshot.

Why this exists: the crawler dropped `public-lead-traders` because querying it with
a uniqueCode filter returns another trader's row. Paging the whole board keeps each
row's stats attached to that row's own uniqueCode, so those fields can be restored
without re-crawling ledgers. Only fields that are currently absent are written, and
each patched file records where the values came from.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
LEADERBOARD = DATA_DIR / "universe" / "lead_traders.json"
FIELDS = ("nickName", "aum", "pnl", "pnlRatio", "winRatio", "leadDays")
SOURCE = "OKX_LEADERBOARD_SNAPSHOT_BY_UNIQUECODE"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true", help="ghi thật, mặc định chạy thử"
    )
    args = parser.parse_args()

    board: Dict[str, Dict[str, Any]] = {
        str(r["uniqueCode"]): r
        for r in json.loads(LEADERBOARD.read_text(encoding="utf-8"))
        if r.get("uniqueCode")
    }

    patched = missing = 0
    for path in sorted(DATA_DIR.rglob("bot_*/overview.json")):
        code = path.parent.name.replace("bot_", "")
        row = board.get(code)
        overview = json.loads(path.read_text(encoding="utf-8"))
        gaps = [f for f in FIELDS if overview.get(f) in (None, "", code)]
        if not gaps:
            continue
        if row is None:
            missing += 1
            print(
                f"  {code[:20]:22s} thiếu {','.join(gaps)} — không có trong bảng xếp hạng"
            )
            continue

        filled = [f for f in gaps if row.get(f) not in (None, "")]
        if not filled:
            missing += 1
            print(f"  {code[:20]:22s} bảng xếp hạng cũng không có {','.join(gaps)}")
            continue

        for field in filled:
            overview[field] = row[field]
        overview["okx_rank"] = row.get("rank")
        provenance = overview.setdefault("provenance", {})
        provenance["profile_fields"] = SOURCE
        provenance["profile_backfilled_at_ms"] = int(time.time() * 1000)
        provenance["profile_backfilled_fields"] = filled
        patched += 1
        print(f"  {str(row.get('nickName'))[:20]:22s} bù {','.join(filled)}")
        if args.apply:
            path.write_text(
                json.dumps(overview, indent=2, ensure_ascii=False), encoding="utf-8"
            )

    print()
    mode = "đã ghi" if args.apply else "CHẠY THỬ — chưa ghi gì"
    print(f"{mode}: bù được {patched} bot · còn thiếu không bù được {missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
