import os, django, json, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','crypto_lab.settings'); django.setup()
from django.db import connections
from Console.Models.Coin_lab import LabStrategies
grp = sys.argv[1]
with connections[LabStrategies.objects.db].cursor() as c:
    c.execute("SELECT lab_strategy_id, lab_strategy_name, lab_strategy_content FROM lab_strategies WHERE lab_strategy_group=%s AND LENGTH(lab_strategy_content)>500 ORDER BY LENGTH(lab_strategy_content) LIMIT 1", [grp])
    sid, name, ct = c.fetchone()
j = json.loads(ct)
print(f"### {name} (id {sid}) — nhóm '{grp}'")
print("Các luồng:", [k for k in j if isinstance(j[k], dict)])
for fname, flow in j.items():
    if not isinstance(flow, dict): continue
    print(f"\n--- LUỒNG '{fname}' | type={flow.get('type')} ---")
    print("  khóa:", list(flow.keys()))
    m = flow.get('match')
    if isinstance(m, list) and m:
        print(f"  số phase (bậc DCA): {len(m)}")
        print("  PHASE 0 (lệnh mở đầu):", json.dumps(m[0], ensure_ascii=False)[:700])
        if len(m) > 1:
            print("  PHASE 1 (vào thêm):", json.dumps(m[1], ensure_ascii=False)[:400])
    break
