import "../global.css";
import React, { useEffect, useRef, useState } from "react";
import { LogBox, Text, View } from "react-native";
import { Stack, useRouter, useSegments } from "expo-router";
import * as Sentry from "@sentry/react-native";

// Crash reporting. DSN comes from EXPO_PUBLIC_SENTRY_DSN (eas.json env) —
// disabled when unset (local dev without a Sentry project).
Sentry.init({
  dsn: process.env.EXPO_PUBLIC_SENTRY_DSN,
  enabled: !!process.env.EXPO_PUBLIC_SENTRY_DSN,
});

// Suppress the dev-mode-only Android activity lifecycle race in expo-keep-awake.
// expo-router internally calls useKeepAwake(); if the Android Activity is
// destroyed during hot-reload / backgrounding, the native call is rejected.
// This is harmless in development and does not occur in production builds.
if (__DEV__) {
  LogBox.ignoreLogs([
    "ExpoKeepAwake.activate",
    "The current activity is no longer available",
  ]);
}
import { useAuthStore } from "../store/useAuthStore";
import {
  requestPermissions,
  getFCMToken,
  sendTokenToBackend,
  setupNotificationListeners,
} from "../lib/notifications";
import { useBiometricStore } from "../store/useBiometricStore";
import { StatusBar } from "expo-status-bar";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  useFonts,
  Inter_400Regular,
  Inter_500Medium,
  Inter_600SemiBold,
  Inter_700Bold,
} from "@expo-google-fonts/inter";
import * as SplashScreen from "expo-splash-screen";
import { ToastProvider } from "../components/shared";
import SplashAnimation from "../components/SplashAnimation";
import BiometricGate from "../components/BiometricGate";

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 1000 * 60 * 5 },
  },
});

// ── Onboarding completion check ────────────────────────────────────────────
// A profile is considered fully onboarded ONLY when disclaimer_accepted_at is
// set on the server. This is the single authoritative signal.
//
// The old height_cm > 0 && weight_kg > 0 fallback has been intentionally
// removed — registration now sends height=0, weight=0 so that fallback would
// have fired immediately for every new account and skipped onboarding.
import type { PatientProfile } from "../types";
function isOnboardingComplete(profile: PatientProfile | null): boolean {
  if (!profile) return false;
  return !!profile.disclaimer_accepted_at;
}

// ── AuthGate — the single source of truth for post-auth routing ────────────
//
// DESIGN RULE: AuthGate is the ONLY place that calls router.replace after
// authentication state changes. login.tsx and register.tsx only mutate store
// state; they never navigate themselves. This eliminates the race condition
// where both AuthGate and the auth screens fought over router.replace.
//
// Routing matrix:
//   unauthenticated + not in (auth)/(onboarding)  → /(auth)/login
//   authenticated   + in (auth)                   →
//       profile complete   → /(tabs)
//       profile incomplete → /(onboarding)/personal-info
//   all other cases                               → no-op (stay put)
function AuthGate({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, profile } = useAuthStore();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;

    const inAuth       = segments[0] === "(auth)";
    const inOnboarding = segments[0] === "(onboarding)";

    if (!isAuthenticated && !inAuth && !inOnboarding) {
      // Not logged in and not already heading to auth — send to login
      router.replace("/(auth)/login");
      return;
    }

    if (isAuthenticated && inAuth) {
      // Just authenticated (login or register) — decide destination based on profile
      if (isOnboardingComplete(profile)) {
        router.replace("/(tabs)");
      } else {
        router.replace("/(onboarding)/personal-info");
      }
    }
  }, [isAuthenticated, isLoading, profile, segments]);

  // FCM setup — fire-and-forget after any successful auth, cleaned up on logout
  const fcmCleanupRef = useRef<(() => void) | undefined>(undefined);
  useEffect(() => {
    if (!isAuthenticated) {
      fcmCleanupRef.current?.();
      fcmCleanupRef.current = undefined;
      return;
    }
    (async () => {
      try {
        const granted = await requestPermissions();
        if (!granted) return;
        const token = await getFCMToken();
        if (token) await sendTokenToBackend(token);
        fcmCleanupRef.current = setupNotificationListeners(router);
      } catch (e) {
        console.warn('FCM setup failed silently', e);
      }
    })();
  }, [isAuthenticated]);

  return <>{children}</>;
}

function RootLayout() {
  const bootstrap     = useAuthStore(s => s.bootstrap);
  const isLoading     = useAuthStore(s => s.isLoading);
  const checkHardware = useBiometricStore(s => s.checkHardware);

  const [fontsLoaded] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
  });

  const [splashDone, setSplashDone] = useState(false);

  useEffect(() => {
    bootstrap();
    checkHardware();
  }, []);

  // Keep the native splash visible until BOTH fonts are loaded AND bootstrap
  // has finished. This closes the race window where the user could navigate to
  // (auth)/register while isLoading=true (AuthGate disabled), then get bounced
  // to onboarding the moment bootstrap resolves with isAuthenticated=true.
  useEffect(() => {
    if (fontsLoaded && !isLoading) SplashScreen.hideAsync();
  }, [fontsLoaded, isLoading]);

  if (!fontsLoaded || isLoading) return null;

  if (!splashDone) {
    return <SplashAnimation onFinish={() => setSplashDone(true)} />;
  }

  const SLIDE = {
    headerShown: false,
    animation: "slide_from_right",
    gestureEnabled: true,
  } as const;

  const MODAL = {
    headerShown: false,
    animation: "slide_from_bottom",
    gestureEnabled: true,
    presentation: "modal",
  } as const;

  return (
    <Sentry.ErrorBoundary
      fallback={
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", padding: 32 }}>
          <Text style={{ fontSize: 16, fontWeight: "600", color: "#111827" }}>
            Something went wrong
          </Text>
          <Text style={{ fontSize: 14, color: "#6B7280", marginTop: 8, textAlign: "center" }}>
            Please close and reopen the app.
          </Text>
        </View>
      }
    >
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BiometricGate>
          <AuthGate>
            <Stack screenOptions={{ headerShown: false }}>
              <Stack.Screen name="(auth)"       options={{ headerShown: false, animation: "fade" }} />
              <Stack.Screen name="(onboarding)" options={{ headerShown: false, animation: "slide_from_right" }} />
              <Stack.Screen name="(tabs)"       options={{ headerShown: false, animation: "fade" }} />
              <Stack.Screen name="doctor/find-doctor"       options={SLIDE} />
              <Stack.Screen name="doctor/activate"          options={SLIDE} />
              <Stack.Screen name="doctor/connection-status" options={SLIDE} />
              <Stack.Screen name="home/notifications" options={SLIDE} />
              <Stack.Screen name="meals/meal-detail"    options={SLIDE} />
              <Stack.Screen name="meals/week-view"      options={SLIDE} />
              <Stack.Screen name="meals/plan-history"   options={SLIDE} />
              <Stack.Screen name="meals/plan-empty"     options={SLIDE} />
              <Stack.Screen name="log/log-meal"      options={MODAL} />
              <Stack.Screen name="log/log-from-plan" options={MODAL} />
              <Stack.Screen name="log/edit-log"      options={MODAL} />
              <Stack.Screen name="progress/weight-log" options={SLIDE} />
              <Stack.Screen name="progress/charts"     options={SLIDE} />
              <Stack.Screen name="profile/edit-profile"   options={SLIDE} />
              <Stack.Screen name="profile/notifications"  options={SLIDE} />
              <Stack.Screen name="profile/account"        options={SLIDE} />
              <Stack.Screen name="profile/about"          options={SLIDE} />
            </Stack>
            <StatusBar style="dark" />
          </AuthGate>
        </BiometricGate>
      </ToastProvider>
    </QueryClientProvider>
    </Sentry.ErrorBoundary>
  );
}

export default Sentry.wrap(RootLayout);
