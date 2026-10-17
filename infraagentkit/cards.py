from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel,Field
import yaml

class AgentCard(BaseModel):
    id:str
    version:str='1.0.0'
    name:str
    scope:dict=Field(default_factory=dict)
    authority:str='advisory'
    tools:list[str]=Field(default_factory=list)
    evidence:dict=Field(default_factory=lambda:{'minimum_confident_sources':1,'unsupported_policy':'escalate'})
    human_gate:dict=Field(default_factory=lambda:{'required_for':['external_action','write']})
    limits:dict=Field(default_factory=lambda:{'max_tool_calls':8,'max_runtime_seconds':120})
    instructions:str=''

def load_card(path:str|Path)->AgentCard:
    return AgentCard.model_validate(yaml.safe_load(Path(path).read_text(encoding='utf-8')))
