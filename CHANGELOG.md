# Changelog

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
