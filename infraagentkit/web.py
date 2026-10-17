from __future__ import annotations
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI,HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,Field
from .runtime import GovernedRuntime
from . import state

BASE=Path(__file__).resolve().parent.parent
runtime=GovernedRuntime.from_directory(BASE/'examples/agents')

class RunIn(BaseModel):
    message:str=Field(min_length=3,max_length=8000)
    agent_ids:list[str]=Field(default_factory=lambda:['hse-agent'])
class Actor(BaseModel):actor:str='project_manager'

app=FastAPI(title='InfraAgentKit Runtime',version='1.0.0')
@app.get('/health')
def health():return {'status':'ok','product':'InfraAgentKit','version':'1.0.0','architecture':'agent-card-tool-policy-evidence-approval-receipt-verifier'}
@app.get('/agents')
def agents():return [c.model_dump() for c in runtime.cards.values()]
@app.get('/tools')
def tools():return runtime.registry.describe()
@app.post('/runs',status_code=201)
def run(p:RunIn):
    try:return runtime.run(p.message,p.agent_ids)
    except KeyError as e:raise HTTPException(422,str(e))
@app.get('/runs/{run_id}')
def get_run(run_id:str):
    r=state.get_run(run_id)
    if not r:raise HTTPException(404,'run not found')
    return r
@app.post('/actions/{action_id}/approve')
def approve(action_id:str,p:Actor):
    try:return runtime.approve(action_id,p.actor)
    except KeyError:raise HTTPException(404,'action not found')
    except ValueError as e:raise HTTPException(409,str(e))
@app.post('/actions/{action_id}/execute')
def execute(action_id:str):
    try:return runtime.execute(action_id)
    except KeyError:raise HTTPException(404,'action not found')
    except PermissionError as e:raise HTTPException(403,str(e))
@app.get('/',response_class=HTMLResponse,include_in_schema=False)
def home():
    return '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>InfraAgentKit</title><style>body{margin:0;background:#0d0d13;color:#f2f2f7;font-family:Inter,system-ui,-apple-system,"PingFang SC"}main{max-width:1100px;margin:auto;padding:40px 22px}.ey{color:#b59cff;font-size:12px;letter-spacing:.14em;font-weight:800}h1{font-size:44px;margin:8px 0}.sub{color:#aaa9bb;max-width:800px;line-height:1.7}.grid{display:grid;grid-template-columns:.9fr 1.1fr;gap:18px;margin-top:26px}.card{background:#151520;border:1px solid #2b2b3d;border-radius:18px;padding:20px}textarea{width:100%;min-height:140px;background:#0d0d15;border:1px solid #33334b;color:white;padding:14px;border-radius:12px}.btn{border:0;border-radius:10px;background:#7c5ce6;color:white;padding:11px 14px;font-weight:700;margin:10px 7px 0 0;cursor:pointer}.alt{background:#29283b}.flow{display:grid;grid-template-columns:repeat(6,1fr);gap:7px;margin:23px 0}.flow div{text-align:center;border:1px solid #303045;border-radius:11px;padding:10px;font-size:12px;color:#c9c5dd}pre{white-space:pre-wrap;max-height:500px;overflow:auto;background:#0b0b10;border-radius:12px;padding:14px;color:#d7d3ee;font-size:12px}@media(max-width:800px){.grid{grid-template-columns:1fr}.flow{grid-template-columns:repeat(2,1fr)}} </style></head><body><main><div class="ey">OPEN GOVERNED AGENT FRAMEWORK · MCP READY</div><h1>InfraAgentKit</h1><p class="sub">交通基础设施智能体技能、工具与 MCP 开源框架。Agent Card 定义权限，Tool Registry 定义能力，Evidence Contract 约束结论，Human Gate 控制副作用，Execution Receipt 与 Verifier 证明动作真实发生。</p><div class="flow"><div>Agent Card</div><div>Tools</div><div>Evidence</div><div>Human Gate</div><div>Receipt</div><div>Verifier</div></div><div class="grid"><section class="card"><h2>运行一个受治理 Agent</h2><textarea id="m">Worker near unprotected edge at Pier P47. Draft a controlled response.</textarea><button class="btn" onclick="run()">Run</button><button class="btn alt" onclick="approve()">Approve + Execute</button><p id="hint" class="sub"></p></section><section class="card"><h2>Runtime Trace</h2><pre id="o">Ready.</pre></section></div></main><script>let action=null;let runid=null;async function run(){let x=await (await fetch('/runs',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({message:document.getElementById('m').value,agent_ids:['hse-agent']})})).json();runid=x.run_id;action=x.actions[0]?.id||null;document.getElementById('o').textContent=JSON.stringify(x,null,2);document.getElementById('hint').textContent=action?'Side effect is blocked until human approval: '+action:'No side-effect action created.'}async function approve(){if(!action)return;await fetch('/actions/'+action+'/approve',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({actor:'demo_project_manager'})});let x=await (await fetch('/actions/'+action+'/execute',{method:'POST'})).json();document.getElementById('o').textContent=JSON.stringify(x,null,2)}</script></body></html>'''
