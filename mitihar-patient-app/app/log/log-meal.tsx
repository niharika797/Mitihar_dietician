import React, { useState } from "react";
import {
  View, Text, TextInput, ScrollView, Pressable, StyleSheet,
  ActivityIndicator, Platform,
} from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft, ChevronDown, ChevronUp } from "lucide-react-native";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { logMeal } from "../../services/progress";
import { useToast } from "../../components/shared";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { useProgressStore } from "../../store/useProgressStore";

const MEAL_TYPES = ["Breakfast", "Morning Snack", "Lunch", "Evening Snack", "Dinner"];

export default function LogMealScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const setLocalWater = useProgressStore(s => s.setLocalWater);

  const [mealType,  setMealType]  = useState("Breakfast");
  const [calories,  setCalories]  = useState("");
  const [protein,   setProtein]   = useState("");
  const [carbs,     setCarbs]     = useState("");
  const [fat,       setFat]       = useState("");
  const [fiber,     setFiber]     = useState("");
  const [notes,     setNotes]     = useState("");
  const [showMacros, setShowMacros] = useState(false);
  const [typeOpen,  setTypeOpen]  = useState(false);

  const saveMut = useMutation({
    mutationFn: () => logMeal({
      meal_type:         mealType.toLowerCase(),
      calories_consumed: parseFloat(calories),
      protein_g:         protein ? parseFloat(protein) : undefined,
      carbs_g:           carbs   ? parseFloat(carbs)   : undefined,
      fat_g:             fat     ? parseFloat(fat)     : undefined,
      fiber_g:           fiber   ? parseFloat(fiber)   : undefined,
      notes:             notes   || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
      showToast("Meal logged! 🎉", "success");
      router.back();
    },
    onError: () => showToast("Failed to log meal", "error"),
  });

  const canSave = !!calories && parseFloat(calories) > 0;

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Log Meal</Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>
        {/* Meal type picker */}
        <View style={s.field}>
          <Text style={s.label}>Meal Type</Text>
          <Pressable style={s.picker} onPress={() => setTypeOpen(o => !o)}>
            <Text style={s.pickerText}>{mealType}</Text>
            {typeOpen ? <ChevronUp size={16} color="#6B7280" /> : <ChevronDown size={16} color="#6B7280" />}
          </Pressable>
          {typeOpen && (
            <View style={s.dropdown}>
              {MEAL_TYPES.map(t => (
                <Pressable key={t} style={[s.dropItem, t === mealType && s.dropItemSel]}
                  onPress={() => { setMealType(t); setTypeOpen(false); }}>
                  <Text style={[s.dropItemText, t === mealType && s.dropItemTextSel]}>{t}</Text>
                </Pressable>
              ))}
            </View>
          )}
        </View>

        {/* Calories */}
        <View style={s.field}>
          <Text style={s.label}>Calories Consumed (kcal) *</Text>
          <View style={s.unitWrap}>
            <TextInput style={[s.input, { paddingRight: 50 }]} value={calories} onChangeText={setCalories}
              keyboardType="decimal-pad" placeholder="320" placeholderTextColor="#9CA3AF" />
            <Text style={s.unit}>kcal</Text>
          </View>
        </View>

        {/* Macros expander */}
        <View style={s.macroBox}>
          <Pressable style={s.macroHeader} onPress={() => setShowMacros(o => !o)}>
            <Text style={s.macroHeaderText}>Macros (optional)</Text>
            {showMacros ? <ChevronUp size={16} color="#6B7280" /> : <ChevronDown size={16} color="#6B7280" />}
          </Pressable>
          {showMacros && (
            <View style={s.macroRow}>
              {[
                { l: "Protein (g)", v: protein, s: setProtein },
                { l: "Carbs (g)",   v: carbs,   s: setCarbs   },
                { l: "Fat (g)",     v: fat,     s: setFat     },
                { l: "Fiber (g)",   v: fiber,   s: setFiber   },
              ].map(m => (
                <View key={m.l} style={s.macroField}>
                  <Text style={s.macroLabel}>{m.l}</Text>
                  <TextInput style={s.macroInput} value={m.v} onChangeText={m.s}
                    keyboardType="decimal-pad" placeholder="0" placeholderTextColor="#9CA3AF" />
                </View>
              ))}
            </View>
          )}
        </View>

        {/* Notes */}
        <View style={s.field}>
          <Text style={s.label}>Notes (optional)</Text>
          <TextInput style={s.input} value={notes} onChangeText={setNotes}
            placeholder="e.g. Had with extra ghee" placeholderTextColor="#9CA3AF" />
        </View>

        <Pressable
          style={[s.saveBtn, !canSave && s.saveBtnDisabled]}
          onPress={() => saveMut.mutate()}
          disabled={!canSave || saveMut.isPending}
        >
          {saveMut.isPending
            ? <ActivityIndicator color="#fff" />
            : <Text style={[s.saveBtnText, !canSave && s.saveBtnTextDisabled]}>Save Meal Log</Text>}
        </Pressable>
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root:               { flex: 1, backgroundColor: "#F9FAFB" },
  header:             { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:            { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:              { fontSize: 18, fontWeight: "600", color: "#111827" },
  scroll:             { padding: 20, gap: 16 },
  field:              { gap: 6 },
  label:              { fontSize: 14, fontWeight: "500", color: "#374151" },
  input:              { height: 52, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", paddingHorizontal: 16, fontSize: 14, color: "#111827", backgroundColor: "#fff" },
  unitWrap:           { position: "relative" },
  unit:               { position: "absolute", right: 14, top: 16, fontSize: 13, color: "#6B7280" },
  picker:             { height: 52, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", paddingHorizontal: 16, backgroundColor: "#fff", flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  pickerText:         { fontSize: 14, color: "#111827" },
  dropdown:           { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", marginTop: 4, overflow: "hidden" },
  dropItem:           { paddingHorizontal: 16, paddingVertical: 13, borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  dropItemSel:        { backgroundColor: "#F0FDF4" },
  dropItemText:       { fontSize: 14, color: "#374151" },
  dropItemTextSel:    { color: "#1E7C45", fontWeight: "600" },
  macroBox:           { borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", overflow: "hidden" },
  macroHeader:        { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 14, backgroundColor: "#F9FAFB" },
  macroHeaderText:    { fontSize: 14, fontWeight: "500", color: "#374151" },
  macroRow:           { flexDirection: "row", flexWrap: "wrap", gap: 10, padding: 12, backgroundColor: "#fff" },
  macroField:         { flex: 1, minWidth: "44%", gap: 4 },
  macroLabel:         { fontSize: 11, color: "#6B7280" },
  macroInput:         { height: 44, borderRadius: 8, borderWidth: 1.5, borderColor: "#E5E7EB", paddingHorizontal: 12, fontSize: 14, color: "#111827", backgroundColor: "#fff" },
  saveBtn:            { height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center", marginTop: 8 },
  saveBtnDisabled:    { backgroundColor: "#E5E7EB" },
  saveBtnText:        { fontSize: 16, fontWeight: "600", color: "#fff" },
  saveBtnTextDisabled:{ color: "#9CA3AF" },
});
