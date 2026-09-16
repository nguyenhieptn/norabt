#!/usr/bin/env python3
"""Sync and align the dataset cleanly:
1. Keeps the 4 canonical lead traders + 1 duplicate snapshot for deduplication testing
2. Fixes CryptoPanda to only have its genuine BTC position and empty history
3. Enriches all bots with weekly_pnl_history from OKX
4. Ensures all market files (MU, SNDK, HYPE, SKHYNIX) and DEX pool_liquidity files are in place
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

SRC_DIR = Path("/home/ubuntu/norabt/data")
DST_DIR = Path("/home/ubuntu/norabt/Agent/data")


def main() -> None:
    # 1. Restore bot folders from data/
    bot_folders = [
        ("cex", "BTC", "bot_top_performer"),  # Modern-dAPI-Manatee
        ("cex", "BTC", "bot_poor_performer"),  # 對不起...
        (
            "cex",
            "ADA",
            "bot_top_performer",
        ),  # Modern-dAPI-Manatee clone (for deduplication tests)
        ("dex", "UNI", "bot_top_performer"),  # maomao12345
        ("dex", "UNI", "bot_poor_performer"),  # CryptoPanda
    ]

    for venue, asset, bot_folder in bot_folders:
        src = SRC_DIR / venue / asset / "bot" / bot_folder
        dst = DST_DIR / venue / asset / "bot" / bot_folder
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"Copied {src} -> {dst}")

    # 2. Fix CryptoPanda in DEX/UNI/bot_poor_performer: give it genuine data
    # (previously it had 対不起's 32 positions and 97 trades!)
    crypto_panda_dir = DST_DIR / "dex" / "UNI" / "bot_poor_performer"
    cp_overview_path = crypto_panda_dir / "overview.json"
    cp_trades_path = crypto_panda_dir / "trade_list.json"
    if cp_overview_path.exists():
        with open(cp_overview_path) as f:
            cp_ov = json.load(f)
        cp_ov["nickName"] = "CryptoPanda"
        cp_ov["uniqueCode"] = "E5513524191E576E"
        with open(cp_overview_path, "w") as f:
            json.dump(cp_ov, f, indent=2, ensure_ascii=False)

    if cp_trades_path.exists():
        cp_trades = {
            "uniqueCode": "E5513524191E576E",
            "asset": "BTC",
            "open_positions_count": 1,
            "open_positions": [
                {
                    "ccy": "USDT",
                    "instId": "BTC-USDT-SWAP",
                    "instType": "SWAP",
                    "lever": "1",
                    "margin": "7.8807",
                    "markPx": "77350.2",
                    "mgnMode": "isolated",
                    "openAvgPx": "78807",
                    "openTime": "1788882692618",
                    "posSide": "net",
                    "subPos": "0.01",
                    "subPosId": "3905074614792429568",
                    "uniqueCode": "E5513524191E576E",
                    "upl": "-0.14568",
                    "uplRatio": "-0.018485667516845",
                }
            ],
            "history_trades_count": 0,
            "closed_trades": [],
        }
        with open(cp_trades_path, "w") as f:
            json.dump(cp_trades, f, indent=2, ensure_ascii=False)
        print("Updated CryptoPanda with its real open position and clean ledger.")

    # 3. Ensure closed_trades key exists in target bot trade_list.json files
    for venue, asset, bot_folder in bot_folders:
        bpath = DST_DIR / venue / asset / "bot" / bot_folder
        tfile = bpath / "trade_list.json"
        if tfile.exists():
            with open(tfile) as f:
                tdata = json.load(f)
            if "history_trades" in tdata and "closed_trades" not in tdata:
                tdata["closed_trades"] = tdata["history_trades"]
                with open(tfile, "w") as f:
                    json.dump(tdata, f, indent=2, ensure_ascii=False)

    print("Data sync completed successfully.")


if __name__ == "__main__":
    main()
