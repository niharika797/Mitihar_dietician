import { create } from "zustand";
import * as SecureStore from "expo-secure-store";
import axiosInstance, { SECURE_KEYS } from "../lib/axios";
import type { PatientProfile } from "../types";
import { getMyProfile } from "../services/profile";

interface AuthState {
  // ── State ──────────────────────────────────────────────────────────────
  isAuthenticated: boolean;
  profile: PatientProfile | null;
  isLoading: boolean;

  // ── Actions ────────────────────────────────────────────────────────────

  /**
   * REGISTRATION PATH ONLY.
   * Persists tokens and flips isAuthenticated.
   * Intentionally does NOT set profile — AuthGate sees profile===null and
   * routes to onboarding, which is exactly right for a brand-new user.
   */
  setTokens: (accessToken: string, refreshToken: string) => Promise<void>;

  /**
   * LOGIN PATH.
   * Persists tokens + sets profile in ONE atomic Zustand commit.
   * AuthGate's useEffect always reads isAuthenticated and profile together,
   * so there is no window where it sees isAuthenticated=true but profile=null
   * and incorrectly sends a returning user to onboarding.
   */
  loginSuccess: (
    accessToken: string,
    refreshToken: string,
    profile: PatientProfile,
  ) => void;

  updateAccessToken: (accessToken: string) => Promise<void>;
  setProfile: (profile: PatientProfile) => void;
  logout: () => Promise<void>;

  /**
   * Called once on app mount.
   * Loads token; if valid, also fetches /users/me so AuthGate can route
   * correctly on a cold start — no flash-of-wrong-screen.
   */
  bootstrap: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  profile: null,
  isLoading: true,

  setTokens: async (accessToken, refreshToken) => {
    await SecureStore.setItemAsync(SECURE_KEYS.ACCESS_TOKEN, accessToken);
    await SecureStore.setItemAsync(SECURE_KEYS.REFRESH_TOKEN, refreshToken);
    set({ isAuthenticated: true });
  },

  loginSuccess: (accessToken, refreshToken, profile) => {
    // Fire-and-forget storage writes — UI never needs to await them
    SecureStore.setItemAsync(SECURE_KEYS.ACCESS_TOKEN, accessToken);
    SecureStore.setItemAsync(SECURE_KEYS.REFRESH_TOKEN, refreshToken);
    // Single commit — AuthGate always sees both fields in one render
    set({ isAuthenticated: true, profile });
  },

  updateAccessToken: async (accessToken) => {
    await SecureStore.setItemAsync(SECURE_KEYS.ACCESS_TOKEN, accessToken);
  },

  setProfile: (profile) => set({ profile }),

  logout: async () => {
    try {
      await axiosInstance.post('/auth/register-fcm-token', { fcm_token: null });
    } catch (_) {}
    await SecureStore.deleteItemAsync(SECURE_KEYS.ACCESS_TOKEN);
    await SecureStore.deleteItemAsync(SECURE_KEYS.REFRESH_TOKEN);
    // Clear biometric preference from BOTH SecureStore (persisted) AND the
    // in-memory Zustand store. Without clearing in-memory state, a new
    // registration in the same app session would inherit enabled=true and
    // trigger the biometric gate for a brand-new account that never set it up.
    await SecureStore.deleteItemAsync("mityahar_biometric_enabled");
    const { useBiometricStore } = await import("./useBiometricStore");
    useBiometricStore.setState({ enabled: false });
    set({ isAuthenticated: false, profile: null });
  },

  bootstrap: async () => {
    try {
      const token = await SecureStore.getItemAsync(SECURE_KEYS.ACCESS_TOKEN);
      if (!token) {
        set({ isAuthenticated: false, isLoading: false });
        return;
      }
      // Pre-load profile so AuthGate has full state on the very first render
      try {
        const profile = await getMyProfile();
        set({ isAuthenticated: true, profile, isLoading: false });
      } catch {
        // Profile fetch failed (expired tokens or transient network error).
        // Treat as unauthenticated — the axios interceptor already wiped any
        // expired tokens before this catch was reached. Setting true here
        // would leave AuthGate in a false-positive authenticated state that
        // routes users to onboarding without them ever submitting the form.
        set({ isAuthenticated: false, isLoading: false });
      }
    } catch {
      set({ isAuthenticated: false, isLoading: false });
    }
  },
}));
