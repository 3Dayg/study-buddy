"""
Planner engine — turns a goal + level + deadline + daily time budget into a
concrete, day-by-day study plan with weekly milestones and a projected
completion date. Also contains the ADAPTIVE re-planning logic that adjusts the
remaining plan based on measured performance, flashcard retention, and the time
the learner actually has.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

LEVEL_FACTORS = {
    "beginner": 1.25,   # needs more time per topic
    "intermediate": 1.0,
    "advanced": 0.7,    # moves faster
}


def _level_factor(level: str) -> float:
    return LEVEL_FACTORS.get((level or "beginner").lower(), 1.0)


def estimate_topic_minutes(topic: dict, level: str) -> int:
    base = int(topic.get("base_minutes", 30))
    return max(10, round(base * _level_factor(level)))


def generate_plan(curriculum: dict, level: str, daily_minutes: int,
                  start: date, deadline: date | None) -> dict:
    """
    Pack topics into days without exceeding the daily minute budget, splitting a
    topic across days if it's larger than a day's budget. Returns a plan dict
    with per-day entries, weekly milestones, total time, and a completion date.
    """
    daily_minutes = max(10, int(daily_minutes))
    topics = curriculum["topics"]

    # Build a flat queue of (topic_id, title, minutes-remaining)
    queue = [
        {"topic_id": t["id"], "title": t["title"],
         "remaining": estimate_topic_minutes(t, level),
         "domain": t.get("domain", "")}
        for t in topics
    ]
    total_minutes = sum(item["remaining"] for item in queue)

    days = []
    cur_day = start
    day_index = 0
    qi = 0
    # guard against pathological loops
    safety = 0
    while qi < len(queue):
        safety += 1
        if safety > 100000:
            break
        budget = daily_minutes
        day_entry = {"date": cur_day.isoformat(), "day_index": day_index, "items": [],
                     "planned_minutes": 0}
        while qi < len(queue) and budget > 0:
            item = queue[qi]
            take = min(item["remaining"], budget)
            # Avoid tiny slivers: if what's left after taking is < 8 min, take it all.
            if 0 < item["remaining"] - take < 8 and item["remaining"] <= budget:
                take = item["remaining"]
            day_entry["items"].append({
                "topic_id": item["topic_id"],
                "title": item["title"],
                "domain": item["domain"],
                "minutes": take,
                "partial": take < item["remaining"],
            })
            day_entry["planned_minutes"] += take
            budget -= take
            item["remaining"] -= take
            if item["remaining"] <= 0:
                qi += 1
        days.append(day_entry)
        day_index += 1
        cur_day = cur_day + timedelta(days=1)

    completion_date = days[-1]["date"] if days else start.isoformat()

    # Weekly milestones: group days into 7-day weeks, summarize topics completed.
    milestones = _build_milestones(days, topics)

    plan = {
        "level": level,
        "daily_minutes": daily_minutes,
        "start_date": start.isoformat(),
        "deadline": deadline.isoformat() if deadline else None,
        "total_minutes": total_minutes,
        "total_days": len(days),
        "completion_date": completion_date,
        "days": days,
        "milestones": milestones,
        "on_track": _is_on_track(completion_date, deadline),
    }
    return plan


def _build_milestones(days: list[dict], topics: list[dict]) -> list[dict]:
    title_by_id = {t["id"]: t["title"] for t in topics}
    milestones = []
    for wk_start in range(0, len(days), 7):
        week_days = days[wk_start: wk_start + 7]
        if not week_days:
            continue
        # topics that FINISH in this week (last day their final partial lands)
        finished = []
        seen = set()
        for d in week_days:
            for it in d["items"]:
                if not it["partial"] and it["topic_id"] not in seen:
                    finished.append(title_by_id.get(it["topic_id"], it["topic_id"]))
                    seen.add(it["topic_id"])
        minutes = sum(d["planned_minutes"] for d in week_days)
        milestones.append({
            "week": wk_start // 7 + 1,
            "start_date": week_days[0]["date"],
            "end_date": week_days[-1]["date"],
            "planned_minutes": minutes,
            "goal": f"Complete: {', '.join(finished)}" if finished
                    else "Continue working through current topics",
            "topics_completed": finished,
        })
    return milestones


def _is_on_track(completion_date: str, deadline: date | None) -> bool:
    if not deadline:
        return True
    return date.fromisoformat(completion_date) <= deadline


# ---------------------------------------------------------------------------
# Adaptive re-planning
# ---------------------------------------------------------------------------

def recommend_adaptations(progress: dict, plan: dict, deadline: date | None,
                          today: date | None = None) -> dict:
    """
    Inspect measured performance and propose concrete adjustments.

    `progress` is expected to contain:
      - avg_quiz_score: float 0..1 (recent quiz accuracy)
      - weak_topics: list of {topic_id, title, score}
      - retention: float 0..1 (fraction of due flashcards recalled)
      - minutes_studied_last7: int (actual studied minutes in last 7 days)
      - days_elapsed: int
      - topics_completed: int
      - topics_total: int

    Returns a dict with:
      - suggested_daily_minutes
      - review_topics (topics to re-teach / drill)
      - message (human summary)
      - pace ('ahead' | 'on_track' | 'behind')
      - actions (list of structured recommendations)
    """
    today = today or datetime.now(timezone.utc).date()
    actions = []

    avg_quiz = progress.get("avg_quiz_score")
    retention = progress.get("retention")
    weak = progress.get("weak_topics") or []
    planned_daily = plan.get("daily_minutes", 30)
    actual7 = progress.get("minutes_studied_last7")
    topics_completed = progress.get("topics_completed", 0)
    topics_total = progress.get("topics_total", len(plan.get("days", [])) or 1)

    # 1) Mastery-driven: low quiz scores -> insert review, slow down.
    suggested_daily = planned_daily
    if avg_quiz is not None and avg_quiz < 0.6:
        suggested_daily = round(planned_daily * 1.2)
        actions.append({
            "type": "reinforce",
            "detail": f"Recent quiz accuracy is {round(avg_quiz*100)}%. Add review time and "
                      f"re-study weak topics before advancing.",
        })
    elif avg_quiz is not None and avg_quiz >= 0.9:
        suggested_daily = max(10, round(planned_daily * 0.9))
        actions.append({
            "type": "accelerate",
            "detail": f"Quiz accuracy is {round(avg_quiz*100)}%. You can safely pick up the "
                      f"pace or shorten sessions.",
        })

    # 2) Retention-driven: poor flashcard recall -> prioritize spaced review.
    if retention is not None and retention < 0.7:
        actions.append({
            "type": "retention",
            "detail": f"Flashcard recall is {round(retention*100)}%. Prioritize due flashcards "
                      f"daily; the FSRS scheduler will tighten intervals automatically.",
        })

    # 3) Time-driven: actual study time diverging from plan.
    if actual7 is not None:
        expected7 = planned_daily * 7
        if expected7 > 0 and actual7 < expected7 * 0.6:
            # Learner is studying much less than planned -> stretch the plan or raise daily goal.
            actions.append({
                "type": "time",
                "detail": f"You studied ~{actual7} min in the last 7 days vs a planned "
                          f"{expected7}. Either extend the deadline or commit a bit more each day.",
            })

    # 4) Pace vs deadline.
    pace = "on_track"
    if deadline and topics_total:
        total_days = max((deadline - today).days, 0)
        remaining_topics = max(topics_total - topics_completed, 0)
        if total_days == 0 and remaining_topics > 0:
            pace = "behind"
        elif total_days > 0:
            needed_per_day = remaining_topics / total_days
            # crude but useful: >1 topic/day usually means behind
            if needed_per_day > 1.3:
                pace = "behind"
                suggested_daily = round(suggested_daily * 1.25)
                actions.append({
                    "type": "deadline",
                    "detail": f"To hit your deadline you need to cover ~{remaining_topics} "
                              f"topics in {total_days} days. Increase daily study time.",
                })
            elif needed_per_day < 0.5:
                pace = "ahead"

    review_topics = [{"topic_id": w.get("topic_id"), "title": w.get("title")} for w in weak[:3]]

    if not actions:
        actions.append({"type": "steady",
                        "detail": "You're progressing well — keep the current rhythm."})

    message = _summarize(pace, avg_quiz, retention, review_topics)

    return {
        "suggested_daily_minutes": max(10, int(suggested_daily)),
        "review_topics": review_topics,
        "pace": pace,
        "actions": actions,
        "message": message,
    }


def _summarize(pace, avg_quiz, retention, review_topics) -> str:
    bits = []
    if pace == "behind":
        bits.append("You're a little behind schedule.")
    elif pace == "ahead":
        bits.append("You're ahead of schedule — nice work.")
    else:
        bits.append("You're on track.")
    if avg_quiz is not None:
        bits.append(f"Quiz accuracy {round(avg_quiz*100)}%.")
    if retention is not None:
        bits.append(f"Flashcard recall {round(retention*100)}%.")
    if review_topics:
        names = ", ".join(t["title"] for t in review_topics if t.get("title"))
        if names:
            bits.append(f"Focus your next review on: {names}.")
    return " ".join(bits)
