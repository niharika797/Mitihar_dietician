import "../global.css";
import React, { useEffect, useState } from "react";
import { Stack, useRouter, useSegments } from "expo-router";
import { useAuthStore } from "../store/useAuthStore";
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

// Keep native splash visible until we manually hide it after our animation
SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 1000 * 60 * 5 },
  },
});

function AuthGate({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    const inAuth = segments[0] === "(auth)";
    const inOnboarding = segments[0] === "(onboarding)";
    if (!isAuthenticated && !inAuth && !inOnboarding) {
      router.replace("/(auth)/login");
    } else if (isAuthenticated && inAuth) {
      router.replace("/(tabs)");
    }
  }, [isAuthenticated, isLoading, segments]);

  return <>{children}</>;
}

export default function RootLayout() {
  const bootstrap    = useAuthStore(s => s.bootstrap);
  const checkHardware = useBiometricStore(s => s.checkHardware);

  const [fontsLoaded] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
  });

  // Controls whether our custom JS splash is still showing
  const [splashDone, setSplashDone] = useState(false);

  // Bootstrap auth + biometric hardware check in parallel on mount
  useEffect(() => {
    bootstrap();
    checkHardware();
  }, []);

  // Hide the NATIVE splash as soon as fonts are ready — our JS splash takes over
  useEffect(() => {
    if (fontsLoaded) SplashScreen.hideAsync();
  }, [fontsLoaded]);

  // Don't render anything until fonts are loaded (avoids FOUC)
  if (!fontsLoaded) return null;

  // Show our animated JS splash until the animation calls onFinish()
  if (!splashDone) {
    return <SplashAnimation onFinish={() => setSplashDone(true)} />;
  }

  // ── Screen transition presets ──────────────────────────────────────────
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
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        {/* BiometricGate — shows fingerprint lock screen when enabled */}
        <BiometricGate>
          <AuthGate>
            <Stack screenOptions={{ headerShown: false }}>
              {/* ── Route groups ───────────────────────────────────────── */}
              <Stack.Screen name="(auth)"       options={{ headerShown: false, animation: "fade" }} />
              <Stack.Screen name="(onboarding)" options={{ headerShown: false, animation: "slide_from_right" }} />
              <Stack.Screen name="(tabs)"       options={{ headerShown: false, animation: "fade" }} />

              {/* ── Doctor connection flow ──────────────────────────── */}
              <Stack.Screen name="doctor/find-doctor"       options={SLIDE} />
              <Stack.Screen name="doctor/activate"          options={SLIDE} />
              <Stack.Screen name="doctor/connection-status" options={SLIDE} />

              {/* ── Home extras ─────────────────────────────────────── */}
              <Stack.Screen name="home/notifications" options={SLIDE} />

              {/* ── Meal plan screens ────────────────────────────────── */}
              <Stack.Screen name="meals/meal-detail"    options={SLIDE} />
              <Stack.Screen name="meals/week-view"      options={SLIDE} />
              <Stack.Screen name="meals/shopping-list"  options={SLIDE} />
              <Stack.Screen name="meals/plan-history"   options={SLIDE} />
              <Stack.Screen name="meals/plan-empty"     options={SLIDE} />

              {/* ── Meal logging ─────────────────────────────────────── */}
              <Stack.Screen name="log/log-meal"      options={MODAL} />
              <Stack.Screen name="log/log-from-plan" options={MODAL} />
              <Stack.Screen name="log/edit-log"      options={MODAL} />

              {/* ── Progress detail screens ──────────────────────────── */}
              <Stack.Screen name="progress/weight-log" options={SLIDE} />
              <Stack.Screen name="progress/water-log"  options={SLIDE} />
              <Stack.Screen name="progress/steps-log"  options={SLIDE} />
              <Stack.Screen name="progress/charts"     options={SLIDE} />

              {/* ── Profile settings screens ─────────────────────────── */}
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
  );
}
