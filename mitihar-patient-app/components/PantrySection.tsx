// Pantry, inline on the home dashboard.
//
// Was app/meals/pantry.tsx (a pushed screen). Moved here so patients can scroll
// to it instead of navigating away. No ScrollView of its own — it renders flat
// inside the home ScrollView; nesting two vertical scrollers breaks momentum
// and swallows touches on Android.
//
// Collapsed by default: the catalogue is up to 80 rows (_PANTRY_CATALOGUE_LIMIT
// in app/routers/meal_plan.py), which would bury everything below it on home.
import React, { useState, useEffect } from "react";
import { View, Text, Pressable, TextInput, StyleSheet, ActivityIndicator } from "react-native";
import { Check, Plus, Search, ChevronDown, ChevronUp } from "lucide-react-native";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "../lib/queryKeys";
import { getPantry, togglePantryItem, getPantrySuggestions } from "../services/meals";
import { useToast } from "./shared";
import type { PantryItem, PantrySuggestion } from "../types";

export default function PantrySection() {
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);

  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  // Only fetch once expanded — home already fires several queries on mount and
  // a collapsed pantry doesn't show anything worth paying for.
  const { data: pantry, isLoading } = useQuery({
    queryKey: QUERY_KEYS.PANTRY(debounced),
    queryFn: () => getPantry(debounced || undefined),
    enabled: open,
  });
  const { data: suggestions } = useQuery({
    queryKey: QUERY_KEYS.PANTRY_SUGGESTIONS,
    queryFn: getPantrySuggestions,
    enabled: open,
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
    <View style={s.wrap}>
      <Pressable style={s.head} onPress={() => setOpen(o => !o)}>
        <View style={{ flex: 1 }}>
          <Text style={s.headTitle}>🧊 My Pantry</Text>
          <Text style={s.headSub}>
            {pantry ? `${pantry.have_count} on hand · ` : ""}we rank meals you can cook
          </Text>
        </View>
        {open ? <ChevronUp size={18} color="#6B7280" /> : <ChevronDown size={18} color="#6B7280" />}
      </Pressable>

      {open && (
        <View style={s.body}>
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
            <View style={s.loader}><ActivityIndicator color="#1E7C45" /></View>
          ) : (
            <>
              {sugg.length > 0 && !debounced && (
                <>
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
                </>
              )}

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
            </>
          )}
        </View>
      )}
    </View>
  );
}

const s = StyleSheet.create({
  wrap:           { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", marginBottom: 12, overflow: "hidden" },
  head:           { flexDirection: "row", alignItems: "center", gap: 12, padding: 14 },
  headTitle:      { fontSize: 15, fontWeight: "600", color: "#111827" },
  headSub:        { fontSize: 11, color: "#6B7280", marginTop: 2 },
  body:           { borderTopWidth: 1, borderTopColor: "#F3F4F6", paddingBottom: 8 },
  loader:         { paddingVertical: 24, alignItems: "center" },
  searchWrap:     { flexDirection: "row", alignItems: "center", gap: 8, margin: 12, paddingHorizontal: 12, height: 42, borderRadius: 10, borderWidth: 1, borderColor: "#E5E7EB", backgroundColor: "#F9FAFB" },
  searchInput:    { flex: 1, fontSize: 14, color: "#111827" },
  catLabel:       { paddingHorizontal: 14, paddingVertical: 8, fontSize: 11, fontWeight: "600", color: "#9CA3AF", letterSpacing: 1 },
  catCard:        { borderTopWidth: 1, borderBottomWidth: 1, borderColor: "#F3F4F6" },
  itemRow:        { flexDirection: "row", alignItems: "center", gap: 12, paddingHorizontal: 14, paddingVertical: 12 },
  itemBorder:     { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  checkbox:       { width: 22, height: 22, borderRadius: 6, borderWidth: 1.5, borderColor: "#D1D5DB", backgroundColor: "#fff", alignItems: "center", justifyContent: "center" },
  checkboxChecked:{ borderColor: "#1E7C45", backgroundColor: "#1E7C45" },
  addBtn:         { width: 22, height: 22, borderRadius: 11, borderWidth: 1.5, borderColor: "#1E7C45", backgroundColor: "#DCFCE7", alignItems: "center", justifyContent: "center" },
  itemName:       { flex: 1, fontSize: 14, color: "#111827" },
  itemHave:       { color: "#1E7C45", fontWeight: "500" },
  reason:         { fontSize: 12, color: "#6B7280", marginTop: 2 },
  empty:          { padding: 20, fontSize: 14, color: "#9CA3AF", textAlign: "center" },
});
