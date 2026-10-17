# Architecture

```text
User / Event / Host
       │
       ▼
   Agent Card
       │
       ▼
Planner / Agent Logic
       │
       ▼
 Tool Registry / MCP
       │
       ▼
 Policy Engine ────── Default Deny
       │
       ▼
Evidence-backed Finding
       │
       ▼
 Action Intent
       │
       ▼
Human Approval Gate
       │
       ▼
 Tool Execution
       │
       ▼
Execution Receipt
       │
       ▼
Independent Verifier
```

The framework intentionally separates reasoning authority from execution authority.
