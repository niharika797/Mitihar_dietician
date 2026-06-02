/**
 * useBiometricStore.ts
 * Manages biometric unlock preference, persisted in storage.
 *
 * State:
 *   enabled           — whether user has turned on biometric unlock
 *   hardwareAvailable — device has fingerprint/face sensor
 *   enrolled          — user has biometrics enrolled in device settings
 *   lastUnlocked      — timestamp of last successful biometric unlock
 *   isReady           — true once checkHardware() has completed (regardless of result)
 *
 * Flow:
 *   1. On app start, checkHardware() is called to probe device capabilities
 *   2. BiometricGate waits for BOTH isReady=true AND authStore.isLoading=false
 *      before making any gate decision — this prevents the double-prompt race
 *      where the gate fires once with enabled=false then again with enabled=true
 *   3. If user enables biometric in settings, setEnabled(true) persists it
 *   4. Successful unlock sets lastUnlocked; failed unlock routes to login
 */
import { create } from "zustand";
import { storage } from "../lib/storage";

const BIOMETRIC_KEY = "mityahar_biometric_enabled";

interface BiometricState {
  enabled: boolean;
  hardwareAvailable: boolean;
  enrolled: boolean;
  lastUnlocked: number | null;   // Date.now() of last success
  isReady: boolean;              // true once checkHardware() has finished

  // Actions
  setEnabled: (val: boolean) => Promise<void>;
  setLastUnlocked: () => void;
  checkHardware: () => Promise<void>;  // probe device + load persisted pref
}

export const useBiometricStore = create<BiometricState>((set) => ({
  enabled: false,
  hardwareAvailable: false,
  enrolled: false,
  lastUnlocked: null,
  isReady: false,

  setEnabled: async (val) => {
    await storage.setItemAsync(BIOMETRIC_KEY, val ? "1" : "0");
    set({ enabled: val });
  },

  setLastUnlocked: () => set({ lastUnlocked: Date.now() }),

  checkHardware: async () => {
    try {
      const LocalAuth = await import("expo-local-authentication");
      const [hasHW, isEnrolled, savedPref] = await Promise.all([
        LocalAuth.hasHardwareAsync(),
        LocalAuth.isEnrolledAsync(),
        storage.getItemAsync(BIOMETRIC_KEY),
      ]);
      set({
        hardwareAvailable: hasHW,
        enrolled: isEnrolled,
        // Only enable if device supports it AND user previously turned it on
        enabled: hasHW && isEnrolled && savedPref === "1",
        isReady: true,   // signal that hardware check is fully complete
      });
    } catch {
      set({ hardwareAvailable: false, enrolled: false, enabled: false, isReady: true });
    }
  },
}));
