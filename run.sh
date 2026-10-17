#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec python -m infraagentkit.cli serve --host "${HOST:-127.0.0.1}" --port "${PORT:-8103}"
