import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
  withCredentials: true
});

export const signup = (payload) => api.post("/signup", payload);
export const login = (payload) => api.post("/login", payload);
export const logout = () => api.post("/logout");
export const getMe = () => api.get("/me");

export const getAssignments = () => api.get("/assignments");
export const createAssignment = (payload) => api.post("/assignments", payload);

export const submitAssignment = ({ assignmentId, text, file }) => {
  const formData = new FormData();
  formData.append("assignment_id", String(assignmentId));
  if (text) {
    formData.append("text", text);
  }
  if (file) {
    formData.append("file", file);
  }
  return api.post("/submit", formData, {
    headers: {
      "Content-Type": "multipart/form-data"
    }
  });
};
export const getSubmissions = (assignmentId) => api.get(`/submissions/${assignmentId}`);

export const evaluateSubmission = (submissionId, { force = true } = {}) =>
  api.post(`/evaluate/${submissionId}?force=${force ? "true" : "false"}`);

export const getStudentResults = () => api.get("/results/student");
export const getTeacherResults = (assignmentId) => api.get(`/results/teacher/${assignmentId}`);

export default api;
