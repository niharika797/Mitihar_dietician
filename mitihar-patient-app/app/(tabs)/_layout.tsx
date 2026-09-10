import React, { useEffect, useRef } from "react";
import { View, Text, TouchableOpacity, StyleSheet } from "react-native";
import { Tabs, useRouter } from "expo-router";
import { Home, UtensilsCrossed, BarChart2, User } from "lucide-react-native";
import { CopilotProvider, CopilotStep, walkthroughable, useCopilot } from "react-native-copilot";
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
const TOTAL_STEPS = 4;

// react-native-copilot's next/prev navigation walks `orderedSteps`, built
// only from CopilotSteps currently mounted and registered. Meals/Progress/
// Profile are separate routes — their real CopilotStep doesn't exist until
// the user has actually navigated there, so goToNext() would have nowhere
// to go past Home. These invisible placeholders register all 4 up front so
// the tour knows its full length from the start; each one is overwritten by
// the real, positioned CopilotStep the moment that screen actually mounts.
// Text is duplicated from each real screen's CopilotStep so the tooltip is
// never wrong if the tour briefly targets a placeholder that hasn't been
// superseded yet.
const StubTarget = walkthroughable(
  React.forwardRef<View>(function StubTarget(_props, ref) {
    return <View ref={ref} style={{ position: "absolute", width: 1, height: 1, opacity: 0 }} pointerEvents="none" />;
  }),
);
function TourStubSteps() {
  return (
    <>
      <CopilotStep order={2} name="meals" text="Your weekly meal plan lives here — browse days and confirm your choices.">
        <StubTarget />
      </CopilotStep>
      <CopilotStep order={3} name="progress" text="Track your weight, streaks, and macros over time.">
        <StubTarget />
      </CopilotStep>
      <CopilotStep order={4} name="profile" text="Manage your details, subscription, and settings here.">
        <StubTarget />
      </CopilotStep>
    </>
  );
}

// Custom tooltip, same layout as react-native-copilot's default, but
// "last step" is decided from the tour's known, fixed step count instead of
// the library's own isLastStep. The other 3 screens only register their
// CopilotStep once actually navigated to (they're separate routes, not
// mounted up front), so on step 1 the library only knows about 1 registered
// step and shows "Finish" instead of "Next" — tapping it would end the tour
// immediately, before Meals/Progress/Profile are ever shown.
function TourTooltip() {
  const { goToNext, stop, currentStep, currentStepNumber } = useCopilot();
  const isLast = currentStepNumber >= TOTAL_STEPS;
  return (
    <View>
      <View style={tt.container}>
        <Text style={tt.text}>{currentStep?.text}</Text>
      </View>
      <View style={tt.bottomBar}>
        {!isLast && (
          <TouchableOpacity onPress={() => stop()} style={tt.button}>
            <Text style={tt.buttonText}>Skip</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity onPress={() => (isLast ? stop() : goToNext())} style={tt.button}>
          <Text style={tt.buttonText}>{isLast ? "Finish" : "Next"}</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}
const tt = StyleSheet.create({
  container: { flex: 1 },
  text: {},
  bottomBar: { marginTop: 10, flexDirection: "row", justifyContent: "flex-end" },
  button: { padding: 10 },
  buttonText: { color: "#1E7C45" },
});

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

  // Tracks the last step name we've already navigated+re-synced for, so
  // arriving on a screen whose real CopilotStep re-registers (replacing the
  // placeholder) and re-emits stepChange doesn't re-trigger navigation.
  const syncedStep = useRef<string | null>(null);

  useEffect(() => {
    if (tourDone) return;

    const onStepChange = (step: any) => {
      if (!step?.name || syncedStep.current === step.name) return;
      const route = STEP_ROUTES[step.name];
      if (!route) return;
      syncedStep.current = step.name;
      router.push(route as any);
      // The step that just changed may still be the always-mounted
      // placeholder (see TourStubSteps) — the real screen's own CopilotStep
      // hasn't registered yet at the instant stepChange fires. Re-target
      // once it has, so the highlight measures the real, visible element
      // instead of the invisible placeholder.
      setTimeout(() => startRef.current(step.name), 400);
    };
    const onStop = () => {
      completeTour()
        .then(getMyProfile)
        .then(setProfile)
        .catch(() => {}); // best-effort — tour already dismissed client-side either way
    };
    copilotEvents.on("stepChange", onStepChange);
    copilotEvents.on("stop", onStop);
    const t = setTimeout(() => {
      syncedStep.current = "home";
      startRef.current();
    }, 2000);
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
    <CopilotProvider tooltipComponent={TourTooltip}>
      <TourController />
      <TourStubSteps />
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
