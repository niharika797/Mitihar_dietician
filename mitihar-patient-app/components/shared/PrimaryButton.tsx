import React from "react";
import { Pressable, Text, ActivityIndicator, StyleSheet, ViewStyle } from "react-native";

interface PrimaryButtonProps {
  onPress: () => void;
  label: string;
  loading?: boolean;
  disabled?: boolean;
  variant?: "solid" | "outline";
  style?: ViewStyle;
}

export function PrimaryButton({
  onPress, label, loading = false, disabled = false, variant = "solid", style,
}: PrimaryButtonProps) {
  const isDisabled = disabled || loading;
  const solid = variant === "solid";

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.base,
        solid ? styles.solid : styles.outline,
        isDisabled && styles.disabled,
        pressed && !isDisabled && styles.pressed,
        style,
      ]}
    >
      {loading
        ? <ActivityIndicator color={solid ? "#fff" : "#1E7C45"} />
        : <Text style={[styles.label, !solid && styles.labelOutline, isDisabled && styles.labelDisabled]}>
            {label}
          </Text>
      }
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    height: 52,
    borderRadius: 26,
    alignItems: "center",
    justifyContent: "center",
  },
  solid:        { backgroundColor: "#1E7C45" },
  outline:      { backgroundColor: "#fff", borderWidth: 1.5, borderColor: "#1E7C45" },
  disabled:     { backgroundColor: "#E5E7EB" },
  pressed:      { opacity: 0.85 },
  label:        { fontSize: 16, fontFamily: "Inter_600SemiBold", color: "#fff" },
  labelOutline: { color: "#1E7C45" },
  labelDisabled:{ color: "#9CA3AF" },
});
