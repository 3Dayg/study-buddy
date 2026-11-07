"""
Self-contained integration test: spins up the real HTTP server in a background
thread, exercises the full API the way the frontend does, and asserts the key
behaviors (plan generation, lessons, quizzes, FSRS flashcard scheduling,
progress, adaptation, replan). Run: python tests/test_api.py
"""
import json
import os
import sys
import threading
import time
import urllib.request
import urllib.error

# Use a throwaway DB so the test is isolated and repeatable.
TEST_DB = "/tmp/studybuddy_apitest.sqlite3"
for suffix in ("", "-wal", "-shm"):
    try:
        os.remove(TEST_DB + suffix)
    except OSError:
        pass
os.environ["STUDYBUDDY_DB"] = TEST_DB

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import ThreadingHTTPServer  # noqa: E402
from app import db  # noqa: E402
from app.server import Handler  # noqa: E402

PORT = 8731
BASE = f"http://127.0.0.1:{PORT}"


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    def _parse(raw):
        try:
            return json.loads(raw.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return raw  # non-JSON (e.g. static HTML)
    try:
        with urllib.request.urlopen(r, timeout=5) as resp:
            return resp.status, _parse(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, _parse(e.read())


def main():
    db.init_db()
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)
    passed = 0

    def check(name, cond):
        nonlocal passed
        if cond:
            passed += 1
            print(f"  PASS  {name}")
        else:
            print(f"  FAIL  {name}")
            raise SystemExit(f"Test failed: {name}")

    try:
        # static frontend served
        st, _ = req("GET", "/")
        check("GET / serves app (200)", st == 200)

        # create a plan for the brief's example goal
        st, r = req("POST", "/api/plans", {
            "goal": "AWS Certified Cloud Practitioner CLF-C02",
            "level": "beginner", "daily_minutes": 45, "deadline": "2026-12-20"})
        check("create plan 200", st == 200)
        check("matched built-in curriculum (not generated)", r["curriculum_generated"] is False)
        check("plan has days", r["plan"]["total_days"] > 0)
        check("plan has milestones", len(r["plan"]["milestones"]) >= 1)
        check("plan has completion date", bool(r["plan"]["completion_date"]))
        pid = r["plan_id"]

        # generated curriculum for a custom goal
        st, r2 = req("POST", "/api/plans", {"goal": "Learn Rust for systems programming",
                                            "level": "intermediate", "daily_minutes": 30})
        check("custom goal generates curriculum", r2["curriculum_generated"] is True)

        # fetch plan overview
        st, p = req("GET", f"/api/plans/{pid}")
        check("get plan 200", st == 200)
        first_topic = p["topics"][0]["id"]

        # fetch a topic (lesson + quiz without answers)
        st, topic = req("GET", f"/api/plans/{pid}/topics/{first_topic}")
        check("topic has lesson sections", len(topic["lesson"]) > 0)
        check("quiz hidden answers (no 'answer' key)",
              all("answer" not in q for q in topic["quiz"]))

        # complete the lesson
        st, r = req("POST", f"/api/plans/{pid}/topics/{first_topic}/lesson-complete",
                    {"minutes": 12})
        check("lesson-complete ok", r.get("ok") is True)

        # submit a perfect quiz (choose correct answers by reading from DB)
        rec = db.get_plan(pid)
        qtopic = next(t for t in rec["curriculum"]["topics"] if t["id"] == first_topic)
        correct_answers = [q["answer"] for q in qtopic["quiz"]]
        st, qr = req("POST", f"/api/plans/{pid}/topics/{first_topic}/quiz",
                     {"answers": correct_answers, "minutes": 5})
        check("quiz scored 100%", abs(qr["score"] - 1.0) < 1e-9)
        check("quiz returns explanations", all("explain" in d for d in qr["detail"]))

        # wrong-answer quiz on another topic -> becomes weak
        t2id = p["topics"][2]["id"]
        rec = db.get_plan(pid)
        qt2 = next(t for t in rec["curriculum"]["topics"] if t["id"] == t2id)
        wrong = [(q["answer"] + 1) % len(q["choices"]) for q in qt2["quiz"]]
        st, qr2 = req("POST", f"/api/plans/{pid}/topics/{t2id}/quiz", {"answers": wrong, "minutes": 5})
        check("wrong quiz scored 0%", qr2["score"] == 0.0)

        # flashcards due
        st, due = req("GET", f"/api/plans/{pid}/flashcards/due")
        check("flashcards are due (new cards)", due["due_count"] > 0)
        card = due["cards"][0]
        check("flashcard has grade preview intervals", set(card["preview"]) == {"again", "hard", "good", "easy"})

        # review a flashcard 'Good' and confirm it leaves the due set
        st, rv = req("POST", f"/api/flashcards/{card['id']}/review", {"grade": 3})
        check("review returns next interval", rv["next_review_days"] is not None and rv["next_review_days"] >= 1)
        st, due2 = req("GET", f"/api/plans/{pid}/flashcards/due")
        check("reviewed card no longer due", due2["due_count"] == due["due_count"] - 1)

        # 'Again' schedules a very short interval
        c2 = due2["cards"][0]
        st, rv2 = req("POST", f"/api/flashcards/{c2['id']}/review", {"grade": 1})
        check("'Again' schedules short interval (<1 day)", rv2["next_review_days"] < 1)

        # progress summary reflects our actions
        st, prog = req("GET", f"/api/plans/{pid}/progress")
        check("progress: 1 topic mastered", prog["topics_mastered"] == 1)
        check("progress: has weak topic", len(prog["weak_topics"]) >= 1)
        check("progress: avg quiz score between 0 and 1", 0 <= prog["avg_quiz_score"] <= 1)
        check("progress: completion pct computed", 0 <= prog["completion_pct"] <= 100)

        # adaptation recommends something sensible
        st, adapt = req("GET", f"/api/plans/{pid}/adapt")
        check("adapt returns suggested daily minutes", adapt["suggested_daily_minutes"] >= 10)
        check("adapt returns actions", len(adapt["actions"]) >= 1)
        check("adapt flags weak topics for review", len(adapt["review_topics"]) >= 1)

        # replan with more time
        st, rp = req("POST", f"/api/plans/{pid}/replan", {"daily_minutes": 90})
        check("replan ok", rp.get("ok") is True)
        check("replan changed daily minutes", rp["daily_minutes"] == 90)

        # error handling
        st, _ = req("GET", "/api/plans/99999")
        check("missing plan -> 404", st == 404)
        st, _ = req("POST", "/api/plans", {"goal": ""})
        check("empty goal -> 400", st == 400)

        print(f"\nAll {passed} checks passed ✅")
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
