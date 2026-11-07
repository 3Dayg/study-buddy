import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Loader } from "../components/common.jsx";

export default function Plan({ planId, onOpenTopic }) {
  const [p, setP] = useState(null);
  const [prog, setProg] = useState(null);

  useEffect(() => {
    let alive = true;
    Promise.all([api.getPlan(planId), api.progress(planId)]).then(([plan, progress]) => {
      if (!alive) return;
      setP(plan);
      setProg(progress);
    });
    return () => { alive = false; };
  }, [planId]);

  if (!p || !prog) return <Loader msg="Loading your study plan…" />;

  const progById = {};
  prog.topics.forEach((t) => (progById[t.topic_id] = t));

  const byDomain = {};
  p.topics.forEach((t) => ((byDomain[t.domain || "Topics"] ||= []).push(t)));

  const TopicRow = ({ t }) => {
    const pr = progById[t.id] || {};
    let ic = "⚪";
    const chips = [];
    if (pr.mastered) { ic = "🌟"; chips.push(<span key="m" className="chip mastered">Mastered</span>); }
    else if (pr.lesson_done) { ic = "📖"; chips.push(<span key="l" className="chip done">Lesson done</span>); }
    if (pr.best_quiz !== null && pr.best_quiz !== undefined)
      chips.push(<span key="q" className={"chip" + (pr.best_quiz < 0.7 ? " weak" : "")}>Quiz {Math.round(pr.best_quiz * 100)}%</span>);
    chips.push(<span key="f" className="chip">{t.num_flashcards} cards</span>);
    return (
      <div className="topic" onClick={() => onOpenTopic(t.id)}>
        <div className="ic">{ic}</div>
        <div className="meta">
          <div className="t">{t.title}</div>
          <div className="status">{chips}</div>
        </div>
        <div className="muted small">›</div>
      </div>
    );
  };

  return (
    <>
      <div>
        <h1>{p.curriculum_title}</h1>
        <p className="muted">{p.curriculum_summary}</p>
        <p className="small" style={{ color: "var(--brand-2)" }}>
          {p.curriculum_generated ? "✨ This curriculum was generated for your custom goal." : "📗 Expert-authored curriculum."}
        </p>
      </div>

      <div className="card">
        <div className="row spread">
          <h3>Milestones</h3>
          <span className="muted small">{p.plan.total_days} study days · finish {p.plan.completion_date}</span>
        </div>
        {p.plan.milestones.map((m) => (
          <div key={m.week} className="milestone">
            <div className="w">Week {m.week} · {m.start_date} → {m.end_date}</div>
            <div>{m.goal}</div>
            <div className="muted small">{m.planned_minutes} min planned</div>
          </div>
        ))}
      </div>

      {Object.entries(byDomain).map(([dom, ts]) => (
        <div key={dom} className="card">
          <h3>{dom}</h3>
          {ts.map((t) => <TopicRow key={t.id} t={t} />)}
        </div>
      ))}

      <details className="card">
        <summary style={{ cursor: "pointer", fontWeight: 700 }}>View full day-by-day schedule</summary>
        <div style={{ marginTop: 14 }}>
          {p.plan.days.map((d) => (
            <div key={d.day_index} className="day">
              <div className="d">Day {d.day_index + 1} · {d.date} · {d.planned_minutes} min</div>
              <div className="muted small">{d.items.map((i) => i.title + (i.partial ? ` (${i.minutes}m)` : "")).join(" · ")}</div>
            </div>
          ))}
        </div>
      </details>
    </>
  );
}
