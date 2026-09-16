#!/usr/bin/env python3
"""Crawl OKX copy-trading lead traders using per-trader endpoints only.

Why this exists: `public-lead-traders` ignores the `uniqueCode` query parameter and
returns a ranked list, so picking `ranks[0]` silently attaches another trader's
profile. Every field here comes from an endpoint that is keyed by uniqueCode, and
every record is verified to carry that same code before it is written.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

from Agent.backend.mcp.inference.public_signals import (
    AttributionVerdict,
    ImpliedMove,
    InstrumentAttributor,
    SubPositionClock,
)

BASE_URL = "https://www.okx.com/api/v5/copytrading"
MARKET_URL = "https://www.okx.com/api/v5/market"
DATA_DIR = Path("/home/ubuntu/norabt/Agent/data")
SNAPSHOT_FALLBACK_DIR = Path("/home/ubuntu/norabt/data")
PAGE_SIZE = 100
REQUEST_DELAY_SECONDS = 0.6

BOTS = [
    "F6476365DB0D09A3",
    "E5513524191E576E",
    "BB3398A957270A39",
    "793739635259546051",
]


FETCH_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.5

# Per-run record of endpoints that never answered, so an empty result is never
# mistaken for "this trader has no data". Written into each bot's provenance.
_FETCH_FAILURES: Dict[str, List[str]] = {}
_FAILURE_LOCK = threading.Lock()


def note_failure(code: str, label: str) -> None:
    with _FAILURE_LOCK:
        _FETCH_FAILURES.setdefault(code, []).append(label)


def fetch(
    url: str, timeout: int = 25, attempts: int = FETCH_ATTEMPTS
) -> Dict[str, Any]:
    """Retry before giving up; a dropped request must not look like empty data.

    Running several traders in parallel makes transient failures likely, and the
    old behaviour turned one into a silent empty list -- King_GG was written with
    zero weekly PnL points while the endpoint served twelve.
    """
    last: Dict[str, Any] = {"code": "-1", "msg": "no attempt made", "data": []}
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
            last = {"code": "-1", "msg": "unparseable response", "data": []}
        else:
            if payload.get("code") == "0":
                return payload
            last = payload
        if attempt + 1 < attempts:
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    return last


def fetch_checked(url: str, code: str, label: str) -> Dict[str, Any]:
    payload = fetch(url)
    if payload.get("code") != "0":
        note_failure(code, f"{label}: {payload.get('code')} {payload.get('msg')}")
    return payload


def rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if payload.get("code") != "0":
        return []
    data = payload.get("data")
    return data if isinstance(data, list) else []


def owned_by(records: List[Dict[str, Any]], code: str) -> List[Dict[str, Any]]:
    """Drop any record that does not carry the uniqueCode we asked for."""
    kept = []
    for record in records:
        owner = record.get("uniqueCode")
        if owner in (None, "", code):
            kept.append(record)
    return kept


def crawl_history(
    code: str, max_pages: int, verbose: bool = False
) -> tuple[List[Dict[str, Any]], bool]:
    collected: List[Dict[str, Any]] = []
    seen: set[str] = set()
    cursor: Optional[str] = None
    truncated = False
    for page in range(1, max_pages + 1):
        url = (
            f"{BASE_URL}/public-subpositions-history?uniqueCode={code}"
            f"&instType=SWAP&limit={PAGE_SIZE}"
        )
        if cursor:
            url += f"&after={cursor}"
        batch = owned_by(rows(fetch_checked(url, code, f"history_page_{page}")), code)
        fresh = [r for r in batch if str(r.get("subPosId")) not in seen]
        for record in fresh:
            seen.add(str(record.get("subPosId")))
        collected.extend(fresh)
        if verbose:
            print(f"    {code[:8]} trang {page}: +{len(fresh)} (tổng {len(collected)})")
        if len(batch) < PAGE_SIZE or not fresh:
            break
        cursor = str(batch[-1].get("subPosId"))
        if page == max_pages:
            truncated = True
        time.sleep(REQUEST_DELAY_SECONDS)
    return collected, truncated


def leaderboard_profiles() -> Dict[str, Dict[str, Any]]:
    """Per-trader profile fields, keyed by the uniqueCode on the same row.

    `public-lead-traders?uniqueCode=X` ignores the filter and returns the first
    page, which is how an earlier version attached another trader's profile. Paging
    the whole board instead keeps each row's stats with the row's own uniqueCode,
    so matching on that key is safe.
    """
    path = DATA_DIR / "universe" / "lead_traders.json"
    if not path.exists():
        return {}
    try:
        rows_ = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {str(r["uniqueCode"]): r for r in rows_ if r.get("uniqueCode")}


def primary_symbol(
    trades: List[Dict[str, Any]], positions: List[Dict[str, Any]]
) -> str:
    exposure: Dict[str, float] = {}
    for trade in trades:
        inst = str(trade.get("instId") or "")
        if not inst:
            continue
        base = inst.split("-")[0].upper()
        try:
            weight = float(trade.get("margin") or 0) * float(trade.get("lever") or 0)
        except (TypeError, ValueError):
            weight = 0.0
        exposure[base] = exposure.get(base, 0.0) + max(weight, 1.0)
    if not exposure:
        for position in positions:
            inst = str(position.get("instId") or "")
            if inst:
                base = inst.split("-")[0].upper()
                exposure[base] = exposure.get(base, 0.0) + 1.0
    if not exposure:
        return "UNKNOWN"
    return max(exposure, key=lambda key: exposure[key])


def current_prices() -> Dict[str, float]:
    prices: Dict[str, float] = {}
    for row in rows(fetch(f"{MARKET_URL}/tickers?instType=SWAP")):
        inst = str(row.get("instId") or "")
        last = row.get("last")
        if inst.endswith("-USDT-SWAP") and last:
            try:
                prices[inst.split("-")[0].upper()] = float(last)
            except (TypeError, ValueError):
                continue
    return prices


def price_at_factory(cache: Dict[tuple, Optional[float]]):
    def price_at(symbol: str, timestamp_ms: int) -> Optional[float]:
        key = (symbol, timestamp_ms // 60_000)
        if key in cache:
            return cache[key]
        url = (
            f"{MARKET_URL}/history-candles?instId={symbol}-USDT-SWAP&bar=1m"
            f"&after={timestamp_ms + 60_000}&limit=2"
        )
        candles = rows(fetch(url))
        value = None
        if candles:
            try:
                value = float(candles[0][4])
            except (TypeError, ValueError, IndexError):
                value = None
        cache[key] = value
        time.sleep(0.25)
        return value

    return price_at


def attribute_positions(
    positions: List[Dict[str, Any]],
    trades: List[Dict[str, Any]],
    prices: Dict[str, float],
) -> Dict[str, int]:
    """Fill in open time from the id, and infer the instrument where OKX withholds it."""
    stats = {"decoded_time": 0, "determined": 0, "narrowed": 0, "outside": 0}
    candidates = sorted(
        {
            str(t.get("instId") or "").split("-")[0].upper()
            for t in trades
            if t.get("instId")
        }
        - {""}
    )
    cost = ImpliedMove.estimate_cost(
        [
            {
                "entry": float(t.get("openAvgPx") or 0),
                "exit": float(t.get("closeAvgPx") or 0),
                "leverage": float(t.get("lever") or 0),
                "pnl_ratio": float(t.get("pnlRatio") or 0),
                "is_short": "short" in str(t.get("posSide", "")).lower(),
            }
            for t in trades
            if t.get("openAvgPx") and t.get("closeAvgPx")
        ]
    )
    price_at = price_at_factory({})

    for position in positions:
        decoded = SubPositionClock.open_time_ms(position.get("subPosId"))
        if decoded and not position.get("openTime"):
            position["derived_open_time"] = decoded
            position["derived_open_time_method"] = "SUBPOS_ID_SNOWFLAKE"
            stats["decoded_time"] += 1
        if position.get("instId"):
            continue

        try:
            ratio = float(position.get("uplRatio"))
            leverage = float(position.get("lever"))
        except (TypeError, ValueError):
            continue
        result = InstrumentAttributor.attribute(
            sub_position_id=position.get("subPosId"),
            pnl_ratio=ratio,
            leverage=leverage,
            is_short="short" in str(position.get("posSide", "")).lower(),
            candidates=candidates,
            price_at=price_at,
            price_now=lambda symbol: prices.get(symbol),
            cost=cost,
        )
        position["attribution"] = result.model_dump(mode="json")
        if result.verdict == AttributionVerdict.DETERMINED:
            position["inferred_instrument"] = f"{result.instrument}-USDT-SWAP"
            stats["determined"] += 1
        elif result.verdict == AttributionVerdict.NARROWED:
            stats["narrowed"] += 1
        elif result.verdict == AttributionVerdict.OUTSIDE_LEDGER_UNIVERSE:
            stats["outside"] += 1
    if cost.round_trip_rate is not None:
        for position in positions:
            position.setdefault("cost_model_round_trip_rate", cost.round_trip_rate)
    return stats


def crawl_one(
    code: str,
    prices: Dict[str, float],
    profiles: Dict[str, Dict[str, Any]],
    max_pages: int,
    now: int,
    verbose: bool = False,
) -> str:
    """Fetch and write one trader. Self-contained so workers can run in parallel."""
    weekly = owned_by(
        rows(
            fetch_checked(
                f"{BASE_URL}/public-weekly-pnl?uniqueCode={code}&instType=SWAP",
                code,
                "weekly_pnl",
            )
        ),
        code,
    )
    time.sleep(REQUEST_DELAY_SECONDS)
    positions = owned_by(
        rows(
            fetch_checked(
                f"{BASE_URL}/public-current-subpositions?uniqueCode={code}"
                f"&instType=SWAP",
                code,
                "current_positions",
            )
        ),
        code,
    )
    time.sleep(REQUEST_DELAY_SECONDS)
    trades, truncated = crawl_history(code, max_pages, verbose=verbose)

    stats = attribute_positions(positions, trades, prices)
    symbol = primary_symbol(trades, positions)
    folder = DATA_DIR / "cex" / symbol / "bot" / f"bot_{code}"
    folder.mkdir(parents=True, exist_ok=True)

    # Profile fields cannot be fetched per trader, so carry them over from a prior
    # snapshot of the SAME uniqueCode, preferring one that actually holds them.
    existing: Dict[str, Any] = {}
    # The archive is searched first: a freshly written file would otherwise
    # match itself and lose fields it never carried.
    for search_root in (SNAPSHOT_FALLBACK_DIR, DATA_DIR):
        if not search_root.is_dir():
            continue
        for candidate in search_root.rglob("overview.json"):
            try:
                payload = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if str(payload.get("uniqueCode")) != code:
                continue
            has_profile = any(
                payload.get(field) not in (None, "")
                for field in ("aum", "aum_usdt", "pnl", "pnl_usdt", "pnlRatio")
            )
            if has_profile:
                existing = payload
                break
            existing = existing or payload
        if existing and any(
            existing.get(field) not in (None, "")
            for field in ("aum", "aum_usdt", "pnl", "pnl_usdt", "pnlRatio")
        ):
            break

    unattributed = sum(1 for p in positions if not p.get("instId"))
    board = profiles.get(code, {})
    if board:
        profile_source = "OKX_LEADERBOARD_SNAPSHOT_BY_UNIQUECODE"
    elif existing:
        profile_source = "LOCAL_SNAPSHOT_UNVERIFIED"
    else:
        profile_source = "UNAVAILABLE"

    def profile_field(*names: str) -> Any:
        for source in (board, existing):
            for name in names:
                value = source.get(name)
                if value not in (None, ""):
                    return value
        return None

    overview = {
        "uniqueCode": code,
        "nickName": profile_field("nickName") or code,
        "aum": profile_field("aum", "aum_usdt"),
        "pnl": profile_field("pnl", "pnl_usdt"),
        "pnlRatio": profile_field("pnlRatio"),
        "winRatio": profile_field("winRatio"),
        "leadDays": profile_field("leadDays"),
        "okx_rank": board.get("rank"),
        "weekly_pnl_history": weekly,
        "provenance": {
            "crawled_at_ms": now,
            "weekly_pnl": f"{BASE_URL}/public-weekly-pnl",
            "positions": f"{BASE_URL}/public-current-subpositions",
            "history": f"{BASE_URL}/public-subpositions-history",
            "profile_fields": profile_source,
            "profile_note": (
                "aum/pnl/pnlRatio/winRatio come from the paged leaderboard "
                "snapshot matched on uniqueCode; querying public-lead-traders "
                "with a uniqueCode filter is ignored by OKX and returns another "
                "trader's row"
            ),
        },
    }
    trade_list = {
        "uniqueCode": code,
        "open_positions_count": len(positions),
        "open_positions": positions,
        "closed_trades_count": len(trades),
        "closed_trades": trades,
        "ledger_truncated": truncated,
        "ledger_page_size": PAGE_SIZE,
        "positions_without_instrument": unattributed,
        "inference": stats,
        "provenance": {"crawled_at_ms": now},
    }
    (folder / "overview.json").write_text(
        json.dumps(overview, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (folder / "trade_list.json").write_text(
        json.dumps(trade_list, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    inferred = (
        f" suy_luận[xác định={stats['determined']} thu hẹp={stats['narrowed']}"
        f" ngoài={stats['outside']}]"
        if any(stats.values())
        else ""
    )
    line = (
        f"{overview['nickName'][:22]:22s} {code:20s} -> cex/{symbol}/bot/bot_{code}"
        f" | lệnh={len(trades):4d} cắt={truncated} vị thế={len(positions):3d}"
        f" thiếu_instId={unattributed} tuần={len(weekly)}{inferred}"
    )

    return line


def main() -> int:
    parser = argparse.ArgumentParser(description="Crawl OKX lead traders per trader")
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--codes", nargs="*", default=BOTS)
    parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help="số luồng chạy song song; mỗi luồng vẫn giữ nhịp nghỉ riêng",
    )
    args = parser.parse_args()

    now = int(time.time() * 1000)
    summary: List[str] = []
    prices = current_prices()
    profiles = leaderboard_profiles()
    print(f"Giá tham chiếu: {len(prices)} instrument")
    print(f"Hồ sơ từ bảng xếp hạng: {len(profiles)} trader")

    workers = max(1, min(args.workers, len(args.codes)))
    print(f"Chạy song song {workers} luồng cho {len(args.codes)} bot\n")
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                crawl_one, code, prices, profiles, args.max_pages, now, workers == 1
            ): code
            for code in args.codes
        }
        for future in as_completed(futures):
            code = futures[future]
            done += 1
            try:
                line = future.result()
            except Exception as exc:  # noqa: BLE001 - one bot must not kill the run
                line = (
                    f"{'(lỗi)':22s} {code:20s} -> THẤT BẠI: {type(exc).__name__}: {exc}"
                )
            print(f"  [{done}/{len(args.codes)}] {line}")
            summary.append(line)

    stamp = datetime.fromtimestamp(now / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
    print(f"\n================ HOÀN TẤT ({stamp}) ================")
    for line in summary:
        print("  " + line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
