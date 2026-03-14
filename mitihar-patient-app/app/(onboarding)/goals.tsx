import React, { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import { OnboardingShell, ChipGrid } from "../../components/shared";
import { useOnboardingStore } from "../../store/useOnboardingStore";

const GOALS = ["Weight Loss","Muscle Gain","Manage Diabetes","Heart Health","PCOS/PCOD Mgmt","Better Energy","Reduce Cholesterol","Build Stamina"];
const PACES = ["Slow & Steady", "Moderate", "Fast"];
const PACE_KEYS = ["slow", "moderate", "fast"];

export default function GoalsScreen() {
  const router = useRouter();
  const { data, update } = useOnboardingStore();
  const [goals, setGoals] = useState<string[]>(data.health_goals ?? []);
  const [paceIdx, setPaceIdx] = useState(PACE_KEYS.indexOf(data.goal_pace) >= 0 ? PACE_KEYS.indexOf(data.goal_pace) : 1);

  const toggleGoal = (g: string) =>
    setGoals(prev => prev.includes(g) ? prev.filter(x => x !== g) : [...prev, g]);

  const handleContinue = () => {
    update({ health_goals: goals, goal_pace: PACE_KEYS[paceIdx] });
    router.push("/(onboarding)/medical-conditions");
  };

  return (
    <OnboardingShell step={3} totalSteps={8} title="Your Health Goals" subtitle="Select all that apply" onContinue={handleContinue} continueDisabled={goals.length === 0} onSkip={() => router.push("/(onboarding)/medical-conditions")}>
      <View style={s.form}>
        <ChipGrid options={GOALS} selected={goals} onToggle={toggleGoal} columns={2} />

        <View style={s.paceSection}>
          <Text style={s.label}>Pace (how fast?)</Text>
          <View style={s.paceRow}>
            {PACES.map((p, i) => (
              <Pressable key={p} onPress={() => setPaceIdx(i)} style={[s.paceBtn, paceIdx === i && s.paceBtnSel]}>
                <Text style={[s.paceText, paceIdx === i && s.paceTextSel]}>{p}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      </View>
    </OnboardingShell>
  );
}

const s = StyleSheet.create({
  form:         { gap: 20 },
  paceSection:  { gap: 10 },
  label:        { fontSize: 14, fontWeight: "500", color: "#374151" },
  paceRow:      { flexDirection: "row", gap: 8 },
  paceBtn:      { flex: 1, height: 44, borderRadius: 10, borderWidth: 1.5, borderColor: "#D1D5DB", alignItems: "center", justifyContent: "center", backgroundColor: "#fff" },
  paceBtnSel:   { borderColor: "#1E7C45", backgroundColor: "#1E7C45" },
  paceText:     { fontSize: 13, fontWeight: "500", color: "#374151" },
  paceTextSel:  { color: "#fff" },
});
