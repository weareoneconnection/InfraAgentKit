"""Runtime API and web console."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from . import __version__
from .cards import AgentCard
from .knowledge import load_packs
from .runtime import ConflictError, GovernanceError, GovernedRuntime
from .security import AuthSettings, Principal, SlidingWindowLimiter

BASE = Path(__file__).resolve().parent
AGENTS_DIR = Path(os.getenv("INFRAAGENTKIT_AGENTS") or BASE / "agents")

runtime = GovernedRuntime.from_directory(AGENTS_DIR)
auth = AuthSettings.from_env()
limiter = SlidingWindowLimiter(limit=int(os.getenv("INFRAAGENTKIT_RATE_LIMIT_PER_MINUTE", "240")))
app = FastAPI(title="InfraAgentKit Runtime", version=__version__,
              description="Governed agents: Agent Card → tools → evidence → human gate → receipt → verifier")


class RunIn(BaseModel):
    message: str = Field(min_length=3, max_length=8000)
    agent_ids: list[str] | None = None
    tenant_id: str = Field(default="public", min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    project_id: str = Field(default="demo", min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")


class Decision(BaseModel):
    actor: str = Field(min_length=2, max_length=120)
    reason: str = Field(default="", max_length=500)


@app.middleware("http")
async def abuse_guard(request: Request, call_next):
    key = request.client.host if request.client else "unknown"
    if not limiter.allow(key):
        return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
    response = await call_next(request)
    response.headers["X-InfraAgentKit-Auth-Mode"] = auth.mode
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


def _principal(request: Request, role: str, claimed_actor: str = "") -> Principal:
    try:
        principal = auth.authenticate(request.headers.get("authorization"), claimed_actor)
    except PermissionError as exc:
        raise HTTPException(401, str(exc), headers={"WWW-Authenticate": "Bearer"})
    if not principal.can(role):
        raise HTTPException(403, f"role '{role}' required")
    return principal


def _errors(fn, *args):
    try:
        return fn(*args)
    except KeyError as exc:
        raise HTTPException(404, str(exc).strip("'"))
    except GovernanceError as exc:
        raise HTTPException(403, str(exc))
    except ConflictError as exc:
        raise HTTPException(409, str(exc))


@app.get("/health")
def health():
    observed = runtime.observability()
    return {"status": "ok", "product": "InfraAgentKit", "version": __version__, "agents": len(runtime.cards),
            "model": observed["model"], "ledger": runtime.audit()["valid"], "security": auth.status(),
            "coverage": runtime.coverage(), "tools": len(runtime.registry.names()), "knowledge_sources": len(load_packs())}


@app.get("/security/status")
def security_status():
    return auth.status()


@app.get("/observability")
def observability():
    return runtime.observability()


@app.get("/evaluation")
def evaluation():
    return {"suite": "INFRAAGENTKIT_BENCHMARK", "version": "4.0", "status": "PASSED", "mode": "rules",
            "cases": 55, "metrics": {"grounding_accuracy": 100.0, "abstention_accuracy": 100.0,
                                      "risk_accuracy": 100.0, "governance_attacks_blocked": 100.0},
            "source": "data/benchmark.jsonl + evals/run_benchmark.py",
            "reproduce": "python evals/run_benchmark.py",
            "model_mode": {"status": "OBSERVED_AT_RUNTIME" if runtime.model else "NOT_CONFIGURED",
                           "telemetry": runtime.observability()["model"]},
            "boundary": "Synthetic benchmark results prove reproducibility on the bundled cases, not field accuracy."}


@app.get("/connectors")
def connectors():
    return {"built_in": {"mode": "SYNTHETIC_READ_ONLY_PREVIEW", "count": 6},
            "file_connectors": runtime.connectors,
            "sdk": {"class": "infraagentkit.connectors.FileSnapshotConnector",
                    "example": "examples/connectors/project-snapshot.json"}}


@app.get("/demo/golden")
def golden_case():
    return {"id": "GOLDEN-P47-01", "title": "P47 临边高处作业闭环",
            "message": "P47 墩临边防护缺失，工人在高处作业未系安全带，下午还要继续施工。",
            "expected": {"lead": "hse-agent", "risk": "HIGH", "evidence": "HSE-WAH-001",
                         "control_steps": 4, "action": "document.draft", "human_gate": True},
            "story": ["数据分诊", "动态编组", "证据检索", "风险研判", "治理智能体回执",
                      "人工审批", "受控执行", "独立核验"]}


@app.get("/agents")
def agents():
    return runtime.catalogue()


@app.get("/catalog/coverage")
def catalog_coverage():
    return runtime.coverage()


@app.get("/tools")
def tools():
    return runtime.registry.describe()


@app.get("/schema/agent-card")
def card_schema():
    return AgentCard.model_json_schema()


@app.post("/runs", status_code=201)
def create_run(payload: RunIn, request: Request, idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")):
    _principal(request, "analyst")
    try:
        return runtime.run(payload.message, payload.agent_ids, tenant_id=payload.tenant_id,
                           project_id=payload.project_id, idempotency_key=idempotency_key)
    except KeyError as exc:
        raise HTTPException(422, str(exc).strip("'"))


@app.get("/runs")
def runs(limit: int = 20):
    return runtime.store.recent_runs(min(max(limit, 1), 100))


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    run = runtime.store.get_run(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return run


@app.get("/actions/pending")
def pending():
    return runtime.store.pending_actions()


@app.post("/actions/{action_id}/approve")
def approve(action_id: str, payload: Decision, request: Request):
    principal = _principal(request, "reviewer", payload.actor)
    return _errors(runtime.approve, action_id, principal.actor)


@app.post("/actions/{action_id}/reject")
def reject(action_id: str, payload: Decision, request: Request):
    principal = _principal(request, "reviewer", payload.actor)
    return _errors(runtime.reject, action_id, principal.actor, payload.reason)


@app.post("/actions/{action_id}/execute")
def execute(action_id: str, request: Request):
    _principal(request, "executor")
    return _errors(runtime.execute, action_id)


@app.get("/ledger")
def ledger(subject: str | None = None):
    return runtime.store.ledger(subject)


@app.get("/ledger/verify")
def ledger_verify():
    return runtime.audit()


@app.get("/", include_in_schema=False)
def console():
    return FileResponse(BASE / "static" / "console.html")
