"""Record what each ranked trader actually trades, from their own ledger.

Why this exists: `traderInsts` on the ranking says which instruments a trader is
configured for, and almost every trader declares almost everything -- 242 of 259
"trade BTC" by that measure, which makes "the top bot on BTC" collapse to "rank 1"
for all 15 assets. Only the ledger shows real exposure, so this profiles a rank
range and records, per asset, the trade count, notional and last close time.

It also answers whether a trader is still working: open positions, and how long
ago the last position closed.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

OKX = "https://www.okx.com/api/v5/copytrading"
UNIVERSE = Path(__file__).resolve().parent.parent.parent / "data" / "universe"
REQUEST_DELAY_SECONDS = 0.6
TRADER_DELAY_SECONDS = 0.4
HISTORY_LIMIT = 100


def fetch(url: str, timeout: int = 25) -> Dict[str, Any]:
    result = subprocess.run(
        ["curl", "-4", "-s", "-m", str(timeout), "-H", "User-Agent: Mozilla/5.0", url],
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"code": "-1", "msg": "unparseable response", "data": []}


def rows(payload: Dict[str, Any]) -> List[Any]:
    if payload.get("code") != "0":
        return []
    data = payload.get("data")
    return data if isinstance(data, list) else []


def owned(records: List[Dict[str, Any]], code: str) -> List[Dict[str, Any]]:
    """Drop anything the endpoint returned that belongs to another trader."""
    return [r for r in records if str(r.get("uniqueCode", code)) == code]


def profile(code: str) -> Dict[str, Any]:
    history = owned(
        rows(
            fetch(
                f"{OKX}/public-subpositions-history"
                f"?uniqueCode={code}&instType=SWAP&limit={HISTORY_LIMIT}"
            )
        ),
        code,
    )
    time.sleep(REQUEST_DELAY_SECONDS)
    positions = owned(
        rows(
            fetch(f"{OKX}/public-current-subpositions?uniqueCode={code}&instType=SWAP")
        ),
        code,
    )

    per_asset: Dict[str, Dict[str, float]] = {}
    last_close = 0
    for trade in history:
        inst = str(trade.get("instId") or "")
        if not inst:
            continue
        base = inst.split("-")[0].upper()
        bucket = per_asset.setdefault(base, {"trades": 0, "notional": 0.0})
        bucket["trades"] += 1
        try:
            bucket["notional"] += float(trade.get("margin") or 0) * float(
                trade.get("lever") or 0
            )
        except (TypeError, ValueError):
            pass
        try:
            last_close = max(last_close, int(trade.get("closeTime") or 0))
        except (TypeError, ValueError):
            pass

    open_assets: Dict[str, int] = {}
    for position in positions:
        inst = str(position.get("instId") or "")
        base = inst.split("-")[0].upper() if inst else "UNKNOWN_INSTRUMENT"
        open_assets[base] = open_assets.get(base, 0) + 1

    return {
        "uniqueCode": code,
        "history_sample": len(history),
        "history_truncated": len(history) >= HISTORY_LIMIT,
        "last_close_ms": last_close or None,
        "open_positions": len(positions),
        "per_asset": per_asset,
        "open_assets": open_assets,
        "profiled_at_ms": int(time.time() * 1000),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-rank", type=int, default=1)
    parser.add_argument("--to-rank", type=int, default=50)
    parser.add_argument("--out", type=Path, default=UNIVERSE / "trader_activity.json")
    args = parser.parse_args()

    traders = json.loads((UNIVERSE / "lead_traders.json").read_text(encoding="utf-8"))
    targets = [t for t in traders if args.from_rank <= t["rank"] <= args.to_rank]

    cache: Dict[str, Any] = {}
    if args.out.exists():
        cache = json.loads(args.out.read_text(encoding="utf-8"))

    print(f"Lập hồ sơ hạng {args.from_rank}-{args.to_rank} ({len(targets)} trader):")
    for i, trader in enumerate(targets, 1):
        code = trader["uniqueCode"]
        if code in cache:
            print(f"  [{i}/{len(targets)}] #{trader['rank']:<4} đã có trong cache")
            continue
        record = profile(code)
        record["rank"] = trader["rank"]
        record["nickName"] = trader["nickName"]
        cache[code] = record
        top = sorted(record["per_asset"].items(), key=lambda kv: -kv[1]["notional"])[:3]
        summary = ", ".join(f"{a} {v['trades']}" for a, v in top) or "không có lệnh"
        print(
            f"  [{i}/{len(targets)}] #{trader['rank']:<4} {str(trader['nickName'])[:18]:18s}"
            f" lệnh={record['history_sample']:<4} mở={record['open_positions']:<4} {summary}"
        )
        args.out.write_text(
            json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        time.sleep(TRADER_DELAY_SECONDS)

    print(f"\nĐã có hồ sơ cho {len(cache)} trader → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
