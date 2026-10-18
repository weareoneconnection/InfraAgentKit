import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from conftest import EDGE
from infraagentkit.connectors import FileSnapshotConnector
from infraagentkit.security import AuthSettings
from infraagentkit.tools import default_registry


def test_control_and_assurance_agents_emit_distinct_receipts(runtime):
    run = runtime.run(EDGE)
    steps = run["platform_steps"]
    assert [step["agent_id"] for step in steps] == [
        "data-intake-triage-agent", "project-orchestrator-agent",
        "evidence-provenance-agent", "independent-verifier-agent",
    ]
    assert all(step["output_digest"] and step["card_fingerprint"] for step in steps)
    assert all(step["status"] == "PASSED" for step in steps)
    with sqlite3.connect(runtime.store.path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM ledger WHERE kind='agent.step'").fetchone()[0] == 4


def test_context_agents_join_and_run_when_signalled(runtime):
    run = runtime.run("Malaysia permit check for IFC P47 and IoT sensor digital twin", ["engineering-agent"])
    ids = {step["agent_id"] for step in run["platform_steps"]}
    assert {"country-localization-agent", "digital-twin-spatial-agent"} <= ids


def test_idempotency_is_scoped_and_does_not_duplicate_actions(runtime):
    first = runtime.run(EDGE, tenant_id="acme", project_id="rail-a", idempotency_key="case-001")
    second = runtime.run(EDGE, tenant_id="acme", project_id="rail-a", idempotency_key="case-001")
    assert second["run_id"] == first["run_id"] and second["idempotent_replay"]
    assert second["actions"] == first["actions"]
    third = runtime.run(EDGE, tenant_id="acme", project_id="rail-b", idempotency_key="case-001")
    assert third["run_id"] != first["run_id"]


def test_file_connector_registers_typed_read_only_tool():
    connector = FileSnapshotConnector("examples/connectors/project-snapshot.json")
    registry = default_registry()
    assert connector.register(registry) == ["snapshot.asset_lookup"]
    schema = registry.get("snapshot.asset_lookup").parameters
    assert schema["required"] == ["asset_id"]
    out = registry.call("snapshot.asset_lookup", {"asset_id": "P47"})
    assert out["mode"] == "FILE_SNAPSHOT" and out["records"][0]["asset_id"] == "P47" and len(out["source_digest"]) == 64


def test_token_rbac_uses_bound_actor_and_roles(monkeypatch):
    raw = {"x" * 24: {"actor": "Reviewer Li", "roles": ["reviewer"]}}
    monkeypatch.setenv("INFRAAGENTKIT_API_TOKENS", json.dumps(raw))
    auth = AuthSettings.from_env()
    principal = auth.authenticate("Bearer " + "x" * 24, "Ignored Actor")
    assert principal.actor == "Reviewer Li" and principal.can("reviewer") and not principal.can("executor")
    with pytest.raises(PermissionError):
        auth.authenticate("Bearer wrong")


def test_stage13_read_only_endpoints():
    from infraagentkit.web import app
    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["version"] == "4.0.0" and "security" in health and isinstance(health["model"], dict)
        assert client.get("/security/status").json()["mode"] in {"demo-unverified", "token-rbac"}
        assert client.get("/evaluation").json()["cases"] == 55
        assert client.get("/demo/golden").json()["expected"]["lead"] == "hse-agent"
        assert client.get("/connectors").json()["sdk"]["class"].endswith("FileSnapshotConnector")
        assert "runtime" in client.get("/observability").json()
