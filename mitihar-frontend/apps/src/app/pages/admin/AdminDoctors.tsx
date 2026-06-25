import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Search, UserCheck, ChevronLeft, ChevronRight, Stethoscope,
  Loader2, X, Plus,
} from 'lucide-react';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { adminApi, DoctorAdminView, CreateDoctorBody, UpdateDoctorBody } from '../../../lib/adminApi';
import { aqk } from '../../../lib/queryKeys';

const PAGE_SIZE = 10;

// ── Onboard Doctor Modal ──────────────────────────────────────────────────────
const EMPTY_FORM: CreateDoctorBody = {
  email: '', password: '', name: '', phone: '',
  specialization: '', clinic_name: '', city: '',
};

function OnboardModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<CreateDoctorBody>(EMPTY_FORM);

  const createMutation = useMutation({
    mutationFn: adminApi.createDoctor,
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: aqk.doctors() });
      queryClient.invalidateQueries({ queryKey: aqk.stats() });
      toast.success(`Dr. ${doc.name} onboarded successfully`);
      onClose();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail ?? 'Failed to create doctor';
      toast.error(typeof msg === 'string' ? msg : 'Failed to create doctor');
    },
  });

  const set = (k: keyof CreateDoctorBody) =>
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm(prev => ({ ...prev, [k]: e.target.value }));

  const canSubmit = form.email.trim() && form.password.length >= 8 && form.name.trim();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} onKeyDown={(e) => e.key === "Escape" && (onClose)} role="button" aria-label="Close dialog" tabIndex={0} />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b border-[#E5E7EB]">
          <p className="text-base font-semibold text-[#111827]">Onboard New Doctor</p>
          <button onClick={onClose} className="w-7 h-7 rounded flex items-center justify-center text-[#9CA3AF] hover:bg-[#F3F4F6]">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-3">
          {/* Required fields */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="doc-name" className="block text-xs font-medium text-[#374151] mb-1">
                Full Name <span className="text-[#DC2626]">*</span>
              </label>
              <input value={form.name} id="doc-name" onChange={set('name')} placeholder="Dr. Priya Mehta"
                className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
            </div>
            <div>
              <label htmlFor="doc-email" className="block text-xs font-medium text-[#374151] mb-1">
                Email <span className="text-[#DC2626]">*</span>
              </label>
              <input type="email" value={form.email} id="doc-email" onChange={set('email')} placeholder="dr@clinic.com"
                className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
            </div>
          </div>

          <div>
            <label htmlFor="doc-password" className="block text-xs font-medium text-[#374151] mb-1">
              Temporary Password <span className="text-[#DC2626]">*</span>
              <span className="text-[#9CA3AF] font-normal ml-1">(min 8 chars)</span>
            </label>
            <input type="password" value={form.password} id="doc-password" onChange={set('password')} placeholder="••••••••"
              className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
          </div>

          {/* Optional fields */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="doc-specialization" className="block text-xs font-medium text-[#374151] mb-1">Specialization</label>
              <input value={form.specialization} id="doc-specialization" onChange={set('specialization')} placeholder="Dietitian"
                className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
            </div>
            <div>
              <label htmlFor="doc-phone" className="block text-xs font-medium text-[#374151] mb-1">Phone</label>
              <input value={form.phone} id="doc-phone" onChange={set('phone')} placeholder="+91 98765 43210"
                className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="doc-clinic" className="block text-xs font-medium text-[#374151] mb-1">Clinic Name</label>
              <input value={form.clinic_name} id="doc-clinic" onChange={set('clinic_name')} placeholder="Wellness Clinic"
                className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
            </div>
            <div>
              <label htmlFor="doc-city" className="block text-xs font-medium text-[#374151] mb-1">City</label>
              <input id="doc-city" value={form.city} onChange={set('city')} placeholder="Mumbai"
                className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
            </div>
          </div>
        </div>

        <div className="flex gap-2 justify-end p-5 border-t border-[#E5E7EB]">
          <button onClick={onClose} className="h-9 px-4 rounded-md border border-[#D1D5DB] text-sm text-[#374151] hover:bg-[#F9FAFB]">
            Cancel
          </button>
          <button
            onClick={() => createMutation.mutate(form)}
            disabled={!canSubmit || createMutation.isPending}
            className="flex items-center gap-1.5 h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] disabled:opacity-50 transition-colors"
          >
            {createMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            Create Doctor
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Edit Doctor Modal ─────────────────────────────────────────────────────────
function EditDoctorModal({ doctor, onClose }: { doctor: DoctorAdminView; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<UpdateDoctorBody>({
    name: doctor.name,
    specialization: doctor.specialization ?? '',
    clinic_name: doctor.clinic_name ?? '',
    city: doctor.city ?? '',
    phone: doctor.phone ?? '',
  });

  const updateMutation = useMutation({
    mutationFn: () => adminApi.updateDoctor(doctor.id, {
      name: form.name?.trim() || undefined,
      specialization: form.specialization?.trim() || undefined,
      clinic_name: form.clinic_name?.trim() || undefined,
      city: form.city?.trim() || undefined,
      phone: form.phone?.trim() || undefined,
    }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: aqk.doctors() });
      toast.success(`${updated.name} updated`);
      onClose();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail ?? 'Failed to update doctor';
      toast.error(typeof msg === 'string' ? msg : 'Failed to update doctor');
    },
  });

  const set = (k: keyof UpdateDoctorBody) =>
    (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm(prev => ({ ...prev, [k]: e.target.value }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} onKeyDown={(e) => e.key === 'Escape' && onClose()} role="button" aria-label="Close dialog" tabIndex={0} />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between p-5 border-b border-[#E5E7EB]">
          <p className="text-base font-semibold text-[#111827]">Edit Doctor</p>
          <button onClick={onClose} className="w-7 h-7 rounded flex items-center justify-center text-[#9CA3AF] hover:bg-[#F3F4F6]">
            <X size={16} />
          </button>
        </div>

        <div className="p-5 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label htmlFor="edit-name" className="block text-xs font-medium text-[#374151] mb-1">Full Name</label>
              <input value={form.name ?? ''} id="edit-name" onChange={set('name')}
                className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
            </div>
            <div>
              <label htmlFor="edit-specialization" className="block text-xs font-medium text-[#374151] mb-1">Specialization</label>
              <input value={form.specialization ?? ''} id="edit-specialization" onChange={set('specialization')}
                className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
            </div>
            <div>
              <label htmlFor="edit-phone" className="block text-xs font-medium text-[#374151] mb-1">Phone</label>
              <input value={form.phone ?? ''} id="edit-phone" onChange={set('phone')}
                className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
            </div>
            <div>
              <label htmlFor="edit-clinic" className="block text-xs font-medium text-[#374151] mb-1">Clinic Name</label>
              <input value={form.clinic_name ?? ''} id="edit-clinic" onChange={set('clinic_name')}
                className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
            </div>
            <div>
              <label htmlFor="edit-city" className="block text-xs font-medium text-[#374151] mb-1">City</label>
              <input value={form.city ?? ''} id="edit-city" onChange={set('city')}
                className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
            </div>
          </div>
        </div>

        <div className="flex gap-2 justify-end p-5 border-t border-[#E5E7EB]">
          <button onClick={onClose} className="h-9 px-4 rounded-md border border-[#D1D5DB] text-sm text-[#374151] hover:bg-[#F9FAFB]">
            Cancel
          </button>
          <button
            onClick={() => updateMutation.mutate()}
            disabled={updateMutation.isPending}
            className="flex items-center gap-1.5 h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] disabled:opacity-50 transition-colors"
          >
            {updateMutation.isPending && <Loader2 size={14} className="animate-spin" />}
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export function AdminDoctors() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [showOnboard, setShowOnboard] = useState(false);
  const [editDoctor, setEditDoctor] = useState<DoctorAdminView | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean; docId: number; docName: string; action: 'deactivate' | 'activate' | 'delete'
  }>({ open: false, docId: 0, docName: '', action: 'deactivate' });

  const { data: doctors = [], isLoading } = useQuery({
    queryKey: aqk.doctors(),
    queryFn: adminApi.listDoctors,
    staleTime: 60_000,
  });

  // Client-side filter + paginate (doctor list is small)
  const filtered = doctors.filter((d: DoctorAdminView) =>
    d.name.toLowerCase().includes(search.toLowerCase()) ||
    d.email.toLowerCase().includes(search.toLowerCase())
  );
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const deactivateMutation = useMutation({
    mutationFn: adminApi.deactivateDoctor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aqk.doctors() });
      toast.success(`${confirmDialog.docName} deactivated`);
      setConfirmDialog(prev => ({ ...prev, open: false }));
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? 'Failed'),
  });

  const deleteMutation = useMutation({
    mutationFn: adminApi.deleteDoctor,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aqk.doctors() });
      queryClient.invalidateQueries({ queryKey: aqk.stats() });
      toast.success(`${confirmDialog.docName} deleted`);
      setConfirmDialog(prev => ({ ...prev, open: false }));
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? 'Failed'),
  });

  const handleConfirm = () => {
    if (confirmDialog.action === 'deactivate' || confirmDialog.action === 'activate') {
      deactivateMutation.mutate(confirmDialog.docId);
    } else {
      deleteMutation.mutate(confirmDialog.docId);
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Doctors</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">{doctors.length} registered doctors</p>
        </div>
        <button
          onClick={() => setShowOnboard(true)}
          className="flex items-center gap-2 h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors"
        >
          <UserCheck size={15} /> Onboard Doctor
        </button>
      </div>

      {/* Search */}
      <div className="relative w-72 mb-4">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
        <input
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
          placeholder="Search doctors..."
          className="w-full h-9 pl-9 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
        />
      </div>

      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
        {isLoading ? (
          <div className="py-16 flex justify-center">
            <Loader2 size={24} className="animate-spin text-[#1E7C45]" />
          </div>
        ) : paginated.length === 0 ? (
          <div className="py-16 flex flex-col items-center text-center">
            <Stethoscope size={32} className="text-[#D1D5DB] mb-3" />
            <p className="text-base font-medium text-[#374151]">No doctors found</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                {['Doctor', 'Specialization', 'Clinic', 'City', 'Status', 'Actions'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(paginated as DoctorAdminView[]).map(doc => (
                <tr key={doc.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-[#F0FDF4] flex items-center justify-center flex-shrink-0">
                        <span className="text-xs font-semibold text-[#1E7C45]">
                          {doc.name.split(' ').map((w: string) => w[0]).join('').slice(0, 2).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-[#111827]">{doc.name}</p>
                        <p className="text-xs text-[#6B7280]">{doc.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-sm text-[#374151]">{doc.specialization ?? '—'}</td>
                  <td className="px-4 py-4 text-sm text-[#374151]">{doc.clinic_name ?? '—'}</td>
                  <td className="px-4 py-4 text-sm text-[#374151]">{doc.city ?? '—'}</td>
                  <td className="px-4 py-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      doc.is_active ? 'bg-[#DCFCE7] text-[#15803d]' : 'bg-[#F3F4F6] text-[#6B7280]'
                    }`}>
                      {doc.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => setEditDoctor(doc)}
                        className="h-7 px-2.5 rounded border border-[#D1D5DB] text-xs text-[#374151] hover:bg-[#F9FAFB] transition-colors"
                      >
                        Edit
                      </button>
                      {doc.is_active ? (
                        <button
                          onClick={() => setConfirmDialog({ open: true, docId: doc.id, docName: doc.name, action: 'deactivate' })}
                          className="h-7 px-2.5 rounded border border-[#FECACA] text-xs text-[#DC2626] hover:bg-[#FEF2F2] transition-colors"
                        >
                          Deactivate
                        </button>
                      ) : (
                        <button
                          onClick={() => setConfirmDialog({ open: true, docId: doc.id, docName: doc.name, action: 'activate' })}
                          className="h-7 px-2.5 rounded border border-[#D1D5DB] text-xs text-[#374151] hover:bg-[#F9FAFB] transition-colors"
                        >
                          Activate
                        </button>
                      )}
                      <button
                        onClick={() => setConfirmDialog({ open: true, docId: doc.id, docName: doc.name, action: 'delete' })}
                        className="h-7 px-2.5 rounded border border-[#FECACA] text-xs text-[#DC2626] hover:bg-[#FEF2F2] transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
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

      {/* Onboard modal */}
      {showOnboard && <OnboardModal onClose={() => setShowOnboard(false)} />}

      {/* Edit doctor modal */}
      {editDoctor && <EditDoctorModal doctor={editDoctor} onClose={() => setEditDoctor(null)} />}

      {/* Confirm dialog */}
      <ConfirmDialog
        open={confirmDialog.open}
        title={
          confirmDialog.action === 'delete' ? 'Delete Doctor?' :
          confirmDialog.action === 'deactivate' ? 'Deactivate Doctor?' : 'Activate Doctor?'
        }
        description={
          confirmDialog.action === 'delete'
            ? `This will remove ${confirmDialog.docName} and disconnect all their patients. This cannot be undone.`
            : confirmDialog.action === 'deactivate'
            ? `This will suspend ${confirmDialog.docName}'s access. Patient data is preserved.`
            : `This will restore ${confirmDialog.docName}'s access to the platform.`
        }
        confirmLabel={
          confirmDialog.action === 'delete' ? 'Delete' :
          confirmDialog.action === 'deactivate' ? 'Deactivate' : 'Activate'
        }
        variant={confirmDialog.action !== 'activate' ? 'danger' : 'default'}
        onConfirm={handleConfirm}
        onCancel={() => setConfirmDialog(prev => ({ ...prev, open: false }))}
      />
    </div>
  );
}
