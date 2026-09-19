#!/usr/bin/env bash
#
# OKX Bot Risk — one-command risk assessment for any OKX copy-trading lead trader.
#
#   curl -fsSL https://agent.expsolution.io/assets/run.sh | bash
#   curl -fsSL https://agent.expsolution.io/assets/run.sh | bash -s -- <BOT_ID>
#
# Everything below runs through the OKX onchainos CLI. This script never talks
# to the analysis service directly: it asks OKX what the service is, and OKX
# supplies the endpoint, the parameter spec and the contract id. The only
# things hard-coded here are the agent's public identifiers on OKX.
set -uo pipefail

AGENT_ID="${OKX_AGENT_ID:-13753}"
SID="${OKX_SERVICE_SID:-40700}"

command -v onchainos >/dev/null 2>&1 || {
    echo "The OKX onchainos CLI is required but was not found on PATH." >&2
    echo "Install it first, then run this again." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "python3 is required." >&2; exit 1; }

printf '\033[2mResolving agent #%s on OKX ...\033[0m\n' "$AGENT_ID"
SVC=$(onchainos agent service-detail --sid "$SID" --agentic-id "$AGENT_ID" 2>&1) || {
    echo "Could not reach OKX." >&2; echo "$SVC" >&2; exit 1; }

# The bot id may come as an argument, an env var, or from the keyboard. When
# this script is piped into bash, stdin is the script itself, so the prompt has
# to read from the controlling terminal instead.
BOT="${1:-${BOT:-}}"

export SVC BOT
python3 <<'PY'
import base64, json, os, subprocess, sys, threading, time

svc = json.loads(os.environ["SVC"])["data"]
spec = (svc.get("serviceDescription") or "").split("\n")
name = spec[1].split("(")[0].strip()
meta = spec[1].split("(")[1].split(")")[0]
hint = spec[1].split(":", 1)[1].strip() if ":" in spec[1] else "the bot id"

print(f"\033[1m{svc.get('serviceName')}  ·  agent #{os.environ.get('OKX_AGENT_ID','13753')}"
      f"  ·  fee {svc.get('feeAmount')} USDT\033[0m\n")

bot = (os.environ.get("BOT") or "").strip()
if not bot:
    print("This service needs one input:")
    print(f"  {hint}\n")
    try:
        tty = open("/dev/tty", "r+")
        tty.write("Enter the bot ID to analyse: "); tty.flush()
        bot = tty.readline().strip()
        tty.write("Analyse this bot? [Y/n] "); tty.flush()
        if tty.readline().strip().lower().startswith("n"):
            print("Cancelled."); sys.exit(0)
    except OSError:
        print("No terminal available. Pass the bot id as an argument instead:", file=sys.stderr)
        print("  curl -fsSL <url> | bash -s -- <BOT_ID>", file=sys.stderr)
        sys.exit(1)
if not bot:
    print("No bot ID given.", file=sys.stderr); sys.exit(1)

routing = base64.b64encode(json.dumps({
    "schemaVersion": 1,
    "serviceSnapshot": {k: svc[k] for k in
                        ("serviceId", "serviceName", "serviceType", "endpoint")
                        if svc.get(k)} | {"fee": str(svc.get("feeAmount", 0))},
    "requestSpec": {"method": (spec[2].strip() if len(spec) > 2 else "POST"),
                    "carrier": "body", "required": [name],
                    "fields": [{"name": name, "type": meta.split(",")[0].strip(),
                                "required": True, "description": hint}]},
}).encode()).decode()

def run(args, label):
    """Run one OKX CLI call while showing a progress bar."""
    box = {}
    def work():
        box["out"] = subprocess.run(args, capture_output=True, text=True).stdout
    th = threading.Thread(target=work, daemon=True); th.start()
    width, i = 30, 0
    while th.is_alive():
        i = (i + 1) % (width + 1)
        print(f"\r  {label:<26} [{'#' * i:<{width}}]", end="", flush=True)
        time.sleep(0.35)
    th.join()
    print(f"\r  {label:<26} [{'#' * width}] done")
    return box.get("out", "")

probe = run(["onchainos", "agent", "a2mcp-probe", "probe", "--routing-base64", routing,
             "--params-base64", base64.b64encode(json.dumps({"code": bot}).encode()).decode()],
            "Submitting to OKX")
try:
    cid = json.loads(probe)["data"]["payload"]["confirmationId"]
except Exception:
    print("\nOKX did not issue a contract id:", file=sys.stderr)
    print(probe[:600], file=sys.stderr); sys.exit(1)
print(f"\033[2m  OKX contract id: {cid}\033[0m")

out = run(["onchainos", "agent", "a2mcp-probe", "confirm-free",
           "--confirmation-id", cid, "--yes"], "Analysing closed trades")
try:
    payload = json.loads(out)["data"]["payload"]; report = payload["result"]
    assert isinstance(report, dict)
except Exception:
    print("\nThe analysis did not return in time. It keeps running on the "
          "provider side — try again in a minute.", file=sys.stderr)
    sys.exit(1)

doc = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
       "okx": {"agent_id": os.environ.get("OKX_AGENT_ID", "13753"),
               "contract_id": cid, "endpoint": payload.get("endpoint"),
               "status_code": payload.get("statusCode")},
       "bot_id": bot, "report": report,
       "detail_url": report.get("report_url")}
path = os.path.join(os.getcwd(), f"okx-risk-{bot}.json")
json.dump(doc, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

print()
# Bot chưa từng được chấm sẽ trả PENDING: phân tích vẫn chạy ở phía nhà cung
# cấp và kết quả đầy đủ nằm ở đường dẫn bên dưới. In ra "None" cho từng ô điểm
# trong trường hợp này trông như hỏng, nên phải nói đúng là đang chạy.
if report.get("status") == "PENDING":
    print(f"  Bot        : {bot}")
    print("  Status     : analysis in progress (first time this bot is seen)")
    print("  The scores are not ready yet. The provider keeps working in the")
    print("  background; open the link below in about a minute for the full")
    print("  report, or run this command again to get the scores inline.")
else:
    print(f"  Bot        : {report.get('name')}  ({bot})")
    print(f"  Verdict    : {report.get('verdict')}")
    for label, key in (("Risk", "risk"), ("Quality", "quality"),
                       ("Confidence", "confidence")):
        v = report.get(key)
        if isinstance(v, (int, float)):
            print(f"  {label:<11}: {v:.1f} / 100")
    reason = report.get("verdict_reason")
    if reason:
        print(f"  Why        : {reason[:150]}")
print()
print(f"  Saved      : {path}")
print(f"  Full report: {report.get('report_url')}")
PY
