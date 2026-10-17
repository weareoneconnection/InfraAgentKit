import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("INFRAAGENTKIT_DB", tempfile.mktemp(suffix=".db"))
for key in ("INFRAAGENTKIT_MODEL_BASE_URL", "INFRAAGENTKIT_MODEL"):
    os.environ.pop(key, None)

from infraagentkit import GovernedRuntime  # noqa: E402
from infraagentkit.cards import load_cards  # noqa: E402
from infraagentkit.store import Store  # noqa: E402

AGENTS = ROOT / "examples" / "agents"
EDGE = "Worker near unprotected edge at Pier P47 without fall protection"


@pytest.fixture
def runtime(tmp_path):
    return GovernedRuntime(load_cards(AGENTS), store=Store(tmp_path / "test.db"))
