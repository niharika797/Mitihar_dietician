import React, { useState } from "react";
import {
  View, Text, Pressable, StyleSheet, ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft, Droplets, Plus, Minus } from "lucide-react-native";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { logWater } from "../../services/progress";
import { useProgressStore, selectWater } from "../../store/useProgressStore";
import { useToast } from "../../components/shared";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { useAuthStore } from "../../store/useAuthStore";

export default function WaterLogScreen() {
  const router    = useRouter();
  const qc        = useQueryClient();
  const { showToast }  = useToast();
  const water          = useProgressStore(selectWater);
  const setLocalWater  = useProgressStore(s => s.setLocalWater);
  const goal           = useAuthStore(s => s.profile?.water_glasses ?? 8);

  const logMut = useMutation({
    mutationFn: (glasses: number) => logWater(glasses),
    onSuccess: (_, glasses) => {
      setLocalWater(glasses);
      qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
    },
    onError: () => showToast("Failed to update water", "error"),
  });

  const add    = () => { const next = Math.min(water + 1, 20); logMut.mutate(next); };
  const remove = () => { const next = Math.max(water - 1, 0);  logMut.mutate(next); };

  const pct = Math.min(water / goal, 1);

  const TIPS = [
    "Drink a glass first thing in the morning to kickstart metabolism.",
    "Sip water before each meal to aid digestion.",
    "Keep a bottle visible on your desk as a reminder.",
    "Herbal teas and coconut water count toward your daily intake.",
    "Thirst is a late signal — drink before you feel thirsty.",
  ];

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Water Log</Text>
        <View style={{ width: 36 }} />
      </View>

      {/* Hero tracker */}
      <View style={s.hero}>
        <Droplets size={36} color="#3B82F6" />
        <Text style={s.heroCount}>{water}<Text style={s.heroUnit}> / {goal}</Text></Text>
        <Text style={s.heroLabel}>glasses today</Text>

        {/* Progress bar */}
        <View style={s.bar}>
          <View style={[s.barFill, { width: `${Math.round(pct * 100)}%` }]} />
        </View>
        <Text style={s.barPct}>{Math.round(pct * 100)}% of daily goal</Text>

        {/* +/- controls */}
        <View style={s.controls}>
          <Pressable style={s.controlBtn} onPress={remove} disabled={water === 0 || logMut.isPending}>
            <Minus size={20} color={water === 0 ? "#D1D5DB" : "#374151"} />
          </Pressable>
          {logMut.isPending
            ? <ActivityIndicator color="#3B82F6" />
            : <Text style={s.controlStatus}>{water === goal ? "✅ Goal reached!" : `${goal - water} more to go`}</Text>}
          <Pressable style={s.controlBtn} onPress={add} disabled={water >= 20 || logMut.isPending}>
            <Plus size={20} color={water >= 20 ? "#D1D5DB" : "#3B82F6"} />
          </Pressable>
        </View>
      </View>

      {/* Glasses grid */}
      <View style={s.glassGrid}>
        {Array.from({ length: goal }, (_, i) => (
          <Pressable key={i} onPress={() => logMut.mutate(i + 1)} style={s.glass}>
            <Droplets size={22} color={i < water ? "#3B82F6" : "#D1D5DB"} fill={i < water ? "#DBEAFE" : "transparent"} />
          </Pressable>
        ))}
      </View>

      {/* Hydration tips */}
      <View style={s.tipsCard}>
        <Text style={s.tipsTitle}>💡 Hydration Tips</Text>
        {TIPS.map((tip, i) => (
          <Text key={i} style={s.tipText}>• {tip}</Text>
        ))}
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  root:          { flex: 1, backgroundColor: "#F9FAFB" },
  header:        { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:       { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:         { fontSize: 18, fontWeight: "600", color: "#111827" },
  hero:          { backgroundColor: "#fff", padding: 28, alignItems: "center", gap: 10, borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  heroCount:     { fontSize: 52, fontWeight: "700", color: "#1D4ED8" },
  heroUnit:      { fontSize: 24, fontWeight: "400", color: "#6B7280" },
  heroLabel:     { fontSize: 14, color: "#6B7280" },
  bar:           { width: "100%", height: 8, backgroundColor: "#E5E7EB", borderRadius: 4, overflow: "hidden" },
  barFill:       { height: "100%", backgroundColor: "#3B82F6", borderRadius: 4 },
  barPct:        { fontSize: 12, color: "#6B7280" },
  controls:      { flexDirection: "row", alignItems: "center", gap: 24, marginTop: 4 },
  controlBtn:    { width: 44, height: 44, borderRadius: 22, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  controlStatus: { fontSize: 14, color: "#374151", fontWeight: "500", minWidth: 120, textAlign: "center" },
  glassGrid:     { flexDirection: "row", flexWrap: "wrap", gap: 8, padding: 20, justifyContent: "center" },
  glass:         { width: 44, height: 44, borderRadius: 12, backgroundColor: "#F9FAFB", alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: "#E5E7EB" },
  tipsCard:      { margin: 16, backgroundColor: "#EFF6FF", borderRadius: 12, borderWidth: 1, borderColor: "#BFDBFE", padding: 16, gap: 8 },
  tipsTitle:     { fontSize: 13, fontWeight: "600", color: "#1E40AF" },
  tipText:       { fontSize: 13, color: "#374151", lineHeight: 20 },
});
