#!/bin/bash
# Nora Backtest — Dừng tiến trình API & Frontend
pkill -f "uvicorn backend.api.main" 2>/dev/null && echo "✅ Đã dừng Nora Backtest (port 18010)." || echo "ℹ️ Nora Backtest hiện không chạy."
