# Stage 13 — production evidence upgrade

InfraAgentKit 4.0 turns the six platform cards into observable runtime actors while preserving the core boundary: specialists reason, platform agents control and verify, and only a named authorised human may approve side effects.

## 13.1 Executable platform agents

Every run now records digest-backed steps for intake, orchestration, evidence provenance and independent verification. Country and digital-twin control steps join when the task contains the corresponding context. Each step stores its card fingerprint, input/output contract, result and SHA-256 digest and receives its own ledger entry.

## 13.2 Identity and access

Set `INFRAAGENTKIT_API_TOKENS` to a JSON object mapping bearer tokens to actors and roles. Roles are `viewer`, `analyst`, `reviewer`, `executor` and `admin`. Without this setting the server is explicitly labelled `demo-unverified`; bundled connectors still cannot deliver an external side effect.

```json
{"replace-with-a-long-random-token":{"actor":"项目经理 张工","roles":["admin"]}}
```

## 13.3 Model evidence

`GET /observability` separates model transport statistics, model-planned calls, model-authored findings and deterministic fallbacks. `infra-agent eval --model` runs an optional live-model suite; normal CI remains deterministic and secret-free.

## 13.4 Connector SDK

`FileSnapshotConnector` validates a strict manifest, registers read-only tools and includes the source-file digest in every result. Validate the runnable example with:

```bash
infra-agent connector-validate examples/connectors/project-snapshot.json
```

Set `INFRAAGENTKIT_CONNECTOR_FILES` to one or more platform-separated manifest paths to load them at startup.

## 13.5 Durable execution context

Runs carry `tenant_id` and `project_id`. The HTTP endpoint accepts `Idempotency-Key`; a repeated request in the same scope returns the original run rather than producing duplicate actions. SQLite remains the reference store; enterprise deployments can replace the store behind the same contracts.

## 13.6 Release engineering

CI covers Python 3.11–3.13. Tagged releases build the Python distribution and container image, attach provenance, publish a GitHub Release and can use PyPI trusted publishing. A separate workflow produces dependency, static-analysis and SBOM evidence.

## 13.7 Golden demonstration

`GET /demo/golden` provides the P47 high-work scenario and its expected route, evidence, risk, action and governance steps. The web console visualises the specialist team, all platform-agent receipts, human gate, execution receipt and independent verification.

## Honest boundary

The public deployment is a reference demo. Its project knowledge and built-in enterprise connectors are synthetic. Token RBAC is production-capable only when backed by a protected secret and TLS; most enterprises should place the service behind their identity-aware gateway. SQLite and the process-local rate limiter are single-instance reference components, not claims of multi-region operation.
