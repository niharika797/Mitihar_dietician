import React from "react";
import { View, Text, ScrollView, Pressable, StyleSheet, Linking } from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft, ExternalLink } from "lucide-react-native";

const APP_VERSION = "1.0.0";

const LINKS = [
  { label: "Privacy Policy",   url: "https://mitihar.com/privacy"  },
  { label: "Terms of Service", url: "https://mitihar.com/terms"    },
  { label: "Contact Support",  url: "mailto:support@mitihar.com"   },
];

export default function AboutScreen() {
  const router = useRouter();

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>About</Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>
        {/* App identity */}
        <View style={s.appCard}>
          <View style={s.logoWrap}><Text style={s.logoEmoji}>🌿</Text></View>
          <Text style={s.appName}>Mitihar</Text>
          <Text style={s.appTagline}>Your AI-powered Indian diet companion</Text>
          <Text style={s.appVersion}>Version {APP_VERSION}</Text>
        </View>

        {/* Disclaimer */}
        <View style={s.disclaimerCard}>
          <Text style={s.disclaimerTitle}>Medical Disclaimer</Text>
          <Text style={s.disclaimerText}>
            Mitihar provides general dietary information and personalised meal plans created by certified
            dieticians. This app is not a substitute for professional medical advice, diagnosis, or
            treatment. Always seek the guidance of your physician or other qualified health provider
            with any questions you may have regarding a medical condition.
          </Text>
        </View>

        {/* Links */}
        <View style={s.linksCard}>
          {LINKS.map((link, i) => (
            <Pressable
              key={link.label}
              style={[s.linkRow, i < LINKS.length - 1 && s.linkBorder]}
              onPress={() => Linking.openURL(link.url)}
            >
              <Text style={s.linkLabel}>{link.label}</Text>
              <ExternalLink size={14} color="#9CA3AF" />
            </Pressable>
          ))}
        </View>

        <Text style={s.copyright}>© {new Date().getFullYear()} Mitihar. All rights reserved.</Text>
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root:            { flex: 1, backgroundColor: "#F9FAFB" },
  header:          { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:         { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  title:           { fontSize: 18, fontWeight: "600", color: "#111827" },
  scroll:          { padding: 20, gap: 16, alignItems: "center" },
  appCard:         { backgroundColor: "#fff", borderRadius: 16, borderWidth: 1, borderColor: "#E5E7EB", padding: 28, alignItems: "center", width: "100%" },
  logoWrap:        { width: 72, height: 72, borderRadius: 36, backgroundColor: "#F0FDF4", alignItems: "center", justifyContent: "center", marginBottom: 12 },
  logoEmoji:       { fontSize: 36 },
  appName:         { fontSize: 22, fontWeight: "700", color: "#111827" },
  appTagline:      { fontSize: 14, color: "#6B7280", marginTop: 4, textAlign: "center" },
  appVersion:      { fontSize: 12, color: "#9CA3AF", marginTop: 8 },
  disclaimerCard:  { backgroundColor: "#FFFBEB", borderRadius: 12, borderWidth: 1, borderColor: "#FDE68A", padding: 16, width: "100%" },
  disclaimerTitle: { fontSize: 13, fontWeight: "600", color: "#92400E", marginBottom: 8 },
  disclaimerText:  { fontSize: 13, color: "#78350F", lineHeight: 20 },
  linksCard:       { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", width: "100%", overflow: "hidden" },
  linkRow:         { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingHorizontal: 16, paddingVertical: 14 },
  linkBorder:      { borderBottomWidth: 1, borderBottomColor: "#F3F4F6" },
  linkLabel:       { fontSize: 14, color: "#374151" },
  copyright:       { fontSize: 12, color: "#9CA3AF" },
});
