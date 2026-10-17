from __future__ import annotations
import json,sqlite3,os
from pathlib import Path
from datetime import datetime,timezone
DB=Path(os.getenv('INFRAAGENTKIT_DB','./data/infraagentkit.db'))
NOW=lambda:datetime.now(timezone.utc).isoformat()
SCHEMA='''
CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,message TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS actions(id TEXT PRIMARY KEY,run_id TEXT NOT NULL,tool TEXT NOT NULL,args TEXT NOT NULL,side_effect TEXT NOT NULL,status TEXT NOT NULL,approved_by TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY,action_id TEXT NOT NULL,kind TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL);
'''
def connect():
    DB.parent.mkdir(parents=True,exist_ok=True);c=sqlite3.connect(DB,check_same_thread=False);c.row_factory=sqlite3.Row;c.executescript(SCHEMA);return c
def save_run(id,message,status,payload):
    with connect() as c:c.execute('INSERT OR REPLACE INTO runs VALUES(?,?,?,?,?)',(id,message,status,json.dumps(payload,ensure_ascii=False),NOW()));c.commit()
def save_action(a):
    with connect() as c:c.execute('INSERT OR REPLACE INTO actions VALUES(?,?,?,?,?,?,?,?)',(a.id,a.run_id,a.tool,json.dumps(a.arguments,ensure_ascii=False),a.side_effect,a.status,a.approved_by,NOW()));c.commit()
def save_receipt(id,action_id,kind,status,payload):
    with connect() as c:c.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)',(id,action_id,kind,status,json.dumps(payload,ensure_ascii=False),NOW()));c.commit()
def get_action(id):
    with connect() as c:r=c.execute('SELECT * FROM actions WHERE id=?',(id,)).fetchone();return dict(r) if r else None
def update_action(id,status,approved_by=None):
    with connect() as c:c.execute('UPDATE actions SET status=?,approved_by=COALESCE(?,approved_by) WHERE id=?',(status,approved_by,id));c.commit()
def get_run(id):
    with connect() as c:
        r=c.execute('SELECT * FROM runs WHERE id=?',(id,)).fetchone()
        if not r:return None
        out=dict(r);out['payload']=json.loads(out['payload']);out['actions']=[dict(x) for x in c.execute('SELECT * FROM actions WHERE run_id=? ORDER BY created_at',(id,))];out['receipts']=[dict(x) for x in c.execute('SELECT r.* FROM receipts r JOIN actions a ON a.id=r.action_id WHERE a.run_id=? ORDER BY r.created_at',(id,))];return out
