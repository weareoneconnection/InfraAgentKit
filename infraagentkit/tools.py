"""Tool registry and the reference tools.

A tool declares its side effect (``read_only``, ``write`` or ``external``)
and whether its output counts as evidence. The runtime, not the agent,
decides whether a call needs a human: read-only tools run during analysis;
anything else becomes an :class:`~infraagentkit.contracts.ActionIntent`.
Reference tools are deterministic and never touch an external system; real
connectors (P6, BIM, ERP, mail) replace them behind the same contract.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from .knowledge import KnowledgeIndex, load_packs
from .text import matched

SideEffect = Literal["read_only", "write", "external"]


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    fn: Callable[..., dict]
    side_effect: SideEffect = "read_only"
    evidence_output: bool = False
    parameters: dict = field(default_factory=dict)

    def schema(self) -> dict:
        return {"name": self.name, "description": self.description, "side_effect": self.side_effect,
                "evidence_output": self.evidence_output, "parameters": self.parameters}


def _parameters(fn: Callable) -> dict:
    props, required = {}, []
    for name, param in inspect.signature(fn).parameters.items():
        kind = {int: "integer", float: "number", bool: "boolean"}.get(param.annotation, "string")
        props[name] = {"type": kind}
        if param.default is inspect.Parameter.empty:
            required.append(name)
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {}

    def register(self, name: str, description: str, fn: Callable[..., dict], side_effect: SideEffect = "read_only",
                 evidence_output: bool = False) -> ToolSpec:
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        spec = ToolSpec(name, description, fn, side_effect, evidence_output, _parameters(fn))
        self._tools[name] = spec
        return spec

    def names(self) -> list[str]:
        return sorted(self._tools)

    def get(self, name: str) -> ToolSpec:
        if name not in self._tools:
            raise KeyError(f"unknown tool: {name}")
        return self._tools[name]

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def call(self, name: str, arguments: dict) -> dict:
        spec = self.get(name)
        allowed = set(spec.parameters["properties"])
        unknown = set(arguments) - allowed
        missing = set(spec.parameters["required"]) - set(arguments)
        if unknown or missing:
            raise ValueError(f"{name}: unknown arguments {sorted(unknown)}, missing {sorted(missing)}")
        return spec.fn(**arguments)

    def describe(self) -> list[dict]:
        return [self._tools[n].schema() for n in self.names()]


# --- reference tools ----------------------------------------------------------

RISK_RULES: list[tuple[str, list[str]]] = [
    ("CRITICAL", ["collapse", "fatal", "fatality", "electrocution", "person fell", "坍塌", "死亡", "触电", "人员坠落"]),
    ("HIGH", ["unprotected edge", "work at height", "working at height", "fall protection", "guardrail missing",
              "no guardrail", "mobile crane", "lifting", "deep excavation", "confined space", "hot work",
              "临边", "高处作业", "未系安全带", "吊装", "深基坑", "受限空间", "动火"]),
    ("MEDIUM", ["crack", "defect", "ncr", "non-conformance", "spill", "leak", "corrosion", "bearing displacement",
                "裂缝", "缺陷", "不符合项", "泄漏", "锈蚀", "位移"]),
]


def risk_assess(text: str) -> dict:
    """Rule-based risk level with the signals that triggered it."""
    for level, terms in RISK_RULES:
        hits = matched(text, terms)
        if hits:
            return {"risk": level, "signals": hits}
    return {"risk": "LOW", "signals": []}


def make_knowledge_search(index: KnowledgeIndex) -> Callable[..., dict]:
    def knowledge_search(query: str, jurisdiction: str = "") -> dict:
        """BM25 search over governed knowledge packs; only hits above the threshold are returned."""
        return {"query": query, "hits": index.search(query, top_k=3, jurisdiction=jurisdiction or None)}
    return knowledge_search


def draft_document(title: str, body: str) -> dict:
    return {"title": title, "body": body, "delivery_status": "DRAFT_ONLY_NOT_SENT", "external_delivery_performed": False}


def notification_send(channel: str, message: str) -> dict:
    # Demo adapter: never sends. A production connector keeps this contract behind the same gate.
    return {"channel": channel, "message": message, "status": "SIMULATED_NOT_SENT", "external_delivery_performed": False}


def _connector_preview(system: str, query: str, records: list[dict]) -> dict:
    """Read-only synthetic connector used to demonstrate the governed adapter contract."""
    return {"system": system, "query": query, "mode": "SYNTHETIC_READ_ONLY_PREVIEW", "records": records,
            "external_write_performed": False}


def schedule_lookup(activity: str) -> dict:
    return _connector_preview("P6/Schedule", activity, [{"activity": "CIV-P47-240", "status": "IN_PROGRESS",
                                                       "float_days": 3, "data_date": "2026-10-15"}])


def cost_lookup(cost_code: str) -> dict:
    return _connector_preview("ERP/Cost", cost_code, [{"cost_code": "CIV-4300", "budget": 1250000,
                                                    "committed": 910000, "forecast": 1315000, "currency": "USD"}])


def procurement_lookup(package: str) -> dict:
    return _connector_preview("Procurement", package, [{"package": "PKG-BRG-03", "status": "AT_RISK",
                                                       "required_on_site": "2026-11-20", "forecast_delivery": "2026-11-27"}])


def document_lookup(reference: str) -> dict:
    return _connector_preview("Document Control", reference, [{"reference": "GIA-DRG-CIV-0042", "revision": "C",
                                                            "status": "APPROVED_FOR_CONSTRUCTION"}])


def twin_locate(asset_id: str) -> dict:
    return _connector_preview("BIM/GIS/Digital Twin", asset_id, [{"asset_id": "P47", "ifc_guid": "2M9xP47DemoGuid",
                                                               "tileset": "rail-corridor-a", "sensor_links": 2}])


def telemetry_read(sensor_id: str) -> dict:
    return _connector_preview("IoT/SCADA", sensor_id, [{"sensor_id": "BRG03-DISP-X", "value": 4.2,
                                                    "unit": "mm", "quality": "GOOD", "timestamp": "2026-10-17T12:00:00Z"}])


def default_registry(index: KnowledgeIndex | None = None) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("knowledge.search", "Search governed engineering knowledge packs (BM25, bilingual)",
                      make_knowledge_search(index or KnowledgeIndex(load_packs())), evidence_output=True)
    registry.register("risk.assess", "Assess infrastructure event risk from text signals", risk_assess)
    registry.register("schedule.lookup", "Read a governed P6/schedule preview", schedule_lookup)
    registry.register("cost.lookup", "Read a governed ERP cost preview", cost_lookup)
    registry.register("procurement.lookup", "Read a governed procurement preview", procurement_lookup)
    registry.register("document.lookup", "Read a governed document-control preview", document_lookup)
    registry.register("twin.locate", "Locate assets and linked sensors in BIM/GIS/digital-twin data", twin_locate)
    registry.register("telemetry.read", "Read governed IoT/SCADA telemetry preview", telemetry_read)
    registry.register("document.draft", "Create a governed draft document (never sent)", draft_document, side_effect="write")
    registry.register("notification.send", "External notification adapter (simulated in the reference kit)",
                      notification_send, side_effect="external")
    return registry
