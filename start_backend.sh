#!/bin/bash

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="/home/ubuntu/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11"

echo "======================================================="
echo "⚙️ KHỞI CHẠY BACKEND SERVICES CLUSTER"
echo "======================================================="

# 1. Khởi chạy coin_service Socket Hub Server & Worker
echo "🚀 Đang khởi chạy Backtest Engine & Socket Hub (coin_service)..."
cd "$BASE_DIR/coin_service"
$PYTHON_BIN manage.py lab_server &
SERVER_PID=$!
echo "   - Lab Server PID: $SERVER_PID (Port 5000)"

$PYTHON_BIN manage.py lab_client &
CLIENT_PID=$!
echo "   - Lab Client PID: $CLIENT_PID"

# 2. Khởi chạy coin_monitor Django REST API
echo "🚀 Đang khởi chạy Data & Metrics REST API (coin_monitor)..."
cd "$BASE_DIR/coin_monitor"
$PYTHON_BIN manage.py runserver 0.0.0.0:8002 &
MONITOR_PID=$!
echo "   - Monitor API PID: $MONITOR_PID (Port 8002)"

echo ""
echo "======================================================="
echo "✅ TOÀN BỘ BACKEND SERVICES ĐÃ ĐƯỢC KHỞI CHẠY!"
echo "   Nhấn Ctrl+C để dừng tất cả dịch vụ."
echo "======================================================="

# Trap Ctrl+C để dừng tất cả tiến trình con
trap "kill $SERVER_PID $CLIENT_PID $MONITOR_PID 2>/dev/null; exit" SIGINT SIGTERM
wait
