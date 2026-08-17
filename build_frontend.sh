#!/bin/bash
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Giới hạn cứng bộ nhớ Node.js tối đa 1.5GB RAM (đảm bảo không chiếm quá ngân sách)
export NODE_OPTIONS="--max-old-space-size=1536 --openssl-legacy-provider"

echo "======================================================="
echo "🚀 BẮT ĐẦU BUILD FRONTEND (NGÂN SÁCH RAM: TỐI ĐA 1.5GB)"
echo "======================================================="

# Kiểm tra RAM khả dụng
AVAIL_RAM=$(free -m | awk '/^Mem:/{print $7}')
echo "🖥️ [Resource Check] RAM Khả Dụng Hiện Tại: ${AVAIL_RAM} MB"
if [ "$AVAIL_RAM" -lt 2000 ]; then
    echo "⚠️ CẢNH BÁO: RAM khả dụng < 2000 MB. Đang dọn dẹp cache trước khi build..."
    sync
fi

# 1. BUILD MONITOR REACT SPA FRONTEND
echo ""
echo "📦 [1/2] Đang build Monitor React Dashboard (frontend/monitor)..."
cd "$BASE_DIR/frontend/monitor"
npm run build
echo "✅ Build Monitor Frontend thành công! (Output: frontend/monitor/build)"

# 2. BUILD PORTAL LARAVEL MIX FRONTEND
echo ""
echo "📦 [2/2] Đang build Portal React Web Assets (frontend/portal)..."
cd "$BASE_DIR/frontend/portal"
npm run prod
echo "✅ Build Portal Frontend thành công! (Output: frontend/portal/public)"

echo ""
echo "======================================================="
echo "🎉 TẤT CẢ FRONTEND ĐÃ ĐƯỢC BIÊN DỊCH THÀNH CÔNG!"
echo "======================================================="
