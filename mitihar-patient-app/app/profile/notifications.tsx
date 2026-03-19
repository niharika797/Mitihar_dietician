import React, { useState, useEffect } from "react";
import { View, Text, Pressable, StyleSheet, Switch, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import * as SecureStore from "expo-secure-store";

type NotifSetting = { id: string; label: string; sub: string; value: boolean };

const DEFAULTS: NotifSetting[] = [
  { id: "meal_reminders",  label: "Meal Reminders",      sub: "Reminders at Breakfast, Lunch & Dinner",     value: true  },
  { id: "water_reminders", label: "Water Reminders",     sub: "Hydration nudges every 2 hours",             value: true  },
  { id: "plan_updates",    label: "Plan Updates",        sub: "When your doctor updates your meal plan",    value: true  },
  { id: "weight_log",      label: "Weight Log Prompt",   sub: "Daily morning reminder to log your weight",  value: false },
  { id: "weekly_report",   label: "Weekly Report",       sub: "Sunday summary of your week's progress",     value: true  },
  { id: "promotions",      label: "Tips & Promotions",   sub: "Health tips and app feature updates",        value: false },
];

const STORAGE_KEY = "mityahar_notif_settings";

export default function NotificationsScreen() {
  const router = useRouter();
  const [settings, setSettings] = useState<NotifSetting[]>(DEFAULTS);
  const [loading, setLoading] = useState(true);

  // Load persisted settings on mount
  useEffect(() => {
    SecureStore.getItemAsync(STORAGE_KEY)
      .then(raw => {
        if (raw) {
          const saved: Record<string, boolean> = JSON.parse(raw);
          setSettings(prev => prev.map(s => ({
            ...s,
            value: saved[s.id] !== undefined ? saved[s.id] : s.value,
          })));
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const toggle = (id: string) => {
    setSettings(prev => {
      const next = prev.map(s => s.id === id ? { ...s, value: !s.value } : s);
      const toSave: Record<string, boolean> = {};
      next.forEach(s => { toSave[s.id] = s.value; });
      SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(toSave)).catch(() => {});
      return next;
    });
  };

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Notifications</Text>
        <View style={{ width: 36 }} />
      </View>

      {loading ? (
        <View style={s.loader}>
          <ActivityIndicator color="#1E7C45" />
        </View>
      ) : (
        <View style={s.card}>
          {settings.map((item, i) => (
            <View key={item.id} style={[s.row, i < settings.length - 1 && s.rowBorder]}>
              <View style={s.rowLeft}>
                <Text style={s.rowLabel}>{item.label}</Text>
                <Text style={s.rowSub}>{item.sub}</Text>
              </View>
              <Switch
                value={item.value}
                onValueChange={() => toggle(item.id)}
                trackColor={{ false: "#E5E7EB", true: "#34B164" }}
                thumbColor="#fff"
              />
            </View>
          ))}
        </View>
      )}

      <Text style={s.footer}>
        Push notification permissions are managed via your device settings.
        {"\n"}Actual push delivery requires FCM setup (coming soon).
      </Text>
    </View>
  );
}

const s = StyleSheet.create({
  root:      { flex: 1, backgroundColor: "#F9FAFB" },
  header:    { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:   { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:     { fontSize: 18, fontWeight: "600", color: "#111827" },
  loader:    { flex: 1, alignItems: "center", justifyContent: "center" },
  card:      { backgroundColor: "#fff", borderTopWidth: 1, borderBottomWidth: 1, borderColor: "#E5E7EB", marginTop: 16 },
  row:       { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 20, paddingVertical: 14 },
  rowBorder: { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  rowLeft:   { flex: 1, marginRight: 12 },
  rowLabel:  { fontSize: 14, fontWeight: "500", color: "#111827" },
  rowSub:    { fontSize: 12, color: "#6B7280", marginTop: 2 },
  footer:    { fontSize: 12, color: "#9CA3AF", textAlign: "center", paddingHorizontal: 24, marginTop: 20, lineHeight: 18 },
});
