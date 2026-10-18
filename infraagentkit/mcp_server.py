"""MCP server (official MCP Python SDK v2) over the governed runtime.

Exposes analysis to any MCP host: knowledge search, risk assessment, running
agents, and reading runs, pending actions and the audit ledger. Approval and
execution are deliberately NOT exposed: an MCP host is an automated client,
so it can propose side effects (as action intents) but never authorise or
perform them. Humans approve through the runtime API or CLI.
"""
from __future__ import annotations

from mcp.server import MCPServer

from . import __version__
from .runtime import GovernedRuntime

EXPOSED = ["list_agents", "catalog_coverage", "knowledge_search", "risk_assess", "run_agents", "get_run",
           "list_pending_actions", "runtime_observability", "verify_ledger"]


def build_server(runtime: GovernedRuntime) -> MCPServer:
    server = MCPServer(
        "InfraAgentKit", version=__version__,
        instructions="Governed transport-infrastructure agents. Side effects are proposals that only a human can approve.",
    )

    @server.tool()
    def list_agents() -> list[dict]:
        """List the registered Agent Cards: domain, authority, tools and proposed actions."""
        return [{"id": c.id, "name": c.name, "tier": c.tier, "domain": c.scope.domain, "authority": c.authority,
                 "capabilities": c.capabilities, "tools": c.tools, "actions": [a.tool for a in c.actions],
                 "fingerprint": c.fingerprint()} for c in runtime.cards.values()]

    @server.tool()
    def catalog_coverage() -> dict:
        """Count governed agents, professional domains, lifecycle stages and the active-team limit."""
        return runtime.coverage()

    @server.tool()
    def knowledge_search(query: str, jurisdiction: str = "") -> dict:
        """Search governed engineering knowledge (bilingual BM25). Returns cited sources with content digests."""
        return runtime.registry.call("knowledge.search", {"query": query, "jurisdiction": jurisdiction})

    @server.tool()
    def risk_assess(text: str) -> dict:
        """Assess the risk level of an infrastructure event and the signals that triggered it."""
        return runtime.registry.call("risk.assess", {"text": text})

    @server.tool()
    def run_agents(message: str, agent_ids: list[str] | None = None) -> dict:
        """Run agents on a situation (routed automatically when agent_ids is empty).

        Returns findings with evidence and any side-effect action intents, which stay
        AWAITING_APPROVAL until a human approves them outside MCP."""
        run = runtime.run(message, agent_ids or None)
        return {"run_id": run["run_id"], "team": run["team"], "agents": run["agents"], "findings": run["findings"],
                "handoffs": run["handoffs"], "synthesis": run["synthesis"],
                "platform_steps": run["platform_steps"],
                "actions": [{"id": a["id"], "tool": a["tool"], "status": a["status"]} for a in run["actions"]],
                "finding_verification": run["finding_verification"]}

    @server.tool()
    def get_run(run_id: str) -> dict:
        """Full trace of a run: tool calls with output digests, findings, actions and receipts."""
        run = runtime.store.get_run(run_id)
        if run is None:
            raise ValueError(f"run not found: {run_id}")
        return run

    @server.tool()
    def list_pending_actions() -> list[dict]:
        """Side-effect intents waiting for a human decision."""
        return runtime.store.pending_actions()

    @server.tool()
    def runtime_observability() -> dict:
        """Model telemetry, governed runtime counts and configured connector manifests."""
        return runtime.observability()

    @server.tool()
    def verify_ledger() -> dict:
        """Recompute the hash chain of the audit ledger and report whether it is intact."""
        return runtime.audit()

    return server
