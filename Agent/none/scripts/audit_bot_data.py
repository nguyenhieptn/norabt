"""Check that every selected bot really carries the data the QC logic needs.

Why this exists: a bot folder existing is not the same as a bot being usable. The
risk logic needs a closed-trade ledger with PnL per trade, a weekly PnL series to
reconstruct capital, a current position book, and rows that actually belong to the
trader we asked for. This walks the selection and reports each requirement
separately, so a gap is visible as a gap rather than averaged into a score.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SELECTION = DATA_DIR / "universe" / "bot_selection.json"
ACTIVE_WITHIN_DAYS = 7

# Fields each closed trade must carry for the risk maths to run at all.
TRADE_FIELDS = (
    "subPosId",
    "instId",
    "posSide",
    "openTime",
    "closeTime",
    "pnl",
    "pnlRatio",
    "margin",
    "lever",
)


def find_folder(code: str) -> Optional[Path]:
    for path in DATA_DIR.rglob(f"bot_{code}"):
        if (path / "trade_list.json").exists():
            return path
    return None


def cell(text: Any, size: int) -> str:
    out, width = "", 0
    for ch in str(text):
        step = 2 if ord(ch) > 0x1100 and not (0x1160 <= ord(ch) <= 0x11FF) else 1
        if width + step > size:
            break
        out += ch
        width += step
    return out + " " * (size - width)


def audit_bot(code: str, asset: str, now_ms: int) -> Dict[str, Any]:
    folder = find_folder(code)
    if folder is None:
        return {
            "code": code,
            "asset": asset,
            "found": False,
            "problems": ["chưa crawl"],
        }

    overview = json.loads((folder / "overview.json").read_text(encoding="utf-8"))
    ledger = json.loads((folder / "trade_list.json").read_text(encoding="utf-8"))
    trades: List[Dict[str, Any]] = ledger.get("closed_trades") or []
    positions: List[Dict[str, Any]] = ledger.get("open_positions") or []
    weekly = overview.get("weekly_pnl_history") or []

    # Blocking: the risk logic cannot run at all. Noted: a gap OKX itself leaves,
    # recorded with its exact size instead of being hidden or inflated.
    problems: List[str] = []
    notes: List[str] = []

    foreign = sum(1 for t in trades if str(t.get("uniqueCode", code)) != code)
    if foreign:
        problems.append(f"{foreign} lệnh của trader khác")

    if not trades:
        problems.append("không có lệnh đóng nào")
    for field in TRADE_FIELDS:
        gaps = sum(1 for t in trades if t.get(field) in (None, ""))
        if not gaps:
            continue
        target = problems if gaps == len(trades) else notes
        target.append(f"{gaps}/{len(trades)} lệnh trống {field}")

    if not weekly:
        problems.append("không có chuỗi PnL tuần")
    for field in ("aum", "pnl", "pnlRatio", "winRatio"):
        if overview.get(field) in (None, ""):
            problems.append(f"overview thiếu {field}")

    failures = (overview.get("provenance") or {}).get("fetch_failures") or []
    if failures:
        notes.append(f"{len(failures)} request phải thử lại/thất bại")

    on_asset = sum(
        1 for t in trades if str(t.get("instId", "")).split("-")[0].upper() == asset
    )
    if on_asset == 0:
        problems.append(f"không có lệnh nào trên {asset}")

    last_close = max((int(t.get("closeTime") or 0) for t in trades), default=0)
    age_days = (now_ms - last_close) / 86_400_000 if last_close else None
    active = bool(positions) or (
        age_days is not None and age_days <= ACTIVE_WITHIN_DAYS
    )
    if not active:
        problems.append("không còn hoạt động")

    no_inst = sum(1 for p in positions if not p.get("instId"))

    return {
        "code": code,
        "asset": asset,
        "found": True,
        "folder": str(folder.relative_to(DATA_DIR)),
        "name": overview.get("nickName") or code,
        "trades": len(trades),
        "on_asset": on_asset,
        "positions": len(positions),
        "positions_without_instrument": no_inst,
        "weekly_points": len(weekly),
        "win_ratio": overview.get("winRatio"),
        "pnl": overview.get("pnl"),
        "roi_pct": overview.get("pnlRatio"),
        "last_close_days": age_days,
        "truncated": bool(ledger.get("ledger_truncated")),
        "problems": problems,
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=SELECTION)
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    now = int(time.time() * 1000)

    pairs: List[Tuple[str, str, str, str]] = []
    for record in selection["assets"]:
        for slot in ("top", "mid"):
            if record[slot]:
                pairs.append(
                    (
                        f"{record['venue']}/{record['symbol']}",
                        slot,
                        record[slot]["code"],
                        record["underlying"],
                    )
                )

    seen: Dict[str, Dict[str, Any]] = {}
    print(
        cell("SLOT", 12)
        + cell("VAI", 5)
        + cell("BOT", 22)
        + cell("lệnh", 6)
        + cell("/asset", 8)
        + cell("vị thế", 8)
        + cell("tuần", 6)
        + cell("win%", 7)
        + "THIẾU"
    )
    print("-" * 116)
    failures = 0
    for slot_name, role, code, underlying in pairs:
        key = f"{code}|{underlying}"
        if key not in seen:
            seen[key] = audit_bot(code, underlying, now)
        row = seen[key]
        if not row["found"]:
            print(
                cell(slot_name, 12) + cell(role, 5) + cell(code[:20], 22) + "CHƯA CRAWL"
            )
            failures += 1
            continue
        if row["problems"]:
            failures += 1
        win = f"{float(row['win_ratio']) * 100:.0f}" if row["win_ratio"] else "—"
        print(
            cell(slot_name, 12)
            + cell(role, 5)
            + cell(row["name"], 22)
            + cell(row["trades"], 6)
            + cell(row["on_asset"], 8)
            + cell(row["positions"], 8)
            + cell(row["weekly_points"], 6)
            + cell(win, 7)
            + (
                "; ".join(row["problems"])
                if row["problems"]
                else ("✓ đủ · " + "; ".join(row["notes"]) if row["notes"] else "✓ đủ")
            )
        )

    print()
    print(
        f"Suất kiểm: {len(pairs)} · bot riêng biệt: {len({c for _, _, c, _ in pairs})}"
        f" · suất có vấn đề: {failures}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
