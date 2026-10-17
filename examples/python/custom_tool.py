"""Extend InfraAgentKit with your own tool and agent in ~30 lines.

Run: python examples/python/custom_tool.py
"""
from __future__ import annotations

import tempfile

from infraagentkit import AgentCard, GovernedRuntime, default_registry
from infraagentkit.store import Store

# 1. A project adapter: read-only, so agents may call it during analysis.
SCHEDULE = {"P47": {"activity": "Pier cap P47 formwork", "float_days": 2, "next_milestone": "Deck pour 2026-11-04"}}


def schedule_lookup(text: str) -> dict:
    for asset, row in SCHEDULE.items():
        if asset.lower() in text.lower():
            return {"asset": asset, **row}
    return {"asset": None}


registry = default_registry()
registry.register("schedule.lookup", "Look up the programme activity for an asset mentioned in the text", schedule_lookup)

# 2. An agent card that may use it. The runtime lints the card against the registry.
card = AgentCard.model_validate({
    "id": "planning-agent", "name": "Planning Agent", "scope": {"domain": "hse"},
    "tools": ["schedule.lookup", "knowledge.search", "risk.assess", "document.draft"],
    "actions": [{"tool": "document.draft", "title": "{agent} recovery note"}],
})

runtime = GovernedRuntime([card], registry=registry, store=Store(tempfile.mktemp(suffix=".db")))
run = runtime.run("Worker near unprotected edge at Pier P47 without fall protection", ["planning-agent"])
for call in run["tool_calls"]:
    print(f"{call['tool']:18} -> {call['output']}")
print("finding:", run["findings"][0]["status"], run["findings"][0]["evidence_refs"])
print("intent :", run["actions"][0]["tool"], run["actions"][0]["status"])
