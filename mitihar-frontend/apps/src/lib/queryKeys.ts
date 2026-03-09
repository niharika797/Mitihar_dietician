/**
 * queryKeys.ts
 * Centralized TanStack Query key factory for the Doctor Dashboard.
 * Keep all cache keys here so invalidation is always consistent.
 */

export const qk = {
  dashboard:    () => ['doctor', 'dashboard'] as const,
  patients:     (page: number, search: string) => ['doctor', 'patients', page, search] as const,
  patient:      (id: number) => ['doctor', 'patient', id] as const,
  patientPlan:  (id: number) => ['doctor', 'patient', id, 'plan'] as const,
  patientLogs:  (id: number, days: number) => ['doctor', 'patient', id, 'logs', days] as const,
  patientNotes: (id: number) => ['doctor', 'patient', id, 'notes'] as const,
  requests:     () => ['doctor', 'requests'] as const,
  codes:        () => ['doctor', 'codes'] as const,
  recipes:      (params: object) => ['doctor', 'recipes', params] as const,
};
