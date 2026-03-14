import React, { useState } from "react";
import {
  View, TextInput as RNTextInput, Text, Pressable,
  StyleSheet, TextInputProps, ViewStyle,
} from "react-native";
import { Eye, EyeOff } from "lucide-react-native";

interface StyledInputProps extends TextInputProps {
  label?: string;
  hint?: string;
  error?: string;
  suffix?: string;
  isPassword?: boolean;
  containerStyle?: ViewStyle;
}

export function StyledInput({
  label, hint, error, suffix, isPassword, containerStyle, ...rest
}: StyledInputProps) {
  const [focused, setFocused] = useState(false);
  const [visible, setVisible] = useState(false);

  const borderColor = error ? "#DC2626" : focused ? "#1E7C45" : "#E5E7EB";

  return (
    <View style={[styles.container, containerStyle]}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <View style={[styles.inputRow, { borderColor }]}>
        <RNTextInput
          {...rest}
          secureTextEntry={isPassword && !visible}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholderTextColor="#9CA3AF"
          style={styles.input}
        />
        {isPassword && (
          <Pressable onPress={() => setVisible(v => !v)} style={styles.eyeBtn}>
            {visible
              ? <EyeOff size={18} color="#6B7280" />
              : <Eye size={18} color="#6B7280" />}
          </Pressable>
        )}
        {suffix && !isPassword ? (
          <Text style={styles.suffix}>{suffix}</Text>
        ) : null}
      </View>
      {error  ? <Text style={styles.error}>{error}</Text>  : null}
      {hint && !error ? <Text style={styles.hint}>{hint}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: 6 },
  label:     { fontSize: 14, fontFamily: "Inter_500Medium", color: "#374151" },
  inputRow: {
    flexDirection: "row",
    alignItems: "center",
    height: 52,
    borderRadius: 12,
    borderWidth: 1.5,
    backgroundColor: "#fff",
    paddingHorizontal: 16,
  },
  input:  { flex: 1, fontSize: 14, fontFamily: "Inter_400Regular", color: "#111827" },
  eyeBtn: { paddingLeft: 8 },
  suffix: { fontSize: 13, color: "#6B7280", fontFamily: "Inter_400Regular" },
  error:  { fontSize: 12, color: "#DC2626", fontFamily: "Inter_400Regular" },
  hint:   { fontSize: 12, color: "#9CA3AF", fontFamily: "Inter_400Regular" },
});
