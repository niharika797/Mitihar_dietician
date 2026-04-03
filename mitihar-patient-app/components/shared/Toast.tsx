import React, { createContext, useContext, useState, useCallback, useRef } from "react";
import { View, Text, StyleSheet } from "react-native";
import Animated, { useSharedValue, useAnimatedStyle, withSpring, withDelay, withTiming, runOnJS } from "react-native-reanimated";
import { CheckCircle, XCircle, Info } from "lucide-react-native";

type ToastType = "success" | "error" | "info";

interface ToastItem {
  id: number;
  message: string;
  type: ToastType;
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const ICONS = {
  success: <CheckCircle size={18} color="#166534" />,
  error:   <XCircle    size={18} color="#991B1B" />,
  info:    <Info       size={18} color="#1E40AF" />,
};

const BG: Record<ToastType, string> = {
  success: "#DCFCE7",
  error:   "#FEE2E2",
  info:    "#DBEAFE",
};

const TEXT_COLOR: Record<ToastType, string> = {
  success: "#166534",
  error:   "#991B1B",
  info:    "#1E40AF",
};

function ToastItem({ item, onDone }: { item: ToastItem; onDone: () => void }) {
  const translateY = useSharedValue(-80);
  const opacity    = useSharedValue(0);

  React.useEffect(() => {
    translateY.value = withSpring(0, { damping: 14, stiffness: 180 });
    opacity.value    = withTiming(1, { duration: 200 });

    // Auto-dismiss after 2.8 s
    const timer = setTimeout(() => {
      opacity.value    = withTiming(0, { duration: 200 });
      translateY.value = withTiming(-80, { duration: 200 }, (done) => {
        if (done) runOnJS(onDone)();
      });
    }, 2800);

    return () => clearTimeout(timer);
  }, []);

  const style = useAnimatedStyle(() => ({
    transform: [{ translateY: translateY.value }],
    opacity: opacity.value,
  }));

  return (
    <Animated.View style={[s.toast, { backgroundColor: BG[item.type] }, style]}>
      {ICONS[item.type]}
      <Text style={[s.msg, { color: TEXT_COLOR[item.type] }]} numberOfLines={2}>
        {item.message}
      </Text>
    </Animated.View>
  );
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const counter = useRef(0);

  const showToast = useCallback((message: string, type: ToastType = "info") => {
    const id = ++counter.current;
    setToasts(prev => [...prev, { id, message, type }]);
  }, []);

  const removeToast = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <View style={s.container} pointerEvents="none">
        {toasts.map(t => (
          <ToastItem key={t.id} item={t} onDone={() => removeToast(t.id)} />
        ))}
      </View>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}

const s = StyleSheet.create({
  container: {
    position: "absolute",
    top: 56, left: 16, right: 16,
    zIndex: 9999,
    gap: 8,
  },
  toast: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderRadius: 12,
    boxShadow: "0px 2px 8px rgba(0,0,0,0.08)",
  },
  msg: {
    flex: 1,
    fontSize: 14,
    fontWeight: "500",
    lineHeight: 19,
  },
});
