#!/usr/bin/env bash
set -e
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"
exec python -m infraagentkit.cli serve --port "${PORT:-8103}" --reload
