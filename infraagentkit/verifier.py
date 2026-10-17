from __future__ import annotations
import uuid
from .contracts import ExecutionReceipt,VerificationReceipt
from .tools import digest

def verify_execution(action,receipt:ExecutionReceipt,approved:bool)->VerificationReceipt:
    checks={
        'approval_valid': approved or action.side_effect=='read_only',
        'tool_matches': receipt.tool==action.tool,
        'input_digest_matches': receipt.input_digest==digest(action.arguments),
        'output_digest_valid': receipt.output_digest==digest(receipt.output),
        'execution_succeeded': receipt.status=='SUCCEEDED',
    }
    return VerificationReceipt(id='VER-'+uuid.uuid4().hex[:10].upper(),action_id=action.id,passed=all(checks.values()),checks=checks,detail='independent contract verification')
