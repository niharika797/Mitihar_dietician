// Shopping list, inline on the home dashboard.
//
// Was app/meals/shopping-list.tsx (a pushed screen). Same reasoning as
// PantrySection: no ScrollView of its own, renders flat inside home's scroller.
//
// The list query runs even while collapsed — it's one request and it drives the
// "N items needed" count in the header, which is the whole point of showing the
// section at a glance.
import React, { useState } from "react";
import { View, Text, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { Check, ChevronDown, ChevronUp } from "lucide-react-native";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "../lib/queryKeys";
import { getShoppingList, toggleShoppingItem } from "../services/meals";
import { useToast } from "./shared";
import type { ShoppingItem } from "../types";

export default function ShoppingListSection() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);

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
  // `at_home`, not `have_at_home` — the old screen read a field that doesn't
  // exist on ShoppingItem, so this count was permanently 0.
  const checkedCount = allItems.filter(i => i.at_home).length;

  return (
    <View style={s.wrap}>
      <Pressable style={s.head} onPress={() => setOpen(o => !o)}>
        <View style={{ flex: 1 }}>
          <Text style={s.headTitle}>🛒 Shopping List</Text>
          <Text style={s.headSub}>
            {isLoading
              ? "loading…"
              : `${allItems.length - checkedCount} items needed · ${checkedCount} already have`}
          </Text>
        </View>
        {open ? <ChevronUp size={18} color="#6B7280" /> : <ChevronDown size={18} color="#6B7280" />}
      </Pressable>

      {open && (
        <View style={s.body}>
          {isLoading ? (
            <View style={s.loader}><ActivityIndicator color="#1E7C45" /></View>
          ) : categories.length === 0 ? (
            <Text style={s.empty}>
              Your shopping list will appear once your doctor creates a meal plan.
            </Text>
          ) : (
            categories.map(cat => {
              const catItems: ShoppingItem[] = Array.isArray(list![cat]) ? list![cat] : [];
              return (
                <View key={cat}>
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
        </View>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  wrap:           { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", marginBottom: 20, overflow: "hidden" },
  head:           { flexDirection: "row", alignItems: "center", gap: 12, padding: 14 },
  headTitle:      { fontSize: 15, fontWeight: "600", color: "#111827" },
  headSub:        { fontSize: 11, color: "#6B7280", marginTop: 2 },
  body:           { borderTopWidth: 1, borderTopColor: "#F3F4F6", paddingBottom: 8 },
  loader:         { paddingVertical: 24, alignItems: "center" },
  catLabel:       { paddingHorizontal: 14, paddingVertical: 8, fontSize: 11, fontWeight: "600", color: "#9CA3AF", letterSpacing: 1 },
  catCard:        { borderTopWidth: 1, borderBottomWidth: 1, borderColor: "#F3F4F6" },
  itemRow:        { flexDirection: "row", alignItems: "center", gap: 12, paddingHorizontal: 14, paddingVertical: 12 },
  itemBorder:     { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  checkbox:       { width: 22, height: 22, borderRadius: 6, borderWidth: 1.5, borderColor: "#D1D5DB", backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  checkboxChecked:{ borderColor: "#1E7C45", backgroundColor: "#1E7C45" },
  itemName:       { flex: 1, fontSize: 14, color: "#111827" },
  itemQty:        { fontSize: 13, color: "#6B7280" },
  itemChecked:    { color: "#9CA3AF", textDecorationLine: "line-through" },
  empty:          { padding: 20, fontSize: 13, color: "#9CA3AF", textAlign: "center", lineHeight: 20 },
});
