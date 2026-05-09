import React, { useState, useEffect } from "react";
import { View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { ChevronRight, Edit2, Bell, Info, LogOut, User, RefreshCw, Settings } from "lucide-react-native";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "../../store/useAuthStore";
import { useToast } from "../../components/shared";
import { logoutPatient } from "../../services/auth";
import { requestRenewal, getMyProfile } from "../../services/profile";
import { computeHealthStats } from "../../utils/calculations";

export default function ProfileScreen() {
  const router = useRouter();
  const { showToast } = useToast();
  const { profile, logout, setProfile } = useAuthStore();
  const queryClient = useQueryClient();

  // Always refresh profile from server when the tab is opened so subscription
  // status, BMI, TDEE and token data are always current.
  useEffect(() => {
    getMyProfile()
      .then(setProfile)
      .catch(() => {});
  }, []);

  const stats = profile?.date_of_birth
    ? computeHealthStats({
        weight_kg:      profile.weight_kg,
        height_cm:      profile.height_cm,
        date_of_birth:  profile.date_of_birth,
        gender:         profile.gender,
        activity_level: profile.activity_level,
      })
    : null;

  const handleLogout = async () => {
    try { await logoutPatient(); } catch {}
    await logout();
    // Clear all cached query data so a different account logging in
    // on the same device never sees the previous user's meals, progress
    // or profile data, even briefly before the first fresh fetch.
    queryClient.clear();
    showToast("Logged out successfully", "success");
    router.replace("/(auth)/login");
  };

  const STATS = [
    { label: "BMI",    value: stats ? stats.bmi.toFixed(1) : "—" },
    { label: "Weight", value: profile ? `${profile.weight_kg} kg` : "—" },
    { label: "Target", value: profile?.target_weight_kg ? `${profile.target_weight_kg} kg` : "—" },
    { label: "TDEE",   value: stats ? `${stats.tdee}` : "—" },
  ];

  const MENU = [
    { icon: Edit2,     label: "Edit Profile",             path: "/profile/edit-profile"  },
    { icon: Bell,      label: "Notification Preferences", path: "/profile/notifications" },
    { icon: Settings,  label: "Account & Security",       path: "/profile/account"       },
    { icon: Info,      label: "About & Disclaimer",       path: "/profile/about"         },
  ];

  const subStatus = profile?.subscription_status;
  const subExpiry = profile?.subscription_end_date;

  // Token 1 data
  const token1 = profile?.token_1;
  const token1Active = profile?.token_1_active ?? false;
  const token1Expiry = profile?.token_1_expiry;
  const renewalRequested = profile?.renewal_requested ?? false;
  const expiringSoon = profile?.expiring_soon ?? false;

  // Days remaining calculation
  const daysLeft = token1Expiry
    ? Math.max(0, Math.ceil((new Date(token1Expiry).getTime() - Date.now()) / 86_400_000))
    : null;
  const progressPct = daysLeft !== null ? Math.min(100, Math.round((daysLeft / 30) * 100)) : 0;
  const showRenewalBtn = token1Active && daysLeft !== null && daysLeft <= 4 && !renewalRequested;

  const renewalMut = useMutation({
    mutationFn: () => requestRenewal(profile!.id),
    onSuccess: () => showToast("Renewal request sent to your doctor 👍", "success"),
    onError: () => showToast("Failed to send request. Try again.", "error"),
  });

  return (
    <ScrollView style={s.root} contentContainerStyle={s.scroll} showsVerticalScrollIndicator={false}>
      {/* Header */}
      <View style={s.header}><Text style={s.headerTitle}>Profile</Text></View>

      <View style={s.body}>
        {/* Avatar card */}
        <View style={s.avatarCard}>
          <View style={s.avatar}>
            <User size={32} color="#fff" />
          </View>
          <View style={s.avatarInfo}>
            <Text style={s.name}>{profile?.name ?? "—"}</Text>
            <Text style={s.email}>{profile?.email ?? "—"}</Text>
            {profile?.phone ? <Text style={s.email}>{profile.phone}</Text> : null}
          </View>
          <Pressable onPress={() => router.push("/profile/edit-profile")} style={s.editBtn}>
            <Edit2 size={16} color="#1E7C45" />
          </Pressable>
        </View>

        {/* Stats grid */}
        <View style={s.statsGrid}>
          {STATS.map(st => (
            <View key={st.label} style={s.statCard}>
              <Text style={s.statVal}>{st.value}</Text>
              <Text style={s.statLabel}>{st.label}</Text>
            </View>
          ))}
        </View>

        {/* Subscription & Token 1 */}
        <Text style={s.sectionLabel}>SUBSCRIPTION</Text>
        <View style={[s.subCard, token1Active ? (expiringSoon ? s.subExpiring : s.subActive) : s.subInactive]}>
          <View style={{ flex: 1 }}>
            <Text style={s.subTitle}>
              {renewalRequested
                ? "🔄 Renewal Requested"
                : expiringSoon
                ? "⚠️ Expiring Soon"
                : token1Active
                ? "✅ Active Plan"
                : "❌ No Active Plan"}
            </Text>
            {token1 && (
              <Text style={s.tokenId}>Patient ID: {token1}</Text>
            )}
            {daysLeft !== null && token1Active && (
              <View style={{ marginTop: 8 }}>
                <View style={s.progressBg}>
                  <View style={[s.progressFill, { width: `${progressPct}%` as any, backgroundColor: expiringSoon ? '#F59E0B' : '#1E7C45' }]} />
                </View>
                <Text style={s.daysLeft}>{daysLeft} days remaining</Text>
              </View>
            )}
          </View>
          {!token1Active && (
            <Pressable onPress={() => router.push("/doctor/activate")} style={s.activateBtn}>
              <Text style={s.activateBtnText}>Activate</Text>
            </Pressable>
          )}
        </View>

        {/* Renewal request button */}
        {showRenewalBtn && (
          <Pressable
            onPress={() => renewalMut.mutate()}
            disabled={renewalMut.isPending}
            style={[s.renewalBtn, renewalMut.isPending && { opacity: 0.6 }]}
          >
            {renewalMut.isPending
              ? <ActivityIndicator size="small" color="#fff" />
              : <RefreshCw size={16} color="#fff" />}
            <Text style={s.renewalBtnText}>Request Renewal</Text>
          </Pressable>
        )}
        {renewalRequested && (
          <View style={s.renewalSentBanner}>
            <Text style={s.renewalSentText}>✅ Renewal request sent — waiting for doctor approval</Text>
          </View>
        )}

        {/* Settings menu */}
        <Text style={s.sectionLabel}>SETTINGS</Text>
        <View style={s.menuCard}>
          {MENU.map((item, i) => {
            const Icon = item.icon;
            return (
              <Pressable key={item.label} onPress={() => router.push(item.path as any)} style={[s.menuRow, i < MENU.length - 1 && s.menuBorder]}>
                <View style={s.menuIcon}>
                  <Icon size={18} color="#374151" />
                </View>
                <Text style={s.menuLabel}>{item.label}</Text>
                <ChevronRight size={16} color="#9CA3AF" />
              </Pressable>
            );
          })}
        </View>

        {/* Logout */}
        <Pressable onPress={handleLogout} style={s.logoutBtn}>
          <LogOut size={18} color="#DC2626" />
          <Text style={s.logoutText}>Log Out</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root:          { flex: 1, backgroundColor: "#F9FAFB" },
  scroll:        { paddingBottom: 40 },
  header:        { backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB", padding: 16 },
  headerTitle:   { fontSize: 20, fontWeight: "600", color: "#111827" },
  body:          { paddingHorizontal: 20, paddingTop: 20, gap: 16 },
  avatarCard:    { backgroundColor: "#fff", borderRadius: 16, borderWidth: 1, borderColor: "#E5E7EB", padding: 20, flexDirection: "row", alignItems: "center", gap: 16 },
  avatar:        { width: 72, height: 72, borderRadius: 36, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  avatarInfo:    { flex: 1 },
  name:          { fontSize: 18, fontWeight: "700", color: "#111827" },
  email:         { fontSize: 13, color: "#6B7280", marginTop: 2 },
  editBtn:       { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F0FDF4", alignItems: "center", justifyContent: "center" },
  statsGrid:     { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  statCard:      { flexBasis: "47%", flexGrow: 1, backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 14, alignItems: "center" },
  statVal:       { fontSize: 20, fontWeight: "700", color: "#111827" },
  statLabel:     { fontSize: 12, color: "#6B7280", marginTop: 2 },
  sectionLabel:  { fontSize: 11, fontWeight: "600", color: "#374151", letterSpacing: 1 },
  subCard:       { borderRadius: 12, borderWidth: 1, padding: 14, flexDirection: "row", alignItems: "center" },
  subActive:     { backgroundColor: "#F0FDF4", borderColor: "#DCFCE7" },
  subInactive:   { backgroundColor: "#FEF3C7", borderColor: "#FCD34D" },
  subTitle:      { fontSize: 14, fontWeight: "600", color: "#111827" },
  subSub:        { fontSize: 12, color: "#6B7280", marginTop: 2 },
  activateBtn:   { height: 34, paddingHorizontal: 14, borderRadius: 99, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  activateBtnText:{ fontSize: 12, fontWeight: "600", color: "#fff" },
  menuCard:      { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", overflow: "hidden" },
  menuRow:       { flexDirection: "row", alignItems: "center", gap: 14, padding: 15 },
  menuBorder:    { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  menuIcon:      { width: 36, height: 36, borderRadius: 10, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  menuLabel:     { flex: 1, fontSize: 14, fontWeight: "500", color: "#111827" },
  logoutBtn:       { height: 52, borderRadius: 26, backgroundColor: "#FFF1F2", borderWidth: 1.5, borderColor: "#FECDD3", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 },
  logoutText:      { fontSize: 15, fontWeight: "600", color: "#DC2626" },
  subExpiring:     { backgroundColor: "#FFFBEB", borderColor: "#FCD34D" },
  tokenId:         { fontSize: 11, color: "#6B7280", marginTop: 4, fontFamily: "monospace" },
  progressBg:      { height: 6, borderRadius: 99, backgroundColor: "#E5E7EB", overflow: "hidden" },
  progressFill:    { height: 6, borderRadius: 99 },
  daysLeft:        { fontSize: 11, color: "#6B7280", marginTop: 4 },
  renewalBtn:      { height: 48, borderRadius: 24, backgroundColor: "#F59E0B", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 },
  renewalBtnText:  { fontSize: 14, fontWeight: "600", color: "#fff" },
  renewalSentBanner: { backgroundColor: "#F0FDF4", borderRadius: 10, padding: 12, borderWidth: 1, borderColor: "#DCFCE7" },
  renewalSentText: { fontSize: 13, color: "#166534", textAlign: "center" },
});
