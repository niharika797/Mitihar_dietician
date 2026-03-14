import React, { useState } from "react";
import {
  View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, ChevronRight, Droplets, Footprints } from "lucide-react-native";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { getTodaySummary, logWater, logSteps, logMeal } from "../../services/progress";
import { getWeeklyPlan } from "../../services/meals";
import { useAuthStore } from "../../store/useAuthStore";
import { useProgressStore, selectWater, selectSteps } from "../../store/useProgressStore";
import { ProgressRing, MacroRow, BottomSheet, useToast } from "../../components/shared";
import type { Meal } from "../../types";

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function todayKey() {
  return new Date().toISOString().slice(0, 10); // "YYYY-MM-DD"
}

const MEAL_SLOTS = [
  { id: "breakfast", emoji: "🌅", label: "Breakfast", time: "08:00 AM" },
  { id: "lunch",     emoji: "☀️",  label: "Lunch",     time: "01:00 PM" },
  { id: "dinner",    emoji: "🌙",  label: "Dinner",    time: "08:00 PM" },
];

export default function HomeScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const profile = useAuthStore(s => s.profile);
  const { hydrateSummary, setLocalWater, setLocalSteps } = useProgressStore();

  const [logSheet, setLogSheet] = useState<string | null>(null);
  const [waterSheet, setWaterSheet] = useState(false);
  const [stepsSheet, setStepsSheet] = useState(false);
  const [tempWater, setTempWater] = useState(0);
  const [tempSteps, setTempSteps] = useState("0");
  const [loggedMeals, setLoggedMeals] = useState<Record<string, boolean>>({});

  // ── Server data ──────────────────────────────────────────────────────────
  const { data: today, isLoading: todayLoading } = useQuery({
    queryKey: QUERY_KEYS.TODAY,
    queryFn: getTodaySummary,
    refetchInterval: 60_000,
  });

  React.useEffect(() => { if (today) hydrateSummary(today); }, [today]);

  const { data: plan } = useQuery({
    queryKey: QUERY_KEYS.WEEK_PLAN,
    queryFn: getWeeklyPlan,
    staleTime: 1000 * 60 * 10,
  });

  // Optimistic local overrides
  const water = useProgressStore(selectWater);
  const steps = useProgressStore(selectSteps);

  // Today's meals from plan (fallback: empty)
  const todayMeals: Meal[] = plan?.[todayKey()] ?? [];

  // ── Mutations ─────────────────────────────────────────────────────────────
  const waterMut = useMutation({
    mutationFn: (g: number) => logWater(g),
    onMutate: (g) => setLocalWater(g),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
      setWaterSheet(false);
      showToast("Water intake saved! 💧", "success");
    },
    onError: () => showToast("Failed to save water", "error"),
  });

  const stepsMut = useMutation({
    mutationFn: (s: number) => logSteps(s),
    onMutate: (s) => setLocalSteps(s),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
      setStepsSheet(false);
      showToast("Steps logged! 👟", "success");
    },
    onError: () => showToast("Failed to save steps", "error"),
  });

  const mealMut = useMutation({
    mutationFn: (meal: Meal) =>
      logMeal({
        meal_type: meal["Meal Type"].toLowerCase(),
        calories_consumed: meal["Total Calories"],
        protein_g: meal["Total Protein"],
        carbs_g:   meal["Total Carbs"],
        fat_g:     meal["Total Fat"],
        fiber_g:   meal["Total Fiber"],
      }),
    onSuccess: (_, meal) => {
      setLoggedMeals(p => ({ ...p, [meal["Meal Type"]]: true }));
      qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
      setLogSheet(null);
      showToast("Meal logged! 🎉", "success");
    },
    onError: () => showToast("Failed to log meal", "error"),
  });

  // ── Derived UI values ─────────────────────────────────────────────────────
  const dailyTarget = today?.tdee ? today.tdee - 400 : (profile ? 1850 : 1850);
  const cals         = today?.calories_consumed ?? 0;
  const calPercent   = Math.min(100, Math.round((cals / dailyTarget) * 100));
  const streak       = today?.streak ?? 0;
  const hasUnread    = true; // static badge — Phase 5 FCM will drive this

  const firstName = profile?.name?.split(" ")[0] ?? "there";

  if (todayLoading) {
    return (
      <View style={s.loader}>
        <ActivityIndicator size="large" color="#1E7C45" />
      </View>
    );
  }

  const selectedMeal = todayMeals.find(m => m["Meal Type"].toLowerCase() === logSheet?.toLowerCase());

  return (
    <View style={s.root}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>

        {/* ── Top header card ── */}
        <View style={s.headerCard}>
          <View style={s.headerRow}>
            <View>
              <Text style={s.greetingText}>{greeting()}, {firstName} ☀️</Text>
              <Text style={s.dateText}>{new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}</Text>
            </View>
            <Pressable onPress={() => router.push("/home/notifications")} style={s.bellBtn}>
              <Bell size={20} color="#374151" />
              {hasUnread && <View style={s.bellDot} />}
            </Pressable>
          </View>
          <View style={s.pillRow}>
            <View style={s.streakPill}>
              <Text style={s.streakEmoji}>🔥</Text>
              <Text style={s.streakText}>{streak} Day Streak</Text>
            </View>
          </View>
        </View>

        <View style={s.body}>
          {/* ── Calories ring ── */}
          <Text style={s.sectionLabel}>TODAY'S CALORIES</Text>
          <View style={s.card}>
            <View style={s.calorieRow}>
              <ProgressRing size={100} percentage={calPercent} color="#1E7C45" />
              <View style={s.calorieInfo}>
                <Text style={s.calBig}>{cals.toLocaleString()}</Text>
                <Text style={s.calSub}>of {dailyTarget.toLocaleString()} target</Text>
                <View style={{ marginTop: 8 }}>
                  <MacroRow
                    protein={0}
                    carbs={0}
                    fat={0}
                  />
                </View>
              </View>
            </View>
          </View>

          {/* ── Today's meals ── */}
          <View style={s.sectionHeader}>
            <Text style={s.sectionLabel}>TODAY'S MEALS</Text>
            <Pressable onPress={() => router.push("/(tabs)/meals")} style={s.seeAllBtn}>
              <Text style={s.seeAllText}>See All</Text>
              <ChevronRight size={14} color="#1E7C45" />
            </Pressable>
          </View>
          <View style={[s.card, { padding: 0, overflow: "hidden" }]}>
            {MEAL_SLOTS.map((slot, i) => {
              const meal = todayMeals.find(m =>
                m["Meal Type"].toLowerCase().includes(slot.id)
              );
              const logged = loggedMeals[slot.label] ?? false;
              return (
                <View key={slot.id} style={[s.mealRow, i < MEAL_SLOTS.length - 1 && s.mealBorder, logged && s.mealLogged]}>
                  <View style={s.mealLeft}>
                    <Text style={s.mealCheck}>{logged ? "✓" : "○"}</Text>
                    <View>
                      <Text style={s.mealSlot}>{slot.emoji} {slot.label} · {slot.time}</Text>
                      <Text style={s.mealName} numberOfLines={1}>
                        {meal ? meal["Menu Names"] : "—"}
                      </Text>
                    </View>
                  </View>
                  <View style={s.mealRight}>
                    {meal && <Text style={s.mealCal}>{meal["Total Calories"]} cal</Text>}
                    {!logged && meal && (
                      <Pressable onPress={() => setLogSheet(slot.label)} style={s.logBtn}>
                        <Text style={s.logBtnText}>Log</Text>
                      </Pressable>
                    )}
                  </View>
                </View>
              );
            })}
          </View>

          {/* ── Quick log ── */}
          <Text style={s.sectionLabel}>QUICK LOG</Text>
          <View style={s.quickGrid}>
            <Pressable style={s.quickCard} onPress={() => { setTempWater(water); setWaterSheet(true); }}>
              <Droplets size={22} color="#2563EB" />
              <Text style={s.quickVal}>{water} / 8</Text>
              <Text style={s.quickSub}>glasses today</Text>
            </Pressable>
            <Pressable style={s.quickCard} onPress={() => { setTempSteps(steps.toString()); setStepsSheet(true); }}>
              <Footprints size={22} color="#1E7C45" />
              <Text style={s.quickVal}>{steps.toLocaleString()}</Text>
              <Text style={s.quickSub}>steps today</Text>
            </Pressable>
          </View>

          {/* ── Doctor note ── */}
          {profile?.doctor_id && (
            <Pressable style={s.doctorBanner} onPress={() => router.push("/doctor/connection-status")}>
              <View style={{ flex: 1 }}>
                <Text style={s.doctorLabel}>📋 Doctor connected</Text>
                <Text style={s.doctorSub}>Tap to view your plan details</Text>
              </View>
              <Text style={s.doctorLink}>View</Text>
            </Pressable>
          )}
        </View>
      </ScrollView>

      {/* ── Log Meal Sheet ── */}
      <BottomSheet open={!!logSheet} onClose={() => setLogSheet(null)}>
        <View style={sh.gap}>
          <Text style={sh.title}>Log {logSheet}</Text>
          {selectedMeal ? (
            <View style={sh.confirm}>
              <Text style={sh.confirmText}>
                {selectedMeal["Menu Names"]} — {selectedMeal["Total Calories"]} cal
              </Text>
            </View>
          ) : (
            <Text style={{ color: "#6B7280", fontSize: 13 }}>No meal planned for this slot today.</Text>
          )}
          {selectedMeal && (
            <Pressable
              style={sh.cta}
              onPress={() => mealMut.mutate(selectedMeal)}
              disabled={mealMut.isPending}
            >
              {mealMut.isPending
                ? <ActivityIndicator color="#fff" />
                : <Text style={sh.ctaText}>✅ Confirm & Log</Text>}
            </Pressable>
          )}
        </View>
      </BottomSheet>

      {/* ── Water Sheet ── */}
      <BottomSheet open={waterSheet} onClose={() => setWaterSheet(false)}>
        <View style={[sh.gap, { alignItems: "center" }]}>
          <Text style={[sh.title, { alignSelf: "flex-start" }]}>Log Water Intake</Text>
          <Text style={{ fontSize: 14, color: "#374151" }}>How many glasses today?</Text>
          <View style={sh.counter}>
            <Pressable onPress={() => setTempWater(Math.max(0, tempWater - 1))} style={sh.counterBtn}>
              <Text style={sh.counterBtnText}>−</Text>
            </Pressable>
            <Text style={sh.counterVal}>{tempWater}</Text>
            <Pressable onPress={() => setTempWater(Math.min(20, tempWater + 1))} style={sh.counterBtn}>
              <Text style={sh.counterBtnText}>+</Text>
            </Pressable>
          </View>
          <View style={sh.dropRow}>
            {Array.from({ length: 8 }, (_, i) => (
              <Droplets key={i} size={20} color={i < tempWater ? "#2563EB" : "#E5E7EB"} />
            ))}
          </View>
          <Pressable style={sh.cta} onPress={() => waterMut.mutate(tempWater)} disabled={waterMut.isPending}>
            {waterMut.isPending ? <ActivityIndicator color="#fff" /> : <Text style={sh.ctaText}>Save</Text>}
          </Pressable>
        </View>
      </BottomSheet>

      {/* ── Steps Sheet ── */}
      <BottomSheet open={stepsSheet} onClose={() => setStepsSheet(false)}>
        <View style={sh.gap}>
          <Text style={sh.title}>Log Steps Today</Text>
          <View style={{ alignItems: "center" }}>
            <Text
              style={sh.stepsInput}
              onPress={() => {}}
            >
              {tempSteps}
            </Text>
          </View>
          <View style={sh.stepsBtnRow}>
            {[1000, 2000, 5000, 8000].map(v => (
              <Pressable key={v} onPress={() => setTempSteps(v.toString())} style={sh.stepPreset}>
                <Text style={sh.stepPresetText}>{v.toLocaleString()}</Text>
              </Pressable>
            ))}
          </View>
          <Pressable style={sh.cta} onPress={() => stepsMut.mutate(parseInt(tempSteps) || 0)} disabled={stepsMut.isPending}>
            {stepsMut.isPending ? <ActivityIndicator color="#fff" /> : <Text style={sh.ctaText}>Save</Text>}
          </Pressable>
        </View>
      </BottomSheet>
    </View>
  );
}

const s = StyleSheet.create({
  root:        { flex: 1, backgroundColor: "#F9FAFB" },
  loader:      { flex: 1, alignItems: "center", justifyContent: "center" },
  scroll:      { paddingBottom: 32 },
  headerCard:  { backgroundColor: "#fff", padding: 16, paddingTop: 20, shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.04, shadowRadius: 6, elevation: 2 },
  headerRow:   { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" },
  greetingText:{ fontSize: 20, fontWeight: "600", color: "#111827" },
  dateText:    { fontSize: 13, color: "#6B7280", marginTop: 2 },
  bellBtn:     { width: 40, height: 40, borderRadius: 20, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  bellDot:     { position: "absolute", top: 8, right: 8, width: 8, height: 8, borderRadius: 4, backgroundColor: "#DC2626", borderWidth: 2, borderColor: "#fff" },
  pillRow:     { flexDirection: "row", gap: 8, marginTop: 12 },
  streakPill:  { flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: "#FFFBEB", borderRadius: 99, paddingHorizontal: 14, paddingVertical: 6 },
  streakEmoji: { fontSize: 16 },
  streakText:  { fontSize: 14, fontWeight: "600", color: "#92400E" },
  body:        { paddingHorizontal: 20, paddingTop: 20 },
  sectionLabel:{ fontSize: 11, fontWeight: "600", color: "#374151", letterSpacing: 1, marginBottom: 10 },
  sectionHeader:{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 10 },
  seeAllBtn:   { flexDirection: "row", alignItems: "center", gap: 2 },
  seeAllText:  { fontSize: 12, fontWeight: "500", color: "#1E7C45" },
  card:        { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 16, marginBottom: 20 },
  calorieRow:  { flexDirection: "row", alignItems: "center", gap: 20 },
  calorieInfo: { flex: 1 },
  calBig:      { fontSize: 28, fontWeight: "700", color: "#111827" },
  calSub:      { fontSize: 12, color: "#6B7280" },
  mealRow:     { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 16, paddingVertical: 12 },
  mealBorder:  { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  mealLogged:  { backgroundColor: "#F0FDF4" },
  mealLeft:    { flexDirection: "row", alignItems: "center", gap: 8, flex: 1 },
  mealCheck:   { fontSize: 16, color: "#34B164", width: 20 },
  mealSlot:    { fontSize: 11, color: "#9CA3AF" },
  mealName:    { fontSize: 14, fontWeight: "500", color: "#111827", maxWidth: 180 },
  mealRight:   { flexDirection: "row", alignItems: "center", gap: 8 },
  mealCal:     { fontSize: 14, fontWeight: "600", color: "#1E7C45" },
  logBtn:      { height: 30, paddingHorizontal: 12, borderRadius: 99, borderWidth: 1.5, borderColor: "#1E7C45", backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  logBtnText:  { fontSize: 12, fontWeight: "500", color: "#1E7C45" },
  quickGrid:   { flexDirection: "row", gap: 12, marginBottom: 20 },
  quickCard:   { flex: 1, backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 14 },
  quickVal:    { fontSize: 16, fontWeight: "700", color: "#111827", marginTop: 6 },
  quickSub:    { fontSize: 11, color: "#6B7280" },
  doctorBanner:{ flexDirection: "row", alignItems: "center", backgroundColor: "#F0FDF4", borderWidth: 1, borderColor: "#DCFCE7", borderRadius: 12, padding: 14, marginBottom: 8 },
  doctorLabel: { fontSize: 12, fontWeight: "500", color: "#166534" },
  doctorSub:   { fontSize: 12, color: "#374151", marginTop: 2 },
  doctorLink:  { fontSize: 12, fontWeight: "500", color: "#1E7C45" },
});

const sh = StyleSheet.create({
  gap:           { gap: 16 },
  title:         { fontSize: 18, fontWeight: "600", color: "#111827" },
  confirm:       { backgroundColor: "#F0FDF4", borderRadius: 8, padding: 12 },
  confirmText:   { fontSize: 12, color: "#166534" },
  cta:           { height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  ctaText:       { fontSize: 16, fontWeight: "600", color: "#fff" },
  counter:       { flexDirection: "row", alignItems: "center", gap: 24 },
  counterBtn:    { width: 48, height: 48, borderRadius: 24, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  counterBtnText:{ fontSize: 24, color: "#fff", lineHeight: 28 },
  counterVal:    { fontSize: 40, fontWeight: "700", color: "#111827", minWidth: 40, textAlign: "center" },
  dropRow:       { flexDirection: "row", gap: 6 },
  stepsInput:    { fontSize: 40, fontWeight: "700", color: "#111827", borderWidth: 1.5, borderColor: "#1E7C45", borderRadius: 12, paddingHorizontal: 24, paddingVertical: 12, minWidth: 160, textAlign: "center" },
  stepsBtnRow:   { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  stepPreset:    { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 99, borderWidth: 1, borderColor: "#E5E7EB", backgroundColor: "#F9FAFB" },
  stepPresetText:{ fontSize: 13, color: "#374151", fontWeight: "500" },
});
