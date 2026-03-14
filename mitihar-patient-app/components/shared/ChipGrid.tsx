import React from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import { Check } from "lucide-react-native";

interface ChipGridProps {
  options: string[];
  selected: string[];
  onToggle: (value: string) => void;
  columns?: 1 | 2;
  small?: boolean;
}

export function ChipGrid({ options, selected, onToggle, columns = 2, small = false }: ChipGridProps) {
  return (
    <View style={[s.grid, columns === 1 && s.singleCol]}>
      {options.map(opt => {
        const sel = selected.includes(opt);
        return (
          <Pressable
            key={opt}
            onPress={() => onToggle(opt)}
            style={[
              s.chip,
              columns === 1 && s.chipFull,
              sel && s.chipSel,
              small && s.chipSmall,
            ]}
          >
            {sel && <Check size={small ? 12 : 14} color="#166534" />}
            <Text style={[s.label, sel && s.labelSel, small && s.labelSmall]} numberOfLines={2}>
              {opt}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const s = StyleSheet.create({
  grid:       { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  singleCol:  { flexDirection: "column" },
  chip: {
    flexBasis: "47%", flexGrow: 1,
    height: 48,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: "#E5E7EB",
    backgroundColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
    flexDirection: "row",
    gap: 4,
    paddingHorizontal: 8,
  },
  chipFull:   { flexBasis: "100%", flexGrow: 0 },
  chipSel:    { borderColor: "#1E7C45", backgroundColor: "#DCFCE7" },
  chipSmall:  { height: 42 },
  label:      { fontSize: 13, fontWeight: "500", color: "#374151", textAlign: "center" },
  labelSel:   { color: "#166534" },
  labelSmall: { fontSize: 12 },
});
