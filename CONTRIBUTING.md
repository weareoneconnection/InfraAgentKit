# Contributing

1. Every behaviour change comes with a test; run `pytest -q` and `infra-agent eval` before a pull request.
2. Declare side effects honestly in the tool registration; a tool that writes anywhere is not `read_only`.
3. Never mark a finding SUPPORTED without sources returned by an evidence tool in the same run.
4. New knowledge sources need a stable `ref`, a version and a domain; synthetic content must say so.
5. New MCP tools must not approve, reject or execute actions.
