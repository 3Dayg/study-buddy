/* StudyBuddy SPA — vanilla JS, no framework, no build step. */

const App = (() => {
  const state = { planId: null, view: "onboard" };
  const el = (id) => document.getElementById(id);
  const app = () => el("app");

  // ---- tiny DOM helpers ----
  function h(tag, attrs = {}, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (k === "class") node.className = v;
      else if (k === "html") node.innerHTML = v;
      else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
      else if (v !== null && v !== undefined) node.setAttribute(k, v);
    }
    for (const c of children.flat()) {
      if (c === null || c === undefined || c === false) continue;
      node.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
    }
    return node;
  }
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function toast(msg, kind = "") {
    const t = el("toast");
    t.textContent = msg;
    t.className = "toast " + kind;
    setTimeout(() => t.classList.add("hidden"), 2600);
  }

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...opts,
      body: opts.body ? JSON.stringify(opts.body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Request failed");
    return data;
  }

  function loader(msg = "Loading…") {
    app().innerHTML = "";
    app().appendChild(h("div", { class: "loader" }, h("div", { class: "spinner" }), msg));
  }

  // ---- navigation ----
  function setNav(view) {
    state.view = view;
    el("nav").classList.toggle("hidden", !state.planId);
    document.querySelectorAll(".navbtn[data-view]").forEach((b) =>
      b.classList.toggle("active", b.dataset.view === view));
  }

  function go(view) {
    setNav(view);
    if (view === "dashboard") renderDashboard();
    else if (view === "plan") renderPlan();
    else if (view === "review") renderReview();
    else if (view === "adapt") renderAdapt();
  }

  // ===================== ONBOARDING =====================
  function renderOnboard() {
    state.planId = null;
    el("nav").classList.add("hidden");
    const form = { level: "beginner" };

    const levelPills = ["beginner", "intermediate", "advanced"].map((lv) =>
      h("div", {
        class: "pill" + (lv === form.level ? " active" : ""),
        onclick: (e) => {
          form.level = lv;
          e.currentTarget.parentElement.querySelectorAll(".pill").forEach((p) => p.classList.remove("active"));
          e.currentTarget.classList.add("active");
        },
      }, lv[0].toUpperCase() + lv.slice(1)));

    const goalInput = h("input", { id: "goalInput", placeholder: "e.g. AWS Certified Cloud Practitioner (CLF-C02)" });
    const minutesInput = h("input", { id: "minutesInput", type: "number", min: "10", max: "600", value: "45" });
    const deadlineInput = h("input", { id: "deadlineInput", type: "date" });

    const examples = ["AWS Certified Cloud Practitioner (CLF-C02)", "Learn Python for data analysis", "Spanish for travel", "Intro to machine learning"];

    app().innerHTML = "";
    app().append(
      h("div", { class: "hero" },
        h("div", { class: "tag" }, "Your personal AI study tutor"),
        h("h1", {}, "Go from ", h("span", { class: "gradient-text" }, "zero to mastery"), ", one day at a time."),
        h("p", { class: "muted" }, "Tell me what you want to learn. I'll build a personalized plan, teach each topic, quiz you, and schedule spaced-repetition flashcards that adapt to how you perform."),
      ),
      h("div", { class: "card", style: "max-width:620px;margin:0 auto" },
        h("label", {}, "What do you want to learn?"),
        goalInput,
        h("div", { class: "tag-row" }, examples.map((ex) =>
          h("span", { class: "chip", style: "cursor:pointer", onclick: () => (goalInput.value = ex) }, ex))),
        h("label", {}, "Your current knowledge level"),
        h("div", { class: "pills" }, levelPills),
        h("div", { class: "grid cols-2" },
          h("div", {}, h("label", {}, "Daily time commitment (minutes)"), minutesInput),
          h("div", {}, h("label", {}, "Target deadline (optional)"), deadlineInput)),
        h("button", {
          class: "btn block", style: "margin-top:22px",
          onclick: async () => {
            const goal = goalInput.value.trim();
            if (!goal) return toast("Please enter a learning goal", "bad");
            loader("Designing your personalized study plan…");
            try {
              const r = await api("/api/plans", {
                method: "POST",
                body: {
                  goal, level: form.level,
                  daily_minutes: parseInt(minutesInput.value || "45", 10),
                  deadline: deadlineInput.value || null,
                },
              });
              state.planId = r.plan_id;
              localStorage.setItem("studybuddy_plan", r.plan_id);
              toast(r.curriculum_generated ? "Custom plan generated!" : "Expert curriculum loaded!", "good");
              go("dashboard");
            } catch (e) { toast(e.message, "bad"); renderOnboard(); }
          },
        }, "✨ Build my study plan"),
      ),
    );
    loadExistingPlans();
  }

  async function loadExistingPlans() {
    try {
      const r = await api("/api/plans");
      if (!r.plans.length) return;
      const list = h("div", { class: "card", style: "max-width:620px;margin:18px auto 0" },
        h("h3", {}, "Resume a plan"),
        ...r.plans.slice(0, 5).map((p) =>
          h("div", {
            class: "topic", onclick: () => { state.planId = p.id; localStorage.setItem("studybuddy_plan", p.id); go("dashboard"); },
          },
            h("div", { class: "ic" }, "📘"),
            h("div", { class: "meta" },
              h("div", { class: "t" }, p.goal),
              h("div", { class: "status" }, `${p.level} · ${p.daily_minutes} min/day` + (p.deadline ? ` · due ${p.deadline}` : ""))))),
      );
      app().appendChild(list);
    } catch (_) {}
  }

  // ===================== DASHBOARD =====================
  async function renderDashboard() {
    loader("Loading your dashboard…");
    const s = await api(`/api/plans/${state.planId}/progress`);
    updateDueBadge(s.due_flashcards);

    const pct = (v) => (v === null || v === undefined ? "—" : Math.round(v * 100) + "%");
    const clsFor = (v, hi = 0.8, lo = 0.6) => v === null || v === undefined ? "" : v >= hi ? "good" : v >= lo ? "warn" : "bad";

    app().innerHTML = "";
    app().append(
      h("div", { class: "row spread" },
        h("div", {},
          h("h1", {}, s.goal),
          h("p", { class: "muted" }, `${s.level} · ${s.daily_minutes} min/day` +
            (s.deadline ? ` · deadline ${s.deadline}` : "") +
            (s.completion_date ? ` · projected finish ${s.completion_date}` : ""))),
        h("div", {}, s.deadline ? h("span", { class: "chip " + (s.on_track ? "mastered" : "weak") }, s.on_track ? "On track ✓" : "Behind schedule") : null),
      ),

      h("div", { class: "card" },
        h("div", { class: "row spread" }, h("h3", {}, "Overall mastery"), h("span", { class: "muted" }, `${s.topics_mastered}/${s.total_topics} topics mastered`)),
        h("div", { class: "progress" }, h("span", { style: `width:${s.completion_pct}%` })),
        h("div", { class: "muted small", style: "margin-top:8px" }, `${s.completion_pct}% complete`)),

      h("div", { class: "grid cols-4" },
        stat(s.lessons_done + "/" + s.total_topics, "Lessons done"),
        stat(pct(s.avg_quiz_score), "Avg quiz score", clsFor(s.avg_quiz_score)),
        stat(pct(s.retention), "Flashcard recall", clsFor(s.retention, 0.85, 0.7)),
        stat(s.due_flashcards, "Cards due now", s.due_flashcards > 0 ? "warn" : "good")),

      h("div", { class: "grid cols-2" },
        h("div", { class: "card" },
          h("h3", {}, "Jump back in"),
          h("button", { class: "btn block", style: "margin-bottom:10px", onclick: () => go("plan") }, "📚 Continue studying"),
          s.due_flashcards > 0
            ? h("button", { class: "btn block warn", onclick: () => go("review") }, `🔁 Review ${s.due_flashcards} due flashcards`)
            : h("div", { class: "muted small center" }, "No flashcards due — you're caught up! 🎉")),
        h("div", { class: "card" },
          h("h3", {}, "Study time"),
          h("div", { class: "row spread" }, h("span", { class: "muted" }, "Last 7 days"), h("b", {}, s.minutes_studied_last7 + " min")),
          h("div", { class: "row spread" }, h("span", { class: "muted" }, "All time"), h("b", {}, s.minutes_studied_total + " min")),
          s.weak_topics.length
            ? h("div", { style: "margin-top:12px" }, h("div", { class: "muted small" }, "Needs work:"),
                h("div", { class: "tag-row" }, s.weak_topics.map((w) => h("span", { class: "chip weak" }, w.title))))
            : null)),
    );
  }

  function stat(num, lbl, cls = "") {
    return h("div", { class: "card stat" }, h("div", { class: "num " + cls }, String(num)), h("div", { class: "lbl" }, lbl));
  }

  function updateDueBadge(n) {
    const b = el("dueBadge");
    b.textContent = n;
    b.classList.toggle("hidden", !n);
  }

  // ===================== STUDY PLAN =====================
  async function renderPlan() {
    loader("Loading your study plan…");
    const [p, prog] = await Promise.all([
      api(`/api/plans/${state.planId}`),
      api(`/api/plans/${state.planId}/progress`),
    ]);
    const progById = {};
    prog.topics.forEach((t) => (progById[t.topic_id] = t));

    const topicNode = (t) => {
      const pr = progById[t.id] || {};
      let ic = "⚪", chips = [];
      if (pr.mastered) { ic = "🌟"; chips.push(h("span", { class: "chip mastered" }, "Mastered")); }
      else if (pr.lesson_done) { ic = "📖"; chips.push(h("span", { class: "chip done" }, "Lesson done")); }
      if (pr.best_quiz !== null && pr.best_quiz !== undefined)
        chips.push(h("span", { class: "chip" + (pr.best_quiz < 0.7 ? " weak" : "") }, `Quiz ${Math.round(pr.best_quiz * 100)}%`));
      chips.push(h("span", { class: "chip" }, `${t.num_flashcards} cards`));
      return h("div", { class: "topic", onclick: () => renderTopic(t.id) },
        h("div", { class: "ic" }, ic),
        h("div", { class: "meta" },
          h("div", { class: "t" }, t.title),
          h("div", { class: "status" }, chips)),
        h("div", { class: "muted small" }, "›"));
    };

    // group topics by domain
    const byDomain = {};
    p.topics.forEach((t) => ((byDomain[t.domain || "Topics"] ||= []).push(t)));

    app().innerHTML = "";
    app().append(
      h("div", {},
        h("h1", {}, p.curriculum_title),
        h("p", { class: "muted" }, p.curriculum_summary),
        p.curriculum_generated
          ? h("p", { class: "small", style: "color:var(--brand-2)" }, "✨ This curriculum was generated for your custom goal.")
          : h("p", { class: "small", style: "color:var(--brand-2)" }, "📗 Expert-authored curriculum."),
      ),
      h("div", { class: "card" },
        h("div", { class: "row spread" }, h("h3", {}, "Milestones"),
          h("span", { class: "muted small" }, `${p.plan.total_days} study days · finish ${p.plan.completion_date}`)),
        ...p.plan.milestones.map((m) =>
          h("div", { class: "milestone" },
            h("div", { class: "w" }, `Week ${m.week} · ${m.start_date} → ${m.end_date}`),
            h("div", {}, m.goal),
            h("div", { class: "muted small" }, `${m.planned_minutes} min planned`)))),
      ...Object.entries(byDomain).map(([dom, ts]) =>
        h("div", { class: "card" }, h("h3", {}, dom), ...ts.map(topicNode))),
      h("details", { class: "card" },
        h("summary", { style: "cursor:pointer;font-weight:700" }, "View full day-by-day schedule"),
        h("div", { style: "margin-top:14px" }, ...p.plan.days.map((d) =>
          h("div", { class: "day" },
            h("div", { class: "d" }, `Day ${d.day_index + 1} · ${d.date} · ${d.planned_minutes} min`),
            h("div", { class: "muted small" }, d.items.map((i) => i.title + (i.partial ? ` (${i.minutes}m)` : "")).join(" · ")))))),
    );
  }

  // ===================== TOPIC (lesson + quiz + cards) =====================
  async function renderTopic(topicId) {
    loader("Opening lesson…");
    const t = await api(`/api/plans/${state.planId}/topics/${topicId}`);
    const started = Date.now();

    const lessonSections = t.lesson.map((s) =>
      h("div", { class: "lesson-section" }, h("h3", {}, s.heading), h("div", { class: "body" }, s.body)));
    const exampleNodes = t.examples.map((e) =>
      h("div", { class: "example" }, h("div", { class: "title" }, "💡 " + e.title), h("div", {}, e.body)));

    app().innerHTML = "";
    app().append(
      h("div", { class: "row", style: "margin-bottom:8px" },
        h("button", { class: "btn outline small", onclick: () => go("plan") }, "← Back to plan")),
      h("div", {}, h("div", { class: "muted small" }, t.domain), h("h1", {}, t.title),
        t.objective ? h("p", { class: "muted" }, "🎯 " + t.objective) : null),
      h("div", { class: "card" }, h("h2", {}, "📖 Lesson"), ...lessonSections,
        exampleNodes.length ? h("h3", { style: "margin-top:18px" }, "Worked examples") : null, ...exampleNodes,
        h("button", {
          class: "btn good", style: "margin-top:12px",
          onclick: async (e) => {
            const mins = Math.round((Date.now() - started) / 60000);
            await api(`/api/plans/${state.planId}/topics/${topicId}/lesson-complete`, { method: "POST", body: { minutes: mins } });
            e.currentTarget.textContent = "✓ Lesson marked complete";
            e.currentTarget.disabled = true;
            toast("Lesson complete! Now test yourself below.", "good");
          },
        }, "Mark lesson complete ✓")),
      renderQuizCard(t, topicId),
      h("div", { class: "card center" },
        h("h3", {}, "🔁 Flashcards"),
        h("p", { class: "muted" }, `${t.num_flashcards} spaced-repetition cards for this topic.`),
        h("button", { class: "btn", onclick: () => renderReview(topicId) }, "Study these flashcards")),
    );
  }

  function renderQuizCard(topic, topicId) {
    const chosen = new Array(topic.quiz.length).fill(null);
    const card = h("div", { class: "card" }, h("h2", {}, "📝 Quick quiz"));
    const started = Date.now();
    if (!topic.quiz.length) { card.appendChild(h("p", { class: "muted" }, "No quiz for this topic.")); return card; }

    const qNodes = topic.quiz.map((q, qi) => {
      const choiceEls = q.choices.map((c, ci) =>
        h("div", { class: "choice", "data-qi": qi, "data-ci": ci,
          onclick: (e) => {
            if (card.dataset.submitted) return;
            chosen[qi] = ci;
            e.currentTarget.parentElement.querySelectorAll(".choice").forEach((x) => x.classList.remove("selected"));
            e.currentTarget.classList.add("selected");
          } }, c));
      return h("div", { class: "q" }, h("div", { class: "prompt" }, `${qi + 1}. ${q.q}`), ...choiceEls);
    });

    const submitBtn = h("button", { class: "btn", onclick: async () => {
      if (chosen.includes(null)) return toast("Answer all questions first", "bad");
      const mins = Math.round((Date.now() - started) / 60000);
      const r = await api(`/api/plans/${state.planId}/topics/${topicId}/quiz`, { method: "POST", body: { answers: chosen, minutes: mins } });
      card.dataset.submitted = "1";
      r.detail.forEach((d, qi) => {
        const qEl = qNodes[qi];
        qEl.querySelectorAll(".choice").forEach((ce, ci) => {
          if (ci === d.correct_answer) ce.classList.add("correct");
          else if (ci === d.chosen && !d.is_correct) ce.classList.add("wrong");
        });
        qEl.appendChild(h("div", { class: "explain" }, (d.is_correct ? "✓ " : "✗ ") + d.explain));
      });
      submitBtn.classList.add("hidden");
      const pct = Math.round(r.score * 100);
      const kind = r.score >= 0.8 ? "good" : r.score >= 0.6 ? "warn" : "bad";
      resultBox.className = "card stat";
      resultBox.innerHTML = "";
      resultBox.append(
        h("div", { class: "num " + kind }, pct + "%"),
        h("div", { class: "lbl" }, `${r.correct} / ${r.total} correct · ` +
          (r.score >= 0.8 ? "Mastered! 🌟" : r.score >= 0.6 ? "Good — review the misses" : "Keep studying, you've got this")),
        h("button", { class: "btn secondary", style: "margin-top:12px", onclick: () => renderTopic(topicId) }, "Retake quiz"),
      );
      updateDueBadgeFromServer();
    } }, "Submit answers");

    const resultBox = h("div", {});
    card.append(...qNodes, submitBtn, resultBox);
    return card;
  }

  // ===================== REVIEW (flashcards) =====================
  async function renderReview(topicId = null) {
    setNav("review");
    loader("Fetching cards due for review…");
    const q = topicId ? `?topic_id=${encodeURIComponent(topicId)}` : "";
    const r = await api(`/api/plans/${state.planId}/flashcards/due${q}`);
    updateDueBadge(topicId ? el("dueBadge").textContent : r.due_count);

    if (!r.cards.length) {
      app().innerHTML = "";
      app().append(h("div", { class: "card empty" },
        h("div", { class: "big-emoji" }, "🎉"),
        h("h2", {}, "All caught up!"),
        h("p", { class: "muted" }, "No flashcards are due right now. The FSRS scheduler will surface them again at the optimal moment."),
        h("button", { class: "btn", onclick: () => go("dashboard") }, "Back to dashboard")));
      return;
    }

    let idx = 0, reviewed = 0;
    const total = r.cards.length;

    function showCard() {
      if (idx >= r.cards.length) {
        app().innerHTML = "";
        app().append(h("div", { class: "card empty" },
          h("div", { class: "big-emoji" }, "✅"),
          h("h2", {}, `Reviewed ${reviewed} card${reviewed === 1 ? "" : "s"}!`),
          h("p", { class: "muted" }, "Great work. Spaced repetition is doing its job behind the scenes."),
          h("div", { class: "row center", style: "justify-content:center" },
            h("button", { class: "btn", onclick: () => go("dashboard") }, "Dashboard"),
            h("button", { class: "btn secondary", onclick: () => go("plan") }, "Keep studying"))));
        updateDueBadgeFromServer();
        return;
      }
      const card = r.cards[idx];
      const fc = h("div", { class: "flashcard" },
        h("div", { class: "inner" },
          h("div", { class: "face front" }, h("div", {}, card.front), h("div", { class: "hint" }, "click to reveal")),
          h("div", { class: "face back" }, h("div", {}, card.back), h("div", { class: "hint" }, "how well did you recall it?"))));
      fc.addEventListener("click", () => { fc.classList.toggle("flipped"); gradeRow.style.visibility = fc.classList.contains("flipped") ? "visible" : "hidden"; });

      const grades = [
        { g: 1, label: "Again", cls: "bad", key: "again" },
        { g: 2, label: "Hard", cls: "warn", key: "hard" },
        { g: 3, label: "Good", cls: "good", key: "good" },
        { g: 4, label: "Easy", cls: "secondary", key: "easy" },
      ];
      const gradeRow = h("div", { class: "grade-row", style: "visibility:hidden" },
        grades.map((gr) => h("button", { class: "btn " + gr.cls, onclick: async () => {
          const res = await api(`/api/flashcards/${card.id}/review`, { method: "POST", body: { grade: gr.g, minutes: 0.2 } });
          reviewed++;
          idx++;
          toast(`Next review in ${fmtDays(res.next_review_days)}`, "good");
          showCard();
        } }, gr.label, h("small", {}, fmtDays(card.preview[gr.key])))));

      app().innerHTML = "";
      app().append(
        h("div", { class: "row spread" },
          h("button", { class: "btn outline small", onclick: () => go("plan") }, "← Exit"),
          h("span", { class: "muted" }, `Card ${idx + 1} of ${total}`)),
        h("div", { class: "progress thin", style: "margin:10px 0 20px" }, h("span", { style: `width:${(idx / total) * 100}%` })),
        fc, gradeRow,
        h("p", { class: "muted small center", style: "margin-top:16px" }, "Rate your recall honestly — FSRS uses it to schedule the next review."));
    }
    showCard();
  }

  function fmtDays(d) {
    if (d === null || d === undefined) return "";
    if (d < 1 / 24) return Math.max(1, Math.round(d * 1440)) + "m";
    if (d < 1) return Math.round(d * 24) + "h";
    if (d < 30) return Math.round(d) + "d";
    if (d < 365) return Math.round(d / 30) + "mo";
    return (d / 365).toFixed(1) + "y";
  }

  async function updateDueBadgeFromServer() {
    try { const r = await api(`/api/plans/${state.planId}/flashcards/due`); updateDueBadge(r.due_count); } catch (_) {}
  }

  // ===================== ADAPT =====================
  async function renderAdapt() {
    loader("Analyzing your performance…");
    const [rec, p] = await Promise.all([
      api(`/api/plans/${state.planId}/adapt`),
      api(`/api/plans/${state.planId}`),
    ]);
    const paceChip = { ahead: ["mastered", "Ahead of schedule"], on_track: ["done", "On track"], behind: ["weak", "Behind schedule"] }[rec.pace] || ["", rec.pace];

    app().innerHTML = "";
    app().append(
      h("h1", {}, "Adaptive tutor"),
      h("p", { class: "muted" }, "Your plan adjusts to how you actually perform — mastery, retention, and the time you put in."),
      h("div", { class: "card" },
        h("div", { class: "row spread" }, h("h3", {}, "Assessment"), h("span", { class: "chip " + paceChip[0] }, paceChip[1])),
        h("p", {}, rec.message),
        h("div", { style: "margin-top:12px" }, ...rec.actions.map((a) =>
          h("div", { class: "action" }, h("div", { class: "k" }, a.type), h("div", {}, a.detail))))),

      h("div", { class: "card" },
        h("h3", {}, "Apply an adjustment"),
        h("p", { class: "muted small" }, `Current: ${p.daily_minutes} min/day` + (p.deadline ? `, deadline ${p.deadline}` : ", no deadline") +
          `. Suggested daily time: ${rec.suggested_daily_minutes} min.`),
        h("div", { class: "grid cols-2" },
          h("div", {}, h("label", {}, "New daily minutes"),
            h("input", { id: "adaptMinutes", type: "number", min: "10", max: "600", value: rec.suggested_daily_minutes })),
          h("div", {}, h("label", {}, "New deadline (optional)"),
            h("input", { id: "adaptDeadline", type: "date", value: p.deadline || "" }))),
        h("button", { class: "btn", style: "margin-top:16px", onclick: async () => {
          const body = { daily_minutes: parseInt(el("adaptMinutes").value, 10) };
          const dl = el("adaptDeadline").value;
          body.deadline = dl || null;
          const r = await api(`/api/plans/${state.planId}/replan`, { method: "POST", body });
          toast(`Plan updated — new finish date ${r.plan.completion_date}`, "good");
          go("plan");
        } }, "♻️ Re-plan with these settings")),

      rec.review_topics.length
        ? h("div", { class: "card" }, h("h3", {}, "Recommended review"),
            h("p", { class: "muted small" }, "These topics have the lowest quiz scores — revisit them next."),
            ...rec.review_topics.map((t) => h("div", { class: "topic", onclick: () => renderTopic(t.topic_id) },
              h("div", { class: "ic" }, "🔁"), h("div", { class: "meta" }, h("div", { class: "t" }, t.title)),
              h("div", { class: "muted" }, "›"))))
        : null,
    );
  }

  // ===================== boot =====================
  function bind() {
    document.querySelectorAll(".navbtn[data-view]").forEach((b) =>
      b.addEventListener("click", () => go(b.dataset.view)));
    el("switchPlan").addEventListener("click", () => { localStorage.removeItem("studybuddy_plan"); renderOnboard(); });
    el("homeLink").addEventListener("click", () => { if (state.planId) go("dashboard"); else renderOnboard(); });
  }

  async function init() {
    bind();
    const saved = localStorage.getItem("studybuddy_plan");
    if (saved) {
      try { await api(`/api/plans/${saved}`); state.planId = parseInt(saved, 10); return go("dashboard"); }
      catch (_) { localStorage.removeItem("studybuddy_plan"); }
    }
    renderOnboard();
  }

  return { init };
})();

document.addEventListener("DOMContentLoaded", App.init);
