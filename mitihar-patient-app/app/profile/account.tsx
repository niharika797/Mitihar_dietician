import React, { useState, useEffect } from "react";
import { View, Text, Pressable, StyleSheet, Alert, Switch, Modal, TextInput, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft, ChevronRight, Trash2, Shield, LogOut, Fingerprint, Eye, EyeOff, KeyRound } from "lucide-react-native";
import { useMutation } from "@tanstack/react-query";
import { logoutPatient } from "../../services/auth";
import { deleteMyAccount, activateSubscription } from "../../services/profile";
import { useAuthStore } from "../../store/useAuthStore";
import { useBiometricStore } from "../../store/useBiometricStore";
import { useToast } from "../../components/shared";

export default function AccountScreen() {
  const router = useRouter();
  const { showToast } = useToast();
  const logout = useAuthStore(s => s.logout);
  const profile = useAuthStore(s => s.profile);
  const setTokens = useAuthStore(s => s.setTokens);
  const setProfile = useAuthStore(s => s.setProfile);
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

  // ── Activate subscription state ───────────────────────────────────────────
  const [activateModalVisible, setActivateModalVisible] = useState(false);
  const [activateCode, setActivateCode]                 = useState("");
  const [activateError, setActivateError]               = useState("");

  const activateMut = useMutation({
    mutationFn: () => activateSubscription(activateCode.trim().toUpperCase()),
    onSuccess: async (result) => {
      await setTokens(result.access_token, result.refresh_token);
      setProfile(result.patient);
      setActivateModalVisible(false);
      showToast("Subscription activated!", "success");
    },
    onError: (err: any) => {
      setActivateError(err?.response?.data?.detail ?? "Invalid or already-used code. Please try again.");
    },
  });

  // ── Delete account state ──────────────────────────────────────────────────
  // Step 1: Alert confirms intent.
  // Step 2: Modal captures password for verification.
  const [deleteModalVisible, setDeleteModalVisible] = useState(false);
  const [deletePassword, setDeletePassword]         = useState("");
  const [deletePasswordError, setDeletePasswordError] = useState("");
  const [showDeletePw, setShowDeletePw]             = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => deleteMyAccount(deletePassword),
    onSuccess: async () => {
      setDeleteModalVisible(false);
      // Clear all local state — tokens, biometric key, profile
      await logout();
      router.replace("/(auth)/login");
    },
    onError: (err: any) => {
      // Parse the backend error message
      const detail = err?.response?.data?.detail ?? "Something went wrong. Please try again.";
      setDeletePasswordError(detail);
    },
  });

  // Step 1 — show the initial confirmation alert
  const handleDeleteAccount = () => {
    Alert.alert(
      "Delete Account",
      "This will permanently delete your account and all your data including meal logs, progress, and meal plans. This cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Continue",
          style: "destructive",
          onPress: () => {
            // Step 2 — open the password modal
            setDeletePassword("");
            setDeletePasswordError("");
            setShowDeletePw(false);
            deleteMutation.reset();
            setDeleteModalVisible(true);
          },
        },
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

        {/* Activate Subscription — only shown for inactive patients */}
        {profile?.subscription_status === "inactive" && (
          <Pressable
            style={[s.actionRow, s.actionBorder]}
            onPress={() => {
              setActivateCode("");
              setActivateError("");
              activateMut.reset();
              setActivateModalVisible(true);
            }}
          >
            <View style={s.actionLeft}>
              <KeyRound size={16} color="#1E7C45" />
              <View>
                <Text style={[s.actionLabel, { color: "#1E7C45" }]}>Activate Subscription</Text>
                <Text style={s.actionSub}>Enter your doctor's code</Text>
              </View>
            </View>
            <ChevronRight size={16} color="#9CA3AF" />
          </Pressable>
        )}

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

      {/* ── Activate subscription modal ────────────────────────────────────── */}
      <Modal
        visible={activateModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => !activateMut.isPending && setActivateModalVisible(false)}
      >
        <View style={s.overlay}>
          <View style={s.modalCard}>
            <View style={s.modalHeader}>
              <View style={[s.modalIconWrap, { backgroundColor: "#F0FDF4" }]}>
                <KeyRound size={18} color="#1E7C45" />
              </View>
              <View>
                <Text style={s.modalTitle}>Activate Subscription</Text>
                <Text style={s.modalSub}>Enter the code from your doctor</Text>
              </View>
            </View>

            <View style={[s.pwWrap, activateError ? { borderColor: "#DC2626" } : null]}>
              <TextInput
                style={s.pwInput}
                placeholder="e.g. ASHOK1"
                placeholderTextColor="#9CA3AF"
                value={activateCode}
                onChangeText={t => { setActivateCode(t); setActivateError(""); }}
                autoCapitalize="characters"
                autoCorrect={false}
                editable={!activateMut.isPending}
              />
            </View>

            {activateError !== "" && (
              <Text style={s.pwError}>{activateError}</Text>
            )}

            <View style={s.modalActions}>
              <Pressable
                style={s.modalCancelBtn}
                onPress={() => { setActivateModalVisible(false); activateMut.reset(); }}
                disabled={activateMut.isPending}
              >
                <Text style={s.modalCancelText}>Cancel</Text>
              </Pressable>
              <Pressable
                style={[s.modalDeleteBtn, { backgroundColor: "#1E7C45" }, (!activateCode.trim() || activateMut.isPending) && s.modalDeleteBtnDisabled]}
                onPress={() => activateMut.mutate()}
                disabled={!activateCode.trim() || activateMut.isPending}
              >
                {activateMut.isPending
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={s.modalDeleteText}>Activate</Text>
                }
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>

      {/* ── Password confirmation modal ─────────────────────────────────────
           Shown after the user confirms intent in the Alert above.
           Requires the account password before deletion proceeds.
        ────────────────────────────────────────────────────────────────── */}
      <Modal
        visible={deleteModalVisible}
        transparent
        animationType="fade"
        onRequestClose={() => !deleteMutation.isPending && setDeleteModalVisible(false)}
      >
        <View style={s.overlay}>
          <View style={s.modalCard}>
            {/* Header */}
            <View style={s.modalHeader}>
              <View style={s.modalIconWrap}>
                <Trash2 size={18} color="#DC2626" />
              </View>
              <View>
                <Text style={s.modalTitle}>Confirm deletion</Text>
                <Text style={s.modalSub}>Enter your password to continue</Text>
              </View>
            </View>

            {/* Warning bullet list */}
            <View style={s.modalWarnings}>
              {[
                "Your profile and personal data will be anonymised",
                "All meal logs and progress records will be deleted",
                "Your meal plans will be removed",
                "Your original email will be freed for re-registration",
              ].map((w, i) => (
                <Text key={w} style={s.modalWarningItem}>• {w}</Text>
              ))}
            </View>

            {/* Password input */}
            <View style={s.pwWrap}>
              <TextInput
                style={[s.pwInput, deletePasswordError ? s.pwInputError : null]}
                placeholder="Your password"
                placeholderTextColor="#9CA3AF"
                value={deletePassword}
                onChangeText={t => { setDeletePassword(t); setDeletePasswordError(""); }}
                secureTextEntry={!showDeletePw}
                autoCapitalize="none"
                autoCorrect={false}
                editable={!deleteMutation.isPending}
              />
              <Pressable
                onPress={() => setShowDeletePw(v => !v)}
                style={s.pwEye}
                hitSlop={8}
              >
                {showDeletePw
                  ? <EyeOff size={16} color="#6B7280" />
                  : <Eye    size={16} color="#6B7280" />}
              </Pressable>
            </View>

            {/* Inline error */}
            {deletePasswordError !== "" && (
              <Text style={s.pwError}>{deletePasswordError}</Text>
            )}

            {/* Actions */}
            <View style={s.modalActions}>
              <Pressable
                style={s.modalCancelBtn}
                onPress={() => { setDeleteModalVisible(false); deleteMutation.reset(); }}
                disabled={deleteMutation.isPending}
              >
                <Text style={s.modalCancelText}>Cancel</Text>
              </Pressable>
              <Pressable
                style={[s.modalDeleteBtn, (!deletePassword || deleteMutation.isPending) && s.modalDeleteBtnDisabled]}
                onPress={() => deleteMutation.mutate()}
                disabled={!deletePassword || deleteMutation.isPending}
              >
                {deleteMutation.isPending
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={s.modalDeleteText}>Delete Account</Text>
                }
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
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
  // ── Delete account modal ────────────────────────────────────────────────
  overlay:            { flex: 1, backgroundColor: "rgba(0,0,0,0.45)", alignItems: "center", justifyContent: "center" },
  modalCard:          { width: "88%", backgroundColor: "#fff", borderRadius: 16, padding: 20, gap: 16 },
  modalHeader:        { flexDirection: "row", alignItems: "center", gap: 12 },
  modalIconWrap:      { width: 40, height: 40, borderRadius: 20, backgroundColor: "#FEF2F2", alignItems: "center", justifyContent: "center" },
  modalTitle:         { fontSize: 15, fontWeight: "600", color: "#111827" },
  modalSub:           { fontSize: 12, color: "#6B7280", marginTop: 1 },
  modalWarnings:      { gap: 5 },
  modalWarningItem:   { fontSize: 12, color: "#374151", lineHeight: 18 },
  pwWrap:             { flexDirection: "row", alignItems: "center", borderWidth: 1.5, borderColor: "#E5E7EB", borderRadius: 10, paddingHorizontal: 14 },
  pwInput:            { flex: 1, height: 46, fontSize: 14, color: "#111827" },
  pwInputError:       { borderColor: "#DC2626" },
  pwEye:              { padding: 4 },
  pwError:            { fontSize: 12, color: "#DC2626", marginTop: -8 },
  modalActions:       { flexDirection: "row", gap: 10 },
  modalCancelBtn:     { flex: 1, height: 42, borderRadius: 10, borderWidth: 1.5, borderColor: "#E5E7EB", alignItems: "center", justifyContent: "center" },
  modalCancelText:    { fontSize: 14, fontWeight: "500", color: "#374151" },
  modalDeleteBtn:     { flex: 1, height: 42, borderRadius: 10, backgroundColor: "#DC2626", alignItems: "center", justifyContent: "center" },
  modalDeleteBtnDisabled: { backgroundColor: "#9CA3AF" },
  modalDeleteText:    { fontSize: 14, fontWeight: "600", color: "#fff" },
});
