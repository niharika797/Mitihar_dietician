import React from "react";
import { Text, ActivityIndicator, StyleSheet, PressableProps, GestureResponderEvent } from "react-native";
import * as Haptics from "expo-haptics";
import { AnimatedPressable } from "./AnimatedPressable";
import { colors, radius, spacing } from "../../constants/theme";

type Variant = "primary" | "secondary" | "ghost";

interface ButtonProps extends Omit<PressableProps, "style"> {
  label: string;
  variant?: Variant;
  loading?: boolean;
  disabled?: boolean;
  /** Fires a light haptic on tap — for actions that commit something (log, save, retry), not plain navigation. */
  haptic?: boolean;
}

// Replaces the hand-rolled Pressable + local StyleSheet CTA that every tab
// screen redefined on its own (same 52px/pill shape as OnboardingShell's
// footer CTA, formalized here for reuse outside onboarding). Press feedback
// via AnimatedPressable (scale 0.97) — every tap now responds physically.
export function Button({ label, variant = "primary", loading, disabled, haptic, onPress, ...pressableProps }: ButtonProps) {
  const isDisabled = disabled || loading;

  const handlePress = (e: GestureResponderEvent) => {
    if (haptic) Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    onPress?.(e);
  };

  return (
    <AnimatedPressable
      {...pressableProps}
      onPress={handlePress}
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
    </AnimatedPressable>
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
