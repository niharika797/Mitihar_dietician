import React, { useState } from "react";
import { View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { storage } from "../../lib/storage";
import { useMutation } from "@tanstack/react-query";
import { OnboardingShell, useToast } from "../../components/shared";
import { useOnboardingStore } from "../../store/useOnboardingStore";
import { useAuthStore } from "../../store/useAuthStore";
import { submitOnboarding, acceptDisclaimer, activateSubscription, getMyProfile } from "../../services/profile";
import { getApiError } from "../../lib/getApiError";

export default function DisclaimerScreen() {
  const router = useRouter();
  const { showToast } = useToast();
  const { toPayload, reset } = useOnboardingStore();
  const { setProfile, setTokens } = useAuthStore();
  const [accepted, setAccepted] = useState(false);

  const submitMut = useMutation({
    mutationFn: async () => {
      // toPayload() throws a plain Error if store data is invalid —
      // catch it here so onError shows the real message via getApiError.
      let payload;
      try {
        payload = toPayload();
      } catch (e: any) {
        throw new Error(e?.message ?? "Invalid profile data. Please go back and check your entries.");
      }
      await submitOnboarding(payload);
      await acceptDisclaimer();

      // If the patient registered with a doctor code, activate their subscription now.
      // This is the only correct place — after onboarding + disclaimer, before redirect.
      const pendingCode = await storage.getItemAsync("mityahar_pending_doctor_code");
      if (pendingCode) {
        try {
          const result = await activateSubscription(pendingCode);
          // Update both tokens so the patient's next request carries sub_status=active.
          await setTokens(result.access_token, result.refresh_token);
        } catch (_) {
          // Code expired or already used — don't crash the onboarding flow.
          // Patient lands as inactive and can retry from Account → Activate Subscription.
        } finally {
          await storage.deleteItemAsync("mityahar_pending_doctor_code");
        }
      }

      return getMyProfile();
    },
    onSuccess: (profile) => {
      setProfile(profile);
      reset();
      showToast("Profile complete! Welcome to Mitihar 🎉", "success");
      router.replace("/(onboarding)/complete");
    },
    onError: (err: any) => {
      showToast(getApiError(err), "error");
    },
  });

  return (
    <OnboardingShell
      step={7} totalSteps={7}
      title="Before We Begin"
      onContinue={() => submitMut.mutate()}
      continueDisabled={!accepted || submitMut.isPending}
      continueLabel={submitMut.isPending ? "Saving..." : "Accept & Start My Journey"}
      scrollable={false}
    >
      {/* flex: 1 so this container fills the shell's content area */}
      <View style={s.form}>
        {/* Disclaimer scroll box — flex: 1 expands to fill available space */}
        <ScrollView style={s.box} nestedScrollEnabled showsVerticalScrollIndicator>
          <Text style={s.boxHeading}>DISCLAIMER</Text>
          <Text style={s.boxBody}>
            Mitihar provides nutritional guidance based on your personal inputs and goals. This app is designed to support healthy eating habits and is NOT a substitute for medical advice from a qualified healthcare professional.{"\n\n"}
            The meal plans, calorie targets, and nutritional recommendations provided by Mitihar are generated using general nutritional principles and the information you have provided. Individual results may vary.{"\n\n"}
            If you have any medical conditions, are pregnant, breastfeeding, or are on medication, please consult your doctor or a registered dietician before making significant changes to your diet.{"\n\n"}
            Mitihar is not responsible for any health outcomes resulting from the use of this app. Always prioritize your health and wellbeing, and seek professional medical advice when needed.{"\n\n"}
            By using this application, you acknowledge that you have read and understood this disclaimer and agree to use the app responsibly.{"\n\n"}
            Your personal data is handled in accordance with our Privacy Policy. We do not share your health information with third parties without your explicit consent.
          </Text>
        </ScrollView>

        {/* Accept checkbox */}
        <Pressable onPress={() => setAccepted(v => !v)} style={s.checkRow}>
          <View style={[s.checkbox, accepted && s.checkboxSel]}>
            {accepted && (
              <View style={s.checkmark}>
                <Text style={{ color: "#fff", fontSize: 12, lineHeight: 12 }}>✓</Text>
              </View>
            )}
          </View>
          <Text style={s.checkLabel}>I have read and agree to the terms</Text>
        </Pressable>

        {submitMut.isPending && (
          <View style={s.loadingRow}>
            <ActivityIndicator color="#1E7C45" size="small" />
            <Text style={s.loadingText}>Saving your profile...</Text>
          </View>
        )}
      </View>
    </OnboardingShell>
  );
}

const s = StyleSheet.create({
  form:         { flex: 1, gap: 20 },
  box:          { flex: 1, backgroundColor: "#F9FAFB", borderWidth: 1, borderColor: "#E5E7EB", borderRadius: 12, padding: 16 },
  boxHeading:   { fontSize: 13, fontWeight: "700", color: "#111827", marginBottom: 12, letterSpacing: 0.5 },
  boxBody:      { fontSize: 12, color: "#374151", lineHeight: 20 },
  checkRow:     { flexDirection: "row", alignItems: "flex-start", gap: 12 },
  checkbox:     { width: 22, height: 22, borderRadius: 6, borderWidth: 2, borderColor: "#D1D5DB", backgroundColor: "#fff", alignItems: "center", justifyContent: "center", marginTop: 1 },
  checkboxSel:  { borderColor: "#1E7C45", backgroundColor: "#1E7C45" },
  checkmark:    { alignItems: "center", justifyContent: "center" },
  checkLabel:   { flex: 1, fontSize: 15, fontWeight: "500", color: "#111827", lineHeight: 22 },
  loadingRow:   { flexDirection: "row", alignItems: "center", gap: 8, justifyContent: "center" },
  loadingText:  { fontSize: 13, color: "#6B7280" },
});
