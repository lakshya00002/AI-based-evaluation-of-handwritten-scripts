const BASE = import.meta.env.VITE_API_URL || "";

function authHeader() {
  const t = localStorage.getItem("token");
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export async function apiFetch(path, options = {}) {
  const url = `${BASE}${path}`;
  const headers = { ...authHeader(), ...(options.headers || {}) };
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem("token");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || JSON.stringify(j);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type");
  if (ct && ct.includes("application/json")) return res.json();
  return res.text();
}

export const api = {
  register: (body) => apiFetch("/api/v1/auth/register", { method: "POST", body: JSON.stringify(body) }),
  token: async (email, password) => {
    const form = new URLSearchParams();
    form.set("username", email);
    form.set("password", password);
    return apiFetch("/api/v1/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
  },
  assignments: () => apiFetch("/api/v1/assignments"),
  assignment: (id) => apiFetch(`/api/v1/assignments/${id}`),
  createAssignment: (body) => apiFetch("/api/v1/assignments", { method: "POST", body: JSON.stringify(body) }),
  upload: (formData) =>
    apiFetch("/api/v1/submissions/upload", { method: "POST", body: formData }),
  batchUpload: (formData) =>
    apiFetch("/api/v1/submissions/batch", { method: "POST", body: formData }),
  evaluate: (submissionId, body) =>
    apiFetch(`/api/v1/submissions/${submissionId}/evaluate`, { method: "POST", body: JSON.stringify(body) }),
  getSubmission: (id) => apiFetch(`/api/v1/submissions/${id}`),
  teacherSubmissions: (assignmentId) =>
    apiFetch(`/api/v1/teacher/assignments/${assignmentId}/submissions`),
  overrideScore: (scoreId, body) =>
    apiFetch(`/api/v1/teacher/scores/${scoreId}/override`, { method: "POST", body: JSON.stringify(body) }),
};
