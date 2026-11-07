import React from "react";

const TABS = [
  { key: "dashboard", label: "Dashboard" },
  { key: "plan", label: "Study Plan" },
  { key: "calendar", label: "Calendar" },
  { key: "review", label: "Review" },
  { key: "adapt", label: "Adapt" },
];

export default function Nav({ view, dueCount, onNavigate, onSwitchPlan, onHome }) {
  return (
    <header className="topbar">
      <div className="brand" onClick={onHome}>
        <span className="logo">📚</span>
        <span>StudyBuddy</span>
      </div>
      <nav className="nav">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={"navbtn" + (view === t.key ? " active" : "")}
            onClick={() => onNavigate(t.key)}
          >
            {t.label}
            {t.key === "review" && dueCount > 0 && <span className="badge">{dueCount}</span>}
          </button>
        ))}
        <button className="navbtn ghost" onClick={onSwitchPlan}>Switch plan</button>
      </nav>
    </header>
  );
}
