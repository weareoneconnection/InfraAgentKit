"""Governed runtime: route → plan → call read-only tools → finding → intents → human gate → execute → verify.

Reasoning authority and execution authority are separate. Analysis can only
call read-only tools the card declares; side effects come out of a run only
as :class:`ActionIntent` objects. Executing an intent re-checks policy
against the card that proposed it, runs exactly the approved arguments,
writes an execution receipt and an independent verification receipt, and
appends every step to the hash-chained ledger.
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path

from . import policy
from .cards import AgentCard, lint, load_cards
from .contracts import ActionIntent, ExecutionReceipt, ToolCall
from .llm import Model, from_env
from .reasoning import eligible_hits, model_finding, model_plan, rule_finding, rule_plan
from .store import Store
from .tools import ToolRegistry, default_registry, digest
from .verifier import verify_execution, verify_findings

HUMAN_PREFIXES_FORBIDDEN = ("agent:", "policy:", "model:", "runtime")
RISK_ORDER = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def higher(a: str, b: str) -> str:
    return max(a, b, key=lambda r: RISK_ORDER.index(r) if r in RISK_ORDER else 0)
ROUTE_RATIO = 0.6


class GovernanceError(PermissionError):
    """A request the governance rules do not allow."""


class ConflictError(RuntimeError):
    """The action already moved on (e.g. a concurrent execution)."""


class GovernedRuntime:
    def __init__(self, cards: list[AgentCard], registry: ToolRegistry | None = None, store: Store | None = None,
                 model: Model | None = None) -> None:
        self.registry = registry or default_registry()
        self.cards = {c.id: c for c in cards}
        self.store = store or Store()
        self.model = model
        problems = [issue for card in cards for issue in lint(card, self.registry)]
        if problems:
            raise ValueError("invalid agent cards: " + "; ".join(problems))

    @classmethod
    def from_directory(cls, path: str | Path, **kwargs) -> "GovernedRuntime":
        kwargs.setdefault("model", from_env())
        return cls(load_cards(path), **kwargs)

    # --- routing -------------------------------------------------------------------
    def route(self, message: str) -> list[str]:
        """Pick agents whose domain the message's governed evidence points to.

        A secondary domain joins only if its best source scores at least
        ``ROUTE_RATIO`` of the top source, so a passing mention does not
        convene another agent.
        """
        hits = self.registry.call("knowledge.search", {"query": message}).get("hits", []) if "knowledge.search" in self.registry else []
        best: dict[str, float] = {}
        for hit in hits:
            best[hit["domain"]] = max(best.get(hit["domain"], 0.0), hit["score"])
        top = max(best.values(), default=0.0)
        domains = [d for d, score in sorted(best.items(), key=lambda kv: -kv[1]) if score >= ROUTE_RATIO * top]
        chosen = []
        for domain in domains:
            chosen += [c.id for c in self.cards.values() if (c.scope.domain == domain or domain in c.evidence.domains) and c.id not in chosen]
        if chosen:
            return chosen[:3]
        # Nothing governed matched: one advisory agent answers, and it will report a GAP.
        advisory = sorted(c.id for c in self.cards.values() if c.authority == "advisory")
        return [advisory[0] if advisory else next(iter(self.cards))]

    # --- analysis --------------------------------------------------------------------
    def run(self, message: str, agent_ids: list[str] | None = None) -> dict:
        run_id = "RUN-" + uuid.uuid4().hex[:10].upper()
        routed = agent_ids is None
        agent_ids = agent_ids or self.route(message)
        unknown = [a for a in agent_ids if a not in self.cards]
        if unknown:
            raise KeyError(f"unknown agent(s): {unknown}")
        calls: list[ToolCall] = []
        findings, actions = [], []
        for aid in agent_ids:
            card = self.cards[aid]
            started = time.monotonic()
            # The rules plan always runs (the user's own words are always searched and assessed); a model plan can only
            # add calls, so a rewritten query can widen recall but never lose what the original message finds.
            planned = [(tool, args, "rules") for tool, args in rule_plan(card, self.registry, message)]
            if self.model is not None:
                for tool, args in model_plan(self.model, card, self.registry, message) or []:
                    if (tool, args) not in [(t, a) for t, a, _ in planned]:
                        planned.append((tool, args, "model"))
            outputs, risk = [], "LOW"
            for tool, args, planned_by in planned[: card.limits.max_tool_calls]:
                spec = self.registry.get(tool)
                decision = policy.for_analysis(card, spec)
                call = ToolCall(agent_id=aid, tool=tool, arguments=args, planned_by=planned_by)
                if not decision.allowed:
                    call.error = f"denied: {decision.reason}"
                elif time.monotonic() - started > card.limits.max_runtime_seconds:
                    call.error = "denied: runtime limit reached"
                else:
                    try:
                        call.output = self.registry.call(tool, args)
                        call.output_digest = digest(call.output)
                    except (ValueError, TypeError) as exc:
                        call.error = f"failed: {exc}"
                calls.append(call)
                if call.output is not None:
                    if spec.evidence_output:
                        outputs.append(call.output)
                    if tool == "risk.assess":
                        risk = higher(risk, call.output.get("risk", "LOW"))  # never lowered by a reworded assessment
            hits = eligible_hits(card, outputs)
            finding = (model_finding(self.model, card, message, risk, hits) if self.model is not None else None) \
                or rule_finding(card, message, risk, hits)
            findings.append(finding)
            actions.extend(self._propose(run_id, card, finding))
        payload = {
            "run_id": run_id, "message": message, "agents": agent_ids, "routed": routed,
            "tool_calls": [c.model_dump() for c in calls], "findings": [f.model_dump() for f in findings],
            "action_ids": [a.id for a in actions],
            "governance": {"analysis_tools": "read_only", "side_effects": "intents_only",
                           "self_approval": "forbidden", "unsupported_findings_trigger_actions": False},
        }
        evidence_tools = {t for t in self.registry.names() if self.registry.get(t).evidence_output}
        payload["finding_verification"] = verify_findings(payload, evidence_tools)
        self.store.save_run(run_id, message, "AWAITING_APPROVAL" if any(a.status == "AWAITING_APPROVAL" for a in actions) else "ANALYSED", payload)
        return self.store.get_run(run_id)

    def _propose(self, run_id: str, card: AgentCard, finding) -> list[ActionIntent]:
        out = []
        for proposed in card.actions:
            if proposed.when == "supported" and finding.status != "SUPPORTED":
                continue
            spec = self.registry.get(proposed.tool)
            decision = policy.for_proposal(card, spec)
            if not decision.allowed:
                continue
            citations = ", ".join(finding.evidence_refs) or "none"
            values = {"title": proposed.title.format(agent=card.name), "body": f"{finding.claim}\nEvidence: {citations}",
                      "message": f"{finding.claim} (evidence: {citations})", "channel": card.scope.domain, "text": finding.claim}
            args = {p: values[p] for p in spec.parameters["properties"] if p in values}
            action = ActionIntent(
                id="ACT-" + uuid.uuid4().hex[:10].upper(), run_id=run_id, agent_id=card.id, card_fingerprint=card.fingerprint(),
                tool=spec.name, arguments=args, side_effect=spec.side_effect, reason=decision.reason,
            )
            if decision.approval == "policy":
                action.status, action.approved_by, action.approval_kind = "APPROVED", f"policy:{card.id}@{card.version}", "policy"
            self.store.save_action(action)
            out.append(action)
        return out

    # --- human gate ------------------------------------------------------------------
    def _human(self, actor: str) -> str:
        actor = (actor or "").strip()
        if len(actor) < 2 or actor.lower().startswith(HUMAN_PREFIXES_FORBIDDEN):
            raise GovernanceError("approvals must come from a named human, not an agent, model or policy")
        return actor

    def approve(self, action_id: str, actor: str) -> dict:
        actor = self._human(actor)
        action = self._action(action_id)
        if action.status != "AWAITING_APPROVAL":
            raise ConflictError(f"action is {action.status}, not awaiting approval")
        action.status, action.approved_by, action.approval_kind = "APPROVED", actor, "human"
        if not self.store.transition(action, "AWAITING_APPROVAL", "action.approved", actor):
            raise ConflictError("action changed concurrently")
        return action.model_dump()

    def reject(self, action_id: str, actor: str, reason: str = "") -> dict:
        actor = self._human(actor)
        action = self._action(action_id)
        if action.status not in {"AWAITING_APPROVAL", "APPROVED"}:
            raise ConflictError(f"action is {action.status}")
        expected = action.status
        action.status, action.reason = "REJECTED", reason or action.reason
        if not self.store.transition(action, expected, "action.rejected", actor):
            raise ConflictError("action changed concurrently")
        return action.model_dump()

    def _action(self, action_id: str) -> ActionIntent:
        action = self.store.get_action(action_id)
        if action is None:
            raise KeyError(action_id)
        return action

    # --- execution --------------------------------------------------------------------
    def execute(self, action_id: str) -> dict:
        action = self._action(action_id)
        spec = self.registry.get(action.tool)
        decision = policy.for_execution(self.cards.get(action.agent_id), spec, action)
        if not decision.allowed:
            raise GovernanceError(decision.reason)
        executing = action.model_copy(update={"status": "EXECUTING"})
        if not self.store.transition(executing, "APPROVED", "action.executing", "runtime"):
            raise ConflictError("action is already executing or executed")
        try:
            output, status = self.registry.call(action.tool, action.arguments), "SUCCEEDED"
        except Exception as exc:  # a failing connector still produces a receipt
            output, status = {"error": str(exc), "external_delivery_performed": False}, "FAILED"
        receipt = ExecutionReceipt(id="RCP-" + uuid.uuid4().hex[:10].upper(), action_id=action.id, tool=action.tool,
                                   status=status, input_digest=digest(action.arguments), output_digest=digest(output), output=output)
        verification = verify_execution(action, receipt, decision)
        self.store.save_receipt(receipt.id, action.id, "execution", receipt.model_dump())
        self.store.save_receipt(verification.id, action.id, "verification", verification.model_dump())
        final = executing.model_copy(update={"status": "EXECUTED" if verification.passed else "FAILED"})
        self.store.transition(final, "EXECUTING", "action.executed" if verification.passed else "action.failed", "runtime")
        return {"action": final.model_dump(), "execution_receipt": receipt.model_dump(), "verification_receipt": verification.model_dump()}

    def audit(self) -> dict:
        return self.store.verify_ledger()
