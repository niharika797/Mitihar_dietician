import type { TextStyle } from "react-native";

// Design tokens for the patient app's core tabs (Home/Meals/Progress/Profile).
// Ports the palette + type scale that already existed, unused, in
// tailwind.config.js — every value here was already live somewhere in the
// app as a hand-typed hex; this just gives them one name so screens stop
// re-typing "#1E7C45" and "#6B7280" per file.

export const colors = {
  brand: {
    50: "#F0FDF4",
    100: "#DCFCE7",
    200: "#BBF7D0",
    300: "#86EFAC",
    400: "#34B164",
    500: "#23924F",
    600: "#1E7C45", // primary brand green
    700: "#15803D",
  },
  // Warm accent — already present throughout the app (streak pill, snack
  // icon, renewal CTA) but scattered as unlabeled hex. Named here so it can
  // be used deliberately for highlights/streaks/badges instead of by accident.
  warm: {
    50: "#FFFBEB",
    100: "#FEF3C7",
    200: "#FDE68A",
    300: "#FCD34D",
    400: "#F59E0B",
    600: "#D97706",
    700: "#92400E",
  },
  gray: {
    50: "#F9FAFB",
    100: "#F3F4F6",
    200: "#E5E7EB",
    400: "#9CA3AF",
    500: "#6B7280",
    700: "#374151",
    900: "#111827",
  },
  error: "#DC2626",
  errorBg: "#FEF2F2",
  errorBorder: "#FECACA",
  info: "#2563EB",
  white: "#FFFFFF",
  macro: {
    protein: "#166534",
    proteinBg: "#DCFCE7",
    carbs: "#92400E",
    carbsBg: "#FEF3C7",
    fat: "#6B21A8",
    fatBg: "#F3E8FF",
    fiber: "#1E40AF",
    fiberBg: "#DBEAFE",
  },
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
} as const;

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  pill: 999,
} as const;

// Icon sizes were 14-32px with no scale across the app. Three stops covers
// every existing usage (inline chevrons/dots -> sm, standard row/action icons
// -> md, quick-log/hero icons -> lg).
export const iconSize = {
  sm: 16,
  md: 20,
  lg: 24,
} as const;

const fontFamily = {
  regular: "Inter_400Regular",
  medium: "Inter_500Medium",
  semibold: "Inter_600SemiBold",
  bold: "Inter_700Bold",
  extrabold: "Inter_800ExtraBold",
} as const;

// Named presets pairing size + the correct loaded Inter weight, so text
// actually renders in Inter instead of the OS default font with a
// `fontWeight` string faking the weight.
const TABULAR_NUMS = ["tabular-nums"] as NonNullable<TextStyle["fontVariant"]>;

// Not `as const` — RN's TextStyle.fontVariant wants a mutable FontVariant[],
// and a deep-frozen object here would hand it a readonly tuple instead.
export const typography = {
  // Big hero numbers (calorie count, weight, BMI) — heavier weight + tabular
  // figures so digits don't shift width as they change.
  displayLarge: { fontSize: 34, fontFamily: fontFamily.extrabold, color: colors.gray[900], fontVariant: TABULAR_NUMS },
  display: { fontSize: 28, fontFamily: fontFamily.bold, color: colors.gray[900] },
  title: { fontSize: 20, fontFamily: fontFamily.semibold, color: colors.gray[900] },
  heading: { fontSize: 16, fontFamily: fontFamily.semibold, color: colors.gray[900] },
  body: { fontSize: 14, fontFamily: fontFamily.regular, color: colors.gray[700] },
  bodyMedium: { fontSize: 14, fontFamily: fontFamily.medium, color: colors.gray[900] },
  // Stat tile values (BMI, Weight, TDEE, weight-journey numbers) — tabular
  // figures at body-ish size so grids of numbers line up.
  statValue: { fontSize: 18, fontFamily: fontFamily.extrabold, color: colors.gray[900], fontVariant: TABULAR_NUMS },
  caption: { fontSize: 12, fontFamily: fontFamily.regular, color: colors.gray[500] },
  captionMedium: { fontSize: 12, fontFamily: fontFamily.medium, color: colors.gray[700] },
  label: { fontSize: 11, fontFamily: fontFamily.semibold, color: colors.gray[700], letterSpacing: 1 },
};
