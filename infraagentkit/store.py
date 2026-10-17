"""SQLite store with an append-only, hash-chained audit ledger.

Every state change (run analysed, action proposed / approved / rejected /
executed, receipts) is appended to ``ledger`` with
``hash = sha256(prev_hash + kind + subject + payload_digest)``. Editing or
deleting any earlier row breaks the chain, which :meth:`Store.verify_ledger`
reports with the first broken sequence number.

Action status changes are compare-and-set (``UPDATE ... WHERE status = ?``),
so two concurrent executions of the same approved action cannot both run.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from .contracts import ActionIntent
from .tools import digest

GENESIS = "0" * 64

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, message TEXT NOT NULL, status TEXT NOT NULL,
  payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY, run_id TEXT NOT NULL, payload TEXT NOT NULL,
  status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, action_id TEXT NOT NULL, kind TEXT NOT NULL,
  payload TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
  subject TEXT NOT NULL, actor TEXT NOT NULL, payload_digest TEXT NOT NULL, prev_hash TEXT NOT NULL,
  hash TEXT NOT NULL, created_at TEXT NOT NULL);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def chain_hash(prev: str, kind: str, subject: str, actor: str, payload_digest: str) -> str:
    return hashlib.sha256(f"{prev}|{kind}|{subject}|{actor}|{payload_digest}".encode()).hexdigest()


class Store:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or os.getenv("INFRAAGENTKIT_DB", "./data/infraagentkit.db"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    # --- ledger ------------------------------------------------------------------
    def _append(self, c: sqlite3.Connection, kind: str, subject: str, actor: str, payload) -> str:
        row = c.execute("SELECT hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        prev = row["hash"] if row else GENESIS
        pd = digest(payload)
        h = chain_hash(prev, kind, subject, actor, pd)
        c.execute("INSERT INTO ledger(kind,subject,actor,payload_digest,prev_hash,hash,created_at) VALUES(?,?,?,?,?,?,?)",
                  (kind, subject, actor, pd, prev, h, now()))
        return h

    def ledger(self, subject: str | None = None) -> list[dict]:
        with self._conn() as c:
            rows = c.execute("SELECT * FROM ledger" + (" WHERE subject LIKE ?" if subject else "") + " ORDER BY seq",
                             (f"{subject}%",) if subject else ()).fetchall()
        return [dict(r) for r in rows]

    def verify_ledger(self) -> dict:
        prev = GENESIS
        rows = self.ledger()
        for row in rows:
            expected = chain_hash(prev, row["kind"], row["subject"], row["actor"], row["payload_digest"])
            if row["prev_hash"] != prev or row["hash"] != expected:
                return {"valid": False, "entries": len(rows), "broken_at": row["seq"]}
            prev = row["hash"]
        return {"valid": True, "entries": len(rows), "head": prev}

    # --- runs ------------------------------------------------------------------
    def save_run(self, run_id: str, message: str, status: str, payload: dict) -> None:
        with self._lock, self._conn() as c:
            c.execute("INSERT INTO runs VALUES(?,?,?,?,?)", (run_id, message, status, json.dumps(payload, ensure_ascii=False), now()))
            self._append(c, "run.analysed", run_id, "runtime", payload)

    def get_run(self, run_id: str) -> dict | None:
        with self._conn() as c:
            row = c.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if not row:
                return None
            actions = [json.loads(r["payload"]) for r in c.execute("SELECT payload FROM actions WHERE run_id=? ORDER BY created_at", (run_id,))]
            receipts = [{"kind": r["kind"], **json.loads(r["payload"])} for r in c.execute(
                "SELECT r.kind, r.payload FROM receipts r JOIN actions a ON a.id=r.action_id WHERE a.run_id=? ORDER BY r.created_at", (run_id,))]
        return {**json.loads(row["payload"]), "status": row["status"], "actions": actions, "receipts": receipts}

    def recent_runs(self, limit: int = 20) -> list[dict]:
        with self._conn() as c:
            return [dict(r) for r in c.execute("SELECT id, message, status, created_at FROM runs ORDER BY created_at DESC LIMIT ?", (limit,))]

    # --- actions -------------------------------------------------------------------
    def save_action(self, action: ActionIntent) -> None:
        with self._lock, self._conn() as c:
            c.execute("INSERT INTO actions VALUES(?,?,?,?,?,?)",
                      (action.id, action.run_id, action.model_dump_json(), action.status, now(), now()))
            self._append(c, "action.proposed", action.id, action.agent_id, action.model_dump())

    def get_action(self, action_id: str) -> ActionIntent | None:
        with self._conn() as c:
            row = c.execute("SELECT payload FROM actions WHERE id=?", (action_id,)).fetchone()
        return ActionIntent.model_validate_json(row["payload"]) if row else None

    def pending_actions(self) -> list[dict]:
        with self._conn() as c:
            return [json.loads(r["payload"]) for r in c.execute("SELECT payload FROM actions WHERE status='AWAITING_APPROVAL' ORDER BY created_at")]

    def transition(self, action: ActionIntent, expected: str, kind: str, actor: str) -> bool:
        """Compare-and-set the action's status; False if another caller moved it first."""
        with self._lock, self._conn() as c:
            cur = c.execute("UPDATE actions SET payload=?, status=?, updated_at=? WHERE id=? AND status=?",
                            (action.model_dump_json(), action.status, now(), action.id, expected))
            if cur.rowcount != 1:
                return False
            self._append(c, kind, action.id, actor, action.model_dump())
            return True

    def save_receipt(self, receipt_id: str, action_id: str, kind: str, payload: dict) -> None:
        with self._lock, self._conn() as c:
            c.execute("INSERT INTO receipts VALUES(?,?,?,?,?)", (receipt_id, action_id, kind, json.dumps(payload, ensure_ascii=False), now()))
            self._append(c, f"receipt.{kind}", action_id, "runtime", payload)
