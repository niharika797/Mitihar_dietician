import React, { useState, useMemo } from "react";
import {
  View, Text, StyleSheet, ActivityIndicator, Pressable, ScrollView,
} from "react-native";
import { useRouter } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { LinearGradient } from "expo-linear-gradient";
import * as Sentry from "@sentry/react-native";
import { useAuthStore } from "../../store/useAuthStore";
import { generatePlan, confirmMealChoice, getDailyChoices, getWeeklyPlan } from "../../services/meals";
import { useToast } from "../../components/shared";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { MacroRow } from "../../components/shared";
import type { Meal, WeeklyComboV2, WeekResponseV2 } from "../../types";

const MEAL_ORDER = ["Breakfast", "Lunch", "Dinner"];
const MEAL_CALORIE_LABELS: Record<string, string> = {
  Breakfast: "kcal target",
  Lunch:     "kcal target",
  Dinner:    "kcal target",
};

const TEASER_MEALS: Meal[] = [
  { Date: "", "Meal Type": "Breakfast", "Menu Names": "Oats Upma + Moong Dal Cheela",         "Diet Type": "Vegetarian", "Total Calories": 395, "Total Protein": 18, "Total Carbs": 58, "Total Fat": 8,  "Total Fiber": 6 },
  { Date: "", "Meal Type": "Lunch",     "Menu Names": "Dal Tadka + 2 Rotis + Cucumber Raita", "Diet Type": "Vegetarian", "Total Calories": 520, "Total Protein": 22, "Total Carbs": 68, "Total Fat": 14, "Total Fiber": 8 },
  { Date: "", "Meal Type": "Dinner",    "Menu Names": "Palak Paneer + 1 Roti + Salad",         "Diet Type": "Vegetarian", "Total Calories": 410, "Total Protein": 20, "Total Carbs": 38, "Total Fat": 16, "Total Fiber": 6 },
];

function todayKey() { return new Date().toISOString().slice(0, 10); }

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// Returns the 7 ISO date strings (Mon–Sun) of the week containing todayStr
function getWeekDays(todayStr: string): string[] {
  // Parse as local noon to avoid UTC-shift date drift
  const [y, m, d] = todayStr.split("-").map(Number);
  const base = new Date(y, m - 1, d);
  const dow = base.getDay(); // 0=Sun
  base.setDate(base.getDate() + (dow === 0 ? -6 : 1 - dow)); // rewind to Mon
  return Array.from({ length: 7 }, (_, i) => {
    const dd = new Date(base);
    dd.setDate(base.getDate() + i);
    const yy = dd.getFullYear();
    const mm = String(dd.getMonth() + 1).padStart(2, "0");
    const day = String(dd.getDate()).padStart(2, "0");
    return `${yy}-${mm}-${day}`;
  });
}

// ── Week date strip ────────────────────────────────────────────────────────
interface WeekStripProps {
  days: string[];
  selected: string;
  today: string;
  onSelect: (d: string) => void;
}

function WeekStrip({ days, selected, today, onSelect }: WeekStripProps) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.weekStripRow}>
      {days.map((d, i) => {
        const isToday    = d === today;
        const isSelected = d === selected;
        const isPast     = d < today;
        const dayNum     = new Date(d + "T12:00:00").getDate();
        return (
          <Pressable
            key={d}
            style={[s.dayPill, isSelected && s.dayPillSelected, isToday && !isSelected && s.dayPillToday]}
            onPress={() => onSelect(d)}
          >
            <Text style={[s.dayPillLabel, isSelected && s.dayPillLabelSelected, isPast && !isSelected && s.dayPillLabelPast]}>
              {DAY_LABELS[i]}
            </Text>
            <Text style={[s.dayPillNum, isSelected && s.dayPillNumSelected, isPast && !isSelected && s.dayPillNumPast]}>
              {dayNum}
            </Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

// ── Past day read-only view ─────────────────────────────────────────────────
function PastDayView({ date }: { date: string }) {
  const { data, isLoading } = useQuery({
    queryKey: QUERY_KEYS.DAILY_CHOICES(date),
    queryFn: () => getDailyChoices(date),
    staleTime: 1000 * 60 * 10,
  });

  if (isLoading) {
    return (
      <View style={s.pastLoading}>
        <ActivityIndicator size="small" color="#1E7C45" />
      </View>
    );
  }

  const choiceMap: Record<string, { recipe_name: string; calories: number }> = {};
  for (const c of (data?.choices ?? [])) {
    choiceMap[c.meal_type] = { recipe_name: c.recipe_name, calories: c.calories };
  }

  return (
    <View style={s.pastWrapper}>
      {MEAL_ORDER.map((mealType) => {
        const choice = choiceMap[mealType];
        return (
          <View key={mealType} style={s.pastSlot}>
            <View style={s.slotHeader}>
              <Text style={s.slotTitle}>{mealType.toUpperCase()}</Text>
            </View>
            {choice ? (
              <View style={s.pastChoice}>
                <Text style={s.pastCheck}>✓</Text>
                <View style={{ flex: 1 }}>
                  <Text style={s.pastName} numberOfLines={2}>{choice.recipe_name}</Text>
                  <Text style={s.pastCal}>{Math.round(choice.calories)} kcal planned</Text>
                </View>
              </View>
            ) : (
              <View style={s.pastNoLog}>
                <Text style={s.pastNoLogText}>— Not logged</Text>
              </View>
            )}
          </View>
        );
      })}
    </View>
  );
}

// ── v2 combo card (weekly plan combos from doctor) ─────────────────────────
interface V2ComboCardProps {
  combo: WeeklyComboV2;
  onSelect: () => void;
  onCardPress: () => void;
  isPending: boolean;
  isConfirmedThisCombo: boolean;
  isSlotConfirmed: boolean;
}

function V2ComboCard({ combo, onSelect, onCardPress, isPending, isConfirmedThisCombo, isSlotConfirmed }: V2ComboCardProps) {
  const dishNames = combo.dishes.map(d => d.recipe_name).join(" + ");
  return (
    <Pressable style={[s.suggCard, isConfirmedThisCombo && s.suggCardSelected]} onPress={onCardPress}>
      {combo.contains_doctor_pick && (
        <View style={[s.pinBadge, { marginBottom: 6 }]}>
          <Text style={s.pinBadgeText}>🩺 Doctor's pick</Text>
        </View>
      )}
      <Text style={s.suggName} numberOfLines={3}>{dishNames}</Text>
      <Text style={s.suggCal}>~{Math.round(combo.total_calories)} kcal</Text>
      {(combo.required_count ?? 0) > 0 && (
        combo.cookable ? (
          <View style={s.cookNowBadge}><Text style={s.cookNowText}>✓ Cook now</Text></View>
        ) : (combo.have_count ?? 0) > 0 ? (
          <Text style={s.coverageText}>
            Have {combo.have_count}/{combo.required_count}
            {combo.missing_ingredients && combo.missing_ingredients.length > 0
              ? ` · need ${combo.missing_ingredients.slice(0, 2).join(", ")}${combo.missing_ingredients.length > 2 ? ` +${combo.missing_ingredients.length - 2}` : ""}`
              : ""}
          </Text>
        ) : null
      )}
      <View style={{ gap: 3, marginTop: 4 }}>
        {combo.dishes.map(d => (
          <View key={d.food_item_id} style={[s.slotTag, combo.pinned_dish_ids.includes(d.food_item_id) && s.slotTagPinned]}>
            <Text style={s.slotTagText}>{d.slot_type}</Text>
          </View>
        ))}
      </View>
      {isConfirmedThisCombo ? (
        <View style={[s.selectBtn, { backgroundColor: "#15803D" }]}>
          <Text style={s.selectBtnText}>✓ Chosen</Text>
        </View>
      ) : (
        <Pressable
          style={[s.selectBtn, (isPending || isSlotConfirmed) && s.selectBtnDisabled]}
          onPress={e => { e.stopPropagation?.(); onSelect(); }}
          disabled={isPending || isSlotConfirmed}
        >
          {isPending
            ? <ActivityIndicator size="small" color="#fff" />
            : <Text style={s.selectBtnText}>Select</Text>}
        </Pressable>
      )}
    </Pressable>
  );
}

// ── Teaser (free users) ────────────────────────────────────────────────────
function TeaserMealCard({ meal }: { meal: Meal }) {
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
        <View style={s.teaserContainer}>
          {TEASER_MEALS.map((meal) => (
            <TeaserMealCard key={meal["Meal Type"]} meal={meal} />
          ))}
          <LinearGradient
            colors={["rgba(249,250,251,0)", "rgba(249,250,251,0.97)"]}
            style={s.teaserGradient}
            pointerEvents="none"
          />
        </View>
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

// ── Empty plan ─────────────────────────────────────────────────────────────
function EmptyPlan({
  isConnected, onFindDoctor, onGenerate,
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
          <Text style={s.emptySub}>Your plan is being set up. Tap below to generate it now.</Text>
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

// ── Main screen ────────────────────────────────────────────────────────────
export default function MealsScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const profile = useAuthStore(s => s.profile);
  const isSubscribed = profile?.subscription_status === "active";
  const isConnected = !!(profile?.doctor_id || isSubscribed);
  const today = todayKey();

  const [selectedDate, setSelectedDate] = useState(today);
  const weekDays = useMemo(() => getWeekDays(today), [today]);
  const isPastDay = selectedDate < today;

  // Load confirmed choices for the selected date (today/future only — past days use PastDayView)
  const { data: dailyChoices } = useQuery({
    queryKey: QUERY_KEYS.DAILY_CHOICES(selectedDate),
    queryFn: () => getDailyChoices(selectedDate),
    staleTime: 1000 * 60 * 5,
    enabled: isSubscribed && !isPastDay,
  });

  // v2 weekly plan query — detect generation_version
  const weekPlanQuery = useQuery({
    queryKey: QUERY_KEYS.WEEK_PLAN,
    queryFn: getWeeklyPlan,
    staleTime: 1000 * 60 * 5,
    enabled: isSubscribed,
  });
  const weekData = weekPlanQuery.data;
  const v2Plan = weekData as WeekResponseV2 | undefined;

  // v2 slot confirmed state: key="${date}-${mealType}", value=combo_id
  const [v2ConfirmedSlots, setV2ConfirmedSlots] = useState<Record<string, number>>({});

  // Seed confirmed slots from server on mount/date change so hard-refresh restores "✓ Chosen"
  React.useEffect(() => {
    if (!dailyChoices?.choices) return;
    const updates: Record<string, number> = {};
    for (const c of dailyChoices.choices) {
      if (c.weekly_combo_id != null) {
        updates[`${dailyChoices.date}-${c.meal_type}`] = c.weekly_combo_id;
      }
    }
    if (Object.keys(updates).length > 0) {
      setV2ConfirmedSlots(prev => ({ ...prev, ...updates }));
    }
  }, [dailyChoices]);

  const v2ConfirmMut = useMutation({
    mutationFn: (vars: { combo: WeeklyComboV2; mealType: string; date: string }) =>
      confirmMealChoice({
        food_item_ids: vars.combo.dishes.map(d => d.food_item_id),
        date: vars.date,
        meal_type: vars.mealType,
        weekly_combo_id: vars.combo.combo_id,
      }),
    onSuccess: (_, vars) => {
      setV2ConfirmedSlots(prev => ({ ...prev, [`${vars.date}-${vars.mealType}`]: vars.combo.combo_id }));
      qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
      qc.invalidateQueries({ queryKey: QUERY_KEYS.DAILY_CHOICES(vars.date) });
      qc.invalidateQueries({ queryKey: QUERY_KEYS.WEEK_PLAN });
    },
    onError: () => showToast("Failed to confirm choice. Try again.", "error"),
  });

  const autoAttempted = React.useRef(false);
  React.useEffect(() => {
    if (!isSubscribed || autoAttempted.current) return;
    autoAttempted.current = true;
    generatePlan()
      .then(() => qc.invalidateQueries({ queryKey: QUERY_KEYS.WEEK_PLAN }))
      .catch((e) => Sentry.captureException(e));
  }, [isSubscribed]);

  if (!isSubscribed) {
    return <TeaserView onFindDoctor={() => router.push("/doctor/find-doctor")} />;
  }

  // Format selected date for display
  const [selY, selM, selD] = selectedDate.split("-").map(Number);
  const selDateLabel = new Date(selY, selM - 1, selD).toLocaleDateString("en-IN", {
    weekday: "long", day: "numeric", month: "long",
  });

  return (
    <ScrollView style={s.root} contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
      <View style={s.header}>
        <Text style={s.headerTitle}>Meal Plan</Text>
      </View>

      {/* Week strip */}
      <WeekStrip days={weekDays} selected={selectedDate} today={today} onSelect={setSelectedDate} />

      <View style={s.body}>
        <Text style={s.dateLabel}>{selDateLabel}</Text>

        {isPastDay ? (
          // Past days: read-only confirmed choices
          <>
            <Text style={s.subLabel}>What you planned for this day</Text>
            <PastDayView date={selectedDate} />
          </>
        ) : (
          (() => {
            const v2DayData = v2Plan?.days.find(d => d.date === selectedDate);
            const v2IsPending = v2Plan?.approval_status === "pending";
            return (
              <>
                <Text style={s.subLabel}>
                  {selectedDate === today ? "Choose your combo for today" : "Plan ahead — choose your combo for this day"}
                </Text>
                {v2IsPending ? (
                  <View style={s.pendingCard}>
                    <Text style={s.pendingText}>Your meal plan is being reviewed by your doctor. Check back soon.</Text>
                  </View>
                ) : !v2DayData ? (
                  <View style={s.noSugg}>
                    <Text style={s.noSuggText}>No plan data for this day.</Text>
                  </View>
                ) : (
                  MEAL_ORDER.map(mealType => {
                    const slotData = v2DayData.meals[mealType as keyof typeof v2DayData.meals];
                    const slotKey = `${selectedDate}-${mealType}`;
                    const confirmedComboId = v2ConfirmedSlots[slotKey];
                    const isSlotAlreadyConfirmed = (dailyChoices?.choices ?? []).some(c => c.meal_type === mealType);
                    const isSlotConfirmed = confirmedComboId !== undefined || isSlotAlreadyConfirmed;
                    return (
                      <View key={`v2-${selectedDate}-${mealType}`} style={s.slotContainer}>
                        <View style={s.slotHeader}>
                          <Text style={s.slotTitle}>{mealType.toUpperCase()}</Text>
                        </View>
                        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.cardRow}>
                          {slotData.combos.map(combo => (
                            <V2ComboCard
                              key={combo.combo_id}
                              combo={combo}
                              onSelect={() => v2ConfirmMut.mutate({ combo, mealType, date: selectedDate })}
                              onCardPress={() => router.push({
                                pathname: "/meals/combo-detail" as any,
                                params: {
                                  combo: JSON.stringify(combo),
                                  date: selectedDate,
                                  mealType,
                                },
                              })}
                              isPending={v2ConfirmMut.isPending && v2ConfirmMut.variables?.combo.combo_id === combo.combo_id}
                              isConfirmedThisCombo={confirmedComboId === combo.combo_id}
                              isSlotConfirmed={isSlotConfirmed}
                            />
                          ))}
                        </ScrollView>
                      </View>
                    );
                  })
                )}
              </>
            );
          })()
        )}

        {/* Pantry + Shopping List moved to the home dashboard (components/
            PantrySection, ShoppingListSection) — history stays here. */}
        <View style={s.actionRow}>
          <Pressable onPress={() => router.push("/meals/plan-history")} style={s.actionBtn}>
            <Text style={s.actionBtnText}>📋 Plan History</Text>
          </Pressable>
        </View>
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root:              { flex: 1, backgroundColor: "#F9FAFB" },
  scroll:            { paddingBottom: 40 },
  header:            { backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB", padding: 16, flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  headerTitle:       { fontSize: 20, fontWeight: "600", color: "#111827" },
weekBtnDisabled:   { flexDirection: "row", alignItems: "center", gap: 2 },
  weekBtnTextDisabled: { fontSize: 13, fontWeight: "500", color: "#9CA3AF" },
  body:              { paddingHorizontal: 16, paddingTop: 16, gap: 12 },
  dateLabel:         { fontSize: 14, fontWeight: "600", color: "#111827" },
  subLabel:          { fontSize: 12, color: "#6B7280", marginBottom: 4 },

  // Slot
  slotContainer:     { backgroundColor: "#fff", borderRadius: 14, borderWidth: 1, borderColor: "#E5E7EB", overflow: "hidden" },
  slotHeader:        { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 14, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  slotTitle:         { fontSize: 12, fontWeight: "700", color: "#374151", letterSpacing: 0.8 },
  slotTarget:        { fontSize: 12, fontWeight: "500", color: "#6B7280" },

  // Suggestion cards row
  cardRow:           { paddingHorizontal: 12, paddingVertical: 12, gap: 10 },
  suggCard:          { width: 160, backgroundColor: "#F9FAFB", borderRadius: 10, borderWidth: 1.5, borderColor: "#E5E7EB", padding: 12 },
  suggCardSelected:  { borderColor: "#1E7C45", backgroundColor: "#F0FDF4" },
  badgeRow:          { flexDirection: "row", flexWrap: "wrap", gap: 4, marginBottom: 6, minHeight: 18 },
  pinBadge:          { flexDirection: "row", alignItems: "center", gap: 3, backgroundColor: "#FEF3C7", borderRadius: 99, paddingHorizontal: 6, paddingVertical: 2 },
  pinBadgeText:      { fontSize: 9, fontWeight: "600", color: "#92400E" },
  recoBadge:         { backgroundColor: "#DCFCE7", borderRadius: 99, paddingHorizontal: 6, paddingVertical: 2 },
  recoBadgeText:     { fontSize: 9, fontWeight: "600", color: "#166534" },
  selectedBadge:     { backgroundColor: "#1E7C45", borderRadius: 99, paddingHorizontal: 6, paddingVertical: 2 },
  selectedBadgeText: { fontSize: 9, fontWeight: "600", color: "#fff" },
  suggName:          { fontSize: 13, fontWeight: "600", color: "#111827", lineHeight: 17, marginBottom: 2 },
  suggCal:           { fontSize: 12, fontWeight: "700", color: "#1E7C45", marginBottom: 4 },
  cookNowBadge:      { alignSelf: "flex-start", backgroundColor: "#DCFCE7", borderRadius: 99, paddingHorizontal: 8, paddingVertical: 2, marginBottom: 4 },
  cookNowText:       { fontSize: 10, fontWeight: "700", color: "#166534" },
  coverageText:      { fontSize: 11, color: "#6B7280", marginBottom: 4 },
  selectBtn:         { marginTop: 10, height: 32, borderRadius: 8, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  selectBtnDisabled: { opacity: 0.6 },
  selectBtnText:     { fontSize: 12, fontWeight: "600", color: "#fff" },

  // Confirmed state
  confirmedContainer:{ paddingHorizontal: 14, paddingVertical: 12 },
  confirmedRow:      { flexDirection: "row", alignItems: "center", gap: 10 },
  confirmedCheck:    { fontSize: 18, color: "#1E7C45" },
  confirmedName:     { fontSize: 14, fontWeight: "600", color: "#111827" },
  confirmedLabel:    { fontSize: 11, color: "#6B7280", marginTop: 2 },
  changeBtn:         { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8, borderWidth: 1.5, borderColor: "#1E7C45" },
  changeBtnText:     { fontSize: 12, fontWeight: "500", color: "#1E7C45" },

  // Slot-type tag inside combo card
  slotTag:           { backgroundColor: "#EFF6FF", borderRadius: 4, paddingHorizontal: 5, paddingVertical: 1, alignSelf: "flex-start" },
  slotTagText:       { fontSize: 9, fontWeight: "600", color: "#1D4ED8" },
  slotTagPinned:     { backgroundColor: "#FEF3C7" },

  // v2 pending state
  pendingCard:       { backgroundColor: "#FEF9C3", borderRadius: 12, borderWidth: 1, borderColor: "#FDE047", padding: 16 },
  pendingText:       { fontSize: 14, color: "#713F12", textAlign: "center", lineHeight: 20 },

  // No suggestions
  noSugg:            { padding: 16, alignItems: "center" },
  noSuggText:        { fontSize: 13, color: "#9CA3AF" },

  // Week strip
  weekStripRow:      { paddingHorizontal: 16, paddingVertical: 10, gap: 8 },
  dayPill:           { alignItems: "center", paddingHorizontal: 10, paddingVertical: 6, borderRadius: 10, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff", minWidth: 44 },
  dayPillSelected:   { backgroundColor: "#1E7C45", borderColor: "#1E7C45" },
  dayPillToday:      { borderColor: "#1E7C45" },
  dayPillLabel:      { fontSize: 10, fontWeight: "600", color: "#6B7280" },
  dayPillLabelSelected: { color: "#fff" },
  dayPillLabelPast:  { color: "#9CA3AF" },
  dayPillNum:        { fontSize: 15, fontWeight: "700", color: "#111827", marginTop: 1 },
  dayPillNumSelected:{ color: "#fff" },
  dayPillNumPast:    { color: "#9CA3AF" },

  // Past day view
  pastLoading:       { paddingVertical: 32, alignItems: "center" },
  pastWrapper:       { gap: 12 },
  pastSlot:          { backgroundColor: "#fff", borderRadius: 14, borderWidth: 1, borderColor: "#E5E7EB", overflow: "hidden" },
  pastChoice:        { flexDirection: "row", alignItems: "flex-start", gap: 10, paddingHorizontal: 14, paddingVertical: 12 },
  pastCheck:         { fontSize: 18, color: "#1E7C45", marginTop: 1 },
  pastName:          { fontSize: 14, fontWeight: "600", color: "#111827", lineHeight: 18 },
  pastCal:           { fontSize: 12, color: "#6B7280", marginTop: 2 },
  pastNoLog:         { paddingHorizontal: 14, paddingVertical: 14 },
  pastNoLogText:     { fontSize: 13, color: "#9CA3AF", fontStyle: "italic" },

  // Skeleton
  skelLine:          { backgroundColor: "#E5E7EB", borderRadius: 4 },

  // Misc
  empty:             { alignItems: "center", padding: 40 },
  emptyEmoji:        { fontSize: 48, marginBottom: 12 },
  emptyTitle:        { fontSize: 18, fontWeight: "600", color: "#111827", marginBottom: 8 },
  emptySub:          { fontSize: 14, color: "#6B7280", textAlign: "center", lineHeight: 20, marginBottom: 20 },
  emptyBtn:          { height: 48, paddingHorizontal: 24, borderRadius: 24, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  emptyBtnText:      { fontSize: 14, fontWeight: "600", color: "#fff" },
  actionRow:         { flexDirection: "row", gap: 12 },
  actionBtn:         { flex: 1, height: 48, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  actionBtnText:     { fontSize: 13, fontWeight: "500", color: "#374151" },
  // Legacy meal card (teaser only)
  mealCard:          { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 16 },
  mealHeader:        { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 4 },
  mealType:          { fontSize: 11, fontWeight: "600", color: "#6B7280", textTransform: "uppercase", letterSpacing: 0.5 },
  mealCal:           { fontSize: 14, fontWeight: "700", color: "#1E7C45" },
  mealName:          { fontSize: 15, fontWeight: "600", color: "#111827" },
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
