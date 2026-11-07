import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Loader } from "../components/common.jsx";
import Calendar from "../components/Calendar.jsx";

export default function CalendarView({ planId, onOpenTopic }) {
  const [plan, setPlan] = useState(null);
  const [progress, setProgress] = useState(null);
  const [meta, setMeta] = useState(null);

  useEffect(() => {
    let alive = true;
    Promise.all([api.getPlan(planId), api.progress(planId)]).then(([p, prog]) => {
      if (!alive) return;
      setPlan(p.plan);
      setMeta(p);
      setProgress(prog);
    });
    return () => { alive = false; };
  }, [planId]);

  if (!plan) return <Loader msg="Loading your calendar…" />;

  return (
    <>
      <h1>📅 Study Calendar</h1>
      <p className="muted">
        Your plan laid out day by day. Milestones (🏁) and your projected finish (🎓) are pinned to
        their dates{meta.deadline ? ", along with your deadline (⏰)" : ""}. Click any study day to
        see its topics and jump straight into a lesson.
      </p>

      <div className="grid cols-4" style={{ marginBottom: 4 }}>
        <div className="card stat"><div className="num">{plan.total_days}</div><div className="lbl">Study days</div></div>
        <div className="card stat"><div className="num">{plan.milestones.length}</div><div className="lbl">Weekly milestones</div></div>
        <div className="card stat"><div className="num" style={{ fontSize: 22 }}>{plan.completion_date}</div><div className="lbl">Projected finish</div></div>
        <div className="card stat"><div className="num" style={{ fontSize: 22 }}>{meta.deadline || "—"}</div><div className="lbl">Your deadline</div></div>
      </div>

      <div className="card">
        <Calendar plan={plan} progress={progress} onOpenTopic={onOpenTopic} />
      </div>

      <div className="card">
        <h3>All milestones</h3>
        {plan.milestones.map((m) => (
          <div key={m.week} className="milestone">
            <div className="w">Week {m.week} · {m.start_date} → {m.end_date}</div>
            <div>{m.goal}</div>
            <div className="muted small">{m.planned_minutes} min planned</div>
          </div>
        ))}
      </div>
    </>
  );
}
