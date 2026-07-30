import React, { useState, useEffect } from "react";
import { View, Text, ScrollView, Pressable, TextInput, StyleSheet, ActivityIndicator } from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft, Check, Plus, Search } from "lucide-react-native";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "../../lib/queryKeys";
import { getPantry, togglePantryItem, getPantrySuggestions } from "../../services/meals";
import { useToast } from "../../components/shared";
import type { PantryItem, PantrySuggestion } from "../../types";

export default function PantryScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();

  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  const { data: pantry, isLoading } = useQuery({
    queryKey: QUERY_KEYS.PANTRY(debounced),
    queryFn: () => getPantry(debounced || undefined),
  });
  const { data: suggestions } = useQuery({
    queryKey: QUERY_KEYS.PANTRY_SUGGESTIONS,
    queryFn: getPantrySuggestions,
  });

  const toggle = useMutation({
    mutationFn: ({ id, have }: { id: number; have: boolean }) => togglePantryItem(id, have),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["meal-plan", "pantry"] });
      qc.invalidateQueries({ queryKey: QUERY_KEYS.WEEK_PLAN });   // re-rank combos by new coverage
    },
    onError: () => showToast("Failed to update pantry", "error"),
  });

  const items: PantryItem[] = pantry?.items ?? [];
  const sugg: PantrySuggestion[] = suggestions ?? [];

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>My Pantry</Text>
        <View style={{ width: 36 }} />
      </View>
      <Text style={s.summary}>{pantry?.have_count ?? 0} ingredients on hand · we rank meals you can cook</Text>

      <View style={s.searchWrap}>
        <Search size={16} color="#9CA3AF" />
        <TextInput
          style={s.searchInput}
          placeholder="Search ingredients…"
          placeholderTextColor="#9CA3AF"
          value={search}
          onChangeText={setSearch}
          autoCorrect={false}
        />
      </View>

      {isLoading ? (
        <View style={s.loader}><ActivityIndicator size="large" color="#1E7C45" /></View>
      ) : (
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 32 }}>
          {sugg.length > 0 && !debounced && (
            <View style={s.section}>
              <Text style={s.catLabel}>SUGGESTED FOR YOUR CONDITIONS</Text>
              <View style={s.catCard}>
                {sugg.map((sg, i) => (
                  <Pressable
                    key={sg.ingredient_id}
                    onPress={() => toggle.mutate({ id: sg.ingredient_id, have: true })}
                    style={[s.itemRow, i < sugg.length - 1 && s.itemBorder]}
                  >
                    <View style={s.addBtn}><Plus size={14} color="#1E7C45" strokeWidth={3} /></View>
                    <View style={{ flex: 1 }}>
                      <Text style={s.itemName}>{sg.name}{sg.name_hindi ? `  ·  ${sg.name_hindi}` : ""}</Text>
                      <Text style={s.reason}>{sg.reason}</Text>
                    </View>
                  </Pressable>
                ))}
              </View>
            </View>
          )}

          <View style={s.section}>
            <Text style={s.catLabel}>{debounced ? "SEARCH RESULTS" : "COMMON INGREDIENTS"}</Text>
            <View style={s.catCard}>
              {items.length === 0 ? (
                <Text style={s.empty}>No ingredients found.</Text>
              ) : items.map((it, i) => (
                <Pressable
                  key={it.ingredient_id}
                  onPress={() => toggle.mutate({ id: it.ingredient_id, have: !it.have })}
                  style={[s.itemRow, i < items.length - 1 && s.itemBorder]}
                >
                  <View style={[s.checkbox, it.have && s.checkboxChecked]}>
                    {it.have && <Check size={12} color="#fff" strokeWidth={3} />}
                  </View>
                  <Text style={[s.itemName, it.have && s.itemHave]}>
                    {it.name}{it.name_hindi ? `  ·  ${it.name_hindi}` : ""}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>
        </ScrollView>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  root:           { flex: 1, backgroundColor: "#F9FAFB" },
  loader:         { paddingVertical: 60, alignItems: "center" },
  header:         { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:        { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:          { fontSize: 18, fontWeight: "600", color: "#111827" },
  summary:        { fontSize: 13, color: "#6B7280", paddingHorizontal: 20, paddingVertical: 10 },
  searchWrap:     { flexDirection: "row", alignItems: "center", gap: 8, marginHorizontal: 16, marginBottom: 8, paddingHorizontal: 12, height: 44, borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", backgroundColor: "#fff" },
  searchInput:    { flex: 1, fontSize: 14, color: "#111827" },
  section:        { marginBottom: 8 },
  catLabel:       { paddingHorizontal: 20, paddingVertical: 8, fontSize: 11, fontWeight: "600", color: "#9CA3AF", letterSpacing: 1 },
  catCard:        { backgroundColor: "#fff", borderTopWidth: 1, borderBottomWidth: 1, borderColor: "#E5E7EB" },
  itemRow:        { flexDirection: "row", alignItems: "center", gap: 12, paddingHorizontal: 20, paddingVertical: 14 },
  itemBorder:     { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  checkbox:       { width: 22, height: 22, borderRadius: 6, borderWidth: 1.5, borderColor: "#D1D5DB", backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  checkboxChecked:{ borderColor: "#1E7C45", backgroundColor: "#1E7C45" },
  addBtn:         { width: 22, height: 22, borderRadius: 11, borderWidth: 1.5, borderColor: "#1E7C45", backgroundColor: "#DCFCE7", alignItems: "center", justifyContent: "center" },
  itemName:       { flex: 1, fontSize: 14, color: "#111827" },
  itemHave:       { color: "#1E7C45", fontWeight: "500" },
  reason:         { fontSize: 12, color: "#6B7280", marginTop: 2 },
  empty:          { padding: 20, fontSize: 14, color: "#9CA3AF", textAlign: "center" },
});
