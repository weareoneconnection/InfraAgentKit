"""``infra-agent`` command line."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .cards import AgentCard, lint, load_cards
from .knowledge import load_packs
from .tools import default_registry

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples" / "agents"


def _print(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _runtime(args):
    from .runtime import GovernedRuntime
    return GovernedRuntime.from_directory(args.agents)


def cmd_doctor(args) -> int:
    registry = default_registry()
    problems, cards = [], []
    try:
        cards = load_cards(args.agents)
        problems = [p for c in cards for p in lint(c, registry)]
    except Exception as exc:  # report, do not crash
        problems.append(str(exc))
    try:
        import mcp  # noqa: F401
        mcp_ok = True
    except ImportError:
        mcp_ok = False
    _print({"status": "ok" if not problems else "failed", "version": __version__, "python": sys.version.split()[0],
            "agents": [c.id for c in cards], "tools": registry.names(), "knowledge_sources": len(load_packs()),
            "mcp_sdk": mcp_ok, "problems": problems})
    return 0 if not problems else 1


def cmd_validate(args) -> int:
    from .cards import load_card
    registry = default_registry()
    failed = 0
    for path in [Path(p) for p in args.paths]:
        try:
            issues = lint(load_card(path), registry)
        except Exception as exc:
            issues = [str(exc)]
        failed += bool(issues)
        print(f"{'FAIL' if issues else 'OK  '} {path}" + "".join(f"\n     - {i}" for i in issues))
    return 1 if failed else 0


def cmd_init(args) -> int:
    target = Path(args.path)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy(EXAMPLES / "hse-agent.yaml", target / "agent.yaml")
    (target / "README.md").write_text("# New InfraAgentKit agent\n\nEdit `agent.yaml`, then run `infra-agent validate agent.yaml`.\n", encoding="utf-8")
    print(target.resolve())
    return 0


def cmd_run(args) -> int:
    run = _runtime(args).run(args.message, args.agent or None)
    _print({k: run[k] for k in ("run_id", "agents", "findings", "actions", "finding_verification")})
    return 0


def cmd_pending(args) -> int:
    _print(_runtime(args).store.pending_actions())
    return 0


def cmd_approve(args) -> int:
    _print(_runtime(args).approve(args.action_id, args.actor))
    return 0


def cmd_reject(args) -> int:
    _print(_runtime(args).reject(args.action_id, args.actor, args.reason))
    return 0


def cmd_execute(args) -> int:
    _print(_runtime(args).execute(args.action_id))
    return 0


def cmd_audit(args) -> int:
    result = _runtime(args).audit()
    _print(result)
    return 0 if result["valid"] else 2


def cmd_schema(_args) -> int:
    _print(AgentCard.model_json_schema())
    return 0


def cmd_eval(_args) -> int:
    return subprocess.call([sys.executable, str(ROOT / "evals" / "run_benchmark.py")], cwd=ROOT)


def cmd_serve(args) -> int:
    import uvicorn
    uvicorn.run("infraagentkit.web:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def cmd_mcp(args) -> int:
    from .mcp_server import build_server
    server = build_server(_runtime(args))
    if args.transport == "streamable-http":
        server.run(transport="streamable-http", port=args.port)
    else:
        server.run()
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="infra-agent", description="Governed agents for transport infrastructure")
    parser.add_argument("--agents", default=str(EXAMPLES), help="directory of Agent Card YAML files")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="check cards, tools, knowledge and MCP SDK").set_defaults(fn=cmd_doctor)
    p = sub.add_parser("validate", help="lint Agent Card files"); p.add_argument("paths", nargs="+"); p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("init", help="scaffold a new agent"); p.add_argument("path"); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("run", help="run agents on a message"); p.add_argument("message"); p.add_argument("--agent", action="append")
    p.set_defaults(fn=cmd_run)
    sub.add_parser("pending", help="list actions awaiting approval").set_defaults(fn=cmd_pending)
    p = sub.add_parser("approve", help="approve an action as a named human"); p.add_argument("action_id"); p.add_argument("--actor", required=True)
    p.set_defaults(fn=cmd_approve)
    p = sub.add_parser("reject", help="reject an action"); p.add_argument("action_id"); p.add_argument("--actor", required=True)
    p.add_argument("--reason", default=""); p.set_defaults(fn=cmd_reject)
    p = sub.add_parser("execute", help="execute an approved action"); p.add_argument("action_id"); p.set_defaults(fn=cmd_execute)
    sub.add_parser("audit", help="verify the hash-chained ledger").set_defaults(fn=cmd_audit)
    sub.add_parser("schema", help="print the Agent Card JSON Schema").set_defaults(fn=cmd_schema)
    sub.add_parser("eval", help="run the governance benchmark").set_defaults(fn=cmd_eval)
    p = sub.add_parser("serve", help="runtime API and console"); p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8103); p.add_argument("--reload", action="store_true"); p.set_defaults(fn=cmd_serve)
    p = sub.add_parser("mcp-serve", help="MCP server (official SDK v2)")
    p.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio"); p.add_argument("--port", type=int, default=8113)
    p.set_defaults(fn=cmd_mcp)
    args = parser.parse_args(argv)
    try:
        raise SystemExit(args.fn(args))
    except (KeyError, PermissionError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
