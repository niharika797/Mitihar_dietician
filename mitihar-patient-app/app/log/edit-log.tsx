import React, { useState } from "react";
import {
  View, Text, TextInput, ScrollView, Pressable, StyleSheet,
  ActivityIndicator, Alert,
} from "react-native";
import { useRouter, useLocalSearchParams } from "expo-router";
import { ChevronLeft, Info } from "lucide-react-native";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { editMealLog, deleteMealLog } from "../../services/progress";
import { useToast } from "../../components/shared";
import { QUERY_KEYS } from "../../lib/queryKeys";

export default function EditLogScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  // Params passed from the log history row: id, meal_type, calories, notes
  const params = useLocalSearchParams<{
    id: string; meal_type: string;
    calories: string; notes: string; editable: string;
  }>();

  const id       = Number(params.id ?? 0);
  const editable = params.editable !== "false";

  const [mealType, setMealType] = useState(params.meal_type ?? "Breakfast");
  const [calories, setCalories] = useState(params.calories ?? "");
  const [notes,    setNotes]    = useState(params.notes    ?? "");

  const saveMut = useMutation({
    mutationFn: () => editMealLog(id, {
      meal_type:         mealType.toLowerCase(),
      calories_consumed: parseFloat(calories) || 0,
      notes:             notes || undefined,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
      showToast("Log updated! ✅", "success");
      router.back();
    },
    onError: () => showToast("Failed to update log", "error"),
  });

  const deleteMut = useMutation({
    mutationFn: () => deleteMealLog(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
      showToast("Log deleted", "success");
      router.back();
    },
    onError: () => showToast("Failed to delete log", "error"),
  });

  const handleDelete = () => {
    Alert.alert("Delete Log", "Are you sure you want to delete this meal log?", [
      { text: "Cancel", style: "cancel" },
      { text: "Delete", style: "destructive", onPress: () => deleteMut.mutate() },
    ]);
  };

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Edit Log</Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>
        {!editable && (
          <View style={s.lockedBanner}>
            <Info size={16} color="#B45309" />
            <Text style={s.lockedText}>This log is locked after 24 hours and cannot be edited.</Text>
          </View>
        )}

        <View style={s.field}>
          <Text style={s.label}>Meal Type</Text>
          <TextInput style={[s.input, !editable && s.inputLocked]} value={mealType}
            onChangeText={setMealType} editable={editable} placeholderTextColor="#9CA3AF" />
        </View>

        <View style={s.field}>
          <Text style={s.label}>Calories (kcal)</Text>
          <TextInput style={[s.input, !editable && s.inputLocked]} value={calories}
            onChangeText={setCalories} keyboardType="decimal-pad"
            editable={editable} placeholderTextColor="#9CA3AF" />
        </View>

        <View style={s.field}>
          <Text style={s.label}>Notes</Text>
          <TextInput style={[s.input, !editable && s.inputLocked]} value={notes}
            onChangeText={setNotes} editable={editable}
            placeholder="Any notes about this meal" placeholderTextColor="#9CA3AF" />
        </View>

        {editable && (
          <>
            <Pressable style={s.saveBtn} onPress={() => saveMut.mutate()} disabled={saveMut.isPending}>
              {saveMut.isPending
                ? <ActivityIndicator color="#fff" />
                : <Text style={s.saveBtnText}>Save Changes</Text>}
            </Pressable>
            <Pressable style={s.deleteBtn} onPress={handleDelete} disabled={deleteMut.isPending}>
              <Text style={s.deleteBtnText}>Delete this log</Text>
            </Pressable>
          </>
        )}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root:         { flex: 1, backgroundColor: "#F9FAFB" },
  header:       { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:      { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:        { fontSize: 18, fontWeight: "600", color: "#111827" },
  scroll:       { padding: 20, gap: 16 },
  lockedBanner: { flexDirection: "row", gap: 10, alignItems: "flex-start", backgroundColor: "#FEF3C7", borderWidth: 1, borderColor: "#FCD34D", borderRadius: 8, padding: 12 },
  lockedText:   { flex: 1, fontSize: 12, color: "#92400E", lineHeight: 18 },
  field:        { gap: 6 },
  label:        { fontSize: 14, fontWeight: "500", color: "#374151" },
  input:        { height: 52, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", paddingHorizontal: 16, fontSize: 14, color: "#111827", backgroundColor: "#fff" },
  inputLocked:  { backgroundColor: "#F9FAFB", color: "#9CA3AF" },
  saveBtn:      { height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  saveBtnText:  { fontSize: 16, fontWeight: "600", color: "#fff" },
  deleteBtn:    { alignItems: "center", paddingVertical: 8 },
  deleteBtnText:{ fontSize: 14, fontWeight: "500", color: "#DC2626" },
});
