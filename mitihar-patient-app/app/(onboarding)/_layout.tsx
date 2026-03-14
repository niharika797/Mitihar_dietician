import { Stack } from "expo-router";

export default function OnboardingLayout() {
  return (
    <Stack screenOptions={{ headerShown: false, animation: "slide_from_right" }}>
      <Stack.Screen name="personal-info" />
      <Stack.Screen name="activity-level" />
      <Stack.Screen name="goals" />
      <Stack.Screen name="medical-conditions" />
      <Stack.Screen name="allergies" />
      <Stack.Screen name="dietary-preferences" />
      <Stack.Screen name="lifestyle" />
      <Stack.Screen name="disclaimer" />
      <Stack.Screen name="complete" />
    </Stack>
  );
}
