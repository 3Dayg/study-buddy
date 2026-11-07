import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Loader } from "../components/common.jsx";

const PACE = {
  ahead: ["mastered", "Ahead of schedule"],
  on_track: ["done", "On track"],
  behind: ["weak", "Behind schedule"],
};

export default function Adapt({ planId, onReplanned, onOpenTopic, showToast }) {
  const [rec, setRec] = useState(null);
  const [meta, setMeta] = useState(null);
  const [minutes, setMinutes] = useState("");
  const [deadline, setDeadline] = useState("");

  useEffect(() => {
    let alive = true;
    Promise.all([api.adapt(planId), api.getPlan(planId)]).then(([r, p]) => {
      if (!alive) return;
      setRec(r);
      setMeta(p);
      setMinutes(r.suggested_daily_minutes);
      setDeadline(p.deadline || "");
    });
    return () => { alive = false; };
  }, [planId]);

  if (!rec || !meta) return <Loader msg="Analyzing your performance…" />;

  const [chipCls, chipLabel] = PACE[rec.pace] || ["", rec.pace];

  async function replan() {
    const r = await api.replan(planId, { daily_minutes: parseInt(minutes, 10), deadline: deadline || null });
    showToast(`Plan updated — new finish date ${r.plan.completion_date}`, "good");
    onReplanned();
  }

  return (
    <>
      <h1>Adaptive tutor</h1>
      <p className="muted">Your plan adjusts to how you actually perform — mastery, retention, and the time you put in.</p>

      <div className="card">
        <div className="row spread">
          <h3>Assessment</h3>
          <span className={"chip " + chipCls}>{chipLabel}</span>
        </div>
        <p>{rec.message}</p>
        <div style={{ marginTop: 12 }}>
          {rec.actions.map((a, i) => (
            <div key={i} className="action">
              <div className="k">{a.type}</div>
              <div>{a.detail}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h3>Apply an adjustment</h3>
        <p className="muted small">
          Current: {meta.daily_minutes} min/day{meta.deadline ? `, deadline ${meta.deadline}` : ", no deadline"}.
          Suggested daily time: {rec.suggested_daily_minutes} min.
        </p>
        <div className="grid cols-2">
          <div>
            <label>New daily minutes</label>
            <input type="number" min="10" max="600" value={minutes} onChange={(e) => setMinutes(e.target.value)} />
          </div>
          <div>
            <label>New deadline (optional)</label>
            <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
          </div>
        </div>
        <button className="btn" style={{ marginTop: 16 }} onClick={replan}>♻️ Re-plan with these settings</button>
      </div>

      {rec.review_topics.length > 0 && (
        <div className="card">
          <h3>Recommended review</h3>
          <p className="muted small">These topics have the lowest quiz scores — revisit them next.</p>
          {rec.review_topics.map((t) => (
            <div key={t.topic_id} className="topic" onClick={() => onOpenTopic(t.topic_id)}>
              <div className="ic">🔁</div>
              <div className="meta"><div className="t">{t.title}</div></div>
              <div className="muted">›</div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
