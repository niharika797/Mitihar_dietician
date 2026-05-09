import React, { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import { Check } from "lucide-react-native";
import { OnboardingShell } from "../../components/shared";
import { useOnboardingStore } from "../../store/useOnboardingStore";

const LEVELS = [
  { key: "sedentary",         emoji: "🪑", title: "Sedentary",          desc: "Little or no exercise, desk job" },
  { key: "lightly_active",    emoji: "🚶", title: "Lightly Active",     desc: "Light exercise 1–3 days/week" },
  { key: "moderately_active", emoji: "🏃", title: "Moderately Active",  desc: "Moderate exercise 3–5 days/week" },
  { key: "very_active",       emoji: "🏋️", title: "Very Active",        desc: "Hard exercise 6–7 days/week" },
  { key: "super_active",      emoji: "🔥", title: "Super Active",       desc: "Very intense daily or twice daily" },
];

const CONDITIONS = [
  { key: "Healthy",          emoji: "✨", title: "Healthy",           desc: "Standard balanced nutrition" },
  { key: "Diabetic-Friendly", emoji: "🩸", title: "Diabetic-Friendly", desc: "Low glycemic index focus" },
  { key: "Gym-Friendly",      emoji: "💪", title: "Gym-Friendly",      desc: "Optimized for performance" },
];

export default function ActivityLevelScreen() {
  const router = useRouter();
  const { data, update } = useOnboardingStore();
  const [selected, setSelected] = useState(data.activity_level || "lightly_active");
  const [condition, setCondition] = useState(data.health_condition || "Healthy");

  const handleContinue = () => {
    update({ 
      activity_level: selected,
      health_condition: condition 
    });
    router.push("/(onboarding)/goals");
  };

  return (
    <OnboardingShell step={2} totalSteps={8} title="Health & Activity" subtitle="Customize your base nutritional profile" onContinue={handleContinue} continueDisabled={!selected}>
      <View style={s.section}>
        <Text style={s.sectionTitle}>Activity Level</Text>
        <View style={s.list}>
          {LEVELS.map(level => {
            const sel = selected === level.key;
            return (
              <Pressable key={level.key} onPress={() => setSelected(level.key)} style={[s.card, sel && s.cardSel]}>
                <Text style={s.emoji}>{level.emoji}</Text>
                <View style={s.cardBody}>
                  <Text style={s.cardTitle}>{level.title}</Text>
                  <Text style={s.cardDesc}>{level.desc}</Text>
                </View>
                {sel && <Check size={20} color="#1E7C45" />}
              </Pressable>
            );
          })}
        </View>
      </View>

      <View style={[s.section, { marginTop: 24 }]}>
        <Text style={s.sectionTitle}>Dietary Context</Text>
        <View style={s.list}>
          {CONDITIONS.map(item => {
            const sel = condition === item.key;
            return (
              <Pressable key={item.key} onPress={() => setCondition(item.key)} style={[s.card, sel && s.cardSel]}>
                <Text style={s.emoji}>{item.emoji}</Text>
                <View style={s.cardBody}>
                  <Text style={s.cardTitle}>{item.title}</Text>
                  <Text style={s.cardDesc}>{item.desc}</Text>
                </View>
                {sel && <Check size={20} color="#1E7C45" />}
              </Pressable>
            );
          })}
        </View>
      </View>
    </OnboardingShell>
  );
}

const s = StyleSheet.create({
  section:   { marginBottom: 10 },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: "#374151", marginBottom: 12 },
  list:      { gap: 10 },
  card:      { flexDirection: "row", alignItems: "center", gap: 12, padding: 14, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff" },
  cardSel:   { borderColor: "#23924F", backgroundColor: "#F0FDF4" },
  emoji:     { fontSize: 24, width: 32, textAlign: "center" },
  cardBody:  { flex: 1 },
  cardTitle: { fontSize: 15, fontWeight: "600", color: "#111827" },
  cardDesc:  { fontSize: 12, color: "#6B7280", marginTop: 2 },
});
