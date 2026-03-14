import "../global.css";
import React, { useEffect } from "react";
import { Stack, useRouter, useSegments } from "expo-router";
import { useAuthStore } from "../store/useAuthStore";
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

SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 1000 * 60 * 5,
    },
  },
});

function AuthGate({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuthStore();
  const segments = useSegments();
  const router = useRouter();

  useEffect(() => {
    if (isLoading) return;
    const inAuth = segments[0] === "(auth)";
    if (!isAuthenticated && !inAuth) {
      router.replace("/(auth)/login");
    } else if (isAuthenticated && inAuth) {
      router.replace("/(tabs)");
    }
  }, [isAuthenticated, isLoading, segments]);

  return <>{children}</>;
}

export default function RootLayout() {
  const bootstrap = useAuthStore((s) => s.bootstrap);
  const [fontsLoaded] = useFonts({
    Inter_400Regular,
    Inter_500Medium,
    Inter_600SemiBold,
    Inter_700Bold,
  });

  useEffect(() => {
    bootstrap();
  }, []);

  useEffect(() => {
    if (fontsLoaded) SplashScreen.hideAsync();
  }, [fontsLoaded]);

  if (!fontsLoaded) return null;

  // ── Global slide transition for all push screens ───────────────────────
  const SLIDE = {
    headerShown: false,
    animation: "slide_from_right",
    gestureEnabled: true,
  } as const;

  // ── Modal slide-up for bottom-sheet-style flows ────────────────────────
  const MODAL = {
    headerShown: false,
    animation: "slide_from_bottom",
    gestureEnabled: true,
    presentation: "modal",
  } as const;

  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthGate>
          <Stack screenOptions={{ headerShown: false }}>
            {/* ── Grouped route segments (tabs, auth, onboarding) ───────── */}
            <Stack.Screen name="(auth)"        options={{ headerShown: false, animation: "fade" }} />
            <Stack.Screen name="(onboarding)"  options={{ headerShown: false, animation: "slide_from_right" }} />
            <Stack.Screen name="(tabs)"        options={{ headerShown: false, animation: "fade" }} />

            {/* ── Doctor connection flow ──────────────────────────────── */}
            <Stack.Screen name="doctor/find-doctor"        options={SLIDE} />
            <Stack.Screen name="doctor/activate"           options={SLIDE} />
            <Stack.Screen name="doctor/connection-status"  options={SLIDE} />

            {/* ── Home extras ─────────────────────────────────────────── */}
            <Stack.Screen name="home/notifications"        options={SLIDE} />

            {/* ── Meal plan screens ────────────────────────────────────── */}
            <Stack.Screen name="meals/meal-detail"         options={SLIDE} />
            <Stack.Screen name="meals/week-view"           options={SLIDE} />
            <Stack.Screen name="meals/shopping-list"       options={SLIDE} />
            <Stack.Screen name="meals/plan-history"        options={SLIDE} />
            <Stack.Screen name="meals/plan-empty"          options={SLIDE} />

            {/* ── Meal logging (modal slide-up feels more natural) ─────── */}
            <Stack.Screen name="log/log-meal"              options={MODAL} />
            <Stack.Screen name="log/log-from-plan"         options={MODAL} />
            <Stack.Screen name="log/edit-log"              options={MODAL} />

            {/* ── Progress detail screens ──────────────────────────────── */}
            <Stack.Screen name="progress/weight-log"       options={SLIDE} />
            <Stack.Screen name="progress/water-log"        options={SLIDE} />
            <Stack.Screen name="progress/steps-log"        options={SLIDE} />
            <Stack.Screen name="progress/charts"           options={SLIDE} />

            {/* ── Profile settings screens ─────────────────────────────── */}
            <Stack.Screen name="profile/edit-profile"      options={SLIDE} />
            <Stack.Screen name="profile/notifications"     options={SLIDE} />
            <Stack.Screen name="profile/account"           options={SLIDE} />
            <Stack.Screen name="profile/about"             options={SLIDE} />
          </Stack>
          <StatusBar style="dark" />
        </AuthGate>
      </ToastProvider>
    </QueryClientProvider>
  );
}
