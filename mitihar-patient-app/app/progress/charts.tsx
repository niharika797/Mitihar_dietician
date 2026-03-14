import React, { useState } from "react";
import { View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import { useQuery } from "@tanstack/react-query";
import { LineChart, BarChart } from "react-native-gifted-charts";
import { getWeightHistory, getWeeklyReport } from "../../services/progress";
import { useAuthStore } from "../../store/useAuthStore";
import { QUERY_KEYS } from "../../lib/queryKeys";

type Range = "30d" | "90d";

export default function ChartsScreen() {
  const router   = useRouter();
  const profile  = useAuthStore(s => s.profile);
  const [range, setRange] = useState<Range>("30d");

  const days = range === "30d" ? 30 : 90;

  const { data: weightEntries, isLoading: wLoading } = useQuery({
    queryKey: QUERY_KEYS.WEIGHT_HISTORY(days),
    queryFn:  () => getWeightHistory(days),
  });

  const { data: weeklyReport, isLoading: rLoading } = useQuery({
    queryKey: QUERY_KEYS.WEEKLY_REPORT,
    queryFn:  getWeeklyReport,
  });

  const isLoading = wLoading || rLoading;

  // Weight line chart data
  const weightData = (weightEntries ?? [])
    .slice(-14)
    .map(e => ({
      value: e.weight_kg,
      label: e.date.slice(5),          // "MM-DD"
      dataPointText: String(e.weight_kg),
    }));

  // Calorie bar chart data (last 7 days from weekly report)
  const calData = Object.entries(weeklyReport ?? {})
    .slice(-7)
    .map(([date, v]) => ({
      value:      v.calories_consumed,
      label:      date.slice(5),        // "MM-DD"
      frontColor: v.calories_consumed >= (profile?.tdee ?? 1800) * 0.8 ? "#34B164" : "#FCD34D",
    }));

  const startWeight   = weightEntries?.[0]?.weight_kg ?? profile?.weight_kg ?? 0;
  const currentWeight = weightEntries?.[weightEntries.length - 1]?.weight_kg ?? profile?.weight_kg ?? 0;
  const targetWeight  = profile?.target_weight_kg ?? 0;
  const totalLost     = (startWeight - currentWeight).toFixed(1);
  const remaining     = Math.max(currentWeight - targetWeight, 0).toFixed(1);

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Weight History</Text>
        <View style={s.rangeRow}>
          {(["30d", "90d"] as Range[]).map(r => (
            <Pressable key={r} style={[s.rangeBtn, range === r && s.rangeBtnActive]}
              onPress={() => setRange(r)}>
              <Text style={[s.rangeBtnText, range === r && s.rangeBtnTextActive]}>{r}</Text>
            </Pressable>
          ))}
        </View>
      </View>

      {isLoading ? (
        <View style={s.loader}><ActivityIndicator size="large" color="#1E7C45" /></View>
      ) : (
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>
          {/* Current weight */}
          <View style={s.heroRow}>
            <Text style={s.heroWeight}>{currentWeight} kg</Text>
            {parseFloat(totalLost) > 0 && (
              <Text style={s.heroDelta}>↓ {totalLost}kg since start</Text>
            )}
          </View>

          {/* Weight line chart */}
          <View style={s.chartCard}>
            <Text style={s.chartLabel}>WEIGHT TREND</Text>
            {weightData.length < 2 ? (
              <Text style={s.noData}>Not enough data yet. Keep logging daily!</Text>
            ) : (
              <LineChart
                data={weightData}
                width={300}
                height={200}
                color="#1E7C45"
                thickness={2.5}
                hideDataPoints={false}
                dataPointsColor="#1E7C45"
                dataPointsRadius={4}
                xAxisLabelTextStyle={{ fontSize: 9, color: "#9CA3AF" }}
                yAxisTextStyle={{ fontSize: 9, color: "#9CA3AF" }}
                noOfSections={4}
                curved
                isAnimated
              />
            )}
          </View>

          {/* Calorie bar chart */}
          <View style={s.chartCard}>
            <Text style={s.chartLabel}>CALORIE TREND (LAST 7 DAYS)</Text>
            {calData.length === 0 ? (
              <Text style={s.noData}>No calorie data yet.</Text>
            ) : (
              <BarChart
                data={calData}
                width={300}
                height={160}
                barWidth={32}
                barBorderRadius={4}
                referenceLine1Position={profile?.tdee ?? 1850}
                referenceLine1Config={{ color: "#D1D5DB", dashWidth: 4, dashGap: 4 }}
                xAxisLabelTextStyle={{ fontSize: 9, color: "#6B7280" }}
                yAxisTextStyle={{ fontSize: 9, color: "#9CA3AF" }}
                noOfSections={4}
                isAnimated
              />
            )}
          </View>

          {/* Stats summary table */}
          <View style={s.statsCard}>
            {[
              { label: "Starting weight", value: `${startWeight} kg`   },
              { label: "Current weight",  value: `${currentWeight} kg` },
              { label: "Goal weight",     value: `${targetWeight} kg`  },
              { label: "Total lost",      value: `${totalLost} kg`     },
              { label: "Remaining",       value: `${remaining} kg`     },
            ].map((row, i, arr) => (
              <View key={row.label} style={[s.statsRow, i < arr.length - 1 && s.statsRowBorder]}>
                <Text style={s.statsLabel}>{row.label}</Text>
                <Text style={s.statsValue}>{row.value}</Text>
              </View>
            ))}
          </View>
        </ScrollView>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  root:               { flex: 1, backgroundColor: "#F9FAFB" },
  header:             { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:            { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:              { fontSize: 18, fontWeight: "600", color: "#111827" },
  rangeRow:           { flexDirection: "row", gap: 4 },
  rangeBtn:           { height: 28, paddingHorizontal: 10, borderRadius: 99, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  rangeBtnActive:     { backgroundColor: "#1E7C45" },
  rangeBtnText:       { fontSize: 12, fontWeight: "500", color: "#374151" },
  rangeBtnTextActive: { color: "#fff" },
  loader:             { flex: 1, alignItems: "center", justifyContent: "center" },
  scroll:             { padding: 16, gap: 16, paddingBottom: 32 },
  heroRow:            { flexDirection: "row", alignItems: "baseline", gap: 10 },
  heroWeight:         { fontSize: 28, fontWeight: "700", color: "#111827" },
  heroDelta:          { fontSize: 14, color: "#34B164", fontWeight: "500" },
  chartCard:          { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 16, gap: 10, overflow: "hidden" },
  chartLabel:         { fontSize: 11, fontWeight: "600", color: "#374151", letterSpacing: 1 },
  noData:             { fontSize: 13, color: "#9CA3AF", textAlign: "center", paddingVertical: 24 },
  statsCard:          { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", overflow: "hidden" },
  statsRow:           { flexDirection: "row", justifyContent: "space-between", padding: 14 },
  statsRowBorder:     { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  statsLabel:         { fontSize: 13, color: "#6B7280" },
  statsValue:         { fontSize: 14, fontWeight: "600", color: "#111827" },
});
