import React, { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import Slider from "@react-native-community/slider";
import { useRouter } from "expo-router";
import { Minus, Plus } from "lucide-react-native";
import { Picker } from "@react-native-picker/picker";
import { OnboardingShell, ChipGrid, Toggle } from "../../components/shared";
import { useOnboardingStore } from "../../store/useOnboardingStore";

const HABITS      = ["Skips Breakfast","Late Night Eating","Irregular Meals","Eats Quickly","Large Portions","Stress Eating"];
const OCCUPATIONS = ["Desk job","Manual labor","Standing job","Mixed"];

export default function LifestyleScreen() {
  const router = useRouter();
  const { data, update } = useOnboardingStore();

  const [sleep,      setSleep]      = useState(data.sleep_hours    ?? 7);
  const [water,      setWater]      = useState(data.water_glasses  ?? 8);
  const [occupation, setOccupation] = useState(data.occupation     || "Desk job");
  const [smoking,    setSmoking]    = useState(data.smoking        ?? false);
  const [alcohol,    setAlcohol]    = useState(data.alcohol        ?? false);
  const [habits,     setHabits]     = useState<string[]>(data.eating_habits ?? []);

  const toggleHabit = (h: string) =>
    setHabits(prev => prev.includes(h) ? prev.filter(x => x !== h) : [...prev, h]);

  const handleContinue = () => {
    update({ sleep_hours: sleep, water_glasses: water, occupation, smoking, alcohol, eating_habits: habits });
    router.push("/(onboarding)/disclaimer");
  };

  return (
    <OnboardingShell step={7} totalSteps={8} title="Your Lifestyle" onContinue={handleContinue} onSkip={() => router.push("/(onboarding)/disclaimer")}>
      <View style={s.form}>
        {/* Sleep */}
        <View>
          <View style={s.rowBetween}>
            <Text style={s.label}>Sleep Hours per Night</Text>
            <Text style={s.valueText}>{sleep} hrs</Text>
          </View>
          <Slider
            minimumValue={4} maximumValue={10} step={0.5}
            value={sleep} onValueChange={setSleep}
            minimumTrackTintColor="#1E7C45" maximumTrackTintColor="#E5E7EB"
            thumbTintColor="#1E7C45"
            style={{ marginTop: 4 }}
          />
          <View style={s.rowBetween}>
            <Text style={s.rangeText}>4 hrs</Text>
            <Text style={s.rangeText}>10 hrs</Text>
          </View>
        </View>

        {/* Water */}
        <View>
          <Text style={s.label}>Daily Water Intake (glasses)</Text>
          <View style={s.counterRow}>
            <Pressable onPress={() => setWater(Math.max(1, water - 1))} style={s.counterBtn}>
              <Minus size={18} color="#fff" />
            </Pressable>
            <Text style={s.counterVal}>{water}</Text>
            <Pressable onPress={() => setWater(Math.min(20, water + 1))} style={s.counterBtn}>
              <Plus size={18} color="#fff" />
            </Pressable>
          </View>
        </View>

        {/* Occupation */}
        <View>
          <Text style={s.label}>Occupation Type</Text>
          <View style={s.pickerWrap}>
            <Picker selectedValue={occupation} onValueChange={setOccupation} style={s.picker}>
              {OCCUPATIONS.map(o => <Picker.Item key={o} label={o} value={o} />)}
            </Picker>
          </View>
        </View>

        {/* Smoking / Alcohol toggles */}
        {[
          { label: "Smoking", value: smoking, set: setSmoking },
          { label: "Alcohol", value: alcohol, set: setAlcohol },
        ].map(item => (
          <View key={item.label} style={s.toggleRow}>
            <Text style={s.toggleLabel}>{item.label}</Text>
            <Toggle value={item.value} onToggle={item.set} />
          </View>
        ))}

        {/* Eating habits */}
        <View>
          <Text style={s.label}>Eating Habits</Text>
          <ChipGrid options={HABITS} selected={habits} onToggle={toggleHabit} columns={2} small />
        </View>
      </View>
    </OnboardingShell>
  );
}

const s = StyleSheet.create({
  form:        { gap: 22 },
  label:       { fontSize: 14, fontWeight: "500", color: "#374151" },
  rowBetween:  { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  valueText:   { fontSize: 16, fontWeight: "600", color: "#1E7C45" },
  rangeText:   { fontSize: 11, color: "#9CA3AF" },
  counterRow:  { flexDirection: "row", alignItems: "center", gap: 20, marginTop: 8 },
  counterBtn:  { width: 44, height: 44, borderRadius: 22, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  counterVal:  { fontSize: 28, fontWeight: "700", color: "#111827", minWidth: 40, textAlign: "center" },
  pickerWrap:  { borderWidth: 1.5, borderColor: "#E5E7EB", borderRadius: 12, overflow: "hidden" },
  picker:      { height: 52 },
  toggleRow:   { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  toggleLabel: { fontSize: 14, fontWeight: "500", color: "#111827" },
});
