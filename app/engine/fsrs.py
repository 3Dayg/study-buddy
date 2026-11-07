"""
FSRS (Free Spaced Repetition Scheduler) — pure-Python, dependency-free implementation.

This is a faithful implementation of the FSRS v4/4.5 scheduling algorithm used to
decide *when* a flashcard should next be reviewed, based on how well the learner
recalled it. It is the spaced-repetition brain of the study app.

Model summary
-------------
Each card tracks two latent variables:
  * stability (S): the number of days until retrievability decays to ~90%.
  * difficulty (D): intrinsic hardness of the card, in the range [1, 10].

On every review the learner gives a grade:
  1 = Again (forgot)   2 = Hard   3 = Good   4 = Easy

From the grade, the elapsed time since the last review, and the current (S, D),
FSRS updates stability and difficulty and computes the next interval so that the
predicted probability of recall at the next review equals the desired retention
(default 0.90).

The 17 default weights below come from the FSRS reference model. They are plain
numbers; no external library is required.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

# FSRS-4.5 default parameters (w0..w18 subset used here uses the 17-weight form w0..w16
# plus the two short-term weights w17,w18 from 4.5).
DEFAULT_WEIGHTS = (
    0.4072, 1.1829, 3.1262, 15.4722, 7.2102, 0.5316, 1.0651, 0.0234,
    1.616, 0.1544, 1.0824, 1.9813, 0.0953, 0.2975, 2.2042, 0.2407,
    2.9466, 0.5034, 0.6567,
)

DECAY = -0.5
FACTOR = 19.0 / 81.0  # derived so that R(S, S) == 0.9

# Rating constants
AGAIN = 1
HARD = 2
GOOD = 3
EASY = 4

# Card states
STATE_NEW = "new"
STATE_LEARNING = "learning"
STATE_REVIEW = "review"
STATE_RELEARNING = "relearning"


def retrievability(elapsed_days: float, stability: float) -> float:
    """Probability of recall after `elapsed_days` given current stability."""
    if stability <= 0:
        return 0.0
    return (1.0 + FACTOR * elapsed_days / stability) ** DECAY


def interval_for_retention(stability: float, request_retention: float) -> float:
    """Days until retrievability decays to `request_retention`."""
    return (stability / FACTOR) * (request_retention ** (1.0 / DECAY) - 1.0)


@dataclass
class CardState:
    """Serializable scheduling state for a single flashcard."""
    stability: float = 0.0
    difficulty: float = 0.0
    state: str = STATE_NEW
    reps: int = 0
    lapses: int = 0
    last_review: Optional[str] = None  # ISO timestamp
    due: Optional[str] = None          # ISO timestamp

    def to_dict(self) -> dict:
        return {
            "stability": round(self.stability, 6),
            "difficulty": round(self.difficulty, 6),
            "state": self.state,
            "reps": self.reps,
            "lapses": self.lapses,
            "last_review": self.last_review,
            "due": self.due,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CardState":
        return cls(
            stability=float(d.get("stability") or 0.0),
            difficulty=float(d.get("difficulty") or 0.0),
            state=d.get("state") or STATE_NEW,
            reps=int(d.get("reps") or 0),
            lapses=int(d.get("lapses") or 0),
            last_review=d.get("last_review"),
            due=d.get("due"),
        )


class FSRS:
    def __init__(self, weights=DEFAULT_WEIGHTS, request_retention: float = 0.90,
                 maximum_interval: int = 36500):
        self.w = tuple(weights)
        self.request_retention = request_retention
        self.maximum_interval = maximum_interval

    # --- initial values for brand-new cards ----------------------------------
    def _init_stability(self, grade: int) -> float:
        return max(self.w[grade - 1], 0.1)

    def _init_difficulty(self, grade: int) -> float:
        d = self.w[4] - math.exp(self.w[5] * (grade - 1)) + 1.0
        return self._clamp_difficulty(d)

    @staticmethod
    def _clamp_difficulty(d: float) -> float:
        return min(max(d, 1.0), 10.0)

    # --- difficulty & stability updates ---------------------------------------
    def _next_difficulty(self, d: float, grade: int) -> float:
        delta = -self.w[6] * (grade - 3)
        next_d = d + delta * ((10.0 - d) / 9.0)
        # mean reversion toward the "easy" difficulty anchor
        d0_easy = self._init_difficulty(EASY)
        next_d = self.w[7] * d0_easy + (1.0 - self.w[7]) * next_d
        return self._clamp_difficulty(next_d)

    def _next_recall_stability(self, d: float, s: float, r: float, grade: int) -> float:
        hard_penalty = self.w[15] if grade == HARD else 1.0
        easy_bonus = self.w[16] if grade == EASY else 1.0
        return s * (
            1.0
            + math.exp(self.w[8])
            * (11.0 - d)
            * (s ** -self.w[9])
            * (math.exp(self.w[10] * (1.0 - r)) - 1.0)
            * hard_penalty
            * easy_bonus
        )

    def _next_forget_stability(self, d: float, s: float, r: float) -> float:
        return (
            self.w[11]
            * (d ** -self.w[12])
            * (((s + 1.0) ** self.w[13]) - 1.0)
            * math.exp(self.w[14] * (1.0 - r))
        )

    def _short_term_stability(self, s: float, grade: int) -> float:
        return s * math.exp(self.w[17] * (grade - 3 + self.w[18]))

    # --- public scheduling entry point ----------------------------------------
    def review(self, card: CardState, grade: int, now: Optional[datetime] = None) -> CardState:
        """Return a new CardState after applying a review with `grade` at `now`."""
        if grade not in (AGAIN, HARD, GOOD, EASY):
            raise ValueError("grade must be 1..4")
        now = now or datetime.now(timezone.utc)

        new = CardState(
            stability=card.stability,
            difficulty=card.difficulty,
            state=card.state,
            reps=card.reps,
            lapses=card.lapses,
            last_review=card.last_review,
            due=card.due,
        )

        if card.state == STATE_NEW:
            new.difficulty = self._init_difficulty(grade)
            new.stability = self._init_stability(grade)
            new.reps = 1
            if grade == AGAIN:
                new.state = STATE_LEARNING
            elif grade in (GOOD, HARD):
                new.state = STATE_LEARNING if grade == HARD else STATE_REVIEW
            else:
                new.state = STATE_REVIEW
        else:
            elapsed = 0.0
            if card.last_review:
                last = datetime.fromisoformat(card.last_review)
                elapsed = max((now - last).total_seconds() / 86400.0, 0.0)
            r = retrievability(elapsed, card.stability)

            new.difficulty = self._next_difficulty(card.difficulty, grade)
            new.reps = card.reps + 1

            if grade == AGAIN:
                new.lapses = card.lapses + 1
                new.stability = self._next_forget_stability(new.difficulty, card.stability, r)
                new.state = STATE_RELEARNING
            else:
                if elapsed < 1.0 and card.state in (STATE_LEARNING, STATE_RELEARNING):
                    # same-day short-term review
                    new.stability = self._short_term_stability(card.stability, grade)
                else:
                    new.stability = self._next_recall_stability(
                        new.difficulty, card.stability, r, grade
                    )
                new.state = STATE_REVIEW

        interval_days = self._compute_interval(new)
        new.last_review = now.isoformat()
        new.due = (now + timedelta(days=interval_days)).isoformat()
        return new

    def _compute_interval(self, card: CardState) -> float:
        if card.state in (STATE_LEARNING, STATE_RELEARNING):
            # short learning steps measured in fractions of a day
            return max(interval_for_retention(card.stability, self.request_retention), 1.0 / 1440.0 * 10)
        raw = interval_for_retention(card.stability, self.request_retention)
        clamped = min(max(round(raw), 1), self.maximum_interval)
        return float(clamped)

    def preview(self, card: CardState, now: Optional[datetime] = None) -> dict:
        """Return the next interval (in days) for each possible grade — used to label buttons."""
        now = now or datetime.now(timezone.utc)
        out = {}
        for grade, name in ((AGAIN, "again"), (HARD, "hard"), (GOOD, "good"), (EASY, "easy")):
            nxt = self.review(card, grade, now)
            if nxt.due and nxt.last_review:
                days = (datetime.fromisoformat(nxt.due) - datetime.fromisoformat(nxt.last_review)).total_seconds() / 86400.0
            else:
                days = 0.0
            out[name] = round(days, 2)
        return out
