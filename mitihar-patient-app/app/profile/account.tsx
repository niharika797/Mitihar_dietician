import React, { useState, useEffect } from "react";
import { View, Text, Pressable, StyleSheet, Alert, Switch } from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft, ChevronRight, Trash2, Shield, LogOut, Fingerprint } from "lucide-react-native";
import { useMutation } from "@tanstack/react-query";
import { logoutPatient } from "../../services/auth";
import { useAuthStore } from "../../store/useAuthStore";
import { useBiometricStore } from "../../store/useBiometricStore";
import { useToast } from "../../components/shared";

export default function AccountScreen() {
  const router = useRouter();
  const { showToast } = useToast();
  const logout = useAuthStore(s => s.logout);
  const profile = useAuthStore(s => s.profile);
  const { enabled, hardwareAvailable, enrolled, setEnabled, checkHardware } = useBiometricStore();

  // Probe device capabilities on mount
  useEffect(() => { checkHardware(); }, []);

  const logoutMut = useMutation({
    mutationFn: logoutPatient,
    onSettled: () => {
      logout();
      router.replace("/(auth)/login");
    },
  });

  const handleDeleteAccount = () => {
    Alert.alert(
      "Delete Account",
      "This will permanently delete your account and all associated data. This action cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        { text: "Delete", style: "destructive", onPress: () => showToast("Please contact support to delete your account.", "error") },
      ]
    );
  };

  const handleBiometricToggle = async (val: boolean) => {
    if (val && !enrolled) {
      showToast("No biometrics enrolled on this device. Please add a fingerprint in Settings.", "error");
      return;
    }
    await setEnabled(val);
    showToast(val ? "Fingerprint unlock enabled 🔒" : "Fingerprint unlock disabled", val ? "success" : "info");
  };

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Account</Text>
        <View style={{ width: 36 }} />
      </View>

      {/* Identity */}
      <View style={s.identityCard}>
        <View style={s.avatar}><Text style={s.avatarText}>{(profile?.name ?? "U")[0].toUpperCase()}</Text></View>
        <View>
          <Text style={s.idName}>{profile?.name ?? "—"}</Text>
          <Text style={s.idEmail}>{profile?.email ?? "—"}</Text>
        </View>
      </View>

      {/* Security settings */}
      <View style={s.actionsCard}>
        {/* Change Password */}
        <Pressable style={[s.actionRow, s.actionBorder]} onPress={() => showToast("Password reset email sent!", "success")}>
          <View style={s.actionLeft}>
            <Shield size={16} color="#6B7280" />
            <Text style={s.actionLabel}>Change Password</Text>
          </View>
          <ChevronRight size={16} color="#9CA3AF" />
        </Pressable>

        {/* Biometric toggle — only shown if hardware exists */}
        {hardwareAvailable && (
          <View style={s.actionRow}>
            <View style={s.actionLeft}>
              <Fingerprint size={16} color="#1E7C45" />
              <View>
                <Text style={s.actionLabel}>Fingerprint Unlock</Text>
                <Text style={s.actionSub}>
                  {enrolled ? "Unlock app with biometrics" : "No fingerprint enrolled on device"}
                </Text>
              </View>
            </View>
            <Switch
              value={enabled}
              onValueChange={handleBiometricToggle}
              trackColor={{ false: "#E5E7EB", true: "#34B164" }}
              thumbColor="#fff"
              disabled={!enrolled}
            />
          </View>
        )}
      </View>

      {/* Logout */}
      <Pressable style={s.logoutBtn} onPress={() => logoutMut.mutate()}>
        <LogOut size={16} color="#DC2626" />
        <Text style={s.logoutText}>Log Out</Text>
      </Pressable>

      {/* Danger zone */}
      <View style={s.dangerCard}>
        <Text style={s.dangerTitle}>Danger Zone</Text>
        <Pressable style={s.deleteBtn} onPress={handleDeleteAccount}>
          <Trash2 size={15} color="#DC2626" />
          <Text style={s.deleteBtnText}>Delete My Account</Text>
        </Pressable>
        <Text style={s.dangerSub}>This will permanently remove all your data.</Text>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  root:           { flex: 1, backgroundColor: "#F9FAFB" },
  header:         { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:        { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:          { fontSize: 18, fontWeight: "600", color: "#111827" },
  identityCard:   { flexDirection: "row", alignItems: "center", gap: 14, backgroundColor: "#fff", padding: 20, borderBottomWidth: 1, borderColor: "#E5E7EB", marginBottom: 16 },
  avatar:         { width: 48, height: 48, borderRadius: 24, backgroundColor: "#F0FDF4", alignItems: "center", justifyContent: "center" },
  avatarText:     { fontSize: 20, fontWeight: "700", color: "#1E7C45" },
  idName:         { fontSize: 16, fontWeight: "600", color: "#111827" },
  idEmail:        { fontSize: 13, color: "#6B7280" },
  actionsCard:    { backgroundColor: "#fff", borderTopWidth: 1, borderBottomWidth: 1, borderColor: "#E5E7EB", marginBottom: 12 },
  actionRow:      { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, paddingVertical: 14 },
  actionBorder:   { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  actionLeft:     { flexDirection: "row", alignItems: "center", gap: 12, flex: 1 },
  actionLabel:    { fontSize: 14, color: "#374151" },
  actionSub:      { fontSize: 11, color: "#9CA3AF", marginTop: 1 },
  logoutBtn:      { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, backgroundColor: "#fff", borderTopWidth: 1, borderBottomWidth: 1, borderColor: "#E5E7EB", paddingVertical: 14, marginBottom: 24 },
  logoutText:     { fontSize: 15, fontWeight: "600", color: "#DC2626" },
  dangerCard:     { marginHorizontal: 20, backgroundColor: "#FFF5F5", borderRadius: 12, borderWidth: 1, borderColor: "#FECACA", padding: 16, gap: 10 },
  dangerTitle:    { fontSize: 12, fontWeight: "700", color: "#DC2626", letterSpacing: 0.5 },
  deleteBtn:      { flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: "#fff", borderRadius: 8, borderWidth: 1, borderColor: "#FECACA", paddingHorizontal: 14, paddingVertical: 10 },
  deleteBtnText:  { fontSize: 14, fontWeight: "500", color: "#DC2626" },
  dangerSub:      { fontSize: 12, color: "#6B7280" },
});
