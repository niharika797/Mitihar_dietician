/**
 * SplashAnimation.tsx
 * Custom animated splash screen for Mityahar.
 * Plays a ~1.8s animation then calls onFinish().
 *
 * Animation sequence:
 *  0ms   — logo fades in + scales up (spring)
 *  600ms — app name slides up + fades in
 *  1200ms— tagline fades in
 *  1600ms— whole screen fades out
 *  1800ms— onFinish() called
 */
import React, { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View, Dimensions } from "react-native";
import Svg, { Ellipse, Path } from "react-native-svg";

const { width } = Dimensions.get("window");

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

interface Props { onFinish: () => void; }

export default function SplashAnimation({ onFinish }: Props) {
  // Animation values
  const logoScale   = useRef(new Animated.Value(0.3)).current;
  const logoOpacity = useRef(new Animated.Value(0)).current;
  const nameTransY  = useRef(new Animated.Value(20)).current;
  const nameOpacity = useRef(new Animated.Value(0)).current;
  const tagOpacity  = useRef(new Animated.Value(0)).current;
  const screenOp    = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.sequence([
      // Step 1 — logo spring in (0–500ms)
      Animated.parallel([
        Animated.spring(logoScale,   { toValue: 1, friction: 6, tension: 80, useNativeDriver: true }),
        Animated.timing(logoOpacity, { toValue: 1, duration: 400, useNativeDriver: true }),
      ]),
      // Step 2 — app name slides up (500–800ms)
      Animated.parallel([
        Animated.timing(nameOpacity, { toValue: 1, duration: 300, useNativeDriver: true }),
        Animated.timing(nameTransY,  { toValue: 0, duration: 300, useNativeDriver: true }),
      ]),
      // Step 3 — tagline fades in (800–1100ms)
      Animated.timing(tagOpacity, { toValue: 1, duration: 300, useNativeDriver: true }),
      // Step 4 — hold for 400ms
      Animated.delay(400),
      // Step 5 — entire screen fades out (1500–1800ms)
      Animated.timing(screenOp, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]).start(() => onFinish());
  }, []);

  return (
    <Animated.View style={[s.root, { opacity: screenOp }]}>
      <View style={s.center}>
        {/* Logo */}
        <Animated.View style={[s.logoWrap, {
          transform: [{ scale: logoScale }],
          opacity: logoOpacity,
        }]}>
          <MityaharLeaf size={80} />
        </Animated.View>

        {/* App name */}
        <Animated.Text style={[s.appName, {
          opacity: nameOpacity,
          transform: [{ translateY: nameTransY }],
        }]}>
          Mityahar
        </Animated.Text>

        {/* Tagline */}
        <Animated.Text style={[s.tagline, { opacity: tagOpacity }]}>
          Your personal diet companion
        </Animated.Text>
      </View>

      {/* Bottom badge */}
      <Animated.Text style={[s.badge, { opacity: tagOpacity }]}>
        Powered by AI · Built for India
      </Animated.Text>
    </Animated.View>
  );
}

const s = StyleSheet.create({
  root:    { ...StyleSheet.absoluteFillObject, backgroundColor: "#fff", alignItems: "center", justifyContent: "center", zIndex: 999 },
  center:  { alignItems: "center" },
  logoWrap:{ width: 100, height: 100, borderRadius: 24, backgroundColor: "#F0FDF4", alignItems: "center", justifyContent: "center", marginBottom: 20, shadowColor: "#1E7C45", shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.15, shadowRadius: 12, elevation: 6 },
  appName: { fontSize: 36, fontWeight: "700", color: "#1E7C45", letterSpacing: 0.5 },
  tagline: { fontSize: 14, color: "#6B7280", marginTop: 8, letterSpacing: 0.2 },
  badge:   { position: "absolute", bottom: 40, fontSize: 11, color: "#D1D5DB" },
});
