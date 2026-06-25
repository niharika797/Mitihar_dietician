import React from "react";
import { View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft, Share2, Check } from "lucide-react-native";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { getShoppingList, toggleShoppingItem } from "../../services/meals";
import { useToast } from "../../components/shared";
import type { ShoppingItem } from "../../types";

export default function ShoppingListScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();

  const { data: list, isLoading } = useQuery({
    queryKey: QUERY_KEYS.SHOPPING_LIST,
    queryFn: getShoppingList,
  });

  const toggleMut = useMutation({
    mutationFn: ({ name, at_home }: { name: string; at_home: boolean }) =>
      toggleShoppingItem(name, !at_home),
    onSuccess: () => qc.invalidateQueries({ queryKey: QUERY_KEYS.SHOPPING_LIST }),
    onError: () => showToast("Failed to update item", "error"),
  });

  // ShoppingListResponse = { [category: string]: ShoppingItem[] }
  // Guard: filter out any non-array values (e.g. if backend adds metadata keys)
  const categories = list ? Object.keys(list).filter(k => Array.isArray(list![k])) : [];
  const allItems: ShoppingItem[] = categories.flatMap(cat => (Array.isArray(list![cat]) ? list![cat] : []));
  const checkedCount = allItems.filter(i => i.have_at_home).length;

  if (isLoading) return <View style={s.loader}><ActivityIndicator size="large" color="#1E7C45" /></View>;

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Shopping List</Text>
        <Pressable onPress={() => showToast("List shared! 📤", "success")} style={s.shareBtn} hitSlop={8}>
          <Share2 size={16} color="#374151" />
        </Pressable>
      </View>

      <Text style={s.summary}>{allItems.length - checkedCount} items needed · {checkedCount} already have</Text>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 32 }}>
        {categories.length === 0 ? (
          <View style={s.empty}>
            <Text style={s.emptyEmoji}>🛒</Text>
            <Text style={s.emptyTitle}>No shopping list yet</Text>
            <Text style={s.emptySub}>Your shopping list will appear once your doctor creates a meal plan.</Text>
          </View>
        ) : (
          categories.map(cat => {
            const catItems: ShoppingItem[] = Array.isArray(list![cat]) ? list![cat] : [];
            return (
              <View key={cat} style={s.catSection}>
                <Text style={s.catLabel}>{cat.toUpperCase()}</Text>
                <View style={s.catCard}>
                  {catItems.map((item, i) => (
                    <Pressable
                      key={item.ingredient}
                      onPress={() => toggleMut.mutate({ name: item.ingredient, at_home: item.at_home })}
                      style={[s.itemRow, i < catItems.length - 1 && s.itemBorder]}
                    >
                      <View style={[s.checkbox, item.at_home && s.checkboxChecked]}>
                        {item.at_home && <Check size={12} color="#fff" strokeWidth={3} />}
                      </View>
                      <Text style={[s.itemName, item.at_home && s.itemChecked]}>
                        {item.ingredient}
                      </Text>
                      <Text style={[s.itemQty, item.at_home && s.itemChecked]}>
                        {item.quantity} {item.unit}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              </View>
            );
          })
        )}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root:           { flex: 1, backgroundColor: "#F9FAFB" },
  loader:         { flex: 1, alignItems: "center", justifyContent: "center" },
  header:         { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:        { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:          { fontSize: 18, fontWeight: "600", color: "#111827" },
  shareBtn:       { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  summary:        { fontSize: 13, color: "#6B7280", paddingHorizontal: 20, paddingVertical: 10 },
  catSection:     { marginBottom: 8 },
  catLabel:       { paddingHorizontal: 20, paddingVertical: 8, fontSize: 11, fontWeight: "600", color: "#9CA3AF", letterSpacing: 1 },
  catCard:        { backgroundColor: "#fff", borderTopWidth: 1, borderBottomWidth: 1, borderColor: "#E5E7EB" },
  itemRow:        { flexDirection: "row", alignItems: "center", gap: 12, paddingHorizontal: 20, paddingVertical: 14 },
  itemBorder:     { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  checkbox:       { width: 22, height: 22, borderRadius: 6, borderWidth: 1.5, borderColor: "#D1D5DB", backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  checkboxChecked:{ borderColor: "#1E7C45", backgroundColor: "#1E7C45" },
  itemName:       { flex: 1, fontSize: 14, color: "#111827" },
  itemQty:        { fontSize: 13, color: "#6B7280" },
  itemChecked:    { color: "#9CA3AF", textDecorationLine: "line-through" },
  empty:          { alignItems: "center", paddingVertical: 60, paddingHorizontal: 32 },
  emptyEmoji:     { fontSize: 48, marginBottom: 12 },
  emptyTitle:     { fontSize: 18, fontWeight: "600", color: "#111827", marginBottom: 8 },
  emptySub:       { fontSize: 14, color: "#6B7280", textAlign: "center", lineHeight: 20 },
});
