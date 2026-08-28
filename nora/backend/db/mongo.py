"""MongoDB Data Access Layer for Market Candles & Indicators.

Hỗ trợ:
- Kết nối MongoDB Connection Pool
- Nạp nến nhanh theo khung thời gian (1m, 1h, 4h, ...)
- Lọc theo dải thời gian (start_ts, end_ts)
- Projection: Chỉ lấy các cột chỉ báo cần thiết để tiết kiệm RAM & Network
- Chuyển đổi trực tiếp sang Pandas DataFrame để phân tích
"""
import os
from typing import Any, Dict, List, Optional, Union

import pandas as pd
import pymongo
from pymongo.collection import Collection
from pymongo.database import Database

# Cấu hình mặc định MongoDB
MONGO_HOST = os.getenv("NORA_MONGO_HOST", "127.0.0.1")
MONGO_PORT = int(os.getenv("NORA_MONGO_PORT", "27117"))
MONGO_USER = os.getenv("NORA_MONGO_USER", "")
MONGO_PASS = os.getenv("NORA_MONGO_PASS", "")

_CLIENT_INSTANCE: Optional[pymongo.MongoClient] = None


def get_mongo_client(
    host: Optional[str] = None,
    port: Optional[int] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    auth_db: Optional[str] = None,
) -> pymongo.MongoClient:
    """Trả về Singleton MongoClient với connection pool."""
    global _CLIENT_INSTANCE
    target_host = host or MONGO_HOST
    target_port = port or MONGO_PORT
    target_user = username or MONGO_USER
    target_pass = password or MONGO_PASS

    if host or port or username or password:
        # Custom client
        return pymongo.MongoClient(
            host=target_host,
            port=target_port,
            username=target_user or None,
            password=target_pass or None,
            authSource=auth_db or "admin",
            maxPoolSize=50,
            serverSelectionTimeoutMS=5000,
        )

    if _CLIENT_INSTANCE is None:
        _CLIENT_INSTANCE = pymongo.MongoClient(
            host=target_host,
            port=target_port,
            username=target_user or None,
            password=target_pass or None,
            maxPoolSize=50,
            serverSelectionTimeoutMS=5000,
        )
    return _CLIENT_INSTANCE


def get_db(db_name: str = "backtest_data_1m_strategy810") -> Database:
    """Lấy database object."""
    client = get_mongo_client()
    return client[db_name]


def get_collection(collection_name: str, db_name: str = "backtest_data_1m_strategy810") -> Collection:
    """Lấy collection object (ví dụ: candle_1m, candle_4h)."""
    return get_db(db_name)[collection_name]


def list_databases() -> List[str]:
    """Danh sách database nến có sẵn trên MongoDB."""
    client = get_mongo_client()
    try:
        return client.list_database_names()
    except Exception:
        return []


def list_symbols(frame: str = "4h", db_name: str = "backtest_data_1m_strategy810") -> List[str]:
    """Lấy danh sách các cặp coin có sẵn trong collection."""
    col = get_collection(f"candle_{frame}", db_name=db_name)
    return col.distinct("symbol")


def fetch_candles_df(
    symbol: str,
    frame: str = "4h",
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    columns: Optional[List[str]] = None,
    db_name: str = "backtest_data_1m_strategy810",
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """Nạp dữ liệu nến và chỉ báo thành DataFrame."""
    col = get_collection(f"candle_{frame}", db_name=db_name)

    query = {}
    if symbol:
        query["symbol"] = symbol
    if start_ts is not None or end_ts is not None:
        query["timestamp"] = {}
        if start_ts is not None:
            # timestamp is close_time in seconds, so we divide by 1000
            query["timestamp"]["$gte"] = start_ts // 1000
        if end_ts is not None:
            query["timestamp"]["$lte"] = (end_ts // 1000) + 60

    projection: Optional[Dict[str, int]] = None
    if columns:
        # Đảm bảo luôn có các cột cơ sở
        essential = {"_id": 0, "symbol": 1, "open_time": 1, "close_time": 1, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}
        for c in columns:
            essential[c] = 1
        projection = essential
    else:
        projection = {"_id": 0}

    cursor = col.find(query, projection=projection).sort("open_time", pymongo.ASCENDING)
    if limit:
        cursor = cursor.limit(limit)

    records = list(cursor)
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame.from_records(records)
    if "open_time" in df.columns:
        df["open_time"] = pd.to_numeric(df["open_time"], errors="coerce")
    return df
