"""
Progress aggregation — computes the numbers shown on the dashboard and the
inputs the adaptive planner consumes (mastery, retention, pace, time spent).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import db
from app.engine.fsrs import CardState, retrievability


def _now():
    return datetime.now(timezone.utc)


def due_flashcards(plan_id: int, topic_id: str | None = None) -> list[dict]:
    """Return flashcards whose `due` time has passed (or that are new)."""
    now = _now()
    out = []
    for fc in db.get_flashcards(plan_id, topic_id):
        state = fc["fsrs"]
        due = state.get("due")
        if not due or datetime.fromisoformat(due) <= now:
            out.append(fc)
    return out


def flashcard_retention(plan_id: int) -> float | None:
    """
    Estimate current retention as the mean predicted retrievability across all
    scheduled (non-new) cards. This reflects how well the schedule is holding
    knowledge in memory right now.
    """
    cards = db.get_flashcards(plan_id)
    now = _now()
    vals = []
    for fc in cards:
        st = CardState.from_dict(fc["fsrs"])
        if st.state == "new" or not st.last_review or st.stability <= 0:
            continue
        elapsed = max((now - datetime.fromisoformat(st.last_review)).total_seconds() / 86400.0, 0.0)
        vals.append(retrievability(elapsed, st.stability))
    if not vals:
        return None
    return sum(vals) / len(vals)


def build_summary(plan_id: int) -> dict:
    """Produce the full progress snapshot used by the dashboard + adaptive engine."""
    rec = db.get_plan(plan_id)
    if not rec:
        return {}
    curriculum = rec["curriculum"]
    plan = rec["plan"]
    topics = curriculum["topics"]
    tp = db.get_topic_progress(plan_id)

    topic_rows = []
    lessons_done = 0
    quizzes_taken = 0
    mastered = 0
    for t in topics:
        p = tp.get(t["id"], {})
        lesson_done = bool(p.get("lesson_done"))
        best = p.get("best_quiz")
        if lesson_done:
            lessons_done += 1
        if p.get("quiz_attempts"):
            quizzes_taken += 1
        is_mastered = lesson_done and best is not None and best >= 0.8
        if is_mastered:
            mastered += 1
        topic_rows.append({
            "topic_id": t["id"],
            "title": t["title"],
            "domain": t.get("domain", ""),
            "difficulty": t.get("difficulty", 1),
            "lesson_done": lesson_done,
            "best_quiz": best,
            "last_quiz": p.get("last_quiz"),
            "quiz_attempts": p.get("quiz_attempts", 0),
            "mastered": is_mastered,
            "num_flashcards": len(t.get("flashcards", [])),
            "num_quiz": len(t.get("quiz", [])),
        })

    total_topics = len(topics)
    scores = db.recent_quiz_scores(plan_id, 20)
    avg_quiz = sum(scores) / len(scores) if scores else None
    retention = flashcard_retention(plan_id)

    # weak topics: have a quiz attempt but best score < 0.7
    weak = [
        {"topic_id": r["topic_id"], "title": r["title"], "score": r["best_quiz"]}
        for r in topic_rows
        if r["best_quiz"] is not None and r["best_quiz"] < 0.7
    ]
    weak.sort(key=lambda x: x["score"])

    due = due_flashcards(plan_id)
    all_cards = db.get_flashcards(plan_id)

    minutes7 = db.minutes_studied_since(
        plan_id, (_now() - timedelta(days=7)).isoformat()
    )
    minutes_total = db.minutes_studied_since(plan_id, "0000-01-01T00:00:00")

    completion_pct = round(100 * mastered / total_topics) if total_topics else 0

    return {
        "plan_id": plan_id,
        "goal": rec["goal"],
        "level": rec["level"],
        "daily_minutes": rec["daily_minutes"],
        "deadline": rec["deadline"],
        "completion_date": plan.get("completion_date"),
        "on_track": plan.get("on_track", True),
        "total_topics": total_topics,
        "lessons_done": lessons_done,
        "quizzes_taken": quizzes_taken,
        "topics_mastered": mastered,
        "completion_pct": completion_pct,
        "avg_quiz_score": avg_quiz,
        "retention": retention,
        "due_flashcards": len(due),
        "total_flashcards": len(all_cards),
        "minutes_studied_last7": round(minutes7),
        "minutes_studied_total": round(minutes_total),
        "weak_topics": weak,
        "topics": topic_rows,
    }
