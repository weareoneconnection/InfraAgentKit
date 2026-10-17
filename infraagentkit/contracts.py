from __future__ import annotations
from typing import Any,Literal
from pydantic import BaseModel,Field

class EvidenceRef(BaseModel):
    ref:str
    title:str=''
    source_type:str='tool'
    digest:str=''

class Finding(BaseModel):
    agent_id:str
    claim:str
    status:Literal['SUPPORTED','GAP','CONFLICT']
    evidence_refs:list[str]=Field(default_factory=list)
    confidence:float=Field(ge=0,le=1)
    gaps:list[str]=Field(default_factory=list)

class ActionIntent(BaseModel):
    id:str
    run_id:str
    tool:str
    arguments:dict[str,Any]
    side_effect:Literal['read_only','write','external']
    status:Literal['AWAITING_APPROVAL','APPROVED','EXECUTED','BLOCKED']='AWAITING_APPROVAL'
    approved_by:str|None=None

class ExecutionReceipt(BaseModel):
    id:str
    action_id:str
    tool:str
    status:Literal['SUCCEEDED','FAILED']
    input_digest:str
    output_digest:str
    output:dict[str,Any]

class VerificationReceipt(BaseModel):
    id:str
    action_id:str
    passed:bool
    checks:dict[str,bool]
    detail:str

class RunRequest(BaseModel):
    message:str=Field(min_length=3,max_length=8000)
    agent_ids:list[str]=Field(default_factory=lambda:['hse-agent'])
