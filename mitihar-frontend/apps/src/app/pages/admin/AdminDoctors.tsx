import React, { useState } from 'react';
import { Search, UserCheck, ChevronLeft, ChevronRight, Stethoscope } from 'lucide-react';
import { allDoctors } from '../../data/mockData';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { toast } from 'sonner';

const PAGE_SIZE = 5;

export function AdminDoctors() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [doctors, setDoctors] = useState(allDoctors);
  const [confirmDialog, setConfirmDialog] = useState<{ open: boolean; docId: string; action: string }>({
    open: false, docId: '', action: ''
  });

  const filtered = doctors.filter(d =>
    d.name.toLowerCase().includes(search.toLowerCase()) ||
    d.email.toLowerCase().includes(search.toLowerCase())
  );

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleAction = (docId: string, action: string) => {
    setConfirmDialog({ open: true, docId, action });
  };

  const confirm = () => {
    const doc = doctors.find(d => d.id === confirmDialog.docId);
    if (confirmDialog.action === 'deactivate') {
      setDoctors(prev => prev.map(d => d.id === confirmDialog.docId ? { ...d, status: 'inactive' as const } : d));
      toast.success(`${doc?.name} deactivated`);
    } else if (confirmDialog.action === 'activate') {
      setDoctors(prev => prev.map(d => d.id === confirmDialog.docId ? { ...d, status: 'active' as const } : d));
      toast.success(`${doc?.name} activated`);
    }
    setConfirmDialog({ open: false, docId: '', action: '' });
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Doctors</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">{doctors.length} registered doctors</p>
        </div>
        <button className="flex items-center gap-2 h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors">
          <UserCheck size={15} />
          Onboard Doctor
        </button>
      </div>

      {/* Search */}
      <div className="relative w-72 mb-4">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
        <input
          type="text"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search doctors..."
          className="w-full h-9 pl-9 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
        />
      </div>

      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
        {paginated.length === 0 ? (
          <div className="py-16 flex flex-col items-center text-center">
            <Stethoscope size={32} className="text-[#D1D5DB] mb-3" />
            <p className="text-base font-medium text-[#374151]">No doctors found</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                {['Doctor', 'Specialty', 'Active Patients', 'Revenue', 'Codes Left', 'Billing', 'Status', 'Actions'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginated.map(doc => (
                <tr key={doc.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-[#F0FDF4] flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-semibold text-[#1E7C45]">
                          {doc.name.split(' ').filter((_, i) => i > 0).map(w => w[0]).join('').slice(0, 2)}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#111827]">{doc.name}</p>
                        <p className="text-xs text-[#6B7280]">{doc.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-sm text-[#374151]">{doc.specialty}</td>
                  <td className="px-4 py-4 text-sm text-[#374151] tabular-nums">{doc.activePatients}</td>
                  <td className="px-4 py-4 text-sm font-medium text-[#111827] tabular-nums">₹{doc.revenue.toLocaleString('en-IN')}</td>
                  <td className="px-4 py-4">
                    <span className={`text-sm tabular-nums font-medium ${doc.codesRemaining <= 3 ? 'text-[#DC2626]' : 'text-[#374151]'}`}>
                      {doc.codesRemaining}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <StatusBadge status={doc.billingStatus} />
                  </td>
                  <td className="px-4 py-4">
                    <StatusBadge status={doc.status} />
                  </td>
                  <td className="px-4 py-4">
                    <button
                      onClick={() => handleAction(doc.id, doc.status === 'active' ? 'deactivate' : 'activate')}
                      className={`h-7 px-2.5 rounded border text-xs transition-colors ${
                        doc.status === 'active'
                          ? 'border-[#FECACA] text-[#DC2626] hover:bg-[#FEF2F2]'
                          : 'border-[#D1D5DB] text-[#374151] hover:bg-[#F9FAFB]'
                      }`}
                    >
                      {doc.status === 'active' ? 'Deactivate' : 'Activate'}
                    </button>
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
            Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of {filtered.length}
          </p>
          <div className="flex items-center gap-1">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
              className="w-8 h-8 rounded border border-[#E5E7EB] flex items-center justify-center text-[#374151] hover:bg-[#F3F4F6] disabled:opacity-40">
              <ChevronLeft size={14} />
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
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

      <ConfirmDialog
        open={confirmDialog.open}
        title={confirmDialog.action === 'deactivate' ? 'Deactivate Doctor?' : 'Activate Doctor?'}
        description={
          confirmDialog.action === 'deactivate'
            ? 'This will suspend the doctor\'s access to the platform. Their patient data will be preserved.'
            : 'This will restore the doctor\'s access to the platform.'
        }
        confirmLabel={confirmDialog.action === 'deactivate' ? 'Deactivate' : 'Activate'}
        variant={confirmDialog.action === 'deactivate' ? 'danger' : 'default'}
        onConfirm={confirm}
        onCancel={() => setConfirmDialog({ open: false, docId: '', action: '' })}
      />
    </div>
  );
}
