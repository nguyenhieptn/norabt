#!/usr/bin/env bash
# Chạy full flow: service-detail -> tự lấy endpoint -> probe -> confirm-free
# Dùng: bash run-nora.sh <BOT_CODE>
set -e
BOT="${1:?Cần truyền mã bot, ví dụ: bash run-nora.sh EF1CC6F40E834D1A}"
OC="${HOME}/.local/bin/onchainos"

# 1. Tra endpoint từ OKX theo SID 40700 (ví đã login là OKX tự biết endpoint)
echo "→ Tra thông tin Agent SID 40700 từ OKX..."
"$OC" agent service-detail --sid 40700 --agentic-id 13753 > /tmp/nora_svc.json

ENDPOINT=$(python3 -c "import json; d=json.load(open('/tmp/nora_svc.json')); print(d['data']['endpoint'])")
SID=$(python3      -c "import json; d=json.load(open('/tmp/nora_svc.json')); print(d['data']['sid'])")
STYPE=$(python3    -c "import json; d=json.load(open('/tmp/nora_svc.json')); print(d['data']['serviceType'])")

echo "→ Endpoint: $ENDPOINT"

# 2. Probe
ROUTING="{\"schemaVersion\":1,\"serviceSnapshot\":{\"serviceType\":\"$STYPE\",\"endpoint\":\"$ENDPOINT\",\"serviceId\":$SID}}"
"$OC" agent a2mcp-probe probe \
  --routing-json "$ROUTING" \
  --params-json "{\"code\":\"$BOT\"}" > /tmp/nora_probe.json

CONFID=$(python3 -c "import json; d=json.load(open('/tmp/nora_probe.json')); print(d['data']['payload']['confirmationId'])")
echo "→ ConfirmationId: $CONFID"

# 3. Confirm-free -> kết quả
"$OC" agent a2mcp-probe confirm-free --confirmation-id "$CONFID" --yes
