import React, { useRef, useEffect } from "react";
import { View, Text, Pressable, StyleSheet, ScrollView } from "react-native";
import Animated, { useSharedValue, useAnimatedStyle, withSpring } from "react-native-reanimated";
// @react-native-clipboard/clipboard requires a native build; not available in Expo Go.
// Lazy-require with fallback so the module loads in both environments.
let Clipboard: { setString: (text: string) => void } | null = null;
try {
  Clipboard = require("@react-native-clipboard/clipboard").default;
} catch {
  Clipboard = null;
}
import { useRouter } from "expo-router";
import { ChevronLeft, Copy, CheckCircle2 } from "lucide-react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { getRequestStatus, getMyVisit } from "../../services/profile";
import { useAuthStore } from "../../store/useAuthStore";
import { getMyProfile } from "../../services/profile";
import { useToast } from "../../components/shared";

type SubStatus = "active" | "pending" | "none";

const CONFIG: Record<SubStatus, {
  emoji: string; title: string; color: string; bg: string; border: string;
  subtitle: (name?: string) => string; body: string;
  badge: { text: string; bg: string; color: string } | null;
}> = {
  active: {
    emoji: "✅", title: "Connected!", color: "#1E7C45", bg: "#F0FDF4", border: "#DCFCE7",
    subtitle: (name) => `You are connected to ${name ?? "your doctor"}`,
    body: "Your doctor has been notified and will create your personalised meal plan within 24–48 hours.",
    badge: { text: "Active", bg: "#DCFCE7", color: "#166534" },
  },
  pending: {
    emoji: "⏳", title: "Request Sent", color: "#D97706", bg: "#FFFBEB", border: "#FDE68A",
    subtitle: () => "Waiting for your doctor to accept",
    body: "Your doctor will review your profile and accept your request shortly. This page updates automatically.",
    badge: { text: "Pending", bg: "#FEF3C7", color: "#92400E" },
  },
  none: {
    emoji: "🔍", title: "Not Connected", color: "#6B7280", bg: "#F9FAFB", border: "#E5E7EB",
    subtitle: () => "You don't have an active doctor connection",
    body: "Connect with a dietician to get a personalised meal plan tailored to your health goals.",
    badge: null,
  },
};

export default function ConnectionStatusScreen() {
  const router = useRouter();
  const { showToast } = useToast();
  const { profile, setProfile } = useAuthStore();
  const qc = useQueryClient();
  const prevStatus = useRef<string | null>(null);
  const celebrateAnim = useSharedValue(0);

  // ── Poll request status every 30s until accepted ──────────────────────
  const { data: reqStatus } = useQuery({
    queryKey: QUERY_KEYS.REQUEST_STATUS,
    queryFn: getRequestStatus,
    enabled: !!profile,
    refetchInterval: (data) =>
      (data?.status === "accepted" || profile?.subscription_status === "active") ? false : 30_000,
    refetchIntervalInBackground: false,
  });

  // ── When request is accepted, refresh the profile so JWT sub_status syncs
  useEffect(() => {
    const current = reqStatus?.status;
    if (prevStatus.current === "pending" && current === "accepted") {
      celebrateAnim.value = withSpring(1, { damping: 6 });
      getMyProfile().then((p) => {
        setProfile(p);
        qc.invalidateQueries({ queryKey: QUERY_KEYS.ME });
        showToast("Your doctor accepted you! 🎉", "success");
      }).catch(() => {});
    }
    prevStatus.current = current ?? null;
  }, [reqStatus?.status]);

  // ── Fetch Token 2 / visit info when active ─────────────────────────────
  const subStatus: SubStatus =
    profile?.subscription_status === "active" ? "active" :
    reqStatus?.status === "pending"            ? "pending" : "none";

  const { data: visitData } = useQuery({
    queryKey: QUERY_KEYS.MY_VISIT,
    queryFn: getMyVisit,
    enabled: subStatus === "active",
    staleTime: 60_000,
  });

  const cfg = CONFIG[subStatus];
  const doctorName = (profile as any)?.doctor_name ?? undefined;

  // Copy token 2 to clipboard
  const copyToken2 = () => {
    if (visitData?.token_2) {
      Clipboard?.setString(visitData.token_2);
      showToast("Token 2 copied!", "success");
    }
  };

  const cardAnimStyle = useAnimatedStyle(() => ({
    transform: [{ scale: 1 + celebrateAnim.value * 0.03 }],
  }));

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Connection Status</Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>

        {/* Status card — animates on accept */}
        <Animated.View style={[{ width: "100%" }, cardAnimStyle]}>
          <View style={[s.statusCard, { backgroundColor: cfg.bg, borderColor: cfg.border }]}>
            <Text style={s.statusEmoji}>{cfg.emoji}</Text>
            <Text style={[s.statusTitle, { color: cfg.color }]}>{cfg.title}</Text>
            <Text style={s.statusSub}>{cfg.subtitle(doctorName)}</Text>
            {cfg.badge && (
              <View style={[s.badge, { backgroundColor: cfg.badge.bg }]}>
                <Text style={[s.badgeText, { color: cfg.badge.color }]}>{cfg.badge.text}</Text>
              </View>
            )}
          </View>
        </Animated.View>

        {/* Info body */}
        <View style={s.infoCard}>
          <Text style={s.infoText}>{cfg.body}</Text>
        </View>

        {/* ── Active — subscription details ───────────────────────────── */}
        {subStatus === "active" && profile && (
          <View style={s.detailCard}>
            {[
              { label: "Status", value: "Active ✅" },
              {
                label: "Expires",
                value: (() => {
                  const raw = profile.subscription_end_date ?? profile.token_1_expiry;
                  if (!raw) return "—";
                  return new Date(raw).toLocaleDateString("en-IN", {
                    day: "numeric", month: "short", year: "numeric"
                  });
                })(),
              },
            ].map((row, i, arr) => (
              <View key={row.label} style={[s.detailRow, i < arr.length - 1 && s.detailBorder]}>
                <Text style={s.detailLabel}>{row.label}</Text>
                <Text style={s.detailValue}>{row.value}</Text>
              </View>
            ))}
          </View>
        )}

        {/* ── Token 2 / visit cycle card (active patients only) ──────── */}
        {subStatus === "active" && visitData?.has_visit && (
          <View style={s.visitCard}>
            <Text style={s.visitCardTitle}>Visit Cycle (Token 2)</Text>
            <Text style={s.visitHint}>Share this code with your doctor at your clinic visit</Text>
            <View style={s.tokenRow}>
              <Text style={s.token2Text}>{visitData.token_2}</Text>
              <Pressable onPress={copyToken2} style={s.copyBtn} hitSlop={8}>
                <Copy size={15} color="#1E7C45" />
              </Pressable>
            </View>
            <View style={s.visitStats}>
              {[
                { label: "Visits this cycle", value: String(visitData.visit_counter) },
                {
                  label: "Cycle expiry",
                  value: visitData.cycle_expiry
                    ? new Date(visitData.cycle_expiry).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
                    : "—"
                },
              ].map((item, i, arr) => (
                <View key={item.label} style={[s.visitStatItem, i < arr.length - 1 && s.visitStatBorder]}>
                  <Text style={s.visitStatLabel}>{item.label}</Text>
                  <Text style={s.visitStatValue}>{item.value}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* ── Active with no visit cycle yet ──────────────────────────── */}
        {subStatus === "active" && visitData && !visitData.has_visit && (
          <View style={[s.visitCard, { alignItems: "center", paddingVertical: 20 }]}>
            <CheckCircle2 size={28} color="#9CA3AF" />
            <Text style={[s.visitHint, { textAlign: "center", marginTop: 8 }]}>
              Token 2 will appear here after your first clinic visit is recorded by your doctor.
            </Text>
          </View>
        )}

        {/* ── CTAs ─────────────────────────────────────────────────────── */}
        {subStatus === "active" && (
          <Pressable style={s.primaryBtn} onPress={() => router.replace("/(tabs)")}>
            <Text style={s.primaryBtnText}>View My Meal Plan</Text>
          </Pressable>
        )}
        {subStatus === "pending" && (
          <Pressable style={s.secondaryBtn} onPress={() => router.replace("/(tabs)")}>
            <Text style={s.secondaryBtnText}>Go to Dashboard</Text>
          </Pressable>
        )}
        {subStatus === "none" && (
          <View style={s.ctaStack}>
            <Pressable style={s.primaryBtn} onPress={() => router.push("/doctor/activate")}>
              <Text style={s.primaryBtnText}>Have a Code? Activate</Text>
            </Pressable>
            <Pressable style={s.secondaryBtn} onPress={() => router.push("/doctor/find-doctor")}>
              <Text style={s.secondaryBtnText}>Find a Doctor</Text>
            </Pressable>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root:             { flex: 1, backgroundColor: "#F9FAFB" },
  header:           { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:          { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:            { fontSize: 18, fontWeight: "600", color: "#111827" },
  scroll:           { alignItems: "center", padding: 24, gap: 16 },
  statusCard:       { width: "100%", borderWidth: 1.5, borderRadius: 20, padding: 28, alignItems: "center", gap: 8 },
  statusEmoji:      { fontSize: 52 },
  statusTitle:      { fontSize: 22, fontWeight: "700" },
  statusSub:        { fontSize: 14, color: "#374151", textAlign: "center" },
  badge:            { borderRadius: 99, paddingHorizontal: 14, paddingVertical: 4 },
  badgeText:        { fontSize: 12, fontWeight: "600" },
  infoCard:         { width: "100%", backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 16 },
  infoText:         { fontSize: 14, color: "#374151", lineHeight: 22 },
  detailCard:       { width: "100%", backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", overflow: "hidden" },
  detailRow:        { flexDirection: "row", justifyContent: "space-between", padding: 14 },
  detailBorder:     { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  detailLabel:      { fontSize: 13, color: "#6B7280" },
  detailValue:      { fontSize: 13, fontWeight: "600", color: "#111827" },
  visitCard:        { width: "100%", backgroundColor: "#fff", borderRadius: 12, borderWidth: 1.5, borderColor: "#DCFCE7", padding: 16, gap: 8 },
  visitCardTitle:   { fontSize: 14, fontWeight: "700", color: "#111827" },
  visitHint:        { fontSize: 12, color: "#6B7280", lineHeight: 18 },
  tokenRow:         { flexDirection: "row", alignItems: "center", justifyContent: "space-between", backgroundColor: "#F0FDF4", borderRadius: 10, paddingHorizontal: 14, paddingVertical: 12, marginTop: 4 },
  token2Text:       { fontSize: 16, fontWeight: "700", color: "#1E7C45", fontFamily: "monospace", letterSpacing: 1 },
  copyBtn:          { padding: 6, borderRadius: 8, backgroundColor: "#DCFCE7" },
  visitStats:       { borderWidth: 1, borderColor: "#E5E7EB", borderRadius: 10, overflow: "hidden", marginTop: 4 },
  visitStatItem:    { flexDirection: "row", justifyContent: "space-between", alignItems: "center", padding: 12 },
  visitStatBorder:  { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  visitStatLabel:   { fontSize: 12, color: "#6B7280" },
  visitStatValue:   { fontSize: 13, fontWeight: "600", color: "#111827" },
  ctaStack:         { width: "100%", gap: 10 },
  primaryBtn:       { width: "100%", height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  primaryBtnText:   { fontSize: 16, fontWeight: "600", color: "#fff" },
  secondaryBtn:     { width: "100%", height: 52, borderRadius: 26, backgroundColor: "#fff", borderWidth: 1.5, borderColor: "#E5E7EB", alignItems: "center", justifyContent: "center" },
  secondaryBtnText: { fontSize: 15, fontWeight: "500", color: "#374151" },
});
