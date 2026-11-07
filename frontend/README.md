# StudyBuddy — React frontend

A Vite + React (18) single-page app for StudyBuddy. It talks to the Python API
(`/api/*`) and adds a **month-grid study calendar** plus a calendar widget on the
dashboard.

## Develop

The Python API must be running (see the repo root `run.sh`, defaults to port 8000).

```bash
cd frontend
npm install        # one-time (requires network for the npm registry)
npm run dev        # Vite dev server on http://localhost:5173, proxies /api -> :8000
```

Open http://localhost:5173.

## Build for production

```bash
npm run build      # emits the compiled SPA into ../app/web_dist
```

The Python server auto-detects `app/web_dist/` and serves the built React app
from it. So after building you can run the whole thing with just:

```bash
cd .. && python3 -m app.server   # serves the React build at http://127.0.0.1:8000
```

If `app/web_dist/` is absent, the server falls back to the dependency-free
vanilla frontend in `app/web/` — so the app always runs with only Python, even
without Node.

## Structure

```
src/
├── main.jsx            # React entry
├── App.jsx             # view routing + shared state (plan id, due badge, toasts)
├── api.js              # fetch wrapper for the REST API
├── styles.css          # design system (shared with the vanilla app) + calendar styles
├── components/
│   ├── Calendar.jsx    # month-grid calendar (milestones, deadline, completion coloring)
│   ├── Nav.jsx
│   └── common.jsx      # Loader, Stat, ProgressBar, Toast, useToast, fmtDays
└── views/
    ├── Onboard.jsx     # create / resume a plan
    ├── Dashboard.jsx   # stats + mini calendar with next milestone
    ├── Plan.jsx        # topics by domain + milestones + day-by-day
    ├── CalendarView.jsx# full-page calendar
    ├── Topic.jsx       # lesson + quiz + flashcard entry
    ├── Review.jsx      # FSRS flashcard review
    └── Adapt.jsx       # adaptive recommendations + re-plan
```

## The calendar

`Calendar.jsx` renders a month grid from the plan:

- Each **study day** shows dots (one per topic, capped) and planned minutes.
- **Milestones** (🏁) and the **projected finish** (🎓) are pinned to their dates;
  your **deadline** (⏰) too.
- Days are colored by progress: all topics done = green, some done = amber.
- Click a study day to see its topics and jump straight into a lesson.
- The dashboard uses the same component in a compact `mini` variant.

It's driven entirely by data the API already returns (`plan.days`,
`plan.milestones`, and per-topic status from `/api/plans/{id}/progress`) — no
backend changes were needed.
