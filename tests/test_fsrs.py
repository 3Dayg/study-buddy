"""
Unit tests for the FSRS spaced-repetition engine. These lock in the core
algorithmic properties so a future change can't silently break scheduling.
Run: python tests/test_fsrs.py
"""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine.fsrs import (FSRS, CardState, AGAIN, HARD, GOOD, EASY,
                             retrievability, interval_for_retention,
                             STATE_REVIEW, STATE_RELEARNING)

passed = 0


def check(name, cond):
    global passed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        raise SystemExit(f"  FAIL  {name}")


def main():
    f = FSRS()
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)

    # Retrievability is 1.0 at t=0 and ~0.9 at t=stability.
    check("R(0) == 1.0", abs(retrievability(0, 5) - 1.0) < 1e-9)
    check("R(stability) ~= 0.9", abs(retrievability(5, 5) - 0.9) < 1e-3)
    check("R decreases over time", retrievability(10, 5) < retrievability(2, 5))

    # interval_for_retention inverts retrievability: interval at 0.9 == stability.
    check("interval@0.9 == stability", abs(interval_for_retention(5, 0.9) - 5) < 1e-6)

    # New-card grades: higher grade => longer first interval.
    ivals = {}
    for g, name in ((AGAIN, "again"), (HARD, "hard"), (GOOD, "good"), (EASY, "easy")):
        c = f.review(CardState(), g, t0)
        days = (datetime.fromisoformat(c.due) - datetime.fromisoformat(c.last_review)).total_seconds() / 86400.0
        ivals[name] = days
    check("new: again < hard < good < easy intervals",
          ivals["again"] < ivals["hard"] < ivals["good"] < ivals["easy"])

    # Successful reviews grow stability; intervals expand.
    c = f.review(CardState(), GOOD, t0)
    s1 = c.stability
    c = f.review(c, GOOD, t0 + timedelta(days=int(round(s1))))
    check("stability grows after successful review", c.stability > s1)
    check("state is review after good reviews", c.state == STATE_REVIEW)

    # A lapse (Again) reduces stability, increments lapses, enters relearning.
    before = c.stability
    c = f.review(c, AGAIN, t0 + timedelta(days=30))
    check("lapse reduces stability", c.stability < before)
    check("lapse increments lapse count", c.lapses == 1)
    check("lapse -> relearning state", c.state == STATE_RELEARNING)

    # Difficulty stays within [1, 10].
    c = CardState()
    t = t0
    for i in range(20):
        c = f.review(c, AGAIN if i % 2 else EASY, t)
        t += timedelta(days=1)
        check(f"difficulty in [1,10] (step {i})", 1.0 <= c.difficulty <= 10.0) if i == 19 else None
    check("difficulty bounded after many reviews", 1.0 <= c.difficulty <= 10.0)

    # Easy produces a longer interval than Good from the same state.
    base = f.review(CardState(), GOOD, t0)
    later = t0 + timedelta(days=int(round(base.stability)))
    good = f.review(base, GOOD, later)
    easy = f.review(base, EASY, later)
    gd = (datetime.fromisoformat(good.due) - datetime.fromisoformat(good.last_review)).days
    ed = (datetime.fromisoformat(easy.due) - datetime.fromisoformat(easy.last_review)).days
    check("easy interval >= good interval", ed >= gd)

    # Serialization round-trips.
    d = c.to_dict()
    c2 = CardState.from_dict(d)
    check("CardState serializes round-trip", c2.to_dict() == d)

    # Preview returns four labeled intervals.
    pv = f.preview(CardState(), t0)
    check("preview has 4 grade keys", set(pv) == {"again", "hard", "good", "easy"})

    print(f"\nAll {passed} FSRS checks passed ✅")


if __name__ == "__main__":
    main()
