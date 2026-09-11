import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { colors, radius, spacing, typography } from "../../constants/theme";

interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

// The isError -> message + retry pattern that already existed, proven, in
// app/doctor/find-doctor.tsx — Home/Meals/Progress had no equivalent for
// their main data fetch (a failed request just showed nothing). Reused here
// instead of re-invented per screen.
export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <View style={s.center}>
      <Text style={s.emoji}>⚠️</Text>
      <Text style={s.message}>{message}</Text>
      <Pressable onPress={onRetry} style={s.retryBtn}>
        <Text style={s.retryText}>Retry</Text>
      </Pressable>
    </View>
  );
}

const s = StyleSheet.create({
  center: { alignItems: "center", justifyContent: "center", gap: spacing.md, padding: spacing.xxxl },
  emoji: { fontSize: 40 },
  message: { ...typography.bodyMedium, color: colors.gray[700], textAlign: "center" },
  retryBtn: { paddingHorizontal: spacing.xxl, paddingVertical: spacing.sm + 2, backgroundColor: colors.brand[600], borderRadius: radius.pill },
  retryText: { color: colors.white, fontFamily: "Inter_600SemiBold", fontSize: 14 },
});
