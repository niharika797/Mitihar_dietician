import React, { useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import { Check } from "lucide-react-native";
import { OnboardingShell, ChipGrid, Toggle } from "../../components/shared";
import { useOnboardingStore } from "../../store/useOnboardingStore";

const CONDITIONS = [
  "Type 2 Diabetes","Pre-diabetes","Hypertension","High Cholesterol",
  "PCOS/PCOD","Hypothyroidism","Hyperthyroidism","Heart Disease",
  "Kidney Disease","Fatty Liver","IBS/IBD","Celiac Disease",
  "Osteoporosis","Anemia","Gout",
];

export default function MedicalConditionsScreen() {
  const router = useRouter();
  const { data, update } = useOnboardingStore();
  const [conditions, setConditions] = useState<string[]>(data.medical_conditions ?? []);
  const [onMeds, setOnMeds] = useState(false);

  const toggle = (c: string) => {
    if (c === "None of the above") { setConditions(["None of the above"]); return; }
    setConditions(prev =>
      prev.includes(c) ? prev.filter(x => x !== c) : [...prev.filter(x => x !== "None of the above"), c]
    );
  };

  const handleContinue = () => {
    update({ medical_conditions: conditions });
    router.push("/(onboarding)/allergies");
  };

  const noneSelected = conditions.includes("None of the above");

  return (
    <OnboardingShell step={4} totalSteps={8} title="Medical Conditions" subtitle="Select all that apply" onContinue={handleContinue} continueDisabled={conditions.length === 0} onSkip={() => router.push("/(onboarding)/allergies")}>
      <View style={s.form}>
        <ChipGrid options={CONDITIONS} selected={conditions} onToggle={toggle} columns={2} small />

        {/* None of the above — full width */}
        <Pressable onPress={() => toggle("None of the above")} style={[s.noneBtn, noneSelected && s.noneBtnSel]}>
          {noneSelected && <Check size={14} color="#166534" />}
          <Text style={[s.noneText, noneSelected && s.noneTextSel]}>None of the above</Text>
        </Pressable>

        {/* Medication toggle */}
        <View style={s.medRow}>
          <View style={s.medInfo}>
            <Text style={s.medTitle}>Currently on medication?</Text>
            <Text style={s.medSub}>Helps us tailor recommendations</Text>
          </View>
          <Toggle value={onMeds} onToggle={setOnMeds} />
        </View>
      </View>
    </OnboardingShell>
  );
}

const s = StyleSheet.create({
  form:         { gap: 16 },
  noneBtn:      { height: 48, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6 },
  noneBtnSel:   { borderColor: "#1E7C45", backgroundColor: "#DCFCE7" },
  noneText:     { fontSize: 14, fontWeight: "500", color: "#374151" },
  noneTextSel:  { color: "#166534" },
  medRow:       { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 14, backgroundColor: "#F9FAFB", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB" },
  medInfo:      { flex: 1 },
  medTitle:     { fontSize: 14, fontWeight: "500", color: "#111827" },
  medSub:       { fontSize: 12, color: "#6B7280" },
});
