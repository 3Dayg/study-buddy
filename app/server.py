"""
StudyBuddy HTTP server — pure Python stdlib (http.server), no frameworks.

Serves a JSON REST API under /api/* and the static single-page frontend from
the React build in app/web_dist/ if present, else the vanilla app/web/.
Run with:  python -m app.server   (or python app/server.py)
"""

from __future__ import annotations

import json
import os
import re
import traceback
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from app import db
from app.engine import content as content_engine
from app.engine import planner as planner_engine
from app.engine import progress as progress_engine
from app.engine.fsrs import FSRS, CardState

def _resolve_web_dir():
    """Prefer the built React app (app/web_dist) if present; otherwise serve the
    zero-build vanilla frontend (app/web). This lets the app run with just Python
    OR as the compiled React SPA after `npm run build`."""
    here = os.path.dirname(__file__)
    override = os.environ.get("STUDYBUDDY_WEB_DIR")
    if override and os.path.isdir(override):
        return override
    dist = os.path.join(here, "web_dist")
    if os.path.isfile(os.path.join(dist, "index.html")):
        return dist
    return os.path.join(here, "web")


WEB_DIR = _resolve_web_dir()
fsrs = FSRS()

# (method, compiled-regex) -> handler
ROUTES = []


def route(method, pattern):
    rx = re.compile("^" + pattern + "$")

    def deco(fn):
        ROUTES.append((method, rx, fn))
        return fn
    return deco


class ApiError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


# ---------------------------------------------------------------------------
# API handlers
# ---------------------------------------------------------------------------

@route("POST", r"/api/plans")
def create_plan(handler, match, body):
    goal = (body.get("goal") or "").strip()
    if not goal:
        raise ApiError(400, "A learning goal is required.")
    level = (body.get("level") or "beginner").lower()
    if level not in ("beginner", "intermediate", "advanced"):
        level = "beginner"
    try:
        daily_minutes = int(body.get("daily_minutes") or 30)
    except (TypeError, ValueError):
        daily_minutes = 30
    daily_minutes = max(10, min(daily_minutes, 600))

    deadline_str = (body.get("deadline") or "").strip() or None
    deadline = None
    if deadline_str:
        try:
            deadline = date.fromisoformat(deadline_str)
        except ValueError:
            raise ApiError(400, "Deadline must be YYYY-MM-DD.")

    curriculum = content_engine.build_curriculum(goal)
    start = datetime.now(timezone.utc).date()
    plan = planner_engine.generate_plan(curriculum, level, daily_minutes, start, deadline)

    plan_id = db.create_plan(goal, level, daily_minutes,
                             deadline.isoformat() if deadline else None,
                             curriculum, plan)
    return {"plan_id": plan_id,
            "curriculum_generated": curriculum.get("generated", False),
            "plan": plan,
            "curriculum_title": curriculum["title"]}


@route("GET", r"/api/plans")
def list_plans(handler, match, body):
    return {"plans": db.list_plans()}


@route("GET", r"/api/plans/(\d+)")
def get_plan(handler, match, body):
    plan_id = int(match.group(1))
    rec = db.get_plan(plan_id)
    if not rec:
        raise ApiError(404, "Plan not found.")
    # strip heavy lesson bodies from the curriculum for the overview payload
    cur = rec["curriculum"]
    topic_index = [
        {"id": t["id"], "title": t["title"], "domain": t.get("domain", ""),
         "difficulty": t.get("difficulty", 1), "objective": t.get("objective", ""),
         "num_quiz": len(t.get("quiz", [])), "num_flashcards": len(t.get("flashcards", []))}
        for t in cur["topics"]
    ]
    return {
        "plan_id": plan_id,
        "goal": rec["goal"],
        "level": rec["level"],
        "daily_minutes": rec["daily_minutes"],
        "deadline": rec["deadline"],
        "curriculum_title": cur["title"],
        "curriculum_summary": cur.get("summary", ""),
        "curriculum_generated": cur.get("generated", False),
        "domains": cur.get("domains", []),
        "topics": topic_index,
        "plan": rec["plan"],
    }


@route("GET", r"/api/plans/(\d+)/topics/([\w\-]+)")
def get_topic(handler, match, body):
    plan_id = int(match.group(1))
    topic_id = match.group(2)
    rec = db.get_plan(plan_id)
    if not rec:
        raise ApiError(404, "Plan not found.")
    topic = next((t for t in rec["curriculum"]["topics"] if t["id"] == topic_id), None)
    if not topic:
        raise ApiError(404, "Topic not found.")
    # Return lesson + examples + quiz WITHOUT the answers (answers checked server-side).
    quiz_public = [
        {"q": q["q"], "choices": q["choices"]} for q in topic.get("quiz", [])
    ]
    tp = db.get_topic_progress(plan_id).get(topic_id, {})
    return {
        "topic_id": topic_id,
        "title": topic["title"],
        "domain": topic.get("domain", ""),
        "objective": topic.get("objective", ""),
        "lesson": topic.get("lesson", []),
        "examples": topic.get("examples", []),
        "quiz": quiz_public,
        "num_flashcards": len(topic.get("flashcards", [])),
        "lesson_done": bool(tp.get("lesson_done")),
        "best_quiz": tp.get("best_quiz"),
    }


@route("POST", r"/api/plans/(\d+)/topics/([\w\-]+)/lesson-complete")
def complete_lesson(handler, match, body):
    plan_id = int(match.group(1))
    topic_id = match.group(2)
    if not db.get_plan(plan_id):
        raise ApiError(404, "Plan not found.")
    db.mark_lesson_done(plan_id, topic_id)
    db.log_study(plan_id, "lesson", topic_id, float(body.get("minutes") or 0))
    return {"ok": True}


@route("POST", r"/api/plans/(\d+)/topics/([\w\-]+)/quiz")
def submit_quiz(handler, match, body):
    plan_id = int(match.group(1))
    topic_id = match.group(2)
    rec = db.get_plan(plan_id)
    if not rec:
        raise ApiError(404, "Plan not found.")
    topic = next((t for t in rec["curriculum"]["topics"] if t["id"] == topic_id), None)
    if not topic:
        raise ApiError(404, "Topic not found.")
    answers = body.get("answers") or []
    quiz = topic.get("quiz", [])
    if len(answers) != len(quiz):
        raise ApiError(400, "Answer count does not match quiz length.")
    correct = 0
    detail = []
    for i, q in enumerate(quiz):
        chosen = answers[i]
        is_correct = (chosen == q["answer"])
        if is_correct:
            correct += 1
        detail.append({
            "q": q["q"],
            "chosen": chosen,
            "correct_answer": q["answer"],
            "is_correct": is_correct,
            "explain": q.get("explain", ""),
            "choices": q["choices"],
        })
    total = len(quiz)
    score = correct / total if total else 0.0
    db.record_quiz(plan_id, topic_id, score, correct, total, detail)
    db.log_study(plan_id, "quiz", topic_id, float(body.get("minutes") or 0))
    return {"score": score, "correct": correct, "total": total, "detail": detail}


@route("GET", r"/api/plans/(\d+)/flashcards/due")
def flashcards_due(handler, match, body):
    plan_id = int(match.group(1))
    if not db.get_plan(plan_id):
        raise ApiError(404, "Plan not found.")
    topic_id = _query_param(handler, "topic_id")
    due = progress_engine.due_flashcards(plan_id, topic_id)
    cards = []
    for fc in due:
        state = CardState.from_dict(fc["fsrs"])
        cards.append({
            "id": fc["id"],
            "topic_id": fc["topic_id"],
            "front": fc["front"],
            "back": fc["back"],
            "state": state.state,
            "preview": fsrs.preview(state),
        })
    return {"due_count": len(cards), "cards": cards}


@route("POST", r"/api/flashcards/(\d+)/review")
def review_flashcard(handler, match, body):
    fc_id = int(match.group(1))
    fc = db.get_flashcard(fc_id)
    if not fc:
        raise ApiError(404, "Flashcard not found.")
    try:
        grade = int(body.get("grade"))
    except (TypeError, ValueError):
        raise ApiError(400, "grade (1-4) is required.")
    if grade not in (1, 2, 3, 4):
        raise ApiError(400, "grade must be 1..4.")
    state = CardState.from_dict(fc["fsrs"])
    new_state = fsrs.review(state, grade)
    db.update_flashcard_fsrs(fc_id, new_state.to_dict())
    db.log_study(fc["plan_id"], "flashcard", fc["topic_id"], float(body.get("minutes") or 0))
    next_days = None
    if new_state.due and new_state.last_review:
        next_days = round(
            (datetime.fromisoformat(new_state.due) -
             datetime.fromisoformat(new_state.last_review)).total_seconds() / 86400.0, 2)
    return {"ok": True, "next_review_days": next_days,
            "state": new_state.state, "stability": round(new_state.stability, 2)}


@route("GET", r"/api/plans/(\d+)/progress")
def plan_progress(handler, match, body):
    plan_id = int(match.group(1))
    if not db.get_plan(plan_id):
        raise ApiError(404, "Plan not found.")
    return progress_engine.build_summary(plan_id)


@route("GET", r"/api/plans/(\d+)/adapt")
def plan_adapt(handler, match, body):
    plan_id = int(match.group(1))
    rec = db.get_plan(plan_id)
    if not rec:
        raise ApiError(404, "Plan not found.")
    summary = progress_engine.build_summary(plan_id)
    deadline = date.fromisoformat(rec["deadline"]) if rec["deadline"] else None
    days_elapsed = 0
    try:
        start = date.fromisoformat(rec["plan"]["start_date"])
        days_elapsed = (datetime.now(timezone.utc).date() - start).days
    except Exception:
        pass
    progress_input = {
        "avg_quiz_score": summary.get("avg_quiz_score"),
        "weak_topics": summary.get("weak_topics"),
        "retention": summary.get("retention"),
        "minutes_studied_last7": summary.get("minutes_studied_last7"),
        "days_elapsed": days_elapsed,
        "topics_completed": summary.get("topics_mastered"),
        "topics_total": summary.get("total_topics"),
    }
    return planner_engine.recommend_adaptations(progress_input, rec["plan"], deadline)


@route("POST", r"/api/plans/(\d+)/replan")
def replan(handler, match, body):
    """Regenerate the remaining plan with new settings (apply an adaptation)."""
    plan_id = int(match.group(1))
    rec = db.get_plan(plan_id)
    if not rec:
        raise ApiError(404, "Plan not found.")
    daily_minutes = rec["daily_minutes"]
    if body.get("daily_minutes"):
        daily_minutes = max(10, min(int(body["daily_minutes"]), 600))
    deadline = date.fromisoformat(rec["deadline"]) if rec["deadline"] else None
    if "deadline" in body:
        deadline = date.fromisoformat(body["deadline"]) if body["deadline"] else None

    start = datetime.now(timezone.utc).date()
    new_plan = planner_engine.generate_plan(rec["curriculum"], rec["level"],
                                            daily_minutes, start, deadline)
    db.update_plan_json(plan_id, new_plan)
    db.update_plan_settings(plan_id, daily_minutes=daily_minutes,
                            deadline=deadline.isoformat() if deadline else None)
    return {"ok": True, "plan": new_plan, "daily_minutes": daily_minutes,
            "deadline": deadline.isoformat() if deadline else None}


# ---------------------------------------------------------------------------
# HTTP plumbing
# ---------------------------------------------------------------------------

def _query_param(handler, name):
    from urllib.parse import parse_qs
    q = parse_qs(urlparse(handler.path).query)
    v = q.get(name)
    return v[0] if v else None


class Handler(BaseHTTPRequestHandler):
    server_version = "StudyBuddy/1.0"

    def log_message(self, fmt, *args):
        # concise request logging
        print("[%s] %s" % (self.log_date_time_string(), fmt % args))

    def _send_json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _dispatch(self, method):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            return self._handle_api(method, path)
        if method == "GET":
            return self._serve_static(path)
        self._send_json(405, {"error": "Method not allowed"})

    def _handle_api(self, method, path):
        body = {}
        if method in ("POST", "PUT", "PATCH"):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            if raw:
                try:
                    body = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    return self._send_json(400, {"error": "Invalid JSON body"})
        for m, rx, fn in ROUTES:
            if m != method:
                continue
            mt = rx.match(path)
            if mt:
                try:
                    result = fn(self, mt, body)
                    return self._send_json(200, result)
                except ApiError as e:
                    return self._send_json(e.status, {"error": e.message})
                except Exception:
                    traceback.print_exc()
                    return self._send_json(500, {"error": "Internal server error"})
        self._send_json(404, {"error": "Not found"})

    def _serve_static(self, path):
        if path == "/" or path == "":
            path = "/index.html"
        # prevent path traversal
        safe = os.path.normpath(path).lstrip("/\\")
        full = os.path.join(WEB_DIR, safe)
        if not os.path.abspath(full).startswith(os.path.abspath(WEB_DIR)) or not os.path.isfile(full):
            # SPA fallback
            full = os.path.join(WEB_DIR, "index.html")
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json",
            ".svg": "image/svg+xml",
        }.get(os.path.splitext(full)[1], "application/octet-stream")
        try:
            with open(full, "rb") as f:
                data = f.read()
        except OSError:
            return self._send_json(404, {"error": "Not found"})
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")


def main():
    db.init_db()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"StudyBuddy running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
