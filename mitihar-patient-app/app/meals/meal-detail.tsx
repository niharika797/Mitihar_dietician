import React, { useState, useRef, useEffect } from "react";
import {
  View, Text, ScrollView, Pressable, StyleSheet,
  ActivityIndicator, Animated, LayoutAnimation, UIManager, Platform,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { ChevronLeft, ThumbsUp, ThumbsDown, ChevronDown } from "lucide-react-native";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { getWeeklyPlan } from "../../services/meals";
import { logMeal, rateMeal, getMyRatings, MealRating } from "../../services/progress";
import { useToast } from "../../components/shared";
import type { Meal, Dish, WeeklyPlan } from "../../types";

if (Platform.OS === "android") {
  UIManager.setLayoutAnimationEnabledExperimental?.(true);
}

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

// ── DishCard ─────────────────────────────────────────────────────────────────

interface DishCardProps {
  dish: Dish;
  index: number;
  rating: 1 | -1 | null;
  onRate: (food_id: number, r: 1 | -1) => void;
  ratingPending: boolean;
}

function DishCard({ dish, index, rating, onRate, ratingPending }: DishCardProps) {
  const [expanded, setExpanded] = useState(false);
  const fade  = useRef(new Animated.Value(0)).current;
  const slide = useRef(new Animated.Value(14)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fade,  { toValue: 1, duration: 380, delay: index * 100, useNativeDriver: true }),
      Animated.timing(slide, { toValue: 0, duration: 380, delay: index * 100, useNativeDriver: true }),
    ]).start();
  }, []);

  const toggleExpand = () => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setExpanded(p => !p);
  };

  const hasIngredients = (dish.ingredients?.length ?? 0) > 0;

  return (
    <Animated.View style={[s.dishCard, { opacity: fade, transform: [{ translateY: slide }] }]}>

      {/* Tapping name/macros area collapses/expands if ingredients present */}
      <Pressable onPress={hasIngredients ? toggleExpand : undefined} style={{ marginBottom: 12 }}>
        <View style={s.dishTop}>
          <View style={{ flex: 1, marginRight: 10 }}>
            <Text style={s.dishName}>{dish.recipe_name}</Text>
            <View style={s.slotTag}>
              <Text style={s.slotTagText}>
                {SLOT_LABELS[dish.slot_type] ?? dish.slot_type}
              </Text>
            </View>
          </View>
          <View style={s.dishCalBlock}>
            {/* Session 22E (F4): scaled per-serving kcal, matches the scaled
                ingredient grams shown below. Falls back to unscaled for legacy dishes. */}
            <Text style={s.dishCal}>{Math.round(dish.scaled_calories ?? dish.calories)}</Text>
            <Text style={s.dishCalUnit}>kcal</Text>
          </View>
        </View>

        <View style={s.macroPills}>
          {[
            { label: "P",  val: dish.protein },
            { label: "C",  val: dish.carbs },
            { label: "F",  val: dish.fat },
            { label: "Fi", val: dish.fiber },
          ].map(m => (
            <View key={m.label} style={s.macroPill}>
              <Text style={s.macroPillVal}>{Math.round(m.val)}g</Text>
              <Text style={s.macroPillLabel}>{m.label}</Text>
            </View>
          ))}
        </View>
      </Pressable>

      {/* Rating — always visible */}
      <View style={s.ratingRow}>
        <Text style={s.ratingPrompt}>How was it?</Text>
        <View style={s.ratingBtns}>
          <Pressable
            onPress={() => onRate(dish.food_id, 1)}
            disabled={ratingPending}
            style={[s.rateBtn, rating === 1 && s.rateBtnLiked]}
            hitSlop={10}
          >
            <ThumbsUp size={15} color={rating === 1 ? "#fff" : "#1E7C45"} strokeWidth={2.2} />
          </Pressable>
          <Pressable
            onPress={() => onRate(dish.food_id, -1)}
            disabled={ratingPending}
            style={[s.rateBtn, rating === -1 && s.rateBtnDisliked]}
            hitSlop={10}
          >
            <ThumbsDown size={15} color={rating === -1 ? "#fff" : "#DC2626"} strokeWidth={2.2} />
          </Pressable>
        </View>
      </View>

      {/* Ingredients — expandable, only if data present */}
      {hasIngredients && (
        <>
          <Pressable onPress={toggleExpand} style={s.ingredsToggle}>
            <Text style={s.ingredsToggleText}>INGREDIENTS</Text>
            <View style={expanded ? s.chevronOpen : undefined}>
              <ChevronDown size={13} color="#9CA3AF" />
            </View>
          </Pressable>

          {expanded && (
            <View style={s.ingredsList}>
              {dish.ingredients!.map(({ name, amount_g }) => (
                <View key={name} style={s.ingredRow}>
                  <Text style={s.ingredName}>{name}</Text>
                  <View style={s.ingredLabelPill}>
                    <Text style={s.ingredLabelText}>{gramsToLabel(amount_g)}</Text>
                  </View>
                </View>
              ))}
            </View>
          )}
        </>
      )}
    </Animated.View>
  );
}

// ── Screen ────────────────────────────────────────────────────────────────────

export default function MealDetailScreen() {
  const router = useRouter();
  const { date, type } = useLocalSearchParams<{ date: string; type: string }>();
  const qc = useQueryClient();
  const { showToast } = useToast();

  const [logged, setLogged]             = useState(false);
  const [localRatings, setLocalRatings] = useState<Record<number, 1 | -1>>({});

  const { data: plan, isLoading } = useQuery({
    queryKey: QUERY_KEYS.WEEK_PLAN,
    queryFn: getWeeklyPlan,
  });

  const meal: Meal | undefined = (plan as WeeklyPlan | undefined)?.[date ?? ""]?.find(m => m["Meal Type"] === type);

  const { data: allRatings = [] } = useQuery({
    queryKey: QUERY_KEYS.MY_RATINGS,
    queryFn: getMyRatings,
    staleTime: 1000 * 60 * 5,
  });

  const serverRatings = React.useMemo<Record<number, 1 | -1>>(
    () => Object.fromEntries((allRatings as MealRating[]).map(r => [r.food_item_id, r.rating as 1 | -1])),
    [allRatings]
  );

  const logMut = useMutation({
    mutationFn: () =>
      logMeal({
        meal_type: meal!["Meal Type"],
        calories:  meal!["Total Calories"],
        protein:   meal!["Total Protein"],
        carbs:     meal!["Total Carbs"],
        fat:       meal!["Total Fat"],
        fiber:     meal!["Total Fiber"],
      }),
    onSuccess: () => {
      setLogged(true);
      qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
      setTimeout(() => router.back(), 1400);
    },
    onError: () => showToast("Failed to log meal", "error"),
  });

  const rateMut = useMutation({
    mutationFn: ({ food_id, rating }: { food_id: number; rating: 1 | -1 }) =>
      rateMeal(food_id, rating, (meal as any)?.recommendation_id ?? null),
    onMutate: ({ food_id, rating }) => {
      setLocalRatings(p => ({ ...p, [food_id]: rating }));
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.MY_RATINGS });
      showToast("Feedback saved 👍", "success");
    },
    onError: () => showToast("Could not save feedback", "error"),
  });

  if (isLoading) {
    return (
      <View style={s.loader}>
        <ActivityIndicator size="large" color="#1E7C45" />
      </View>
    );
  }

  if (!meal) {
    return (
      <View style={s.loader}>
        <Text style={s.notFoundText}>Meal not found</Text>
        <Pressable onPress={() => router.back()} style={s.backLink}>
          <Text style={s.backLinkText}>← Go back</Text>
        </Pressable>
      </View>
    );
  }

  const dishes: Dish[] = meal.dishes ?? [];

  return (
    <View style={s.root}>

      {/* ── Header ───────────────────────────────────────────────────────── */}
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <View style={s.headerCenter}>
          <Text style={s.headerType}>{(meal["Meal Type"] ?? "").toUpperCase()}</Text>
          <Text style={s.headerCal}>{Math.round(meal["Total Calories"])} kcal total</Text>
        </View>
        <View style={{ width: 36 }} />
      </View>

      {/* ── Scroll ───────────────────────────────────────────────────────── */}
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>

        {dishes.length > 0 ? (
          dishes.map((dish, i) => {
            const rating = localRatings[dish.food_id] ?? (serverRatings[dish.food_id] ?? null);
            return (
              <DishCard
                key={dish.food_id}
                dish={dish}
                index={i}
                rating={rating}
                onRate={(fid, r) => rateMut.mutate({ food_id: fid, rating: r })}
                ratingPending={rateMut.isPending}
              />
            );
          })
        ) : (
          /* Legacy fallback: plan without dishes[] */
          <View style={s.dishCard}>
            <Text style={s.dishName}>{meal["Menu Names"]}</Text>
            <View style={s.macroPills}>
              {[
                { label: "P",  val: meal["Total Protein"] },
                { label: "C",  val: meal["Total Carbs"] },
                { label: "F",  val: meal["Total Fat"] },
                { label: "Fi", val: meal["Total Fiber"] },
              ].map(m => (
                <View key={m.label} style={s.macroPill}>
                  <Text style={s.macroPillVal}>{Math.round(m.val)}g</Text>
                  <Text style={s.macroPillLabel}>{m.label}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* Combined nutrition summary */}
        <View style={s.summaryCard}>
          <Text style={s.summaryHeading}>TOTAL FOR THIS MEAL</Text>
          <View style={s.summaryRow}>
            {[
              { label: "Calories", val: `${Math.round(meal["Total Calories"])}`, unit: "kcal" },
              { label: "Protein",  val: `${Math.round(meal["Total Protein"])}`,  unit: "g" },
              { label: "Carbs",    val: `${Math.round(meal["Total Carbs"])}`,    unit: "g" },
              { label: "Fat",      val: `${Math.round(meal["Total Fat"])}`,      unit: "g" },
              { label: "Fiber",    val: `${Math.round(meal["Total Fiber"])}`,    unit: "g" },
            ].map(({ label, val, unit }) => (
              <View key={label} style={s.summaryItem}>
                <View style={s.summaryValRow}>
                  <Text style={s.summaryVal}>{val}</Text>
                  <Text style={s.summaryUnit}>{unit}</Text>
                </View>
                <Text style={s.summaryLabel}>{label}</Text>
              </View>
            ))}
          </View>
        </View>

        {meal.doctor_note && (
          <View style={s.noteCard}>
            <Text style={s.noteHeading}>📝 Doctor's Note</Text>
            <Text style={s.noteText}>"{meal.doctor_note}"</Text>
          </View>
        )}

      </ScrollView>

      {/* ── Sticky footer ────────────────────────────────────────────────── */}
      <View style={s.footer}>
        {logged ? (
          <View style={s.loggedBanner}>
            <Text style={s.loggedText}>✅ Logged!</Text>
          </View>
        ) : (
          <Pressable
            style={s.primaryBtn}
            onPress={() => logMut.mutate()}
            disabled={logMut.isPending}
          >
            {logMut.isPending
              ? <ActivityIndicator color="#fff" />
              : <Text style={s.primaryBtnText}>✅  I Had This</Text>}
          </Pressable>
        )}
      </View>

    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const G  = "#1E7C45";
const GL = "#EDF7F1";
const GD = "#166534";
const BD = "#E8EDE8";
const BG = "#F8F9F6";

const s = StyleSheet.create({
  root:         { flex: 1, backgroundColor: BG },
  loader:       { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: BG },
  notFoundText: { fontSize: 15, color: "#6B7280" },
  backLink:     { marginTop: 8 },
  backLinkText: { color: G, fontSize: 14 },

  // Header
  header:       { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 16, paddingTop: 52, paddingBottom: 14, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: BD },
  backBtn:      { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  headerCenter: { flex: 1, alignItems: "center" },
  headerType:   { fontSize: 12, fontWeight: "800", color: G, letterSpacing: 2.5 },
  headerCal:    { fontSize: 11, color: "#9CA3AF", marginTop: 2 },

  // Scroll
  scroll: { padding: 16, paddingBottom: 36 },

  // Dish card
  dishCard: {
    backgroundColor: "#fff",
    borderRadius: 18,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: BD,
    shadowColor: "#1A6B3A",
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.07,
    shadowRadius: 10,
    elevation: 3,
  },
  dishTop:     { flexDirection: "row", alignItems: "flex-start", marginBottom: 12 },
  dishName:    { fontSize: 17, fontWeight: "700", color: "#111827", lineHeight: 23, marginBottom: 5 },
  slotTag:     { alignSelf: "flex-start", backgroundColor: GL, borderRadius: 99, paddingHorizontal: 8, paddingVertical: 2 },
  slotTagText: { fontSize: 10, fontWeight: "600", color: GD, letterSpacing: 0.4 },
  dishCalBlock:{ alignItems: "flex-end" },
  dishCal:     { fontSize: 26, fontWeight: "800", color: "#111827", lineHeight: 30 },
  dishCalUnit: { fontSize: 10, color: "#9CA3AF", marginTop: 2 },

  // Macro pills
  macroPills:     { flexDirection: "row", gap: 6 },
  macroPill:      { flex: 1, backgroundColor: BG, borderRadius: 10, paddingVertical: 7, alignItems: "center", borderWidth: 1, borderColor: BD },
  macroPillVal:   { fontSize: 12, fontWeight: "700", color: "#374151" },
  macroPillLabel: { fontSize: 9, color: "#9CA3AF", marginTop: 1, fontWeight: "600" },

  // Rating row
  ratingRow:       { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 12, borderTopWidth: 1, borderTopColor: "#F3F4F6" },
  ratingPrompt:    { fontSize: 11, color: "#9CA3AF", fontWeight: "500" },
  ratingBtns:      { flexDirection: "row", gap: 8 },
  rateBtn:         { width: 38, height: 38, borderRadius: 19, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#F9FAFB", alignItems: "center", justifyContent: "center" },
  rateBtnLiked:    { backgroundColor: G, borderColor: G },
  rateBtnDisliked: { backgroundColor: "#DC2626", borderColor: "#DC2626" },

  // Per-dish ingredients
  ingredsToggle:     { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingTop: 10, borderTopWidth: 1, borderTopColor: "#F3F4F6" },
  ingredsToggleText: { fontSize: 10, fontWeight: "700", color: "#9CA3AF", letterSpacing: 1 },
  chevronOpen:       { transform: [{ rotate: "180deg" }] },
  ingredsList:       { paddingTop: 8 },
  ingredRow:         { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 5, borderTopWidth: 1, borderTopColor: "#F9FAFB" },
  ingredName:        { fontSize: 12, color: "#374151", flex: 1, marginRight: 8 },
  ingredLabelPill:   { backgroundColor: "#F3F4F6", borderRadius: 99, paddingHorizontal: 8, paddingVertical: 2 },
  ingredLabelText:   { fontSize: 10, color: "#6B7280", fontWeight: "500" },

  // Summary card
  summaryCard:    { backgroundColor: GL, borderRadius: 16, padding: 16, borderWidth: 1, borderColor: "#D1FAE5", marginBottom: 12 },
  summaryHeading: { fontSize: 9, fontWeight: "700", color: GD, letterSpacing: 1.5, marginBottom: 12 },
  summaryRow:     { flexDirection: "row", justifyContent: "space-between" },
  summaryItem:    { alignItems: "center" },
  summaryValRow:  { flexDirection: "row", alignItems: "baseline", gap: 1 },
  summaryVal:     { fontSize: 14, fontWeight: "800", color: "#111827" },
  summaryUnit:    { fontSize: 9, color: "#6B7280", fontWeight: "500" },
  summaryLabel:   { fontSize: 9, color: "#6B7280", marginTop: 3, fontWeight: "500" },

  // Doctor note
  noteCard:    { backgroundColor: "#FFFBEB", borderRadius: 16, padding: 14, borderWidth: 1, borderColor: "#FDE68A", marginBottom: 12 },
  noteHeading: { fontSize: 11, fontWeight: "700", color: "#92400E", marginBottom: 6 },
  noteText:    { fontSize: 13, color: "#78350F", lineHeight: 20, fontStyle: "italic" },

  // Footer
  footer:         { padding: 16, paddingBottom: 32, borderTopWidth: 1, borderTopColor: BD, backgroundColor: "#fff" },
  primaryBtn:     { height: 52, borderRadius: 26, backgroundColor: G, alignItems: "center", justifyContent: "center" },
  primaryBtnText: { fontSize: 16, fontWeight: "700", color: "#fff", letterSpacing: 0.3 },
  loggedBanner:   { height: 52, borderRadius: 26, backgroundColor: GL, alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: "#D1FAE5" },
  loggedText:     { fontSize: 16, fontWeight: "600", color: GD },
});
