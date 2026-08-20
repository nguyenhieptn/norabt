#!/bin/bash
# Nora Backtest — hệ thống backtest độc lập
#   API + giao diện: http://localhost:18010
#   Đọc dữ liệu backtest từ MySQL của hệ thống hiện tại (CHỈ ĐỌC)
set -e
BASE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYBIN=/home/ubuntu/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11

echo "======================================================="
echo "🔬 NORA BACKTEST"
echo "======================================================="

if [ ! -f "$BASE/nora/frontend/dist/index.html" ]; then
    echo "📦 Chưa có bản build giao diện — đang build (giới hạn 4 cores)..."
    cd "$BASE/nora/frontend"
    [ -d node_modules ] || taskset -c 0-3 nice -n 10 npm install --no-audit --no-fund
    taskset -c 0-3 nice -n 10 npm run build
fi

pkill -f "uvicorn backend.api.main" 2>/dev/null && sleep 2 || true

cd "$BASE/nora"
setsid nohup taskset -c 4-7 nice -n 5 "$PYBIN" -m uvicorn backend.api.main:app \
    --host 0.0.0.0 --port 18010 > "$BASE/data/logs/nora_api.log" 2>&1 < /dev/null &

sleep 6
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:18010/api/health | grep -q 200; then
    echo "✅ Đang chạy tại http://localhost:18010"
    echo "   Log: data/logs/nora_api.log"
else
    echo "❌ Khởi động thất bại — xem data/logs/nora_api.log"
    exit 1
fi
echo "======================================================="
