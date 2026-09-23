import React from "react";
import { Pressable, PressableProps, ViewStyle, StyleProp } from "react-native";
import Animated, { useSharedValue, useAnimatedStyle, withTiming } from "react-native-reanimated";

const AnimatedView = Animated.createAnimatedComponent(Pressable);

interface AnimatedPressableProps extends PressableProps {
  style?: StyleProp<ViewStyle>;
  children?: React.ReactNode;
}

// Physical press feedback (expo-animation skill's recipe): scale 0.97 in
// ~120ms on press-in, back to 1 on press-out. Feedback fires on press-in so
// it reads as an instant, physical response instead of waiting for the tap
// to complete.
export function AnimatedPressable({ style, onPressIn, onPressOut, ...pressableProps }: AnimatedPressableProps) {
  const scale = useSharedValue(1);
  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.get() }],
  }));

  return (
    <AnimatedView
      {...pressableProps}
      style={[style, animatedStyle]}
      onPressIn={(e) => {
        scale.set(withTiming(0.97, { duration: 120 }));
        onPressIn?.(e);
      }}
      onPressOut={(e) => {
        scale.set(withTiming(1, { duration: 120 }));
        onPressOut?.(e);
      }}
    />
  );
}
