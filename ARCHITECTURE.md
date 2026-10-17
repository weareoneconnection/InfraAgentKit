# Architecture

```text
             CLI · Web console · Runtime API · MCP (official SDK v2)
                                   │
                          GovernedRuntime v3
   ┌──────────────┬────────────────┼──────────────────┬──────────────────┐
   │              │                │                  │                  │
 Intake +    Team composer     Tool registry     Policy engine      Independent
 evidence    (lead + support,  (10 governed       (default deny,    verifier
 routing      max 5 domain)     adapters)          re-check)         + synthesis
   │              │                │                  │                  │
   └──────────────┴──────── Store (SQLite) + hash-chained ledger ─────────┘
                                   │
                 Knowledge packs (YAML, versioned, SHA-256 per source; BM25, bilingual)
```

| Module | Responsibility |
| --- | --- |
| `cards.py` | Strict Agent Card model, fingerprint, lint against the registry |
| `tools.py` | Tool registry, argument schemas, reference tools |
| `knowledge.py` / `text.py` | Knowledge packs, BM25 with Latin words and CJK bigrams, word-boundary matching |
| `reasoning.py` | Rule and model planning, rule and model findings, citation validation |
| `policy.py` | Analysis, proposal and execution decisions |
| `runtime.py` | Routing, runs, intents, human gate, execution |
| `verifier.py` | Finding verification and 8-check execution verification |
| `store.py` | Runs, actions, receipts, compare-and-set transitions, ledger |
| `web.py` / `static/console.html` | Runtime API and console |
| `mcp_server.py` | MCP tools over the runtime (no approval/execution) |

Reasoning authority and execution authority are separate by construction: the only path from analysis to a side effect is an `ActionIntent` that a named human approves (or an operator card's declared write exemption), and the executor re-validates it.

The example catalogue contains 24 domain agents, 4 control agents and 2 assurance agents. Control agents coordinate context but cannot approve. Domain specialists remain independently evidence-bound; the runtime records handoffs and produces a synthesis that names contributors, gaps, conflicts and the controlling risk.

Production evolution: Postgres store, identity provider in front of the API, signed ledger heads, and real connector packages replacing the read-only P6, BIM/GIS, ERP, procurement, document and IoT preview adapters behind the same contracts.
