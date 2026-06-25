import React, { useState } from "react";
import {
  View, Text, TextInput, Pressable,
  ScrollView, StyleSheet, ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft, Eye, EyeOff, Plus } from "lucide-react-native";
import { useMutation } from "@tanstack/react-query";
import { storage } from "../../lib/storage";
import { useAuthStore } from "../../store/useAuthStore";
import { useToast } from "../../components/shared";
import { registerPatient } from "../../services/auth";
import { loginPatient } from "../../services/auth";
import { getApiError } from "../../lib/getApiError";

function getStrength(pw: string): number {
  let s = 0;
  if (pw.length >= 8)          s++;
  if (/[A-Z]/.test(pw))        s++;
  if (/[0-9]/.test(pw))        s++;
  if (/[^A-Za-z0-9]/.test(pw)) s++;
  return s;
}

const STRENGTH_COLORS = ["#E5E7EB", "#DC2626", "#F59E0B", "#34B164", "#1E7C45"];
const STRENGTH_LABELS = ["", "Weak", "Fair", "Good", "Strong"];

export default function RegisterScreen() {
  const router = useRouter();
  const { setTokens } = useAuthStore();
  const { showToast } = useToast();

  const [name, setName]               = useState("");
  const [email, setEmail]             = useState("");
  const [password, setPassword]       = useState("");
  const [showPw, setShowPw]           = useState(false);
  const [doctorCode, setDoctorCode]   = useState("");
  const [showDrCode, setShowDrCode]   = useState(false);

  const strength = getStrength(password);
  const canSubmit = name.trim().length > 0 && email.trim().length > 0 && password.length >= 8;

  const registerMut = useMutation({
    mutationFn: async () => {
      await registerPatient({
        name: name.trim(),
        email: email.trim(),
        password,
        ...(doctorCode.trim() ? { doctor_code: doctorCode.trim() } : {}),
      });
      // Persist code so disclaimer.tsx can activate the subscription after onboarding.
      if (doctorCode.trim()) {
        await storage.setItemAsync("mityahar_pending_doctor_code", doctorCode.trim());
      }
      // Auto-login after register
      return loginPatient(email.trim(), password);
    },
    onSuccess: async (tokens) => {
      // setTokens persists tokens and flips isAuthenticated=true while profile stays null.
      // AuthGate reacts to that state change and routes to /(onboarding)/personal-info
      // because profile===null means onboarding is incomplete.
      // Do NOT call router.replace here — AuthGate owns all post-auth navigation.
      await setTokens(tokens.access_token, tokens.refresh_token);
      showToast("Account created! Let's set up your profile 🎉", "success");
    },
    onError: (err: any) => {
      showToast(getApiError(err, "Registration failed. Try again."), "error");
    },
  });

  return (
    <ScrollView
      style={s.root}
      contentContainerStyle={s.scroll}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
    >
      {/* Back */}
      <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
        <ChevronLeft size={20} color="#374151" />
      </Pressable>

      <Text style={s.heading}>Create Account</Text>
      <Text style={s.sub}>Start your diet journey today</Text>

      <View style={s.form}>
        {/* Name */}
        <View style={s.field}>
          <Text style={s.label}>Full Name</Text>
          <TextInput
            style={s.input} placeholder="Radha Sharma"
            value={name} onChangeText={setName} autoCapitalize="words"
          />
        </View>

        {/* Email */}
        <View style={s.field}>
          <Text style={s.label}>Email Address</Text>
          <TextInput
            style={s.input} placeholder="you@example.com"
            value={email} onChangeText={setEmail}
            keyboardType="email-address" autoCapitalize="none"
          />
        </View>

        {/* Password */}
        <View style={s.field}>
          <Text style={s.label}>Password</Text>
          <View style={s.pwRow}>
            <TextInput
              style={[s.input, { flex: 1, marginBottom: 0 }]}
              placeholder="Min. 8 characters"
              value={password} onChangeText={setPassword}
              secureTextEntry={!showPw} autoCapitalize="none"
            />
            <Pressable onPress={() => setShowPw(v => !v)} style={s.eyeBtn} hitSlop={8}>
              {showPw ? <EyeOff size={18} color="#6B7280" /> : <Eye size={18} color="#6B7280" />}
            </Pressable>
          </View>
          {password.length > 0 && (
            <View style={{ marginTop: 8 }}>
              <View style={s.strengthBar}>
                {[1, 2, 3, 4].map(segment => (
                  <View
                    key={segment}
                    style={[s.strengthSegment, { backgroundColor: segment <= strength ? STRENGTH_COLORS[strength] : "#E5E7EB" }]}
                  />
                ))}
              </View>
              <Text style={[s.strengthLabel, { color: STRENGTH_COLORS[strength] }]}>
                {STRENGTH_LABELS[strength]}
              </Text>
            </View>
          )}
          <Text style={s.hint}>Must be 8+ characters</Text>
        </View>

        {/* Doctor code (optional) */}
        {!showDrCode ? (
          <Pressable onPress={() => setShowDrCode(true)} style={s.drCodeLink}>
            <Plus size={16} color="#1E7C45" />
            <Text style={s.drCodeLinkText}>Have a doctor code?</Text>
          </Pressable>
        ) : (
          <View style={s.field}>
            <Text style={s.label}>Doctor Code <Text style={s.optional}>(optional)</Text></Text>
            <TextInput
              style={s.input} placeholder="e.g. ASHOK-2026"
              value={doctorCode} onChangeText={setDoctorCode}
              autoCapitalize="characters"
            />
            <Text style={s.hint}>Have a code from your doctor? Enter it here.</Text>
          </View>
        )}

        {/* Create account */}
        <Pressable
          style={[s.primaryBtn, (!canSubmit || registerMut.isPending) && s.primaryBtnDisabled]}
          onPress={() => registerMut.mutate()}
          disabled={!canSubmit || registerMut.isPending}
        >
          {registerMut.isPending
            ? <ActivityIndicator color="#fff" />
            : <Text style={s.primaryBtnText}>Create Account</Text>}
        </Pressable>

        {/* Divider */}
        <View style={s.divider}>
          <View style={s.line} /><Text style={s.dividerText}>or</Text><View style={s.line} />
        </View>

        {/* Google */}
        <Pressable style={s.googleBtn} onPress={() => showToast("Google sign-in coming soon", "info")}>
          <Text style={s.googleText}>Continue with Google</Text>
        </Pressable>

        <View style={s.footerRow}>
          <Text style={s.footerText}>Already have an account? </Text>
          <Pressable onPress={() => router.push("/(auth)/login")}>
            <Text style={s.link}>Sign In</Text>
          </Pressable>
        </View>
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root:               { flex: 1, backgroundColor: "#fff" },
  scroll:             { padding: 24, paddingTop: 48, flexGrow: 1 },
  backBtn:            { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center", marginBottom: 20 },
  heading:            { fontSize: 24, fontWeight: "700", color: "#111827", marginBottom: 4 },
  sub:                { fontSize: 14, color: "#6B7280", marginBottom: 24 },
  form:               { gap: 16 },
  field:              { gap: 6 },
  label:              { fontSize: 14, fontWeight: "500", color: "#374151" },
  optional:           { fontWeight: "400", color: "#9CA3AF" },
  input:              { height: 52, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", paddingHorizontal: 16, fontSize: 14, color: "#111827", backgroundColor: "#fff" },
  pwRow:              { flexDirection: "row", alignItems: "center" },
  eyeBtn:             { position: "absolute", right: 14 },
  strengthBar:        { flexDirection: "row", gap: 4 },
  strengthSegment:    { flex: 1, height: 3, borderRadius: 99 },
  strengthLabel:      { fontSize: 11, fontWeight: "500", marginTop: 2 },
  hint:               { fontSize: 12, color: "#9CA3AF", marginTop: 2 },
  drCodeLink:         { flexDirection: "row", alignItems: "center", gap: 4 },
  drCodeLinkText:     { fontSize: 14, fontWeight: "500", color: "#1E7C45" },
  primaryBtn:         { height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  primaryBtnDisabled: { backgroundColor: "#6B7280" },
  primaryBtnText:     { fontSize: 16, fontWeight: "600", color: "#fff" },
  divider:            { flexDirection: "row", alignItems: "center", gap: 12 },
  line:               { flex: 1, height: 1, backgroundColor: "#E5E7EB" },
  dividerText:        { fontSize: 12, color: "#6B7280" },
  googleBtn:          { height: 52, borderRadius: 26, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  googleText:         { fontSize: 15, fontWeight: "500", color: "#111827" },
  footerRow:          { flexDirection: "row", justifyContent: "center", marginTop: 8 },
  footerText:         { fontSize: 14, color: "#6B7280" },
  link:               { fontSize: 14, color: "#1E7C45", fontWeight: "500" },
});
