import React from "react";
import { View, Text, StyleSheet, ActivityIndicator } from "react-native";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { Pressable, ScrollView } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useAuthStore } from "../../store/useAuthStore";
import { generatePlan } from "../../services/meals";
import { useToast } from "../../components/shared";
import { ChevronRight } from "lucide-react-native";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { getWeeklyPlan } from "../../services/meals";
import { MacroRow } from "../../components/shared";
import type { Meal } from "../../types";

const MEAL_ORDER = ["Breakfast", "Lunch", "Dinner"];

const TEASER_MEALS: Meal[] = [
  { Date: "", "Meal Type": "Breakfast", "Menu Names": "Oats Upma + Moong Dal Cheela",         "Diet Type": "Vegetarian", "Total Calories": 395, "Total Protein": 18, "Total Carbs": 58, "Total Fat": 8,  "Total Fiber": 6 },
  { Date: "", "Meal Type": "Lunch",     "Menu Names": "Dal Tadka + 2 Rotis + Cucumber Raita", "Diet Type": "Vegetarian", "Total Calories": 520, "Total Protein": 22, "Total Carbs": 68, "Total Fat": 14, "Total Fiber": 8 },
  { Date: "", "Meal Type": "Dinner",    "Menu Names": "Palak Paneer + 1 Roti + Salad",         "Diet Type": "Vegetarian", "Total Calories": 410, "Total Protein": 20, "Total Carbs": 38, "Total Fat": 16, "Total Fiber": 6 },
];

function todayKey() { return new Date().toISOString().slice(0, 10); }

function MealCard({ meal }: { meal: Meal }) {
  return (
    <View style={s.mealCard}>
      <View style={s.mealHeader}>
        <Text style={s.mealType}>{meal["Meal Type"]}</Text>
        <Text style={s.mealCal}>{meal["Total Calories"]} cal</Text>
      </View>
      <Text style={s.mealName} numberOfLines={2}>{meal["Menu Names"]}</Text>
      <View style={{ marginTop: 8 }}>
        <MacroRow
          protein={Math.round(meal["Total Protein"])}
          carbs={Math.round(meal["Total Carbs"])}
          fat={Math.round(meal["Total Fat"])}
          fiber={Math.round(meal["Total Fiber"])}
        />
      </View>
    </View>
  );
}

function TeaserView({ onFindDoctor }: { onFindDoctor: () => void }) {
  return (
    <ScrollView style={s.root} contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
      <View style={s.header}>
        <Text style={s.headerTitle}>Meal Plan</Text>
        <View style={s.weekBtnDisabled}>
          <Text style={s.weekBtnTextDisabled}>Sample Preview</Text>
        </View>
      </View>

      <View style={s.body}>
        <Text style={s.dateLabel}>
          {new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}
        </Text>

        {/* Meal cards — clipped to show top portion */}
        <View style={s.teaserContainer}>
          {TEASER_MEALS.map((meal) => (
            <MealCard key={meal["Meal Type"]} meal={meal} />
          ))}

          {/* Gradient fade over bottom half */}
          <LinearGradient
            colors={["rgba(249,250,251,0)", "rgba(249,250,251,0.97)"]}
            style={s.teaserGradient}
            pointerEvents="none"
          />
        </View>

        {/* Lock card CTA */}
        <View style={s.lockCard}>
          <Text style={s.lockIcon}>🔒</Text>
          <Text style={s.lockTitle}>Your personalised plan is waiting</Text>
          <Text style={s.lockSub}>
            Connect with a dietician to get a meal plan tailored to your health goals, body, and diet.
          </Text>
          <Pressable onPress={onFindDoctor} style={s.lockCta}>
            <Text style={s.lockCtaText}>Find a Doctor</Text>
          </Pressable>
        </View>
      </View>
    </ScrollView>
  );
}

function EmptyPlan({
  isConnected, onFindDoctor, onGenerate
}: { isConnected: boolean; onFindDoctor: () => void; onGenerate: () => Promise<void> }) {
  const [generating, setGenerating] = React.useState(false);
  const handleGenerate = async () => {
    setGenerating(true);
    await onGenerate();
    setGenerating(false);
  };
  return (
    <View style={s.empty}>
      <Text style={s.emptyEmoji}>🍽️</Text>
      {isConnected ? (
        <>
          <Text style={s.emptyTitle}>No meal plan yet</Text>
          <Text style={s.emptySub}>
            Your plan is being set up. If it doesn't appear shortly, tap below to generate it now.
          </Text>
          <Pressable onPress={handleGenerate} style={s.emptyBtn} disabled={generating}>
            {generating
              ? <ActivityIndicator color="#fff" size="small" />
              : <Text style={s.emptyBtnText}>Generate My Plan</Text>}
          </Pressable>
        </>
      ) : (
        <>
          <Text style={s.emptyTitle}>No meal plan yet</Text>
          <Text style={s.emptySub}>Connect with a dietician to get a personalised meal plan.</Text>
          <Pressable onPress={onFindDoctor} style={s.emptyBtn}>
            <Text style={s.emptyBtnText}>Find a Doctor</Text>
          </Pressable>
        </>
      )}
    </View>
  );
}

export default function MealsScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const profile = useAuthStore(s => s.profile);
  const isSubscribed = profile?.subscription_status === "active";
  const isConnected = !!(profile?.doctor_id || isSubscribed);

  // Always call hooks regardless of subscription status (Rules of Hooks)
  const { data: plan, isLoading } = useQuery({
    queryKey: QUERY_KEYS.WEEK_PLAN,
    queryFn: getWeeklyPlan,
    staleTime: 1000 * 60 * 10,
    enabled: isSubscribed,
  });

  const todayMeals: Meal[] = plan?.[todayKey()] ?? [];

  const autoAttempted = React.useRef(false);
  React.useEffect(() => {
    if (!isSubscribed) return;
    if (!isLoading && isConnected && !autoAttempted.current) {
      const planIsEmpty = !plan || Object.keys(plan).length === 0;
      if (planIsEmpty) {
        autoAttempted.current = true;
        generatePlan()
          .then(() => qc.invalidateQueries({ queryKey: QUERY_KEYS.WEEK_PLAN }))
          .catch(() => {});
      }
    }
  }, [isLoading, plan, isConnected, isSubscribed]);

  // Free users see the teaser — real plan hidden until subscription active
  if (!isSubscribed) {
    return <TeaserView onFindDoctor={() => router.push("/doctor/find-doctor")} />;
  }

  if (isLoading) return <View style={s.loader}><ActivityIndicator size="large" color="#1E7C45" /></View>;

  return (
    <ScrollView style={s.root} contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
      <View style={s.header}>
        <Text style={s.headerTitle}>Meal Plan</Text>
        <Pressable onPress={() => router.push("/meals/week-view")} style={s.weekBtn}>
          <Text style={s.weekBtnText}>Week View</Text>
          <ChevronRight size={14} color="#1E7C45" />
        </Pressable>
      </View>

      <View style={s.body}>
        <Text style={s.dateLabel}>
          {new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}
        </Text>

        {todayMeals.length === 0 ? (
          <EmptyPlan
            isConnected={isConnected}
            onFindDoctor={() => router.push("/doctor/find-doctor")}
            onGenerate={async () => {
              try {
                await generatePlan();
                qc.invalidateQueries({ queryKey: QUERY_KEYS.WEEK_PLAN });
                showToast("Meal plan generated! 🎉", "success");
              } catch {
                showToast("Plan generation failed. Please try again.", "error");
              }
            }}
          />
        ) : (
          MEAL_ORDER
            .map(type => todayMeals.find(m => m["Meal Type"] === type))
            .filter((m): m is Meal => !!m)
            .map((meal) => (
              <Pressable
                key={meal["Meal Type"]}
                onPress={() => router.push({ pathname: "/meals/meal-detail", params: { date: todayKey(), type: meal["Meal Type"] } })}
                style={s.mealCard}
              >
                <View style={s.mealHeader}>
                  <Text style={s.mealType}>{meal["Meal Type"]}</Text>
                  <Text style={s.mealCal}>{meal["Total Calories"]} cal</Text>
                </View>
                <Text style={s.mealName} numberOfLines={2}>{meal["Menu Names"]}</Text>
                <View style={{ marginTop: 8 }}>
                  <MacroRow
                    protein={Math.round(meal["Total Protein"])}
                    carbs={Math.round(meal["Total Carbs"])}
                    fat={Math.round(meal["Total Fat"])}
                    fiber={Math.round(meal["Total Fiber"])}
                  />
                </View>
                {meal.doctor_note && (
                  <View style={s.note}>
                    <Text style={s.noteText}>📝 "{meal.doctor_note}"</Text>
                  </View>
                )}
              </Pressable>
            ))
        )}

        {todayMeals.length > 0 && (
          <View style={s.actionRow}>
            <Pressable onPress={() => router.push("/meals/shopping-list")} style={s.actionBtn}>
              <Text style={s.actionBtnText}>🛒 Shopping List</Text>
            </Pressable>
            <Pressable onPress={() => router.push("/meals/plan-history")} style={s.actionBtn}>
              <Text style={s.actionBtnText}>📋 Plan History</Text>
            </Pressable>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root:              { flex: 1, backgroundColor: "#F9FAFB" },
  loader:            { flex: 1, alignItems: "center", justifyContent: "center" },
  scroll:            { paddingBottom: 40 },
  header:            { backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB", padding: 16, flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  headerTitle:       { fontSize: 20, fontWeight: "600", color: "#111827" },
  weekBtn:           { flexDirection: "row", alignItems: "center", gap: 2 },
  weekBtnText:       { fontSize: 13, fontWeight: "500", color: "#1E7C45" },
  weekBtnDisabled:   { flexDirection: "row", alignItems: "center", gap: 2 },
  weekBtnTextDisabled: { fontSize: 13, fontWeight: "500", color: "#9CA3AF" },
  body:              { paddingHorizontal: 20, paddingTop: 16, gap: 12 },
  dateLabel:         { fontSize: 13, fontWeight: "500", color: "#374151", marginBottom: 4 },
  mealCard:          { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 16 },
  mealHeader:        { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 4 },
  mealType:          { fontSize: 11, fontWeight: "600", color: "#6B7280", textTransform: "uppercase", letterSpacing: 0.5 },
  mealCal:           { fontSize: 14, fontWeight: "700", color: "#1E7C45" },
  mealName:          { fontSize: 15, fontWeight: "600", color: "#111827" },
  note:              { marginTop: 8, backgroundColor: "#F0FDF4", borderRadius: 6, padding: 8 },
  noteText:          { fontSize: 11, color: "#374151", fontStyle: "italic" },
  empty:             { alignItems: "center", padding: 40 },
  emptyEmoji:        { fontSize: 48, marginBottom: 12 },
  emptyTitle:        { fontSize: 18, fontWeight: "600", color: "#111827", marginBottom: 8 },
  emptySub:          { fontSize: 14, color: "#6B7280", textAlign: "center", lineHeight: 20, marginBottom: 20 },
  emptyBtn:          { height: 48, paddingHorizontal: 24, borderRadius: 24, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  emptyBtnText:      { fontSize: 14, fontWeight: "600", color: "#fff" },
  actionRow:         { flexDirection: "row", gap: 12 },
  actionBtn:         { flex: 1, height: 48, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  actionBtnText:     { fontSize: 13, fontWeight: "500", color: "#374151" },
  // Teaser styles
  teaserContainer:   { position: "relative", overflow: "hidden", maxHeight: 360 },
  teaserGradient:    { position: "absolute", bottom: 0, left: 0, right: 0, height: 200 },
  lockCard:          { backgroundColor: "#fff", borderRadius: 16, borderWidth: 1.5, borderColor: "#E5E7EB", padding: 24, alignItems: "center", marginTop: 8, shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.06, shadowRadius: 8, elevation: 3 },
  lockIcon:          { fontSize: 32, marginBottom: 10 },
  lockTitle:         { fontSize: 17, fontWeight: "700", color: "#111827", textAlign: "center", marginBottom: 8 },
  lockSub:           { fontSize: 14, color: "#6B7280", textAlign: "center", lineHeight: 20, marginBottom: 20 },
  lockCta:           { height: 52, paddingHorizontal: 32, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  lockCtaText:       { fontSize: 15, fontWeight: "600", color: "#fff" },
});
