import React, { useEffect, useRef } from "react";
import { Tabs, useRouter } from "expo-router";
import { Home, UtensilsCrossed, BarChart2, User } from "lucide-react-native";
import { CopilotProvider, useCopilot } from "react-native-copilot";
import { useAuthStore } from "../../store/useAuthStore";
import { completeTour, getMyProfile } from "../../services/profile";

// Maps each tour step's `name` to its tab route. Order in the tab bar
// (Home, Meals, Progress, Profile) is what the tour walks, matching the
// CopilotStep `order` values set on each screen's header.
const STEP_ROUTES: Record<string, string> = {
  home: "/(tabs)",
  meals: "/(tabs)/meals",
  progress: "/(tabs)/progress",
  profile: "/(tabs)/profile",
};

function TourController() {
  const { start, copilotEvents } = useCopilot();
  const router = useRouter();
  const profile = useAuthStore(s => s.profile);
  const setProfile = useAuthStore(s => s.setProfile);

  // `start` closes over `steps`, which is empty until every CopilotStep has
  // registered — read the live value via a ref rather than freezing it in
  // the mount-only effect below (confirmed necessary: react-native-copilot
  // needs the registering screen fully mounted first, see upstream issue
  // https://github.com/mohebifar/react-native-copilot/issues/322).
  const startRef = useRef(start);
  startRef.current = start;
  const tourDone = !!profile?.product_tour_completed_at;

  useEffect(() => {
    if (tourDone) return;

    const onStepChange = (step: any) => {
      const route = step?.name ? STEP_ROUTES[step.name] : undefined;
      if (route) router.push(route as any);
    };
    const onStop = () => {
      completeTour()
        .then(getMyProfile)
        .then(setProfile)
        .catch(() => {}); // best-effort — tour already dismissed client-side either way
    };
    copilotEvents.on("stepChange", onStepChange);
    copilotEvents.on("stop", onStop);
    const t = setTimeout(() => startRef.current(), 2000);
    return () => {
      clearTimeout(t);
      copilotEvents.off("stepChange", onStepChange);
      copilotEvents.off("stop", onStop);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tourDone]);

  return null;
}

export default function TabsLayout() {
  return (
    <CopilotProvider>
      <TourController />
      <TabsInner />
    </CopilotProvider>
  );
}

function TabsInner() {
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: "#1E7C45",
        tabBarInactiveTintColor: "#9CA3AF",
        tabBarStyle: {
          backgroundColor: "#FFFFFF",
          borderTopColor: "#E5E7EB",
          borderTopWidth: 1,
          paddingBottom: 8,
          paddingTop: 4,
          height: 64,
        },
        tabBarLabelStyle: {
          fontSize: 11,
          fontFamily: "Inter_500Medium",
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Home",
          tabBarIcon: ({ color, size }) => <Home color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="meals"
        options={{
          title: "Meals",
          tabBarIcon: ({ color, size }) => <UtensilsCrossed color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="progress"
        options={{
          title: "Progress",
          tabBarIcon: ({ color, size }) => <BarChart2 color={color} size={size} />,
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarIcon: ({ color, size }) => <User color={color} size={size} />,
        }}
      />
    </Tabs>
  );
}
