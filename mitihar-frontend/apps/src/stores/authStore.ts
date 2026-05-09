/**
 * Zustand auth store — single source of truth for authentication state.
 *
 * Security rules:
 *  - access_token lives in JS memory ONLY (this Zustand store).
 *    It is NEVER written to localStorage, sessionStorage, or any cookie.
 *    It vanishes on tab close — that's intentional.
 *  - refresh_token lives in an HttpOnly cookie set by FastAPI.
 *    JS cannot read it. It is sent automatically by the browser on
 *    requests to /api/v1/auth/refresh (via withCredentials on Axios).
 *  - persist: false — Zustand does not persist this store anywhere.
 */

import { create } from 'zustand';

export type UserRole = 'doctor' | 'admin';

interface AuthState {
  // Token — memory only, never persisted
  access_token: string | null;

  // Identity
  role: UserRole | null;
  user_id: number | null;
  user_name: string | null;

  // Derived convenience flag
  is_authenticated: boolean;

  // Actions
  setAuth: (params: {
    access_token: string;
    role: UserRole;
    user_id: number;
    user_name: string;
  }) => void;

  // Used by the Axios interceptor when a silent refresh returns a new token
  setAccessToken: (token: string) => void;

  // Called on logout or when refresh fails
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  // ── Initial state ──────────────────────────────────────────────────────────
  access_token: null,
  role: null,
  user_id: null,
  user_name: null,
  is_authenticated: false,

  // ── Actions ────────────────────────────────────────────────────────────────

  setAuth: ({ access_token, role, user_id, user_name }) =>
    set({
      access_token,
      role,
      user_id,
      user_name,
      is_authenticated: true,
    }),

  setAccessToken: (token) =>
    set((state) => ({
      ...state,
      access_token: token,
    })),

  clearAuth: () =>
    set({
      access_token: null,
      role: null,
      user_id: null,
      user_name: null,
      is_authenticated: false,
    }),
}));
