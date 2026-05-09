/**
 * BiometricGate.tsx
 * Sits between bootstrap() completing and the app rendering.
 * If biometric is enabled, shows a lock screen with fingerprint/Face ID prompt.
 *
 * States:
 *   idle      — checking if biometric needed (brief)
 *   locked    — showing the lock UI, waiting for user to tap "Unlock"
 *   unlocked  — passed, renders children normally
 *   fallback  — biometric failed 3x, show "Use Password" button
 */
import React, { useEffect, useState, useCallback } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import Svg, { Ellipse, Path } from "react-native-svg";
import { useAuthStore } from "../store/useAuthStore";
import { useBiometricStore } from "../store/useBiometricStore";
import { useRouter } from "expo-router";

type GateState = "idle" | "locked" | "unlocked" | "fallback";

const MAX_ATTEMPTS = 3;

export default function BiometricGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuthStore();
  const { enabled, isReady: biometricReady, setLastUnlocked } = useBiometricStore();

  const [gateState, setGateState] = useState<GateState>("idle");
  const [attempts, setAttempts] = useState(0);
  const [hint, setHint]         = useState("");

  // Only make the gate decision once BOTH stores have finished loading.
  // Previously this effect depended on [isAuthenticated, enabled] separately,
  // which caused a double-fire: first when bootstrap() finished (enabled=false →
  // unlocked), then again when checkHardware() finished (enabled=true → locked).
  // Now we wait for authLoading=false AND biometricReady=true before acting.
  useEffect(() => {
    if (authLoading || !biometricReady) return;  // both must be settled first

    if (!isAuthenticated) {
      setGateState("unlocked"); // not logged in — let AuthGate handle routing
      return;
    }
    if (!enabled) {
      setGateState("unlocked"); // biometric off — open normally
      return;
    }
    setGateState("locked");
    triggerPrompt();            // auto-show prompt on first lock
  }, [authLoading, biometricReady, isAuthenticated, enabled]);

  const triggerPrompt = useCallback(async () => {
    try {
      const LocalAuth = await import("expo-local-authentication");
      const supportedTypes = await LocalAuth.supportedAuthenticationTypesAsync();
      const isFace = supportedTypes.includes(
        LocalAuth.AuthenticationType.FACIAL_RECOGNITION
      );
      const result = await LocalAuth.authenticateAsync({
        promptMessage: "Unlock Mitihar",
        fallbackLabel: "Use Password",
        cancelLabel: "Cancel",
        disableDeviceFallback: false,
      });
      if (result.success) {
        setLastUnlocked();
        setGateState("unlocked");
      } else {
        const next = attempts + 1;
        setAttempts(next);
        if (result.error === "user_cancel") {
          setHint("Tap to try again");
        } else if (next >= MAX_ATTEMPTS) {
          setHint("Too many attempts. Use your password.");
          setGateState("fallback");
        } else {
          setHint(`${MAX_ATTEMPTS - next} attempt${MAX_ATTEMPTS - next === 1 ? "" : "s"} remaining`);
        }
      }
    } catch {
      setGateState("unlocked"); // graceful fallback if library fails
    }
  }, [attempts]);

  const handleFallback = async () => {
    const { logout } = useAuthStore.getState();
    await logout();
    router.replace("/(auth)/login");
  };

  if (gateState === "idle" || gateState === "unlocked") {
    return <>{children}</>;
  }

  // ── Lock screen UI ──────────────────────────────────────────────────────
  return (
    <View style={s.root}>
      <View style={s.logoWrap}>
        <Svg width={52} height={52} viewBox="0 0 48 48">
          <Ellipse cx={24} cy={30} rx={14} ry={10} fill="#DCFCE7" />
          <Path d="M24 8 C 24 8, 12 18, 12 28 C 12 36 18 40 24 40 C 30 40 36 36 36 28 C 36 18 24 8 24 8Z" fill="#1E7C45" opacity={0.92} />
          <Path d="M24 8 C 24 8, 24 22, 24 38" stroke="#34B164" strokeWidth={1.5} strokeDasharray="2 3" />
        </Svg>
      </View>

      <Text style={s.appName}>Mitihar</Text>
      <Text style={s.lockLabel}>🔒 App Locked</Text>
      <Text style={s.lockSub}>Verify your identity to continue</Text>

      {hint !== "" && <Text style={s.hint}>{hint}</Text>}

      {gateState === "fallback" ? (
        <Pressable style={s.fallbackBtn} onPress={handleFallback}>
          <Text style={s.fallbackText}>Use Password Instead</Text>
        </Pressable>
      ) : (
        <Pressable style={s.unlockBtn} onPress={triggerPrompt}>
          <Text style={s.unlockIcon}>👆</Text>
          <Text style={s.unlockText}>Tap to Unlock</Text>
        </Pressable>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  root:        { flex: 1, backgroundColor: "#fff", alignItems: "center", justifyContent: "center", gap: 12 },
  logoWrap:    { width: 80, height: 80, borderRadius: 20, backgroundColor: "#F0FDF4", alignItems: "center", justifyContent: "center", marginBottom: 8 },
  appName:     { fontSize: 28, fontWeight: "700", color: "#1E7C45" },
  lockLabel:   { fontSize: 18, fontWeight: "600", color: "#111827", marginTop: 16 },
  lockSub:     { fontSize: 14, color: "#6B7280", textAlign: "center", paddingHorizontal: 40 },
  hint:        { fontSize: 13, color: "#DC2626", marginTop: 4 },
  unlockBtn:   { marginTop: 24, alignItems: "center", gap: 6, padding: 20, borderRadius: 20, borderWidth: 1.5, borderColor: "#DCFCE7", backgroundColor: "#F0FDF4" },
  unlockIcon:  { fontSize: 36 },
  unlockText:  { fontSize: 14, fontWeight: "600", color: "#1E7C45" },
  fallbackBtn: { marginTop: 24, height: 48, paddingHorizontal: 32, borderRadius: 24, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  fallbackText:{ fontSize: 14, fontWeight: "500", color: "#374151" },
});
