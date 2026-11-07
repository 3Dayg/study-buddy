import React, { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { Loader } from "../components/common.jsx";

export default function Topic({ planId, topicId, onBack, onStudyFlashcards, showToast }) {
  const [t, setT] = useState(null);
  const startedRef = useRef(Date.now());

  useEffect(() => {
    startedRef.current = Date.now();
    api.getTopic(planId, topicId).then(setT);
  }, [planId, topicId]);

  if (!t) return <Loader msg="Opening lesson…" />;

  return (
    <>
      <div className="row" style={{ marginBottom: 8 }}>
        <button className="btn outline small" onClick={onBack}>← Back to plan</button>
      </div>
      <div>
        <div className="muted small">{t.domain}</div>
        <h1>{t.title}</h1>
        {t.objective && <p className="muted">🎯 {t.objective}</p>}
      </div>

      <div className="card">
        <h2>📖 Lesson</h2>
        {t.lesson.map((s, i) => (
          <div key={i} className="lesson-section">
            <h3>{s.heading}</h3>
            <div className="body">{s.body}</div>
          </div>
        ))}
        {t.examples.length > 0 && <h3 style={{ marginTop: 18 }}>Worked examples</h3>}
        {t.examples.map((e, i) => (
          <div key={i} className="example">
            <div className="title">💡 {e.title}</div>
            <div>{e.body}</div>
          </div>
        ))}
        <LessonCompleteButton planId={planId} topicId={topicId} startedRef={startedRef} showToast={showToast} initial={t.lesson_done} />
      </div>

      <Quiz planId={planId} topicId={topicId} quiz={t.quiz} showToast={showToast} />

      <div className="card center">
        <h3>🔁 Flashcards</h3>
        <p className="muted">{t.num_flashcards} spaced-repetition cards for this topic.</p>
        <button className="btn" onClick={() => onStudyFlashcards(topicId)}>Study these flashcards</button>
      </div>
    </>
  );
}

function LessonCompleteButton({ planId, topicId, startedRef, showToast, initial }) {
  const [done, setDone] = useState(initial);
  return (
    <button
      className="btn good"
      style={{ marginTop: 12 }}
      disabled={done}
      onClick={async () => {
        const mins = Math.round((Date.now() - startedRef.current) / 60000);
        await api.completeLesson(planId, topicId, mins);
        setDone(true);
        showToast("Lesson complete! Now test yourself below.", "good");
      }}
    >
      {done ? "✓ Lesson marked complete" : "Mark lesson complete ✓"}
    </button>
  );
}

function Quiz({ planId, topicId, quiz, showToast }) {
  const [chosen, setChosen] = useState(() => new Array(quiz.length).fill(null));
  const [result, setResult] = useState(null);
  const startedRef = useRef(Date.now());

  if (!quiz.length) {
    return <div className="card"><h2>📝 Quick quiz</h2><p className="muted">No quiz for this topic.</p></div>;
  }

  async function submit() {
    if (chosen.includes(null)) return showToast("Answer all questions first", "bad");
    const mins = Math.round((Date.now() - startedRef.current) / 60000);
    const r = await api.submitQuiz(planId, topicId, chosen, mins);
    setResult(r);
  }

  const submitted = !!result;
  const detail = result?.detail || [];

  return (
    <div className="card">
      <h2>📝 Quick quiz</h2>
      {quiz.map((q, qi) => {
        const d = detail[qi];
        return (
          <div key={qi} className="q">
            <div className="prompt">{qi + 1}. {q.q}</div>
            {q.choices.map((c, ci) => {
              let cls = "choice";
              if (!submitted && chosen[qi] === ci) cls += " selected";
              if (submitted && d) {
                if (ci === d.correct_answer) cls += " correct";
                else if (ci === d.chosen && !d.is_correct) cls += " wrong";
              }
              return (
                <div
                  key={ci}
                  className={cls}
                  onClick={() => {
                    if (submitted) return;
                    setChosen((prev) => { const n = [...prev]; n[qi] = ci; return n; });
                  }}
                >
                  {c}
                </div>
              );
            })}
            {submitted && d && <div className="explain">{(d.is_correct ? "✓ " : "✗ ") + d.explain}</div>}
          </div>
        );
      })}

      {!submitted ? (
        <button className="btn" onClick={submit}>Submit answers</button>
      ) : (
        <div className="card stat">
          <div className={"num " + (result.score >= 0.8 ? "good" : result.score >= 0.6 ? "warn" : "bad")}>
            {Math.round(result.score * 100)}%
          </div>
          <div className="lbl">
            {result.correct} / {result.total} correct · {result.score >= 0.8 ? "Mastered! 🌟" : result.score >= 0.6 ? "Good — review the misses" : "Keep studying, you've got this"}
          </div>
          <button
            className="btn secondary"
            style={{ marginTop: 12 }}
            onClick={() => { setChosen(new Array(quiz.length).fill(null)); setResult(null); startedRef.current = Date.now(); }}
          >
            Retake quiz
          </button>
        </div>
      )}
    </div>
  );
}
