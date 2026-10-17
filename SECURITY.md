# Security Policy

Report vulnerabilities privately to the maintainers; do not include credentials or customer data in issues.

- The reference tools never deliver anything externally (`DRAFT_ONLY_NOT_SENT`, `SIMULATED_NOT_SENT`).
- The runtime API has no built-in authentication; deploy it behind an identity-aware gateway and map the approver to the authenticated user.
- Connectors must use least-privilege credentials from a secret store, be idempotent and keep the receipt contract.
- Treat model output and tool output as untrusted data; the runtime validates both before use.
