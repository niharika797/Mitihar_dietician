import React from "react";
import { View, Text, ScrollView, Pressable, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import type { AppNotification } from "../../types";

const SAMPLE: AppNotification[] = [
  { id: 1, type: "plan_update", title: "Plan Updated",        body: "Your doctor swapped Thursday dinner to Dal Makhani", time: "09:15 AM", date: "today",     read: false },
  { id: 2, type: "reminder",   title: "Lunch Reminder",       body: "Time to log your lunch — Dal Tadka + Rotis 🍛",      time: "01:05 PM", date: "today",     read: false },
  { id: 3, type: "streak",     title: "🔥 Streak Milestone!", body: "You've logged 7 days in a row. Keep it up!",          time: "08:00 AM", date: "today",     read: true  },
  { id: 4, type: "info",       title: "Weekly Report Ready",  body: "Your weekly progress report is available to view",   time: "07:00 AM", date: "yesterday", read: true  },
];

const TYPE_BG: Record<string, string>     = { plan_update: "#DCFCE7", reminder: "#DBEAFE", streak: "#FFFBEB", info: "#F3F4F6" };
const TYPE_ICON: Record<string, string>   = { plan_update: "🟢",      reminder: "🔔",      streak: "🔥",      info: "ℹ️"    };
const TYPE_BORDER: Record<string, string> = { plan_update: "#1E7C45", reminder: "#2563EB", streak: "#D97706", info: "#9CA3AF" };

function NotifRow({ n }: { n: AppNotification }) {
  return (
    <View style={[s.row, n.read && s.rowRead, { borderLeftColor: TYPE_BORDER[n.type] }]}>
      <View style={[s.iconWrap, { backgroundColor: TYPE_BG[n.type] }]}>
        <Text style={s.iconEmoji}>{TYPE_ICON[n.type]}</Text>
      </View>
      <View style={s.content}>
        <View style={s.contentTop}>
          <Text style={s.rowTitle} numberOfLines={1}>{n.title}</Text>
          <Text style={s.rowTime}>{n.time}</Text>
        </View>
        <Text style={s.rowBody} numberOfLines={2}>{n.body}</Text>
      </View>
    </View>
  );
}

function Section({ label, items }: { label: string; items: AppNotification[] }) {
  return (
    <View style={s.section}>
      <Text style={s.sectionLabel}>{label}</Text>
      <View style={s.sectionCard}>
        {items.map((n, i) => (
          <View key={n.id} style={i < items.length - 1 ? s.itemBorder : undefined}>
            <NotifRow n={n} />
          </View>
        ))}
      </View>
    </View>
  );
}

export default function NotificationsScreen() {
  const router = useRouter();
  const today     = SAMPLE.filter(n => n.date === "today");
  const yesterday = SAMPLE.filter(n => n.date === "yesterday");

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Notifications</Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView style={s.scroll} contentContainerStyle={{ paddingBottom: 32 }} showsVerticalScrollIndicator={false}>
        {today.length > 0     && <Section label="TODAY"     items={today} />}
        {yesterday.length > 0 && <Section label="YESTERDAY" items={yesterday} />}
        {SAMPLE.length === 0  && (
          <View style={s.empty}>
            <Text style={s.emptyEmoji}>✅</Text>
            <Text style={s.emptyTitle}>You're all caught up!</Text>
            <Text style={s.emptySub}>No new notifications</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root:        { flex: 1, backgroundColor: "#F9FAFB" },
  header:      { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:     { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:       { fontSize: 18, fontWeight: "600", color: "#111827" },
  scroll:      { flex: 1 },
  section:     { marginBottom: 8 },
  sectionLabel:{ paddingHorizontal: 20, paddingVertical: 10, fontSize: 11, fontWeight: "600", color: "#9CA3AF", letterSpacing: 1 },
  sectionCard: { backgroundColor: "#fff", borderTopWidth: 1, borderBottomWidth: 1, borderColor: "#E5E7EB" },
  row:         { flexDirection: "row", alignItems: "flex-start", gap: 12, padding: 14, paddingLeft: 12, backgroundColor: "#fff", borderLeftWidth: 3 },
  rowRead:     { backgroundColor: "#F9FAFB", borderLeftColor: "transparent" },
  itemBorder:  { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  iconWrap:    { width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center", flexShrink: 0 },
  iconEmoji:   { fontSize: 18 },
  content:     { flex: 1 },
  contentTop:  { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 2 },
  rowTitle:    { fontSize: 14, fontWeight: "600", color: "#111827", flex: 1 },
  rowTime:     { fontSize: 11, color: "#9CA3AF", marginLeft: 8, flexShrink: 0 },
  rowBody:     { fontSize: 13, color: "#6B7280", lineHeight: 18 },
  empty:       { alignItems: "center", paddingVertical: 60 },
  emptyEmoji:  { fontSize: 48, marginBottom: 12 },
  emptyTitle:  { fontSize: 18, fontWeight: "600", color: "#111827", marginBottom: 4 },
  emptySub:    { fontSize: 14, color: "#6B7280" },
});
