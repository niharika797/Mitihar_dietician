import React from "react";
import { View, Text, Pressable, StyleSheet, ScrollView } from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import { useQuery } from "@tanstack/react-query";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { getRequestStatus } from "../../services/profile";
import { useAuthStore } from "../../store/useAuthStore";

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
    subtitle: (name) => `Waiting for ${name ?? "your doctor"} to accept`,
    body: "Your doctor will review your profile and accept your request shortly.",
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
  const profile = useAuthStore(s => s.profile);

  const { data: reqStatus } = useQuery({
    queryKey: QUERY_KEYS.REQUEST_STATUS,
    queryFn: getRequestStatus,
    enabled: !!profile,
  });

  const subStatus: SubStatus =
    profile?.subscription_status === "active" ? "active" :
    reqStatus?.status === "pending"            ? "pending" : "none";

  const cfg = CONFIG[subStatus];
  const doctorName = (profile as any)?.doctor_name ?? undefined;

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
        {/* Status card */}
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

        {/* Info body */}
        <View style={s.infoCard}>
          <Text style={s.infoText}>{cfg.body}</Text>
        </View>

        {/* Active — connection details */}
        {subStatus === "active" && profile && (
          <View style={s.detailCard}>
            {[
              { label: "Status",    value: "Active ✅"                                         },
              { label: "Expires",   value: profile.subscription_end_date?.slice(0, 10) ?? "—" },
            ].map((row, i, arr) => (
              <View key={row.label} style={[s.detailRow, i < arr.length - 1 && s.detailBorder]}>
                <Text style={s.detailLabel}>{row.label}</Text>
                <Text style={s.detailValue}>{row.value}</Text>
              </View>
            ))}
          </View>
        )}

        {/* CTAs */}
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
  root:          { flex: 1, backgroundColor: "#F9FAFB" },
  header:        { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:       { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:         { fontSize: 18, fontWeight: "600", color: "#111827" },
  scroll:        { alignItems: "center", padding: 24, gap: 16 },
  statusCard:    { width: "100%", borderWidth: 1.5, borderRadius: 20, padding: 28, alignItems: "center", gap: 8 },
  statusEmoji:   { fontSize: 52 },
  statusTitle:   { fontSize: 22, fontWeight: "700" },
  statusSub:     { fontSize: 14, color: "#374151", textAlign: "center" },
  badge:         { borderRadius: 99, paddingHorizontal: 14, paddingVertical: 4 },
  badgeText:     { fontSize: 12, fontWeight: "600" },
  infoCard:      { width: "100%", backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 16 },
  infoText:      { fontSize: 14, color: "#374151", lineHeight: 22 },
  detailCard:    { width: "100%", backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", overflow: "hidden" },
  detailRow:     { flexDirection: "row", justifyContent: "space-between", padding: 14 },
  detailBorder:  { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  detailLabel:   { fontSize: 13, color: "#6B7280" },
  detailValue:   { fontSize: 13, fontWeight: "600", color: "#111827" },
  ctaStack:      { width: "100%", gap: 10 },
  primaryBtn:    { width: "100%", height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  primaryBtnText:{ fontSize: 16, fontWeight: "600", color: "#fff" },
  secondaryBtn:  { width: "100%", height: 52, borderRadius: 26, backgroundColor: "#fff", borderWidth: 1.5, borderColor: "#E5E7EB", alignItems: "center", justifyContent: "center" },
  secondaryBtnText:{ fontSize: 15, fontWeight: "500", color: "#374151" },
});
