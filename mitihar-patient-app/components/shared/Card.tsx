import React from "react";
import { View, ViewProps, StyleSheet } from "react-native";
import { colors, radius, spacing } from "../../constants/theme";

// The bordered white surface every tab hand-rolls inline (`backgroundColor:
// "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB"`, etc.).
// `padding={false}` for cases that need edge-to-edge content (e.g. Home's
// meal-row list) — same escape hatch those screens already used inline.
interface CardProps extends ViewProps {
  padded?: boolean;
}

export function Card({ padded = true, style, ...viewProps }: CardProps) {
  return <View {...viewProps} style={[s.base, padded && s.padded, style]} />;
}

const s = StyleSheet.create({
  base: {
    backgroundColor: colors.white,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.gray[200],
  },
  padded: { padding: spacing.lg },
});
