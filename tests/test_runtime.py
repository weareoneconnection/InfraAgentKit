import sqlite3
import threading

import pytest

from infraagentkit import ConflictError, GovernanceError

from conftest import EDGE


def test_supported_finding_cites_retrieved_sources_and_proposes_an_intent(runtime):
    run = runtime.run(EDGE)
    assert run["agents"] == ["hse-agent"]
    finding = run["findings"][0]
    assert finding["status"] == "SUPPORTED" and "HSE-WAH-001" in finding["evidence_refs"] and finding["risk"] == "HIGH"
    assert run["finding_verification"]["passed"]
    assert [a["status"] for a in run["actions"]] == ["AWAITING_APPROVAL"]
    assert all(c["output_digest"] for c in run["tool_calls"])


def test_no_evidence_means_gap_and_no_side_effects(runtime):
    run = runtime.run("I have no knowledge of this site, just saying hello")
    assert run["findings"][0]["status"] == "GAP" and run["findings"][0]["questions"]
    assert run["actions"] == []


def test_human_gate_receipt_and_verification(runtime):
    aid = runtime.run(EDGE, ["hse-agent"])["actions"][0]["id"]
    with pytest.raises(GovernanceError):
        runtime.execute(aid)
    runtime.approve(aid, "项目经理 张工")
    result = runtime.execute(aid)
    assert result["action"]["status"] == "EXECUTED"
    assert result["verification_receipt"]["passed"] and all(result["verification_receipt"]["checks"].values())
    assert result["execution_receipt"]["output"]["delivery_status"] == "DRAFT_ONLY_NOT_SENT"
    run = runtime.store.get_run(result["action"]["run_id"])
    assert {r["kind"] for r in run["receipts"]} == {"execution", "verification"}


@pytest.mark.parametrize("actor", ["agent:hse-agent", "policy:x", "model:qwen", "runtime", " "])
def test_only_named_humans_can_approve(runtime, actor):
    aid = runtime.run(EDGE, ["hse-agent"])["actions"][0]["id"]
    with pytest.raises(GovernanceError):
        runtime.approve(aid, actor)


def test_rejected_action_cannot_run(runtime):
    aid = runtime.run(EDGE, ["hse-agent"])["actions"][0]["id"]
    runtime.reject(aid, "HSE 经理 李工", "use the site template")
    with pytest.raises(GovernanceError):
        runtime.execute(aid)


def test_concurrent_execution_runs_once(runtime):
    aid = runtime.run(EDGE, ["hse-agent"])["actions"][0]["id"]
    runtime.approve(aid, "项目经理 张工")
    outcomes = []

    def go():
        try:
            runtime.execute(aid)
            outcomes.append("ok")
        except (ConflictError, GovernanceError):
            outcomes.append("blocked")

    threads = [threading.Thread(target=go) for _ in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert outcomes.count("ok") == 1
    with sqlite3.connect(runtime.store.path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM receipts WHERE kind='execution'").fetchone()[0] == 1


def test_operator_policy_approval_is_recorded_and_verified(runtime):
    run = runtime.run("Bridge bearing displacement and corrosion above the alert threshold at BRG-03")
    action = run["actions"][0]
    assert run["agents"] == ["asset-agent"] and action["approval_kind"] == "policy"
    assert action["approved_by"].startswith("policy:asset-agent@")
    assert runtime.execute(action["id"])["verification_receipt"]["passed"]


def test_external_side_effects_always_need_a_human(runtime):
    run = runtime.run("Mobile crane lifting at station S12 tomorrow; crane certificate expired", ["plant-agent"])
    ext = next(a for a in run["actions"] if a["tool"] == "notification.send")
    assert ext["status"] == "AWAITING_APPROVAL" and ext["side_effect"] == "external"


def test_ledger_detects_tampering(runtime):
    aid = runtime.run(EDGE, ["hse-agent"])["actions"][0]["id"]
    runtime.approve(aid, "项目经理 张工")
    runtime.execute(aid)
    assert runtime.audit()["valid"]
    with sqlite3.connect(runtime.store.path) as conn:
        conn.execute("DELETE FROM ledger WHERE kind='action.approved'")
    assert not runtime.audit()["valid"]


class Hostile:
    def __init__(self, plan=None, finding=None):
        self.plan, self.finding = plan, finding

    def complete_json(self, system, user, schema):
        assert "<data>" in user  # untrusted input is always fenced
        return self.plan if schema["title"] == "tool_plan" else self.finding


def test_model_cannot_cite_unretrieved_sources_or_plan_side_effects(runtime):
    runtime.model = Hostile(plan={"calls": [{"tool": "document.draft", "arguments_json": "{}"}]},
                            finding={"claim": "fine", "evidence_refs": ["MADE-UP"], "gaps": [], "questions": []})
    run = runtime.run(EDGE, ["hse-agent"])
    assert all(c["planned_by"] == "rules" for c in run["tool_calls"])
    assert run["findings"][0]["composed_by"] == "rules" and "MADE-UP" not in run["findings"][0]["evidence_refs"]


def test_valid_model_finding_is_used(runtime):
    runtime.model = Hostile(finding={"claim": "Stop work at P47 until edge protection is verified.",
                                     "evidence_refs": ["HSE-WAH-001"], "gaps": [], "questions": ["Is a rescue plan in place?"]})
    finding = runtime.run(EDGE, ["hse-agent"])["findings"][0]
    assert finding["composed_by"] == "model" and finding["evidence_refs"] == ["HSE-WAH-001"]
