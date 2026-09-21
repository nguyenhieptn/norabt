"""Fetch on-chain token security evidence for the DEX assets.

Why this exists: Logic 1 grades a `token_security` source for every DEX asset, and
without a file it stays MISSING forever -- no amount of price crawling fixes it.
GoPlus publishes the contract-level facts (honeypot, taxes, mint authority, holder
concentration, LP locks) for free, keyed by the token address we already store in
pool_liquidity.json.

No composite score is written. The earlier version of this dataset carried an
invented `security_score: 98`; the flags below are the evidence, and anything the
provider does not answer stays null rather than becoming a reassuring number.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
GOPLUS = "https://api.gopluslabs.io/api/v1"
REQUEST_DELAY_SECONDS = 1.0

DEX_ASSETS = ["WBTC", "WETH", "SOL", "UNI", "PEPE"]
EVM_CHAIN_IDS = {"ETHEREUM": "1", "BSC": "56", "BASE": "8453", "ARBITRUM": "42161"}


def fetch(url: str, timeout: int = 25) -> Dict[str, Any]:
    result = subprocess.run(
        ["curl", "-4", "-s", "-m", str(timeout), "-H", "User-Agent: Mozilla/5.0", url],
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"code": 0, "message": "unparseable response"}


def as_bool(raw: Any) -> Optional[bool]:
    """GoPlus answers "1"/"0"; anything else means the provider did not answer."""
    if raw in ("1", 1, True):
        return True
    if raw in ("0", 0, False):
        return False
    return None


def as_float(raw: Any) -> Optional[float]:
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def top10_pct(holders: Any) -> Optional[float]:
    if not isinstance(holders, list) or not holders:
        return None
    rows = [h for h in holders[:10] if isinstance(h, dict)]
    shares = [as_float(h.get("percent")) for h in rows]
    shares = [s for s in shares if s is not None]
    if not shares:
        return None
    total = sum(shares)
    if total == 0.0 and any((as_float(h.get("balance")) or 0.0) > 0.0 for h in rows):
        # Wrapped SOL reports total_supply 0, so GoPlus prints percent "0" for every
        # holder. Zero here means "could not compute", not "no concentration".
        return None
    return min(100.0, total * 100.0)


def lp_locked(lp_holders: Any) -> Optional[bool]:
    if not isinstance(lp_holders, list) or not lp_holders:
        return None
    return any(
        str(h.get("is_locked")) == "1" for h in lp_holders if isinstance(h, dict)
    )


def parse_evm(record: Dict[str, Any]) -> Dict[str, Any]:
    buy_tax, sell_tax = (
        as_float(record.get("buy_tax")),
        as_float(record.get("sell_tax")),
    )
    return {
        "is_honeypot": as_bool(record.get("is_honeypot")),
        # GoPlus reports taxes as a fraction; the schema wants percent.
        "buy_tax": buy_tax * 100.0 if buy_tax is not None else None,
        "sell_tax": sell_tax * 100.0 if sell_tax is not None else None,
        "is_mintable": as_bool(record.get("is_mintable")),
        "is_blacklisted": as_bool(record.get("is_blacklisted")),
        "top10_holder_pct": top10_pct(record.get("holders")),
        "liquidity_locked": lp_locked(record.get("lp_holders")),
        "holder_count": as_float(record.get("holder_count")),
        "security_score": None,
    }


def parse_solana(record: Dict[str, Any]) -> Dict[str, Any]:
    mintable = record.get("mintable")
    metadata = record.get("metadata_mutable")
    return {
        # Solana has no honeypot/tax equivalent in this feed; leave them unanswered.
        "is_honeypot": None,
        "buy_tax": None,
        "sell_tax": None,
        "is_mintable": as_bool((mintable or {}).get("status")),
        "is_blacklisted": as_bool((record.get("freezable") or {}).get("status")),
        "top10_holder_pct": top10_pct(record.get("holders")),
        "liquidity_locked": None,
        "metadata_mutable": as_bool((metadata or {}).get("status")),
        "security_score": None,
    }


def crawl_asset(asset: str) -> str:
    market_dir = DATA_DIR / "dex" / asset / "market"
    pool_path = market_dir / "pool_liquidity.json"
    if not pool_path.exists():
        return "THẤT BẠI: không có pool_liquidity.json"
    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    chain = str(pool.get("chain", "")).upper()
    address = (pool.get("base_token") or {}).get("address")
    if not address:
        return "THẤT BẠI: pool_liquidity không có địa chỉ token"

    if chain == "SOLANA":
        payload = fetch(f"{GOPLUS}/solana/token_security?contract_addresses={address}")
        parse, key = parse_solana, address
    elif chain in EVM_CHAIN_IDS:
        chain_id = EVM_CHAIN_IDS[chain]
        payload = fetch(
            f"{GOPLUS}/token_security/{chain_id}?contract_addresses={address}"
        )
        parse, key = parse_evm, address.lower()
    else:
        return f"THẤT BẠI: chuỗi {chain} chưa hỗ trợ"

    if payload.get("code") != 1:
        return (
            f"THẤT BẠI: GoPlus trả code={payload.get('code')} {payload.get('message')}"
        )
    record = (payload.get("result") or {}).get(key)
    if not record:
        return "THẤT BẠI: GoPlus không có dữ liệu cho địa chỉ này"

    observed = int(time.time() * 1000)
    out = {
        "asset": asset,
        "chain": chain,
        "token_address": address,
        "source": "GOPLUS_TOKEN_SECURITY_API",
        "observed_at": observed,
        "updated_at": observed,
        "security": parse(record),
    }
    (market_dir / "token_security.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    flags = out["security"]
    answered = sum(1 for v in flags.values() if v is not None)
    return f"{answered}/{len(flags)} chỉ báo có câu trả lời, top10={flags['top10_holder_pct']}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", nargs="*", default=DEX_ASSETS)
    args = parser.parse_args()

    failures: List[str] = []
    for i, asset in enumerate(args.assets, 1):
        print(f"[{i}/{len(args.assets)}] DEX/{asset}")
        outcome = crawl_asset(asset)
        print(f"      {outcome}")
        if outcome.startswith("THẤT BẠI"):
            failures.append(f"DEX/{asset}: {outcome}")
        time.sleep(REQUEST_DELAY_SECONDS)

    print()
    print(
        f"Thất bại {len(failures)} asset:"
        if failures
        else "Tất cả đều có dữ liệu thật."
    )
    for f in failures:
        print(f"  · {f}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
