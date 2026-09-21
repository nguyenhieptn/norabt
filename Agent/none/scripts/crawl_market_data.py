"""Refresh the CEX/DEX market inputs that Logic 1 grades.

Why this exists: the orderbook snapshots shipped with the repo were hand-written
placeholders -- five assets sharing one timestamp, BTC quoted at 77,910 from March
2025, four round-number levels each. Logic 1 already refused them as STALE, but a
fabricated file in the tree is a trap for the next reader, so this script replaces
them with real OKX depth and fills the flow/OI/sentiment inputs that were absent.

Every field written here comes from a public OKX endpoint. Nothing is defaulted:
an endpoint that fails leaves the file untouched and the asset is reported as a
failure, so a missing source stays MISSING rather than becoming a plausible number.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
OKX = "https://www.okx.com/api/v5"
REQUEST_DELAY_SECONDS = 0.6
ASSET_DELAY_SECONDS = 1.0
BOOK_LEVELS = 50

CEX_ASSETS = ["BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "BNB", "LINK", "SUI"]
DEX_ASSETS = ["WBTC", "WETH", "SOL", "UNI", "PEPE"]


def fetch(url: str, timeout: int = 20) -> Dict[str, Any]:
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


def now_ms() -> int:
    return int(time.time() * 1000)


_CONTRACT_SIZES: Dict[str, float] = {}


def contract_size(inst_id: str) -> Optional[float]:
    """Coins per contract (ctVal). OKX book sizes are contracts, not coins."""
    if not _CONTRACT_SIZES:
        for row in rows(fetch(f"{OKX}/public/instruments?instType=SWAP")):
            try:
                _CONTRACT_SIZES[row["instId"]] = float(row["ctVal"])
            except (KeyError, TypeError, ValueError):
                continue
    return _CONTRACT_SIZES.get(inst_id)


def crawl_orderbook(asset: str, market_dir: Path) -> str:
    inst_id = f"{asset}-USDT-SWAP"
    data = rows(fetch(f"{OKX}/market/books?instId={inst_id}&sz={BOOK_LEVELS}"))
    if not data:
        return "THẤT BẠI: books rỗng"
    book = data[0]
    bids, asks = book.get("bids") or [], book.get("asks") or []
    if not bids or not asks:
        return "THẤT BẠI: không có bid/ask"

    ct_val = contract_size(inst_id)
    if ct_val is None:
        return "THẤT BẠI: không lấy được ctVal, không quy đổi được hợp đồng"

    # OKX rows are [price, size, deprecated, order_count] with size in CONTRACTS.
    # Depth is read as price x size, so sizes are converted to coins here --
    # otherwise ADA (ctVal 100) reads 100x too thin and BTC (ctVal 0.01) 100x
    # too deep, and a major pair gets mislabelled ILLIQUID.
    def levels(raw: List[Any]) -> List[List[str]]:
        return [
            [lv[0], f"{float(lv[1]) * ct_val:.10g}", lv[3]]
            for lv in raw
            if len(lv) >= 4
        ]

    payload = {
        "symbol": inst_id,
        "timestamp": int(book.get("ts") or now_ms()),
        "source": "OKX_PUBLIC_REST_market_books",
        "contract_size": ct_val,
        "size_unit": "BASE_COIN",
        "bids": levels(bids),
        "asks": levels(asks),
    }
    (market_dir / "orderbook_l2.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return f"orderbook {len(bids)}x{len(asks)} mức"


def last_price(inst_id: str) -> Optional[float]:
    data = rows(fetch(f"{OKX}/market/ticker?instId={inst_id}"))
    try:
        return float(data[0]["last"])
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def crawl_taker_flow(asset: str, market_dir: Path) -> str:
    inst_id = f"{asset}-USDT-SWAP"
    # Instrument-level, matching the OI and price we report beside it. The ccy-wide
    # feed sums every contract on the currency and describes a different universe.
    data = rows(
        fetch(
            f"{OKX}/rubik/stat/taker-volume-contract?instId={inst_id}&period=1H&limit=24"
        )
    )
    if not data:
        return "THẤT BẠI: taker-volume-contract rỗng"

    # Row 0 is the hour still in progress; its absolute volume is a partial count.
    now = now_ms()
    complete = [row for row in data if int(row[0]) + 3_600_000 <= now]
    if not complete:
        return "THẤT BẠI: chưa có khung giờ nào đóng"
    bucket = complete[0]

    ct_val = contract_size(inst_id)
    price = last_price(inst_id)
    if ct_val is None or price is None:
        return "THẤT BẠI: thiếu ctVal hoặc giá để quy USD"

    # [ts, sellVol, buyVol] in CONTRACTS -> coins -> USD.
    ts, sell_ct, buy_ct = int(bucket[0]), float(bucket[1]), float(bucket[2])
    sell_usd, buy_usd = sell_ct * ct_val * price, buy_ct * ct_val * price
    net = buy_usd - sell_usd
    ratio = buy_usd / sell_usd if sell_usd else None
    if ratio is None:
        label = "UNKNOWN"
    elif ratio >= 1.2:
        label = "BULLISH_AGGRESSIVE (Lực Mua chủ động áp đảo)"
    elif ratio <= 0.8:
        label = "BEARISH_AGGRESSIVE (Lực Bán xả thị trường áp đảo)"
    else:
        label = "BALANCED (Hai chiều cân bằng)"

    payload = {
        "name": f"taker_volume_{asset}",
        "updated_at": ts,
        "source": "OKX_PUBLIC_REST_rubik_taker_volume_contract",
        "basis": "INSTRUMENT_LEVEL",
        "unit": "USD",
        "bucket_complete": True,
        "data": {
            "ccy": asset,
            "symbol": inst_id,
            "period": "1H",
            "buy_vol_usd": buy_usd,
            "sell_vol_usd": sell_usd,
            "total_vol_usd": buy_usd + sell_usd,
            "buy_sell_ratio": ratio,
            "net_flow_usd": net,
            "flow_sentiment": label,
            "contract_size": ct_val,
            "reference_price": price,
            "updated_at": ts,
        },
    }
    (market_dir / f"taker_volume_{asset}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return f"taker net={net:+,.0f} USD (mua {buy_usd:,.0f} / bán {sell_usd:,.0f})"


def crawl_delta_oi(asset: str, market_dir: Path) -> str:
    inst_id = f"{asset}-USDT-SWAP"
    # Instrument-level history, not the ccy-wide rubik series: the latter sums every
    # contract on the currency and read up to 32 % above this instrument's real OI.
    series = rows(
        fetch(
            f"{OKX}/rubik/stat/contracts/open-interest-history"
            f"?instId={inst_id}&period=5m&limit=100"
        )
    )
    if len(series) < 3:
        return "THẤT BẠI: chuỗi OI quá ngắn"

    # Rows are [ts, oi_contracts, oi_ccy, oi_usd], newest first. Deltas across the
    # window give sigma meaning; a single snapshot would force sigma to 0 and make
    # every move look normal.
    try:
        oi = [float(row[3]) for row in series]
    except (IndexError, TypeError, ValueError):
        return "THẤT BẠI: chuỗi OI thiếu cột USD"
    ts = int(series[0][0])
    current, previous = oi[0], oi[1]
    deltas = [a - b for a, b in zip(oi[:-1], oi[1:])]
    sigma = statistics.pstdev(deltas) if len(deltas) > 1 else 0.0
    delta = current - previous
    zscore = delta / sigma if sigma else None
    buildup = zscore is not None and zscore >= 2.0

    payload = {
        "name": f"delta_oi_{inst_id}",
        "updated_at": ts,
        "source": "OKX_PUBLIC_REST_rubik_open_interest_history",
        "basis": "INSTRUMENT_LEVEL",
        "data": {
            "symbol": inst_id,
            "period": "5m",
            "current_oi_usd": current,
            "prev_oi_usd": previous,
            "delta_oi_usd": delta,
            "delta_oi_pct": (delta / previous * 100.0) if previous else None,
            "sigma_oi": sigma,
            "zscore": zscore,
            "sample_size": len(oi),
            "is_liquidity_buildup": buildup,
            "buildup_type": "OI_SPIKE" if buildup else "NONE",
            "updated_at": ts,
        },
    }
    (market_dir / f"delta_oi_{inst_id}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return f"OI {current:,.0f} USD, Δ={delta:+,.0f}"


def crawl_sentiment(asset: str, market_dir: Path) -> str:
    inst_id = f"{asset}-USDT-SWAP"
    ls_rows = rows(
        fetch(
            f"{OKX}/rubik/stat/contracts/long-short-account-ratio?ccy={asset}&period=1H"
        )
    )
    time.sleep(REQUEST_DELAY_SECONDS)
    funding = rows(fetch(f"{OKX}/public/funding-rate?instId={inst_id}"))
    time.sleep(REQUEST_DELAY_SECONDS)
    oi_now = rows(fetch(f"{OKX}/public/open-interest?instType=SWAP&instId={inst_id}"))

    if not ls_rows or not funding:
        return "THẤT BẠI: thiếu long/short hoặc funding"

    ls_ratio = float(ls_rows[0][1])
    observed = int(ls_rows[0][0])
    rate = float(funding[0]["fundingRate"])
    if ls_ratio >= 1.2:
        label = "BULLISH (Phe Long áp đảo)"
    elif ls_ratio <= 0.83:
        label = "BEARISH (Phe Short áp đảo)"
    else:
        label = "NEUTRAL (Hai phe cân bằng)"

    payload = {
        "symbol": inst_id,
        "updated_at": observed,
        "source": "OKX_PUBLIC_REST_long_short_contract+funding_rate+open_interest",
        "basis": "INSTRUMENT_LEVEL",
        "sentiment": {
            "symbol": inst_id,
            "base_ccy": asset,
            "ls_ratio": f"{ls_ratio:.2f}",
            "sentiment_label": label,
            "funding_rate": f"{rate * 100:+.4f}% / 8h",
            "next_funding_time": funding[0].get("nextFundingTime"),
            "open_interest_usd": float(oi_now[0]["oiUsd"]) if oi_now else None,
            "updated_at": observed,
        },
    }
    (market_dir / f"sentiment_{asset}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return f"L/S={ls_ratio:.2f} funding={rate * 100:+.4f}%"


def refresh_candles(market_dir: Path, inst_id_key: str) -> str:
    """Append the 1H candles published since the file was last written."""
    path = market_dir / "ohlcv_1h_2023_present.json"
    if not path.exists():
        return "THẤT BẠI: không có file nến"
    payload = json.loads(path.read_text(encoding="utf-8"))
    candles = payload.get("candles") or []
    inst_id = payload.get(inst_id_key)
    if not candles or not inst_id:
        return f"THẤT BẠI: file nến thiếu candles/{inst_id_key}"

    newest = max(int(c["timestamp"]) for c in candles)
    fresh = rows(fetch(f"{OKX}/market/candles?instId={inst_id}&bar=1H&limit=100"))
    if not fresh:
        return "THẤT BẠI: candles rỗng"

    added = []
    for row in fresh:
        ts = int(row[0])
        if ts <= newest:
            continue
        added.append(
            {
                "timestamp": ts,
                "datetime": time.strftime(
                    "%Y-%m-%d %H:%M:%S UTC", time.gmtime(ts / 1000)
                ),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "vol": float(row[5]),
                "volCcy": float(row[6]),
                "volCcyQuote": float(row[7]),
            }
        )
    if not added:
        return "đã mới nhất, không có nến mới"

    payload["candles"] = sorted(candles + added, key=lambda c: int(c["timestamp"]))
    payload["total_candles"] = len(payload["candles"])
    path.write_text(json.dumps(payload), encoding="utf-8")
    newest_added = max(added, key=lambda c: c["timestamp"])
    return f"+{len(added)} nến, mới nhất {newest_added['datetime']}"


DEXSCREENER = "https://api.dexscreener.com/latest/dex/tokens"
POOL_PRICE_TOLERANCE = 0.20


def select_pool(
    pairs: List[Dict[str, Any]], chain: str, reference: float
) -> Tuple[Optional[Tuple[float, float, Dict[str, Any]]], int]:
    """Deepest pool on the chain whose price agrees with the exchange reference.

    Returns ((liquidity_usd, price_usd, pair), rejected_count). Price is checked
    before liquidity is considered: the manipulated pools are precisely the ones
    claiming the most liquidity.
    """
    wanted = chain.lower()
    accepted: List[Tuple[float, float, Dict[str, Any]]] = []
    rejected = 0
    for pair in pairs:
        if wanted and str(pair.get("chainId", "")).lower() != wanted:
            continue
        try:
            price = float(pair["priceUsd"])
        except (KeyError, TypeError, ValueError):
            continue
        if price <= 0 or abs(price - reference) / reference > POOL_PRICE_TOLERANCE:
            rejected += 1
            continue
        liquidity = float((pair.get("liquidity") or {}).get("usd") or 0.0)
        accepted.append((liquidity, price, pair))
    if not accepted:
        return None, rejected
    return max(accepted, key=lambda item: item[0]), rejected


def crawl_pool_liquidity(asset: str, market_dir: Path) -> str:
    """Pick the deepest pool whose price agrees with the CEX reference.

    On-chain token feeds list manipulated pools next to real ones: UNI came back
    with a UNI/REN pair quoting 43,000,000 USD per UNI and 1.3 B of claimed
    liquidity. Sorting by liquidity alone walks straight into those, so any pool
    whose price disagrees with the exchange reference is discarded outright.
    """
    pool_path = market_dir / "pool_liquidity.json"
    candles_path = market_dir / "ohlcv_1h_2023_present.json"
    if not pool_path.exists() or not candles_path.exists():
        return "THẤT BẠI: thiếu pool_liquidity.json hoặc file nến"

    existing = json.loads(pool_path.read_text(encoding="utf-8"))
    address = (existing.get("base_token") or {}).get("address")
    if not address:
        return "THẤT BẠI: không có địa chỉ token"

    benchmark = json.loads(candles_path.read_text(encoding="utf-8")).get(
        "price_benchmark"
    )
    reference = last_price(benchmark) if benchmark else None
    if reference is None:
        return "THẤT BẠI: không lấy được giá tham chiếu từ sàn"

    payload = fetch(f"{DEXSCREENER}/{address}")
    pairs = payload.get("pairs") or []
    if not pairs:
        return "THẤT BẠI: DexScreener không trả pool nào"

    chosen, rejected = select_pool(pairs, str(existing.get("chain", "")), reference)
    if chosen is None:
        return f"THẤT BẠI: {rejected} pool đều lệch giá tham chiếu {reference:.6g}"
    liquidity, price, pair = chosen
    observed = int(time.time() * 1000)
    out = {
        "asset": asset,
        "chain": existing.get("chain"),
        "dex_id": pair.get("dexId"),
        "pair_address": pair.get("pairAddress"),
        "base_token": {
            "address": (pair.get("baseToken") or {}).get("address"),
            "name": (pair.get("baseToken") or {}).get("name"),
            "symbol": (pair.get("baseToken") or {}).get("symbol"),
        },
        "quote_token": {
            "address": (pair.get("quoteToken") or {}).get("address"),
            "name": (pair.get("quoteToken") or {}).get("name"),
            "symbol": (pair.get("quoteToken") or {}).get("symbol"),
        },
        "price_usd": price,
        "reference_price_usd": reference,
        "reference_instrument": benchmark,
        "price_gap_pct": (price - reference) / reference * 100.0,
        "tvl_usd": liquidity,
        "volume_24h_usd": float((pair.get("volume") or {}).get("h24") or 0.0),
        "pools_rejected_on_price": rejected,
        "observed_at": observed,
        "updated_at": observed,
        "source": "DEXSCREENER_PRICE_VALIDATED",
    }
    pool_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return (
        f"{pair.get('dexId')} {out['base_token']['symbol']}/{out['quote_token']['symbol']}"
        f" giá {price:.6g} (lệch {out['price_gap_pct']:+.1f}%), TVL {liquidity:,.0f},"
        f" loại {rejected} pool lệch giá"
    )


def refresh_dex_ticks(market_dir: Path) -> str:
    """Replace the tick print window with the latest public trades."""
    path = market_dir / "ticks_100ms_stream.json"
    if not path.exists():
        return "THẤT BẠI: không có file tick"
    payload = json.loads(path.read_text(encoding="utf-8"))
    pair = payload.get("benchmark_pair")
    if not pair:
        return "THẤT BẠI: file tick thiếu benchmark_pair"

    trades = rows(fetch(f"{OKX}/market/trades?instId={pair}&limit=100"))
    if not trades:
        return "THẤT BẠI: trades rỗng"

    payload["ticks"] = sorted(trades, key=lambda t: int(t["ts"]))
    payload["total_ticks"] = len(trades)
    payload["updated_at"] = max(int(t["ts"]) for t in trades)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    stamp = time.strftime(
        "%Y-%m-%d %H:%M:%S UTC", time.gmtime(payload["updated_at"] / 1000)
    )
    return f"{len(trades)} tick, mới nhất {stamp}"


def run_cex(assets: List[str], steps: List[str]) -> List[str]:
    failures = []
    for i, asset in enumerate(assets, 1):
        market_dir = DATA_DIR / "cex" / asset / "market"
        market_dir.mkdir(parents=True, exist_ok=True)
        print(f"[{i}/{len(assets)}] CEX/{asset}")

        jobs = []
        if "orderbook" in steps:
            jobs.append(
                ("orderbook", lambda a=asset, d=market_dir: crawl_orderbook(a, d))
            )
        if "flow" in steps:
            jobs += [
                ("taker", lambda a=asset, d=market_dir: crawl_taker_flow(a, d)),
                ("oi", lambda a=asset, d=market_dir: crawl_delta_oi(a, d)),
                ("sentiment", lambda a=asset, d=market_dir: crawl_sentiment(a, d)),
            ]
        if "candles" in steps:
            jobs.append(("candles", lambda d=market_dir: refresh_candles(d, "instId")))
        for label, job in jobs:
            outcome = job()
            print(f"      {label:10s} {outcome}")
            if outcome.startswith("THẤT BẠI"):
                failures.append(f"CEX/{asset}/{label}: {outcome}")
            time.sleep(REQUEST_DELAY_SECONDS)
        time.sleep(ASSET_DELAY_SECONDS)
    return failures


def run_dex(assets: List[str], steps: List[str]) -> List[str]:
    failures = []
    for i, asset in enumerate(assets, 1):
        market_dir = DATA_DIR / "dex" / asset / "market"
        print(f"[{i}/{len(assets)}] DEX/{asset}")
        jobs = []
        if "candles" in steps:
            jobs.append(
                ("candles", lambda d=market_dir: refresh_candles(d, "price_benchmark"))
            )
        if "ticks" in steps:
            jobs.append(("ticks", lambda d=market_dir: refresh_dex_ticks(d)))
        if "pool" in steps:
            jobs.append(
                ("pool", lambda a=asset, d=market_dir: crawl_pool_liquidity(a, d))
            )
        for label, job in jobs:
            outcome = job()
            print(f"      {label:10s} {outcome}")
            if outcome.startswith("THẤT BẠI"):
                failures.append(f"DEX/{asset}/{label}: {outcome}")
            time.sleep(REQUEST_DELAY_SECONDS)
        time.sleep(ASSET_DELAY_SECONDS)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cex", nargs="*", default=CEX_ASSETS)
    parser.add_argument("--dex", nargs="*", default=DEX_ASSETS)
    parser.add_argument(
        "--steps",
        nargs="*",
        default=["orderbook", "flow", "candles", "ticks", "pool"],
        choices=["orderbook", "flow", "candles", "ticks", "pool"],
    )
    args = parser.parse_args()

    failures: List[str] = []
    if {"orderbook", "flow", "candles"} & set(args.steps):
        failures += run_cex(args.cex, args.steps)
    if {"candles", "ticks", "pool"} & set(args.steps):
        failures += run_dex(args.dex, args.steps)

    print()
    if failures:
        print(f"Thất bại {len(failures)} mục — file cũ giữ nguyên, không ghi số bịa:")
        for f in failures:
            print(f"  · {f}")
    else:
        print("Tất cả các mục đều lấy được dữ liệu thật.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
