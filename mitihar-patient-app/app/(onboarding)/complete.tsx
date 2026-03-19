import React, { useEffect } from "react";
import { View, Text, Pressable, StyleSheet, ScrollView } from "react-native";
import { useRouter } from "expo-router";
import Svg, { Path } from "react-native-svg";
import { useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "../../store/useAuthStore";
import { computeHealthStats } from "../../utils/calculations";
import { generatePlan } from "../../services/meals";
import { QUERY_KEYS } from "../../lib/queryKeys";

function CheckCircle() {
  return (
    <View style={s.successIcon}>
      <Svg width={40} height={32} viewBox="0 0 40 32" fill="none">
        <Path d="M3 16L14 27L37 4" stroke="#1E7C45" strokeWidth={4} strokeLinecap="round" strokeLinejoin="round" />
      </Svg>
    </View>
  );
}

export default function CompleteScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const profile = useAuthStore(s => s.profile);

  // Ensure a diet plan exists — re-trigger generation if onboarding
  // completed but the backend silent-failed during plan auto-gen.
  useEffect(() => {
    generatePlan()
      .then(() => qc.invalidateQueries({ queryKey: QUERY_KEYS.WEEK_PLAN }))
      .catch(() => {}); // soft-fail — user can retry from Meals tab
  }, []);

  // Compute stats from stored profile or show fallback zeroes
  const stats = profile
    ? computeHealthStats({
        weight_kg:       profile.weight_kg,
        height_cm:       profile.height_cm,
        date_of_birth:   profile.date_of_birth ?? "1993-01-01",
        gender:          profile.gender,
        activity_level:  profile.activity_level,
        pace_preference: profile.pace_preference,
      })
    : null;

  const paceLabel: Record<string, string> = {
    slow_and_steady: "for slow & steady pace",
    moderate:        "for moderate pace",
    fast:            "for fast pace",
  };
  const paceNote = paceLabel[profile?.pace_preference ?? "moderate"] ?? "for moderate pace";

  const rows = stats
    ? [
        { label: "BMI",                 value: `${stats.bmi}`,                       note: stats.bmiCategory, highlight: false },
        { label: "BMR (Base Rate)",     value: `${stats.bmr.toLocaleString()} kcal`, note: "",                highlight: false },
        { label: "TDEE (with activity)", value: `${stats.tdee.toLocaleString()} kcal`, note: "",             highlight: false },
        { label: "Daily Target",        value: `${stats.dailyTarget.toLocaleString()} kcal`, note: paceNote, highlight: true },
      ]
    : [];

  return (
    <ScrollView style={s.root} contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
      {/* Success icon */}
      <View style={s.center}>
        <CheckCircle />
        <Text style={s.heading}>Your Profile is Ready! 🎉</Text>
        <Text style={s.sub}>Here's what we calculated for you</Text>
      </View>

      {/* Stats card */}
      {rows.length > 0 && (
        <View style={s.card}>
          {rows.map((row, i) => (
            <View
              key={row.label}
              style={[s.row, row.highlight && s.rowHighlight, i < rows.length - 1 && s.rowBorder]}
            >
              <View>
                <Text style={s.rowLabel}>{row.label}</Text>
                {row.note ? <Text style={s.rowNote}>{row.note}</Text> : null}
              </View>
              <Text style={[s.rowValue, row.highlight && s.rowValueHighlight]}>{row.value}</Text>
            </View>
          ))}
        </View>
      )}

      <Pressable style={s.cta} onPress={() => router.replace("/(tabs)")}>
        <Text style={s.ctaText}>View My Meal Plan</Text>
      </Pressable>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root:               { flex: 1, backgroundColor: "#fff" },
  scroll:             { alignItems: "center", padding: 24, paddingTop: 48 },
  center:             { alignItems: "center", marginBottom: 28 },
  successIcon:        { width: 80, height: 80, borderRadius: 40, backgroundColor: "#F0FDF4", borderWidth: 3, borderColor: "#34B164", alignItems: "center", justifyContent: "center", marginBottom: 20 },
  heading:            { fontSize: 24, fontWeight: "700", color: "#1E7C45", marginBottom: 6, textAlign: "center" },
  sub:                { fontSize: 14, color: "#6B7280", textAlign: "center" },
  card:               { width: "100%", borderWidth: 1, borderColor: "#E5E7EB", borderRadius: 12, overflow: "hidden", marginBottom: 32 },
  row:                { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 14, backgroundColor: "#fff" },
  rowHighlight:       { backgroundColor: "#F0FDF4" },
  rowBorder:          { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  rowLabel:           { fontSize: 14, color: "#374151" },
  rowNote:            { fontSize: 11, color: "#6B7280", marginTop: 2 },
  rowValue:           { fontSize: 18, fontWeight: "700", color: "#111827" },
  rowValueHighlight:  { color: "#1E7C45" },
  cta:                { width: "100%", height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  ctaText:            { fontSize: 16, fontWeight: "600", color: "#fff" },
});
