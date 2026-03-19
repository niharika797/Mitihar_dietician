/**
 * queryKeys.ts
 * Centralized TanStack Query key factory for the Doctor Dashboard.
 * Keep all cache keys here so invalidation is always consistent.
 */

// ── Admin query keys ─────────────────────────────────────────────────────────
export const aqk = {
  stats:          () => ['admin', 'stats'] as const,
  doctors:        () => ['admin', 'doctors'] as const,
  patients:       (page: number, search: string) => ['admin', 'patients', page, search] as const,
  food:           (params: object) => ['admin', 'food', params] as const,
  pendingFood:    () => ['admin', 'food', 'pending'] as const,
  billing:        () => ['admin', 'billing'] as const,
  codes:          (doctorId?: number) => ['admin', 'codes', doctorId ?? 'all'] as const,
  auditLogs:      (params: object) => ['admin', 'audit-logs', params] as const,
  consultations:  () => ['admin', 'consultations'] as const,
  annualStats:    () => ['admin', 'consultations', 'annual'] as const,
  renewals:       () => ['admin', 'renewals'] as const,
};

// ── Doctor query keys ─────────────────────────────────────────────────────────
export const qk = {
  dashboard:       () => ['doctor', 'dashboard'] as const,
  patients:        (page: number, search: string) => ['doctor', 'patients', page, search] as const,
  patient:         (id: number) => ['doctor', 'patient', id] as const,
  patientPlan:     (id: number) => ['doctor', 'patient', id, 'plan'] as const,
  patientLogs:     (id: number, days: number) => ['doctor', 'patient', id, 'logs', days] as const,
  patientNotes:    (id: number) => ['doctor', 'patient', id, 'notes'] as const,
  patientVisits:   (id: number) => ['doctor', 'patient', id, 'visits'] as const,
  pendingRenewals: () => ['doctor', 'pending-renewals'] as const,
  requests:        () => ['doctor', 'requests'] as const,
  codes:           () => ['doctor', 'codes'] as const,
  recipes:         (params: object) => ['doctor', 'recipes', params] as const,
};
