import React from "react";
import { View, Text, ScrollView, Pressable, StyleSheet } from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft, Bell } from "lucide-react-native";

export default function NotificationsScreen() {
  const router = useRouter();

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Notifications</Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView style={s.scroll} contentContainerStyle={s.scrollContent} showsVerticalScrollIndicator={false}>
        <View style={s.empty}>
          <View style={s.bellWrap}>
            <Bell size={40} color="#9CA3AF" />
          </View>
          <Text style={s.emptyTitle}>No notifications yet</Text>
          <Text style={s.emptySub}>Your doctor and plan updates will appear here.</Text>
        </View>
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
  scrollContent:{ flexGrow: 1 },
  empty:       { flex: 1, alignItems: "center", justifyContent: "center", paddingVertical: 80 },
  bellWrap:    { width: 80, height: 80, borderRadius: 40, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center", marginBottom: 16 },
  emptyTitle:  { fontSize: 18, fontWeight: "600", color: "#111827", marginBottom: 6 },
  emptySub:    { fontSize: 14, color: "#6B7280", textAlign: "center", paddingHorizontal: 32 },
});
