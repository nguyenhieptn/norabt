"""Kết nối MySQL — CHỈ ĐỌC.

Dùng chung cơ sở dữ liệu với hệ thống cũ nên tuyệt đối không ghi.
Mọi truy vấn đều phải có điều kiện lọc theo run (lab_result_account),
tránh kéo cả bảng như lỗi tràn bộ nhớ của portal cũ.
"""
import os
from contextlib import contextmanager

import pymysql

DB = dict(
    host=os.getenv("NORA_DB_HOST", "14.225.16.78"),
    port=int(os.getenv("NORA_DB_PORT", "3324")),
    user=os.getenv("NORA_DB_USER", "optimization"),
    password=os.getenv("NORA_DB_PASS", "0timization!@#QWEASDZXC"),
    database=os.getenv("NORA_DB_NAME", "coin_lab"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
    connect_timeout=10,
    read_timeout=60,
)


@contextmanager
def cursor():
    conn = pymysql.connect(**DB)
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()


def fetch_all(sql: str, params=None):
    with cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def fetch_one(sql: str, params=None):
    with cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchone()
