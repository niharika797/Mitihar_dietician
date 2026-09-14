import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Search, ChevronLeft, ChevronRight, ArrowUpRight,
  UserX, Loader2, AlertCircle, RefreshCw, CheckCircle, Clock, Copy,
} from 'lucide-react';
import { doctorApi, PatientSummary, PendingRenewalItem, PendingApproval } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';

// ── helpers ───────────────────────────────────────────────────────────────────
function daysLeft(expiry: string | null): number | null {
  if (!expiry) return null;
  return Math.ceil((new Date(expiry).getTime() - Date.now()) / 86_400_000);
}

function DaysLeftBadge({ expiry }: { expiry: string | null }) {
  const d = daysLeft(expiry);
  if (d === null) return <span className="text-sm text-muted-foreground">—</span>;
  if (d <= 0)  return <span className="text-xs font-semibold text-destructive bg-red-50 px-2 py-0.5 rounded-full">Expired</span>;
  if (d <= 4)  return <span className="text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full">{d}d left ⚠️</span>;
  return <span className="text-xs font-semibold text-brand-700 bg-brand-100 px-2 py-0.5 rounded-full">{d}d left</span>;
}

function Token1Badge({ active, token }: { active: boolean; token: string | null }) {
  const copy = () => {
    if (!token) return;
    navigator.clipboard.writeText(token).then(() => toast.success('Token 1 copied!'));
  };
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5">
        <p className="text-xs font-mono text-secondary-foreground">{token ?? '—'}</p>
        {token && (
          <button
            onClick={copy}
            title="Copy Token 1"
            className="p-0.5 rounded hover:bg-muted text-muted-foreground hover:text-primary transition-colors"
          >
            <Copy size={14} />
          </button>
        )}
      </div>
      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full w-fit ${active ? 'bg-brand-100 text-brand-700' : 'bg-secondary text-muted-foreground'}`}>
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

  const { data: pendingApprovalsData } = useQuery({
    queryKey: qk.pendingApprovals(),
    queryFn: doctorApi.getPendingApprovals,
    staleTime: 30_000,
  });
  const pendingApprovalIds = new Set(
    (pendingApprovalsData?.pending ?? []).map((p: PendingApproval) => p.patient_id),
  );

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
          <h1 data-tour="tour-patients" className="text-2xl font-semibold text-foreground tracking-tight">Patients</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {data ? `${data.total} total patients` : 'Loading…'}
          </p>
        </div>
      </div>

      {/* Expiry warning banner */}
      {pendingRenewals.length > 0 && (
        <div className="mb-4 flex items-center justify-between gap-3 px-4 py-3 rounded-lg bg-amber-50 border border-amber-500/30">
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-amber-700" />
            <p className="text-sm text-amber-700 font-medium">
              {pendingRenewals.length} patient{pendingRenewals.length > 1 ? 's' : ''} requesting renewal
            </p>
          </div>
          <Button variant="primary" size="sm" onClick={() => approveAllMut.mutate()} disabled={approveAllMut.isPending}>
            {approveAllMut.isPending
              ? <Loader2 size={14} className="animate-spin" />
              : <CheckCircle size={14} />}
            Approve All
          </Button>
        </div>
      )}

      {/* Search */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-xs">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text" value={search} onChange={e => handleSearch(e.target.value)}
            placeholder="Search by name or email…"
            className="w-full h-9 pl-9 pr-3 rounded-md border border-border bg-input-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        {isFetching && !isLoading && <Loader2 size={16} className="animate-spin text-primary" />}
      </div>

      {/* Table */}
      <Card className="overflow-x-auto">
        {isLoading ? (
          <div className="py-20 flex justify-center"><Loader2 size={20} className="animate-spin text-primary" /></div>
        ) : isError ? (
          <div className="py-20 flex flex-col items-center"><AlertCircle size={20} className="text-destructive mb-3" /><p className="text-sm text-secondary-foreground">Could not load patients</p></div>
        ) : data?.patients.length === 0 ? (
          <div className="py-16 flex flex-col items-center">
            <UserX size={20} className="text-slate-300 mb-2" />
            <p className="text-sm text-muted-foreground">No patients found</p>
          </div>
        ) : (
          <table className="w-full min-w-[900px]">
            <thead>
              <tr className="bg-input-background border-b border-border">
                {['Patient', 'Token 1', 'Token 2 / Last Visit', 'Days Left', 'Visits (Month)', 'Renewal', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground whitespace-nowrap">{h}</th>
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
                  hasPendingApproval={pendingApprovalIds.has(p.id)}
                />
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {/* Pagination */}
      {data && data.total > 10 && (
        <div className="flex items-center justify-between mt-4 px-1">
          <p className="text-sm text-muted-foreground">
            Showing {(page - 1) * 10 + 1}–{Math.min(page * 10, data.total)} of {data.total}
          </p>
          <div className="flex items-center gap-1">
            <Button variant="outline" size="sm" className="w-8 h-8 p-0" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
              <ChevronLeft size={14} />
            </Button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const p = totalPages <= 5 ? i + 1 : Math.max(1, page - 2) + i;
              if (p > totalPages) return null;
              return (
                <Button
                  key={p}
                  variant={page === p ? 'primary' : 'outline'}
                  size="sm"
                  className="w-8 h-8 p-0"
                  onClick={() => setPage(p)}
                >
                  {p}
                </Button>
              );
            })}
            <Button variant="outline" size="sm" className="w-8 h-8 p-0" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
              <ChevronRight size={14} />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Patient row ───────────────────────────────────────────────────────────────
function PatientRow({
  patient, onView, onApprove, approving, hasPendingApproval,
}: {
  patient: PatientSummary;
  onView: () => void;
  onApprove: () => void;
  approving: boolean;
  hasPendingApproval: boolean;
}) {
  return (
    <tr className="border-b border-border last:border-0 hover:bg-input-background transition-colors">
      <td className="px-4 py-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-brand-50 flex items-center justify-center flex-shrink-0">
            <span className="text-xs font-semibold text-primary">
              {patient.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium text-foreground">{patient.name}</p>
              {hasPendingApproval && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-50 border border-amber-500/30 text-amber-700 font-medium whitespace-nowrap">
                  Plan pending
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground">{patient.email}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-4">
        <Token1Badge active={patient.token_1_active} token={patient.token_1} />
      </td>
      <td className="px-4 py-4 text-xs text-muted-foreground">
        —
      </td>
      <td className="px-4 py-4">
        <DaysLeftBadge expiry={patient.token_1_expiry} />
      </td>
      <td className="px-4 py-4 text-sm text-secondary-foreground tabular-nums">—</td>
      <td className="px-4 py-4">
        {patient.renewal_requested ? (
          <Button variant="primary" size="sm" onClick={onApprove} disabled={approving}>
            {approving ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Approve
          </Button>
        ) : (
          <span className="text-xs text-muted-foreground">
            {patient.expiring_soon ? '⚠️ Expiring' : '—'}
          </span>
        )}
      </td>
      <td className="px-4 py-4">
        <Button variant="outline" size="sm" onClick={onView}>
          View <ArrowUpRight size={14} />
        </Button>
      </td>
    </tr>
  );
}
