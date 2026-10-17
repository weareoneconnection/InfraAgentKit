from __future__ import annotations
import uuid
from pathlib import Path
from .cards import AgentCard,load_card
from .contracts import Finding,ActionIntent,ExecutionReceipt
from .tools import ToolRegistry,default_registry,digest
from .policy import PolicyEngine
from .verifier import verify_execution
from . import state

class GovernedRuntime:
    def __init__(self,cards:list[AgentCard]|None=None,registry:ToolRegistry|None=None):
        self.registry=registry or default_registry();self.policy=PolicyEngine();self.cards={c.id:c for c in (cards or [])}
    @classmethod
    def from_directory(cls,path:str|Path):
        cards=[load_card(p) for p in Path(path).glob('*.yaml')];return cls(cards)
    def run(self,message:str,agent_ids:list[str])->dict:
        run_id='RUN-'+uuid.uuid4().hex[:10].upper();findings=[];actions=[];tool_trace=[]
        for aid in agent_ids:
            if aid not in self.cards:raise KeyError(f'unknown agent {aid}')
            card=self.cards[aid];calls=0
            # common grounded analysis path: risk + knowledge when declared
            risk=None;hits=[]
            if 'risk.assess' in card.tools and calls<card.limits.get('max_tool_calls',8):
                risk=self.registry.call('risk.assess',text=message);tool_trace.append({'agent_id':aid,'tool':'risk.assess','output':risk});calls+=1
            if 'knowledge.search' in card.tools and calls<card.limits.get('max_tool_calls',8):
                k=self.registry.call('knowledge.search',query=message);hits=k.get('hits',[]);tool_trace.append({'agent_id':aid,'tool':'knowledge.search','output':k});calls+=1
            refs=[h['ref'] for h in hits]
            min_sources=int(card.evidence.get('minimum_confident_sources',1))
            status='SUPPORTED' if len(refs)>=min_sources else 'GAP'
            claim=f"{card.name}: risk {risk['risk'] if risk else 'not-assessed'}; {len(refs)} governed evidence source(s)."
            findings.append(Finding(agent_id=aid,claim=claim,status=status,evidence_refs=refs,confidence=0.88 if status=='SUPPORTED' else 0.35,gaps=[] if status=='SUPPORTED' else ['insufficient governed evidence']).model_dump())
            # side-effect proposal is an intent, never implicit execution
            if status=='SUPPORTED' and 'document.draft' in card.tools:
                spec=self.registry.get('document.draft');pd=self.policy.decide(card,spec)
                if pd.allowed:
                    a=ActionIntent(id='ACT-'+uuid.uuid4().hex[:10].upper(),run_id=run_id,tool=spec.name,arguments={'title':f'{card.name} response draft','body':claim+' Evidence: '+', '.join(refs)},side_effect=spec.side_effect,status='AWAITING_APPROVAL' if pd.approval_required else 'APPROVED')
                    state.save_action(a);actions.append(a.model_dump())
        payload={'run_id':run_id,'message':message,'agents':agent_ids,'findings':findings,'tool_trace':tool_trace,'actions':actions,'governance':{'model_or_agent_cannot_self_approve':True,'unsupported_findings_do_not_trigger_actions':True}}
        state.save_run(run_id,message,'AWAITING_APPROVAL' if actions else 'ANALYZED',payload);return payload
    def approve(self,action_id:str,actor:str)->dict:
        row=state.get_action(action_id)
        if not row:raise KeyError(action_id)
        if row['status']!='AWAITING_APPROVAL':raise ValueError('action is not awaiting approval')
        state.update_action(action_id,'APPROVED',actor);return state.get_action(action_id)
    def execute(self,action_id:str)->dict:
        row=state.get_action(action_id)
        if not row:raise KeyError(action_id)
        if row['status']!='APPROVED':raise PermissionError('human approval required')
        import json
        args=json.loads(row['args']);spec=self.registry.get(row['tool']);out=self.registry.call(spec.name,**args)
        receipt=ExecutionReceipt(id='RCP-'+uuid.uuid4().hex[:10].upper(),action_id=action_id,tool=spec.name,status='SUCCEEDED',input_digest=digest(args),output_digest=digest(out),output=out)
        action=ActionIntent(id=row['id'],run_id=row['run_id'],tool=row['tool'],arguments=args,side_effect=row['side_effect'],status='APPROVED',approved_by=row['approved_by'])
        verification=verify_execution(action,receipt,approved=bool(row['approved_by']))
        state.save_receipt(receipt.id,action_id,'execution',receipt.status,receipt.model_dump())
        state.save_receipt(verification.id,action_id,'verification','PASSED' if verification.passed else 'FAILED',verification.model_dump())
        state.update_action(action_id,'EXECUTED' if verification.passed else 'BLOCKED')
        return {'execution_receipt':receipt.model_dump(),'verification_receipt':verification.model_dump()}
