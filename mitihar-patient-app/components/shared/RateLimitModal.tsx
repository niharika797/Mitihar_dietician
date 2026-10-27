import React from "react";
import { Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { Info } from "../../lib/icons";
import { useRateLimitStore } from "../../store/useRateLimitStore";

/** Pop-up for a 429 from the server. Message and wait time come from the server's answer. */
export function RateLimitModal() {
  const visible = useRateLimitStore((s) => s.visible);
  const message = useRateLimitStore((s) => s.message);
  const hide = useRateLimitStore((s) => s.hide);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={hide}>
      <View style={s.backdrop}>
        <View style={s.card} accessibilityRole="alert">
          <View style={s.iconWrap}>
            <Info size={22} color="#92400E" />
          </View>
          <Text style={s.title}>Please take a short break</Text>
          <Text style={s.body}>{message}</Text>
          <Pressable style={s.btn} onPress={hide} accessibilityRole="button" accessibilityLabel="Dismiss">
            <Text style={s.btnText}>OK</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const s = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: "rgba(17,24,39,0.45)", alignItems: "center", justifyContent: "center", padding: 24 },
  card:     { width: "100%", maxWidth: 380, backgroundColor: "#fff", borderRadius: 20, padding: 24, alignItems: "center" },
  iconWrap: { width: 44, height: 44, borderRadius: 22, backgroundColor: "#FEF3C7", alignItems: "center", justifyContent: "center", marginBottom: 12 },
  title:    { fontSize: 18, fontWeight: "700", color: "#111827", textAlign: "center" },
  body:     { fontSize: 14, lineHeight: 21, color: "#4B5563", textAlign: "center", marginTop: 8 },
  btn:      { marginTop: 20, height: 48, alignSelf: "stretch", borderRadius: 24, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center" },
  btnText:  { fontSize: 16, fontWeight: "600", color: "#fff" },
});
