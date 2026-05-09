import React, { useState } from "react";
import {
  View, Text, TextInput, ScrollView, Pressable, StyleSheet, ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft } from "lucide-react-native";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { updateProfile } from "../../services/profile";
import { useAuthStore } from "../../store/useAuthStore";
import { useToast } from "../../components/shared";
import { QUERY_KEYS } from "../../lib/queryKeys";

export default function EditProfileScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const profile = useAuthStore(s => s.profile);
  const setProfile = useAuthStore(s => s.setProfile);

  const [name,         setName]         = useState(profile?.name ?? "");
  const [phone,        setPhone]        = useState(profile?.phone ?? "");
  const [weight,       setWeight]       = useState(String(profile?.weight_kg ?? ""));
  const [targetWeight, setTargetWeight] = useState(String(profile?.target_weight_kg ?? ""));

  const hasChanges =
    name         !== (profile?.name ?? "")                          ||
    phone        !== (profile?.phone ?? "")                         ||
    parseFloat(weight)       !== profile?.weight_kg                 ||
    parseFloat(targetWeight) !== profile?.target_weight_kg;

  const saveMut = useMutation({
    mutationFn: () => updateProfile({
      name,
      phone: phone || undefined,
      weight_kg:        parseFloat(weight)       || undefined,
      target_weight_kg: parseFloat(targetWeight) || undefined,
    }),
    onSuccess: (updated) => {
      setProfile(updated);
      qc.invalidateQueries({ queryKey: QUERY_KEYS.ME });
      showToast("Profile updated! ✅", "success");
      router.back();
    },
    onError: () => showToast("Failed to save changes", "error"),
  });

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Edit Profile</Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>
        <Text style={s.sectionLabel}>PERSONAL DETAILS</Text>

        <View style={s.field}>
          <Text style={s.label}>Full Name</Text>
          <TextInput style={s.input} value={name} onChangeText={setName} placeholder="Your name" placeholderTextColor="#9CA3AF" />
        </View>

        <View style={s.field}>
          <Text style={s.label}>Email Address</Text>
          <TextInput style={[s.input, s.inputLocked]} value={profile?.email ?? ""} editable={false} />
          <Text style={s.hint}>Email cannot be changed</Text>
        </View>

        <View style={s.field}>
          <Text style={s.label}>Phone Number</Text>
          <TextInput style={s.input} value={phone} onChangeText={setPhone} keyboardType="phone-pad" placeholder="+91 XXXXX XXXXX" placeholderTextColor="#9CA3AF" />
        </View>

        <View style={s.divider} />
        <Text style={s.sectionLabel}>HEALTH METRICS</Text>

        <View style={s.row}>
          <View style={[s.field, { flex: 1 }]}>
            <Text style={s.label}>Current Weight</Text>
            <View style={s.unitWrap}>
              <TextInput style={[s.input, { paddingRight: 40 }]} value={weight} onChangeText={setWeight} keyboardType="decimal-pad" placeholder="70" placeholderTextColor="#9CA3AF" />
              <Text style={s.unit}>kg</Text>
            </View>
          </View>
          <View style={[s.field, { flex: 1 }]}>
            <Text style={s.label}>Target Weight</Text>
            <View style={s.unitWrap}>
              <TextInput style={[s.input, { paddingRight: 40 }]} value={targetWeight} onChangeText={setTargetWeight} keyboardType="decimal-pad" placeholder="65" placeholderTextColor="#9CA3AF" />
              <Text style={s.unit}>kg</Text>
            </View>
          </View>
        </View>

        {parseFloat(weight) !== profile?.weight_kg && (
          <View style={s.warningBox}>
            <Text style={s.warningText}>⚠️ Updating your weight will recalculate your daily calorie target.</Text>
          </View>
        )}

        <Pressable
          style={[s.saveBtn, !hasChanges && s.saveBtnDisabled]}
          onPress={() => saveMut.mutate()}
          disabled={!hasChanges || saveMut.isPending}
        >
          {saveMut.isPending
            ? <ActivityIndicator color="#fff" />
            : <Text style={[s.saveBtnText, !hasChanges && s.saveBtnTextDisabled]}>Save Changes</Text>}
        </Pressable>
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root:               { flex: 1, backgroundColor: "#F9FAFB" },
  header:             { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:            { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:              { fontSize: 18, fontWeight: "600", color: "#111827" },
  scroll:             { padding: 20, gap: 16 },
  sectionLabel:       { fontSize: 11, fontWeight: "600", color: "#374151", letterSpacing: 1 },
  field:              { gap: 6 },
  label:              { fontSize: 14, fontWeight: "500", color: "#374151" },
  input:              { height: 52, borderRadius: 12, borderWidth: 1.5, borderColor: "#E5E7EB", paddingHorizontal: 16, fontSize: 14, color: "#111827", backgroundColor: "#fff" },
  inputLocked:        { backgroundColor: "#F9FAFB", color: "#9CA3AF" },
  hint:               { fontSize: 12, color: "#9CA3AF" },
  divider:            { height: 1, backgroundColor: "#E5E7EB" },
  row:                { flexDirection: "row", gap: 12 },
  unitWrap:           { position: "relative" },
  unit:               { position: "absolute", right: 14, top: 16, fontSize: 13, color: "#6B7280" },
  warningBox:         { backgroundColor: "#FEF3C7", borderWidth: 1, borderColor: "#FCD34D", borderRadius: 8, padding: 12 },
  warningText:        { fontSize: 12, color: "#92400E" },
  saveBtn:            { height: 52, borderRadius: 26, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center", marginTop: 8 },
  saveBtnDisabled:    { backgroundColor: "#E5E7EB" },
  saveBtnText:        { fontSize: 16, fontWeight: "600", color: "#fff" },
  saveBtnTextDisabled:{ color: "#9CA3AF" },
});
