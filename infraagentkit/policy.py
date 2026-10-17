"""Policy engine: default deny, evaluated at proposal time and again at execution.

Rules, in order:

1. A tool the card does not declare is denied.
2. Read-only tools may run during analysis without approval.
3. Side-effect tools never run during analysis; they become action intents.
4. External side effects always need a human. Writes need a human unless an
   *operator* card lists the tool in ``human_gate.exempt_tools``; the
   approval is then recorded as a policy approval naming the card.
5. At execution the decision is re-evaluated against the card version that
   proposed the action; a changed card or a missing approval blocks it.
"""
from __future__ import annotations

from dataclasses import dataclass

from .cards import AgentCard
from .contracts import ActionIntent
from .tools import ToolSpec


@dataclass(frozen=True)
class Decision:
    allowed: bool
    approval: str  # "none" | "human" | "policy"
    reason: str


def for_analysis(card: AgentCard, tool: ToolSpec) -> Decision:
    if tool.name not in card.tools:
        return Decision(False, "none", "tool not declared in the Agent Card")
    if tool.side_effect != "read_only":
        return Decision(False, "none", "side-effect tools never run during analysis")
    return Decision(True, "none", "read-only tool declared in the card")


def for_proposal(card: AgentCard, tool: ToolSpec) -> Decision:
    if tool.name not in card.tools:
        return Decision(False, "none", "tool not declared in the Agent Card")
    if tool.side_effect == "read_only":
        return Decision(False, "none", "read-only tools are not actions")
    if tool.side_effect == "external":
        return Decision(True, "human", "external side effects always need a human")
    if (card.authority == "operator" and tool.name in card.human_gate.exempt_tools
            and "write" not in card.human_gate.required_for):
        return Decision(True, "policy", f"operator card {card.id} exempts {tool.name}")
    return Decision(True, "human", "write side effects need a human")


def for_execution(card: AgentCard | None, tool: ToolSpec, action: ActionIntent) -> Decision:
    if card is None:
        return Decision(False, "none", "proposing agent is no longer registered")
    if card.fingerprint() != action.card_fingerprint:
        return Decision(False, "none", "agent card changed since the action was proposed")
    proposal = for_proposal(card, tool)
    if not proposal.allowed:
        return proposal
    if action.status != "APPROVED" or not action.approved_by:
        return Decision(False, "none", "action is not approved")
    if proposal.approval == "human" and action.approval_kind != "human":
        return Decision(False, "none", "a human approval is required")
    return Decision(True, action.approval_kind or "none", "approved under the current card")
