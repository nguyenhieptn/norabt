#!/bin/bash
# Nora Backtest — Dừng tiến trình API & Frontend
pkill -TERM -f "uvicorn backend.api.main" 2>/dev/null && sleep 1 || true
pkill -9 -f "uvicorn backend.api.main" 2>/dev/null || true
fuser -k 18010/tcp 2>/dev/null || true
echo "✅ Đã dừng Nora Backtest (port 18010)."
