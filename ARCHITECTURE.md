# Architecture

```text
             CLI · Web console · Runtime API · MCP (official SDK v2)
                                   │
                          GovernedRuntime v4
   ┌──────────────┬────────────────┼──────────────────┬──────────────────┐
   │              │                │                  │                  │
 Intake +    Team composer     Tool registry     Policy engine      Independent
 evidence    (lead + support,  (governed tools    (default deny,    verifier
 routing      max 5 domain)     + Connector SDK)   RBAC re-check)    + synthesis
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
| `security.py` | Token RBAC, actor binding, rate limiting and explicit demo boundary |
| `connectors.py` | Typed Connector SDK and digest-bound file snapshot reference connector |
| `verifier.py` | Finding verification and 8-check execution verification |
| `store.py` | Runs, actions, receipts, compare-and-set transitions, ledger |
| `web.py` / `static/console.html` | Runtime API and console |
| `mcp_server.py` | MCP tools over the runtime (no approval/execution) |

Reasoning authority and execution authority are separate by construction: the only path from analysis to a side effect is an `ActionIntent` that a named human approves (or an operator card's declared write exemption), and the executor re-validates it.

The example catalogue contains 24 domain agents, 4 control agents and 2 assurance agents. In v4 the platform agents are not catalogue decoration: intake, orchestration, provenance and independent verification emit ordered, fingerprinted `agent.step` receipts on every run. Country and digital-twin controls join when their signals are present. Control agents coordinate context but cannot approve. Domain specialists remain independently evidence-bound; the runtime records handoffs and produces a synthesis that names contributors, gaps, conflicts and the controlling risk.

Runs carry tenant and project scopes, and optional idempotency keys prevent duplicate work inside that scope. Runtime/model telemetry, deterministic evaluation results and connector manifests are exposed separately so an operator can distinguish a real model response from a rule fallback.

Security has two explicit modes. `token-rbac` binds actors and reviewer/executor rights to server-side tokens. Without token configuration, `demo-unverified` remains usable for judging but clearly reports that identity is not verified and bundled side-effect adapters are simulations. Production evolution still requires an external identity provider, Postgres, signed ledger heads, secret management and real enterprise connector packages replacing preview adapters behind the same contracts.
