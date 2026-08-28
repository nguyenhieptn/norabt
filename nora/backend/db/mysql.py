"""MySQL Data Access Layer for Nora Backtest.

Hỗ trợ:
- Connection pool / Context manager an toàn
- Truy vấn thông thường (fetch_all, fetch_one, execute, execute_batch)
- Truy vấn dòng (stream_rows) với SSCursor để xử lý hàng triệu bản ghi không tràn RAM
- Quản lý giao dịch (transaction)
"""
import os
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Tuple

import pymysql
import pymysql.cursors

# Cấu hình mặc định (có thể ghi đè qua biến môi trường)
DEFAULT_MYSQL_CONFIG = dict(
    host=os.getenv("NORA_DB_HOST", "14.225.16.78"),
    port=int(os.getenv("NORA_DB_PORT", "3324")),
    user=os.getenv("NORA_DB_USER", "optimization"),
    password=os.getenv("NORA_DB_PASS", "0timization!@#QWEASDZXC"),
    database=os.getenv("NORA_DB_NAME", "coin_lab"),
    charset="utf8mb4",
    connect_timeout=10,
    read_timeout=60,
    autocommit=True,
)


def get_connection(config: Optional[Dict[str, Any]] = None, use_dict_cursor: bool = True) -> pymysql.Connection:
    """Tạo một kết nối mới tới MySQL."""
    cfg = dict(DEFAULT_MYSQL_CONFIG)
    if config:
        cfg.update(config)
    cursor_class = pymysql.cursors.DictCursor if use_dict_cursor else pymysql.cursors.Cursor
    return pymysql.connect(**cfg, cursorclass=cursor_class)


@contextmanager
def cursor(config: Optional[Dict[str, Any]] = None) -> Generator[pymysql.cursors.DictCursor, None, None]:
    """Context manager cấp phát cursor dạng Dictionary, tự động đóng kết nối khi xong."""
    conn = get_connection(config=config, use_dict_cursor=True)
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()


@contextmanager
def transaction(config: Optional[Dict[str, Any]] = None) -> Generator[pymysql.cursors.DictCursor, None, None]:
    """Context manager thực thi giao dịch MySQL (Commit/Rollback tự động)."""
    cfg = dict(DEFAULT_MYSQL_CONFIG)
    if config:
        cfg.update(config)
    cfg["autocommit"] = False
    conn = pymysql.connect(**cfg, cursorclass=pymysql.cursors.DictCursor)
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(sql: str, params: Optional[Tuple[Any, ...]] = None, config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Truy vấn lấy toàn bộ kết quả dạng danh sách dictionary."""
    with cursor(config=config) as cur:
        cur.execute(sql, params or ())
        return cur.fetchall() or []


def fetch_one(sql: str, params: Optional[Tuple[Any, ...]] = None, config: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Truy vấn lấy 1 bản ghi duy nhất."""
    with cursor(config=config) as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()


def execute(sql: str, params: Optional[Tuple[Any, ...]] = None, config: Optional[Dict[str, Any]] = None) -> int:
    """Thực thi câu lệnh INSERT / UPDATE / DELETE, trả về số dòng bị ảnh hưởng hoặc lastrowid."""
    with cursor(config=config) as cur:
        affected = cur.execute(sql, params or ())
        return cur.lastrowid if cur.lastrowid else affected


def execute_batch(sql: str, params_list: List[Tuple[Any, ...]], config: Optional[Dict[str, Any]] = None) -> int:
    """Thực thi batch insert/update hàng loạt với executemany."""
    if not params_list:
        return 0
    with transaction(config=config) as cur:
        return cur.executemany(sql, params_list)


def stream_rows(sql: str, params: Optional[Tuple[Any, ...]] = None, batch_size: int = 10000, config: Optional[Dict[str, Any]] = None) -> Generator[Dict[str, Any], None, None]:
    """Đọc dữ liệu theo dòng (Server-Side Cursor) để xử lý dữ liệu lớn (triệu dòng) không làm tràn RAM."""
    cfg = dict(DEFAULT_MYSQL_CONFIG)
    if config:
        cfg.update(config)
    conn = pymysql.connect(**cfg, cursorclass=pymysql.cursors.SSDictCursor)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            while True:
                chunk = cur.fetchmany(batch_size)
                if not chunk:
                    break
                for row in chunk:
                    yield row
    finally:
        conn.close()
