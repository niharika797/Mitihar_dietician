/**
 * SplashAnimation.tsx
 * Custom animated splash screen for Mityahar.
 * Plays a ~1.8s animation then calls onFinish().
 *
 * Animation sequence:
 *  0ms    — logo fades in + scales up (spring)
 *  400ms  — app name slides up + fades in
 *  700ms  — tagline fades in
 *  1100ms — hold 400ms
 *  1500ms — whole screen fades out
 *  1800ms — onFinish() called
 *
 * Uses react-native-reanimated so all animations run on the UI thread.
 */
import React, { useEffect } from "react";
import { Platform, StyleSheet, Text, View } from "react-native";
import Animated, {
  useSharedValue, useAnimatedStyle,
  withSpring, withTiming, withDelay, withSequence,
  runOnJS,
} from "react-native-reanimated";
import Svg, { Ellipse, Path } from "react-native-svg";

function MityaharLeaf({ size = 72 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 48 48">
      <Ellipse cx={24} cy={30} rx={14} ry={10} fill="#DCFCE7" />
      <Path
        d="M24 8 C 24 8, 12 18, 12 28 C 12 36 18 40 24 40 C 30 40 36 36 36 28 C 36 18 24 8 24 8Z"
        fill="#1E7C45"
        opacity={0.92}
      />
      <Path
        d="M24 8 C 24 8, 24 22, 24 38"
        stroke="#34B164"
        strokeWidth={1.5}
        strokeDasharray="2 3"
      />
      <Path d="M24 20 C 24 20, 18 16, 16 12" stroke="#34B164" strokeWidth={1.5} />
      <Path d="M24 26 C 24 26, 30 22, 32 18" stroke="#34B164" strokeWidth={1.5} />
    </Svg>
  );
}

// Hoisted to a plain boolean: the withTiming callback below is a worklet and
// runs on the UI thread, where it can only close over serializable values —
// referencing the `Platform` module inside it throws "Platform is not defined".
const IS_WEB = Platform.OS === "web";

interface Props { onFinish: () => void; }

export default function SplashAnimation({ onFinish }: Props) {
  const logoScale   = useSharedValue(0.3);
  const logoOpacity = useSharedValue(0);
  const nameTransY  = useSharedValue(20);
  const nameOpacity = useSharedValue(0);
  const tagOpacity  = useSharedValue(0);
  const screenOp    = useSharedValue(1);

  const logoStyle = useAnimatedStyle(() => ({
    transform: [{ scale: logoScale.value }],
    opacity: logoOpacity.value,
  }));

  const nameStyle = useAnimatedStyle(() => ({
    opacity: nameOpacity.value,
    transform: [{ translateY: nameTransY.value }],
  }));

  const tagStyle  = useAnimatedStyle(() => ({ opacity: tagOpacity.value }));
  const rootStyle = useAnimatedStyle(() => ({ opacity: screenOp.value }));

  useEffect(() => {
    // Step 1 (0ms) — logo springs in; opacity times in over 400ms
    logoScale.value = withSpring(1, { damping: 6, stiffness: 80 });
    logoOpacity.value = withTiming(1, { duration: 400 });

    // Step 2 (400ms) — name slides up + fades in
    nameOpacity.value = withDelay(400, withTiming(1, { duration: 300 }));
    nameTransY.value  = withDelay(400, withTiming(0, { duration: 300 }));

    // Step 3 (700ms) — tagline fades in
    tagOpacity.value = withDelay(700, withTiming(1, { duration: 300 }));

    // Step 4 (1400ms) — hold 400ms then screen fades out; fire onFinish when done
    screenOp.value = withDelay(
      1400,
      withSequence(
        withTiming(1, { duration: 1 }), // hold frame
        withTiming(0, { duration: 300 }, (done) => {
          // Native only — see the web branch below for why.
          if (done && !IS_WEB) runOnJS(onFinish)();
        }),
      ),
    );

    // On web, reanimated drives animations off requestAnimationFrame, which the
    // browser suspends whenever the tab is backgrounded or not compositing. The
    // withTiming completion callback above then never fires and the splash never
    // hands off — the app is stuck here forever. setTimeout keeps running in
    // background tabs (throttled, not suspended), so it is the reliable trigger.
    if (Platform.OS === "web") {
      const t = setTimeout(onFinish, 1700); // 1400ms delay + 300ms fade
      return () => clearTimeout(t);
    }
  }, []);

  return (
    <Animated.View style={[s.root, rootStyle]}>
      <View style={s.center}>
        {/* Logo */}
        <Animated.View style={[s.logoWrap, logoStyle]}>
          <MityaharLeaf size={80} />
        </Animated.View>

        {/* App name */}
        <Animated.Text style={[s.appName, nameStyle]}>
          Mitihar
        </Animated.Text>

        {/* Tagline */}
        <Animated.Text style={[s.tagline, tagStyle]}>
          Your personal diet companion
        </Animated.Text>
      </View>

      {/* Bottom badge */}
      <Animated.Text style={[s.badge, tagStyle]}>
        Powered by AI · Built for India
      </Animated.Text>
    </Animated.View>
  );
}

const s = StyleSheet.create({
  root:     { ...StyleSheet.absoluteFillObject, backgroundColor: "#fff", alignItems: "center", justifyContent: "center", zIndex: 999 },
  center:   { alignItems: "center" },
  logoWrap: { width: 100, height: 100, borderRadius: 24, backgroundColor: "#F0FDF4", alignItems: "center", justifyContent: "center", marginBottom: 20, boxShadow: "0px 4px 12px rgba(30,124,69,0.15)" },
  appName:  { fontSize: 36, fontWeight: "700", color: "#1E7C45", letterSpacing: 0.5 },
  tagline:  { fontSize: 14, color: "#6B7280", marginTop: 8, letterSpacing: 0.2 },
  badge:    { position: "absolute", bottom: 40, fontSize: 11, color: "#D1D5DB" },
});
