"""Snapshot the OKX lead-trader ranking and which instruments each one runs.

Why this exists: the earlier asset->bot map was built by pulling every trader's
ledger, which cost ~260 paged requests and went stale within a day. The ranking
itself publishes `traderInsts` per trader, so one pass of 13 pages rebuilds the
map. Rank order in this response IS OKX's own ranking, which is what "top 1" and
"rank 20-50" refer to.

`traderInsts` says what a trader is configured to run, not what they filled last
week. It is a pre-filter for choosing who to crawl; activity is then confirmed
against each chosen trader's own ledger, never assumed from this list.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List

OKX = "https://www.okx.com/api/v5/copytrading"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "universe"
PAGE_SIZE = 20
REQUEST_DELAY_SECONDS = 0.8


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


def scan(page_size: int = PAGE_SIZE) -> List[Dict[str, Any]]:
    traders: List[Dict[str, Any]] = []
    seen: set[str] = set()
    page = 1
    while True:
        payload = fetch(
            # No sortType: that is OKX's own default ranking, and it is what
            # "top 1" and "rank 20-50" refer to. Passing sortType=pnl_ratio
            # silently narrows the board from 259 traders to 82.
            f"{OKX}/public-lead-traders?instType=SWAP&limit={page_size}&page={page}"
        )
        if payload.get("code") != "0":
            print(f"  trang {page}: lỗi {payload.get('code')} {payload.get('msg')}")
            break
        blocks = payload.get("data") or []
        ranks = blocks[0].get("ranks") if blocks else []
        if not ranks:
            break

        fresh = 0
        for row in ranks:
            code = row.get("uniqueCode")
            if not code or code in seen:
                continue
            seen.add(code)
            fresh += 1
            traders.append(
                {
                    "rank": len(traders) + 1,
                    "uniqueCode": code,
                    "nickName": row.get("nickName"),
                    "aum": row.get("aum"),
                    "pnl": row.get("pnl"),
                    "pnlRatio": row.get("pnlRatio"),
                    "winRatio": row.get("winRatio"),
                    "leadDays": row.get("leadDays"),
                    "copyTraderNum": row.get("copyTraderNum"),
                    "maxCopyTraderNum": row.get("maxCopyTraderNum"),
                    "copyState": row.get("copyState"),
                    "traderInsts": row.get("traderInsts") or [],
                }
            )
        print(f"  trang {page}: +{fresh} (tổng {len(traders)})")
        if fresh == 0:
            break
        page += 1
        time.sleep(REQUEST_DELAY_SECONDS)
    return traders


def build_map(traders: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """asset -> trader codes, each list left in rank order."""
    per_asset: Dict[str, List[str]] = {}
    for trader in traders:
        for inst in trader["traderInsts"]:
            base = str(inst).split("-")[0].upper()
            per_asset.setdefault(base, []).append(trader["uniqueCode"])
    return per_asset


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-size", type=int, default=PAGE_SIZE)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    print(f"Quét bảng xếp hạng OKX (mỗi trang {args.page_size}):")
    traders = scan(args.page_size)
    if not traders:
        print("Không lấy được trader nào — không ghi đè dữ liệu cũ.")
        return 1

    per_asset = build_map(traders)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    observed = int(time.time() * 1000)
    (args.out_dir / "lead_traders.json").write_text(
        json.dumps(traders, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (args.out_dir / "asset_bot_map.json").write_text(
        json.dumps(
            {
                "observed_at": observed,
                "source": "OKX_public_lead_traders.traderInsts",
                "any": per_asset,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    no_insts = sum(1 for t in traders if not t["traderInsts"])
    print(
        f"\nTổng {len(traders)} trader · {len(per_asset)} asset xuất hiện"
        f" · {no_insts} trader không khai traderInsts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
