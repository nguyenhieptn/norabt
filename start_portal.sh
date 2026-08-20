#!/bin/bash
# Khởi chạy Portal Laravel 5.5 (Phoenix System) qua Docker PHP 7.4
# - PHP 8.4 của hệ thống KHÔNG tương thích Laravel 5.5 nên portal chạy trong container php:7.4
# - Giới hạn tài nguyên: 2 CPU cores, 1GB RAM (trong ngưỡng <= 1/2 server)
set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE=norabt-portal-php74
NAME=norabt-portal

# Build image nếu chưa có
if ! docker image inspect $IMAGE >/dev/null 2>&1; then
    echo "🐳 Image $IMAGE chưa có - đang build..."
    docker build -t $IMAGE -f "$BASE_DIR/coins/docker/php74.Dockerfile" "$BASE_DIR/coins/docker"
fi

# Cài vendor nếu chưa có (lần đầu)
if [ ! -d "$BASE_DIR/coins/vendor" ]; then
    echo "📥 vendor/ chưa có - composer install (giới hạn 4 cores, 2GB RAM)..."
    docker run --rm --cpus=4 --memory=2g --network host -u 1000:1000 \
        -v "$BASE_DIR/coins:/app" $IMAGE \
        composer install --no-dev --prefer-dist --no-interaction --no-progress
fi

# Khởi chạy (xóa container cũ nếu tồn tại)
docker rm -f $NAME >/dev/null 2>&1 || true
# Port 18088: dải 18xxx tránh tranh chấp với dịch vụ khác trên server dùng chung
docker run -d --name $NAME --restart unless-stopped --network host \
    --cpus=2 --memory=1g -u 1000:1000 \
    -v "$BASE_DIR/coins:/app" -w /app \
    -v "$BASE_DIR/coins/docker/php-custom.ini:/usr/local/etc/php/conf.d/zz-norabt.ini:ro" \
    $IMAGE php artisan serve --host 0.0.0.0 --port 18088

echo "✅ Portal đang chạy tại http://localhost:18088 (container: $NAME)"
echo "   Dừng: docker stop $NAME | Log: docker logs -f $NAME"
