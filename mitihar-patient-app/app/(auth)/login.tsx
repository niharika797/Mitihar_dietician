import React, { useState } from "react";
import {
  View, Text, TextInput, Pressable,
  ScrollView, StyleSheet, ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { Eye, EyeOff } from "lucide-react-native";
import { useMutation } from "@tanstack/react-query";
import { useAuthStore } from "../../store/useAuthStore";
import { useToast } from "../../components/shared";
import { loginPatient } from "../../services/auth";
import { getMyProfile } from "../../services/profile";

// ── Mitihar leaf logo (SVG-via-react-native-svg) ──────────────────────────
import Svg, { Ellipse, Path } from "react-native-svg";
function MitiharLogo() {
  return (
    <View style={s.logoWrap}>
      <Svg width={48} height={48} viewBox="0 0 48 48">
        <Ellipse cx={24} cy={30} rx={14} ry={10} fill="#DCFCE7" />
        <Path d="M24 8 C 24 8, 12 18, 12 28 C 12 36 18 40 24 40 C 30 40 36 36 36 28 C 36 18 24 8 24 8Z" fill="#1E7C45" opacity={0.9} />
        <Path d="M24 8 C 24 8, 24 22, 24 38" stroke="#34B164" strokeWidth={1.5} strokeDasharray="2 3" />
        <Path d="M24 20 C 24 20, 18 16, 16 12" stroke="#34B164" strokeWidth={1.5} />
        <Path d="M24 26 C 24 26, 30 22, 32 18" stroke="#34B164" strokeWidth={1.5} />
      </Svg>
    </View>
  );
}

// ── Google G SVG ──────────────────────────────────────────────────────────
import { G, Path as SvgPath } from "react-native-svg";
function GoogleIcon() {
  return (
    <Svg width={20} height={20} viewBox="0 0 24 24">
      <SvgPath d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
      <SvgPath d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <SvgPath d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
      <SvgPath d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </Svg>
  );
}

export default function LoginScreen() {
  const router = useRouter();
  const { setTokens, setProfile } = useAuthStore();
  const { showToast } = useToast();

  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);

  const loginMut = useMutation({
    mutationFn: () => loginPatient(email.trim(), password),
    onSuccess: async (tokens) => {
      await setTokens(tokens.access_token, tokens.refresh_token);
      try {
        const profile = await getMyProfile();
        setProfile(profile);
        // Onboarding is complete when:
        //   1. disclaimer_accepted_at is set (authoritative), OR
        //   2. height_cm > 0 AND weight_kg > 0 (placeholder values used at registration are 0)
        // This dual-check prevents re-directing existing completed patients to onboarding
        // even if disclaimer_accepted_at was missed due to a previous backend bug.
        const onboardingDone =
          !!profile.disclaimer_accepted_at ||
          (Number(profile.height_cm) > 0 && Number(profile.weight_kg) > 0);

        if (!onboardingDone) {
          router.replace("/(onboarding)/personal-info");
        } else {
          router.replace("/(tabs)");
        }
      } catch {
        router.replace("/(tabs)");
      }
    },
    onError: () => showToast("Invalid email or password", "error"),
  });

  const canSubmit = email.trim().length > 0 && password.length >= 6;

  return (
    <ScrollView
      style={s.root}
      contentContainerStyle={s.scroll}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
    >
      {/* Logo block */}
      <View style={s.logoBlock}>
        <MitiharLogo />
        <Text style={s.appName}>Mitihar</Text>
        <Text style={s.tagline}>Your personal diet companion</Text>
      </View>

      {/* Form */}
      <View style={s.form}>
        {/* Email */}
        <View style={s.field}>
          <Text style={s.label}>Email</Text>
          <TextInput
            style={s.input}
            placeholder="you@example.com"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoCorrect={false}
          />
        </View>

        {/* Password */}
        <View style={s.field}>
          <Text style={s.label}>Password</Text>
          <View style={s.pwRow}>
            <TextInput
              style={[s.input, { flex: 1, marginBottom: 0 }]}
              placeholder="••••••••"
              value={password}
              onChangeText={setPassword}
              secureTextEntry={!showPw}
              autoCapitalize="none"
            />
            <Pressable onPress={() => setShowPw(v => !v)} style={s.eyeBtn} hitSlop={8}>
              {showPw
                ? <EyeOff size={18} color="#6B7280" />
                : <Eye    size={18} color="#6B7280" />}
            </Pressable>
          </View>
          <Pressable style={s.forgotWrap} onPress={() => showToast("Password reset coming soon", "info")}>
            <Text style={s.forgot}>Forgot password?</Text>
          </Pressable>
        </View>

        {/* Sign in */}
        <Pressable
          style={[s.primaryBtn, (!canSubmit || loginMut.isPending) && s.primaryBtnDisabled]}
          onPress={() => loginMut.mutate()}
          disabled={!canSubmit || loginMut.isPending}
        >
          {loginMut.isPending
            ? <ActivityIndicator color="#fff" />
            : <Text style={s.primaryBtnText}>Sign In</Text>}
        </Pressable>

        {/* Divider */}
        <View style={s.divider}>
          <View style={s.line} />
          <Text style={s.dividerText}>or continue with</Text>
          <View style={s.line} />
        </View>

        {/* Google */}
        <Pressable style={s.googleBtn} onPress={() => showToast("Google sign-in coming soon", "info")}>
          <GoogleIcon />
          <Text style={s.googleText}>Continue with Google</Text>
        </Pressable>

        {/* Register link */}
        <View style={s.footer}>
          <Text style={s.footerText}>Don't have an account? </Text>
          <Pressable onPress={() => router.push("/(auth)/register")}>
            <Text style={s.link}>Register</Text>
          </Pressable>
        </View>
      </View>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root:              { flex: 1, backgroundColor: "#fff" },
  scroll:            { padding: 24, paddingTop: 48, flexGrow: 1 },
  logoBlock:         { alignItems: "center", marginBottom: 36 },
  logoWrap:          { width: 80, height: 80, borderRadius: 20, backgroundColor: "#F0FDF4", alignItems: "center", justifyContent: "center", marginBottom: 12 },
  appName:           { fontSize: 24, fontWeight: "700", color: "#1E7C45" },
  tagline:           { fontSize: 14, color: "#6B7280", marginTop: 2 },
  form:              { gap: 16 },
  field:             { gap: 6 },
  label:             { fontSize: 14, fontWeight: "500", color: "#374151" },
  input:             { height: 52, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", paddingHorizontal: 16, fontSize: 14, color: "#111827", backgroundColor: "#fff" },
  pwRow:             { flexDirection: "row", alignItems: "center", gap: 0 },
  eyeBtn:            { position: "absolute", right: 14 },
  forgotWrap:        { alignItems: "flex-end", marginTop: 4 },
  forgot:            { fontSize: 12, color: "#1E7C45", fontWeight: "500" },
  primaryBtn:        { height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center", marginTop: 4 },
  primaryBtnDisabled:{ backgroundColor: "#6B7280" },
  primaryBtnText:    { fontSize: 16, fontWeight: "600", color: "#fff" },
  divider:           { flexDirection: "row", alignItems: "center", gap: 12 },
  line:              { flex: 1, height: 1, backgroundColor: "#E5E7EB" },
  dividerText:       { fontSize: 12, color: "#6B7280" },
  googleBtn:         { height: 52, borderRadius: 26, borderWidth: 1.5, borderColor: "#E5E7EB", backgroundColor: "#fff", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 10 },
  googleText:        { fontSize: 15, fontWeight: "500", color: "#111827" },
  footer:            { flexDirection: "row", justifyContent: "center", marginTop: 8 },
  footerText:        { fontSize: 14, color: "#6B7280" },
  link:              { fontSize: 14, color: "#1E7C45", fontWeight: "500" },
});
