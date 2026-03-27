import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

export default api;

// Jobs
export const searchJobs = (params = {}) => api.post("/api/jobs/search", params);
export const listJobs = (filters = {}) => api.get("/api/jobs", { params: filters });
export const getJob = (id: string) => api.get(`/api/jobs/${id}`);
export const scoreJob = (id: string) => api.post(`/api/jobs/${id}/score`);
export const tweakCV = (id: string) => api.post(`/api/cv/tweak/${id}`);

// Applications
export const listApplications = () => api.get("/api/applications");
export const createApplication = (jobId: string) => api.post("/api/applications", { job_id: jobId });
export const updateApplication = (id: string, data: object) => api.patch(`/api/applications/${id}`, data);
export const deleteApplication = (id: string) => api.delete(`/api/applications/${id}`);

// Recruiters
export const findRecruiters = (jobId: string) => api.post(`/api/recruiters/find/${jobId}`);
export const listRecruiters = () => api.get("/api/recruiters");

// Calendar
export const getCalendar = () => api.get("/api/calendar");

// CV
export const uploadCV = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/api/cv/upload", form);
};
export const getCurrentCV = () => api.get("/api/cv/current");
