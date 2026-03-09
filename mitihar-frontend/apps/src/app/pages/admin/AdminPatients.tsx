import React, { useState } from 'react';
import { Search, Users } from 'lucide-react';
import { patients, allDoctors } from '../../data/mockData';
import { StatusBadge } from '../../components/ui/StatusBadge';

const PAGE_SIZE = 8;

export function AdminPatients() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const filtered = patients.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    p.email.toLowerCase().includes(search.toLowerCase())
  );

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const getDoctorName = (doctorId: string) =>
    allDoctors.find(d => d.id === doctorId)?.name ?? 'Unknown';

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Patients</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">{patients.length} total patients across platform</p>
        </div>
      </div>

      <div className="relative w-72 mb-4">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
        <input
          type="text"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search patients..."
          className="w-full h-9 pl-9 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
        />
      </div>

      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
        {paginated.length === 0 ? (
          <div className="py-16 flex flex-col items-center">
            <Users size={32} className="text-[#D1D5DB] mb-3" />
            <p className="text-base font-medium text-[#374151]">No patients found</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                {['Patient', 'Doctor', 'Plan Expiry', 'BMI', 'Conditions', 'Status'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginated.map(p => (
                <tr key={p.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-[#F0FDF4] flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-semibold text-[#1E7C45]">
                          {p.name.split(' ').map(w => w[0]).join('').slice(0, 2)}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#111827]">{p.name}</p>
                        <p className="text-xs text-[#6B7280]">{p.age}y · {p.gender}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-sm text-[#374151]">{getDoctorName(p.doctorId)}</td>
                  <td className="px-4 py-4 text-sm text-[#374151] tabular-nums">{p.planExpiry}</td>
                  <td className="px-4 py-4 text-sm text-[#374151] tabular-nums">{p.bmi}</td>
                  <td className="px-4 py-4">
                    <div className="flex flex-wrap gap-1">
                      {p.conditions.length > 0
                        ? p.conditions.slice(0, 2).map(c => (
                            <span key={c} className="px-2 py-0.5 rounded-full text-[11px] bg-[#EFF6FF] text-[#2563EB]">{c}</span>
                          ))
                        : <span className="text-xs text-[#9CA3AF]">None</span>
                      }
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <StatusBadge status={p.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {filtered.length > PAGE_SIZE && (
        <div className="flex items-center justify-between mt-4 px-1">
          <p className="text-sm text-[#6B7280]">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-1">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="h-8 px-3 rounded border border-[#E5E7EB] text-sm text-[#374151] hover:bg-[#F3F4F6] disabled:opacity-40">
              Previous
            </button>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="h-8 px-3 rounded border border-[#E5E7EB] text-sm text-[#374151] hover:bg-[#F3F4F6] disabled:opacity-40">
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
