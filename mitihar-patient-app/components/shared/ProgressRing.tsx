import React, { useEffect } from "react";
import { View, Text, StyleSheet } from "react-native";
import Svg, { Circle } from "react-native-svg";
import Animated, { useSharedValue, useAnimatedProps, withTiming, Easing } from "react-native-reanimated";

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

// Ease-out bezier for UI entrances/value changes (expo-animation skill's table).
const EASE_OUT = Easing.bezier(0.23, 1, 0.32, 1);

interface ProgressRingProps {
  size?: number;
  strokeWidth?: number;
  percentage: number;
  color?: string;
  trackColor?: string;
  label?: string;
  centerText?: string;
}

export function ProgressRing({
  size = 80,
  strokeWidth = 8,
  percentage,
  color = "#1E7C45",
  trackColor = "#E5E7EB",
  label,
  centerText,
}: ProgressRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clampedPct = Math.min(100, Math.max(0, percentage));
  const center = size / 2;

  // Animates on mount and every time percentage changes, instead of snapping.
  const progress = useSharedValue(0);
  useEffect(() => {
    progress.set(withTiming(clampedPct, { duration: 600, easing: EASE_OUT }));
  }, [clampedPct]);

  const animatedProps = useAnimatedProps(() => ({
    strokeDashoffset: circumference - (progress.get() / 100) * circumference,
  }));

  return (
    <View style={s.wrapper}>
      <View style={{ width: size, height: size }}>
        <Svg width={size} height={size} style={{ transform: [{ rotate: "-90deg" }] }}>
          {/* Track */}
          <Circle
            cx={center} cy={center} r={radius}
            stroke={trackColor} strokeWidth={strokeWidth} fill="none"
          />
          {/* Progress */}
          <AnimatedCircle
            cx={center} cy={center} r={radius}
            stroke={color} strokeWidth={strokeWidth} fill="none"
            strokeLinecap="round"
            strokeDasharray={`${circumference} ${circumference}`}
            animatedProps={animatedProps}
          />
        </Svg>
        {/* Center text — absolutely positioned over SVG */}
        <View style={[StyleSheet.absoluteFillObject, s.center]}>
          <Text style={[s.centerText, { fontSize: size > 100 ? 22 : 16 }]}>
            {centerText ?? `${Math.round(clampedPct)}%`}
          </Text>
        </View>
      </View>
      {label ? <Text style={s.label}>{label}</Text> : null}
    </View>
  );
}

const s = StyleSheet.create({
  wrapper:    { alignItems: "center", gap: 4 },
  center:     { alignItems: "center", justifyContent: "center" },
  centerText: { fontWeight: "700", color: "#111827" },
  label:      { fontSize: 12, color: "#6B7280" },
});
