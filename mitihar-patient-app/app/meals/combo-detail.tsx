import React, { useState } from "react";
import {
  View, Text, ScrollView, Pressable, StyleSheet,
  ActivityIndicator, LayoutAnimation, UIManager, Platform,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { ChevronLeft, ChevronDown } from "lucide-react-native";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { confirmMealChoice, getDailyChoices, getComboDetails } from "../../services/meals";
import { useToast } from "../../components/shared";
import type { WeeklyComboV2 } from "../../types";

if (Platform.OS === "android") {
  UIManager.setLayoutAnimationEnabledExperimental?.(true);
}

const BOWL_FACTORS: Record<"S" | "M" | "L", number> = { S: 0.75, M: 1.0, L: 1.25 };
const BOWL_DB_MAP: Record<"S" | "M" | "L", string> = { S: "small", M: "medium", L: "large" };
const BOWL_LABELS: Record<"S" | "M" | "L", string> = {
  S: "Small bowl · 75% of standard",
  M: "Medium bowl · Standard serving",
  L: "Large bowl · 125% of standard",
};

const SLOT_LABELS: Record<string, string> = {
  main_dish:    "Main Dish",
  grain:        "Grain",
  dal_protein:  "Dal & Protein",
  sabzi:        "Vegetable",
  accompaniment:"Side",
  beverage:     "Beverage",
  snack_item:   "Snack",
};

function gramsToLabel(g: number): string {
  if (g <= 2)   return "a pinch";
  if (g <= 10)  return "1 tsp";
  if (g <= 25)  return "1 tbsp";
  if (g <= 60)  return "small";
  if (g <= 130) return "medium";
  if (g <= 220) return "large";
  return "generous";
}

export default function ComboDetailScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();

  const params = useLocalSearchParams<{ combo: string; date: string; mealType: string }>();
  const combo: WeeklyComboV2 = JSON.parse(params.combo ?? "{}");
  const date = params.date ?? "";
  const mealType = params.mealType ?? "";

  const [bowlSize, setBowlSize] = useState<"S" | "M" | "L">("M");
  const bowlFactor = BOWL_FACTORS[bowlSize];

  const [expandedDish, setExpandedDish] = useState<number | null>(null);

  const { data: dailyChoices } = useQuery({
    queryKey: QUERY_KEYS.DAILY_CHOICES(date),
    queryFn: () => getDailyChoices(date),
    staleTime: 1000 * 60 * 5,
  });

  const { data: comboDetail, isLoading: detailLoading } = useQuery({
    queryKey: ["combo-detail", combo.combo_id],
    queryFn: () => getComboDetails(combo.combo_id),
    staleTime: 1000 * 60 * 10,
    enabled: !!combo.combo_id,
  });

  const confirmMut = useMutation({
    mutationFn: () =>
      confirmMealChoice({
        food_item_ids: combo.dishes.map(d => d.food_item_id),
        date,
        meal_type: mealType,
        weekly_combo_id: combo.combo_id,
        bowl_size: BOWL_DB_MAP[bowlSize],
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
      qc.invalidateQueries({ queryKey: QUERY_KEYS.DAILY_CHOICES(date) });
      qc.invalidateQueries({ queryKey: QUERY_KEYS.WEEK_PLAN });
      showToast("Combo confirmed!", "success");
      setTimeout(() => router.back(), 800);
    },
    onError: () => showToast("Failed to confirm. Try again.", "error"),
  });

  // Determine confirm button state
  const slotChoice = dailyChoices?.choices.find(c => c.meal_type === mealType);
  const isThisComboConfirmed = slotChoice?.weekly_combo_id === combo.combo_id;
  const isOtherComboConfirmed = !!(slotChoice && slotChoice.weekly_combo_id !== combo.combo_id);

  const scaledTotal = Math.round((combo.total_calories ?? 0) * bowlFactor);

  const toggleDish = (dishId: number) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpandedDish(prev => (prev === dishId ? null : dishId));
  };

  return (
    <View style={s.root}>

      {/* Header */}
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <View style={s.headerCenter}>
          <Text style={s.headerType}>{mealType.toUpperCase()} · OPTION {(combo.combo_index ?? 0) + 1}</Text>
          <Text style={s.headerSub}>{combo.dishes.length} dishes · ~{scaledTotal} kcal</Text>
        </View>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>

        {/* Doctor's pick badge */}
        {combo.contains_doctor_pick && (
          <View style={s.doctorBadge}>
            <Text style={s.doctorBadgeText}>🩺 Doctor's recommended combo</Text>
          </View>
        )}

        {/* Bowl size selector */}
        <View style={s.bowlSection}>
          <Text style={s.sectionLabel}>SERVING SIZE</Text>
          <View style={s.pillRow}>
            {(["S", "M", "L"] as const).map(size => (
              <Pressable
                key={size}
                style={[s.pill, bowlSize === size && s.pillSelected]}
                onPress={() => setBowlSize(size)}
              >
                <Text style={[s.pillText, bowlSize === size && s.pillTextSelected]}>{size}</Text>
              </Pressable>
            ))}
          </View>
          <Text style={s.bowlHint}>{BOWL_LABELS[bowlSize]}</Text>
        </View>

        {/* Total calories */}
        <View style={s.totalCard}>
          <Text style={s.totalLabel}>TOTAL</Text>
          <View style={s.totalRow}>
            <Text style={s.totalCal}>{scaledTotal}</Text>
            <Text style={s.totalUnit}>kcal</Text>
          </View>
        </View>

        {/* Dishes */}
        <Text style={s.sectionLabel}>DISHES</Text>
        {detailLoading ? (
          <ActivityIndicator style={{ marginTop: 16 }} color="#1E7C45" />
        ) : (
          combo.dishes.map(dish => {
            const detail = comboDetail?.dishes.find(d => d.food_item_id === dish.food_item_id);
            const isPinned = combo.pinned_dish_ids.includes(dish.food_item_id);
            const scaledCal = Math.round(dish.calories * bowlFactor);
            const scaledProtein = detail ? Math.round(detail.protein * bowlFactor) : null;
            const scaledCarbs = detail ? Math.round(detail.carbs * bowlFactor) : null;
            const scaledFat = detail ? Math.round(detail.fat * bowlFactor) : null;
            const ingredients = detail?.ingredients ?? [];
            const isExpanded = expandedDish === dish.food_item_id;

            return (
              <View key={dish.food_item_id} style={s.dishCard}>
                <View style={s.dishTop}>
                  <View style={{ flex: 1, marginRight: 8 }}>
                    <Text style={s.dishName}>{dish.recipe_name}</Text>
                    <View style={s.badgeRow}>
                      <View style={s.slotTag}>
                        <Text style={s.slotTagText}>{SLOT_LABELS[dish.slot_type] ?? dish.slot_type}</Text>
                      </View>
                      {isPinned && (
                        <View style={s.pinBadge}>
                          <Text style={s.pinBadgeText}>🩺 Doctor's pick</Text>
                        </View>
                      )}
                    </View>
                  </View>
                  <View style={s.dishCalBlock}>
                    <Text style={s.dishCal}>{scaledCal}</Text>
                    <Text style={s.dishCalUnit}>kcal</Text>
                  </View>
                </View>

                {/* Macros — shown if detail endpoint returned them */}
                {scaledProtein !== null ? (
                  <View style={s.macroPills}>
                    {[
                      { label: "P", val: scaledProtein },
                      { label: "C", val: scaledCarbs! },
                      { label: "F", val: scaledFat! },
                    ].map(m => (
                      <View key={m.label} style={s.macroPill}>
                        <Text style={s.macroPillVal}>{m.val}g</Text>
                        <Text style={s.macroPillLabel}>{m.label}</Text>
                      </View>
                    ))}
                  </View>
                ) : null}

                {/* Ingredients */}
                {ingredients.length > 0 ? (
                  <>
                    <Pressable onPress={() => toggleDish(dish.food_item_id)} style={s.ingredToggle}>
                      <Text style={s.ingredToggleText}>INGREDIENTS</Text>
                      <View style={isExpanded ? s.chevronOpen : undefined}>
                        <ChevronDown size={13} color="#9CA3AF" />
                      </View>
                    </Pressable>
                    {isExpanded && (
                      <View style={s.ingredList}>
                        {ingredients.map(ing => (
                          <View key={ing.name} style={s.ingredRow}>
                            <Text style={s.ingredName}>{ing.name}</Text>
                            <View style={s.ingredPill}>
                              <Text style={s.ingredPillText}>{gramsToLabel(ing.amount_g)}</Text>
                            </View>
                          </View>
                        ))}
                      </View>
                    )}
                  </>
                ) : !detailLoading ? (
                  <Text style={s.ingredPlaceholder}>Ingredient details coming soon</Text>
                ) : null}
              </View>
            );
          })
        )}
      </ScrollView>

      {/* Sticky confirm button */}
      <View style={s.footer}>
        {isThisComboConfirmed ? (
          <View style={[s.confirmBtn, s.confirmBtnConfirmed]}>
            <Text style={s.confirmBtnText}>✓ Already chosen — {bowlSize} bowl</Text>
          </View>
        ) : isOtherComboConfirmed ? (
          <View style={[s.confirmBtn, s.confirmBtnDisabled]}>
            <Text style={[s.confirmBtnText, { color: "#6B7280" }]}>Another combo chosen for {mealType}</Text>
          </View>
        ) : (
          <Pressable
            style={[s.confirmBtn, confirmMut.isPending && s.confirmBtnDisabled]}
            onPress={() => confirmMut.mutate()}
            disabled={confirmMut.isPending}
          >
            {confirmMut.isPending
              ? <ActivityIndicator color="#fff" />
              : <Text style={s.confirmBtnText}>Confirm this combo</Text>}
          </Pressable>
        )}
      </View>

    </View>
  );
}

const G  = "#1E7C45";
const GL = "#EDF7F1";
const GD = "#166534";
const BD = "#E8EDE8";
const BG = "#F8F9F6";

const s = StyleSheet.create({
  root:         { flex: 1, backgroundColor: BG },

  header:       { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 16, paddingTop: 52, paddingBottom: 14, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: BD },
  backBtn:      { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  headerCenter: { flex: 1, alignItems: "center" },
  headerType:   { fontSize: 12, fontWeight: "800", color: G, letterSpacing: 2 },
  headerSub:    { fontSize: 11, color: "#9CA3AF", marginTop: 2 },

  scroll:       { padding: 16, paddingBottom: 36 },

  doctorBadge:     { backgroundColor: "#FEF3C7", borderRadius: 10, paddingHorizontal: 14, paddingVertical: 8, marginBottom: 14, borderWidth: 1, borderColor: "#FDE68A" },
  doctorBadgeText: { fontSize: 13, color: "#92400E", fontWeight: "600" },

  bowlSection:  { backgroundColor: "#fff", borderRadius: 14, padding: 14, borderWidth: 1, borderColor: BD, marginBottom: 12 },
  sectionLabel: { fontSize: 10, fontWeight: "700", color: "#9CA3AF", letterSpacing: 1.5, marginBottom: 10 },
  pillRow:      { flexDirection: "row", gap: 10, marginBottom: 8 },
  pill:         { flex: 1, height: 40, borderRadius: 20, borderWidth: 1.5, borderColor: "#E5E7EB", alignItems: "center", justifyContent: "center", backgroundColor: "#F9FAFB" },
  pillSelected: { backgroundColor: G, borderColor: G },
  pillText:     { fontSize: 15, fontWeight: "700", color: "#374151" },
  pillTextSelected: { color: "#fff" },
  bowlHint:     { fontSize: 11, color: "#6B7280", textAlign: "center" },

  totalCard:    { backgroundColor: GL, borderRadius: 14, padding: 16, borderWidth: 1, borderColor: "#D1FAE5", marginBottom: 14, alignItems: "center" },
  totalLabel:   { fontSize: 9, fontWeight: "700", color: GD, letterSpacing: 1.5, marginBottom: 4 },
  totalRow:     { flexDirection: "row", alignItems: "baseline", gap: 3 },
  totalCal:     { fontSize: 42, fontWeight: "800", color: "#111827", lineHeight: 48 },
  totalUnit:    { fontSize: 14, color: "#6B7280", fontWeight: "500" },

  dishCard:     { backgroundColor: "#fff", borderRadius: 16, padding: 14, marginBottom: 10, borderWidth: 1, borderColor: BD },
  dishTop:      { flexDirection: "row", alignItems: "flex-start", marginBottom: 10 },
  dishName:     { fontSize: 15, fontWeight: "700", color: "#111827", lineHeight: 20, marginBottom: 5 },
  badgeRow:     { flexDirection: "row", flexWrap: "wrap", gap: 5 },
  slotTag:      { backgroundColor: GL, borderRadius: 99, paddingHorizontal: 8, paddingVertical: 2 },
  slotTagText:  { fontSize: 10, fontWeight: "600", color: GD, letterSpacing: 0.3 },
  pinBadge:     { backgroundColor: "#FEF3C7", borderRadius: 99, paddingHorizontal: 6, paddingVertical: 2 },
  pinBadgeText: { fontSize: 9, fontWeight: "600", color: "#92400E" },
  dishCalBlock: { alignItems: "flex-end" },
  dishCal:      { fontSize: 22, fontWeight: "800", color: "#111827", lineHeight: 26 },
  dishCalUnit:  { fontSize: 10, color: "#9CA3AF", marginTop: 1 },

  macroPills:      { flexDirection: "row", gap: 6, marginBottom: 10 },
  macroPill:       { flex: 1, backgroundColor: BG, borderRadius: 8, paddingVertical: 6, alignItems: "center", borderWidth: 1, borderColor: BD },
  macroPillVal:    { fontSize: 11, fontWeight: "700", color: "#374151" },
  macroPillLabel:  { fontSize: 9, color: "#9CA3AF", marginTop: 1, fontWeight: "600" },

  ingredToggle:     { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingTop: 8, borderTopWidth: 1, borderTopColor: "#F3F4F6" },
  ingredToggleText: { fontSize: 10, fontWeight: "700", color: "#9CA3AF", letterSpacing: 1 },
  chevronOpen:      { transform: [{ rotate: "180deg" }] },
  ingredList:       { paddingTop: 8 },
  ingredRow:        { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 4, borderTopWidth: 1, borderTopColor: "#F9FAFB" },
  ingredName:       { fontSize: 12, color: "#374151", flex: 1, marginRight: 8 },
  ingredPill:       { backgroundColor: "#F3F4F6", borderRadius: 99, paddingHorizontal: 8, paddingVertical: 2 },
  ingredPillText:   { fontSize: 10, color: "#6B7280", fontWeight: "500" },
  ingredPlaceholder:{ fontSize: 11, color: "#9CA3AF", marginTop: 6, fontStyle: "italic" },

  footer:              { padding: 16, paddingBottom: 32, borderTopWidth: 1, borderTopColor: BD, backgroundColor: "#fff" },
  confirmBtn:          { height: 52, borderRadius: 26, backgroundColor: G, alignItems: "center", justifyContent: "center" },
  confirmBtnConfirmed: { backgroundColor: GD },
  confirmBtnDisabled:  { backgroundColor: "#E5E7EB" },
  confirmBtnText:      { fontSize: 15, fontWeight: "700", color: "#fff", letterSpacing: 0.3 },
});
