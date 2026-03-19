import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Search, ChevronLeft, ChevronRight, ArrowUpRight,
  UserX, Loader2, AlertCircle, RefreshCw, CheckCircle, Clock, Copy,
} from 'lucide-react';
import { doctorApi, PatientSummary, PendingRenewalItem } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';

// ── helpers ───────────────────────────────────────────────────────────────────
function daysLeft(expiry: string | null): number | null {
  if (!expiry) return null;
  return Math.ceil((new Date(expiry).getTime() - Date.now()) / 86_400_000);
}

function DaysLeftBadge({ expiry }: { expiry: string | null }) {
  const d = daysLeft(expiry);
  if (d === null) return <span className="text-sm text-[#9CA3AF]">—</span>;
  if (d <= 0)  return <span className="text-xs font-semibold text-[#DC2626] bg-[#FEF2F2] px-2 py-0.5 rounded-full">Expired</span>;
  if (d <= 4)  return <span className="text-xs font-semibold text-[#B45309] bg-[#FFFBEB] px-2 py-0.5 rounded-full">{d}d left ⚠️</span>;
  return <span className="text-xs font-semibold text-[#15803d] bg-[#DCFCE7] px-2 py-0.5 rounded-full">{d}d left</span>;
}

function Token1Badge({ active, token }: { active: boolean; token: string | null }) {
  const copy = () => {
    if (!token) return;
    navigator.clipboard.writeText(token).then(() => toast.success('Token 1 copied!'));
  };
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5">
        <p className="text-xs font-mono text-[#374151]">{token ?? '—'}</p>
        {token && (
          <button
            onClick={copy}
            title="Copy Token 1"
            className="p-0.5 rounded hover:bg-[#F3F4F6] text-[#9CA3AF] hover:text-[#1E7C45] transition-colors"
          >
            <Copy size={12} />
          </button>
        )}
      </div>
      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full w-fit ${active ? 'bg-[#DCFCE7] text-[#15803d]' : 'bg-[#F3F4F6] text-[#6B7280]'}`}>
        {active ? 'Active' : 'Inactive'}
      </span>
    </div>
  );
}

export function Patients() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(1);

  const handleSearch = useCallback((val: string) => {
    setSearch(val);
    setPage(1);
    clearTimeout((handleSearch as any)._t);
    (handleSearch as any)._t = setTimeout(() => setDebouncedSearch(val), 350);
  }, []);

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: qk.patients(page, debouncedSearch),
    queryFn: () => doctorApi.listPatients(page, debouncedSearch),
    placeholderData: (prev) => prev,
  });

  const { data: pendingRenewals = [] } = useQuery({
    queryKey: qk.pendingRenewals(),
    queryFn: doctorApi.getPendingRenewals,
    staleTime: 30_000,
  });

  const approveMut = useMutation({
    mutationFn: (patientId: number) => doctorApi.approveRenewal(patientId),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: qk.patients(page, debouncedSearch) });
      queryClient.invalidateQueries({ queryKey: qk.pendingRenewals() });
      toast.success('Renewal approved');
    },
    onError: () => toast.error('Failed to approve renewal'),
  });

  const approveAllMut = useMutation({
    mutationFn: doctorApi.approveAllRenewals,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: qk.patients(page, debouncedSearch) });
      queryClient.invalidateQueries({ queryKey: qk.pendingRenewals() });
      toast.success(`${data.approved_count} renewals approved`);
    },
    onError: () => toast.error('Failed to approve renewals'),
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / 10)) : 1;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Patients</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">
            {data ? `${data.total} total patients` : 'Loading…'}
          </p>
        </div>
      </div>

      {/* Expiry warning banner */}
      {pendingRenewals.length > 0 && (
        <div className="mb-4 flex items-center justify-between gap-3 px-4 py-3 rounded-lg bg-[#FFFBEB] border border-[#FDE68A]">
          <div className="flex items-center gap-2">
            <Clock size={15} className="text-[#B45309]" />
            <p className="text-sm text-[#B45309] font-medium">
              {pendingRenewals.length} patient{pendingRenewals.length > 1 ? 's' : ''} requesting renewal
            </p>
          </div>
          <button
            onClick={() => approveAllMut.mutate()}
            disabled={approveAllMut.isPending}
            className="flex items-center gap-1.5 h-8 px-3 rounded-md bg-[#1E7C45] text-white text-xs hover:bg-[#166534] disabled:opacity-50"
          >
            {approveAllMut.isPending
              ? <Loader2 size={12} className="animate-spin" />
              : <CheckCircle size={12} />}
            Approve All
          </button>
        </div>
      )}

      {/* Search */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-xs">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
          <input
            type="text" value={search} onChange={e => handleSearch(e.target.value)}
            placeholder="Search by name or email…"
            className="w-full h-9 pl-9 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
          />
        </div>
        {isFetching && !isLoading && <Loader2 size={16} className="animate-spin text-[#1E7C45]" />}
      </div>

      {/* Table */}
      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-x-auto">
        {isLoading ? (
          <div className="py-20 flex justify-center"><Loader2 size={28} className="animate-spin text-[#1E7C45]" /></div>
        ) : isError ? (
          <div className="py-20 flex flex-col items-center"><AlertCircle size={32} className="text-[#DC2626] mb-3" /><p className="text-sm text-[#374151]">Could not load patients</p></div>
        ) : data?.patients.length === 0 ? (
          <div className="py-16 flex flex-col items-center">
            <UserX size={28} className="text-[#D1D5DB] mb-2" />
            <p className="text-sm text-[#9CA3AF]">No patients found</p>
          </div>
        ) : (
          <table className="w-full min-w-[900px]">
            <thead>
              <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                {['Patient', 'Token 1', 'Token 2 / Last Visit', 'Days Left', 'Visits (Month)', 'Renewal', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data?.patients.map((p: PatientSummary) => (
                <PatientRow
                  key={p.id} patient={p}
                  onView={() => navigate(`/doctor/patients/${p.id}`)}
                  onApprove={() => approveMut.mutate(p.id)}
                  approving={approveMut.isPending && approveMut.variables === p.id}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {data && data.total > 10 && (
        <div className="flex items-center justify-between mt-4 px-1">
          <p className="text-sm text-[#6B7280]">
            Showing {(page - 1) * 10 + 1}–{Math.min(page * 10, data.total)} of {data.total}
          </p>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="w-8 h-8 rounded border border-[#E5E7EB] flex items-center justify-center hover:bg-[#F3F4F6] disabled:opacity-40">
              <ChevronLeft size={14} />
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const p = totalPages <= 5 ? i + 1 : Math.max(1, page - 2) + i;
              if (p > totalPages) return null;
              return (
                <button key={p} onClick={() => setPage(p)}
                  className={`w-8 h-8 rounded border text-sm ${page === p ? 'bg-[#1E7C45] border-[#1E7C45] text-white' : 'border-[#E5E7EB] text-[#374151] hover:bg-[#F3F4F6]'}`}>
                  {p}
                </button>
              );
            })}
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="w-8 h-8 rounded border border-[#E5E7EB] flex items-center justify-center hover:bg-[#F3F4F6] disabled:opacity-40">
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Patient row ───────────────────────────────────────────────────────────────
function PatientRow({
  patient, onView, onApprove, approving,
}: {
  patient: PatientSummary;
  onView: () => void;
  onApprove: () => void;
  approving: boolean;
}) {
  return (
    <tr className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
      <td className="px-4 py-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-[#F0FDF4] flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-semibold text-[#1E7C45]">
              {patient.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
            </span>
          </div>
          <div>
            <p className="text-sm font-medium text-[#111827]">{patient.name}</p>
            <p className="text-xs text-[#6B7280]">{patient.email}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-4">
        <Token1Badge active={patient.token_1_active} token={patient.token_1} />
      </td>
      <td className="px-4 py-4 text-xs text-[#6B7280]">
        —
      </td>
      <td className="px-4 py-4">
        <DaysLeftBadge expiry={patient.token_1_expiry} />
      </td>
      <td className="px-4 py-4 text-sm text-[#374151] tabular-nums">—</td>
      <td className="px-4 py-4">
        {patient.renewal_requested ? (
          <button onClick={onApprove} disabled={approving}
            className="flex items-center gap-1.5 h-7 px-2.5 rounded-md bg-[#1E7C45] text-white text-xs hover:bg-[#166534] disabled:opacity-50">
            {approving ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />}
            Approve
          </button>
        ) : (
          <span className="text-xs text-[#9CA3AF]">
            {patient.expiring_soon ? '⚠️ Expiring' : '—'}
          </span>
        )}
      </td>
      <td className="px-4 py-4">
        <button onClick={onView}
          className="flex items-center gap-1 h-7 px-2.5 rounded border border-[#D1D5DB] bg-white text-xs text-[#374151] hover:border-[#1E7C45] hover:text-[#1E7C45]">
          View <ArrowUpRight size={11} />
        </button>
      </td>
    </tr>
  );
}
