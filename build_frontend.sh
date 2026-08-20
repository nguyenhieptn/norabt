#!/bin/bash
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. GIỚI HẠN BỘ NHỚ V8 ENGINE: Tối đa 2.5GB RAM (dưới 8% tổng RAM 30GB máy chủ)
export NODE_OPTIONS="--max-old-space-size=2560 --openssl-legacy-provider"

# 2. GIỚI HẠN CPU CORES: Ghim cố định chỉ sử dụng 4 cores (Core 0, 1, 2, 3 - tức 1/6 CPU của 24 vCPUs)
CPU_AFFINITY="taskset -c 0-3"

echo "=========================================================================="
echo "🚀 BẮT ĐẦU BUILD FRONTEND (LIMIT: TỐI ĐA 4 CORES CPU & 2.5GB RAM)"
echo "=========================================================================="

# Kiểm tra an toàn bộ nhớ
AVAIL_RAM=$(free -m | awk '/^Mem:/{print $7}')
echo "🖥️ [Resource Guard] RAM Khả Dụng Hiện Tại: ${AVAIL_RAM} MB"
if [ "$AVAIL_RAM" -lt 3000 ]; then
    echo "⚠️ CẢNH BÁO: RAM khả dụng < 3000 MB. Đang dọn dẹp bộ nhớ trước khi build..."
    sync
fi

# 0. KIỂM THỬ LOGIC TRƯỚC KHI BUILD (fail-fast ~1s thay vì phí 1 lần build dài)
echo ""
echo "🧪 [0/2] Kiểm thử cấu hình & logic frontend trước khi build..."
node "$BASE_DIR/frontend/test_frontend_logic.js"

# 0.5. CÀI DEPENDENCIES NẾU THIẾU (lần build đầu) - có giới hạn CPU
for APP in monitor portal; do
    if [ ! -d "$BASE_DIR/frontend/$APP/node_modules" ]; then
        echo "📥 node_modules của $APP chưa có - cài đặt (giới hạn 4 cores)..."
        cd "$BASE_DIR/frontend/$APP"
        $CPU_AFFINITY npm ci --prefer-offline --no-audit --no-fund
    fi
done

# 1. BUILD MONITOR REACT SPA FRONTEND
echo ""
echo "📦 [1/2] Đang build Monitor React Dashboard (frontend/monitor)..."
cd "$BASE_DIR/frontend/monitor"

# 1a. Biên dịch theme/layout SCSS -> CSS (index.html tham chiếu các file .css này;
# CRA chỉ copy nguyên trạng public/ nên phải compile trước khi build)
echo "🎨 Biên dịch theme & layout SCSS (8 màu x dark/light)..."
for scss in public/assets/theme/*/*.scss public/assets/layout/css/*/*.scss; do
    $CPU_AFFINITY ./node_modules/.bin/sass --no-source-map --quiet --style=compressed "$scss" "${scss%.scss}.css"
done
echo "   ✅ Theme CSS sẵn sàng ($(find public/assets/theme public/assets/layout/css -name '*.css' | wc -l) files)"

$CPU_AFFINITY npm run build

# 1b. Symlink build/public -> . vì AppWrapper.js đổi theme runtime qua đường dẫn 'public/assets/...'
ln -sfn . build/public
echo "✅ Build Monitor Frontend thành công! (Output: frontend/monitor/build)"

# Dọn dẹp cache giữa 2 giai đoạn build
sync
sleep 2

# 2. BUILD PORTAL LARAVEL MIX FRONTEND
echo ""
echo "📦 [2/2] Đang build Portal React Web Assets (frontend/portal)..."
cd "$BASE_DIR/frontend/portal"
$CPU_AFFINITY npm run prod
echo "✅ Build Portal Frontend thành công! (Output: frontend/portal/public)"

echo ""
echo "=========================================================================="
echo "🎉 TẤT CẢ FRONTEND ĐÃ ĐƯỢC BIÊN DỊCH THÀNH CÔNG AN TOÀN VÀ TỐI ƯU!"
echo "=========================================================================="
