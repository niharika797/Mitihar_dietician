import React, { useState } from 'react';
import { Search, ScrollText } from 'lucide-react';
import { auditLogs } from '../../data/mockData';

export function AuditLogs() {
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');

  const filtered = auditLogs.filter(log => {
    const matchSearch = log.action.toLowerCase().includes(search.toLowerCase()) ||
      log.actor.toLowerCase().includes(search.toLowerCase()) ||
      log.target.toLowerCase().includes(search.toLowerCase());
    const matchRole = roleFilter === 'all' || log.actorRole === roleFilter;
    return matchSearch && matchRole;
  });

  const formatTimestamp = (ts: string) => {
    const d = new Date(ts);
    return d.toLocaleString('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: false
    });
  };

  const roleColors: Record<string, string> = {
    admin: 'bg-[#DCFCE7] text-[#15803d]',
    doctor: 'bg-[#EFF6FF] text-[#2563EB]',
    system: 'bg-[#F3F4F6] text-[#6B7280]',
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Audit Logs</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">All platform actions and events</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search logs..."
            className="w-64 h-9 pl-9 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
          />
        </div>
        <div className="flex items-center gap-1 border border-[#D1D5DB] rounded-md overflow-hidden">
          {[
            { value: 'all', label: 'All' },
            { value: 'admin', label: 'Admin' },
            { value: 'doctor', label: 'Doctor' },
            { value: 'system', label: 'System' },
          ].map(f => (
            <button
              key={f.value}
              onClick={() => setRoleFilter(f.value)}
              className={`h-9 px-3 text-xs font-medium transition-colors ${
                roleFilter === f.value ? 'bg-[#1E7C45] text-white' : 'text-[#6B7280] hover:bg-[#F3F4F6]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
        {filtered.length === 0 ? (
          <div className="py-16 flex flex-col items-center">
            <ScrollText size={32} className="text-[#D1D5DB] mb-3" />
            <p className="text-base font-medium text-[#374151]">No logs found</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                {['Timestamp', 'Actor', 'Role', 'Action', 'Target', 'IP Address'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(log => (
                <tr key={log.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                  <td className="px-4 py-3 whitespace-nowrap">
                    <span className="text-xs font-mono text-[#6B7280]">{formatTimestamp(log.timestamp)}</span>
                  </td>
                  <td className="px-4 py-3 text-sm font-medium text-[#111827]">{log.actor}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize ${roleColors[log.actorRole]}`}>
                      {log.actorRole}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-[#374151]">{log.action}</td>
                  <td className="px-4 py-3 text-sm text-[#6B7280]">{log.target}</td>
                  <td className="px-4 py-3">
                    <code className="text-xs font-mono text-[#9CA3AF]">{log.ipAddress}</code>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
