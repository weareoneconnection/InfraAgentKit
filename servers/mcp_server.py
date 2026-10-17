"""Run the InfraAgentKit MCP server: ``python servers/mcp_server.py [--transport streamable-http]``."""
from __future__ import annotations

import argparse
from pathlib import Path

from infraagentkit.mcp_server import build_server
from infraagentkit.runtime import GovernedRuntime

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    parser.add_argument("--port", type=int, default=8113)
    parser.add_argument("--agents", default=str(Path(__file__).resolve().parent.parent / "examples" / "agents"))
    args = parser.parse_args()
    server = build_server(GovernedRuntime.from_directory(args.agents))
    if args.transport == "streamable-http":
        server.run(transport="streamable-http", port=args.port)
    else:
        server.run()
