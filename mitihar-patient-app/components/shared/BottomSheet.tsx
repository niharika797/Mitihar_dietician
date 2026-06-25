import React, { useEffect, useState } from "react";
import { View, Pressable, StyleSheet, ScrollView, useWindowDimensions } from "react-native";
import Animated, {
  useSharedValue, useAnimatedStyle,
  withTiming, Easing, runOnJS,
} from "react-native-reanimated";

interface BottomSheetProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  maxHeight?: number;
}

export function BottomSheet({ open, onClose, children, maxHeight }: BottomSheetProps) {
  const { height: screenHeight } = useWindowDimensions();
  const effectiveMaxHeight = maxHeight ?? screenHeight * 0.9;

  const translateY = useSharedValue(screenHeight);
  const backdropOpacity = useSharedValue(0);
  const [mounted, setMounted] = useState(open);

  useEffect(() => {
    if (open) {
      setMounted(true);
      backdropOpacity.value = withTiming(0.5, { duration: 250 });
      translateY.value = withTiming(0, { duration: 220, easing: Easing.out(Easing.cubic) });
    } else {
      backdropOpacity.value = withTiming(0, { duration: 250 });
      translateY.value = withTiming(screenHeight, { duration: 280 }, (finished) => {
        if (finished) runOnJS(setMounted)(false);
      });
    }
  }, [open, screenHeight]);

  const sheetStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: translateY.value }],
  }));

  const backdropStyle = useAnimatedStyle(() => ({
    opacity: backdropOpacity.value,
  }));

  if (!mounted) return null;

  return (
    <View style={StyleSheet.absoluteFillObject} pointerEvents={open ? "auto" : "none"}>
      {/* Backdrop */}
      <Animated.View style={[s.backdrop, backdropStyle]}>
        <Pressable style={StyleSheet.absoluteFillObject} onPress={onClose} />
      </Animated.View>

      {/* Sheet */}
      <Animated.View style={[s.sheet, { maxHeight: effectiveMaxHeight }, sheetStyle]}>
        {/* Drag handle */}
        <View style={s.handle} />
        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={s.content}
          keyboardShouldPersistTaps="handled"
        >
          {children}
        </ScrollView>
      </Animated.View>
    </View>
  );
}

const s = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "#000",
  },
  sheet: {
    position: "absolute",
    bottom: 0, left: 0, right: 0,
    backgroundColor: "#fff",
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    boxShadow: "0px -4px 16px rgba(0,0,0,0.12)",
  },
  handle: {
    width: 32, height: 4,
    backgroundColor: "#D1D5DB",
    borderRadius: 99,
    alignSelf: "center",
    marginTop: 10,
    marginBottom: 4,
  },
  content: { padding: 20, paddingBottom: 32 },
});
