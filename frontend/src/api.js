// Thin fetch wrapper around the StudyBuddy Python API.
async function request(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

export const api = {
  listPlans: () => request("/api/plans"),
  createPlan: (body) => request("/api/plans", { method: "POST", body }),
  getPlan: (id) => request(`/api/plans/${id}`),
  getTopic: (id, tid) => request(`/api/plans/${id}/topics/${tid}`),
  completeLesson: (id, tid, minutes) =>
    request(`/api/plans/${id}/topics/${tid}/lesson-complete`, { method: "POST", body: { minutes } }),
  submitQuiz: (id, tid, answers, minutes) =>
    request(`/api/plans/${id}/topics/${tid}/quiz`, { method: "POST", body: { answers, minutes } }),
  dueFlashcards: (id, topicId) =>
    request(`/api/plans/${id}/flashcards/due` + (topicId ? `?topic_id=${encodeURIComponent(topicId)}` : "")),
  reviewFlashcard: (fcId, grade, minutes = 0.2) =>
    request(`/api/flashcards/${fcId}/review`, { method: "POST", body: { grade, minutes } }),
  progress: (id) => request(`/api/plans/${id}/progress`),
  adapt: (id) => request(`/api/plans/${id}/adapt`),
  replan: (id, body) => request(`/api/plans/${id}/replan`, { method: "POST", body }),
};
