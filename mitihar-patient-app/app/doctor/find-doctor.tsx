import React, { useState, useEffect, useRef } from "react";
import {
  View, Text, ScrollView, Pressable, TextInput,
  StyleSheet, ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { ChevronLeft, MapPin, Search, Star, RefreshCcw } from "lucide-react-native";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { requestDoctor, listDoctors, PublicDoctor } from "../../services/profile";
import { useToast } from "../../components/shared";
import { QUERY_KEYS } from "../../lib/queryKeys";

export default function FindDoctorScreen() {
  const router = useRouter();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [requestedIds, setRequestedIds] = useState<Set<number>>(new Set());
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce search input — fire query 400ms after user stops typing
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedSearch(search), 400);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [search]);

  const { data: doctors = [], isLoading, isError, refetch, isFetching } = useQuery({
    queryKey: QUERY_KEYS.DOCTORS(debouncedSearch || undefined),
    queryFn: () => listDoctors(debouncedSearch || undefined),
    staleTime: 5 * 60 * 1000, // 5 minutes — doctor list doesn't change often
  });

  const requestMut = useMutation({
    mutationFn: (id: number) => requestDoctor(id),
    onSuccess: (_, id) => {
      setRequestedIds(prev => new Set([...prev, id]));
      qc.invalidateQueries({ queryKey: QUERY_KEYS.REQUEST_STATUS });
      showToast("Request sent! Your doctor will respond within 24h ⏳", "success");
      setTimeout(() => router.push("/doctor/connection-status"), 1200);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail ?? "Failed to send request";
      // 409 = already sent; treat gracefully
      if (err?.response?.status === 409) {
        showToast("You already sent a request to this doctor", "info");
      } else {
        showToast(msg, "error");
      }
    },
  });

  return (
    <View style={s.root}>
      {/* Header */}
      <View style={s.header}>
        <Pressable onPress={() => router.back()} style={s.backBtn} hitSlop={8}>
          <ChevronLeft size={20} color="#374151" />
        </Pressable>
        <Text style={s.title}>Find a Doctor</Text>
        <Pressable onPress={() => refetch()} hitSlop={8} style={s.refreshBtn}>
          {isFetching
            ? <ActivityIndicator size="small" color="#1E7C45" />
            : <RefreshCcw size={18} color="#6B7280" />}
        </Pressable>
      </View>

      {/* Search */}
      <View style={s.searchWrap}>
        <Search size={16} color="#9CA3AF" style={s.searchIcon} />
        <TextInput
          style={s.searchInput}
          value={search}
          onChangeText={setSearch}
          placeholder="Search by name, specialty, city..."
          placeholderTextColor="#9CA3AF"
          autoCapitalize="none"
          returnKeyType="search"
        />
        {search.length > 0 && (
          <Pressable onPress={() => setSearch("")} hitSlop={8} style={s.clearBtn}>
            <Text style={s.clearText}>✕</Text>
          </Pressable>
        )}
      </View>

      {/* Status row */}
      {!isLoading && !isError && (
        <Text style={s.countText}>
          {doctors.length === 0
            ? "No doctors found"
            : `${doctors.length} doctor${doctors.length === 1 ? "" : "s"} found`}
        </Text>
      )}

      {/* Body */}
      {isLoading ? (
        <View style={s.center}>
          <ActivityIndicator size="large" color="#1E7C45" />
          <Text style={s.loadingText}>Finding doctors near you…</Text>
        </View>
      ) : isError ? (
        <View style={s.center}>
          <Text style={s.errorEmoji}>⚠️</Text>
          <Text style={s.errorText}>Could not load doctors</Text>
          <Pressable onPress={() => refetch()} style={s.retryBtn}>
            <Text style={s.retryText}>Retry</Text>
          </Pressable>
        </View>
      ) : doctors.length === 0 ? (
        <View style={s.center}>
          <Text style={s.errorEmoji}>🔍</Text>
          <Text style={s.errorText}>
            {search ? `No results for "${search}"` : "No doctors available right now"}
          </Text>
        </View>
      ) : (
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>
          {doctors.map(doc => (
            <DoctorCard
              key={doc.id}
              doc={doc}
              requested={requestedIds.has(doc.id)}
              loading={requestMut.isPending && requestMut.variables === doc.id}
              onRequest={() => requestMut.mutate(doc.id)}
            />
          ))}
        </ScrollView>
      )}
    </View>
  );
}

// ─── Doctor Card Component ──────────────────────────────────────────────────

interface CardProps {
  doc: PublicDoctor;
  requested: boolean;
  loading: boolean;
  onRequest: () => void;
}

function DoctorCard({ doc, requested, loading, onRequest }: CardProps) {
  const unavailable = !doc.is_accepting;
  const fee = null; // Fee is an internal business detail — not shown to patients
  const exp = doc.experience_years ? `${doc.experience_years} yrs exp` : null;
  const location = [doc.city, doc.state].filter(Boolean).join(", ");
  const rating = doc.rating ? Number(doc.rating).toFixed(1) : null;

  return (
    <View style={s.card}>
      <View style={s.cardTop}>
        <View style={s.avatar}><Text style={s.avatarEmoji}>👨‍⚕️</Text></View>
        <View style={s.cardInfo}>
          {/* Name row */}
          <View style={s.nameRow}>
            <View style={{ flex: 1 }}>
              <Text style={s.docName}>{doc.name}</Text>
              {doc.specialization && <Text style={s.docSpec}>{doc.specialization}</Text>}
            </View>
            {unavailable && (
              <View style={s.unavailBadge}><Text style={s.unavailText}>Unavailable</Text></View>
            )}
          </View>

          {/* Location */}
          {(location || doc.clinic_name) && (
            <View style={s.locRow}>
              <MapPin size={11} color="#9CA3AF" />
              <Text style={s.locText} numberOfLines={1}>
                {[location, doc.clinic_name].filter(Boolean).join(" · ")}
              </Text>
            </View>
          )}

          {/* Meta: rating · exp · fee */}
          <View style={s.metaRow}>
            {rating && (
              <>
                <View style={s.ratingRow}>
                  <Star size={12} color="#F59E0B" fill="#F59E0B" />
                  <Text style={s.rating}>{rating}</Text>
                  {doc.review_count > 0 && (
                    <Text style={s.reviews}>({doc.review_count})</Text>
                  )}
                </View>
                <Text style={s.dot}>·</Text>
              </>
            )}
            {exp && <><Text style={s.meta}>{exp}</Text><Text style={s.dot}>·</Text></>}
            {fee && <Text style={s.fee}>{fee}</Text>}
          </View>

          {/* CTA button */}
          <Pressable
            onPress={onRequest}
            disabled={unavailable || requested || loading}
            style={[s.reqBtn, (unavailable || requested) && s.reqBtnDisabled]}
          >
            {loading
              ? <ActivityIndicator color="#fff" size="small" />
              : <Text style={[s.reqBtnText, (unavailable || requested) && s.reqBtnTextDisabled]}>
                  {requested ? "Request Sent ✓" : unavailable ? "Not Available" : "Send Request"}
                </Text>}
          </Pressable>
        </View>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  root:          { flex: 1, backgroundColor: "#F9FAFB" },
  header:        { flexDirection: "row", alignItems: "center", justifyContent: "space-between", padding: 16, backgroundColor: "#fff", borderBottomWidth: 1, borderBottomColor: "#E5E7EB" },
  backBtn:       { width: 36, height: 36, borderRadius: 18, backgroundColor: "#F3F4F6", alignItems: "center", justifyContent: "center" },
  refreshBtn:    { width: 36, height: 36, alignItems: "center", justifyContent: "center" },
  title:         { fontSize: 18, fontWeight: "600", color: "#111827" },
  searchWrap:    { flexDirection: "row", alignItems: "center", margin: 16, borderWidth: 1.5, borderColor: "#E5E7EB", borderRadius: 12, backgroundColor: "#fff", paddingHorizontal: 14 },
  searchIcon:    { marginRight: 8 },
  searchInput:   { flex: 1, height: 44, fontSize: 14, color: "#111827" },
  clearBtn:      { padding: 4 },
  clearText:     { fontSize: 14, color: "#9CA3AF" },
  countText:     { fontSize: 12, color: "#6B7280", marginHorizontal: 20, marginBottom: 8 },
  scroll:        { paddingHorizontal: 16, paddingBottom: 40 },
  center:        { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, paddingBottom: 80 },
  loadingText:   { fontSize: 14, color: "#6B7280" },
  errorEmoji:    { fontSize: 40 },
  errorText:     { fontSize: 15, color: "#374151", textAlign: "center" },
  retryBtn:      { paddingHorizontal: 24, paddingVertical: 10, backgroundColor: "#1E7C45", borderRadius: 99 },
  retryText:     { color: "#fff", fontWeight: "600", fontSize: 14 },
  // Card
  card:          { backgroundColor: "#fff", borderRadius: 12, borderWidth: 1, borderColor: "#E5E7EB", padding: 16, marginBottom: 12 },
  cardTop:       { flexDirection: "row", gap: 14 },
  avatar:        { width: 52, height: 52, borderRadius: 26, backgroundColor: "#F0FDF4", alignItems: "center", justifyContent: "center", flexShrink: 0 },
  avatarEmoji:   { fontSize: 24 },
  cardInfo:      { flex: 1, gap: 6 },
  nameRow:       { flexDirection: "row", alignItems: "flex-start" },
  docName:       { fontSize: 15, fontWeight: "600", color: "#111827" },
  docSpec:       { fontSize: 12, color: "#6B7280" },
  unavailBadge:  { backgroundColor: "#F3F4F6", borderRadius: 99, paddingHorizontal: 8, paddingVertical: 3 },
  unavailText:   { fontSize: 11, color: "#6B7280" },
  locRow:        { flexDirection: "row", alignItems: "center", gap: 4 },
  locText:       { fontSize: 12, color: "#6B7280", flex: 1 },
  metaRow:       { flexDirection: "row", alignItems: "center", gap: 6, flexWrap: "wrap" },
  ratingRow:     { flexDirection: "row", alignItems: "center", gap: 3 },
  rating:        { fontSize: 12, fontWeight: "600", color: "#374151" },
  reviews:       { fontSize: 11, color: "#9CA3AF" },
  dot:           { fontSize: 12, color: "#9CA3AF" },
  meta:          { fontSize: 12, color: "#374151" },
  fee:           { fontSize: 12, fontWeight: "600", color: "#1E7C45" },
  reqBtn:        { height: 38, borderRadius: 99, backgroundColor: "#1E7C45", alignItems: "center", justifyContent: "center", marginTop: 4 },
  reqBtnDisabled:{ backgroundColor: "#F3F4F6" },
  reqBtnText:    { fontSize: 13, fontWeight: "600", color: "#fff" },
  reqBtnTextDisabled: { color: "#9CA3AF" },
});
