import React, { useState } from "react";
import {
  View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator, TextInput,
} from "react-native";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Droplets, Footprints, Plus } from "lucide-react-native";
import { BarChart } from "react-native-gifted-charts";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { getTodaySummary, logWater, logSteps, logWeight, getWeightHistory } from "../../services/progress";
import { useAuthStore } from "../../store/useAuthStore";
import { useProgressStore, selectWater, selectSteps } from "../../store/useProgressStore";
import { BottomSheet, useToast } from "../../components/shared";
import type { WeightEntry } from "../../types";

type BarData = { value: number; label?: string; frontColor?: string };

export default function ProgressScreen() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const profile = useAuthStore(s => s.profile);
  const { setLocalWater, setLocalSteps, hydrateWeightHistory, appendWeightEntry } = useProgressStore();

  const [waterSheet,  setWaterSheet]  = useState(false);
  const [stepsSheet,  setStepsSheet]  = useState(false);
  const [weightSheet, setWeightSheet] = useState(false);
  const [tempWater,   setTempWater]   = useState(0);
  const [tempSteps,   setTempSteps]   = useState("");
  const [tempWeight,  setTempWeight]  = useState("");

  const water = useProgressStore(selectWater);
  const steps = useProgressStore(selectSteps);
  const localWeight = useProgressStore(s => s.localWeight);
  const weightHistory = useProgressStore(s => s.weightHistory);

  const { data: today, isLoading } = useQuery({
    queryKey: QUERY_KEYS.TODAY,
    queryFn: getTodaySummary,
    refetchInterval: 60_000,
  });

  const { data: weightData } = useQuery({
    queryKey: QUERY_KEYS.WEIGHT_HISTORY(30),
    queryFn: () => getWeightHistory(30),
  });

  React.useEffect(() => { if (weightData) hydrateWeightHistory(weightData); }, [weightData]);

  const currentWeight = localWeight ?? profile?.weight_kg ?? 0;
  const targetWeight  = profile?.target_weight_kg ?? 0;
  const waterPct  = Math.min(100, Math.round((water / 8) * 100));
  const stepsPct  = Math.min(100, Math.round((steps / 8000) * 100));
  const streak    = today?.streak ?? 0;

  // chart data — last 7 weight entries (guard: weightHistory may be undefined on first load)
  const chartData: BarData[] = (Array.isArray(weightHistory) ? weightHistory : []).slice(-7).map(e => ({
    value: e.weight_kg,
    label: e.date.slice(5), // MM-DD
    frontColor: "#1E7C45",
  }));

  // ── Mutations ─────────────────────────────────────────────────────────────
  const waterMut = useMutation({
    mutationFn: (g: number) => logWater(g),
    onMutate:   (g) => setLocalWater(g),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY }); setWaterSheet(false); showToast("Water saved! 💧", "success"); },
    onError:    () => showToast("Failed to save water", "error"),
  });

  const stepsMut = useMutation({
    mutationFn: (s: number) => logSteps(s),
    onMutate:   (s) => setLocalSteps(s),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: QUERY_KEYS.TODAY }); setStepsSheet(false); showToast("Steps logged! 👟", "success"); },
    onError:    () => showToast("Failed to save steps", "error"),
  });

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

  if (isLoading) return <View style={s.loader}><ActivityIndicator size="large" color="#1E7C45" /></View>;

  return (
    <View style={s.root}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>
        {/* Header */}
        <View style={s.header}><Text style={s.headerTitle}>My Progress</Text></View>

        <View style={s.body}>
          <Text style={s.sectionLabel}>TODAY</Text>

          {/* Water card */}
          <MetricCard
            icon={<Droplets size={20} color="#2563EB" />}
            label="💧 Water"
            value={`${water} / 8 glasses`}
            pct={waterPct}
            barColor="#2563EB"
            onLog={() => { setTempWater(water); setWaterSheet(true); }}
          />
          {/* Steps card */}
          <MetricCard
            icon={<Footprints size={20} color="#1E7C45" />}
            label="👟 Steps"
            value={steps.toLocaleString()}
            pct={stepsPct}
            barColor="#1E7C45"
            note="Goal: 8,000"
            onLog={() => { setTempSteps(steps.toString()); setStepsSheet(true); }}
          />
          {/* Weight card */}
          <MetricCard
            icon={<Text style={{ fontSize: 20 }}>⚖️</Text>}
            label="⚖️ Weight"
            value={`${currentWeight} kg`}
            note={targetWeight ? `Goal: ${targetWeight} kg` : undefined}
            noteColor="#1E7C45"
            onLog={() => { setTempWeight(currentWeight.toString()); setWeightSheet(true); }}
          />

          {/* Weight journey */}
          <Text style={[s.sectionLabel, { marginTop: 8 }]}>WEIGHT JOURNEY</Text>
          <View style={s.card}>
            <View style={s.weightGrid}>
              <StatPair label="Current" value={`${currentWeight} kg`} highlight />
              <StatPair label="Goal"    value={`${targetWeight} kg`} />
              <StatPair label="Left"    value={`${Math.max(0, currentWeight - targetWeight).toFixed(1)} kg`} />
              <StatPair label="Streak"  value={`${streak}d`} />
            </View>
            {chartData.length > 1 ? (
              <View style={s.chartWrap}>
                <BarChart
                  data={chartData}
                  barWidth={24}
                  spacing={16}
                  hideRules
                  xAxisThickness={0}
                  yAxisThickness={0}
                  yAxisTextStyle={{ fontSize: 9, color: "#9CA3AF" }}
                  xAxisLabelTextStyle={{ fontSize: 9, color: "#9CA3AF" }}
                  noOfSections={4}
                  maxValue={Math.max(...chartData.map(d => d.value)) + 2}
                  height={120}
                  barBorderRadius={4}
                />
              </View>
            ) : (
              <Text style={s.noData}>Log your weight to see the trend</Text>
            )}
          </View>

          {/* Streak */}
          <Text style={s.sectionLabel}>STREAK</Text>
          <View style={s.card}>
            <Text style={s.streakBig}>🔥 {streak} Day Streak!</Text>
            <Text style={s.streakSub}>Keep logging every day</Text>
            <View style={s.dotRow}>
              {STREAK_DOTS.map((done, i) => (
                <View key={STREAK_LABELS[i]} style={s.dotCol}>
                  <Text style={s.dotLabel}>{STREAK_LABELS[i]}</Text>
                  <View style={[s.dot, done && s.dotDone]} />
                </View>
              ))}
            </View>
          </View>
        </View>
      </ScrollView>

      {/* ── Water Sheet ── */}
      <BottomSheet open={waterSheet} onClose={() => setWaterSheet(false)}>
        <View style={sh.gap}>
          <Text style={sh.title}>Log Water Intake</Text>
          <View style={sh.counter}>
            <Pressable onPress={() => setTempWater(Math.max(0, tempWater - 1))} style={sh.btn}>
              <Text style={sh.btnText}>−</Text>
            </Pressable>
            <Text style={sh.counterVal}>{tempWater}</Text>
            <Pressable onPress={() => setTempWater(Math.min(20, tempWater + 1))} style={sh.btn}>
              <Text style={sh.btnText}>+</Text>
            </Pressable>
          </View>
          <View style={sh.dropRow}>
            {Array.from({ length: 8 }, (_, i) => (
              <Droplets key={`drop-${i}`} size={20} color={i < tempWater ? "#2563EB" : "#E5E7EB"} />
            ))}
          </View>
          <Pressable style={sh.cta} onPress={() => waterMut.mutate(tempWater)} disabled={waterMut.isPending}>
            {waterMut.isPending ? <ActivityIndicator color="#fff" /> : <Text style={sh.ctaText}>Save</Text>}
          </Pressable>
        </View>
      </BottomSheet>

      {/* ── Steps Sheet ── */}
      <BottomSheet open={stepsSheet} onClose={() => setStepsSheet(false)}>
        <View style={sh.gap}>
          <Text style={sh.title}>Log Steps</Text>
          <TextInput
            style={sh.stepsInput}
            value={tempSteps}
            onChangeText={setTempSteps}
            keyboardType="number-pad"
            textAlign="center"
            placeholder="0"
          />
          <View style={sh.presetRow}>
            {[1000,2000,5000,8000].map(v => (
              <Pressable key={v} onPress={() => setTempSteps(v.toString())} style={sh.preset}>
                <Text style={sh.presetText}>{v.toLocaleString()}</Text>
              </Pressable>
            ))}
          </View>
          <Pressable style={sh.cta} onPress={() => stepsMut.mutate(parseInt(tempSteps)||0)} disabled={stepsMut.isPending}>
            {stepsMut.isPending ? <ActivityIndicator color="#fff" /> : <Text style={sh.ctaText}>Save</Text>}
          </Pressable>
        </View>
      </BottomSheet>

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
          <Pressable style={sh.cta} onPress={() => weightMut.mutate(parseFloat(tempWeight)||currentWeight)} disabled={weightMut.isPending}>
            {weightMut.isPending ? <ActivityIndicator color="#fff" /> : <Text style={sh.ctaText}>Save</Text>}
          </Pressable>
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
          <Pressable onPress={onLog} style={s.logBtn}>
            <Plus size={14} color="#1E7C45" />
            <Text style={s.logBtnText}>Log</Text>
          </Pressable>
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
  header:     { backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB", padding: 16 },
  headerTitle:{ fontSize: 20, fontWeight: "600", color: "#111827" },
  body:       { paddingHorizontal: 20, paddingTop: 16 },
  sectionLabel:{ fontSize: 11, fontWeight: "600", color: "#374151", letterSpacing: 1, marginBottom: 10 },
  card:       { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 16, marginBottom: 16 },
  metricCard: { flexDirection: "row", alignItems: "flex-start", gap: 12, backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 14, marginBottom: 10 },
  metricIcon: { width: 44, height: 44, borderRadius: 10, backgroundColor: "#F9FAFB", alignItems: "center", justifyContent: "center" },
  metricBody: { flex: 1 },
  metricRow:  { flexDirection: "row", alignItems: "flex-start" },
  metricVal:  { fontSize: 16, fontWeight: "700", color: "#111827" },
  bar:        { height: 6, backgroundColor: "#E5E7EB", borderRadius: 99, marginTop: 6, overflow: "hidden" },
  barFill:    { height: "100%", borderRadius: 99 },
  metricNote: { fontSize: 11, color: "#9CA3AF", marginTop: 3 },
  logBtn:     { flexDirection: "row", alignItems: "center", gap: 4, height: 32, paddingHorizontal: 12, borderRadius: 99, backgroundColor: "#F0FDF4" },
  logBtnText: { fontSize: 13, fontWeight: "500", color: "#1E7C45" },
  weightGrid: { flexDirection: "row", flexWrap: "wrap", gap: 12, marginBottom: 14 },
  statPair:   { alignItems: "center", minWidth: "40%" },
  statVal:    { fontSize: 16, fontWeight: "700", color: "#111827" },
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
  counter:     { flexDirection: "row", alignItems: "center", gap: 24, alignSelf: "center" },
  btn:         { width: 48, height: 48, borderRadius: 24, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  btnText:     { fontSize: 24, color: "#fff", lineHeight: 28 },
  counterVal:  { fontSize: 40, fontWeight: "700", color: "#111827", minWidth: 48, textAlign: "center" },
  dropRow:     { flexDirection: "row", gap: 6, alignSelf: "center" },
  stepsInput:  { height: 64, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", fontSize: 28, fontWeight: "700", color: "#111827" },
  presetRow:   { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  preset:      { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 99, borderWidth: 1, borderColor: "#E5E7EB", backgroundColor: "#F9FAFB" },
  presetText:  { fontSize: 13, color: "#374151", fontWeight: "500" },
  weightRow:   { flexDirection: "row", alignItems: "center", gap: 10, alignSelf: "center" },
  weightInput: { width: 100, height: 64, borderRadius: 12, borderWidth: 1.5, borderColor: "#1E7C45", fontSize: 28, fontWeight: "700", color: "#111827" },
  kgLabel:     { fontSize: 20, fontWeight: "600", color: "#374151" },
  weightGood:  { textAlign: "center", fontSize: 13, color: "#34B164", fontWeight: "500" },
  cta:         { height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  ctaText:     { fontSize: 16, fontWeight: "600", color: "#fff" },
});
