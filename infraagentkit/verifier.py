"""Independent verification of findings and executions.

The verifier recomputes everything from stored data instead of trusting the
agent or the executor: every SUPPORTED finding must cite sources that its
own evidence-tool calls returned (whose recorded outputs still hash to the
recorded digests), and every execution must match an approved intent, the
tool it named and the exact arguments that were approved.
"""
from __future__ import annotations

import uuid

from .contracts import ActionIntent, ExecutionReceipt, VerificationReceipt
from .policy import Decision
from .tools import digest


def verify_findings(run: dict, evidence_tools: set[str]) -> dict:
    problems = []
    for call in run.get("tool_calls", []):
        if call.get("output") is not None and digest(call["output"]) != call.get("output_digest"):
            problems.append(f"tool output for {call['agent_id']}:{call['tool']} was altered")
    for finding in run.get("findings", []):
        returned = {
            hit["ref"]
            for call in run.get("tool_calls", [])
            if call["agent_id"] == finding["agent_id"] and call["tool"] in evidence_tools and call.get("output")
            for hit in call["output"].get("hits", [])
        }
        if finding["status"] == "SUPPORTED":
            if not finding["evidence_refs"]:
                problems.append(f"{finding['agent_id']}: SUPPORTED without evidence")
            missing = set(finding["evidence_refs"]) - returned
            if missing:
                problems.append(f"{finding['agent_id']}: cites sources its tools did not return: {sorted(missing)}")
    return {"passed": not problems, "problems": problems}


def verify_execution(action: ActionIntent, receipt: ExecutionReceipt, decision: Decision) -> VerificationReceipt:
    checks = {
        "policy_allowed_at_execution": decision.allowed,
        "approval_recorded": bool(action.approved_by) and action.approval_kind in {"human", "policy"},
        "human_approval_when_required": decision.approval != "human" or action.approval_kind == "human",
        "tool_matches_intent": receipt.tool == action.tool,
        "input_matches_approved_arguments": receipt.input_digest == digest(action.arguments),
        "output_digest_valid": receipt.output_digest == digest(receipt.output),
        "execution_succeeded": receipt.status == "SUCCEEDED",
        # A write tool must not have delivered anything outside the system.
        "delivery_matches_side_effect": not receipt.output.get("external_delivery_performed") or action.side_effect == "external",
    }
    passed = all(checks.values())
    return VerificationReceipt(id="VER-" + uuid.uuid4().hex[:10].upper(), action_id=action.id, passed=passed, checks=checks,
                               detail="independent contract verification" if passed else "verification failed: "
                               + ", ".join(k for k, v in checks.items() if not v))
