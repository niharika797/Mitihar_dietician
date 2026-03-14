import React from "react";
import { View, Text, ScrollView, Pressable, StyleSheet } from "react-native";
import { ChevronLeft } from "lucide-react-native";
import { useRouter } from "expo-router";

interface OnboardingShellProps {
  step: number;
  totalSteps: number;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  onContinue: () => void;
  onSkip?: () => void;
  continueDisabled?: boolean;
  continueLabel?: string;
  onBack?: () => void;
}

export function OnboardingShell({
  step, totalSteps, title, subtitle, children,
  onContinue, onSkip, continueDisabled, continueLabel = "Continue →", onBack,
}: OnboardingShellProps) {
  const router = useRouter();
  const progress = (step / totalSteps) * 100;

  const handleBack = () => {
    if (onBack) onBack();
    else router.back();
  };

  return (
    <View style={s.root}>
      {/* ── Header ── */}
      <View style={s.header}>
        <View style={s.headerRow}>
          <Pressable onPress={handleBack} style={s.backBtn} hitSlop={8}>
            <ChevronLeft size={20} color="#374151" />
          </Pressable>
          <Text style={s.stepText}>Step {step} of {totalSteps}</Text>
          {onSkip ? (
            <Pressable onPress={onSkip} hitSlop={8}>
              <Text style={s.skipText}>Skip</Text>
            </Pressable>
          ) : (
            <View style={{ width: 36 }} />
          )}
        </View>
        {/* Progress bar */}
        <View style={s.track}>
          <View style={[s.fill, { width: `${progress}%` as any }]} />
        </View>
        <Text style={s.title}>{title}</Text>
        {subtitle ? <Text style={s.subtitle}>{subtitle}</Text> : null}
      </View>

      {/* ── Scrollable body ── */}
      <ScrollView
        style={s.body}
        contentContainerStyle={s.bodyContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {children}
      </ScrollView>

      {/* ── Footer CTA ── */}
      <View style={s.footer}>
        <Pressable
          onPress={onContinue}
          disabled={continueDisabled}
          style={[s.cta, continueDisabled && s.ctaDisabled]}
        >
          <Text style={[s.ctaText, continueDisabled && s.ctaTextDisabled]}>
            {continueLabel}
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  root:            { flex: 1, backgroundColor: "#fff" },
  header:          { paddingHorizontal: 20, paddingTop: 12, paddingBottom: 4 },
  headerRow:       { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 12 },
  backBtn:         { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  stepText:        { fontSize: 12, color: "#6B7280" },
  skipText:        { fontSize: 14, fontWeight: "500", color: "#1E7C45" },
  track:           { height: 4, backgroundColor: "#E5E7EB", borderRadius: 99, overflow: "hidden", marginBottom: 16 },
  fill:            { height: "100%", backgroundColor: "#34B164", borderRadius: 99 },
  title:           { fontSize: 20, fontWeight: "600", color: "#111827" },
  subtitle:        { fontSize: 14, color: "#6B7280", marginTop: 2 },
  body:            { flex: 1 },
  bodyContent:     { paddingHorizontal: 20, paddingVertical: 16, paddingBottom: 32 },
  footer:          { padding: 16, paddingBottom: 24, borderTopWidth: 1, borderTopColor: "#F3F4F6" },
  cta:             { height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  ctaDisabled:     { backgroundColor: "#E5E7EB" },
  ctaText:         { fontSize: 16, fontWeight: "600", color: "#fff" },
  ctaTextDisabled: { color: "#9CA3AF" },
});
