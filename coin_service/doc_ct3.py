import os, django, json, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE','crypto_lab.settings'); django.setup()
from django.db import connections
from Console.Models.Coin_lab import LabStrategies
grp = sys.argv[1]
with connections[LabStrategies.objects.db].cursor() as c:
    c.execute("SELECT lab_strategy_id, lab_strategy_name, lab_strategy_content FROM lab_strategies WHERE lab_strategy_group=%s AND LENGTH(lab_strategy_content) BETWEEN 1500 AND 9000 ORDER BY LENGTH(lab_strategy_content) LIMIT 1", [grp])
    sid, name, ct = c.fetchone()
j = json.loads(ct)
print(f"### {name} (id {sid}) — {grp}")
for fname, flow in j.items():
    if not isinstance(flow, dict) or 'match' not in flow: continue
    m = flow['match']
    print(f"\nLUỒNG '{fname}' type={flow.get('type')} | {len(m)} phase")
    for i, ph in enumerate(m[:3]):
        print(f"  Phase {i}: package={ph.get('enter_package')}% margin={ph.get('margin')} tp={ph.get('takeprofit')} sl={ph.get('stoploss')}")
        print(f"    {json.dumps(ph.get('condition'), ensure_ascii=False)[:400]}")
    ex = flow.get('exit') or flow.get('close')
    if ex: print(f"  THOÁT: {json.dumps(ex, ensure_ascii=False)[:250]}")
