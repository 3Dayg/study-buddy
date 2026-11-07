"""
SQLite persistence layer (Python stdlib `sqlite3`, no ORM, no dependencies).

Holds study plans, per-topic progress, quiz attempts, and flashcard scheduling
state. The schema is intentionally small; the engines do the heavy lifting and
store their results here as JSON where convenient.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime, timezone

_DB_PATH = os.environ.get("STUDYBUDDY_DB", os.path.join(os.path.dirname(__file__), "..", "studybuddy.sqlite3"))
_local = threading.local()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        _local.conn = conn
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS plans (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    goal          TEXT NOT NULL,
    level         TEXT NOT NULL,
    daily_minutes INTEGER NOT NULL,
    deadline      TEXT,
    curriculum    TEXT NOT NULL,      -- JSON
    plan          TEXT NOT NULL,      -- JSON
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS topic_progress (
    plan_id        INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    topic_id       TEXT NOT NULL,
    lesson_done    INTEGER NOT NULL DEFAULT 0,
    best_quiz      REAL,              -- best quiz score 0..1
    last_quiz      REAL,
    quiz_attempts  INTEGER NOT NULL DEFAULT 0,
    updated_at     TEXT,
    PRIMARY KEY (plan_id, topic_id)
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id    INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    topic_id   TEXT NOT NULL,
    score      REAL NOT NULL,         -- 0..1
    correct    INTEGER NOT NULL,
    total      INTEGER NOT NULL,
    detail     TEXT,                  -- JSON: per-question outcome
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS flashcards (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id     INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    topic_id    TEXT NOT NULL,
    front       TEXT NOT NULL,
    back        TEXT NOT NULL,
    fsrs        TEXT NOT NULL,        -- JSON CardState
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS study_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id    INTEGER NOT NULL REFERENCES plans(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL,         -- 'lesson' | 'quiz' | 'flashcard'
    topic_id   TEXT,
    minutes    REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fc_due ON flashcards(plan_id, topic_id);
CREATE INDEX IF NOT EXISTS idx_log_plan ON study_log(plan_id, created_at);
"""


def init_db() -> None:
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()


# --- plans -----------------------------------------------------------------

def create_plan(goal, level, daily_minutes, deadline, curriculum, plan) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO plans (goal, level, daily_minutes, deadline, curriculum, plan, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (goal, level, daily_minutes, deadline,
         json.dumps(curriculum), json.dumps(plan), _now()),
    )
    plan_id = cur.lastrowid
    # seed topic_progress and flashcards
    for t in curriculum["topics"]:
        conn.execute(
            "INSERT OR IGNORE INTO topic_progress (plan_id, topic_id, updated_at) VALUES (?,?,?)",
            (plan_id, t["id"], _now()),
        )
        for fc in t.get("flashcards", []):
            from app.engine.fsrs import CardState
            conn.execute(
                "INSERT INTO flashcards (plan_id, topic_id, front, back, fsrs, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (plan_id, t["id"], fc["front"], fc["back"],
                 json.dumps(CardState().to_dict()), _now()),
            )
    conn.commit()
    return plan_id


def get_plan(plan_id: int) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["curriculum"] = json.loads(d["curriculum"])
    d["plan"] = json.loads(d["plan"])
    return d


def update_plan_json(plan_id: int, plan: dict) -> None:
    conn = get_conn()
    conn.execute("UPDATE plans SET plan=? WHERE id=?", (json.dumps(plan), plan_id))
    conn.commit()


def update_plan_settings(plan_id: int, daily_minutes=None, deadline=None) -> None:
    conn = get_conn()
    if daily_minutes is not None:
        conn.execute("UPDATE plans SET daily_minutes=? WHERE id=?", (daily_minutes, plan_id))
    if deadline is not None:
        conn.execute("UPDATE plans SET deadline=? WHERE id=?", (deadline, plan_id))
    conn.commit()


def list_plans() -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, goal, level, daily_minutes, deadline, created_at FROM plans ORDER BY id DESC"
    ).fetchall()
    return [dict(r) for r in rows]


# --- progress --------------------------------------------------------------

def mark_lesson_done(plan_id: int, topic_id: str) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE topic_progress SET lesson_done=1, updated_at=? WHERE plan_id=? AND topic_id=?",
        (_now(), plan_id, topic_id),
    )
    conn.commit()


def record_quiz(plan_id: int, topic_id: str, score: float, correct: int,
                total: int, detail: list) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO quiz_attempts (plan_id, topic_id, score, correct, total, detail, created_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (plan_id, topic_id, score, correct, total, json.dumps(detail), _now()),
    )
    row = conn.execute(
        "SELECT best_quiz, quiz_attempts FROM topic_progress WHERE plan_id=? AND topic_id=?",
        (plan_id, topic_id),
    ).fetchone()
    best = score if not row or row["best_quiz"] is None else max(row["best_quiz"], score)
    attempts = (row["quiz_attempts"] if row else 0) + 1
    conn.execute(
        "UPDATE topic_progress SET best_quiz=?, last_quiz=?, quiz_attempts=?, updated_at=? "
        "WHERE plan_id=? AND topic_id=?",
        (best, score, attempts, _now(), plan_id, topic_id),
    )
    conn.commit()


def get_topic_progress(plan_id: int) -> dict[str, dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM topic_progress WHERE plan_id=?", (plan_id,)).fetchall()
    return {r["topic_id"]: dict(r) for r in rows}


# --- flashcards ------------------------------------------------------------

def get_flashcards(plan_id: int, topic_id: str | None = None) -> list[dict]:
    conn = get_conn()
    if topic_id:
        rows = conn.execute(
            "SELECT * FROM flashcards WHERE plan_id=? AND topic_id=? ORDER BY id",
            (plan_id, topic_id),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM flashcards WHERE plan_id=? ORDER BY id", (plan_id,)
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["fsrs"] = json.loads(d["fsrs"])
        out.append(d)
    return out


def get_flashcard(fc_id: int) -> dict | None:
    conn = get_conn()
    r = conn.execute("SELECT * FROM flashcards WHERE id=?", (fc_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["fsrs"] = json.loads(d["fsrs"])
    return d


def update_flashcard_fsrs(fc_id: int, card_state: dict) -> None:
    conn = get_conn()
    conn.execute("UPDATE flashcards SET fsrs=? WHERE id=?", (json.dumps(card_state), fc_id))
    conn.commit()


# --- study log -------------------------------------------------------------

def log_study(plan_id: int, kind: str, topic_id: str | None, minutes: float) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO study_log (plan_id, kind, topic_id, minutes, created_at) VALUES (?,?,?,?,?)",
        (plan_id, kind, topic_id, minutes, _now()),
    )
    conn.commit()


def minutes_studied_since(plan_id: int, iso_since: str) -> float:
    conn = get_conn()
    r = conn.execute(
        "SELECT COALESCE(SUM(minutes),0) AS m FROM study_log WHERE plan_id=? AND created_at>=?",
        (plan_id, iso_since),
    ).fetchone()
    return float(r["m"] or 0)


def recent_quiz_scores(plan_id: int, limit: int = 20) -> list[float]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT score FROM quiz_attempts WHERE plan_id=? ORDER BY id DESC LIMIT ?",
        (plan_id, limit),
    ).fetchall()
    return [r["score"] for r in rows]
