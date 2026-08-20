#!/bin/bash
# Khởi chạy Frontend PRODUCTION (nhẹ, có proxy API) - KHÔNG dùng dev server trên máy chủ
#   Monitor UI : http://localhost:18001 (static build + proxy API -> Django 18002)
#   Portal UI  : http://localhost:18088 (xem start_portal.sh - Docker PHP 7.4)
# Yêu cầu: đã chạy build_frontend.sh trước đó.

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================================="
echo "💻 KHỞI CHẠY FRONTEND PRODUCTION SERVERS"
echo "======================================================="

if [ ! -f "$BASE_DIR/frontend/monitor/build/index.html" ]; then
    echo "❌ Chưa có bản build. Chạy: bash build_frontend.sh"
    exit 1
fi

# Dừng instance cũ nếu có
pkill -f "serve_monitor.py" 2>/dev/null && sleep 1

echo "🚀 Monitor UI (port 18001, giới hạn cores 4-7)..."
nohup taskset -c 4-7 python3 "$BASE_DIR/frontend/serve_monitor.py" \
    > "$BASE_DIR/frontend/serve_monitor.log" 2>&1 &
echo "   PID: $! | Log: frontend/serve_monitor.log"

echo ""
echo "ℹ️  Portal UI (port 18088): bash start_portal.sh"
echo "ℹ️  Backend API (port 18002) cần chạy để dashboard có dữ liệu: xem start_backend.sh"
echo "======================================================="
