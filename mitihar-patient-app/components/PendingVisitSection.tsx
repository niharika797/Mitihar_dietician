// Doctor-flagged visits awaiting this patient's confirmation, inline on home.
//
// When a patient can't show Token 2 (phone forgotten or lost) the doctor flags
// the visit instead of recording it. Nothing is charged until the patient
// answers here — that confirmation IS the fraud control, so this card is the
// only place a pending charge is visible to them.
//
// Renders nothing when there is nothing pending, matching DoctorStatusBanner's
// return-null convention rather than showing an empty state on the dashboard.
import React from "react";
import { View, Text, Pressable, StyleSheet, ActivityIndicator } from "react-native";
import { Flag } from "lucide-react-native";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "../lib/queryKeys";
import { getPendingVisits, respondToPendingVisit } from "../services/profile";
import type { PendingVisit } from "../services/profile";
import { useToast } from "./shared";
import { getApiError } from "../lib/getApiError";

export default function PendingVisitSection() {
  const qc = useQueryClient();
  const { showToast } = useToast();

  const { data: pending, isLoading } = useQuery({
    queryKey: QUERY_KEYS.PENDING_VISITS,
    queryFn: getPendingVisits,
  });

  const respond = useMutation({
    mutationFn: ({ id, action }: { id: number; action: "approve" | "reject" }) =>
      respondToPendingVisit(id, action),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.PENDING_VISITS });
      // Approving can increment the visit counter, so the visit card is stale.
      qc.invalidateQueries({ queryKey: QUERY_KEYS.MY_VISIT });
      // Show the server's message — it is the one that knows whether the visit
      // was actually charged and at what rate.
      showToast(res.message, res.status === "approved" ? "success" : "info");
    },
    onError: (err) => showToast(getApiError(err), "error"),
  });

  // Self-hiding: no card at all while loading or when nothing is pending.
  if (isLoading || !pending || pending.length === 0) return null;

  return (
    <>
      <Text style={s.sectionLabel}>ACTION NEEDED</Text>
      {pending.map((v: PendingVisit) => {
        // Both buttons share one mutation, so scope the spinner to the row and
        // action actually in flight (same trick as find-doctor.tsx).
        const busy = respond.isPending && respond.variables?.id === v.id;
        return (
          <View key={v.id} style={s.card}>
            <View style={s.header}>
              <Flag size={16} color="#92400E" />
              <Text style={s.title}>Confirm your visit</Text>
            </View>

            <Text style={s.body}>
              {v.doctor_name} recorded a visit on{" "}
              {new Date(v.visit_date).toLocaleDateString("en-IN", {
                day: "numeric", month: "short", year: "numeric",
              })}
              . Confirm only if this visit actually happened.
            </Text>

            {v.doctor_note ? <Text style={s.note}>“{v.doctor_note}”</Text> : null}

            <View style={s.actions}>
              <Pressable
                onPress={() => respond.mutate({ id: v.id, action: "approve" })}
                disabled={busy}
                style={[s.approveBtn, busy && s.btnDisabled]}
              >
                {busy && respond.variables?.action === "approve"
                  ? <ActivityIndicator color="#fff" size="small" />
                  : <Text style={s.approveTxt}>Yes, I visited</Text>}
              </Pressable>

              <Pressable
                onPress={() => respond.mutate({ id: v.id, action: "reject" })}
                disabled={busy}
                style={[s.rejectBtn, busy && s.btnDisabled]}
              >
                {busy && respond.variables?.action === "reject"
                  ? <ActivityIndicator color="#374151" size="small" />
                  : <Text style={s.rejectTxt}>No, I didn't</Text>}
              </Pressable>
            </View>
          </View>
        );
      })}
    </>
  );
}

const s = StyleSheet.create({
  sectionLabel: {
    fontSize: 12, fontWeight: "600", color: "#6B7280",
    letterSpacing: 0.6, marginTop: 24, marginBottom: 10,
  },
  card: {
    backgroundColor: "#FFFBEB", borderWidth: 1, borderColor: "#FDE68A",
    borderRadius: 14, padding: 16, marginBottom: 10,
  },
  header: { flexDirection: "row", alignItems: "center", gap: 8, marginBottom: 8 },
  title: { fontSize: 15, fontWeight: "600", color: "#92400E" },
  body: { fontSize: 14, lineHeight: 20, color: "#374151" },
  note: {
    fontSize: 13, fontStyle: "italic", color: "#6B7280",
    marginTop: 8, paddingLeft: 10, borderLeftWidth: 2, borderLeftColor: "#FDE68A",
  },
  actions: { flexDirection: "row", gap: 10, marginTop: 14 },
  approveBtn: {
    flex: 1, height: 40, borderRadius: 20, backgroundColor: "#1E7C45",
    alignItems: "center", justifyContent: "center",
  },
  approveTxt: { fontSize: 14, fontWeight: "600", color: "#fff" },
  rejectBtn: {
    flex: 1, height: 40, borderRadius: 20, backgroundColor: "#fff",
    borderWidth: 1.5, borderColor: "#E5E7EB",
    alignItems: "center", justifyContent: "center",
  },
  rejectTxt: { fontSize: 14, fontWeight: "500", color: "#374151" },
  btnDisabled: { opacity: 0.6 },
});
