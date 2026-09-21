"""Fetch 1H candles for the instruments bots trade outside the 15-asset universe.

Why this exists: the strategy analysis places every trade against the market phase
in force when it opened, and a trade on an instrument we hold no candles for can
only be counted as UNKNOWN. The 30 selected bots put 47 % of their fills into 144
other instruments, so phase coverage sat at 53 %. Pulling candles for the busiest
of those lifts it to ~88 % without touching the asset universe itself.

These are reference series for phase labelling only. They live apart from
data/cex and data/dex so they never widen the set of assets Logic 1 reports on.
"""

from __future__ import annotations

import argparse
import collections
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PHASE_DIR = DATA_DIR / "phases"
OKX = "https://www.okx.com/api/v5"
PAGE = 100
TARGET_CANDLES = 3000  # ~125 days, comfortably past the longest ledger we hold
REQUEST_DELAY_SECONDS = 0.25


def fetch(url: str, timeout: int = 20, attempts: int = 3) -> Dict[str, Any]:
    last: Dict[str, Any] = {"code": "-1", "msg": "no attempt", "data": []}
    for attempt in range(attempts):
        result = subprocess.run(
            [
                "curl",
                "-4",
                "-s",
                "-m",
                str(timeout),
                "-H",
                "User-Agent: Mozilla/5.0",
                url,
            ],
            capture_output=True,
            text=True,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            last = {"code": "-1", "msg": "unparseable", "data": []}
        else:
            if payload.get("code") == "0":
                return payload
            last = payload
        time.sleep(0.8 * (attempt + 1))
    return last


def rows(payload: Dict[str, Any]) -> List[Any]:
    data = payload.get("data") if payload.get("code") == "0" else None
    return data if isinstance(data, list) else []


def missing_symbols(limit: int) -> List[str]:
    """Instruments the selected bots trade most that we hold no candles for."""
    have = {p.parts[-3] for p in DATA_DIR.rglob("*/market/ohlcv_1h*.json")}
    have |= {p.stem for p in PHASE_DIR.glob("*.json")}
    selection = json.loads(
        (DATA_DIR / "universe" / "bot_selection.json").read_text(encoding="utf-8")
    )
    codes = {
        record[slot]["code"]
        for record in selection["assets"]
        for slot in ("top", "mid")
        if record[slot]
    }
    counts: collections.Counter = collections.Counter()
    for code in codes:
        for path in DATA_DIR.rglob(f"bot_{code}/trade_list.json"):
            ledger = json.loads(path.read_text(encoding="utf-8"))
            for trade in ledger.get("closed_trades") or []:
                symbol = str(trade.get("instId", "")).split("-")[0].upper()
                if symbol and symbol not in have:
                    counts[symbol] += 1
    return [symbol for symbol, _ in counts.most_common(limit)]


def crawl_symbol(symbol: str) -> str:
    inst_id = f"{symbol}-USDT-SWAP"
    collected: Dict[int, List[Any]] = {}
    cursor = ""
    while len(collected) < TARGET_CANDLES:
        url = f"{OKX}/market/history-candles?instId={inst_id}&bar=1H&limit={PAGE}"
        if cursor:
            url += f"&after={cursor}"
        batch = rows(fetch(url))
        if not batch:
            break
        for row in batch:
            collected[int(row[0])] = row
        cursor = str(batch[-1][0])
        if len(batch) < PAGE:
            break
        time.sleep(REQUEST_DELAY_SECONDS)

    if len(collected) < 400:
        return f"THẤT BẠI: chỉ lấy được {len(collected)} nến (cần tối thiểu 400)"

    candles = [
        {
            "timestamp": ts,
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts / 1000)),
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "vol": float(r[5]),
        }
        for ts, r in sorted(collected.items())
    ]
    PHASE_DIR.mkdir(parents=True, exist_ok=True)
    (PHASE_DIR / f"{symbol}.json").write_text(
        json.dumps(
            {
                "symbol": symbol,
                "instId": inst_id,
                "bar": "1H",
                "source": "OKX_PUBLIC_REST_history_candles",
                "purpose": "PHASE_REFERENCE_ONLY",
                "total_candles": len(candles),
                "candles": candles,
            }
        ),
        encoding="utf-8",
    )
    return f"{len(candles)} nến, từ {candles[0]['datetime'][:10]}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="*")
    parser.add_argument("--top", type=int, default=30)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    symbols = args.symbols or missing_symbols(args.top)
    if not symbols:
        print("Không còn instrument nào thiếu nến.")
        return 0

    print(f"Lấy nến tham chiếu cho {len(symbols)} instrument, {args.workers} luồng:")
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(crawl_symbol, s): s for s in symbols}
        for done, future in enumerate(as_completed(futures), 1):
            symbol = futures[future]
            try:
                outcome = future.result()
            except Exception as exc:  # noqa: BLE001 - one symbol must not kill the run
                outcome = f"THẤT BẠI: {type(exc).__name__}: {exc}"
            print(f"  [{done}/{len(symbols)}] {symbol:10s} {outcome}")
            if outcome.startswith("THẤT BẠI"):
                failures.append(symbol)

    print()
    print(f"Thất bại: {', '.join(failures)}" if failures else "Tất cả đều lấy được.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
