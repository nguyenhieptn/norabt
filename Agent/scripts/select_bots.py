"""Pick two active lead traders per asset: the top-ranked one and a mid-pack one.

Why this exists: enumerating every bot that touches an asset costs a full crawl and
tells us nothing a paired sample does not. One top-ranked bot and one mid-pack bot
per asset contrasts "the board's best" against "a typical credible operator" on the
same market.

The pair is ordered by realised return, not by board position. Board rank moves
day to day and does not say a bot is doing well: sorting by rank put a +72.5 %
bot in the weaker slot on ETH and a +10.5 % bot under a +6.5 % one on ADA. The
leader is the best performer still available on the asset; the second is drawn
from the clearly weaker half, so the pair contrasts rather than ties.

Candidates come from each trader's own ledger (data/universe/trader_activity.json),
never from the ranking's `traderInsts`: that field lists what a trader is configured
to run and 242 of 259 traders declare BTC, which would collapse "the top BTC bot"
into "rank 1" for every asset. A trader also has to still be working -- an open book
or a close within the activity window -- or the snapshot describes a bot that stopped.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "universe"
LEADERBOARD = DATA_DIR / "lead_traders.json"
ACTIVITY = DATA_DIR / "trader_activity.json"

# The 15 working slots: 10 CEX + 5 DEX. A slot is a market we observe, not a bot
# pool -- OKX lead traders trade the underlying, so DEX/WBTC borrows BTC's bots and
# DEX/WETH borrows ETH's. Slots sharing an underlying share the same pair of bots.
ASSET_UNIVERSE = [
    ("CEX", "BTC", "BTC"),
    ("CEX", "ETH", "ETH"),
    ("CEX", "SOL", "SOL"),
    ("CEX", "XRP", "XRP"),
    ("CEX", "DOGE", "DOGE"),
    ("CEX", "ADA", "ADA"),
    ("CEX", "AVAX", "AVAX"),
    ("CEX", "BNB", "BNB"),
    ("CEX", "LINK", "LINK"),
    ("CEX", "SUI", "SUI"),
    ("DEX", "WBTC", "BTC"),
    ("DEX", "WETH", "ETH"),
    ("DEX", "SOL", "SOL"),
    ("DEX", "UNI", "UNI"),
    ("DEX", "PEPE", "PEPE"),
]

DEFAULT_SEED = 42
ACTIVE_WITHIN_DAYS = 7

# The leader must actually be doing well, not merely sit high on a board that
# reshuffles daily.
MIN_TOP_ROI_PCT = 0.0

# The market history runs from 2023, so a bot needs a real ledger before any of
# this is measurable: a handful of fills gives no win rate and no return
# distribution. Ask for a full one, and step down only where the asset cannot
# supply it. No lead trader runs a single asset -- asking for 30 fills on ADA
# alone would empty every pool but BTC and ETH -- so the per-asset bar stays
# small while the ledger bar does the work.
#   (total closed trades, closed trades on this asset)
EVIDENCE_LADDER = ((50, 3), (30, 3), (30, 1))
MIN_TRADES_ON_ASSET = EVIDENCE_LADDER[-1][1]
MIN_TOTAL_TRADES = EVIDENCE_LADDER[-1][0]

# Why the second pick was made.
WEAKER_PERFORMER = "WEAKER_PERFORMER"
NO_SECOND_BOT = "NO_SECOND_BOT"


def cell(text: Any, size: int) -> str:
    out, width = "", 0
    for ch in str(text):
        step = 2 if ord(ch) > 0x1100 and not (0x1160 <= ord(ch) <= 0x11FF) else 1
        if width + step > size:
            break
        out += ch
        width += step
    return out + " " * (size - width)


def is_active(record: Dict[str, Any], now_ms: int) -> bool:
    if record.get("open_positions"):
        return True
    last_close = record.get("last_close_ms")
    if not last_close:
        return False
    return (now_ms - int(last_close)) <= ACTIVE_WITHIN_DAYS * 86_400_000


def trades_on_asset(record: Dict[str, Any], asset: str) -> int:
    """Closed trades on the asset, not merely an open position on it.

    An open book with no closed history carries no PnL, no win rate and no return
    distribution, so such a bot cannot be risk-assessed on that asset at all.
    """
    stats = (record.get("per_asset") or {}).get(asset) or {}
    return int(stats.get("trades", 0))


def candidates_for(
    activity: List[Dict[str, Any]],
    asset: str,
    now_ms: int,
    min_trades: int = MIN_TRADES_ON_ASSET,
    min_total: int = MIN_TOTAL_TRADES,
) -> List[Dict[str, Any]]:
    return [
        r
        for r in activity
        if trades_on_asset(r, asset) >= min_trades
        and int(r.get("history_sample", 0)) >= min_total
        and is_active(r, now_ms)
    ]


def pool_for(
    activity: List[Dict[str, Any]], asset: str, now_ms: int, needed: int
) -> Tuple[List[Dict[str, Any]], Tuple[int, int]]:
    """Walk down the evidence ladder until the asset can fill its slots."""
    for total, on_asset in EVIDENCE_LADDER:
        pool = candidates_for(activity, asset, now_ms, on_asset, total)
        if len(pool) >= needed:
            return pool, (total, on_asset)
    last = EVIDENCE_LADDER[-1]
    return candidates_for(activity, asset, now_ms, last[1], last[0]), last


def roi_pct(record: Dict[str, Any]) -> float:
    try:
        return float(record.get("pnlRatio") or 0.0) * 100.0
    except (TypeError, ValueError):
        return 0.0


def pick_mid(
    free: List[Dict[str, Any]], top: Dict[str, Any], rng: random.Random
) -> Tuple[Optional[Dict[str, Any]], str]:
    """A random bot from the weaker half of what is left on this asset.

    Weaker half rather than the runner-up: the second slot stands for a bot that
    also runs but does not keep up, and the runner-up is often within noise of the
    leader, which would make the comparison say nothing.
    """
    weaker = sorted(
        (r for r in free if roi_pct(r) < roi_pct(top)),
        key=roi_pct,
        reverse=True,
    )
    if not weaker:
        return None, NO_SECOND_BOT
    half = weaker[len(weaker) // 2 :] if len(weaker) > 1 else weaker
    return rng.choice(half), WEAKER_PERFORMER


def select(
    universe: List[Tuple[str, str, str]],
    leaderboard: Path = LEADERBOARD,
    activity_path: Path = ACTIVITY,
    seed: int = DEFAULT_SEED,
    now_ms: Optional[int] = None,
) -> Dict[str, Any]:
    traders = json.loads(leaderboard.read_text(encoding="utf-8"))
    board = {t["uniqueCode"]: t for t in traders}
    activity = list(json.loads(activity_path.read_text(encoding="utf-8")).values())
    for record in activity:
        row = board.get(record["uniqueCode"], {})
        record.setdefault("rank", row.get("rank", 10**6))
        record.setdefault("pnlRatio", row.get("pnlRatio"))
        record.setdefault("winRatio", row.get("winRatio"))
    # Best performer first: this order decides who leads each asset.
    activity.sort(key=lambda r: (-roi_pct(r), r["rank"]))

    now = now_ms if now_ms is not None else int(time.time() * 1000)
    rng = random.Random(seed)

    def entry(record: Optional[Dict[str, Any]], asset: str) -> Optional[Dict[str, Any]]:
        if record is None:
            return None
        stats = (record.get("per_asset") or {}).get(asset, {})
        return {
            "code": record["uniqueCode"],
            "name": record.get("nickName") or record["uniqueCode"],
            "okx_rank": record["rank"],
            "roi_pct": roi_pct(record),
            "win_ratio": record.get("winRatio"),
            "trades_on_asset": int(stats.get("trades", 0)),
            "total_trades_sampled": int(record.get("history_sample", 0)),
            "notional_on_asset": float(stats.get("notional", 0.0)),
            "open_positions": record.get("open_positions", 0),
            "last_close_ms": record.get("last_close_ms"),
        }

    # Every slot gets its own two bots: the pair exists to be compared against each
    # other, so a bot reused across assets would compare a market with itself.
    slots_by_underlying: Dict[str, List[Tuple[str, str]]] = {}
    for venue, symbol, underlying in universe:
        slots_by_underlying.setdefault(underlying, []).append((venue, symbol))

    pools, thresholds, widest = {}, {}, {}
    for underlying, slots in slots_by_underlying.items():
        pools[underlying], thresholds[underlying] = pool_for(
            activity, underlying, now, 2 * len(slots)
        )
        # The widest pool is the asset's real resource, and it is what decides how
        # much slack an asset has against the assets it shares bots with.
        widest[underlying] = candidates_for(activity, underlying, now)
    # Scarcest first: AVAX and PEPE have exactly two eligible bots each, so if a
    # deeper asset claims one of them first the thin asset can no longer be paired.
    order = sorted(
        slots_by_underlying,
        key=lambda u: len(widest[u]) - 2 * len(slots_by_underlying[u]),
    )

    taken: set[str] = set()
    chosen: Dict[Tuple[str, str], Dict[str, Any]] = {}

    remaining_need = {u: 2 * len(sl) for u, sl in slots_by_underlying.items()}

    def reserved_by_others(underlying: str) -> set[str]:
        """Bots a tighter asset cannot give up.

        BNB, LINK and ADA draw from an overlapping handful of bots. Without this
        guard the asset allocated first takes what it likes and ADA is left with a
        single bot, so a pair it could have had disappears.
        """
        locked: set[str] = set()
        for other, need in remaining_need.items():
            if other == underlying or need <= 0:
                continue
            free = [r for r in widest[other] if r["uniqueCode"] not in taken]
            if len(free) <= need:
                locked.update(r["uniqueCode"] for r in free)
        return locked

    def available(underlying: str) -> Tuple[List[Dict[str, Any]], int]:
        """Free candidates, widening the evidence bar only when forced to.

        The bar is re-checked during allocation, not just up front: BNB and ADA
        draw from an overlapping set of three bots, so ADA can run out after BNB
        takes two even though its own pool looked large enough at the start.
        """
        locked = reserved_by_others(underlying)
        free = [
            r
            for r in pools[underlying]
            if r["uniqueCode"] not in taken and r["uniqueCode"] not in locked
        ]
        if free:
            return free, thresholds[underlying]
        wider = [
            r
            for r in widest[underlying]
            if r["uniqueCode"] not in taken and r["uniqueCode"] not in locked
        ]
        if wider:
            thresholds[underlying] = EVIDENCE_LADDER[-1]
        return wider, thresholds[underlying]

    for underlying in order:
        slots = slots_by_underlying[underlying]

        # Leaders for every slot on this asset first, so a second-slot draw cannot
        # take the bot that the asset's other slot would have led with. The asset is
        # finished before moving on, which is what protects a two-candidate asset
        # like AVAX from a deep asset claiming one of its only two bots.
        tops: Dict[Tuple[str, str], Optional[Dict[str, Any]]] = {}
        for slot in slots:
            free, _ = available(underlying)
            free = [r for r in free if roi_pct(r) >= MIN_TOP_ROI_PCT]
            top = free[0] if free else None
            if top:
                taken.add(top["uniqueCode"])
                remaining_need[underlying] -= 1
            tops[slot] = top

        for slot in slots:
            top = tops[slot]
            base = {
                "underlying": underlying,
                "candidates": len(pools[underlying]),
                "evidence_bar": {
                    "min_total_trades": thresholds[underlying][0],
                    "min_trades_on_asset": thresholds[underlying][1],
                },
            }
            if top is None:
                chosen[slot] = {
                    **base,
                    "top": None,
                    "mid": None,
                    "mid_basis": NO_SECOND_BOT,
                }
                continue
            free, _ = available(underlying)
            mid, basis = pick_mid(free, top, rng)
            if mid:
                taken.add(mid["uniqueCode"])
                remaining_need[underlying] -= 1
            base["min_trades_on_asset"] = thresholds[underlying]
            chosen[slot] = {
                **base,
                "top": entry(top, underlying),
                "mid": entry(mid, underlying),
                "mid_basis": basis,
            }

    records = [
        {**chosen[(venue, symbol)], "venue": venue, "symbol": symbol}
        for venue, symbol, _ in universe
    ]

    codes: List[str] = []
    for rec in records:
        for slot in ("top", "mid"):
            if rec[slot] and rec[slot]["code"] not in codes:
                codes.append(rec[slot]["code"])

    return {
        "assets": records,
        "unique_codes": codes,
        "seed": seed,
        "profiled_traders": len(activity),
        "active_window_days": ACTIVE_WITHIN_DAYS,
        "selected_at_ms": now,
    }


def render(result: Dict[str, Any]) -> str:
    lines = [
        cell("SLOT", 11)
        + cell("BOT CHẠY NGON", 24)
        + cell("ROI%", 8)
        + cell("lệnh", 6)
        + cell("/asset", 7)
        + cell("BOT YẾU HƠN", 22)
        + cell("ROI%", 8)
        + cell("lệnh", 6)
        + cell("/asset", 7)
        + "CĂN CỨ",
        "-" * 122,
    ]
    for rec in result["assets"]:
        top, mid = rec["top"], rec["mid"]
        basis = {
            WEAKER_PERFORMER: "bốc ngẫu nhiên trong nửa yếu hơn",
            NO_SECOND_BOT: "không còn bot thứ 2 chưa dùng",
        }[rec["mid_basis"]]
        bar = rec["evidence_bar"]
        if (bar["min_total_trades"], bar["min_trades_on_asset"]) != EVIDENCE_LADDER[0]:
            basis += (
                f" · asset mỏng, hạ chuẩn xuống {bar['min_total_trades']} lệnh tổng"
                f"/{bar['min_trades_on_asset']} lệnh trên asset"
            )
        lines.append(
            cell(f"{rec['venue']}/{rec['symbol']}", 11)
            + cell(top["name"] if top else "— không có —", 24)
            + cell(f"{top['roi_pct']:+.1f}" if top else "—", 8)
            + cell(top["total_trades_sampled"] if top else "—", 6)
            + cell(top["trades_on_asset"] if top else "—", 7)
            + cell(mid["name"] if mid else "— không có bot thứ 2 —", 22)
            + cell(f"{mid['roi_pct']:+.1f}" if mid else "—", 8)
            + cell(mid["total_trades_sampled"] if mid else "—", 6)
            + cell(mid["trades_on_asset"] if mid else "—", 7)
            + basis
        )

    slots = sum(1 for r in result["assets"] for s in ("top", "mid") if r[s])
    paired = sum(1 for r in result["assets"] if r["mid_basis"] == WEAKER_PERFORMER)
    lines += [
        "",
        f"Suất chọn: {slots}/{2 * len(result['assets'])}"
        f" · bot riêng biệt: {len(result['unique_codes'])} (seed={result['seed']})",
        f"Slot có đủ cặp ngon + yếu hơn: {paired}/{len(result['assets'])}"
        f" · slot đạt chuẩn cao nhất ({EVIDENCE_LADDER[0][0]} lệnh tổng"
        f"/{EVIDENCE_LADDER[0][1]} trên asset): "
        f"{sum(1 for r in result['assets'] if (r['evidence_bar']['min_total_trades'], r['evidence_bar']['min_trades_on_asset']) == EVIDENCE_LADDER[0])}"
        f"/{len(result['assets'])}"
        f" · đã lập hồ sơ {result['profiled_traders']} trader"
        f" · 'đang hoạt động' = có vị thế mở hoặc đóng lệnh trong"
        f" {result['active_window_days']} ngày",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--leaderboard", type=Path, default=LEADERBOARD)
    parser.add_argument("--activity", type=Path, default=ACTIVITY)
    parser.add_argument("--out", type=Path, default=DATA_DIR / "bot_selection.json")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--codes-only", action="store_true")
    args = parser.parse_args()

    result = select(ASSET_UNIVERSE, args.leaderboard, args.activity, seed=args.seed)
    args.out.write_text(
        json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8"
    )

    if args.codes_only:
        print(" ".join(result["unique_codes"]))
    elif args.json:
        print(json.dumps(result, indent=1, ensure_ascii=False))
    else:
        print(render(result))
        print(f"\nĐã ghi: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
