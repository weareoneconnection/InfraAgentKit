"""Wire contracts shared by the runtime, API, MCP server and verifier."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    agent_id: str
    tool: str
    arguments: dict[str, Any]
    output: dict[str, Any] | None = None
    output_digest: str = ""
    planned_by: Literal["rules", "model"] = "rules"
    error: str | None = None


class Finding(BaseModel):
    agent_id: str
    claim: str
    status: Literal["SUPPORTED", "GAP"]
    evidence_refs: list[str] = Field(default_factory=list)
    risk: str = "LOW"
    confidence: float = Field(ge=0, le=1)
    gaps: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    composed_by: Literal["rules", "model"] = "rules"


ActionStatus = Literal["AWAITING_APPROVAL", "APPROVED", "REJECTED", "EXECUTING", "EXECUTED", "FAILED"]


class ActionIntent(BaseModel):
    id: str
    run_id: str
    agent_id: str
    card_fingerprint: str
    tool: str
    arguments: dict[str, Any]
    side_effect: Literal["write", "external"]
    status: ActionStatus = "AWAITING_APPROVAL"
    approved_by: str | None = None
    approval_kind: Literal["human", "policy"] | None = None
    reason: str = ""


class ExecutionReceipt(BaseModel):
    id: str
    action_id: str
    tool: str
    status: Literal["SUCCEEDED", "FAILED"]
    input_digest: str
    output_digest: str
    output: dict[str, Any]


class VerificationReceipt(BaseModel):
    id: str
    action_id: str
    passed: bool
    checks: dict[str, bool]
    detail: str
