import React, { useState } from "react";
import {
  View, Text, TextInput, ScrollView, Pressable, StyleSheet, ActivityIndicator,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { logMeal } from "../../services/progress";
import { getWeeklyPlan } from "../../services/meals";
import { useToast } from "../../components/shared";
import { QUERY_KEYS } from "../../lib/queryKeys";
import type { WeeklyPlan } from "../../types";

export default function LogFromPlanScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { date, type } = useLocalSearchParams<{ date: string; type: string }>();

  const { data: plan } = useQuery({ queryKey: QUERY_KEYS.WEEK_PLAN, queryFn: getWeeklyPlan });
  const meal = (plan as WeeklyPlan | undefined)?.[date ?? ""]?.find(m => m["Meal Type"] === type);

  const [calories, setCalories] = useState(String(Math.round(meal?.["Total Calories"] ?? 0)));
  const [protein,  setProtein]  = useState(String(Math.round(meal?.["Total Protein"]  ?? 0)));
  const [carbs,    setCarbs]    = useState(String(Math.round(meal?.["Total Carbs"]    ?? 0)));
  const [fat,      setFat]      = useState(String(Math.round(meal?.["Total Fat"]      ?? 0)));
  const [fiber,    setFiber]    = useState(String(Math.round(meal?.["Total Fiber"]    ?? 0)));
  const [notes,    setNotes]    = useState("");

  const saveMut = useMutation({
    mutationFn: () => logMeal({
      meal_type: (type ?? "Lunch"),
      calories:  parseFloat(calories) || 0,
      protein:   parseFloat(protein)  || undefined,
      carbs:     parseFloat(carbs)    || undefined,
      fat:       parseFloat(fat)      || undefined,
      fiber:     parseFloat(fiber)    || undefined,
      notes:             notes || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
      showToast("Meal logged! 🎉", "success");
      router.back();
    },
    onError: () => showToast("Failed to log meal", "error"),
  });

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Log from Plan</Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>
        {/* Pre-filled banner */}
        {meal && (
          <View style={s.banner}>
            <Text style={s.bannerSub}>Logging as recommended:</Text>
            <Text style={s.bannerTitle} numberOfLines={2}>{meal["Menu Names"]}</Text>
          </View>
        )}

        <View style={s.field}>
          <Text style={s.label}>Calories Consumed (kcal)</Text>
          <View style={s.unitWrap}>
            <TextInput style={[s.input, { paddingRight: 50 }]} value={calories}
              onChangeText={setCalories} keyboardType="decimal-pad" placeholderTextColor="#9CA3AF" />
            <Text style={s.unit}>kcal</Text>
          </View>
        </View>

        <View style={s.field}>
          <Text style={s.label}>Macros</Text>
          <View style={s.macroRow}>
            {[
              { l: "Protein (g)", v: protein, s: setProtein },
              { l: "Carbs (g)",   v: carbs,   s: setCarbs   },
              { l: "Fat (g)",     v: fat,     s: setFat     },
              { l: "Fiber (g)",   v: fiber,   s: setFiber   },
            ].map(m => (
              <View key={m.l} style={s.macroField}>
                <Text style={s.macroLabel}>{m.l}</Text>
                <TextInput style={s.macroInput} value={m.v} onChangeText={m.s}
                  keyboardType="decimal-pad" placeholderTextColor="#9CA3AF" />
              </View>
            ))}
          </View>
        </View>

        <View style={s.field}>
          <Text style={s.label}>Notes (optional)</Text>
          <TextInput style={s.input} value={notes} onChangeText={setNotes}
            placeholder="Any adjustments?" placeholderTextColor="#9CA3AF" />
        </View>

        <Pressable style={s.saveBtn} onPress={() => saveMut.mutate()} disabled={saveMut.isPending}>
          {saveMut.isPending
            ? <ActivityIndicator color="#fff" />
            : <Text style={s.saveBtnText}>Save Meal Log</Text>}
        </Pressable>

        <Pressable style={s.altBtn} onPress={() => router.push("/log/log-meal")}>
          <Text style={s.altBtnText}>Had something different?</Text>
        </Pressable>
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root:       { flex: 1, backgroundColor: "#F9FAFB" },
  header:     { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:    { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:      { fontSize: 18, fontWeight: "600", color: "#111827" },
  scroll:     { padding: 20, gap: 16 },
  banner:     { backgroundColor: "#F0FDF4", borderRadius: 10, borderWidth: 1, borderColor: "#DCFCE7", padding: 14, gap: 4 },
  bannerSub:  { fontSize: 12, color: "#166534" },
  bannerTitle:{ fontSize: 14, fontWeight: "600", color: "#111827" },
  field:      { gap: 6 },
  label:      { fontSize: 14, fontWeight: "500", color: "#374151" },
  input:      { height: 52, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", paddingHorizontal: 16, fontSize: 14, color: "#111827", backgroundColor: "#fff" },
  unitWrap:   { position: "relative" },
  unit:       { position: "absolute", right: 14, top: 16, fontSize: 13, color: "#6B7280" },
  macroRow:   { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  macroField: { flex: 1, minWidth: "44%", gap: 4 },
  macroLabel: { fontSize: 11, color: "#6B7280" },
  macroInput: { height: 44, borderRadius: 8, borderWidth: 1.5, borderColor: "#E5E7EB", paddingHorizontal: 12, fontSize: 14, color: "#111827", backgroundColor: "#fff" },
  saveBtn:    { height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  saveBtnText:{ fontSize: 16, fontWeight: "600", color: "#fff" },
  altBtn:     { alignItems: "center", paddingVertical: 4 },
  altBtnText: { fontSize: 14, fontWeight: "500", color: "#1E7C45" },
});
