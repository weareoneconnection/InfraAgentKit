"""Agent Card: the declarative contract of an agent.

A card is data, not a prompt. It states what the agent is for, which tools
it may call, how much evidence a conclusion needs, which side effects it may
propose and which of those a human must approve. Cards are validated
strictly (unknown keys are errors) and linted against a tool registry, so a
typo in a tool name fails at load time instead of silently disabling a
control.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .tools import ToolRegistry


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Scope(_Strict):
    domain: str
    lifecycle: list[str] = Field(default_factory=list)
    jurisdictions: list[str] = Field(default_factory=list)


class EvidencePolicy(_Strict):
    minimum_sources: int = Field(default=1, ge=1, le=5)
    domains: list[str] = Field(default_factory=list, description="Only sources from these domains count; empty = any.")
    unsupported_policy: Literal["gap", "escalate"] = "escalate"


class HumanGate(_Strict):
    required_for: list[Literal["write", "external"]] = Field(default_factory=lambda: ["write", "external"])
    exempt_tools: list[str] = Field(default_factory=list, description="Operator cards only: tools that run on policy approval.")


class Limits(_Strict):
    max_tool_calls: int = Field(default=6, ge=1, le=50)
    max_runtime_seconds: int = Field(default=60, ge=1, le=900)


class ProposedAction(_Strict):
    tool: str
    when: Literal["supported", "always"] = "supported"
    title: str = "{agent} response draft"


class AgentCard(_Strict):
    id: str
    version: str = "1.0.0"
    name: str
    description: str = ""
    scope: Scope
    authority: Literal["advisory", "operator"] = "advisory"
    tools: list[str]
    evidence: EvidencePolicy = Field(default_factory=EvidencePolicy)
    human_gate: HumanGate = Field(default_factory=HumanGate)
    limits: Limits = Field(default_factory=Limits)
    actions: list[ProposedAction] = Field(default_factory=list)
    instructions: str = ""

    @field_validator("id")
    @classmethod
    def _slug(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,48}", value):
            raise ValueError("id must be a lowercase slug, e.g. hse-agent")
        return value

    def fingerprint(self) -> str:
        from .tools import digest
        return digest(self.model_dump())[:16]


def lint(card: AgentCard, registry: ToolRegistry) -> list[str]:
    """Contract problems that would make the card unsafe or ineffective."""
    issues = []
    for tool in card.tools:
        if tool not in registry:
            issues.append(f"{card.id}: tool '{tool}' is not registered")
    for action in card.actions:
        if action.tool not in card.tools:
            issues.append(f"{card.id}: proposed action '{action.tool}' is not in the card's tools")
        elif action.tool in registry and registry.get(action.tool).side_effect == "read_only":
            issues.append(f"{card.id}: proposed action '{action.tool}' is read-only; actions are for side effects")
    if card.human_gate.exempt_tools and card.authority != "operator":
        issues.append(f"{card.id}: only operator cards may exempt tools from the human gate")
    for tool in card.human_gate.exempt_tools:
        if tool in registry and registry.get(tool).side_effect == "external":
            issues.append(f"{card.id}: external tool '{tool}' can never be exempt from the human gate")
    if not any(t in registry and registry.get(t).evidence_output for t in card.tools):
        issues.append(f"{card.id}: no evidence-producing tool, so no finding can ever be SUPPORTED")
    return issues


def load_card(path: str | Path) -> AgentCard:
    return AgentCard.model_validate(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def load_cards(directory: str | Path) -> list[AgentCard]:
    cards = [load_card(p) for p in sorted(Path(directory).glob("*.yaml"))]
    ids = [c.id for c in cards]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate agent ids")
    return cards
