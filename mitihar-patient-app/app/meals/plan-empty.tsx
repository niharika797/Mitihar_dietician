import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { useRouter } from "expo-router";

export default function PlanEmptyScreen() {
  const router = useRouter();
  return (
    <View style={s.root}>
      <View style={s.card}>
        <Text style={s.emoji}>🥗</Text>
        <Text style={s.title}>No Meal Plan Yet</Text>
        <Text style={s.sub}>
          Your doctor will create a personalised Indian meal plan for you within 24–48 hours of connecting.
        </Text>
        <View style={s.steps}>
          {[
            { n: "1", label: "Connect with a doctor" },
            { n: "2", label: "Doctor creates your plan" },
            { n: "3", label: "Start eating healthy!" },
          ].map(step => (
            <View key={step.n} style={s.step}>
              <View style={s.stepNum}><Text style={s.stepNumText}>{step.n}</Text></View>
              <Text style={s.stepLabel}>{step.label}</Text>
            </View>
          ))}
        </View>
      </View>
      <Pressable style={s.primaryBtn} onPress={() => router.push("/doctor/find-doctor")}>
        <Text style={s.primaryBtnText}>Find a Doctor</Text>
      </Pressable>
      <Pressable style={s.secondaryBtn} onPress={() => router.push("/doctor/activate")}>
        <Text style={s.secondaryBtnText}>Have a Code? Activate</Text>
      </Pressable>
    </View>
  );
}

const s = StyleSheet.create({
  root:           { flex: 1, backgroundColor: "#F9FAFB", padding: 24, justifyContent: "center" },
  card:           { backgroundColor: "#fff", borderRadius: 16, borderWidth: 1, borderColor: "#E5E7EB", padding: 28, alignItems: "center", marginBottom: 20 },
  emoji:          { fontSize: 56, marginBottom: 16 },
  title:          { fontSize: 22, fontWeight: "700", color: "#111827", marginBottom: 10, textAlign: "center" },
  sub:            { fontSize: 14, color: "#6B7280", textAlign: "center", lineHeight: 22, marginBottom: 24 },
  steps:          { width: "100%", gap: 14 },
  step:           { flexDirection: "row", alignItems: "center", gap: 14 },
  stepNum:        { width: 30, height: 30, borderRadius: 15, backgroundColor: "#F0FDF4", alignItems: "center", justifyContent: "center" },
  stepNumText:    { fontSize: 13, fontWeight: "700", color: "#1E7C45" },
  stepLabel:      { fontSize: 14, color: "#374151", fontWeight: "500" },
  primaryBtn:     { height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center", marginBottom: 10 },
  primaryBtnText: { fontSize: 16, fontWeight: "600", color: "#fff" },
  secondaryBtn:   { height: 52, borderRadius: 26, backgroundColor: "#fff", borderWidth: 1.5, borderColor: "#E5E7EB", alignItems: "center", justifyContent: "center" },
  secondaryBtnText:{ fontSize: 15, fontWeight: "500", color: "#374151" },
});
