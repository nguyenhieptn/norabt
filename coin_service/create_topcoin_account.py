import argparse
import os
from datetime import datetime

import django
from pymongo import MongoClient

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crypto_lab.settings")
django.setup()

from django.conf import settings
from Console.Models.Coin_lab import LabAccount, LabCampaigns, LabStrategies

DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "NEARUSDT", "LTCUSDT", "ATOMUSDT", "FTMUSDT", "INJUSDT",
    "ARBUSDT", "OPUSDT", "SUIUSDT", "TIAUSDT", "SEIUSDT",
    "RENDERUSDT", "1000PEPEUSDT", "FETUSDT", "GALAUSDT", "APTUSDT",
]


def parse_date(value):
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(value, fmt).timestamp())
        except ValueError:
            pass
    raise ValueError(f"Unsupported date format: {value}")


def mongo_db(alias):
    cfg = settings.DATABASES[alias]
    client_cfg = dict(cfg["CLIENT"])
    return MongoClient(**client_cfg)[cfg["NAME"]]


def processed_symbols(alias):
    db = mongo_db(alias)
    collections = ["candle_1m", "candle_4h"]
    missing_colls = [coll for coll in collections if coll not in db.list_collection_names()]
    if missing_colls:
        return set(), missing_colls
    return set(db.candle_1m.distinct("symbol")) & set(db.candle_4h.distinct("symbol")), []


def main():
    parser = argparse.ArgumentParser(description="Create one lab account with campaigns for top-coin backtest.")
    parser.add_argument("--name", default=f"TOP25_BASELINE_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--balance", type=float, default=10000)
    parser.add_argument("--strategy-id", type=int, default=810)
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--stop", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--db", default="backtest_data_1m_custom_local")
    parser.add_argument("--data-length", type=int, default=1)
    parser.add_argument("--active-budget", type=float, default=100.0, help="Percent of campaign budget allowed to trade.")
    parser.add_argument("--server", default="localhost", help="Lab server name used by UI/scheduler.")
    parser.add_argument("--group", default="No group", help="Lab account group shown in UI.")
    parser.add_argument("--symbols", nargs="*", default=DEFAULT_SYMBOLS)
    parser.add_argument("--allow-missing", action="store_true", help="Create campaigns even if processed Mongo data is missing.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be created without writing MySQL.")
    args = parser.parse_args()

    symbols = [symbol.upper() for symbol in args.symbols]
    strategy = LabStrategies.objects.filter(lab_strategy_id=args.strategy_id).first()
    if strategy is None:
        raise SystemExit(f"Strategy {args.strategy_id} does not exist")

    available, missing_colls = processed_symbols(args.db)
    if missing_colls:
        print(f"Processed DB alias {args.db} is missing collections: {', '.join(missing_colls)}")
    ready = [symbol for symbol in symbols if symbol in available]
    missing = [symbol for symbol in symbols if symbol not in available]

    print(f"Strategy: {strategy.lab_strategy_id} - {strategy.lab_strategy_name}")
    print(f"Account: {args.name}")
    print(f"Period: {args.start} -> {args.stop}")
    print(f"DB alias: {args.db}")
    print(f"Server: {args.server}")
    print(f"Group: {args.group}")
    print(f"Active budget: {args.active_budget}%")
    print(f"Ready symbols ({len(ready)}): {', '.join(ready) if ready else '-'}")
    print(f"Missing processed symbols ({len(missing)}): {', '.join(missing) if missing else '-'}")

    if missing and not args.allow_missing:
        raise SystemExit("Refusing to create campaigns until processed data exists. Use --allow-missing to override.")
    if args.dry_run:
        print("Dry run only; no MySQL rows were created.")
        return

    if LabAccount.objects.filter(lab_account_name=args.name).exists():
        raise SystemExit(f"Account name already exists: {args.name}")

    start_ts = parse_date(args.start)
    stop_ts = parse_date(args.stop)
    create_symbols = symbols if args.allow_missing else ready

    account = LabAccount.objects.create(
        lab_account_name=args.name,
        lab_account_balance=args.balance,
        lab_account_margin_balance=args.balance,
        lab_account_margin_type="CROSS",
        lab_account_track_balance=1,
        lab_account_running=0,
        lab_account_sync=1,
        lab_account_leap=0,
        lab_account_db=args.db,
        lab_account_data_type="1m",
        lab_account_data_length=args.data_length,
        lab_account_server=args.server,
        lab_account_group=args.group,
    )

    for index, symbol in enumerate(create_symbols, start=1):
        LabCampaigns.objects.create(
            lab_campaign_name=f"{args.name}_{symbol}",
            lab_campaign_account=account.lab_account_id,
            lab_campaign_symbol=symbol,
            lab_campaign_start=start_ts,
            lab_campaign_stop=stop_ts,
            lab_campaign_strategy=args.strategy_id,
            lab_campaign_side="BOTH",
            lab_campaign_budget=args.balance,
            lab_campaign_active_budget=args.active_budget,
            lab_campaign_running=0,
            lab_campaign_priority=index,
        )

    print(f"Created account {account.lab_account_id} with {len(create_symbols)} campaigns.")
    print(f"Run: python run_backtest.py {account.lab_account_id}")


if __name__ == "__main__":
    main()
