from __future__ import annotations
from dataclasses import dataclass
from .cards import AgentCard
from .tools import ToolSpec

@dataclass
class PolicyDecision:
    allowed:bool
    approval_required:bool
    reason:str

class PolicyEngine:
    def decide(self,card:AgentCard,tool:ToolSpec)->PolicyDecision:
        if tool.name not in card.tools:return PolicyDecision(False,False,'tool not declared in Agent Card')
        if card.authority not in {'advisory','operator'}:return PolicyDecision(False,False,'unknown authority')
        if tool.side_effect=='read_only':return PolicyDecision(True,False,'read-only tool')
        if card.authority=='advisory':return PolicyDecision(True,True,'advisory agents require human approval for side effects')
        required=set(card.human_gate.get('required_for',[]))
        return PolicyDecision(True,tool.side_effect in required or 'external_action' in required and tool.side_effect=='external','Agent Card human gate')
