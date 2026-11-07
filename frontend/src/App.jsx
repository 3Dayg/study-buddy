import React, { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import Nav from "./components/Nav.jsx";
import { Toast, useToast, Loader } from "./components/common.jsx";
import Onboard from "./views/Onboard.jsx";
import Dashboard from "./views/Dashboard.jsx";
import Plan from "./views/Plan.jsx";
import CalendarView from "./views/CalendarView.jsx";
import Topic from "./views/Topic.jsx";
import Review from "./views/Review.jsx";
import Adapt from "./views/Adapt.jsx";

const STORAGE_KEY = "studybuddy_plan";

export default function App() {
  const [planId, setPlanId] = useState(null);
  const [view, setView] = useState("onboard");
  const [topicId, setTopicId] = useState(null);     // active topic (Topic view)
  const [reviewTopic, setReviewTopic] = useState(null); // topic filter for Review
  const [dueCount, setDueCount] = useState(0);
  const [booting, setBooting] = useState(true);
  const [navKey, setNavKey] = useState(0);          // force refresh of data views
  const [toast, showToast] = useToast();

  // Restore saved plan on first load.
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) { setBooting(false); return; }
    api.getPlan(saved)
      .then(() => { setPlanId(parseInt(saved, 10)); setView("dashboard"); })
      .catch(() => localStorage.removeItem(STORAGE_KEY))
      .finally(() => setBooting(false));
  }, []);

  // Keep the "due" badge fresh whenever we have a plan / change views.
  const refreshDue = useCallback(() => {
    if (!planId) return;
    api.dueFlashcards(planId).then((r) => setDueCount(r.due_count)).catch(() => {});
  }, [planId]);
  useEffect(() => { refreshDue(); }, [refreshDue, view, navKey]);

  const openPlan = (id) => {
    setPlanId(id);
    localStorage.setItem(STORAGE_KEY, id);
    setView("dashboard");
  };

  const navigate = (v) => { setTopicId(null); setReviewTopic(null); setView(v); };
  const openTopic = (tid) => { setTopicId(tid); setView("topic"); };
  const studyFlashcards = (tid = null) => { setReviewTopic(tid); setView("review"); };
  const switchPlan = () => { localStorage.removeItem(STORAGE_KEY); setPlanId(null); setView("onboard"); };
  const home = () => navigate(planId ? "dashboard" : "onboard");
  const bump = () => setNavKey((k) => k + 1);

  if (booting) return <Loader msg="Starting StudyBuddy…" />;

  let content;
  if (!planId || view === "onboard") {
    content = <Onboard onCreated={openPlan} showToast={showToast} />;
  } else if (view === "dashboard") {
    content = <Dashboard key={navKey} planId={planId} onNavigate={navigate} onOpenTopic={openTopic} />;
  } else if (view === "plan") {
    content = <Plan key={navKey} planId={planId} onOpenTopic={openTopic} />;
  } else if (view === "calendar") {
    content = <CalendarView key={navKey} planId={planId} onOpenTopic={openTopic} />;
  } else if (view === "topic") {
    content = (
      <Topic
        planId={planId}
        topicId={topicId}
        onBack={() => navigate("plan")}
        onStudyFlashcards={studyFlashcards}
        showToast={showToast}
      />
    );
  } else if (view === "review") {
    content = (
      <Review
        key={reviewTopic || "all"}
        planId={planId}
        topicId={reviewTopic}
        onDone={() => { bump(); navigate("dashboard"); }}
        onExit={() => { bump(); navigate("plan"); }}
        showToast={showToast}
      />
    );
  } else if (view === "adapt") {
    content = (
      <Adapt
        key={navKey}
        planId={planId}
        onReplanned={() => { bump(); navigate("plan"); }}
        onOpenTopic={openTopic}
        showToast={showToast}
      />
    );
  }

  return (
    <>
      {planId && view !== "onboard" && (
        <Nav
          view={view}
          dueCount={dueCount}
          onNavigate={navigate}
          onSwitchPlan={switchPlan}
          onHome={home}
        />
      )}
      <main>{content}</main>
      <Toast toast={toast} />
    </>
  );
}
