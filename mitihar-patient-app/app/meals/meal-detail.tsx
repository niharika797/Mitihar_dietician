import React, { useState } from "react";
import {
  View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { getWeeklyPlan } from "../../services/meals";
import { logMeal } from "../../services/progress";
import { MacroRow, useToast } from "../../components/shared";
import type { Meal } from "../../types";

export default function MealDetailScreen() {
  const router = useRouter();
  const { date, type } = useLocalSearchParams<{ date: string; type: string }>();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [logged, setLogged] = useState(false);

  const { data: plan, isLoading } = useQuery({
    queryKey: QUERY_KEYS.WEEK_PLAN,
    queryFn: getWeeklyPlan,
  });

  const meal: Meal | undefined = plan?.[date ?? ""]?.find(m => m["Meal Type"] === type);

  const logMut = useMutation({
    mutationFn: () => logMeal({
      meal_type: meal!["Meal Type"].toLowerCase(),
      calories_consumed: meal!["Total Calories"],
      protein_g: meal!["Total Protein"],
      carbs_g:   meal!["Total Carbs"],
      fat_g:     meal!["Total Fat"],
      fiber_g:   meal!["Total Fiber"],
    }),
    onSuccess: () => {
      setLogged(true);
      qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
      showToast("Meal logged! 🎉", "success");
    },
    onError: () => showToast("Failed to log meal", "error"),
  });

  if (isLoading) return <View style={s.loader}><ActivityIndicator size="large" color="#1E7C45" /></View>;
  if (!meal)    return (
    <View style={s.loader}>
      <Text style={{ color: "#6B7280" }}>Meal not found</Text>
      <Pressable onPress={() => router.back()} style={s.backBtnSm}><Text style={{ color: "#1E7C45" }}>← Go back</Text></Pressable>
    </View>
  );

  const mealAny = meal as any;
  const items: string[] = mealAny["Items"] ? JSON.parse(mealAny["Items"]) : [];
  const macros = [
    { label: "Calories",  value: meal["Total Calories"] },
    { label: "Protein",   value: `${Math.round(meal["Total Protein"])}g` },
    { label: "Carbs",     value: `${Math.round(meal["Total Carbs"])}g` },
    { label: "Fat",       value: `${Math.round(meal["Total Fat"])}g` },
  ];

  return (
    <View style={s.root}>
      {/* Floating header */}
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.headerTitle} numberOfLines={1}>{meal["Meal Type"]}</Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>
        {/* Meal type badge */}
        <View style={s.badge}>
          <Text style={s.badgeText}>{meal["Meal Type"].toUpperCase()}</Text>
        </View>

        {/* Name */}
        <Text style={s.mealName}>{meal["Menu Names"]}</Text>

        {/* Tags */}
        <View style={s.tagRow}>
          {["🥗 Vegetarian", "🇮🇳 Indian"].map(t => (
            <View key={t} style={s.tag}><Text style={s.tagText}>{t}</Text></View>
          ))}
        </View>

        {/* Macros grid */}
        <Text style={s.sectionLabel}>NUTRITION PER SERVING</Text>
        <View style={s.macroGrid}>
          {macros.map(m => (
            <View key={m.label} style={s.macroCard}>
              <Text style={s.macroVal}>{m.value}</Text>
              <Text style={s.macroLabel}>{m.label}</Text>
            </View>
          ))}
        </View>

        {/* Full macro pills */}
        <View style={s.pillRow}>
          <MacroRow
            protein={Math.round(meal["Total Protein"])}
            carbs={Math.round(meal["Total Carbs"])}
            fat={Math.round(meal["Total Fat"])}
            fiber={Math.round(meal["Total Fiber"])}
          />
        </View>

        {/* Ingredients */}
        {items.length > 0 && (
          <>
            <Text style={s.sectionLabel}>INGREDIENTS</Text>
            <View style={s.listCard}>
              {items.map((item, i) => (
                <View key={i} style={[s.listRow, i < items.length - 1 && s.listBorder]}>
                  <Text style={s.listBullet}>•</Text>
                  <Text style={s.listText}>{item}</Text>
                </View>
              ))}
            </View>
          </>
        )}

        {/* Doctor note */}
        {meal.doctor_note && (
          <>
            <Text style={s.sectionLabel}>DOCTOR'S NOTE</Text>
            <View style={s.noteCard}>
              <Text style={s.noteLabel}>📝 Your doctor said:</Text>
              <Text style={s.noteText}>"{meal.doctor_note}"</Text>
            </View>
          </>
        )}
      </ScrollView>

      {/* Bottom CTA */}
      <View style={s.footer}>
        {logged ? (
          <View style={s.loggedBanner}>
            <Text style={s.loggedText}>✅ Logged</Text>
          </View>
        ) : (
          <View style={s.footerRow}>
            <Pressable style={s.primaryBtn} onPress={() => logMut.mutate()} disabled={logMut.isPending}>
              {logMut.isPending ? <ActivityIndicator color="#fff" /> : <Text style={s.primaryBtnText}>✅ I Had This</Text>}
            </Pressable>
          </View>
        )}
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  root:        { flex: 1, backgroundColor: "#fff" },
  loader:      { flex: 1, alignItems: "center", justifyContent: "center", gap: 12 },
  backBtnSm:   { marginTop: 8 },
  header:      { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  backBtn:     { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  headerTitle: { fontSize: 16, fontWeight: "600", color: "#111827", flex: 1, textAlign: "center" },
  scroll:      { padding: 20, paddingBottom: 100 },
  badge:       { alignSelf: "flex-start", backgroundColor: "#F0FDF4", borderRadius: 99, paddingHorizontal: 10, paddingVertical: 4, marginBottom: 8 },
  badgeText:   { fontSize: 10, fontWeight: "700", color: "#1E7C45", letterSpacing: 0.5 },
  mealName:    { fontSize: 22, fontWeight: "700", color: "#111827", marginBottom: 12 },
  tagRow:      { flexDirection: "row", gap: 8, marginBottom: 20 },
  tag:         { backgroundColor: "#F3F4F6", borderRadius: 99, paddingHorizontal: 12, paddingVertical: 4 },
  tagText:     { fontSize: 12, color: "#374151" },
  sectionLabel:{ fontSize: 11, fontWeight: "600", color: "#374151", letterSpacing: 1, marginBottom: 10, marginTop: 4 },
  macroGrid:   { flexDirection: "row", gap: 8, marginBottom: 12 },
  macroCard:   { flex: 1, backgroundColor: "#F9FAFB", borderRadius: 10, padding: 10, alignItems: "center", borderWidth: 1, borderColor: "#E5E7EB" },
  macroVal:    { fontSize: 16, fontWeight: "700", color: "#111827" },
  macroLabel:  { fontSize: 10, color: "#6B7280", marginTop: 2 },
  pillRow:     { marginBottom: 20 },
  listCard:    { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 16, marginBottom: 20 },
  listRow:     { flexDirection: "row", gap: 8, paddingVertical: 6 },
  listBorder:  { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  listBullet:  { color: "#9CA3AF", fontSize: 14 },
  listText:    { flex: 1, fontSize: 14, color: "#374151" },
  noteCard:    { backgroundColor: "#F0FDF4", borderRadius: 12, borderWidth: 1, borderColor: "#DCFCE7", padding: 14, marginBottom: 20 },
  noteLabel:   { fontSize: 12, fontWeight: "600", color: "#166534", marginBottom: 4 },
  noteText:    { fontSize: 13, color: "#374151", lineHeight: 20, fontStyle: "italic" },
  footer:      { padding: 16, paddingBottom: 28, borderTopWidth: 1, borderTopColor: "#F3F4F6", backgroundColor: "#fff" },
  footerRow:   { flexDirection: "row", gap: 12 },
  primaryBtn:  { flex: 1, height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  primaryBtnText:{ fontSize: 16, fontWeight: "600", color: "#fff" },
  loggedBanner:{ height: 52, borderRadius: 26, backgroundColor: "#F0FDF4", alignItems: "center", justifyContent: "center" },
  loggedText:  { fontSize: 16, fontWeight: "600", color: "#166534" },
});
