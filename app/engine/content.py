"""
Content engine — the "AI tutor" brain.

Given a learning goal it produces a structured curriculum: topics, each with a
multi-section lesson, worked examples, a multiple-choice quiz, and flashcards.

Design note (honesty about "AI"):
There is no external LLM available in this environment (the sandbox has no
outbound network / no model API). So the tutor is a deterministic content
*generator*: it uses a hand-authored knowledge base for known goals (e.g. the
AWS CLF-C02 exam) and a template-driven generator for arbitrary goals. The
generated material is pedagogically structured (concept -> example -> check for
understanding -> spaced recall) exactly like an AI tutor would scaffold it, and
the scheduling / adaptation around it is driven by real algorithms (FSRS and the
adaptive planner). Swapping in a hosted LLM later only requires replacing
`generate_generic_curriculum`.
"""

from __future__ import annotations

import re
from typing import Optional

from app.data.curriculum_aws_clf_c02 import CURRICULUM as AWS_CLF_C02

BUILTIN = {
    "aws-clf-c02": AWS_CLF_C02,
}

# Keywords that let us auto-match a free-text goal to a built-in curriculum.
BUILTIN_MATCHERS = [
    (re.compile(r"\b(clf[- ]?c02|cloud practitioner|aws.*practitioner)\b", re.I), "aws-clf-c02"),
]


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "topic"


def match_builtin(goal: str) -> Optional[str]:
    for pattern, cid in BUILTIN_MATCHERS:
        if pattern.search(goal or ""):
            return cid
    return None


# ---------------------------------------------------------------------------
# Generic curriculum generation for arbitrary goals.
# ---------------------------------------------------------------------------

def _split_into_subjects(goal: str) -> list[str]:
    """Derive a reasonable list of sub-topics from a free-form goal string."""
    cleaned = re.sub(r"\b(learn|study|master|understand|the basics of|basics of|intro to|"
                     r"introduction to|how to|for beginners)\b", "", goal, flags=re.I).strip()
    cleaned = cleaned.strip(" .:-") or goal

    phases = [
        ("Foundations of {t}", 1,
         "Core vocabulary, mental models, and why {t} matters."),
        ("Key Concepts in {t}", 1,
         "The handful of ideas that explain most of {t}."),
        ("How {t} Works in Practice", 2,
         "Step-by-step mechanics and a worked walkthrough of {t}."),
        ("Common Patterns & Tools in {t}", 2,
         "The patterns, tools, and vocabulary practitioners use in {t}."),
        ("Pitfalls & Best Practices in {t}", 2,
         "Mistakes beginners make in {t} and how experts avoid them."),
        ("Applying {t} to a Real Project", 3,
         "Putting the pieces together to solve a realistic {t} problem."),
    ]
    return [(t.format(t=cleaned), d, desc.format(t=cleaned)) for (t, d, desc) in phases]


def generate_generic_curriculum(goal: str) -> dict:
    """Build a structured curriculum for any goal using pedagogical templates."""
    subject = goal.strip()
    topics = []
    for idx, (title, difficulty, objective) in enumerate(_split_into_subjects(goal)):
        tid = f"{slugify(subject)}-{idx+1}"
        topics.append({
            "id": tid,
            "domain": "Core Curriculum",
            "title": title,
            "difficulty": difficulty,
            "base_minutes": 30 + difficulty * 8,
            "objective": objective,
            "lesson": [
                {"heading": "What you'll learn",
                 "body": f"In this topic we build up '{title}'. {objective} Read each section, "
                         f"then try the example, the quiz, and the flashcards — that "
                         f"concept → practice → recall loop is what makes it stick."},
                {"heading": "Core idea",
                 "body": f"Focus on the single most important idea behind '{title}'. Ask "
                         f"yourself: what problem does this solve, and what would go wrong "
                         f"without it? Write the answer in your own words before moving on."},
                {"heading": "Connect it to what you know",
                 "body": f"Relate '{title}' to something you already understand. Analogies turn "
                         f"abstract material into memory. If you can teach it to a friend in two "
                         f"sentences, you've understood it."},
            ],
            "examples": [
                {"title": f"Worked example: {title}",
                 "body": f"Pick a concrete, realistic scenario for '{subject}' that exercises "
                         f"this topic, work it end to end, and note each decision you make and "
                         f"why. Concrete examples are the scaffolding memory hangs on."},
            ],
            "quiz": [
                {"q": f"What is the single most important reason '{title}' matters?",
                 "choices": [
                     "It is purely decorative",
                     "It solves a real problem the subject depends on",
                     "It only matters for exams",
                     "It is never used in practice",
                 ],
                 "answer": 1,
                 "explain": "Every durable concept earns its place by solving a real problem — "
                            "anchor your understanding to that problem."},
                {"q": f"What's the best way to confirm you understand '{title}'?",
                 "choices": [
                     "Re-read it silently",
                     "Highlight the text",
                     "Explain it in your own words / teach it",
                     "Skip ahead",
                 ],
                 "answer": 2,
                 "explain": "Active recall and self-explanation beat passive re-reading for "
                            "retention (the testing effect)."},
            ],
            "flashcards": [
                {"front": f"In one sentence, what is '{title}' about?",
                 "back": objective},
                {"front": f"Why does '{title}' matter?",
                 "back": "Because it solves a concrete problem the rest of the subject builds on "
                         "— state that problem."},
            ],
        })

    return {
        "id": slugify(subject),
        "title": subject,
        "summary": f"A personalized, structured path to learning: {subject}.",
        "domains": ["Core Curriculum"],
        "topics": topics,
        "generated": True,
    }


def build_curriculum(goal: str) -> dict:
    """Resolve a goal to a curriculum: a built-in one if matched, else generated."""
    cid = match_builtin(goal)
    if cid:
        cur = dict(BUILTIN[cid])
        cur["generated"] = False
        return cur
    return generate_generic_curriculum(goal)


def topic_total_quiz_count(topic: dict) -> int:
    return len(topic.get("quiz", []))


def topic_total_flashcards(topic: dict) -> int:
    return len(topic.get("flashcards", []))
