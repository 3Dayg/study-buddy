import React, { useMemo, useState } from "react";

const DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"];

function isoDate(d) {
  // local-date ISO (YYYY-MM-DD) without timezone surprises
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function parseISO(s) {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

/**
 * Month-grid calendar driven by the plan.
 * props:
 *   plan      — the plan object (days[], milestones[], start_date, deadline, completion_date)
 *   progress  — progress summary (topics[] with mastered/lesson_done), optional
 *   mini      — compact variant for the dashboard
 *   onPickDay — (isoDate, dayEntry) => void, optional
 *   onOpenTopic — (topicId) => void, optional
 */
export default function Calendar({ plan, progress, mini = false, onOpenTopic }) {
  // Index plan days and milestones by date for O(1) lookup.
  const { dayByDate, milestoneByDate, firstDate, topicStatus } = useMemo(() => {
    const dayByDate = {};
    (plan.days || []).forEach((d) => (dayByDate[d.date] = d));
    const milestoneByDate = {};
    (plan.milestones || []).forEach((m) => (milestoneByDate[m.end_date] = m));
    const topicStatus = {};
    (progress?.topics || []).forEach((t) => (topicStatus[t.topic_id] = t));
    const firstDate = plan.start_date ? parseISO(plan.start_date) : new Date();
    return { dayByDate, milestoneByDate, firstDate, topicStatus };
  }, [plan, progress]);

  const [cursor, setCursor] = useState(() => new Date(firstDate.getFullYear(), firstDate.getMonth(), 1));
  const [selected, setSelected] = useState(null);

  const todayISO = isoDate(new Date());
  const deadlineISO = plan.deadline || null;
  const finishISO = plan.completion_date || null;

  const monthStart = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
  const monthEnd = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0);
  const gridStart = new Date(monthStart);
  gridStart.setDate(1 - monthStart.getDay()); // back up to Sunday

  const cells = [];
  const cur = new Date(gridStart);
  const totalCells = Math.ceil((monthEnd.getDate() + monthStart.getDay()) / 7) * 7;
  for (let i = 0; i < totalCells; i++) {
    cells.push(new Date(cur));
    cur.setDate(cur.getDate() + 1);
  }

  function dayCompletion(dayEntry) {
    // returns 'done' if all topics touched that day are mastered/lesson-done,
    // 'partial' if some, '' otherwise
    if (!dayEntry || !progress) return "";
    const ids = [...new Set(dayEntry.items.map((i) => i.topic_id))];
    if (!ids.length) return "";
    const doneCount = ids.filter((id) => {
      const s = topicStatus[id];
      return s && (s.mastered || s.lesson_done);
    }).length;
    if (doneCount === ids.length) return "done";
    if (doneCount > 0) return "partial";
    return "";
  }

  const selectedDay = selected ? dayByDate[selected] : null;
  const selectedMilestone = selected ? milestoneByDate[selected] : null;

  return (
    <div className={"calendar" + (mini ? " mini-cal" : "")}>
      <div className="cal-head">
        <div className="cal-title">{MONTHS[cursor.getMonth()]} {cursor.getFullYear()}</div>
        <div className="cal-nav">
          <button title="Previous month" onClick={() => { setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1)); setSelected(null); }}>‹</button>
          <button title="Jump to start" onClick={() => { setCursor(new Date(firstDate.getFullYear(), firstDate.getMonth(), 1)); setSelected(null); }}>•</button>
          <button title="Next month" onClick={() => { setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1)); setSelected(null); }}>›</button>
        </div>
      </div>

      <div className="cal-grid">
        {DOW.map((d) => <div key={d} className="cal-dow">{mini ? d[0] : d}</div>)}
        {cells.map((date, i) => {
          const ds = isoDate(date);
          const inMonth = date.getMonth() === cursor.getMonth();
          const dayEntry = dayByDate[ds];
          const milestone = milestoneByDate[ds];
          const isDeadline = ds === deadlineISO;
          const isFinish = ds === finishISO;
          const comp = dayCompletion(dayEntry);
          const classes = ["cal-cell"];
          if (!inMonth) classes.push("outside");
          if (dayEntry) classes.push("has-study");
          if (ds === todayISO) classes.push("today");
          if (ds === selected) classes.push("selected");

          return (
            <div
              key={i}
              className={classes.join(" ")}
              onClick={() => dayEntry && setSelected(ds === selected ? null : ds)}
            >
              <div className="cal-date">{date.getDate()}</div>

              {dayEntry && (
                <>
                  <div className="cal-dot-row">
                    {dayEntry.items.slice(0, 6).map((it, k) => (
                      <span key={k} className={"cal-dot " + comp} title={it.title} />
                    ))}
                  </div>
                  {!mini && <div className="cal-mins">{dayEntry.planned_minutes}m</div>}
                </>
              )}

              {!mini && milestone && (
                <div className="cal-milestone" title={milestone.goal}>🏁 Week {milestone.week}</div>
              )}
              {!mini && isFinish && !milestone && (
                <div className="cal-milestone" title="Projected completion">🎓 Finish</div>
              )}
              {!mini && isDeadline && <div className="cal-deadline">⏰ Deadline</div>}
            </div>
          );
        })}
      </div>

      {!mini && (
        <div className="cal-legend">
          <span className="item"><span className="cal-dot" /> Scheduled study</span>
          <span className="item"><span className="cal-dot done" /> Completed</span>
          <span className="item"><span className="cal-dot partial" /> In progress</span>
          <span className="item">🏁 Milestone</span>
          <span className="item">🎓 Finish · ⏰ Deadline</span>
        </div>
      )}

      {!mini && selected && (selectedDay || selectedMilestone) && (
        <div className="cal-detail card" style={{ marginTop: 16 }}>
          <h3 style={{ marginBottom: 10 }}>{prettyDate(selected)}</h3>
          {selectedMilestone && (
            <p style={{ color: "var(--brand-2)", fontWeight: 600 }}>
              🏁 Week {selectedMilestone.week} milestone — {selectedMilestone.goal}
            </p>
          )}
          {selectedDay ? (
            selectedDay.items.map((it, k) => {
              const s = topicStatus[it.topic_id];
              const done = s && (s.mastered || s.lesson_done);
              return (
                <div
                  key={k}
                  className={"day-item" + (done ? " done" : "")}
                  style={{ cursor: onOpenTopic ? "pointer" : "default" }}
                  onClick={() => onOpenTopic && onOpenTopic(it.topic_id)}
                >
                  <span className="ti">{done ? "✓ " : ""}{it.title}{it.partial ? " (cont.)" : ""}</span>
                  <span className="muted small">{it.minutes}m</span>
                </div>
              );
            })
          ) : (
            <p className="muted">No study scheduled this day.</p>
          )}
        </div>
      )}
    </div>
  );
}

function prettyDate(iso) {
  const d = parseISO(iso);
  return d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" });
}
