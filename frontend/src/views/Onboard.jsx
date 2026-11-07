import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { Loader } from "../components/common.jsx";

const EXAMPLES = [
  "AWS Certified Cloud Practitioner (CLF-C02)",
  "Learn Python for data analysis",
  "Spanish for travel",
  "Intro to machine learning",
];

export default function Onboard({ onCreated, showToast }) {
  const [goal, setGoal] = useState("");
  const [level, setLevel] = useState("beginner");
  const [minutes, setMinutes] = useState(45);
  const [deadline, setDeadline] = useState("");
  const [busy, setBusy] = useState(false);
  const [plans, setPlans] = useState([]);

  useEffect(() => {
    api.listPlans().then((r) => setPlans(r.plans || [])).catch(() => {});
  }, []);

  async function submit() {
    if (!goal.trim()) return showToast("Please enter a learning goal", "bad");
    setBusy(true);
    try {
      const r = await api.createPlan({
        goal: goal.trim(),
        level,
        daily_minutes: parseInt(minutes || "45", 10),
        deadline: deadline || null,
      });
      showToast(r.curriculum_generated ? "Custom plan generated!" : "Expert curriculum loaded!", "good");
      onCreated(r.plan_id);
    } catch (e) {
      showToast(e.message, "bad");
      setBusy(false);
    }
  }

  if (busy) return <Loader msg="Designing your personalized study plan…" />;

  return (
    <>
      <div className="hero">
        <div className="tag">Your personal AI study tutor</div>
        <h1>Go from <span className="gradient-text">zero to mastery</span>, one day at a time.</h1>
        <p className="muted">
          Tell me what you want to learn. I'll build a personalized plan with a calendar, teach each
          topic, quiz you, and schedule spaced-repetition flashcards that adapt to how you perform.
        </p>
      </div>

      <div className="card" style={{ maxWidth: 620, margin: "0 auto" }}>
        <label>What do you want to learn?</label>
        <input
          value={goal}
          placeholder="e.g. AWS Certified Cloud Practitioner (CLF-C02)"
          onChange={(e) => setGoal(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
        />
        <div className="tag-row">
          {EXAMPLES.map((ex) => (
            <span key={ex} className="chip" style={{ cursor: "pointer" }} onClick={() => setGoal(ex)}>{ex}</span>
          ))}
        </div>

        <label>Your current knowledge level</label>
        <div className="pills">
          {["beginner", "intermediate", "advanced"].map((lv) => (
            <div key={lv} className={"pill" + (level === lv ? " active" : "")} onClick={() => setLevel(lv)}>
              {lv[0].toUpperCase() + lv.slice(1)}
            </div>
          ))}
        </div>

        <div className="grid cols-2">
          <div>
            <label>Daily time commitment (minutes)</label>
            <input type="number" min="10" max="600" value={minutes} onChange={(e) => setMinutes(e.target.value)} />
          </div>
          <div>
            <label>Target deadline (optional)</label>
            <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
          </div>
        </div>

        <button className="btn block" style={{ marginTop: 22 }} onClick={submit}>✨ Build my study plan</button>
      </div>

      {plans.length > 0 && (
        <div className="card" style={{ maxWidth: 620, margin: "18px auto 0" }}>
          <h3>Resume a plan</h3>
          {plans.slice(0, 5).map((p) => (
            <div key={p.id} className="topic" onClick={() => onCreated(p.id)}>
              <div className="ic">📘</div>
              <div className="meta">
                <div className="t">{p.goal}</div>
                <div className="status">{p.level} · {p.daily_minutes} min/day{p.deadline ? ` · due ${p.deadline}` : ""}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
