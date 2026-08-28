"""Build selected GeckoTerminal DEX OHLCV datasets as pickle files."""
import argparse
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests

DEFAULT_BASE_URL = "https://api.geckoterminal.com/api/v2"
DEFAULT_OUTPUT_DIR = "data"
DEFAULT_LIMIT = 500
DEFAULT_PAGE_DELAY_SEC = 12.0
DEFAULT_RETRIES = 5
DEFAULT_RETRY_DELAY_SEC = 60.0
DEFAULT_ASSET_DELAY_SEC = 60.0
DEFAULT_MAX_PAGES = 30
DEFAULT_LOOKBACK_DAYS = 120.0
DEFAULT_CORE_ASSETS = "BTC,ETH,SOL"
DEFAULT_TRENDING_COUNT = 3
DEFAULT_NEW_COUNT = 2
DEFAULT_TRENDING_NETWORKS = "solana,eth"
DEFAULT_CURRENCY = "usd"
DEFAULT_TOKEN = "base"

CORE_POOLS = {
    "BTC": {
        "network": "eth",
        "pool_address": "0x4585fe77225b41b697c938b018e2ac67ac5a20c0",
        "name": "WBTC / WETH 0.05%",
    },
    "ETH": {
        "network": "eth",
        "pool_address": "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640",
        "name": "WETH / USDC 0.05%",
    },
    "SOL": {
        "network": "solana",
        "pool_address": "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE",
        "name": "SOL / USDC",
    },
}

PKL_COLUMNS = ["open_time", "open", "high", "low", "close", "volume"]


class RateLimitError(RuntimeError):
    pass


def log(message: str) -> None:
    print(message, flush=True)


def warn(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _to_seconds(value: Any) -> int:
    if value is None:
        raise ValueError("timestamp is required")
    if isinstance(value, (int, float)):
        num = int(value)
        if num >= 10**12:
            return num // 1000
        return num
    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            return _to_seconds(int(s))
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    raise TypeError(f"Unsupported timestamp type: {type(value)!r}")


def _asset_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_]+", "", value).strip("_")
    return (slug or "POOL").upper()[:32]


def _clean_symbol(value: str) -> str:
    symbol = re.sub(r"[^A-Za-z0-9]+", "", value).upper()
    wrapped = {"WBTC": "BTC", "WETH": "ETH", "WSOL": "SOL", "WBNB": "BNB", "WMATIC": "MATIC"}
    return wrapped.get(symbol, symbol)[:16]


def _api_get(
    base_url: str,
    path: str,
    params: Dict[str, Any],
    timeout: int,
    retries: int,
    retry_delay_sec: float,
) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    clean_params = {k: v for k, v in params.items() if v is not None}
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, params=clean_params, headers={"accept": "application/json"}, timeout=timeout)
        except requests.RequestException as exc:
            if attempt >= retries:
                raise
            wait_sec = retry_delay_sec * (attempt + 1)
            warn(f"[warn] Request failed ({exc}); sleeping {wait_sec:.1f}s before retry {attempt + 1}/{retries}.")
            time.sleep(wait_sec)
            continue

        if response.status_code != 429:
            response.raise_for_status()
            return response.json()
        if attempt >= retries:
            raise RateLimitError(f"429 Too Many Requests for {path}")

        retry_after = response.headers.get("Retry-After")
        wait_sec = retry_delay_sec * (attempt + 1)
        if retry_after and retry_after.isdigit():
            wait_sec = max(wait_sec, float(retry_after))
        warn(f"[warn] Rate limited; sleeping {wait_sec:.1f}s before retry {attempt + 1}/{retries}.")
        time.sleep(wait_sec)
    raise RuntimeError("unreachable retry state")


def _extract_rows(payload: Dict[str, Any]) -> List[List[Any]]:
    data = payload.get("data") or {}
    attributes = data.get("attributes") or {}
    rows = attributes.get("ohlcv_list") or []
    normalized = []
    for row in rows:
        if isinstance(row, (list, tuple)) and len(row) >= 6:
            normalized.append(list(row[:6]))
    return normalized


def _normalize_rows(raw_rows: Iterable[List[Any]], start_sec: int, end_sec: int) -> pd.DataFrame:
    records: Dict[int, Dict[str, Any]] = {}
    for row in raw_rows:
        timestamp_sec = int(row[0])
        if timestamp_sec < start_sec or timestamp_sec > end_sec:
            continue
        open_time = timestamp_sec * 1000
        if open_time in records:
            continue
        records[open_time] = {
            "open_time": open_time,
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5]),
        }
    frame = pd.DataFrame(records.values(), columns=PKL_COLUMNS)
    if frame.empty:
        return frame
    frame = frame.sort_values("open_time").reset_index(drop=True)
    return frame


def _crawl_ohlcv(
    base_url: str,
    network: str,
    pool_address: str,
    timeframe: str,
    aggregate: int,
    start_sec: int,
    end_sec: int,
    limit: int,
    page_delay_sec: float,
    retries: int,
    retry_delay_sec: float,
    timeout: int,
    max_pages: Optional[int],
    currency: str,
    token: str,
) -> Tuple[pd.DataFrame, int]:
    path = f"/networks/{network}/pools/{pool_address}/ohlcv/{timeframe}"
    before_timestamp = end_sec
    page = 0
    raw_rows: List[List[Any]] = []

    while True:
        page += 1
        if max_pages and page > max_pages:
            warn(f"[warn] Reached max_pages={max_pages} for {network}:{pool_address} {aggregate}h; stopping early.")
            break

        payload = _api_get(
            base_url,
            path,
            {
                "aggregate": aggregate,
                "before_timestamp": before_timestamp,
                "limit": limit,
                "currency": currency,
                "token": token,
                "include_empty_intervals": "false",
            },
            timeout,
            retries,
            retry_delay_sec,
        )
        rows = _extract_rows(payload)
        if not rows:
            break

        raw_rows.extend(rows)
        oldest_sec = min(int(row[0]) for row in rows)
        if oldest_sec <= start_sec:
            break
        if len(rows) < limit:
            break

        next_before_timestamp = oldest_sec - 1
        if next_before_timestamp >= before_timestamp:
            break
        before_timestamp = next_before_timestamp
        if page_delay_sec:
            time.sleep(page_delay_sec)

    return _normalize_rows(raw_rows, start_sec, end_sec), page


def _included_symbol_map(payload: Dict[str, Any]) -> Dict[str, str]:
    symbols = {}
    for item in payload.get("included") or []:
        if item.get("type") != "token":
            continue
        attributes = item.get("attributes") or {}
        symbol = attributes.get("symbol")
        if symbol:
            symbols[str(item.get("id"))] = str(symbol)
    return symbols


def _pool_symbol(pool: Dict[str, Any], included_symbols: Dict[str, str]) -> str:
    relationships = pool.get("relationships") or {}
    base_token = relationships.get("base_token") or {}
    token_data = base_token.get("data") or {}
    token_id = str(token_data.get("id") or "")
    if token_id in included_symbols:
        return _clean_symbol(included_symbols[token_id])
    if "_" in token_id:
        return _clean_symbol(token_id.rsplit("_", 1)[-1])

    attributes = pool.get("attributes") or {}
    name = str(attributes.get("name") or attributes.get("pool_created_at") or "")
    first = re.split(r"/|\s", name.strip(), maxsplit=1)[0]
    return _clean_symbol(str(first or pool.get("id") or "POOL"))


def _pool_address(pool: Dict[str, Any]) -> str:
    pool_id = str(pool.get("id") or "")
    if "_" in pool_id:
        return pool_id.rsplit("_", 1)[-1]
    attributes = pool.get("attributes") or {}
    return str(attributes.get("address") or pool_id)


def _discover_pools(
    base_url: str,
    networks: List[str],
    path_name: str,
    count: int,
    timeout: int,
    retries: int,
    retry_delay_sec: float,
    existing_assets: set,
) -> List[Dict[str, str]]:
    if count <= 0:
        return []

    targets: List[Dict[str, str]] = []
    for network in networks:
        payload = _api_get(
            base_url,
            f"/networks/{network}/{path_name}",
            {"include": "base_token,quote_token,dex"},
            timeout,
            retries,
            retry_delay_sec,
        )
        included_symbols = _included_symbol_map(payload)
        for pool in payload.get("data") or []:
            asset = _pool_symbol(pool, included_symbols)
            if not asset or asset in existing_assets:
                continue
            pool_address = _pool_address(pool)
            attributes = pool.get("attributes") or {}
            if not pool_address:
                continue
            existing_assets.add(asset)
            targets.append(
                {
                    "asset": asset,
                    "network": network,
                    "pool_address": pool_address,
                    "name": str(attributes.get("name") or asset),
                }
            )
            if len(targets) >= count:
                return targets
    return targets


def _parse_list(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_hours(value: str) -> List[int]:
    hours = set()
    for part in value.split(","):
        part = part.strip().lower().removesuffix("h")
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            hours.update(range(int(start), int(end) + 1))
        else:
            hours.add(int(part))
    invalid = [hour for hour in hours if hour < 1 or hour > 24]
    if invalid:
        raise ValueError("--hours values must be between 1 and 24")
    if not hours:
        raise ValueError("--hours must not be empty")
    return sorted(hours)


def _aggregate_frame(frame: pd.DataFrame, hours: int) -> pd.DataFrame:
    if frame.empty:
        return frame.loc[:, PKL_COLUMNS].copy()
    interval_ms = hours * 60 * 60 * 1000
    ordered = frame.loc[:, PKL_COLUMNS].sort_values("open_time").reset_index(drop=True)
    buckets = (ordered["open_time"] // interval_ms) * interval_ms
    grouped = (
        ordered.assign(_bucket=buckets)
        .groupby("_bucket", as_index=False, sort=True)
        .agg(
            open_time=("_bucket", "first"),
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            volume=("volume", "sum"),
        )
    )
    return grouped.loc[:, PKL_COLUMNS]


def _write_pickle(path: str, frame: pd.DataFrame) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    frame.to_pickle(path)


def _clear_asset_dirs(output_dir: str, assets: Iterable[str]) -> None:
    for asset in assets:
        path = os.path.join(output_dir, _asset_slug(asset))
        if os.path.isdir(path):
            shutil.rmtree(path)
            log(f"[clear] Removed old {path}")


def _target_set(args: argparse.Namespace, base_url: str, timeout: int, retries: int, retry_delay_sec: float) -> List[Dict[str, str]]:
    assets = [_asset_slug(asset) for asset in _parse_list(args.core_assets)]
    targets = []
    seen_assets = set()
    for asset in assets:
        pool = CORE_POOLS.get(asset)
        if not pool:
            warn(f"[warn] No built-in core pool for {asset}; skipping.")
            continue
        seen_assets.add(asset)
        targets.append({"asset": asset, **pool})

    networks = _parse_list(args.trending_networks)
    trending = _discover_pools(
        base_url,
        networks,
        "trending_pools",
        args.trending_count,
        timeout,
        retries,
        retry_delay_sec,
        seen_assets,
    )
    new = _discover_pools(
        base_url,
        networks,
        "new_pools",
        args.new_count,
        timeout,
        retries,
        retry_delay_sec,
        seen_assets,
    )
    return targets + trending + new


def run(args: argparse.Namespace) -> List[Dict[str, Any]]:
    base_url = os.environ.get("GECKOTERMINAL_BASE_URL", DEFAULT_BASE_URL)
    output_dir = os.environ.get("GECKOTERMINAL_FULL_OUTPUT_DIR", args.output_dir)
    timeout = int(os.environ.get("GECKOTERMINAL_TIMEOUT", "30"))
    limit = args.limit or int(os.environ.get("GECKOTERMINAL_FULL_LIMIT", str(DEFAULT_LIMIT)))
    page_delay_sec = args.page_delay_sec
    if page_delay_sec is None:
        page_delay_sec = float(os.environ.get("GECKOTERMINAL_FULL_PAGE_DELAY_SEC", str(DEFAULT_PAGE_DELAY_SEC)))
    retries = args.retries if args.retries is not None else int(os.environ.get("GECKOTERMINAL_RETRIES", str(DEFAULT_RETRIES)))
    retry_delay_sec = args.retry_delay_sec
    if retry_delay_sec is None:
        retry_delay_sec = float(os.environ.get("GECKOTERMINAL_RETRY_DELAY_SEC", str(DEFAULT_RETRY_DELAY_SEC)))
    asset_delay_sec = args.asset_delay_sec
    if asset_delay_sec is None:
        asset_delay_sec = float(os.environ.get("GECKOTERMINAL_FULL_ASSET_DELAY_SEC", str(DEFAULT_ASSET_DELAY_SEC)))
    max_pages = args.max_pages
    if max_pages is None:
        max_pages_env = os.environ.get("GECKOTERMINAL_FULL_MAX_PAGES")
        max_pages = int(max_pages_env) if max_pages_env else DEFAULT_MAX_PAGES

    if limit < 1 or limit > 1000:
        raise ValueError("--limit must be between 1 and 1000")
    if page_delay_sec < 0:
        raise ValueError("--page-delay-sec must be non-negative")
    if retries < 0:
        raise ValueError("--retries must be non-negative")
    if retry_delay_sec < 0:
        raise ValueError("--retry-delay-sec must be non-negative")
    if asset_delay_sec < 0:
        raise ValueError("--asset-delay-sec must be non-negative")
    if args.currency not in {"usd", "token"}:
        raise ValueError("--currency must be usd or token")
    if args.token not in {"base", "quote"} and not re.fullmatch(r"[A-Za-z0-9:_\-]+", args.token):
        raise ValueError("--token must be base, quote, or a token address")

    if args.end_ts:
        end_sec = _to_seconds(args.end_ts)
    else:
        end_sec = int(time.time())
    if args.start_ts:
        start_sec = _to_seconds(args.start_ts)
    else:
        start_sec = end_sec - int(args.lookback_days * 86400)
    if start_sec >= end_sec:
        raise ValueError("start timestamp must be smaller than end timestamp")

    hours = _parse_hours(args.hours)
    if 1 not in hours:
        hours = [1] + hours
    targets = _target_set(args, base_url, timeout, retries, retry_delay_sec)
    if args.clear:
        _clear_asset_dirs(output_dir, [target["asset"] for target in targets])

    log(f"[start] {len(targets)} assets, files={hours[0]}h..{hours[-1]}h, output={output_dir}")
    log(f"[range] {datetime.fromtimestamp(start_sec, timezone.utc).isoformat()} -> {datetime.fromtimestamp(end_sec, timezone.utc).isoformat()}")

    summaries = []
    total_steps = len(targets) * len(hours)
    step = 0
    for target_index, target in enumerate(targets):
        if target_index > 0 and asset_delay_sec:
            log(f"[wait] Sleeping {asset_delay_sec:.1f}s before next asset")
            time.sleep(asset_delay_sec)

        asset = _asset_slug(target["asset"])
        network = target["network"]
        pool_address = target["pool_address"]
        log(f"[asset] {asset} | {network} | {target.get('name', '')} | pool={pool_address}")

        step += 1
        log(f"[crawl] ({step}/{total_steps}) {asset} 1h source")
        try:
            frame_1h, pages = _crawl_ohlcv(
                base_url,
                network,
                pool_address,
                "hour",
                1,
                start_sec,
                end_sec,
                limit,
                page_delay_sec,
                retries,
                retry_delay_sec,
                timeout,
                max_pages,
                args.currency,
                args.token,
            )
        except Exception as exc:
            warn(f"[error] {asset} 1h failed: {exc}")
            summaries.append(
                {
                    "asset": asset,
                    "network": network,
                    "pool_address": pool_address,
                    "name": target.get("name", ""),
                    "rows_by_hour": {},
                }
            )
            continue

        rows_by_hour: Dict[int, int] = {}
        one_hour_path = os.path.join(output_dir, asset, "1h.pkl")
        _write_pickle(one_hour_path, frame_1h)
        rows_by_hour[1] = len(frame_1h)
        log(f"[write] {asset} 1h rows={len(frame_1h)} pages={pages} path={one_hour_path}")

        for hour in hours:
            if hour == 1:
                continue
            step += 1
            log(f"[build] ({step}/{total_steps}) {asset} {hour}h from 1h")
            frame = _aggregate_frame(frame_1h, hour)
            path = os.path.join(output_dir, asset, f"{hour}h.pkl")
            _write_pickle(path, frame)
            rows_by_hour[hour] = len(frame)
            log(f"[write] {asset} {hour}h rows={len(frame)} path={path}")

        summaries.append(
            {
                "asset": asset,
                "network": network,
                "pool_address": pool_address,
                "name": target.get("name", ""),
                "rows_by_hour": rows_by_hour,
            }
        )

    log("[summary]")
    for item in summaries:
        nonzero = sum(1 for rows in item["rows_by_hour"].values() if rows > 0)
        total_rows = sum(item["rows_by_hour"].values())
        log(f"[summary] {item['asset']} files={nonzero}/{len(hours)} total_rows={total_rows} pool={item['pool_address']}")
    log("[done] Full GeckoTerminal PKL dataset build finished.")
    return summaries


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl selected GeckoTerminal DEX OHLCV assets to PKL files.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output root, default data.")
    parser.add_argument("--core-assets", default=DEFAULT_CORE_ASSETS, help="Comma-separated core assets to crawl: BTC,ETH,SOL.")
    parser.add_argument("--trending-networks", default=DEFAULT_TRENDING_NETWORKS, help="Comma-separated networks for trending/new pools.")
    parser.add_argument("--trending-count", type=int, default=DEFAULT_TRENDING_COUNT, help="How many trending pools to add.")
    parser.add_argument("--new-count", type=int, default=DEFAULT_NEW_COUNT, help="How many new pools to add.")
    parser.add_argument("--hours", default="1-24", help="Hourly pickle files to build, e.g. 1-24 or 1,4,12,24.")
    parser.add_argument("--start-ts", default=None, help="Start timestamp (s, ms, or ISO8601).")
    parser.add_argument("--end-ts", default=None, help="End timestamp (s, ms, or ISO8601). Defaults to now.")
    parser.add_argument("--lookback-days", type=float, default=DEFAULT_LOOKBACK_DAYS, help="Alternative to --start-ts.")
    parser.add_argument("--limit", type=int, default=None, help=f"Rows per page, default {DEFAULT_LIMIT}.")
    parser.add_argument("--page-delay-sec", type=float, default=None, help=f"Seconds between requests, default {DEFAULT_PAGE_DELAY_SEC}.")
    parser.add_argument("--retries", type=int, default=None, help=f"Retries for rate limits, default {DEFAULT_RETRIES}.")
    parser.add_argument("--retry-delay-sec", type=float, default=None, help=f"Base retry delay, default {DEFAULT_RETRY_DELAY_SEC}.")
    parser.add_argument("--asset-delay-sec", type=float, default=None, help=f"Seconds between assets, default {DEFAULT_ASSET_DELAY_SEC}.")
    parser.add_argument("--max-pages", type=int, default=None, help=f"Safety cap per file, default {DEFAULT_MAX_PAGES}.")
    parser.add_argument("--currency", default=DEFAULT_CURRENCY, help="Pricing currency: usd or token.")
    parser.add_argument("--token", default=DEFAULT_TOKEN, help="base, quote, or token address.")
    parser.add_argument("--clear", action="store_true", help="Remove old selected asset directories before writing.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    try:
        run(parse_args(argv))
    except Exception as exc:
        warn(f"[fatal] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
