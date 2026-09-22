#!/usr/bin/env python3
import subprocess
import json
import time
from pathlib import Path


def fetch(url):
    res = subprocess.run(
        ["curl", "-4", "-s", "-m", "10", "-H", "User-Agent: Mozilla/5.0", url],
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(res.stdout).get("data", [])
    except (json.JSONDecodeError, AttributeError):
        return []


def main():
    target_assets = [
        "BTC",
        "ETH",
        "SOL",
        "ADA",
        "AVAX",
        "BNB",
        "DOGE",
        "LINK",
        "SUI",
        "XRP",
        "HYPE",
        "MU",
        "SKHYNIX",
        "PEPE",
        "UNI",
    ]

    # Load or fetch lead traders
    lead_path = Path("Agent/data/market/scanned_lead_traders.json")
    if lead_path.exists():
        with open(lead_path) as f:
            traders = json.load(f)
    else:
        traders = []
        for page in range(1, 15):
            url = f"https://www.okx.com/api/v5/copytrading/public-lead-traders?instType=SWAP&page={page}"
            ranks = fetch(url)
            if not ranks:
                break
            for r in ranks[0].get("ranks", []):
                traders.append(
                    {
                        "code": r.get("uniqueCode"),
                        "nick": r.get("nickName"),
                        "pnl": r.get("pnl"),
                        "winRatio": r.get("winRatio"),
                        "insts": r.get("traderInsts", []),
                    }
                )
            time.sleep(0.2)

    print(f"Total candidate traders to check: {len(traders)}")
    asset_to_traders = {a: [] for a in target_assets}

    for idx, t in enumerate(traders):
        code = t.get("code")
        nick = t.get("nick")
        url = f"https://www.okx.com/api/v5/copytrading/public-subpositions-history?uniqueCode={code}&instType=SWAP&limit=50"
        hist = fetch(url)
        time.sleep(0.25)
        if not hist:
            continue

        counts = {}
        for h in hist:
            inst = h.get("instId", "")
            if "-" in inst:
                sym = inst.split("-")[0].upper()
                counts[sym] = counts.get(sym, 0) + 1

        if not counts:
            continue

        primary = max(counts, key=counts.get)
        for sym, c in counts.items():
            if sym in asset_to_traders:
                asset_to_traders[sym].append(
                    {
                        "code": code,
                        "nick": nick,
                        "sym_trades": c,
                        "total_trades": len(hist),
                        "primary": primary,
                        "pnl": t.get("pnl"),
                        "win": t.get("winRatio"),
                    }
                )

        # Check progress
        filled = sum(1 for a in target_assets if len(asset_to_traders[a]) > 0)
        if idx % 10 == 0 or filled == len(target_assets):
            print(
                f"Checked {idx + 1}/{len(traders)} traders... Filled {filled}/{len(target_assets)} assets."
            )
        if filled == len(target_assets) and idx >= 40:
            break

    # Save results
    output_path = Path("Agent/data/market/asset_traders_mapping.json")
    with open(output_path, "w") as f:
        json.dump(asset_to_traders, f, indent=2)

    print("\n=== COVERAGE SUMMARY ===")
    for a in target_assets:
        candidates = asset_to_traders[a]
        if candidates:
            # Sort by sym_trades descending
            candidates.sort(key=lambda x: x["sym_trades"], reverse=True)
            best = candidates[0]
            print(
                f"[{a:7s}] -> Best: {best['nick'][:20]:20s} ({best['code']}) | Trades: {best['sym_trades']}/{best['total_trades']} | PnL: {str(best['pnl'])[:8]}"
            )
        else:
            print(f"[{a:7s}] -> MISSING")


if __name__ == "__main__":
    main()
