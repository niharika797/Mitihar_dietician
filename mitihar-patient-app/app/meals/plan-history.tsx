import React from "react";
import { View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import { useQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { getPlanHistory } from "../../services/meals";
import type { PlanHistoryItem } from "../../types";

export default function PlanHistoryScreen() {
  const router = useRouter();
  const { data: plans, isLoading } = useQuery({
    queryKey: QUERY_KEYS.PLAN_HISTORY,
    queryFn: getPlanHistory,
  });

  if (isLoading) return <View style={s.loader}><ActivityIndicator size="large" color="#1E7C45" /></View>;

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Plan History</Text>
        <View style={{ width: 36 }} />
      </View>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>
        {(!plans || plans.length === 0) ? (
          <View style={s.empty}>
            <Text style={s.emptyEmoji}>📋</Text>
            <Text style={s.emptyTitle}>No plan history yet</Text>
            <Text style={s.emptySub}>Your plan history will appear here once your doctor generates meal plans.</Text>
          </View>
        ) : (
          plans.map((plan: PlanHistoryItem) => (
            <Pressable key={plan.id} onPress={() => router.push("/(tabs)/meals")} style={s.card}>
              <View style={s.cardLeft}>
                <View style={s.topRow}>
                  {plan.is_active && <View style={s.activeDot} />}
                  {plan.is_active && <Text style={s.activeLabel}>Current Plan</Text>}
                </View>
                <Text style={s.weekLabel}>Week of {plan.week_start_date}</Text>
                <Text style={s.genLabel}>Generated {plan.created_at.slice(0, 10)} · v{plan.version}</Text>
              </View>
              <Pressable onPress={() => router.push("/(tabs)/meals")} style={s.viewBtn}>
                <Text style={s.viewBtnText}>View</Text>
              </Pressable>
            </Pressable>
          ))
        )}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root:       { flex: 1, backgroundColor: "#F9FAFB" },
  loader:     { flex: 1, alignItems: "center", justifyContent: "center" },
  header:     { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:    { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:      { fontSize: 18, fontWeight: "600", color: "#111827" },
  scroll:     { paddingHorizontal: 20, paddingTop: 16, paddingBottom: 32 },
  card:       { flexDirection: "row", alignItems: "center", justifyContent: "space-between", backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 16, marginBottom: 10 },
  cardLeft:   { flex: 1, gap: 4 },
  topRow:     { flexDirection: "row", alignItems: "center", gap: 6 },
  activeDot:  { width: 8, height: 8, borderRadius: 4, backgroundColor: "#34B164" },
  activeLabel:{ fontSize: 12, fontWeight: "600", color: "#166534" },
  weekLabel:  { fontSize: 15, fontWeight: "600", color: "#111827" },
  genLabel:   { fontSize: 12, color: "#6B7280" },
  viewBtn:    { height: 34, paddingHorizontal: 16, borderRadius: 99, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  viewBtnText:{ fontSize: 13, fontWeight: "500", color: "#374151" },
  empty:      { alignItems: "center", paddingTop: 60, paddingHorizontal: 32 },
  emptyEmoji: { fontSize: 48, marginBottom: 12 },
  emptyTitle: { fontSize: 18, fontWeight: "600", color: "#111827", marginBottom: 8 },
  emptySub:   { fontSize: 14, color: "#6B7280", textAlign: "center", lineHeight: 20 },
});
