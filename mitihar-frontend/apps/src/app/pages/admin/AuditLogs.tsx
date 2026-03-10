import React, { useState, useRef, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, ScrollText, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';
import { adminApi, AuditLogEntry } from '../../../lib/adminApi';
import { aqk } from '../../../lib/queryKeys';

const PAGE_SIZE = 50;

const roleColors: Record<string, string> = {
  admin:  'bg-[#DCFCE7] text-[#15803d]',
  doctor: 'bg-[#EFF6FF] text-[#2563EB]',
  system: 'bg-[#F3F4F6] text-[#6B7280]',
};

function formatTs(ts: string) {
  return new Date(ts).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', hour12: false,
  });
}

export function AuditLogs() {
  const [roleFilter, setRoleFilter]   = useState('');
  const [actionSearch, setActionSearch] = useState('');
  const [debouncedAction, setDebouncedAction] = useState('');
  const [page, setPage] = useState(1);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce action search
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setDebouncedAction(actionSearch);
      setPage(1);
    }, 400);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [actionSearch]);

  const queryParams = {
    page,
    ...(roleFilter    ? { actor_role: roleFilter }    : {}),
    ...(debouncedAction ? { action: debouncedAction } : {}),
  };

  const { data, isLoading, isFetching } = useQuery({
    queryKey: aqk.auditLogs(queryParams),
    queryFn:  () => adminApi.getAuditLogs(queryParams),
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  });

  const logs      = data?.logs ?? [];
  const total     = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Audit Logs</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">
            {isLoading ? '…' : `${total.toLocaleString()} total events`}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        {/* Action search */}
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
          <input
            type="text"
            value={actionSearch}
            onChange={e => setActionSearch(e.target.value)}
            placeholder="Filter by action…"
            className="w-60 h-9 pl-9 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
          />
          {isFetching && !isLoading && (
            <Loader2 size={12} className="absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-[#9CA3AF]" />
          )}
        </div>

        {/* Role filter */}
        <div className="flex items-center border border-[#D1D5DB] rounded-md overflow-hidden">
          {[
            { value: '',       label: 'All' },
            { value: 'admin',  label: 'Admin' },
            { value: 'doctor', label: 'Doctor' },
            { value: 'system', label: 'System' },
          ].map(f => (
            <button
              key={f.value}
              onClick={() => { setRoleFilter(f.value); setPage(1); }}
              className={`h-9 px-3 text-xs font-medium transition-colors ${
                roleFilter === f.value ? 'bg-[#1E7C45] text-white' : 'text-[#6B7280] hover:bg-[#F3F4F6]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="py-16 flex justify-center">
            <Loader2 size={24} className="animate-spin text-[#1E7C45]" />
          </div>
        ) : logs.length === 0 ? (
          <div className="py-16 flex flex-col items-center">
            <ScrollText size={32} className="text-[#D1D5DB] mb-3" />
            <p className="text-base font-medium text-[#374151]">No logs found</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                {['Timestamp', 'Actor ID', 'Role', 'Action', 'Entity', 'Entity ID', 'IP Address'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(logs as AuditLogEntry[]).map(log => (
                <tr key={log.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="text-xs font-mono text-[#6B7280]">{formatTs(log.created_at)}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">{log.actor_id}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${
                      roleColors[log.actor_role] ?? 'bg-[#F3F4F6] text-[#6B7280]'
                    }`}>
                      {log.actor_role}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <code className="text-xs font-mono text-[#374151]">{log.action}</code>
                  </td>
                  <td className="px-4 py-3 text-sm text-[#6B7280]">{log.entity_type ?? '—'}</td>
                  <td className="px-4 py-3 text-sm text-[#9CA3AF] tabular-nums">{log.entity_id ?? '—'}</td>
                  <td className="px-4 py-3">
                    <code className="text-xs font-mono text-[#9CA3AF]">{log.ip_address ?? '—'}</code>
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
            Page {page} of {totalPages} &middot; {total.toLocaleString()} total
          </p>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="w-8 h-8 rounded border border-[#E5E7EB] flex items-center justify-center text-[#374151] hover:bg-[#F3F4F6] disabled:opacity-40">
              <ChevronLeft size={14} />
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              const half = 3;
              let start = Math.max(1, page - half);
              const end   = Math.min(totalPages, start + 6);
              start = Math.max(1, end - 6);
              return start + i;
            }).filter(n => n >= 1 && n <= totalPages).map(n => (
              <button key={n} onClick={() => setPage(n)}
                className={`w-8 h-8 rounded border text-sm transition-colors ${
                  page === n ? 'bg-[#1E7C45] border-[#1E7C45] text-white' : 'border-[#E5E7EB] text-[#374151] hover:bg-[#F3F4F6]'
                }`}>{n}</button>
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
