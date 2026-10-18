#!/usr/bin/env python3
"""Optional live-model benchmark; never runs in CI without explicit model configuration."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from infraagentkit.cards import load_cards  # noqa: E402
from infraagentkit.runtime import GovernedRuntime  # noqa: E402
from infraagentkit.store import Store  # noqa: E402


CASES = [
    ("P47 墩临边防护缺失，工人在高处作业未系安全带。", "hse-agent"),
    ("P52 墩拆模后发现混凝土裂缝，请提出质量处置要求。", "quality-agent"),
    ("分包商申请设计变更并要求延长关键线路工期。", "contract-agent"),
    ("支座采购包预测到货晚于要求到场日期。", "procurement-agent"),
]


def main() -> int:
    if not os.getenv("INFRAAGENTKIT_MODEL_BASE_URL") or not os.getenv("INFRAAGENTKIT_MODEL"):
        print(json.dumps({"suite": "INFRAAGENTKIT_MODEL_BENCHMARK", "version": "4.0", "status": "SKIPPED",
                          "reason": "model environment is not configured"}, ensure_ascii=False, indent=2))
        return 0
    runtime = GovernedRuntime(load_cards(ROOT / "examples" / "agents"),
                              store=Store(tempfile.mktemp(suffix=".db")))
    results = []
    for message, expected in CASES:
        run = runtime.run(message)
        finding = run["findings"][0]
        results.append({"expected_lead": expected, "actual_lead": run["team"]["lead"],
                        "composed_by": finding["composed_by"], "status": finding["status"],
                        "citation_valid": run["finding_verification"]["passed"],
                        "platform_steps": len(run["platform_steps"])})
    observed = runtime.observability()
    passed = all(item["actual_lead"] == item["expected_lead"] and item["citation_valid"] for item in results)
    print(json.dumps({"suite": "INFRAAGENTKIT_MODEL_BENCHMARK", "version": "4.0",
                      "status": "PASSED" if passed else "FAILED", "cases": len(results),
                      "results": results, **observed}, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
