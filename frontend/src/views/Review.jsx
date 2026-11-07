import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Loader, fmtDays } from "../components/common.jsx";

const GRADES = [
  { g: 1, label: "Again", cls: "bad", key: "again" },
  { g: 2, label: "Hard", cls: "warn", key: "hard" },
  { g: 3, label: "Good", cls: "good", key: "good" },
  { g: 4, label: "Easy", cls: "secondary", key: "easy" },
];

export default function Review({ planId, topicId = null, onDone, onExit, showToast }) {
  const [cards, setCards] = useState(null);
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [reviewed, setReviewed] = useState(0);

  useEffect(() => {
    api.dueFlashcards(planId, topicId).then((r) => setCards(r.cards));
  }, [planId, topicId]);

  if (!cards) return <Loader msg="Fetching cards due for review…" />;

  if (cards.length === 0) {
    return (
      <div className="card empty">
        <div className="big-emoji">🎉</div>
        <h2>All caught up!</h2>
        <p className="muted">No flashcards are due right now. The FSRS scheduler will surface them again at the optimal moment.</p>
        <button className="btn" onClick={onDone}>Back to dashboard</button>
      </div>
    );
  }

  if (idx >= cards.length) {
    return (
      <div className="card empty">
        <div className="big-emoji">✅</div>
        <h2>Reviewed {reviewed} card{reviewed === 1 ? "" : "s"}!</h2>
        <p className="muted">Great work. Spaced repetition is doing its job behind the scenes.</p>
        <div className="row center" style={{ justifyContent: "center" }}>
          <button className="btn" onClick={onDone}>Dashboard</button>
          <button className="btn secondary" onClick={onExit}>Keep studying</button>
        </div>
      </div>
    );
  }

  const card = cards[idx];

  async function grade(g) {
    const res = await api.reviewFlashcard(card.id, g);
    setReviewed((n) => n + 1);
    setFlipped(false);
    setIdx((i) => i + 1);
    showToast(`Next review in ${fmtDays(res.next_review_days)}`, "good");
  }

  return (
    <>
      <div className="row spread">
        <button className="btn outline small" onClick={onExit}>← Exit</button>
        <span className="muted">Card {idx + 1} of {cards.length}</span>
      </div>
      <div className="progress thin" style={{ margin: "10px 0 20px" }}>
        <span style={{ width: `${(idx / cards.length) * 100}%` }} />
      </div>

      <div className={"flashcard" + (flipped ? " flipped" : "")} onClick={() => setFlipped((f) => !f)}>
        <div className="inner">
          <div className="face front"><div>{card.front}</div><div className="hint">click to reveal</div></div>
          <div className="face back"><div>{card.back}</div><div className="hint">how well did you recall it?</div></div>
        </div>
      </div>

      <div className="grade-row" style={{ visibility: flipped ? "visible" : "hidden" }}>
        {GRADES.map((gr) => (
          <button key={gr.g} className={"btn " + gr.cls} onClick={() => grade(gr.g)}>
            {gr.label}
            <small>{fmtDays(card.preview[gr.key])}</small>
          </button>
        ))}
      </div>

      <p className="muted small center" style={{ marginTop: 16 }}>
        Rate your recall honestly — FSRS uses it to schedule the next review.
      </p>
    </>
  );
}
