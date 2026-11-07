# 📚 StudyBuddy — Your Personal AI Study Tutor

StudyBuddy takes a learning goal (e.g. *AWS Certified Cloud Practitioner CLF-C02*),
your current level, a deadline, and how much time you can give each day — and turns
it into a guided path from zero knowledge to mastery.

It builds a **personalized day-by-day study plan**, **teaches each topic** with
structured lessons and worked examples, **quizzes** you to find gaps, schedules
**flashcards with the FSRS spaced-repetition algorithm**, **tracks your progress**,
and **adapts the plan** based on how you actually perform.

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  Set a goal  │→ │ Learn topics │→ │  Quiz + cards │→ │  Adapt plan  │
└──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

## Quick start

No dependencies to install — it runs on the Python standard library alone
(Python 3.10+).

```bash
./run.sh
# or:  python3 -m app.server
```

Then open **http://127.0.0.1:8000** in your browser.

## Features

| Feature | What it does |
|---|---|
| 🎯 **Personalized plan** | Packs topics into daily sessions within your time budget, produces weekly milestones and a projected completion date, and flags whether you'll hit your deadline. |
| 📖 **Lessons** | Each topic is taught as structured sections + worked examples, following a concept → example → check-for-understanding → recall loop. |
| 📝 **Quizzes** | Multiple-choice questions with instant grading and explanations. Answers are checked server-side (never sent to the client). |
| 🔁 **Flashcards (FSRS)** | A faithful implementation of the **FSRS** spaced-repetition scheduler decides exactly when each card is next due, based on your recall (Again / Hard / Good / Easy). |
| 📊 **Progress tracking** | Mastery %, average quiz score, flashcard recall, study time, and per-topic status. |
| ♻️ **Adaptive tutor** | Analyzes mastery, retention, pace vs deadline, and actual study time, then recommends and applies concrete adjustments (re-planning the remaining schedule). |

## Architecture

Zero third-party dependencies. Backend is Python stdlib (`http.server` + `sqlite3`);
frontend is vanilla HTML/CSS/JS served by the backend. The whole thing runs offline.

```
app/
├── server.py              # http.server REST API + static file serving
├── db.py                  # sqlite3 persistence (plans, progress, quizzes, flashcards, study log)
├── data/
│   └── curriculum_aws_clf_c02.py   # hand-authored AWS CLF-C02 knowledge base
├── engine/
│   ├── content.py         # the "tutor": picks a built-in curriculum or generates one
│   ├── planner.py         # day-by-day plan + milestones + adaptive re-planning
│   ├── fsrs.py            # FSRS spaced-repetition scheduler (pure Python)
│   └── progress.py        # progress aggregation + retention estimation
└── web/                   # index.html, styles.css, app.js (SPA, no build step)
tests/
├── test_fsrs.py           # unit tests for the scheduling algorithm
└── test_api.py            # full end-to-end API integration test
```

### A note on "AI-powered"

This build runs in an environment with **no outbound network and no LLM API**, so
there is no hosted model behind it. The "AI tutor" is therefore a **deterministic
content engine**: it ships an expert-authored curriculum for recognized goals
(the AWS CLF-C02 exam) and a template-driven generator for any other goal, and it
wraps that content in genuinely algorithmic machinery — a real **FSRS** scheduler
and a real **adaptive planner** that respond to your measured performance.

The content layer is cleanly isolated in `app/engine/content.py`. Dropping in a
hosted LLM later means replacing a single function (`generate_generic_curriculum`)
— everything else (scheduling, adaptation, progress, UI) stays exactly as-is.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/plans` | Create a plan from `{goal, level, daily_minutes, deadline}` |
| GET | `/api/plans/{id}` | Plan overview + topic index + schedule |
| GET | `/api/plans/{id}/topics/{tid}` | Lesson, examples, quiz (answers hidden) |
| POST | `/api/plans/{id}/topics/{tid}/lesson-complete` | Mark a lesson done |
| POST | `/api/plans/{id}/topics/{tid}/quiz` | Submit answers, get score + explanations |
| GET | `/api/plans/{id}/flashcards/due` | Cards due now (+ next-interval preview per grade) |
| POST | `/api/flashcards/{id}/review` | Grade a card (1–4); FSRS reschedules it |
| GET | `/api/plans/{id}/progress` | Full progress snapshot |
| GET | `/api/plans/{id}/adapt` | Adaptive recommendations |
| POST | `/api/plans/{id}/replan` | Regenerate the remaining plan with new settings |

## Tests

```bash
python3 tests/test_fsrs.py   # 15 checks — scheduling algorithm properties
python3 tests/test_api.py    # 30 checks — full HTTP API end to end
```

## How FSRS scheduling works here

Each card tracks **stability** (days until recall drops to ~90%) and **difficulty**
(1–10). After each review the algorithm updates both and sets the next due date so
your predicted recall at review time equals the target retention (default 90%).
Grading **Again** shortens the interval and bumps difficulty; **Good/Easy** grow
stability and stretch the interval — so well-known cards reappear rarely and shaky
ones come back fast.
