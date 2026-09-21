"""Derive each asset's macro context from the candle history already on disk.

Why this exists: Logic 1 grades a `macro` source for all 15 slots and it was pinned
to MISSING because nothing ever wrote one. MacroState asks for btc_correlation,
btc_beta, macro_regime and macro_event_risk -- the first three are computable from
the hourly candles we already hold, so no extra network call is needed and the
numbers are reproducible from the dataset.

macro_event_risk stays UNKNOWN. It needs an economic calendar we do not have, and
inventing a label would be worse than admitting the gap.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
REFERENCE = ("cex", "BTC")
WINDOW_HOURS = 720  # 30 days of hourly candles
MIN_OVERLAP = 200

# Regime thresholds, applied to the reference asset over the same window.
TREND_PCT = 3.0
HIGH_VOL_ANNUALISED_PCT = 80.0

SLOTS: List[Tuple[str, str]] = [
    ("cex", "BTC"),
    ("cex", "ETH"),
    ("cex", "SOL"),
    ("cex", "XRP"),
    ("cex", "DOGE"),
    ("cex", "ADA"),
    ("cex", "AVAX"),
    ("cex", "BNB"),
    ("cex", "LINK"),
    ("cex", "SUI"),
    ("dex", "WBTC"),
    ("dex", "WETH"),
    ("dex", "SOL"),
    ("dex", "UNI"),
    ("dex", "PEPE"),
]


def market_dir(venue: str, asset: str) -> Path:
    return DATA_DIR / venue / asset / "market"


def load_closes(venue: str, asset: str) -> Dict[int, float]:
    path = market_dir(venue, asset) / "ohlcv_1h_2023_present.json"
    if not path.exists():
        return {}
    candles = json.loads(path.read_text(encoding="utf-8")).get("candles") or []
    return {int(c["timestamp"]): float(c["close"]) for c in candles if c.get("close")}


def log_returns(closes: Dict[int, float], stamps: List[int]) -> List[float]:
    out = []
    for prev, curr in zip(stamps[:-1], stamps[1:]):
        a, b = closes.get(prev), closes.get(curr)
        if a and b and a > 0 and b > 0:
            out.append(math.log(b / a))
    return out


def pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    n = len(xs)
    if n < 2:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    return max(-1.0, min(1.0, cov / math.sqrt(vx * vy)))


def beta(asset_returns: List[float], ref_returns: List[float]) -> Optional[float]:
    n = len(asset_returns)
    if n < 2:
        return None
    ma, mr = sum(asset_returns) / n, sum(ref_returns) / n
    cov = sum((a - ma) * (r - mr) for a, r in zip(asset_returns, ref_returns))
    var = sum((r - mr) ** 2 for r in ref_returns)
    return cov / var if var > 0 else None


def reference_regime(ref_returns: List[float]) -> Tuple[str, float, float]:
    total = math.exp(sum(ref_returns)) - 1.0
    trend_pct = total * 100.0
    n = len(ref_returns)
    mean = sum(ref_returns) / n
    hourly_sd = math.sqrt(sum((r - mean) ** 2 for r in ref_returns) / n)
    vol_pct = hourly_sd * math.sqrt(24 * 365) * 100.0

    if vol_pct >= HIGH_VOL_ANNUALISED_PCT:
        regime = "RISK_OFF_VOLATILE" if trend_pct < 0 else "RISK_ON_VOLATILE"
    elif trend_pct >= TREND_PCT:
        regime = "RISK_ON"
    elif trend_pct <= -TREND_PCT:
        regime = "RISK_OFF"
    else:
        regime = "NEUTRAL"
    return regime, trend_pct, vol_pct


def build(slots: List[Tuple[str, str]], window_hours: int = WINDOW_HOURS) -> List[str]:
    ref_closes = load_closes(*REFERENCE)
    if not ref_closes:
        return [f"THẤT BẠI: không đọc được nến tham chiếu {REFERENCE[1]}"]

    failures: List[str] = []
    for venue, asset in slots:
        closes = load_closes(venue, asset)
        if not closes:
            failures.append(f"{venue}/{asset}: không có nến")
            print(f"  {venue}/{asset:8s} THẤT BẠI: không có nến")
            continue

        shared = sorted(set(closes) & set(ref_closes))[-window_hours:]
        if len(shared) < MIN_OVERLAP:
            failures.append(f"{venue}/{asset}: chỉ trùng {len(shared)} nến")
            print(f"  {venue}/{asset:8s} THẤT BẠI: chỉ trùng {len(shared)} nến")
            continue

        asset_ret = log_returns(closes, shared)
        ref_ret = log_returns(ref_closes, shared)
        pairs = min(len(asset_ret), len(ref_ret))
        asset_ret, ref_ret = asset_ret[:pairs], ref_ret[:pairs]

        regime, trend_pct, vol_pct = reference_regime(ref_ret)
        observed = min(max(closes), max(ref_closes))
        payload = {
            "asset": asset,
            "venue": venue.upper(),
            "source": "DERIVED_FROM_LOCAL_OHLCV_1H",
            "reference": f"{REFERENCE[0].upper()}/{REFERENCE[1]}",
            "observed_at": observed,
            "updated_at": observed,
            "window_hours": len(shared),
            "sample_size": pairs,
            "macro": {
                "btc_correlation": pearson(asset_ret, ref_ret),
                "btc_beta": beta(asset_ret, ref_ret),
                "macro_regime": regime,
                "reference_trend_pct": trend_pct,
                "reference_annualised_vol_pct": vol_pct,
                # No economic calendar source exists in this dataset.
                "macro_event_risk": "UNKNOWN",
            },
        }
        (market_dir(venue, asset) / "macro_context.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
        macro = payload["macro"]
        corr = macro["btc_correlation"]
        bet = macro["btc_beta"]
        print(
            f"  {venue}/{asset:8s} corr={corr:+.3f} beta={bet:+.2f} "
            f"regime={regime} (BTC {trend_pct:+.1f}%, vol {vol_pct:.0f}%/năm, n={pairs})"
        )
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window-hours", type=int, default=WINDOW_HOURS)
    args = parser.parse_args()

    print(
        f"Tính macro từ {args.window_hours}h nến gần nhất, tham chiếu {REFERENCE[1]}:"
    )
    failures = build(SLOTS, args.window_hours)
    print()
    print(f"Thất bại {len(failures)} slot." if failures else "Đủ 15 slot.")
    for f in failures:
        print(f"  · {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
