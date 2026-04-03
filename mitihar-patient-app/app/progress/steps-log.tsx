import React, { useState } from "react";
import {
  View, Text, TextInput, Pressable, StyleSheet, ActivityIndicator, Modal,
} from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft, Footprints, Plus } from "lucide-react-native";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { logSteps } from "../../services/progress";
import { useProgressStore, selectSteps } from "../../store/useProgressStore";
import { useToast } from "../../components/shared";
import { QUERY_KEYS } from "../../lib/queryKeys";

const STEP_GOAL = 8000;
const PRESETS   = [500, 1000, 2000, 5000, 8000, 10000];

export default function StepsLogScreen() {
  const router   = useRouter();
  const qc       = useQueryClient();
  const { showToast } = useToast();
  const steps         = useProgressStore(selectSteps);
  const setLocalSteps = useProgressStore(s => s.setLocalSteps);

  const [showModal, setShowModal] = useState(false);
  const [input,     setInput]     = useState("");

  const logMut = useMutation({
    mutationFn: (s: number) => logSteps(s),
    onSuccess: (_, s) => {
      setLocalSteps(s);
      qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
      showToast("Steps updated! 🚶", "success");
      setInput("");
      setShowModal(false);
    },
    onError: () => showToast("Failed to update steps", "error"),
  });

  const pct     = Math.min(steps / STEP_GOAL, 1);
  const canSave = !!input && parseInt(input) > 0;

  // Calorie burn estimate: ~0.04 kcal per step
  const caloriesBurned = Math.round(steps * 0.04);
  const distanceKm     = (steps * 0.0008).toFixed(2);

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Steps Log</Text>
        <Pressable style={s.addBtn} onPress={() => setShowModal(true)} hitSlop={8}>
          <Plus size={18} color="#1E7C45" />
        </Pressable>
      </View>

      {/* Hero */}
      <View style={s.hero}>
        <Footprints size={36} color="#6366F1" />
        <Text style={s.heroSteps}>{steps.toLocaleString()}</Text>
        <Text style={s.heroLabel}>steps today · goal {STEP_GOAL.toLocaleString()}</Text>
        <View style={s.bar}>
          <View style={[s.barFill, { width: `${Math.round(pct * 100)}%` }]} />
        </View>
        <Text style={s.barPct}>{Math.round(pct * 100)}% of daily goal</Text>
      </View>

      {/* Stats grid */}
      <View style={s.statsGrid}>
        {[
          { label: "Calories Burned", value: `${caloriesBurned} kcal`, emoji: "🔥" },
          { label: "Distance",        value: `${distanceKm} km`,       emoji: "📍" },
          { label: "Active Minutes",  value: `~${Math.round(steps / 100)} min`, emoji: "⏱" },
          { label: "Goal Progress",   value: `${Math.round(pct * 100)}%`,       emoji: "🎯" },
        ].map(stat => (
          <View key={stat.label} style={s.statCard}>
            <Text style={s.statEmoji}>{stat.emoji}</Text>
            <Text style={s.statValue}>{stat.value}</Text>
            <Text style={s.statLabel}>{stat.label}</Text>
          </View>
        ))}
      </View>

      {/* Quick-set presets */}
      <View style={s.presetsSection}>
        <Text style={s.presetsTitle}>Quick Set</Text>
        <View style={s.presets}>
          {PRESETS.map(p => (
            <Pressable key={p} style={[s.preset, steps === p && s.presetActive]}
              onPress={() => logMut.mutate(p)} disabled={logMut.isPending}>
              <Text style={[s.presetText, steps === p && s.presetTextActive]}>
                {p >= 1000 ? `${p / 1000}k` : p}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>

      {/* Manual entry modal */}
      <Modal visible={showModal} transparent animationType="slide">
        <Pressable style={s.backdrop} onPress={() => setShowModal(false)}>
          <Pressable style={s.sheet} onPress={() => {}}>
            <View style={s.sheetHandle} />
            <Text style={s.sheetTitle}>Enter Steps</Text>
            <TextInput style={s.sheetInput} value={input} onChangeText={setInput}
              keyboardType="number-pad" placeholder="8000" placeholderTextColor="#9CA3AF" />
            <Pressable style={[s.sheetBtn, !canSave && s.sheetBtnDis]}
              onPress={() => logMut.mutate(parseInt(input))} disabled={!canSave || logMut.isPending}>
              {logMut.isPending
                ? <ActivityIndicator color="#fff" />
                : <Text style={[s.sheetBtnText, !canSave && s.sheetBtnTextDis]}>Save</Text>}
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

const s = StyleSheet.create({
  root:            { flex: 1, backgroundColor: "#F9FAFB" },
  header:          { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:         { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:           { fontSize: 18, fontWeight: "600", color: "#111827" },
  addBtn:          { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F0FDF4", alignItems: "center", justifyContent: "center" },
  hero:            { backgroundColor: "#fff", padding: 28, alignItems: "center", gap: 8, borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  heroSteps:       { fontSize: 48, fontWeight: "700", color: "#4338CA" },
  heroLabel:       { fontSize: 13, color: "#6B7280" },
  bar:             { width: "100%", height: 8, backgroundColor: "#E5E7EB", borderRadius: 4, overflow: "hidden" },
  barFill:         { height: "100%", backgroundColor: "#6366F1", borderRadius: 4 },
  barPct:          { fontSize: 12, color: "#6B7280" },
  statsGrid:       { flexDirection: "row", flexWrap: "wrap", padding: 16, gap: 10 },
  statCard:        { flex: 1, minWidth: "44%", backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 14, gap: 4, alignItems: "center" },
  statEmoji:       { fontSize: 22 },
  statValue:       { fontSize: 16, fontWeight: "700", color: "#111827" },
  statLabel:       { fontSize: 11, color: "#6B7280", textAlign: "center" },
  presetsSection:  { paddingHorizontal: 16, gap: 10 },
  presetsTitle:    { fontSize: 13, fontWeight: "600", color: "#374151" },
  presets:         { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  preset:          { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 99, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff" },
  presetActive:    { borderColor: "#6366F1", backgroundColor: "#EEF2FF" },
  presetText:      { fontSize: 13, fontWeight: "500", color: "#374151" },
  presetTextActive:{ color: "#4338CA" },
  backdrop:        { flex: 1, backgroundColor: "rgba(0,0,0,0.4)", justifyContent: "flex-end" },
  sheet:           { backgroundColor: "#fff", borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24, gap: 16 },
  sheetHandle:     { width: 40, height: 4, borderRadius: 2, backgroundColor: "#E5E7EB", alignSelf: "center" },
  sheetTitle:      { fontSize: 18, fontWeight: "600", color: "#111827", textAlign: "center" },
  sheetInput:      { height: 56, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", paddingHorizontal: 16, fontSize: 20, fontWeight: "600", color: "#111827", textAlign: "center" },
  sheetBtn:        { height: 52, borderRadius: 26, backgroundColor: "#6366F1", alignItems: "center", justifyContent: "center" },
  sheetBtnDis:     { backgroundColor: "#E5E7EB" },
  sheetBtnText:    { fontSize: 16, fontWeight: "600", color: "#fff" },
  sheetBtnTextDis: { color: "#9CA3AF" },
});
