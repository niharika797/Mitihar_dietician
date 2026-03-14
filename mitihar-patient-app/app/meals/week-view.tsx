import React, { useState } from "react";
import { View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import { useQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { getWeeklyPlan } from "../../services/meals";
import { MacroRow } from "../../components/shared";
import type { Meal } from "../../types";

const DAY_LABELS = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
const MEAL_ORDER = ["Breakfast","Morning Snack","Lunch","Evening Snack","Dinner"];

function getWeekDates(): Date[] {
  const today = new Date();
  const day = today.getDay(); // 0=Sun
  const monday = new Date(today);
  monday.setDate(today.getDate() - ((day + 6) % 7));
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return d;
  });
}

export default function WeekViewScreen() {
  const router = useRouter();
  const weekDates = getWeekDates();
  const todayIdx = (new Date().getDay() + 6) % 7; // Mon=0
  const [selectedIdx, setSelectedIdx] = useState(todayIdx);

  const { data: plan, isLoading } = useQuery({
    queryKey: QUERY_KEYS.WEEK_PLAN,
    queryFn: getWeeklyPlan,
    staleTime: 1000 * 60 * 10,
  });

  const selectedDate = weekDates[selectedIdx].toISOString().slice(0, 10);
  const dayMeals: Meal[] = plan?.[selectedDate] ?? [];
  const ordered = MEAL_ORDER
    .map(t => dayMeals.find(m => m["Meal Type"] === t))
    .filter((m): m is Meal => !!m);

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Week View</Text>
        <View style={{ width: 36 }} />
      </View>

      {/* Day selector */}
      <View style={s.dayBar}>
        {weekDates.map((date, i) => {
          const sel = selectedIdx === i;
          const hasPlan = plan?.[date.toISOString().slice(0, 10)]?.length ?? 0;
          return (
            <Pressable key={i} onPress={() => setSelectedIdx(i)} style={s.dayBtn}>
              <Text style={s.dayLabel}>{DAY_LABELS[(i + 1) % 7]}</Text>
              <View style={[s.dayCircle, sel && s.dayCircleSel]}>
                <Text style={[s.dayNum, sel && s.dayNumSel]}>{date.getDate()}</Text>
              </View>
              {hasPlan > 0 && <View style={[s.dasDot, sel && s.dasDotSel]} />}
            </Pressable>
          );
        })}
      </View>

      {/* Meal cards for selected day */}
      {isLoading ? (
        <View style={{ flex: 1, alignItems: "center", justifyContent: "center", paddingTop: 60 }}>
          <ActivityIndicator size="large" color="#1E7C45" />
        </View>
      ) : ordered.length === 0 ? (
        <View style={s.empty}>
          <Text style={s.emptyEmoji}>🥗</Text>
          <Text style={s.emptyTitle}>No meals planned</Text>
          <Text style={s.emptySub}>Your doctor hasn't assigned meals for this day yet.</Text>
        </View>
      ) : (
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>
          {ordered.map((meal, idx) => (
            <Pressable
              key={idx}
              style={s.card}
              onPress={() => router.push({ pathname: "/meals/meal-detail", params: { date: selectedDate, type: meal["Meal Type"] } })}
            >
              <View style={s.cardTop}>
                <View style={s.mealTypeBadge}>
                  <Text style={s.mealTypeText}>{meal["Meal Type"]}</Text>
                </View>
                <Text style={s.dietTag}>{meal["Diet Type"]}</Text>
              </View>
              <Text style={s.menuName} numberOfLines={2}>{meal["Menu Names"]}</Text>
              <MacroRow
                protein={meal["Total Protein"]}
                carbs={meal["Total Carbs"]}
                fat={meal["Total Fat"]}
                fiber={meal["Total Fiber"]}
              />
              {meal.doctor_note ? (
                <View style={s.noteWrap}>
                  <Text style={s.noteText}>📝 {meal.doctor_note}</Text>
                </View>
              ) : null}
            </Pressable>
          ))}
        </ScrollView>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  root:          { flex: 1, backgroundColor: "#F9FAFB" },
  header:        { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:       { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:         { fontSize: 18, fontWeight: "600", color: "#111827" },
  dayBar:        { flexDirection: "row", justifyContent: "space-between", backgroundColor: "#fff", paddingHorizontal: 12, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  dayBtn:        { alignItems: "center", gap: 4, flex: 1 },
  dayLabel:      { fontSize: 11, color: "#9CA3AF", fontWeight: "500" },
  dayCircle:     { width: 32, height: 32, borderRadius: 16, alignItems: "center", justifyContent: "center" },
  dayCircleSel:  { backgroundColor: "#1E7C45" },
  dayNum:        { fontSize: 14, fontWeight: "600", color: "#374151" },
  dayNumSel:     { color: "#fff" },
  dasDot:        { width: 4, height: 4, borderRadius: 2, backgroundColor: "#D1D5DB" },
  dasDotSel:     { backgroundColor: "#34B164" },
  scroll:        { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 32, gap: 10 },
  card:          { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 14, gap: 8 },
  cardTop:       { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  mealTypeBadge: { backgroundColor: "#F0FDF4", borderRadius: 99, paddingHorizontal: 10, paddingVertical: 3 },
  mealTypeText:  { fontSize: 11, fontWeight: "600", color: "#166534" },
  dietTag:       { fontSize: 11, color: "#6B7280" },
  menuName:      { fontSize: 15, fontWeight: "600", color: "#111827", lineHeight: 20 },
  noteWrap:      { backgroundColor: "#F0FDF4", borderRadius: 8, padding: 10 },
  noteText:      { fontSize: 12, color: "#374151", lineHeight: 18 },
  empty:         { alignItems: "center", paddingTop: 60, paddingHorizontal: 32 },
  emptyEmoji:    { fontSize: 48, marginBottom: 12 },
  emptyTitle:    { fontSize: 18, fontWeight: "600", color: "#111827", marginBottom: 8 },
  emptySub:      { fontSize: 14, color: "#6B7280", textAlign: "center", lineHeight: 20 },
});
