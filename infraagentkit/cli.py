from __future__ import annotations
import argparse,shutil,subprocess,sys
from pathlib import Path
from .cards import load_card
from .tools import default_registry

def cmd_doctor(_):
    base=Path(__file__).resolve().parent.parent;cards=list((base/'examples/agents').glob('*.yaml'));errs=[]
    for p in cards:
        try:load_card(p)
        except Exception as e:errs.append(f'{p}: {e}')
    print({'status':'ok' if not errs else 'failed','python':sys.version.split()[0],'cards':len(cards),'tools':default_registry().names(),'errors':errs})
    return 0 if not errs else 1

def cmd_init(a):
    target=Path(a.path);target.mkdir(parents=True,exist_ok=True)
    sample=Path(__file__).resolve().parent.parent/'examples/agents/hse-agent.yaml';shutil.copy(sample,target/'agent.yaml')
    (target/'README.md').write_text('# New InfraAgentKit Agent\n\nEdit `agent.yaml`, then register implementation tools in your host runtime.\n')
    print(target.resolve());return 0

def cmd_serve(a):
    import uvicorn;uvicorn.run('infraagentkit.web:app',host='0.0.0.0',port=a.port,reload=a.reload);return 0

def cmd_eval(_):
    base=Path(__file__).resolve().parent.parent;return subprocess.call([sys.executable,str(base/'evals/run_benchmark.py')],cwd=base)

def cmd_mcp(a):
    base=Path(__file__).resolve().parent.parent;return subprocess.call([sys.executable,str(base/'servers/mcp_server.py'),'--transport',a.transport,'--port',str(a.port)],cwd=base)

def main():
    p=argparse.ArgumentParser(prog='infra-agent');s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('doctor');q.set_defaults(fn=cmd_doctor)
    q=s.add_parser('init');q.add_argument('path');q.set_defaults(fn=cmd_init)
    q=s.add_parser('serve');q.add_argument('--port',type=int,default=8103);q.add_argument('--reload',action='store_true');q.set_defaults(fn=cmd_serve)
    q=s.add_parser('eval');q.set_defaults(fn=cmd_eval)
    q=s.add_parser('mcp-serve');q.add_argument('--transport',choices=['stdio','streamable-http'],default='stdio');q.add_argument('--port',type=int,default=8113);q.set_defaults(fn=cmd_mcp)
    a=p.parse_args();raise SystemExit(a.fn(a))
if __name__=='__main__':main()
