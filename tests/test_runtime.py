import os,tempfile
os.environ['INFRAAGENTKIT_DB']=tempfile.mktemp(suffix='.db')
from pathlib import Path
import pytest
from infraagentkit.runtime import GovernedRuntime
BASE=Path(__file__).resolve().parent.parent

def test_evidence_and_human_gate():
    rt=GovernedRuntime.from_directory(BASE/'examples/agents')
    x=rt.run('Worker near unprotected edge at P47',['hse-agent'])
    assert x['findings'][0]['status']=='SUPPORTED' and x['findings'][0]['evidence_refs']
    aid=x['actions'][0]['id']
    with pytest.raises(PermissionError):rt.execute(aid)
    rt.approve(aid,'project_manager');result=rt.execute(aid)
    assert result['verification_receipt']['passed'] is True
    assert result['execution_receipt']['output']['external_delivery_performed'] is False

def test_unknown_tool_not_in_card_cannot_be_used():
    rt=GovernedRuntime.from_directory(BASE/'examples/agents')
    card=rt.cards['hse-agent'];spec=rt.registry.get('notification.send')
    assert rt.policy.decide(card,spec).allowed is False
