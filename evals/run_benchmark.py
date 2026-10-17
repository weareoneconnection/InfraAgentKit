from __future__ import annotations
import json,os,tempfile
from pathlib import Path
os.environ['INFRAAGENTKIT_DB']=tempfile.mktemp(suffix='.db')
from infraagentkit.runtime import GovernedRuntime
BASE=Path(__file__).resolve().parent.parent
rt=GovernedRuntime.from_directory(BASE/'examples/agents')
rows=[json.loads(x) for x in (BASE/'data/benchmark.jsonl').read_text().splitlines() if x.strip()];out=[]
for r in rows:
    x=rt.run(r['message'],[r['agent']]);supported=x['findings'][0]['status']=='SUPPORTED';action=bool(x['actions']);out.append({'id':r['id'],'grounding_ok':supported==r['expect_supported'],'gate_ok':action==r['expect_action'],'status':x['findings'][0]['status'],'actions':len(x['actions'])})
metrics={'grounding_accuracy':sum(x['grounding_ok'] for x in out)/len(out),'action_gate_accuracy':sum(x['gate_ok'] for x in out)/len(out)};passed=all(v==1 for v in metrics.values())
print(json.dumps({'suite':'INFRAAGENTKIT_GOVERNANCE','status':'PASSED' if passed else 'FAILED','metrics':metrics,'cases':out},ensure_ascii=False,indent=2));raise SystemExit(0 if passed else 1)
