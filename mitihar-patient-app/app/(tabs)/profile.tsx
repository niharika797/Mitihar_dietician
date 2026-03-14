import React from "react";
import { View, Text, ScrollView, Pressable, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import { ChevronRight, Edit2, Bell, Info, LogOut, User } from "lucide-react-native";
import { useAuthStore } from "../../store/useAuthStore";
import { useToast } from "../../components/shared";
import { logoutPatient } from "../../services/auth";
import { computeHealthStats } from "../../utils/calculations";

export default function ProfileScreen() {
  const router = useRouter();
  const { showToast } = useToast();
  const { profile, logout } = useAuthStore();

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
    { icon: Edit2, label: "Edit Profile",               path: "/profile/edit-profile"    },
    { icon: Bell,  label: "Notification Preferences",   path: "/profile/notifications"   },
    { icon: Info,  label: "About & Disclaimer",         path: "/profile/about"           },
  ];

  const subStatus = profile?.subscription_status;
  const subExpiry = profile?.subscription_end_date;

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

        {/* Subscription */}
        <Text style={s.sectionLabel}>SUBSCRIPTION</Text>
        <View style={[s.subCard, subStatus === "active" ? s.subActive : s.subInactive]}>
          <View style={{ flex: 1 }}>
            <Text style={s.subTitle}>
              {subStatus === "active" ? "✅ Active Plan" : "❌ No Active Plan"}
            </Text>
            {subStatus === "active" && subExpiry && (
              <Text style={s.subSub}>Expires: {subExpiry.slice(0, 10)}</Text>
            )}
          </View>
          {subStatus !== "active" && (
            <Pressable onPress={() => router.push("/doctor/activate")} style={s.activateBtn}>
              <Text style={s.activateBtnText}>Activate</Text>
            </Pressable>
          )}
        </View>

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
  logoutBtn:     { height: 52, borderRadius: 26, backgroundColor: "#FFF1F2", borderWidth: 1.5, borderColor: "#FECDD3", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 },
  logoutText:    { fontSize: 15, fontWeight: "600", color: "#DC2626" },
});
