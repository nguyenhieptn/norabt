"""Meta Router - Cung cấp dữ liệu tĩnh/môi trường cho Frontend (V2)."""
from typing import List, Dict, Any
from fastapi import APIRouter
from backend.db.mongo import list_symbols

router = APIRouter(prefix="/api/v2", tags=["Meta Data"])

@router.get("/symbols")
def get_symbols() -> List[str]:
    """Lấy danh sách các Symbol (cặp giao dịch) hiện có trong CSDL mới (MongoDB)."""
    # Trả về các symbols có trong collection 1m
    return list_symbols(frame="1m")

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
