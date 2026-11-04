"""SQLite persistence for analysed meetings (standard library only)."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meetings (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    meeting_date TEXT,
    snippet TEXT NOT NULL,
    transcript TEXT NOT NULL,
    counts_json TEXT NOT NULL,
    analysis_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_meetings_created ON meetings(created_at DESC);
"""


@contextmanager
def connect():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_meeting(analysis: dict) -> dict:
    meeting_id = uuid.uuid4().hex[:12]
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    analysis = {**analysis, "meeting_id": meeting_id, "created_at": created}
    ov = analysis["overview"]
    counts = {k: ov[k] for k in ("sentences", "participants", "action_items", "decisions", "issues_open", "needs_review")}
    snippet = analysis["summary"]["overview"]
    with connect() as c:
        c.execute(
            "INSERT INTO meetings (id,title,created_at,meeting_date,snippet,transcript,counts_json,analysis_json) VALUES (?,?,?,?,?,?,?,?)",
            (meeting_id, analysis["title"], created, analysis.get("meeting_date"), snippet,
             analysis["transcript"], json.dumps(counts), json.dumps(analysis)),
        )
    return analysis


def get_meeting(meeting_id: str) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT analysis_json, id, created_at FROM meetings WHERE id=?", (meeting_id,)).fetchone()
    if not row:
        return None
    a = json.loads(row["analysis_json"])
    a["meeting_id"], a["created_at"] = row["id"], row["created_at"]
    return a


def list_meetings(q: str | None = None, limit: int = 100) -> list[dict]:
    sql = "SELECT id,title,created_at,meeting_date,snippet,counts_json FROM meetings"
    args: list = []
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        sql += " WHERE lower(title) LIKE ? OR lower(transcript) LIKE ? OR lower(snippet) LIKE ?"
        args += [like, like, like]
    sql += " ORDER BY created_at DESC LIMIT ?"
    args.append(limit)
    with connect() as c:
        rows = c.execute(sql, args).fetchall()
    return [{"id": r["id"], "title": r["title"], "created_at": r["created_at"], "meeting_date": r["meeting_date"],
             "snippet": r["snippet"], "counts": json.loads(r["counts_json"])} for r in rows]


def delete_meeting(meeting_id: str) -> bool:
    with connect() as c:
        cur = c.execute("DELETE FROM meetings WHERE id=?", (meeting_id,))
        return cur.rowcount > 0
