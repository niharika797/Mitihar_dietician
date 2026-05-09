/**
 * Axios instance for Mityahar API.
 *
 * - baseURL points to FastAPI at localhost:8000/api/v1
 * - withCredentials: true so the HttpOnly refresh_token cookie is
 *   automatically sent on every request (required for /auth/refresh)
 * - Request interceptor: injects Bearer access_token from Zustand store
 * - Response interceptor: on 401 → silently refresh → retry once
 *   If refresh fails → clearAuth() + redirect to login
 */

import axios, {
  AxiosError,
  AxiosRequestConfig,
  InternalAxiosRequestConfig,
} from 'axios';
import { useAuthStore } from '../stores/authStore';

// Base URL is read from VITE_API_URL env var (set in mitihar-frontend/apps/.env).
// Falls back to localhost for local dev. Never hardcode a production URL here.
const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8001/api/v1'; // Audit C-1: fallback must match backend port 8001

// Named export intentionally removed — all consumers use the default import.
// Keeping both caused react-doctor's "duplicate export" warning.
const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─── Request interceptor ─────────────────────────────────────────────────────
// Reads access_token from Zustand store and attaches it as Bearer header.

apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token: string | null = useAuthStore.getState().access_token;
    if (token && config.headers) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ─── Response interceptor ────────────────────────────────────────────────────
// On 401: attempt one silent token refresh, then retry the original request.
// On refresh failure: clear auth state and redirect to login.

let isRefreshing = false;
let refreshQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null = null) {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token!);
  });
  refreshQueue = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean;
    };

    const isRefreshEndpoint = originalRequest?.url?.includes('/auth/refresh');

    if (
      error.response?.status !== 401 ||
      originalRequest?._retry ||
      isRefreshEndpoint
    ) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        refreshQueue.push({ resolve, reject });
      })
        .then((newToken) => {
          if (originalRequest.headers) {
            (originalRequest.headers as Record<string, string>)[
              'Authorization'
            ] = `Bearer ${newToken}`;
          }
          return apiClient(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const { data } = await apiClient.post<{ access_token: string }>(
        '/auth/refresh',
      );
      const newToken = data.access_token;

      useAuthStore.getState().setAccessToken(newToken);
      processQueue(null, newToken);

      if (originalRequest.headers) {
        (originalRequest.headers as Record<string, string>)[
          'Authorization'
        ] = `Bearer ${newToken}`;
      }
      return apiClient(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      useAuthStore.getState().clearAuth();
      window.location.href = '/';
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

export default apiClient;
