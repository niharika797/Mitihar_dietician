import { create } from "zustand";
import * as SecureStore from "expo-secure-store";
import { SECURE_KEYS } from "../lib/axios";
import type { PatientProfile } from "../types";

interface AuthState {
  // ── State ──────────────────────────────────────────────────────────────
  isAuthenticated: boolean;
  profile: PatientProfile | null;
  isLoading: boolean;          // true while bootstrapping from SecureStore

  // ── Actions ────────────────────────────────────────────────────────────
  setTokens: (accessToken: string, refreshToken: string) => Promise<void>;
  setProfile: (profile: PatientProfile) => void;
  logout: () => Promise<void>;
  bootstrap: () => Promise<void>;  // call once on app start
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

  setProfile: (profile) => set({ profile }),

  logout: async () => {
    await SecureStore.deleteItemAsync(SECURE_KEYS.ACCESS_TOKEN);
    await SecureStore.deleteItemAsync(SECURE_KEYS.REFRESH_TOKEN);
    set({ isAuthenticated: false, profile: null });
  },

  // Called from root _layout on mount — checks SecureStore for existing token
  bootstrap: async () => {
    try {
      const token = await SecureStore.getItemAsync(SECURE_KEYS.ACCESS_TOKEN);
      set({ isAuthenticated: !!token, isLoading: false });
    } catch {
      set({ isAuthenticated: false, isLoading: false });
    }
  },
}));
