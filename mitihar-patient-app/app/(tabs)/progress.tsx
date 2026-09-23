import React, { useState, useCallback } from "react";
import {
  View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator, TextInput, useWindowDimensions,
} from "react-native";
import { useFocusEffect } from "expo-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react-native";
import { LineChart } from "react-native-gifted-charts";
import Animated, { FadeInDown, Easing } from "react-native-reanimated";
import * as Haptics from "expo-haptics";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { getTodaySummary, logWeight, getWeightHistory, getStreak } from "../../services/progress";
import { useAuthStore } from "../../store/useAuthStore";
import { useProgressStore } from "../../store/useProgressStore";
import { BottomSheet, useToast, ScreenHeader, ErrorState, Card, Button, AnimatedPressable } from "../../components/shared";
import { colors, spacing, iconSize, typography } from "../../constants/theme";
import type { WeightEntry } from "../../types";
import { CopilotStep, walkthroughable } from "react-native-copilot";

// ScreenHeader is already forwardRef (see components/shared/ScreenHeader.tsx)
// specifically so it stays drop-in compatible with react-native-copilot's
// walkthroughable(), which needs a ref to measure the target on screen.
const CopilotScreenHeader = walkthroughable(ScreenHeader);

const EASE_OUT = Easing.bezier(0.23, 1, 0.32, 1);

type BarData = { value: number; label?: string; frontColor?: string };

export default function ProgressScreen() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const profile = useAuthStore(s => s.profile);
  const { hydrateSummary, hydrateWeightHistory, appendWeightEntry } = useProgressStore();

  const [weightSheet, setWeightSheet] = useState(false);
  const [tempWeight,  setTempWeight]  = useState("");

  const localWeight = useProgressStore(s => s.localWeight);
  const weightHistory = useProgressStore(s => s.weightHistory);

  const { data: today, isLoading } = useQuery({
    queryKey: QUERY_KEYS.TODAY,
    queryFn: getTodaySummary,
    refetchInterval: 60_000,
  });

  const { data: weightData, isError: weightError, refetch: refetchWeight } = useQuery({
    queryKey: QUERY_KEYS.WEIGHT_HISTORY(30),
    queryFn: () => getWeightHistory(30),
  });

  const { data: streakData } = useQuery({
    queryKey: QUERY_KEYS.STREAK,
    queryFn: getStreak,
    staleTime: 1000 * 60 * 5,
  });

  React.useEffect(() => { if (weightData) hydrateWeightHistory(weightData); }, [weightData]);
  React.useEffect(() => { if (today) hydrateSummary(today); }, [today]);

  useFocusEffect(useCallback(() => {
    qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY });
    qc.invalidateQueries({ queryKey: QUERY_KEYS.WEIGHT_HISTORY(30) });
  }, [qc]));

  const currentWeight = localWeight ?? profile?.weight_kg ?? 0;
  const targetWeight  = profile?.target_weight_kg ?? null;
  const streak    = streakData?.streak_days ?? 0;

  // chart data — last 7 weight entries (guard: weightHistory may be undefined on first load)
  const chartData: BarData[] = (Array.isArray(weightHistory) ? weightHistory : []).slice(-7).map(e => ({
    value: e.weight_kg,
    label: e.date.slice(5), // MM-DD
  }));

  const { width: screenWidth } = useWindowDimensions();
  const weightValues = chartData.map(d => d.value);

  // ── Mutations ─────────────────────────────────────────────────────────────
  const weightMut = useMutation({
    mutationFn: (w: number) => logWeight(w),
    onSuccess:  (_, w) => {
      const entry: WeightEntry = { date: new Date().toISOString().slice(0, 10), weight_kg: w };
      appendWeightEntry(entry);
      qc.invalidateQueries({ queryKey: QUERY_KEYS.WEIGHT_HISTORY(30) });
      setWeightSheet(false);
      showToast("Weight logged! ⚖️", "success");
    },
    onError: () => showToast("Failed to log weight", "error"),
  });

  const STREAK_DOTS = [true, true, true, true, false, true, true];
  const STREAK_LABELS = ["M","T","W","T","F","S","S"];

  if (isLoading) return <View style={s.loader}><ActivityIndicator size="large" color={colors.brand[600]} /></View>;

  return (
    <View style={s.root}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>
        <CopilotStep text="Track your weight, streaks, and macros over time." order={3} name="progress">
          <CopilotScreenHeader title="My Progress" />
        </CopilotStep>

        <View style={s.body}>
          <Text style={s.sectionLabel}>TODAY</Text>

          {/* Weight card */}
          <Animated.View entering={FadeInDown.duration(400).easing(EASE_OUT)}>
            <MetricCard
              icon={<Text style={{ fontSize: 20 }}>⚖️</Text>}
              label="⚖️ Weight"
              value={`${currentWeight} kg`}
              note={targetWeight ? `Goal: ${targetWeight} kg` : undefined}
              noteColor={colors.brand[600]}
              onLog={() => { setTempWeight(currentWeight.toString()); setWeightSheet(true); }}
            />
          </Animated.View>

          {/* Weight journey */}
          <Text style={[s.sectionLabel, { marginTop: 8 }]}>WEIGHT JOURNEY</Text>
          <Animated.View entering={FadeInDown.delay(80).duration(400).easing(EASE_OUT)}>
            <Card style={{ marginBottom: spacing.lg }}>
              <View style={s.weightGrid}>
                <StatPair label="Current" value={`${currentWeight} kg`} highlight />
                <StatPair label="Goal"    value={targetWeight !== null ? `${targetWeight} kg` : "Not set"} />
                <StatPair label="Left"    value={targetWeight !== null ? `${Math.abs(currentWeight - targetWeight).toFixed(1)} kg` : "—"} />
                <StatPair label="Streak"  value={`${streak}d`} />
              </View>
              {weightError ? (
                <ErrorState message="Could not load your weight history" onRetry={() => refetchWeight()} />
              ) : chartData.length > 1 ? (
                <View style={s.chartWrap}>
                  <LineChart
                    data={chartData}
                    color={colors.brand[600]}
                    thickness={2.5}
                    curved
                    hideDataPoints={false}
                    dataPointsColor={colors.brand[600]}
                    dataPointsRadius={4}
                    startFillColor={colors.brand[100]}
                    endFillColor={colors.brand[100]}
                    startOpacity={0.3}
                    endOpacity={0.05}
                    areaChart
                    width={screenWidth - 48}
                    height={180}
                    yAxisTextStyle={{ fontSize: 10, color: colors.gray[400] }}
                    xAxisLabelTextStyle={{ fontSize: 9, color: colors.gray[400] }}
                    noOfSections={4}
                    hideRules
                    xAxisThickness={0}
                    yAxisThickness={0}
                  />
                </View>
              ) : (
                <Text style={s.noData}>Log your weight to see the trend</Text>
              )}
            </Card>
          </Animated.View>

          {/* Streak */}
          <Text style={s.sectionLabel}>STREAK</Text>
          <Animated.View entering={FadeInDown.delay(160).duration(400).easing(EASE_OUT)}>
            <Card>
              <Text style={s.streakBig}>🔥 {streak} Day Streak!</Text>
              <Text style={s.streakSub}>Keep logging every day</Text>
              <View style={s.dotRow}>
                {STREAK_DOTS.map((done, i) => (
                  <View key={i} style={s.dotCol}>
                    <Text style={s.dotLabel}>{STREAK_LABELS[i]}</Text>
                    <View style={[s.dot, done && s.dotDone]} />
                  </View>
                ))}
              </View>
            </Card>
          </Animated.View>
        </View>
      </ScrollView>

      {/* ── Weight Sheet ── */}
      <BottomSheet open={weightSheet} onClose={() => setWeightSheet(false)}>
        <View style={sh.gap}>
          <Text style={sh.title}>Log Your Weight</Text>
          <View style={sh.weightRow}>
            <TextInput
              style={sh.weightInput}
              value={tempWeight}
              onChangeText={setTempWeight}
              keyboardType="decimal-pad"
              textAlign="center"
              placeholder="74.5"
            />
            <Text style={sh.kgLabel}>kg</Text>
          </View>
          {parseFloat(tempWeight) > 0 && parseFloat(tempWeight) < currentWeight && (
            <Text style={sh.weightGood}>↓ Down {(currentWeight - parseFloat(tempWeight)).toFixed(1)}kg 🎉</Text>
          )}
          <Button label="Save" onPress={() => weightMut.mutate(parseFloat(tempWeight)||currentWeight)} loading={weightMut.isPending} haptic />
        </View>
      </BottomSheet>
    </View>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────
function MetricCard({ icon, label, value, pct, barColor, note, noteColor, onLog }: {
  icon: React.ReactNode; label: string; value: string;
  pct?: number; barColor?: string; note?: string; noteColor?: string;
  onLog: () => void;
}) {
  return (
    <View style={s.metricCard}>
      <View style={s.metricIcon}>{icon}</View>
      <View style={s.metricBody}>
        <View style={s.metricRow}>
          <View style={{ flex: 1 }}>
            <Text style={s.metricVal}>{value}</Text>
            {pct !== undefined && (
              <>
                <View style={s.bar}><View style={[s.barFill, { width: `${pct}%` as any, backgroundColor: barColor }]} /></View>
                <Text style={s.metricNote}>{note ?? `${pct}%`}</Text>
              </>
            )}
            {note !== undefined && pct === undefined && (
              <Text style={[s.metricNote, noteColor ? { color: noteColor } : {}]}>{note}</Text>
            )}
          </View>
          <AnimatedPressable onPress={onLog} style={s.logBtn}>
            <Plus size={iconSize.sm} color="#1E7C45" />
            <Text style={s.logBtnText}>Log</Text>
          </AnimatedPressable>
        </View>
      </View>
    </View>
  );
}

function StatPair({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <View style={s.statPair}>
      <Text style={s.statVal}>{value}</Text>
      <Text style={[s.statLabel, highlight && { color: "#1E7C45" }]}>{label}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  root:       { flex: 1, backgroundColor: "#F9FAFB" },
  loader:     { flex: 1, alignItems: "center", justifyContent: "center" },
  scroll:     { paddingBottom: 32 },
  body:       { paddingHorizontal: 20, paddingTop: 16 },
  sectionLabel:{ fontSize: 11, fontWeight: "600", color: "#374151", letterSpacing: 1, marginBottom: 10 },
  metricCard: { flexDirection: "row", alignItems: "flex-start", gap: 12, backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 14, marginBottom: 10 },
  metricIcon: { width: 44, height: 44, borderRadius: 10, backgroundColor: "#F9FAFB", alignItems: "center", justifyContent: "center" },
  metricBody: { flex: 1 },
  metricRow:  { flexDirection: "row", alignItems: "flex-start" },
  metricVal:  { ...typography.statValue },
  bar:        { height: 6, backgroundColor: "#E5E7EB", borderRadius: 99, marginTop: 6, overflow: "hidden" },
  barFill:    { height: "100%", borderRadius: 99 },
  metricNote: { fontSize: 11, color: "#9CA3AF", marginTop: 3 },
  logBtn:     { flexDirection: "row", alignItems: "center", gap: 4, height: 32, paddingHorizontal: 12, borderRadius: 99, backgroundColor: "#F0FDF4" },
  logBtnText: { fontSize: 13, fontWeight: "500", color: "#1E7C45" },
  weightGrid: { flexDirection: "row", flexWrap: "wrap", gap: 12, marginBottom: 14 },
  statPair:   { alignItems: "center", minWidth: "40%" },
  statVal:    { ...typography.statValue },
  statLabel:  { fontSize: 12, color: "#6B7280", marginTop: 2 },
  chartWrap:  { marginTop: 4, marginLeft: -8 },
  noData:     { fontSize: 12, color: "#9CA3AF", textAlign: "center", paddingVertical: 16 },
  streakBig:  { fontSize: 20, fontWeight: "700", color: "#D97706" },
  streakSub:  { fontSize: 13, color: "#6B7280", marginTop: 4 },
  dotRow:     { flexDirection: "row", gap: 8, marginTop: 12 },
  dotCol:     { alignItems: "center", gap: 4 },
  dotLabel:   { fontSize: 10, color: "#9CA3AF" },
  dot:        { width: 10, height: 10, borderRadius: 5, backgroundColor: "#E5E7EB" },
  dotDone:    { backgroundColor: "#34B164" },
});

const sh = StyleSheet.create({
  gap:         { gap: 16 },
  title:       { fontSize: 18, fontWeight: "600", color: "#111827" },
  weightRow:   { flexDirection: "row", alignItems: "center", gap: 10, alignSelf: "center" },
  weightInput: { width: 100, height: 64, borderRadius: 12, borderWidth: 1.5, borderColor: "#1E7C45", fontSize: 28, fontWeight: "700", color: "#111827" },
  kgLabel:     { fontSize: 20, fontWeight: "600", color: "#374151" },
  weightGood:  { textAlign: "center", fontSize: 13, color: "#34B164", fontWeight: "500" },
});
