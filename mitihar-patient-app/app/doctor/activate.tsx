import React, { useState, useRef } from "react";
import {
  View, Text, TextInput, Pressable, StyleSheet, ActivityIndicator, ScrollView,
} from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { activateSubscription, getMyProfile } from "../../services/profile";
import { useAuthStore } from "../../store/useAuthStore";
import { useToast } from "../../components/shared";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { getApiError } from "../../lib/getApiError";

export default function ActivateScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const { setProfile, updateAccessToken } = useAuthStore();
  const [code, setCode] = useState(["","","","","",""]);
  const refs = useRef<(TextInput | null)[]>([]);

  const handleDigit = (i: number, val: string) => {
    const v = val.replace(/[^A-Za-z0-9]/g, "").toUpperCase().slice(-1);
    const next = [...code];
    next[i] = v;
    setCode(next);
    if (v && i < 5) refs.current[i + 1]?.focus();
  };

  const handleBackspace = (i: number) => {
    if (!code[i] && i > 0) {
      const next = [...code];
      next[i - 1] = "";
      setCode(next);
      refs.current[i - 1]?.focus();
    }
  };

  const codeStr = code.join("");
  const canActivate = codeStr.length === 6;

  const activateMut = useMutation({
    mutationFn: async () => {
      const resp = await activateSubscription(codeStr);
      if (resp.access_token) {
        await updateAccessToken(resp.access_token);
      }
      return getMyProfile();
    },
    onSuccess: (profile) => {
      setProfile(profile);
      qc.invalidateQueries({ queryKey: QUERY_KEYS.ME });
      showToast("Subscription activated! 🎉", "success");
      router.replace("/doctor/connection-status");
    },
    onError: (err: any) => {
      showToast(getApiError(err, "Invalid code. Please check and try again."), "error");
    },
  });

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Activate Subscription</Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView contentContainerStyle={s.scroll}>
        <View style={s.iconWrap}>
          <Text style={s.iconEmoji}>🔑</Text>
        </View>

        <Text style={s.heading}>Enter Your Activation Code</Text>
        <Text style={s.sub}>
          Your doctor has shared a 6-character code with you. Enter it below to connect and activate your plan.
        </Text>

        {/* 6-box OTP input */}
        <View style={s.codeRow}>
          {code.map((char, i) => (
            <TextInput
              key={i}
              ref={el => { refs.current[i] = el; }}
              value={char}
              maxLength={1}
              onChangeText={val => handleDigit(i, val)}
              onKeyPress={({ nativeEvent }) => {
                if (nativeEvent.key === "Backspace") handleBackspace(i);
              }}
              style={[s.codeBox, char ? s.codeBoxFilled : undefined]}
              keyboardType="default"
              autoCapitalize="characters"
              textAlign="center"
            />
          ))}
        </View>

        <Pressable
          style={[s.primaryBtn, (!canActivate || activateMut.isPending) && s.primaryBtnDisabled]}
          onPress={() => activateMut.mutate()}
          disabled={!canActivate || activateMut.isPending}
        >
          {activateMut.isPending
            ? <ActivityIndicator color="#fff" />
            : <Text style={s.primaryBtnText}>Activate →</Text>}
        </Pressable>

        <Pressable onPress={() => router.push("/doctor/find-doctor")}>
          <Text style={s.linkText}>Don't have a code? Find a doctor</Text>
        </Pressable>

        <View style={s.infoCard}>
          <Text style={s.infoTitle}>ℹ️ What happens next?</Text>
          <Text style={s.infoBody}>
            Once activated, your doctor will receive a notification and create a personalised meal plan for you within 24–48 hours.
          </Text>
        </View>
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root:              { flex: 1, backgroundColor: "#F9FAFB" },
  header:            { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:           { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:             { fontSize: 18, fontWeight: "600", color: "#111827" },
  scroll:            { alignItems: "center", padding: 32, gap: 16 },
  iconWrap:          { width: 80, height: 80, borderRadius: 40, backgroundColor: "#F0FDF4", borderWidth: 2, borderColor: "#DCFCE7", alignItems: "center", justifyContent: "center" },
  iconEmoji:         { fontSize: 36 },
  heading:           { fontSize: 22, fontWeight: "700", color: "#111827", textAlign: "center" },
  sub:               { fontSize: 14, color: "#6B7280", textAlign: "center", lineHeight: 22 },
  codeRow:           { flexDirection: "row", gap: 10 },
  codeBox:           { width: 46, height: 56, fontSize: 22, fontWeight: "700", color: "#111827", borderRadius: 12, borderWidth: 2, borderColor: "#E5E7EB", backgroundColor: "#fff" },
  codeBoxFilled:     { borderColor: "#1E7C45", backgroundColor: "#F0FDF4" },
  primaryBtn:        { width: "100%", height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  primaryBtnDisabled:{ backgroundColor: "#E5E7EB" },
  primaryBtnText:    { fontSize: 16, fontWeight: "600", color: "#fff" },
  linkText:          { fontSize: 14, fontWeight: "500", color: "#1E7C45" },
  infoCard:          { width: "100%", backgroundColor: "#F0FDF4", borderRadius: 12, borderWidth: 1, borderColor: "#DCFCE7", padding: 16, gap: 6 },
  infoTitle:         { fontSize: 13, fontWeight: "600", color: "#166534" },
  infoBody:          { fontSize: 13, color: "#374151", lineHeight: 20 },
});
