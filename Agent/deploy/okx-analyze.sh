#!/usr/bin/env bash
#
# Phân tích rủi ro một lead trader OKX — MỘT lệnh duy nhất, chạy qua nền OKX.
#
#   bash okx-analyze.sh                  (hỏi id bot)
#   bash okx-analyze.sh EF1CC6F40E834D1A (đưa luôn id bot)
#
# Script này CHỈ biết định danh agent trên OKX (AGENT_ID/SID dưới đây). Endpoint,
# serviceId và đặc tả tham số đều do OKX trả về ở bước 1 — không có địa chỉ nào
# của hệ thống cung cấp dịch vụ được cắm cứng ở đây. Đó là điểm phân biệt "gọi
# qua OKX" với "gọi thẳng vào máy chủ nhà cung cấp".
#
# Kết quả: đúng MỘT file JSON, chứa toàn bộ nội dung báo cáo cộng đường dẫn ẩn
# để xem bản đầy đủ có biểu đồ trên web.

set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"

AGENT_ID="${OKX_AGENT_ID:-13753}"
SID="${OKX_SERVICE_SID:-40700}"
OUT_DIR="${OKX_OUT_DIR:-$PWD}"

command -v onchainos >/dev/null || { echo "onchainos CLI not found on PATH." >&2; exit 1; }

bold() { printf '\033[1m%s\033[0m\n' "$*"; }
dim()  { printf '\033[2m%s\033[0m\n' "$*"; }

# --- 1. Ask OKX what this service is -------------------------------------
dim "Resolving agent #$AGENT_ID on OKX ..."
SVC=$(onchainos agent service-detail --sid "$SID" --agentic-id "$AGENT_ID" 2>&1) || {
    echo "Could not reach OKX. Raw response:" >&2; echo "$SVC" >&2; exit 1; }

eval "$(printf '%s' "$SVC" | python3 -c "
import sys, json, shlex
try:
    d = json.load(sys.stdin)['data']
except Exception:
    print('SVC_OK=0'); raise SystemExit
spec = (d.get('serviceDescription') or '').split(chr(10))
prompt = spec[1].split(':', 1)[1].strip() if len(spec) > 1 and ':' in spec[1] else 'the bot uniqueCode'
print('SVC_OK=1')
print('SVC_NAME=' + shlex.quote(d.get('serviceName') or ''))
print('SVC_FEE=' + shlex.quote(str(d.get('feeAmount', 0))))
print('SVC_PROMPT=' + shlex.quote(prompt))
")"
[ "${SVC_OK:-0}" = "1" ] || { echo "OKX did not return a usable service record." >&2; exit 1; }

bold "$SVC_NAME  ·  agent #$AGENT_ID  ·  fee ${SVC_FEE} USDT"
echo

# --- 2. OKX asks for the parameter ---------------------------------------
CODE="${1:-}"
if [ -z "$CODE" ]; then
    echo "This service needs one input:"
    echo "  $SVC_PROMPT"
    echo
    printf 'Enter the bot ID to analyse: '
    read -r CODE
fi
CODE=$(printf '%s' "$CODE" | tr -d '[:space:]')
[ -n "$CODE" ] || { echo "No bot ID given. Nothing to do." >&2; exit 1; }

echo
printf 'Analyse bot %s? [Y/n] ' "$CODE"
read -r ANSWER
case "${ANSWER:-Y}" in [Nn]*) echo "Cancelled."; exit 0 ;; esac
echo

# --- 3. Build the routing FROM OKX'S OWN ANSWER --------------------------
ROUTING=$(printf '%s' "$SVC" | python3 -c "
import sys, json, base64
d = json.load(sys.stdin)['data']
spec = (d.get('serviceDescription') or '').split(chr(10))
fields = []
if len(spec) > 1 and '(' in spec[1]:
    name = spec[1].split('(')[0].strip()
    meta = spec[1].split('(')[1].split(')')[0]
    fields = [{'name': name, 'type': meta.split(',')[0].strip(),
               'required': 'required' in meta,
               'description': spec[1].split(':', 1)[1].strip() if ':' in spec[1] else ''}]
snap = {k: d[k] for k in ('serviceId', 'serviceName', 'serviceType', 'endpoint') if d.get(k)}
snap['fee'] = str(d.get('feeAmount', 0))
print(base64.b64encode(json.dumps({
    'schemaVersion': 1, 'serviceSnapshot': snap,
    'requestSpec': {'method': (spec[2].strip() if len(spec) > 2 else 'POST'),
                    'carrier': 'body',
                    'required': [f['name'] for f in fields if f['required']],
                    'fields': fields}}).encode()).decode())
")

# --- progress bar while OKX works ----------------------------------------
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
progress() {   # $1 = label, $2 = pid to wait on
    local i=0 w=32
    while kill -0 "$2" 2>/dev/null; do
        i=$(( (i + 1) % (w + 1) ))
        printf '\r  %-28s [%-*s] ' "$1" "$w" "$(printf '#%.0s' $(seq 1 $i 2>/dev/null))"
        sleep 0.4
    done
    printf '\r  %-28s [%-*s] done\n' "$1" "$w" "$(printf '#%.0s' $(seq 1 $w))"
}

( onchainos agent a2mcp-probe probe --routing-base64 "$ROUTING" \
     --params-base64 "$(printf '{"code":"%s"}' "$CODE" | base64 -w0)" >"$TMP/probe.json" 2>&1 ) &
progress "Submitting to OKX" $!
wait $! 2>/dev/null

CID=$(python3 -c "
import json,sys
try: print(json.load(open('$TMP/probe.json'))['data']['payload'].get('confirmationId',''))
except Exception: print('')")
[ -n "$CID" ] || { echo; echo "OKX did not issue a confirmation id. Raw response:" >&2
                   head -c 600 "$TMP/probe.json" >&2; echo >&2; exit 1; }
dim "  OKX contract id: $CID"

( onchainos agent a2mcp-probe confirm-free --confirmation-id "$CID" --yes \
     >"$TMP/result.json" 2>&1 ) &
progress "Analysing closed trades" $!
wait $! 2>/dev/null

# --- 4. One JSON file out -------------------------------------------------
python3 - "$TMP/result.json" "$OUT_DIR" "$CODE" "$CID" <<'PY'
import json, sys, os, datetime

raw, out_dir, code, cid = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
try:
    payload = json.load(open(raw))['data']['payload']
except Exception:
    print("\nThe result could not be parsed. Raw response:\n")
    print(open(raw).read()[:800]); raise SystemExit(1)

result = payload.get('result')
if not isinstance(result, dict):
    print("\nOKX returned an empty result — the analysis did not finish in time.")
    print("Try again in a minute; the work continues in the background.")
    raise SystemExit(1)

doc = {
    "generated_at": datetime.datetime.now(datetime.timezone.utc)
                        .isoformat(timespec="seconds").replace("+00:00", "Z"),
    "okx": {"agent_id": os.environ.get("OKX_AGENT_ID", "13753"),
            "contract_id": cid,
            "endpoint": payload.get("endpoint"),
            "status_code": payload.get("statusCode")},
    "bot_id": code,
    "report": result,
    "detail_url": result.get("report_url"),
}
path = os.path.join(out_dir, f"okx-risk-{code}.json")
with open(path, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, ensure_ascii=False, indent=2)

print()
print(f"  Bot        : {result.get('name')}  ({code})")
print(f"  Verdict    : {result.get('verdict')}")
risk, quality = result.get('risk'), result.get('quality')
if isinstance(risk, (int, float)):
    print(f"  Risk       : {risk:.1f} / 100")
if isinstance(quality, (int, float)):
    print(f"  Quality    : {quality:.1f} / 100")
conf = result.get('confidence')
if isinstance(conf, (int, float)):
    print(f"  Confidence : {conf:.1f} / 100")
for w in (result.get('warnings') or [])[:2]:
    print(f"  Warning    : {w[:96]}")
print()
print(f"  Saved      : {path}  ({os.path.getsize(path) // 1024} KB)")
print(f"  Full report: {result.get('report_url')}")
PY
