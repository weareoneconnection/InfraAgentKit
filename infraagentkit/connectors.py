"""Connector SDK and a real file-backed reference connector.

The built-in P6/ERP/BIM examples deliberately remain synthetic.  This module
shows how deployments replace them without changing Agent Cards or policy:
connector tools are registered through the same typed registry and retain a
manifest, source digest and deterministic receipt.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .tools import ToolRegistry


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConnectorTool(_Strict):
    name: str
    description: str
    parameter: str
    records: list[dict] = Field(default_factory=list)


class ConnectorManifest(_Strict):
    id: str
    version: str
    system: str
    mode: str = "FILE_SNAPSHOT"
    tools: list[ConnectorTool]


class FileSnapshotConnector:
    """Register read-only tools from a reviewed JSON snapshot on disk."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        raw = self.path.read_bytes()
        self.digest = hashlib.sha256(raw).hexdigest()
        self.manifest = ConnectorManifest.model_validate_json(raw)

    def register(self, registry: ToolRegistry) -> list[str]:
        names = []
        for tool in self.manifest.tools:
            parameter = tool.parameter
            records = list(tool.records)
            connector = self

            class Lookup:
                __signature__ = inspect.Signature([
                    inspect.Parameter(parameter, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str)
                ], return_annotation=dict)

                def __call__(self, **arguments) -> dict:
                    query = str(arguments[parameter])
                    needle = query.casefold().strip()
                    matched = [row for row in records if not needle or needle in json.dumps(row, ensure_ascii=False).casefold()]
                    return {"connector": connector.manifest.id, "system": connector.manifest.system,
                            "mode": connector.manifest.mode, "query": {parameter: query},
                            "source_digest": connector.digest, "records": matched[:20],
                            "external_write_performed": False}

            registry.register(tool.name, tool.description, Lookup())
            names.append(tool.name)
        return names

    def describe(self) -> dict:
        return {**self.manifest.model_dump(exclude={"tools": {"__all__": {"records"}}}),
                "path": str(self.path), "digest": self.digest,
                "tool_names": [tool.name for tool in self.manifest.tools]}


def load_connectors(registry: ToolRegistry, paths: str = "") -> list[dict]:
    loaded = []
    for raw in filter(None, (item.strip() for item in paths.split(os.pathsep))):
        connector = FileSnapshotConnector(raw)
        connector.register(registry)
        loaded.append(connector.describe())
    return loaded
