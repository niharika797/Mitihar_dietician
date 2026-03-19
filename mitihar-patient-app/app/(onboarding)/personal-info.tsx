import React, { useState } from "react";
import { View, Text, TextInput, Pressable, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import { Picker } from "@react-native-picker/picker";
import { OnboardingShell } from "../../components/shared";
import { useOnboardingStore } from "../../store/useOnboardingStore";

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const DAYS   = Array.from({ length: 31 }, (_, i) => String(i + 1));
const YEARS  = Array.from({ length: 60 }, (_, i) => String(2006 - i));

export default function PersonalInfoScreen() {
  const router = useRouter();
  const { data, update } = useOnboardingStore();

  const [day,    setDay]    = useState(data.dob_day);
  const [month,  setMonth]  = useState(data.dob_month);
  const [year,   setYear]   = useState(data.dob_year);
  const [gender, setGender] = useState(data.gender);
  const [height, setHeight] = useState(data.height_cm);
  const [weight, setWeight] = useState(data.weight_kg);
  const [target, setTarget] = useState(data.target_weight_kg);

  const canContinue = !!(day && month && year && gender && height && weight);
  // target_weight_kg is optional — patient may not have a goal weight

  const handleContinue = () => {
    update({ dob_day: day, dob_month: month, dob_year: year, gender, height_cm: height, weight_kg: weight, target_weight_kg: target });
    router.push("/(onboarding)/activity-level");
  };

  return (
    <OnboardingShell step={1} totalSteps={8} title="Personal Information" onContinue={handleContinue} continueDisabled={!canContinue} onBack={() => router.replace("/(auth)/login")}>
      <View style={s.form}>
        {/* DOB pickers */}
        <View>
          <Text style={s.label}>Date of Birth</Text>
          <View style={s.dobRow}>
            {/* Day */}
            <View style={s.pickerWrap}>
              <Picker selectedValue={day} onValueChange={setDay} style={s.picker}>
                <Picker.Item label="DD" value="" />
                {DAYS.map(d => <Picker.Item key={d} label={d} value={d} />)}
              </Picker>
            </View>
            {/* Month */}
            <View style={s.pickerWrap}>
              <Picker selectedValue={month} onValueChange={setMonth} style={s.picker}>
                <Picker.Item label="MM" value="" />
                {MONTHS.map((m, i) => <Picker.Item key={m} label={m} value={String(i + 1)} />)}
              </Picker>
            </View>
            {/* Year */}
            <View style={s.pickerWrap}>
              <Picker selectedValue={year} onValueChange={setYear} style={s.picker}>
                <Picker.Item label="YYYY" value="" />
                {YEARS.map(y => <Picker.Item key={y} label={y} value={y} />)}
              </Picker>
            </View>
          </View>
        </View>

        {/* Gender */}
        <View>
          <Text style={s.label}>Gender</Text>
          <View style={s.genderRow}>
            {["Male", "Female", "Other"].map(g => (
              <Pressable key={g} onPress={() => setGender(g)} style={[s.genderBtn, gender === g && s.genderBtnSel]}>
                <Text style={[s.genderText, gender === g && s.genderTextSel]}>{g}</Text>
              </Pressable>
            ))}
          </View>
        </View>

        {/* Height */}
        <View>
          <Text style={s.label}>Height</Text>
          <View style={s.inputWrap}>
            <TextInput style={[s.input, { flex: 1 }]} placeholder="162" value={height} onChangeText={setHeight} keyboardType="numeric" />
            <Text style={s.unit}>cm</Text>
          </View>
        </View>

        {/* Weight */}
        <View>
          <Text style={s.label}>Current Weight</Text>
          <View style={s.inputWrap}>
            <TextInput style={[s.input, { flex: 1 }]} placeholder="74.5" value={weight} onChangeText={setWeight} keyboardType="numeric" />
            <Text style={s.unit}>kg</Text>
          </View>
        </View>

        {/* Target weight */}
        <View>
          <Text style={s.label}>Target Weight</Text>
          <View style={s.inputWrap}>
            <TextInput style={[s.input, { flex: 1 }]} placeholder="68" value={target} onChangeText={setTarget} keyboardType="numeric" />
            <Text style={s.unit}>kg</Text>
          </View>
          <Text style={s.hint}>What's your goal weight?</Text>
        </View>
      </View>
    </OnboardingShell>
  );
}

const s = StyleSheet.create({
  form:          { gap: 20 },
  label:         { fontSize: 14, fontWeight: "500", color: "#374151", marginBottom: 8 },
  hint:          { fontSize: 12, color: "#9CA3AF", marginTop: 4 },
  dobRow:        { flexDirection: "row", gap: 8 },
  pickerWrap:    { flex: 1, borderWidth: 1.5, borderColor: "#E5E7EB", borderRadius: 12, overflow: "hidden" },
  picker:        { height: 52 },
  genderRow:     { flexDirection: "row", gap: 8 },
  genderBtn:     { flex: 1, height: 44, borderRadius: 10, borderWidth: 1.5, borderColor: "#D1D5DB", alignItems: "center", justifyContent: "center", backgroundColor: "#fff" },
  genderBtnSel:  { borderColor: "#1E7C45", backgroundColor: "#1E7C45" },
  genderText:    { fontSize: 14, fontWeight: "500", color: "#374151" },
  genderTextSel: { color: "#fff" },
  inputWrap:     { flexDirection: "row", alignItems: "center", borderWidth: 1.5, borderColor: "#E5E7EB", borderRadius: 12, paddingHorizontal: 16 },
  input:         { height: 52, fontSize: 14, color: "#111827" },
  unit:          { fontSize: 13, color: "#6B7280" },
});
