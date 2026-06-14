import axios from "axios";

export const api = axios.create({
  baseURL: "/",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || "请求失败";
    console.error("[API Error]", msg);
    return Promise.reject(err);
  }
);
