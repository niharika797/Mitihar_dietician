import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { colors, spacing, typography } from "../../constants/theme";

interface ScreenHeaderProps {
  title: string;
}

// Meals/Progress/Profile each hand-rolled this identical title bar. Kept as
// forwardRef so it stays drop-in compatible with anything that needs to
// measure it (e.g. a walkthrough/tour overlay targeting the header).
export const ScreenHeader = React.forwardRef<View, ScreenHeaderProps>(function ScreenHeader({ title }, ref) {
  return (
    <View ref={ref} style={s.header}>
      <Text style={s.title}>{title}</Text>
    </View>
  );
});

const s = StyleSheet.create({
  header: {
    backgroundColor: colors.white,
    borderBottomWidth: 1,
    borderBottomColor: colors.gray[200],
    padding: spacing.lg,
  },
  title: { ...typography.title },
});
