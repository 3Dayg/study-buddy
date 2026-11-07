import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Loader, Stat, ProgressBar } from "../components/common.jsx";
import Calendar from "../components/Calendar.jsx";

export default function Dashboard({ planId, onNavigate, onOpenTopic }) {
  const [s, setS] = useState(null);
  const [plan, setPlan] = useState(null);

  useEffect(() => {
    let alive = true;
    Promise.all([api.progress(planId), api.getPlan(planId)]).then(([prog, p]) => {
      if (!alive) return;
      setS(prog);
      setPlan(p.plan);
    });
    return () => { alive = false; };
  }, [planId]);

  if (!s || !plan) return <Loader msg="Loading your dashboard…" />;

  const pct = (v) => (v === null || v === undefined ? "—" : Math.round(v * 100) + "%");
  const clsFor = (v, hi = 0.8, lo = 0.6) =>
    v === null || v === undefined ? "" : v >= hi ? "good" : v >= lo ? "warn" : "bad";

  // next upcoming milestone (first whose end_date >= today)
  const todayISO = new Date().toISOString().slice(0, 10);
  const nextMilestone = (plan.milestones || []).find((m) => m.end_date >= todayISO) || null;

  return (
    <>
      <div className="row spread">
        <div>
          <h1>{s.goal}</h1>
          <p className="muted">
            {s.level} · {s.daily_minutes} min/day
            {s.deadline ? ` · deadline ${s.deadline}` : ""}
            {s.completion_date ? ` · projected finish ${s.completion_date}` : ""}
          </p>
        </div>
        {s.deadline && (
          <div>
            <span className={"chip " + (s.on_track ? "mastered" : "weak")}>
              {s.on_track ? "On track ✓" : "Behind schedule"}
            </span>
          </div>
        )}
      </div>

      <div className="card">
        <div className="row spread">
          <h3>Overall mastery</h3>
          <span className="muted">{s.topics_mastered}/{s.total_topics} topics mastered</span>
        </div>
        <ProgressBar pct={s.completion_pct} />
        <div className="muted small" style={{ marginTop: 8 }}>{s.completion_pct}% complete</div>
      </div>

      <div className="grid cols-4">
        <Stat num={`${s.lessons_done}/${s.total_topics}`} lbl="Lessons done" />
        <Stat num={pct(s.avg_quiz_score)} lbl="Avg quiz score" cls={clsFor(s.avg_quiz_score)} />
        <Stat num={pct(s.retention)} lbl="Flashcard recall" cls={clsFor(s.retention, 0.85, 0.7)} />
        <Stat num={s.due_flashcards} lbl="Cards due now" cls={s.due_flashcards > 0 ? "warn" : "good"} />
      </div>

      {/* Calendar widget on the dashboard */}
      <div className="card">
        <div className="row spread" style={{ marginBottom: 12 }}>
          <h3>📅 Study calendar</h3>
          <button className="btn outline small" onClick={() => onNavigate("calendar")}>Open full calendar →</button>
        </div>
        {nextMilestone && (
          <div className="milestone" style={{ marginBottom: 14 }}>
            <div className="w">Next milestone · Week {nextMilestone.week} · by {nextMilestone.end_date}</div>
            <div>{nextMilestone.goal}</div>
          </div>
        )}
        <Calendar plan={plan} progress={s} mini onOpenTopic={onOpenTopic} />
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h3>Jump back in</h3>
          <button className="btn block" style={{ marginBottom: 10 }} onClick={() => onNavigate("plan")}>📚 Continue studying</button>
          {s.due_flashcards > 0 ? (
            <button className="btn block warn" onClick={() => onNavigate("review")}>🔁 Review {s.due_flashcards} due flashcards</button>
          ) : (
            <div className="muted small center">No flashcards due — you're caught up! 🎉</div>
          )}
        </div>
        <div className="card">
          <h3>Study time</h3>
          <div className="row spread"><span className="muted">Last 7 days</span><b>{s.minutes_studied_last7} min</b></div>
          <div className="row spread"><span className="muted">All time</span><b>{s.minutes_studied_total} min</b></div>
          {s.weak_topics.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div className="muted small">Needs work:</div>
              <div className="tag-row">
                {s.weak_topics.map((w) => <span key={w.topic_id} className="chip weak">{w.title}</span>)}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
