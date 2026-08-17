#!/bin/bash

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NODE_OPTIONS="--openssl-legacy-provider"

echo "======================================================="
echo "💻 KHỞI CHẠY FRONTEND DEVELOPMENT SERVERS"
echo "======================================================="
echo "1. Monitor React SPA: http://localhost:8001"
echo "======================================================="

cd "$BASE_DIR/frontend/monitor"
npm run start
