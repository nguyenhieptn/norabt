#!/usr/bin/env bash
# Chạy full flow: service-detail -> tự lấy endpoint -> probe -> confirm-free
# Dùng:
#   1 bot  : bash run-nora.sh EF1CC6F40E834D1A
#   nhiều bot (chấm chung 1 danh mục, 2-8 mã):
#            bash run-nora.sh 35F888C7BB441B2B 6F262ADB3B44266C
#            bash run-nora.sh "35F888C7BB441B2B,6F262ADB3B44266C"
set -euo pipefail

if [ "$#" -lt 1 ] || [ -z "${1// /}" ]; then
    echo "Cần truyền mã bot, ví dụ: bash run-nora.sh EF1CC6F40E834D1A" >&2
    echo "Nhiều bot: bash run-nora.sh MA_1 MA_2 [MA_3 ...]" >&2
    exit 1
fi
# Mọi đối số (và dấu phẩy/chấm phẩy/khoảng trắng bên trong) -> một chuỗi "A,B,C".
# Endpoint chỉ có MỘT tham số `code`: 1 mã = báo cáo 1 bot, >= 2 mã = báo cáo danh mục.
BOT=$(printf '%s ' "$@" | tr ',;' '  ' | xargs | tr ' ' ',')
OC="${ONCHAINOS_BIN:-$(command -v onchainos 2>/dev/null || echo "$HOME/.local/bin/onchainos")}"

if [ ! -x "$OC" ]; then
    echo "Lỗi: Không tìm thấy onchainos CLI tại '$OC' hoặc trên PATH." >&2
    exit 1
fi

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# Đọc một trường JSON; in lỗi dễ hiểu (thay vì traceback) nếu thiếu.
json_field() {  # json_field <file> <python-expr-on-d> <thông báo khi thiếu>
    python3 - "$1" "$2" "$3" <<'PY'
import json, sys
path, expr, what = sys.argv[1:4]
try:
    d = json.load(open(path))
    value = eval(expr, {"d": d})
    if value in (None, ""):
        raise KeyError(expr)
    print(value)
except Exception:
    raw = open(path).read().strip()
    msg = raw
    try:
        j = json.loads(raw)
        payload = (j.get("data") or {}).get("payload") or {}
        msg = (payload.get("result") or {}).get("message") or payload.get("message") \
            or j.get("msg") or j.get("error") or raw
    except Exception:
        pass
    sys.stderr.write(f"Lỗi: {what}\n→ Phản hồi: {str(msg)[:600]}\n")
    sys.exit(1)
PY
}

# 1. Tra endpoint từ OKX theo SID 40700 (ví đã login là OKX tự biết endpoint)
echo "→ Tra thông tin Agent SID 40700 từ OKX..."
"$OC" agent service-detail --sid 40700 --agentic-id 13753 > "$TMP_DIR/nora_svc.json" || true
ENDPOINT=$(json_field "$TMP_DIR/nora_svc.json" "d['data']['endpoint']" "không lấy được endpoint (đã chạy 'onchainos wallet login' chưa?)")
SID=$(json_field "$TMP_DIR/nora_svc.json" "d['data']['sid']" "không lấy được SID")
STYPE=$(json_field "$TMP_DIR/nora_svc.json" "d['data']['serviceType']" "không lấy được serviceType")

echo "→ Endpoint: $ENDPOINT"
case "$BOT" in
    *,*) echo "→ Danh mục $(echo "$BOT" | tr ',' '\n' | wc -l) bot: $BOT" ;;
    *)   echo "→ Bot: $BOT" ;;
esac

# 2. Probe
ROUTING="{\"schemaVersion\":1,\"serviceSnapshot\":{\"serviceType\":\"$STYPE\",\"endpoint\":\"$ENDPOINT\",\"serviceId\":$SID}}"
"$OC" agent a2mcp-probe probe \
  --routing-json "$ROUTING" \
  --params-json "{\"code\":\"$BOT\"}" > "$TMP_DIR/nora_probe.json" || true

CONFID=$(json_field "$TMP_DIR/nora_probe.json" "d['data']['payload']['confirmationId']" "endpoint từ chối yêu cầu (mã bot sai định dạng, hoặc quá 8 bot?)")
echo "→ ConfirmationId: $CONFID"

# 3. Confirm-free -> kết quả
"$OC" agent a2mcp-probe confirm-free --confirmation-id "$CONFID" --yes
