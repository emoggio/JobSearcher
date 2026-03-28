import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

// Attach stored token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("scout_token");
  if (token && token !== "local") {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Redirect to login on 401
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("scout_token");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export default api;

// Auth
export const login = (username: string, password: string) =>
  api.post("/api/auth/login", { username, password });
export const register = (username: string, password: string, confirm_password: string) =>
  api.post("/api/auth/register", { username, password, confirm_password });
export const recoverAccount = (username: string, recovery_code: string, new_password: string) =>
  api.post("/api/auth/recover", { username, recovery_code, new_password });
export const getMe = () => api.get("/api/auth/me");

// Jobs
export const searchJobs = (params = {}) => api.post("/api/jobs/search", params);
export const listJobs = (filters = {}) => api.get("/api/jobs", { params: filters });
export const getJob = (id: string) => api.get(`/api/jobs/${id}`);
export const scoreJob = (id: string) => api.post(`/api/jobs/${id}/score`);
export const tweakCV = (id: string) => api.post(`/api/cv/tweak/${id}`);

// Applications
export const listApplications = () => api.get("/api/applications");
export const createApplication = (jobId: string) =>
  api.post("/api/applications", { job_id: jobId });
export const updateApplication = (id: string, data: object) =>
  api.patch(`/api/applications/${id}`, data);
export const deleteApplication = (id: string) => api.delete(`/api/applications/${id}`);

// Recruiters
export const findRecruiters = (jobId: string) => api.post(`/api/recruiters/find/${jobId}`);
export const listRecruiters = () => api.get("/api/recruiters");

// Calendar
export const getCalendar = () => api.get("/api/calendar");

// Import job from URL
export const importJobUrl = (url: string) => api.post("/api/jobs/import", { url });

// Logs
export const getLogs = (lines = 100) => api.get("/api/logs", { params: { lines } });

// CV
export const uploadCV = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/api/cv/upload", form);
};
export const getCurrentCV = () => api.get("/api/cv/current");
export const listCVs = () => api.get("/api/cv/list");
export const activateCV = (filename: string) => api.post(`/api/cv/activate/${encodeURIComponent(filename)}`);
export const deleteCVFile = (filename: string) => api.delete(`/api/cv/file/${encodeURIComponent(filename)}`);
export const deleteCV = () => api.delete("/api/cv/current");
export const clearScores = () => api.delete("/api/jobs/scores");
export const clearProfileData = () => api.delete("/api/profile/data");
export const getHealth = () => api.get("/health");

// Profile / Chat
export const getProfile = () => api.get("/api/profile");
export const generateProfileQuestions = () => api.post("/api/profile/generate-questions");
export const saveProfileAnswers = (qa_pairs: { question: string; answer: string }[]) =>
  api.post("/api/profile/save-answers", { qa_pairs });
export const profileChat = (messages: { role: string; content: string }[]) =>
  api.post("/api/profile/chat", { messages });
