import os, django, json, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','crypto_lab.settings'); django.setup()
from django.db import connections
from Console.Models.Coin_lab import LabStrategies
name_like = sys.argv[1]
with connections[LabStrategies.objects.db].cursor() as c:
    c.execute("SELECT lab_strategy_id, lab_strategy_name, lab_strategy_content FROM lab_strategies WHERE lab_strategy_name LIKE %s AND LENGTH(lab_strategy_content)>2000 LIMIT 1", [name_like])
    r = c.fetchone()
sid, name, ct = r
j = json.loads(ct)
print(f"### {name} (id {sid})")
for fname, flow in j.items():
    if not isinstance(flow, dict) or 'match' not in flow: continue
    m = flow['match']
    print(f"\nLUỒNG '{fname}' type={flow.get('type')} | {len(m)} phase")
    for i, ph in enumerate(m[:4]):
        cond = json.dumps(ph.get('condition'), ensure_ascii=False)
        print(f"  Phase {i}: package={ph.get('enter_package')}% margin={ph.get('margin')} step={ph.get('enter_step')} back={ph.get('enter_back')}")
        print(f"           điều kiện: {cond[:330]}")
    break
