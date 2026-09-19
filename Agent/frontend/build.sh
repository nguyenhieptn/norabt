#!/usr/bin/env bash
# Agent/frontend/build.sh -- the ONLY sanctioned way to build this SPA.
#
# WHY THIS SCRIPT EXISTS INSTEAD OF JUST "npm run build": this host runs 15
# OTHER production sites (see Agent/deploy/README.md's own resource-limit
# section) under a hard project-wide ceiling of <=12 cores / <=14GB RAM. A
# bare `npm run build` lets Vite's esbuild/rollup pipeline use every core
# and however much heap it wants -- on this box that risks starving the
# other sites (MySQL/MongoDB/PHP-FPM/6 Docker containers) for the minute or
# two the build runs. Wrapping the actual build command here means nobody
# has to remember the `taskset`/`NODE_OPTIONS` incantation by hand, and a CI
# step or a human just runs this file.
#
# Never run `npm run build` directly -- always `bash Agent/frontend/build.sh`.
set -euo pipefail

_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$_HERE"

if [ ! -d node_modules ]; then
  echo "node_modules/ chưa có -- chạy 'npm install' trước (một lần, không cần" >&2
  echo "taskset: cài đặt phụ thuộc không tốn CPU đáng kể như build)." >&2
  exit 1
fi

# -c 0-3: bounded to 4 logical cores, never all of them -- matches this
# project's own documented build-resource policy (see
# Agent/README.md/docs/frontend-build-optimization notes for the identical
# reasoning already applied to nora/'s own build_frontend.sh).
# NODE_OPTIONS=--max-old-space-size=2560: caps V8's heap at 2.5GB so a
# pathological dependency graph (or Vite/esbuild itself) cannot balloon RAM
# usage on a box shared with MySQL/MongoDB/PHP-FPM and 6 other containers.
taskset -c 0-3 env NODE_OPTIONS=--max-old-space-size=2560 npm run build

# Vite xoá sạch `dist/` mỗi lần build, nên `run.sh` -- script một-lệnh người
# dùng tải bằng `curl -fsSL https://<domain>/assets/run.sh | bash` -- phải được
# đặt lại sau mỗi lần build. Không có bước này thì đường dẫn đó âm thầm thành
# 404 và không ai biết cho tới khi có người thật thử chạy.
# Nguồn duy nhất là Agent/deploy/okx-run.sh; chỗ này chỉ sao chép.
_SRC="$_HERE/../deploy/okx-run.sh"
_DST="$_HERE/../web/dist/assets/run.sh"
if [ -f "$_SRC" ]; then
    install -m 0644 "$_SRC" "$_DST"
    echo "đã đặt lại $_DST"
else
    echo "CẢNH BÁO: không thấy $_SRC -- /assets/run.sh sẽ 404" >&2
fi
