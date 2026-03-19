import React, { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import { Check } from "lucide-react-native";
import { OnboardingShell } from "../../components/shared";
import { useOnboardingStore } from "../../store/useOnboardingStore";

const DIET_TYPES = [
  { key: "Vegetarian",     emoji: "🥗", label: "Vegetarian only" },
  { key: "Eggetarian",     emoji: "🥚", label: "Vegetarian + Eggs (Eggetarian)" },
  { key: "Non-Vegetarian", emoji: "🍗", label: "Non-Vegetarian (Chicken, Fish, Eggs etc.)" },
];
const REGIONS = [
  { key: "North", emoji: "🫓", label: "North Indian" },
  { key: "South", emoji: "🍛", label: "South Indian" },
  { key: "East",  emoji: "🐟", label: "East Indian"  },
  { key: "West",  emoji: "🥘", label: "West Indian"  },
];
const DAYS = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"];

export default function DietaryPreferencesScreen() {
  const router = useRouter();
  const { data, update } = useOnboardingStore();

  const [dietType,           setDietType]           = useState(data.diet_type || "Vegetarian");
  const [nonvegMealsPerWeek, setNonvegMealsPerWeek] = useState(data.nonveg_meals_per_week || 0);
  const [region,             setRegion]             = useState(data.region    || "North");
  const [meals,        setMeals]        = useState(data.meals_per_day || "3");
  const [fastingDays,  setFastingDays]  = useState<string[]>(data.fasting_days ?? []);

  const toggleDay = (d: string) =>
    setFastingDays(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]);

  const handleContinue = () => {
    update({ 
      diet_type: dietType, 
      region, 
      meals_per_day: meals, 
      fasting_days: fastingDays,
      nonveg_meals_per_week: nonvegMealsPerWeek 
    });
    router.push("/(onboarding)/lifestyle");
  };

  return (
    <OnboardingShell step={6} totalSteps={8} title="Dietary Preferences" onContinue={handleContinue} onSkip={() => router.push("/(onboarding)/lifestyle")}>
      <View style={s.form}>
        {/* Diet type */}
        <View>
          <Text style={s.sectionLabel}>Diet Type</Text>
          <View style={s.dietList}>
            {DIET_TYPES.map(dt => {
              const sel = dietType === dt.key;
              return (
                <Pressable 
                  key={dt.key} 
                  onPress={() => {
                    setDietType(dt.key);
                    if (dt.key !== "Non-Vegetarian") setNonvegMealsPerWeek(0);
                  }} 
                  style={[s.dietCard, sel && s.dietCardSel]}
                >
                  <Text style={s.dietEmoji}>{dt.emoji}</Text>
                  <Text style={s.dietLabel}>{dt.label}</Text>
                  {sel && <Check size={18} color="#1E7C45" style={{ marginLeft: "auto" }} />}
                </Pressable>
              );
            })}
          </View>
        </View>

        {/* Non-veg meals count follow-up */}
        {dietType === "Non-Vegetarian" && (
          <View>
            <Text style={s.sectionLabel}>How many non-veg meals per week?</Text>
            <View style={s.numRow}>
              {[1, 2, 3, 4, 5].map(num => {
                const sel = nonvegMealsPerWeek === num;
                return (
                  <Pressable 
                    key={num} 
                    onPress={() => setNonvegMealsPerWeek(num)} 
                    style={[s.numBtn, sel && s.numBtnSel]}
                  >
                    <Text style={[s.numBtnText, sel && s.numBtnTextSel]}>
                      {num === 5 ? "5+" : num}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
          </View>
        )}

        {/* Region */}
        <View>
          <Text style={s.sectionLabel}>Regional Preference</Text>
          <View style={s.regionGrid}>
            {REGIONS.map(r => {
              const sel = region === r.key;
              return (
                <Pressable key={r.key} onPress={() => setRegion(r.key)} style={[s.regionBtn, sel && s.regionBtnSel]}>
                  <Text style={s.regionEmoji}>{r.emoji}</Text>
                  <Text style={[s.regionText, sel && s.regionTextSel]}>{r.label}</Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        {/* Meals per day */}
        <View>
          <Text style={s.sectionLabel}>Meals Per Day</Text>
          <View style={s.mealsRow}>
            {[{ v: "3", l: "3 meals" }, { v: "5", l: "5 meals (with snacks)" }].map(o => (
              <Pressable key={o.v} onPress={() => setMeals(o.v)} style={[s.mealBtn, meals === o.v && s.mealBtnSel]}>
                <Text style={[s.mealText, meals === o.v && s.mealTextSel]}>{o.l}</Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* Fasting days */}
        <View>
          <Text style={s.sectionLabel}>Fasting Days <Text style={s.optional}>(optional)</Text></Text>
          <View style={s.daysRow}>
            {DAYS.map(d => {
              const sel = fastingDays.includes(d);
              return (
                <Pressable key={d} onPress={() => toggleDay(d)} style={[s.dayBtn, sel && s.dayBtnSel]}>
                  <Text style={[s.dayText, sel && s.dayTextSel]}>{d[0]}</Text>
                </Pressable>
              );
            })}
            <Pressable onPress={() => setFastingDays([])} style={[s.noneDay, fastingDays.length === 0 && s.noneDaySel]}>
              <Text style={s.noneDayText}>None</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </OnboardingShell>
  );
}

const s = StyleSheet.create({
  form:          { gap: 22 },
  sectionLabel:  { fontSize: 14, fontWeight: "500", color: "#374151", marginBottom: 10 },
  optional:      { fontWeight: "400", color: "#9CA3AF" },
  dietList:      { gap: 8 },
  dietCard:      { flexDirection: "row", alignItems: "center", gap: 12, padding: 12, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff" },
  dietCardSel:   { borderColor: "#23924F", backgroundColor: "#F0FDF4" },
  dietEmoji:     { fontSize: 20 },
  dietLabel:     { fontSize: 15, fontWeight: "500", color: "#111827" },
  regionGrid:    { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  regionBtn:     { flexBasis: "47%", height: 52, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6 },
  regionBtnSel:  { borderColor: "#23924F", backgroundColor: "#F0FDF4" },
  regionEmoji:   { fontSize: 18 },
  regionText:    { fontSize: 13, fontWeight: "500", color: "#111827" },
  regionTextSel: { color: "#1E7C45" },
  mealsRow:      { flexDirection: "row", gap: 8 },
  mealBtn:       { flex: 1, height: 48, borderRadius: 10, borderWidth: 1.5, borderColor: "#D1D5DB", alignItems: "center", justifyContent: "center", backgroundColor: "#fff" },
  mealBtnSel:    { borderColor: "#1E7C45", backgroundColor: "#1E7C45" },
  mealText:      { fontSize: 13, fontWeight: "500", color: "#374151" },
  mealTextSel:   { color: "#fff" },
  daysRow:       { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  dayBtn:        { width: 44, height: 44, borderRadius: 22, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  dayBtnSel:     { borderColor: "#1E7C45", backgroundColor: "#1E7C45" },
  dayText:       { fontSize: 13, fontWeight: "500", color: "#374151" },
  dayTextSel:    { color: "#fff" },
  noneDay:       { height: 44, paddingHorizontal: 14, borderRadius: 22, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  noneDaySel:    { backgroundColor: "#F3F4F6" },
  noneDayText:   { fontSize: 13, fontWeight: "500", color: "#374151" },
  numRow:        { flexDirection: "row", gap: 8 },
  numBtn:        { flex: 1, height: 44, borderRadius: 10, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  numBtnSel:     { borderColor: "#1E7C45", backgroundColor: "#F0FDF4" },
  numBtnText:    { fontSize: 14, fontWeight: "600", color: "#374151" },
  numBtnTextSel: { color: "#1E7C45" },
});
