#!/bin/bash
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NODE_OPTIONS="--openssl-legacy-provider"

echo "======================================================="
echo "🚀 BẮT ĐẦU BUILD TOÀN BỘ FRONTEND APPLICATIONS"
echo "======================================================="

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
