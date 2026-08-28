"""Package Database (MySQL + MongoDB) cho Nora Backtest Backend."""

from .models import (
    AccountModel,
    CampaignModel,
    OptimizationModel,
    OrderModel,
    OrderType,
    PositionModel,
    PositionStatus,
    PositionType,
)
from .mongo import (
    fetch_candles_df,
    get_collection,
    get_db,
    get_mongo_client,
    list_databases,
    list_symbols,
)
from .mysql import (
    cursor,
    execute,
    execute_batch,
    fetch_all,
    fetch_one,
    get_connection,
    stream_rows,
    transaction,
)

__all__ = [
    # MySQL
    "get_connection",
    "cursor",
    "transaction",
    "fetch_all",
    "fetch_one",
    "execute",
    "execute_batch",
    "stream_rows",
    # MongoDB
    "get_mongo_client",
    "get_db",
    "get_collection",
    "fetch_candles_df",
    "list_symbols",
    "list_databases",
    # Models
    "AccountModel",
    "CampaignModel",
    "PositionModel",
    "OrderModel",
    "OptimizationModel",
    "PositionType",
    "OrderType",
    "PositionStatus",
]
