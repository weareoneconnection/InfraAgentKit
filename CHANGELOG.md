# Changelog

## 3.0.0 — 2026-10-17
- Expanded from 5 examples to 30 governed Agent Cards: 24 lifecycle domains, 4 control agents and 2 assurance agents.
- Added capability, data-class, collaboration, escalation and output-contract declarations with cross-card linting.
- Added dynamic lead/support team composition with a configurable five-agent default cap.
- Added contextual country and digital-twin control agents, fixed-contract handoffs, conflict reporting and synthesis.
- Added 44 lifecycle/platform knowledge entries for 57 bilingual, versioned sources across the full catalogue.
- Added read-only P6, ERP cost, procurement, document-control, BIM/GIS/digital-twin and IoT connector previews.
- Added catalogue coverage API/MCP metadata and a responsive 30-agent mission-control console.
- Expanded validation to 42 tests and 54 benchmark cases with 100% deterministic gates.

## 2.0.0 — 2026-10-17
- Strict Agent Card schema with fingerprint and lint; operator authority with declared write exemptions.
- Bilingual knowledge packs with per-source SHA-256; BM25 retrieval with CJK bigrams and stopwords.
- Word-boundary term matching (fixes "knowledge" matching "edge").
- Evidence routing to agents; rule and optional model planning/findings, both validated.
- Policy re-evaluated at execution against the proposing card's fingerprint; only approved arguments run.
- Named-human approvals only; compare-and-set transitions prevent double execution.
- Hash-chained audit ledger with tamper detection (`infra-agent audit`).
- Execution verifier with 8 checks; finding verifier re-checks citations and tool output digests.
- MCP server on the official SDK v2 exposing analysis only; tested in-process and over stdio.
- Benchmark: 35 cases including 11 governance attacks; 36 tests.

## 1.0.0
- Initial Agent Card, tool registry, human gate, receipts and reference MCP server.
