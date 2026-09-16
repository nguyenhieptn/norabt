"""Meta Router - Cung cấp dữ liệu tĩnh/môi trường cho Frontend (V2)."""
import os
from typing import Any, Dict, List

from fastapi import APIRouter
from backend.db.local_pkl import list_symbols as list_local_symbols
from backend.db.mongo import list_symbols as list_mongo_symbols

router = APIRouter(prefix="/api/v2", tags=["Meta Data"])


def _local_symbols() -> List[str]:
    symbols = set(list_local_symbols(frame="1m"))
    symbols.update(list_local_symbols(frame="4h"))
    return sorted(symbols)


@router.get("/symbols")
def get_symbols() -> List[str]:
    source = os.environ.get("NORA_DATA_SOURCE", "auto").strip().lower()
    if source == "local":
        return _local_symbols()
    if source == "mongo":
        return list_mongo_symbols(frame="1m")

    symbols = set(_local_symbols())
    try:
        symbols.update(list_mongo_symbols(frame="1m"))
    except Exception:
        pass
    return sorted(symbols)

@router.get("/strategies")
def get_strategies() -> List[Dict[str, Any]]:
    """Trả về danh sách các chiến lược đang được Engine 2.0 hỗ trợ."""
    return [
        {
            "id": "keltner",
            "name": "Keltner Channel Strategy",
            "description": "Chiến lược cắt kênh Keltner (Bản cải tiến Nora 2.0)",
            "params_schema": {
                "length": {"type": "integer", "default": 17, "min": 5, "max": 100},
                "multiplier": {"type": "float", "default": 0.5, "min": 0.1, "max": 5.0}
            }
        }
    ]
