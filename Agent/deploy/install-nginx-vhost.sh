#!/usr/bin/env bash
#
# Cài vhost nginx cho agent-web lên máy này.
#
#   sudo bash Agent/deploy/install-nginx-vhost.sh
#
# Máy này đang chạy 15 site production. Script được viết để KHÔNG làm gián
# đoạn chúng:
#
#   * chỉ THÊM một file vhost mới, không sửa vhost nào đang có
#   * chèn 3 dòng limit_*_zone vào khối http{} của nginx.conf -- có kiểm tra
#     trước, chạy lại nhiều lần cũng không nhân đôi
#   * sao lưu nginx.conf trước khi sửa
#   * `nginx -t` trước khi nạp lại; HỎNG thì tự khôi phục và KHÔNG nạp lại
#   * dùng `reload` chứ không `restart` -- kết nối đang mở không bị cắt
#
# Không cấp chứng chỉ TLS ở đây. Cloudflare đang bật proxy nên TLS đã hợp lệ
# sẵn ở biên; chặng Cloudflare->máy này là HTTP cổng 80 (chế độ Flexible).
# Muốn mã hoá nốt chặng đó thì xem "Giai đoạn B" trong Agent/deploy/README.md
# -- và ĐỌC KỸ thứ tự ở đó, làm sai thứ tự sẽ gây vòng lặp chuyển hướng.

set -euo pipefail

DOMAIN="${DOMAIN:-agent.expsolution.io}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TEMPLATE="$REPO_DIR/Agent/deploy/nginx-agent.conf.template"
NGINX_CONF="/etc/nginx/nginx.conf"
VHOST_AVAILABLE="/etc/nginx/sites-available/$DOMAIN"
VHOST_ENABLED="/etc/nginx/sites-enabled/$DOMAIN"
STAMP="$(date +%Y%m%d-%H%M%S)"

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mLỖI: %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "Phải chạy bằng sudo: sudo bash $0"
[ -f "$TEMPLATE" ] || die "Không thấy file mẫu: $TEMPLATE"
command -v nginx >/dev/null || die "Không thấy nginx trên máy này."

# --- 1. Ba dòng zone trong khối http{} -------------------------------------
# Đặt ở http{} chứ không ở server{} vì limit_req_zone/limit_conn_zone chỉ hợp
# lệ ở cấp http. Tên zone có tiền tố agent_ nên không đụng zone của site khác.
say "Kiểm tra 3 dòng limit_*_zone trong $NGINX_CONF"
if grep -q "zone=agent_analyze" "$NGINX_CONF"; then
    echo "    đã có từ trước, bỏ qua"
else
    cp -a "$NGINX_CONF" "$NGINX_CONF.bak.$STAMP"
    echo "    đã sao lưu -> $NGINX_CONF.bak.$STAMP"
    # Chèn ngay sau dòng mở khối http{} đầu tiên.
    awk '
        !done && /^[[:space:]]*http[[:space:]]*\{/ {
            print
            print "\t# agent-web (agent.expsolution.io) -- xem Agent/deploy/nginx-agent.conf.template"
            print "\tlimit_req_zone  $binary_remote_addr zone=agent_analyze:10m rate=30r/m;"
            print "\tlimit_req_zone  $binary_remote_addr zone=agent_general:10m rate=20r/s;"
            print "\tlimit_conn_zone $binary_remote_addr zone=agent_conn:10m;"
            done = 1
            next
        }
        { print }
    ' "$NGINX_CONF.bak.$STAMP" > "$NGINX_CONF"
    grep -q "zone=agent_analyze" "$NGINX_CONF" \
        || { cp -a "$NGINX_CONF.bak.$STAMP" "$NGINX_CONF"; die "Không chèn được vào khối http{}. Đã khôi phục. Hãy thêm 3 dòng bằng tay."; }
    echo "    đã chèn 3 dòng"
fi

# --- 2. File vhost ----------------------------------------------------------
say "Ghi vhost cho $DOMAIN"
if [ -f "$VHOST_AVAILABLE" ]; then
    cp -a "$VHOST_AVAILABLE" "$VHOST_AVAILABLE.bak.$STAMP"
    echo "    file cũ đã sao lưu -> $VHOST_AVAILABLE.bak.$STAMP"
fi
sed "s/<DOMAIN>/$DOMAIN/g" "$TEMPLATE" > "$VHOST_AVAILABLE"
echo "    đã ghi $VHOST_AVAILABLE"

if [ -L "$VHOST_ENABLED" ] || [ -f "$VHOST_ENABLED" ]; then
    echo "    symlink đã có, bỏ qua"
else
    ln -s "$VHOST_AVAILABLE" "$VHOST_ENABLED"
    echo "    đã bật $VHOST_ENABLED"
fi

# --- 3. Kiểm cú pháp, hỏng thì lùi lại -------------------------------------
say "nginx -t"
if nginx -t; then
    echo "    cú pháp hợp lệ"
else
    printf '\n\033[1;31mnginx -t THẤT BẠI — đang khôi phục, KHÔNG nạp lại.\033[0m\n' >&2
    rm -f "$VHOST_ENABLED"
    [ -f "$NGINX_CONF.bak.$STAMP" ] && cp -a "$NGINX_CONF.bak.$STAMP" "$NGINX_CONF"
    die "Đã khôi phục nguyên trạng. 15 site kia không bị ảnh hưởng. Gửi toàn bộ output ở trên cho người phụ trách."
fi

# --- 4. Nạp lại -------------------------------------------------------------
say "systemctl reload nginx"
systemctl reload nginx
echo "    đã nạp lại (reload, không restart)"

# --- 5. Kiểm tra ------------------------------------------------------------
say "Kiểm tra"
echo "--- container nội bộ (phải 200) ---"
curl -s -o /dev/null -w "    127.0.0.1:8770/healthz -> HTTP %{http_code}\n" \
    http://127.0.0.1:8770/healthz || true

echo "--- qua nginx, bỏ qua Cloudflare (phải 200) ---"
curl -s -H "Host: $DOMAIN" -o /dev/null -w "    origin:80/healthz     -> HTTP %{http_code}\n" \
    http://127.0.0.1/healthz || true

echo "--- qua Cloudflare, đường đi thật của OKX (phải 200) ---"
curl -s -o /dev/null -w "    https://$DOMAIN/healthz -> HTTP %{http_code}\n" \
    "https://$DOMAIN/healthz" || true

echo "--- vài site khác, xác nhận không gián đoạn ---"
for h in ai.expsolution.io qhome.com.vn; do
    curl -s -o /dev/null -m 10 -w "    https://$h -> HTTP %{http_code}\n" "https://$h" || true
done

say "Xong"
cat <<EOF
Thử phân tích thật:

  curl -X POST https://$DOMAIN/api/analyze \\
    -H 'Content-Type: application/json' \\
    -d '{"code":"EF1CC6F40E834D1A"}'

Nếu có gì sai, gỡ bỏ bằng:

  sudo rm -f $VHOST_ENABLED
  sudo cp -a $NGINX_CONF.bak.$STAMP $NGINX_CONF   # nếu bản sao lưu này tồn tại
  sudo nginx -t && sudo systemctl reload nginx
EOF
