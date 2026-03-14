import React from "react";
import { Pressable, View, StyleSheet } from "react-native";
import Animated, { useSharedValue, useAnimatedStyle, withTiming } from "react-native-reanimated";

interface ToggleProps {
  value: boolean;
  onToggle: (next: boolean) => void;
  size?: "sm" | "md";
}

export function Toggle({ value, onToggle, size = "md" }: ToggleProps) {
  const trackW = size === "sm" ? 40 : 48;
  const trackH = size === "sm" ? 22 : 26;
  const knobSz = trackH - 6;
  const knobOn = trackW - knobSz - 3;

  const knobX = useSharedValue(value ? knobOn : 3);

  React.useEffect(() => {
    knobX.value = withTiming(value ? knobOn : 3, { duration: 180 });
  }, [value]);

  const knobStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: knobX.value }],
  }));

  return (
    <Pressable
      onPress={() => onToggle(!value)}
      style={[
        s.track,
        { width: trackW, height: trackH, borderRadius: trackH / 2 },
        { backgroundColor: value ? "#1E7C45" : "#D1D5DB" },
      ]}
    >
      <Animated.View
        style={[
          s.knob,
          { width: knobSz, height: knobSz, borderRadius: knobSz / 2, top: 3 },
          knobStyle,
        ]}
      />
    </Pressable>
  );
}

const s = StyleSheet.create({
  track: { justifyContent: "center" },
  knob:  {
    position: "absolute",
    backgroundColor: "#fff",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.2,
    shadowRadius: 2,
    elevation: 2,
  },
});
