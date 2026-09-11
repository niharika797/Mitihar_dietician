import React from "react";
import { Pressable, Text, ActivityIndicator, StyleSheet, PressableProps } from "react-native";
import { colors, radius, spacing } from "../../constants/theme";

type Variant = "primary" | "secondary" | "ghost";

interface ButtonProps extends Omit<PressableProps, "style"> {
  label: string;
  variant?: Variant;
  loading?: boolean;
  disabled?: boolean;
}

// Replaces the hand-rolled Pressable + local StyleSheet CTA that every tab
// screen redefined on its own (same 52px/pill shape as OnboardingShell's
// footer CTA, formalized here for reuse outside onboarding).
export function Button({ label, variant = "primary", loading, disabled, ...pressableProps }: ButtonProps) {
  const isDisabled = disabled || loading;
  return (
    <Pressable
      {...pressableProps}
      disabled={isDisabled}
      style={[
        s.base,
        variant === "primary" && s.primary,
        variant === "secondary" && s.secondary,
        variant === "ghost" && s.ghost,
        isDisabled && variant === "primary" && s.primaryDisabled,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variant === "primary" ? colors.white : colors.brand[600]} size="small" />
      ) : (
        <Text
          style={[
            s.label,
            variant === "primary" && s.labelPrimary,
            variant === "secondary" && s.labelSecondary,
            variant === "ghost" && s.labelGhost,
            isDisabled && variant === "primary" && s.labelPrimaryDisabled,
          ]}
        >
          {label}
        </Text>
      )}
    </Pressable>
  );
}

const s = StyleSheet.create({
  base: {
    height: 52,
    borderRadius: radius.pill,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.xxl,
  },
  primary: { backgroundColor: colors.brand[600] },
  primaryDisabled: { backgroundColor: colors.gray[200] },
  secondary: { backgroundColor: colors.white, borderWidth: 1.5, borderColor: colors.brand[600] },
  ghost: { backgroundColor: "transparent" },
  label: { fontSize: 16, fontFamily: "Inter_600SemiBold" },
  labelPrimary: { color: colors.white },
  labelPrimaryDisabled: { color: colors.gray[400] },
  labelSecondary: { color: colors.brand[600] },
  labelGhost: { color: colors.brand[600] },
});
