# Contributing

1. Add tests for every behavior change.
2. Keep side effects explicit in ToolSpec.
3. Never mark a finding SUPPORTED without evidence references.
4. Run `pytest -q` and `python evals/run_benchmark.py` before a PR.
5. New MCP tools must have typed arguments and clear security boundaries.
