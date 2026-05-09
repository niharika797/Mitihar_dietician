import React, { useState } from "react";
import { View, Text, TextInput, Pressable, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import { AlertTriangle, Check } from "lucide-react-native";
import { OnboardingShell, ChipGrid } from "../../components/shared";
import { useOnboardingStore } from "../../store/useOnboardingStore";

const ALLERGIES = ["Dairy / Lactose","Gluten / Wheat","Tree Nuts","Shellfish / Fish","Eggs","Soy","Nightshades","Peanuts"];

export default function AllergiesScreen() {
  const router = useRouter();
  const { data, update } = useOnboardingStore();
  const [allergies, setAllergies] = useState<string[]>(data.food_allergies ?? []);
  const [other, setOther] = useState("");

  const toggle = (a: string) => {
    if (a === "None") { setAllergies(["None"]); return; }
    setAllergies(prev => prev.includes(a) ? prev.filter(x => x !== a) : [...prev.filter(x => x !== "None"), a]);
  };

  const canContinue = allergies.length > 0 || other.trim().length > 0;

  const handleContinue = () => {
    const final = other.trim() ? [...allergies, other.trim()] : allergies;
    update({ food_allergies: final });
    router.push("/(onboarding)/dietary-preferences");
  };

  const noneSelected = allergies.includes("None");

  return (
    <OnboardingShell step={5} totalSteps={8} title="Food Allergies & Intolerances" onContinue={handleContinue} continueDisabled={!canContinue}>
      <View style={s.form}>
        {/* Warning */}
        <View style={s.warning}>
          <AlertTriangle size={16} color="#B45309" />
          <Text style={s.warningText}>
            <Text style={{ fontWeight: "700" }}>This is mandatory</Text>
            {" — affects your meal plan's safety. Select all that apply, including 'None' if clear."}
          </Text>
        </View>

        <ChipGrid options={ALLERGIES} selected={allergies} onToggle={toggle} columns={2} />

        {/* Other text input */}
        <View style={s.field}>
          <Text style={s.label}>Other (specify)</Text>
          <TextInput
            style={s.input} placeholder="e.g. Mustard, Sesame..."
            value={other} onChangeText={setOther}
          />
        </View>

        {/* None */}
        <Pressable onPress={() => toggle("None")} style={[s.noneBtn, noneSelected && s.noneBtnSel]}>
          {noneSelected && <Check size={14} color="#166534" />}
          <Text style={[s.noneText, noneSelected && s.noneTextSel]}>✓ None of the above</Text>
        </Pressable>
      </View>
    </OnboardingShell>
  );
}

const s = StyleSheet.create({
  form:         { gap: 16 },
  warning:      { flexDirection: "row", gap: 10, alignItems: "flex-start", backgroundColor: "#FFFBEB", borderWidth: 1, borderColor: "#FCD34D", borderRadius: 8, padding: 12 },
  warningText:  { flex: 1, fontSize: 12, color: "#92400E", lineHeight: 18 },
  field:        { gap: 6 },
  label:        { fontSize: 14, fontWeight: "500", color: "#374151" },
  input:        { height: 52, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", paddingHorizontal: 16, fontSize: 14, color: "#111827", backgroundColor: "#fff" },
  noneBtn:      { height: 48, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6 },
  noneBtnSel:   { borderColor: "#1E7C45", backgroundColor: "#DCFCE7" },
  noneText:     { fontSize: 14, fontWeight: "500", color: "#374151" },
  noneTextSel:  { color: "#166534" },
});
