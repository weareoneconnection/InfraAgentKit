"""Runtime API and web console."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from . import __version__
from .cards import AgentCard
from .runtime import ConflictError, GovernanceError, GovernedRuntime

BASE = Path(__file__).resolve().parent
AGENTS_DIR = Path(os.getenv("INFRAAGENTKIT_AGENTS", BASE.parent / "examples" / "agents"))

runtime = GovernedRuntime.from_directory(AGENTS_DIR)
app = FastAPI(title="InfraAgentKit Runtime", version=__version__,
              description="Governed agents: Agent Card → tools → evidence → human gate → receipt → verifier")


class RunIn(BaseModel):
    message: str = Field(min_length=3, max_length=8000)
    agent_ids: list[str] | None = None


class Decision(BaseModel):
    actor: str = Field(min_length=2, max_length=120)
    reason: str = Field(default="", max_length=500)


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
    return {"status": "ok", "product": "InfraAgentKit", "version": __version__, "agents": len(runtime.cards),
            "model": "configured" if runtime.model else "deterministic", "ledger": runtime.audit()["valid"]}


@app.get("/agents")
def agents():
    return [{**c.model_dump(), "fingerprint": c.fingerprint()} for c in runtime.cards.values()]


@app.get("/tools")
def tools():
    return runtime.registry.describe()


@app.get("/schema/agent-card")
def card_schema():
    return AgentCard.model_json_schema()


@app.post("/runs", status_code=201)
def create_run(payload: RunIn):
    try:
        return runtime.run(payload.message, payload.agent_ids)
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
def approve(action_id: str, payload: Decision):
    return _errors(runtime.approve, action_id, payload.actor)


@app.post("/actions/{action_id}/reject")
def reject(action_id: str, payload: Decision):
    return _errors(runtime.reject, action_id, payload.actor, payload.reason)


@app.post("/actions/{action_id}/execute")
def execute(action_id: str):
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
