import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { Search, ChevronLeft, ChevronRight, ArrowUpRight, UserX, Loader2, AlertCircle } from 'lucide-react';
import { doctorApi, PatientSummary } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';
import { StatusBadge } from '../../components/ui/StatusBadge';

function calcAge(dob: string | null): string {
  if (!dob) return '—';
  const years = Math.floor(
    (Date.now() - new Date(dob).getTime()) / (1000 * 60 * 60 * 24 * 365.25)
  );
  return `${years}y`;
}

function subStatusToStatus(s: string): 'active' | 'inactive' | 'expired' | 'pending' {
  if (s === 'active') return 'active';
  if (s === 'expired') return 'expired';
  return 'inactive';
}

export function Patients() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [page, setPage] = useState(1);

  // Debounce search — avoid a query on every keystroke
  const handleSearch = useCallback((val: string) => {
    setSearch(val);
    setPage(1);
    clearTimeout((handleSearch as any)._t);
    (handleSearch as any)._t = setTimeout(() => setDebouncedSearch(val), 350);
  }, []);

  const { data, isLoading, isError, isFetching } = useQuery({
    queryKey: qk.patients(page, debouncedSearch),
    queryFn: () => doctorApi.listPatients(page, debouncedSearch),
    placeholderData: (prev) => prev,  // keepPreviousData equivalent in v5
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / 10)) : 1;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Patients</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">
            {data ? `${data.total} total patients` : 'Loading…'}
          </p>
        </div>
      </div>

      {/* Search bar */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-xs">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
          <input
            type="text"
            value={search}
            onChange={e => handleSearch(e.target.value)}
            placeholder="Search by name or email…"
            className="w-full h-9 pl-9 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
          />
        </div>
        {isFetching && !isLoading && (
          <Loader2 size={16} className="animate-spin text-[#1E7C45]" />
        )}
      </div>

      {/* Table */}
      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="py-20 flex justify-center">
            <Loader2 size={28} className="animate-spin text-[#1E7C45]" />
          </div>
        ) : isError ? (
          <div className="py-20 flex flex-col items-center text-center px-6">
            <AlertCircle size={32} className="text-[#DC2626] mb-3" />
            <p className="text-base font-medium text-[#374151]">Could not load patients</p>
            <p className="text-sm text-[#6B7280] mt-1">Check your connection and try again</p>
          </div>
        ) : data && data.patients.length === 0 ? (
          <EmptyState onClear={() => { setSearch(''); setDebouncedSearch(''); }} />
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                {['Patient', 'Age / BMI', 'Diet Type', 'TDEE', 'Status', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data?.patients.map((patient: PatientSummary) => (
                <tr
                  key={patient.id}
                  className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors cursor-pointer"
                  onClick={() => navigate(`/doctor/patients/${patient.id}`)}
                >
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
                    <p className="text-sm text-[#374151] tabular-nums">
                      {calcAge(patient.date_of_birth)} · {patient.gender === 'M' ? 'M' : patient.gender === 'F' ? 'F' : patient.gender}
                    </p>
                    <p className="text-xs text-[#6B7280]">
                      {patient.bmi != null ? `BMI ${patient.bmi.toFixed(1)}` : 'BMI —'}
                    </p>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm text-[#374151]">{patient.user_type === 'doctor_assigned' ? 'Assigned' : 'Standalone'}</p>
                    <p className="text-xs text-[#6B7280]">{patient.meals_per_day} meals/day</p>
                  </td>
                  <td className="px-4 py-4">
                    <p className="text-sm text-[#374151] tabular-nums">
                      {patient.tdee != null ? `${Math.round(patient.tdee)} kcal` : '—'}
                    </p>
                  </td>
                  <td className="px-4 py-4">
                    <StatusBadge status={subStatusToStatus(patient.subscription_status)} />
                  </td>
                  <td className="px-4 py-4" onClick={e => e.stopPropagation()}>
                    <button
                      onClick={() => navigate(`/doctor/patients/${patient.id}`)}
                      className="flex items-center gap-1 h-7 px-2.5 rounded border border-[#D1D5DB] bg-white text-xs text-[#374151] hover:border-[#1E7C45] hover:text-[#1E7C45] transition-colors"
                    >
                      View <ArrowUpRight size={11} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {data && data.total > 10 && (
        <div className="flex items-center justify-between mt-4 px-1">
          <p className="text-sm text-[#6B7280]">
            Showing {(page - 1) * 10 + 1}–{Math.min(page * 10, data.total)} of {data.total} patients
          </p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="w-8 h-8 rounded border border-[#E5E7EB] flex items-center justify-center text-[#374151] hover:bg-[#F3F4F6] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft size={14} />
            </button>
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const p = totalPages <= 5 ? i + 1 : Math.max(1, page - 2) + i;
              if (p > totalPages) return null;
              return (
                <button
                  key={p}
                  onClick={() => setPage(p)}
                  className={`w-8 h-8 rounded border text-sm transition-colors ${
                    page === p
                      ? 'bg-[#1E7C45] border-[#1E7C45] text-white'
                      : 'border-[#E5E7EB] text-[#374151] hover:bg-[#F3F4F6]'
                  }`}
                >
                  {p}
                </button>
              );
            })}
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="w-8 h-8 rounded border border-[#E5E7EB] flex items-center justify-center text-[#374151] hover:bg-[#F3F4F6] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function EmptyState({ onClear }: { onClear: () => void }) {
  return (
    <div className="py-16 flex flex-col items-center justify-center text-center px-6">
      <div className="w-16 h-16 rounded-full bg-[#F3F4F6] flex items-center justify-center mb-4">
        <UserX size={28} className="text-[#9CA3AF]" />
      </div>
      <p className="text-base font-medium text-[#374151] mb-1">No patients found</p>
      <p className="text-sm text-[#6B7280] mb-4">Try adjusting your search</p>
      <button
        onClick={onClear}
        className="h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors"
      >
        Clear search
      </button>
    </div>
  );
}
