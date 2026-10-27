/**
 * useRateLimitStore.ts
 * Drives the "please take a break" pop-up shown when the server answers 429.
 * The axios response interceptor calls show(); RateLimitModal (mounted once in the root
 * layout) reads it. No persistence: it is a transient notice.
 */
import { create } from "zustand";

export const RATE_LIMIT_FALLBACK =
  "Too many attempts. For your security, we have paused this action for a short while. " +
  "Please take a break and try again shortly.";

interface RateLimitState {
  visible: boolean;
  message: string;
  show: (message?: string) => void;
  hide: () => void;
}

export const useRateLimitStore = create<RateLimitState>((set, get) => ({
  visible: false,
  message: RATE_LIMIT_FALLBACK,
  // Ignore repeats while the pop-up is already open (parallel requests all get a 429).
  show: (message) => {
    if (get().visible) return;
    set({ visible: true, message: message || RATE_LIMIT_FALLBACK });
  },
  hide: () => set({ visible: false }),
}));
