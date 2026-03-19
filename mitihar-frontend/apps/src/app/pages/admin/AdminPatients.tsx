import React, { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Users, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
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
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(1);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce search
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setDebouncedSearch(search);
      setPage(1);
    }, 350);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [search]);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: aqk.patients(page, debouncedSearch),
    queryFn: () => adminApi.listPatients(page, debouncedSearch),
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
              {debouncedSearch ? 'No patients match your search' : 'No patients found'}
            </p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                {['Patient', 'Token 1', 'Days Left', 'User Type', 'Doctor ID', 'BMI', 'Subscription', 'Joined'].map(h => (
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
            Page {page} of {totalPages} &middot; {total} total
          </p>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="w-8 h-8 rounded border border-[#E5E7EB] flex items-center justify-center text-[#374151] hover:bg-[#F3F4F6] disabled:opacity-40">
              <ChevronLeft size={14} />
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              // Sliding window of 7 pages centered on current
              const half = 3;
              let start = Math.max(1, page - half);
              const end = Math.min(totalPages, start + 6);
              start = Math.max(1, end - 6);
              return start + i;
            }).filter(p => p >= 1 && p <= totalPages).map(p => (
              <button key={p} onClick={() => setPage(p)}
                className={`w-8 h-8 rounded border text-sm transition-colors ${
                  page === p ? 'bg-[#1E7C45] border-[#1E7C45] text-white' : 'border-[#E5E7EB] text-[#374151] hover:bg-[#F3F4F6]'
                }`}>{p}</button>
            ))}
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="w-8 h-8 rounded border border-[#E5E7EB] flex items-center justify-center text-[#374151] hover:bg-[#F3F4F6] disabled:opacity-40">
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
