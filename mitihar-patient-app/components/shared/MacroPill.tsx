import React from "react";
import { View, Text, StyleSheet } from "react-native";

type MacroType = "protein" | "carbs" | "fat" | "fiber";

const MACRO_CONFIG: Record<MacroType, { bg: string; text: string; label: string }> = {
  protein: { bg: "#DCFCE7", text: "#166534", label: "P" },
  carbs:   { bg: "#FEF3C7", text: "#92400E", label: "C" },
  fat:     { bg: "#F3E8FF", text: "#6B21A8", label: "F" },
  fiber:   { bg: "#DBEAFE", text: "#1E40AF", label: "Fi" },
};

interface MacroPillProps {
  type: MacroType;
  value: string | number;
  unit?: string;
}

export function MacroPill({ type, value, unit = "g" }: MacroPillProps) {
  const cfg = MACRO_CONFIG[type];
  return (
    <View style={[s.pill, { backgroundColor: cfg.bg }]}>
      <Text style={[s.text, { color: cfg.text }]}>
        {cfg.label} {value}{unit}
      </Text>
    </View>
  );
}

interface MacroRowProps {
  protein: number;
  carbs: number;
  fat: number;
  fiber?: number;
}

export function MacroRow({ protein, carbs, fat, fiber }: MacroRowProps) {
  return (
    <View style={s.row}>
      <MacroPill type="protein" value={protein} />
      <MacroPill type="carbs"   value={carbs} />
      <MacroPill type="fat"     value={fat} />
      {fiber !== undefined && <MacroPill type="fiber" value={fiber} />}
    </View>
  );
}

const s = StyleSheet.create({
  pill: { borderRadius: 99, paddingHorizontal: 8, paddingVertical: 3 },
  text: { fontSize: 11, fontWeight: "600" },
  row:  { flexDirection: "row", flexWrap: "wrap", gap: 6 },
});
