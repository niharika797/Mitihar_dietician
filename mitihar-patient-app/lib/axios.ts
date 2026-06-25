import axios, { AxiosRequestConfig, InternalAxiosRequestConfig } from "axios";
import { storage } from "./storage";

// ─── Keys used for SecureStore ─────────────────────────────────────────────
export const SECURE_KEYS = {
  ACCESS_TOKEN: "mitihar_access_token",
  REFRESH_TOKEN: "mitihar_refresh_token",
} as const;

// ─── Axios instance ────────────────────────────────────────────────────────
const api = axios.create({
  baseURL: process.env.EXPO_PUBLIC_API_URL ?? "http://10.0.2.2:8001/api/v1", // Audit C-1: fallback corrected to port 8001
  // Default timeout for most requests. The onboarding endpoint returns
  // immediately now (plan generation is backgrounded), but 30 s gives
  // headroom for any future slow responses without hammering the user.
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// ─── 401 silent-refresh queue ─────────────────────────────────────────────
let isRefreshing = false;
let failedQueue: {
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}[] = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((p) => (error ? p.reject(error) : p.resolve(token!)));
  failedQueue = [];
}

// ─── Request interceptor — attach Bearer token ─────────────────────────────
api.interceptors.request.use(async (config: InternalAxiosRequestConfig) => {
  const token = await storage.getItemAsync(SECURE_KEYS.ACCESS_TOKEN);
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ─── Response interceptor — 401 → silent refresh ──────────────────────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest: AxiosRequestConfig & { _retry?: boolean } =
      error.config ?? {};

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Queue this request until the refresh completes
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then((token) => {
          if (originalRequest.headers) {
            (originalRequest.headers as Record<string, string>).Authorization =
              `Bearer ${token}`;
          }
          return api(originalRequest);
        })
        .catch(Promise.reject.bind(Promise));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const refreshToken = await storage.getItemAsync(
        SECURE_KEYS.REFRESH_TOKEN
      );
      if (!refreshToken) throw new Error("No refresh token");

      const { data } = await axios.post(
        `${process.env.EXPO_PUBLIC_API_URL ?? "http://10.0.2.2:8001/api/v1"}/auth/refresh`, // Audit C-1
        { refresh_token: refreshToken }
      );

      const newAccessToken: string = data.access_token;
      await storage.setItemAsync(SECURE_KEYS.ACCESS_TOKEN, newAccessToken);

      processQueue(null, newAccessToken);
      if (originalRequest.headers) {
        (originalRequest.headers as Record<string, string>).Authorization =
          `Bearer ${newAccessToken}`;
      }
      return api(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      // Wipe tokens — force re-login
      await storage.deleteItemAsync(SECURE_KEYS.ACCESS_TOKEN);
      await storage.deleteItemAsync(SECURE_KEYS.REFRESH_TOKEN);
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default api;
