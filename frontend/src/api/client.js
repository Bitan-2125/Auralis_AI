import axios from "axios";

const API_URL = (import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://localhost:8000" : "/api")).replace(/\/$/, "");

export const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function expireSession() {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  window.dispatchEvent(new Event("auralis:session-expired"));
}

api.interceptors.response.use(response => response, error => {
  if (error.response?.status === 401 && !error.config?.url?.startsWith("/auth/")) expireSession();
  return Promise.reject(error);
});

export { API_URL };
