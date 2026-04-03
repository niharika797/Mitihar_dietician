import React, { useState } from "react";
import {
  View, Text, ScrollView, Pressable, StyleSheet, TextInput,
  ActivityIndicator, Modal,
} from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft, Plus } from "lucide-react-native";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getWeightHistory, logWeight } from "../../services/progress";
import { useProgressStore } from "../../store/useProgressStore";
import { useToast } from "../../components/shared";
import { QUERY_KEYS } from "../../lib/queryKeys";
import type { WeightEntry } from "../../types";

export default function WeightLogScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { appendWeightEntry } = useProgressStore();

  const [showModal, setShowModal] = useState(false);
  const [input,     setInput]     = useState("");

  const { data: entries, isLoading } = useQuery({
    queryKey: QUERY_KEYS.WEIGHT_HISTORY(90),
    queryFn:  () => getWeightHistory(90),
  });

  const logMut = useMutation({
    mutationFn: () => logWeight(parseFloat(input)),
    onSuccess: () => {
      const entry: WeightEntry = { date: new Date().toISOString().slice(0, 10), weight_kg: parseFloat(input) };
      appendWeightEntry(entry);
      qc.invalidateQueries({ queryKey: QUERY_KEYS.WEIGHT_HISTORY(90) });
      showToast("Weight logged! 💪", "success");
      setInput("");
      setShowModal(false);
    },
    onError: () => showToast("Failed to log weight", "error"),
  });

  const canLog = !!input && parseFloat(input) > 20 && parseFloat(input) < 300;

  const sorted = [...(entries ?? [])].sort((a, b) => b.date.localeCompare(a.date));
  const latest = sorted[0];

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Weight Log</Text>
        <Pressable style={s.addBtn} onPress={() => setShowModal(true)} hitSlop={8}>
          <Plus size={18} color="#1E7C45" />
        </Pressable>
      </View>

      {/* Current weight hero */}
      {latest && (
        <View style={s.hero}>
          <Text style={s.heroWeight}>{latest.weight_kg} kg</Text>
          <Text style={s.heroDate}>Last logged: {latest.date}</Text>
        </View>
      )}

      {isLoading ? (
        <View style={s.loader}><ActivityIndicator size="large" color="#1E7C45" /></View>
      ) : sorted.length === 0 ? (
        <View style={s.empty}>
          <Text style={s.emptyEmoji}>⚖️</Text>
          <Text style={s.emptyTitle}>No weight logs yet</Text>
          <Text style={s.emptySub}>Tap + to log your first weight entry.</Text>
        </View>
      ) : (
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>
          <Text style={s.sectionLabel}>HISTORY (LAST 90 DAYS)</Text>
          <View style={s.card}>
            {sorted.map((entry, i) => {
              const prev = sorted[i + 1];
              const diff = prev ? (entry.weight_kg - prev.weight_kg) : 0;
              return (
                <View key={entry.date} style={[s.row, i < sorted.length - 1 && s.rowBorder]}>
                  <Text style={s.rowDate}>{entry.date}</Text>
                  <View style={s.rowRight}>
                    <Text style={s.rowWeight}>{entry.weight_kg} kg</Text>
                    {diff !== 0 && (
                      <Text style={[s.rowDiff, diff < 0 ? s.rowDiffGood : s.rowDiffBad]}>
                        {diff > 0 ? "+" : ""}{diff.toFixed(1)}
                      </Text>
                    )}
                  </View>
                </View>
              );
            })}
          </View>
        </ScrollView>
      )}

      {/* Log modal */}
      <Modal visible={showModal} transparent animationType="slide">
        <Pressable style={s.backdrop} onPress={() => setShowModal(false)}>
          <Pressable style={s.sheet} onPress={() => {}}>
            <View style={s.sheetHandle} />
            <Text style={s.sheetTitle}>Log Weight</Text>
            <View style={s.unitWrap}>
              <TextInput style={s.sheetInput} value={input} onChangeText={setInput}
                keyboardType="decimal-pad" placeholder="72.5" placeholderTextColor="#9CA3AF" />
              <Text style={s.sheetUnit}>kg</Text>
            </View>
            <Pressable style={[s.sheetBtn, !canLog && s.sheetBtnDisabled]}
              onPress={() => logMut.mutate()} disabled={!canLog || logMut.isPending}>
              {logMut.isPending
                ? <ActivityIndicator color="#fff" />
                : <Text style={[s.sheetBtnText, !canLog && s.sheetBtnTextDisabled]}>Save</Text>}
            </Pressable>
          </Pressable>
        </Pressable>
      </Modal>
    </View>
  );
}

const s = StyleSheet.create({
  root:              { flex: 1, backgroundColor: "#F9FAFB" },
  header:            { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:           { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:             { fontSize: 18, fontWeight: "600", color: "#111827" },
  addBtn:            { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F0FDF4", alignItems: "center", justifyContent: "center" },
  hero:              { backgroundColor: "#fff", padding: 24, alignItems: "center", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  heroWeight:        { fontSize: 36, fontWeight: "700", color: "#111827" },
  heroDate:          { fontSize: 13, color: "#6B7280", marginTop: 4 },
  loader:            { flex: 1, alignItems: "center", justifyContent: "center" },
  empty:             { alignItems: "center", paddingTop: 60, paddingHorizontal: 32 },
  emptyEmoji:        { fontSize: 48, marginBottom: 12 },
  emptyTitle:        { fontSize: 18, fontWeight: "600", color: "#111827", marginBottom: 8 },
  emptySub:          { fontSize: 14, color: "#6B7280", textAlign: "center" },
  scroll:            { padding: 20, gap: 10 },
  sectionLabel:      { fontSize: 11, fontWeight: "600", color: "#9CA3AF", letterSpacing: 1, marginBottom: 4 },
  card:              { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", overflow: "hidden" },
  row:               { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 16, paddingVertical: 14 },
  rowBorder:         { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  rowDate:           { fontSize: 14, color: "#374151" },
  rowRight:          { flexDirection: "row", alignItems: "center", gap: 8 },
  rowWeight:         { fontSize: 14, fontWeight: "600", color: "#111827" },
  rowDiff:           { fontSize: 12, fontWeight: "500" },
  rowDiffGood:       { color: "#16A34A" },
  rowDiffBad:        { color: "#DC2626" },
  backdrop:          { flex: 1, backgroundColor: "rgba(0,0,0,0.4)", justifyContent: "flex-end" },
  sheet:             { backgroundColor: "#fff", borderTopLeftRadius: 24, borderTopRightRadius: 24, padding: 24, gap: 16 },
  sheetHandle:       { width: 40, height: 4, borderRadius: 2, backgroundColor: "#E5E7EB", alignSelf: "center" },
  sheetTitle:        { fontSize: 18, fontWeight: "600", color: "#111827", textAlign: "center" },
  unitWrap:          { position: "relative" },
  sheetInput:        { height: 56, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", paddingHorizontal: 16, paddingRight: 48, fontSize: 20, fontWeight: "600", color: "#111827", textAlign: "center" },
  sheetUnit:         { position: "absolute", right: 16, top: 16, fontSize: 16, color: "#6B7280" },
  sheetBtn:          { height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  sheetBtnDisabled:  { backgroundColor: "#E5E7EB" },
  sheetBtnText:      { fontSize: 16, fontWeight: "600", color: "#fff" },
  sheetBtnTextDisabled:{ color: "#9CA3AF" },
});
