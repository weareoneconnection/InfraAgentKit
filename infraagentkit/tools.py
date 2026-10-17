from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Callable,Literal
import hashlib,json

SideEffect=Literal['read_only','write','external']

@dataclass(frozen=True)
class ToolSpec:
    name:str
    description:str
    side_effect:SideEffect='read_only'
    evidence_output:bool=False
    fn:Callable[...,dict]|None=None

class ToolRegistry:
    def __init__(self):self._tools={}
    def register(self,spec:ToolSpec):
        if not spec.fn:raise ValueError('tool requires function')
        self._tools[spec.name]=spec;return spec
    def names(self):return sorted(self._tools)
    def get(self,name):
        if name not in self._tools:raise KeyError(name)
        return self._tools[name]
    def call(self,name,**kwargs):return self.get(name).fn(**kwargs)
    def describe(self):return [{'name':t.name,'description':t.description,'side_effect':t.side_effect,'evidence_output':t.evidence_output} for t in self._tools.values()]

def digest(value)->str:return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()

# Standard reference tools. Replace them with real project adapters without changing the runtime contract.
REFERENCE_KNOWLEDGE={
 'HSE-WAH-001':'Synthetic rule: work-at-height exposure requires controlled edge/fall protection before restart.',
 'QA-NCR-001':'Synthetic rule: a defect requires recorded inspection, corrective action and verification before closure.',
 'CONTRACT-VAR-001':'Synthetic rule: a variation should retain instruction, entitlement, valuation and time-impact evidence.',
}

def knowledge_search(query:str)->dict:
    q=query.lower();hits=[]
    domain_map=[
        ('HSE-WAH-001',['height','fall','edge','guardrail','hse','高处','临边','坠落']),
        ('QA-NCR-001',['crack','defect','ncr','inspection','quality','裂缝','缺陷','不符合','检验']),
        ('CONTRACT-VAR-001',['variation','claim','eot','contract','valuation','变更','索赔','合同','计价']),
    ]
    for ref,keys in domain_map:
        score=sum(1 for k in keys if k in q)
        if score:
            hits.append({'ref':ref,'text':REFERENCE_KNOWLEDGE[ref],'score':score})
    return {'query':query,'hits':sorted(hits,key=lambda x:x['score'],reverse=True)[:3]}

def risk_assess(text:str)->dict:
    t=text.lower();risk='LOW'
    if any(x in t for x in ['collapse','fatal','坍塌','死亡']):risk='CRITICAL'
    elif any(x in t for x in ['height','fall','edge','lifting','高处','临边','吊装']):risk='HIGH'
    elif any(x in t for x in ['crack','defect','裂缝','缺陷']):risk='MEDIUM'
    return {'risk':risk,'text':text}

def draft_document(title:str,body:str)->dict:
    return {'title':title,'body':body,'delivery_status':'DRAFT_ONLY_NOT_SENT','external_delivery_performed':False}

def external_notify(channel:str,message:str)->dict:
    # demo adapter never sends; in production replace with a connector behind the same approval gate.
    return {'channel':channel,'message':message,'status':'SIMULATED_NOT_SENT','external_delivery_performed':False}

def default_registry()->ToolRegistry:
    r=ToolRegistry()
    r.register(ToolSpec('knowledge.search','Search governed engineering knowledge',evidence_output=True,fn=knowledge_search))
    r.register(ToolSpec('risk.assess','Assess infrastructure event risk',fn=risk_assess))
    r.register(ToolSpec('document.draft','Create a governed draft document',side_effect='write',fn=draft_document))
    r.register(ToolSpec('notification.send','External notification adapter (simulated in demo)',side_effect='external',fn=external_notify))
    return r
