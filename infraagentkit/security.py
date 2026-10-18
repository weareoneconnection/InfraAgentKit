"""Small, explicit security boundary for the reference HTTP runtime.

Token mode is enabled with ``INFRAAGENTKIT_API_TOKENS`` containing a JSON
object whose keys are bearer tokens and whose values contain ``actor`` and
``roles``.  When it is not configured the public reference deployment stays
in an honestly labelled demo mode: simulated actions are available, but the
status endpoint makes clear that identities are not verified.
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass


ROLE_INHERITS = {
    "viewer": {"viewer"},
    "analyst": {"viewer", "analyst"},
    "reviewer": {"viewer", "reviewer"},
    "executor": {"viewer", "executor"},
    "admin": {"viewer", "analyst", "reviewer", "executor", "admin"},
}


@dataclass(frozen=True)
class Principal:
    actor: str
    roles: frozenset[str]
    authenticated: bool
    mode: str

    def can(self, role: str) -> bool:
        return any(role in ROLE_INHERITS.get(item, {item}) for item in self.roles)


class AuthSettings:
    def __init__(self, tokens: dict[str, Principal] | None = None) -> None:
        self.tokens = tokens or {}
        self.mode = "token-rbac" if self.tokens else "demo-unverified"

    @classmethod
    def from_env(cls) -> "AuthSettings":
        raw = os.getenv("INFRAAGENTKIT_API_TOKENS", "").strip()
        if not raw:
            return cls()
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise ValueError("INFRAAGENTKIT_API_TOKENS must be a JSON object") from exc
        if not isinstance(payload, dict):
            raise ValueError("INFRAAGENTKIT_API_TOKENS must be a JSON object")
        tokens: dict[str, Principal] = {}
        for token, item in payload.items():
            if not isinstance(token, str) or len(token) < 16 or not isinstance(item, dict):
                raise ValueError("each API token must be at least 16 characters and map to an object")
            actor = str(item.get("actor", "")).strip()
            roles = frozenset(str(role) for role in item.get("roles", []))
            if len(actor) < 2 or not roles or not roles <= set(ROLE_INHERITS):
                raise ValueError("each API token needs an actor and valid roles")
            tokens[token] = Principal(actor, roles, True, "token-rbac")
        return cls(tokens)

    def authenticate(self, authorization: str | None, claimed_actor: str = "") -> Principal:
        if self.mode == "demo-unverified":
            actor = claimed_actor.strip() or "演示操作者"
            return Principal(actor, frozenset({"analyst", "reviewer", "executor"}), False, self.mode)
        scheme, _, token = (authorization or "").partition(" ")
        principal = self.tokens.get(token) if scheme.lower() == "bearer" else None
        if principal is None:
            raise PermissionError("valid bearer token required")
        return principal

    def status(self) -> dict:
        return {
            "mode": self.mode,
            "identity_verified": self.mode == "token-rbac",
            "production_ready": self.mode == "token-rbac",
            "roles": sorted(ROLE_INHERITS),
            "demo_boundary": None if self.mode == "token-rbac" else
                "Public demo identities are not verified; all bundled side-effect connectors are simulated.",
        }


class SlidingWindowLimiter:
    """Process-local abuse guard for the public demo; gateways remain authoritative."""

    def __init__(self, limit: int = 240, window_seconds: int = 60) -> None:
        self.limit, self.window_seconds = limit, window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            events = self._events[key]
            while events and events[0] <= now - self.window_seconds:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True
