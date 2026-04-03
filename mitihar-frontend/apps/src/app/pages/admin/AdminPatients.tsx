import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Search, Users, Loader2, ChevronLeft, ChevronRight, Trash2 } from 'lucide-react';
import { adminApi, AdminPatientView } from '../../../lib/adminApi';
import { aqk } from '../../../lib/queryKeys';

const PAGE_SIZE = 15;

function subBadge(status: string) {
  const map: Record<string, string> = {
    active: 'bg-[#DCFCE7] text-[#15803d]',
    inactive: 'bg-[#F3F4F6] text-[#6B7280]',
    expired: 'bg-[#FEF3C7] text-[#B45309]',
  };
  return map[status] ?? 'bg-[#F3F4F6] text-[#6B7280]';
}

function daysLeftLabel(expiry: string | null | undefined): React.ReactNode {
  if (!expiry) return <span className="text-[#9CA3AF]">—</span>;
  const d = Math.ceil((new Date(expiry).getTime() - Date.now()) / 86_400_000);
  if (d <= 0)  return <span className="text-xs font-semibold text-[#DC2626]">Expired</span>;
  if (d <= 4)  return <span className="text-xs font-semibold text-[#B45309]">{d}d ⚠️</span>;
  return <span className="text-xs text-[#15803d]">{d}d</span>;
}

export function AdminPatients() {
  // Live search input value (controlled) — kept separate from apiQuery
  // so the input stays responsive while debounce is pending.
  const [search, setSearch] = useState('');

  // Single state object that drives the API call.
  // Both the debounced search term and page are reset together
  // so they can be updated in one setState instead of two.
  const [apiQuery, setApiQuery] = useState({ search: '', page: 1 });

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Confirmation dialog state — holds the patient to be erased, or null when closed
  const [confirmPatient, setConfirmPatient] = useState<{ id: number; name: string } | null>(null);

  const queryClient = useQueryClient();

  // Erase mutation — calls DELETE /admin/patients/{id}
  // On success: close dialog, invalidate all patient pages so table refreshes
  const eraseMutation = useMutation({
    mutationFn: (id: number) => adminApi.erasePatient(id),
    onSuccess: () => {
      setConfirmPatient(null);
      queryClient.invalidateQueries({ queryKey: ['admin', 'patients'] });
      queryClient.invalidateQueries({ queryKey: aqk.stats() });
    },
  });

  // Debounce: one setState call updates both search term and page together
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setApiQuery({ search, page: 1 });
    }, 350);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [search]);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: aqk.patients(apiQuery.page, apiQuery.search),
    queryFn: () => adminApi.listPatients(apiQuery.page, apiQuery.search),
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  });

  const patients = data?.patients ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Patients</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">
            {isLoading ? '…' : `${total} total patients across platform`}
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative w-72 mb-4">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search by name or email..."
          className="w-full h-9 pl-9 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
        />
        {isFetching && !isLoading && (
          <Loader2 size={13} className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-[#9CA3AF]" />
        )}
      </div>

      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="py-16 flex justify-center">
            <Loader2 size={24} className="animate-spin text-[#1E7C45]" />
          </div>
        ) : patients.length === 0 ? (
          <div className="py-16 flex flex-col items-center">
            <Users size={32} className="text-[#D1D5DB] mb-3" />
            <p className="text-base font-medium text-[#374151]">
              {apiQuery.search ? 'No patients match your search' : 'No patients found'}
            </p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                {['Patient', 'Token 1', 'Days Left', 'User Type', 'Doctor ID', 'BMI', 'Subscription', 'Joined', 'Actions'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(patients as AdminPatientView[]).map(p => (
                <tr key={p.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-[#F0FDF4] flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-semibold text-[#1E7C45]">
                          {p.name.split(' ').map((w: string) => w[0]).join('').slice(0, 2).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#111827]">{p.name}</p>
                        <p className="text-xs text-[#6B7280]">{p.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div>
                      <p className="text-xs font-mono text-[#374151]">{(p as any).token_1 ?? '—'}</p>
                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${(p as any).token_1_active ? 'bg-[#DCFCE7] text-[#15803d]' : 'bg-[#F3F4F6] text-[#6B7280]'}`}>
                        {(p as any).token_1_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4">{daysLeftLabel((p as any).token_1_expiry)}</td>
                  <td className="px-4 py-4">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${
                      p.user_type === 'doctor_assigned'
                        ? 'bg-[#EFF6FF] text-[#2563EB]'
                        : 'bg-[#F3F4F6] text-[#6B7280]'
                    }`}>
                      {p.user_type === 'doctor_assigned' ? 'Doctor-Assigned' : 'Standalone'}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-sm text-[#374151] tabular-nums">
                    {p.doctor_id ?? <span className="text-[#9CA3AF]">—</span>}
                  </td>
                  <td className="px-4 py-4 text-sm text-[#374151] tabular-nums">
                    {p.bmi != null ? p.bmi.toFixed(1) : <span className="text-[#9CA3AF]">—</span>}
                  </td>
                  <td className="px-4 py-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${subBadge(p.subscription_status)}`}>
                      {p.subscription_status}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-xs text-[#9CA3AF] tabular-nums whitespace-nowrap">
                    {new Date(p.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </td>
                  {/* Actions — erase patient (DPDP compliance anonymise) */}
                  <td className="px-4 py-4">
                    <button
                      onClick={() => setConfirmPatient({ id: p.id, name: p.name })}
                      title="Erase patient data"
                      className="w-7 h-7 rounded flex items-center justify-center text-[#9CA3AF] hover:text-[#DC2626] hover:bg-[#FEF2F2] transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between mt-4 px-1">
          <p className="text-sm text-[#6B7280]">
            Page {apiQuery.page} of {totalPages} &middot; {total} total
          </p>
          <div className="flex items-center gap-1">
            <button onClick={() => setApiQuery(q => ({ ...q, page: Math.max(1, q.page - 1) }))} disabled={apiQuery.page === 1}
              className="w-8 h-8 rounded border border-[#E5E7EB] flex items-center justify-center text-[#374151] hover:bg-[#F3F4F6] disabled:opacity-40">
              <ChevronLeft size={14} />
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              // Sliding window of 7 pages centered on current
              const half = 3;
              let start = Math.max(1, apiQuery.page - half);
              const end = Math.min(totalPages, start + 6);
              start = Math.max(1, end - 6);
              return start + i;
            }).filter(p => p >= 1 && p <= totalPages).map(p => (
              <button key={p} onClick={() => setApiQuery(q => ({ ...q, page: p }))}
                className={`w-8 h-8 rounded border text-sm transition-colors ${
                  apiQuery.page === p ? 'bg-[#1E7C45] border-[#1E7C45] text-white' : 'border-[#E5E7EB] text-[#374151] hover:bg-[#F3F4F6]'
                }`}>{p}</button>
            ))}
            <button onClick={() => setApiQuery(q => ({ ...q, page: Math.min(totalPages, q.page + 1) }))} disabled={apiQuery.page === totalPages}
              className="w-8 h-8 rounded border border-[#E5E7EB] flex items-center justify-center text-[#374151] hover:bg-[#F3F4F6] disabled:opacity-40">
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
      {/* ── Erase confirmation dialog ─────────────────────────────────────────
           What this does: anonymises PII and hard-deletes all associated
           records (meal logs, progress, notes, plans). The patient row is
           kept for aggregate stats but the email becomes erased_{id}@deleted.local
           so the same email CAN be re-registered. This is DPDP Act compliance.
        ────────────────────────────────────────────────────────────────────── */}
      {confirmPatient && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-[#FEF2F2] flex items-center justify-center flex-shrink-0">
                <Trash2 size={18} className="text-[#DC2626]" />
              </div>
              <div>
                <p className="text-base font-semibold text-[#111827]">Erase patient data?</p>
                <p className="text-sm text-[#6B7280]">This cannot be undone</p>
              </div>
            </div>

            <p className="text-sm text-[#374151] mb-1">
              You are about to erase all data for:
            </p>
            <p className="text-sm font-semibold text-[#111827] mb-4 truncate">
              {confirmPatient.name} <span className="text-[#9CA3AF] font-normal">(ID {confirmPatient.id})</span>
            </p>

            <ul className="text-xs text-[#6B7280] space-y-1 mb-6 list-disc list-inside">
              <li>Name and email will be anonymised</li>
              <li>All meal logs, progress and notes deleted</li>
              <li>Diet plans removed</li>
              <li>Original email freed for re-registration</li>
            </ul>

            {eraseMutation.isError && (
              <p className="text-xs text-[#DC2626] mb-3">
                Something went wrong. Please try again.
              </p>
            )}

            <div className="flex gap-3">
              <button
                onClick={() => { setConfirmPatient(null); eraseMutation.reset(); }}
                disabled={eraseMutation.isPending}
                className="flex-1 h-9 rounded-md border border-[#E5E7EB] text-sm text-[#374151] hover:bg-[#F9FAFB] transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={() => eraseMutation.mutate(confirmPatient.id)}
                disabled={eraseMutation.isPending}
                className="flex-1 h-9 rounded-md bg-[#DC2626] text-white text-sm font-medium hover:bg-[#B91C1C] transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {eraseMutation.isPending
                  ? <><span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> Erasing…</>
                  : 'Yes, erase data'
                }
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
