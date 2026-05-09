import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  Key, RefreshCw, Loader2, BarChart2, TrendingUp, CheckCircle,
} from 'lucide-react';
import { adminApi, DoctorAdminView } from '../../../lib/adminApi';
import { aqk } from '../../../lib/queryKeys';
import apiClient from '../../../lib/axios';

type BillingTab = 'consultations' | 'codes' | 'renewals';

// ── Consultation Tracker Tab ──────────────────────────────────────────────────
function ConsultationsTab() {
  const { data, isLoading } = useQuery({
    queryKey: aqk.consultations(),
    queryFn: () => apiClient.get('/admin/consultations').then(r => r.data),
    staleTime: 60_000,
  });
  const { data: annual } = useQuery({
    queryKey: aqk.annualStats(),
    queryFn: () => apiClient.get('/admin/consultations/annual').then(r => r.data),
    staleTime: 60_000,
  });

  if (isLoading) return <div className="py-20 flex justify-center"><Loader2 size={24} className="animate-spin text-[#1E7C45]" /></div>;

  return (
    <div>
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Consultations This Month', value: data?.total_consultations_this_month ?? 0, color: 'text-[#1E7C45]' },
          { label: 'Total Revenue (Month)', value: `₹${(data?.total_revenue ?? 0).toLocaleString('en-IN')}`, color: 'text-[#111827]' },
          { label: 'Platform Royalty (Month)', value: `₹${(data?.total_royalty ?? 0).toLocaleString('en-IN')}`, color: 'text-[#2563EB]' },
        ].map(s => (
          <div key={s.label} className="bg-white border border-[#E5E7EB] rounded-lg p-5">
            <p className="text-xs text-[#9CA3AF] uppercase tracking-wide mb-1.5">{s.label}</p>
            <p className={`text-3xl font-bold tabular-nums ${s.color}`}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* YTD royalty split */}
      {annual && (
        <div className="bg-white border border-[#E5E7EB] rounded-lg p-5 mb-6">
          <p className="text-base font-medium text-[#111827] mb-4">Financial Year Royalty Split — {annual.financial_year ?? annual.year}</p>
          <div className="grid grid-cols-4 gap-4">
            {[
              { label: 'FY Consultations', value: annual.ytd_consultations },
              { label: 'FY Revenue', value: `₹${annual.ytd_revenue?.toLocaleString('en-IN')}` },
              { label: 'Royalty Pool (2%)', value: `₹${annual.royalty_pool_6pct?.toLocaleString('en-IN')}` },
              { label: 'Per Member (0.67%)', value: `₹${annual.royalty_per_member_2pct?.toLocaleString('en-IN')}` },
            ].map(s => (
              <div key={s.label} className="bg-[#F0FDF4] rounded-lg p-4">
                <p className="text-xs text-[#6B7280] mb-1">{s.label}</p>
                <p className="text-xl font-bold text-[#1E7C45]">{s.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Per-doctor breakdown */}
      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
        <div className="px-5 py-4 border-b border-[#E5E7EB]">
          <p className="text-base font-medium text-[#111827]">Per-Doctor Breakdown — {data?.month}</p>
        </div>
        <table className="w-full">
          <thead>
            <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
              {['Doctor', 'Patients', 'Consultations', 'Revenue Generated', 'Platform Royalty (6%)'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(data?.per_doctor ?? []).map((d: any) => (
              <tr key={d.doctor_id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB]">
                <td className="px-4 py-4">
                  <p className="text-sm font-medium text-[#111827]">{d.doctor_name}</p>
                  <p className="text-xs text-[#6B7280]">{d.doctor_email}</p>
                </td>
                <td className="px-4 py-4 text-sm text-[#374151] tabular-nums">{d.patient_count}</td>
                <td className="px-4 py-4 text-sm font-semibold text-[#1E7C45] tabular-nums">{d.consultations_this_month}</td>
                <td className="px-4 py-4 text-sm text-[#374151] tabular-nums">₹{d.revenue_generated?.toLocaleString('en-IN')}</td>
                <td className="px-4 py-4 text-sm font-semibold text-[#2563EB] tabular-nums">₹{d.platform_royalty?.toLocaleString('en-IN')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Generate Codes Panel ──────────────────────────────────────────────────────
function GenerateCodesPanel({ doctors }: { doctors: DoctorAdminView[] }) {
  const queryClient = useQueryClient();
  const [selectedDoctorId, setSelectedDoctorId] = useState<number | ''>('');
  const [count, setCount] = useState(10);
  const [expiryDays, setExpiryDays] = useState(30);

  const generateMutation = useMutation({
    mutationFn: adminApi.generateCodes,
    onSuccess: (codes) => {
      queryClient.invalidateQueries({ queryKey: aqk.codes() });
      const doc = doctors.find(d => d.id === selectedDoctorId);
      toast.success(`${codes.length} codes generated for ${doc?.name ?? 'doctor'}`);
      setSelectedDoctorId('');
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? 'Failed to generate codes'),
  });

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg p-5 mb-6">
      <h2 className="text-base font-medium text-[#111827] mb-4">Generate Activation Codes</h2>
      <div className="flex items-end gap-4 flex-wrap">
        <div>
          <label htmlFor="gen-doctor" className="block text-sm font-medium text-[#374151] mb-1.5">Doctor</label>
          <select id="gen-doctor" value={selectedDoctorId} onChange={e => setSelectedDoctorId(e.target.value === '' ? '' : Number(e.target.value))}
            className="h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] min-w-[200px]">
            <option value="">Select doctor…</option>
            {doctors.filter(d => d.is_active).map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="gen-count" className="block text-sm font-medium text-[#374151] mb-1.5">Number of Codes</label>
          <select id="gen-count" value={count} onChange={e => setCount(Number(e.target.value))}
            className="h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]">
            {[5, 10, 15, 20, 25, 50].map(n => <option key={n} value={n}>{n} codes</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="gen-expiry" className="block text-sm font-medium text-[#374151] mb-1.5">Valid For</label>
          <select id="gen-expiry" value={expiryDays} onChange={e => setExpiryDays(Number(e.target.value))}
            className="h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]">
            {[7, 14, 30, 60, 90].map(n => <option key={n} value={n}>{n} days</option>)}
          </select>
        </div>
        <button onClick={() => { if (!selectedDoctorId) { toast.error('Select a doctor first'); return; } generateMutation.mutate({ doctor_id: Number(selectedDoctorId), count, expires_in_days: expiryDays }); }}
          disabled={!selectedDoctorId || generateMutation.isPending}
          className="flex items-center gap-2 h-10 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] disabled:opacity-50">
          {generateMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          Generate Codes
        </button>
      </div>
    </div>
  );
}

// ── Codes Tab ─────────────────────────────────────────────────────────────────
function CodesTab({ doctors }: { doctors: DoctorAdminView[] }) {
  const { data: codes = [], isLoading } = useQuery({
    queryKey: aqk.codes(),
    queryFn: () => adminApi.listCodes(),
    staleTime: 30_000,
  });

  return (
    <div>
      <GenerateCodesPanel doctors={doctors} />
      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
        <div className="px-5 py-3 bg-[#F9FAFB] border-b border-[#E5E7EB] flex items-center justify-between">
          <p className="text-sm font-medium text-[#111827]">All Codes</p>
          <p className="text-xs text-[#9CA3AF]">{codes.length} codes</p>
        </div>
        {isLoading ? (
          <div className="py-10 flex justify-center"><Loader2 size={20} className="animate-spin text-[#1E7C45]" /></div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#E5E7EB]">
                {['Code', 'Doctor ID', 'Used', 'Used By', 'Expires', 'Created'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {codes.slice(0, 100).map((c: any) => (
                <tr key={c.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB]">
                  <td className="px-4 py-3"><code className="text-xs font-mono font-semibold text-[#111827]">{c.code}</code></td>
                  <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">{c.doctor_id}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${c.is_used ? 'bg-[#F3F4F6] text-[#6B7280]' : 'bg-[#DCFCE7] text-[#15803d]'}`}>
                      {c.is_used ? 'Used' : 'Available'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-[#374151]">{c.used_by_patient_id ?? <span className="text-[#9CA3AF]">—</span>}</td>
                  <td className="px-4 py-3 text-xs text-[#9CA3AF]">{c.expires_at ? new Date(c.expires_at).toLocaleDateString('en-IN') : '—'}</td>
                  <td className="px-4 py-3 text-xs text-[#9CA3AF]">{new Date(c.created_at).toLocaleDateString('en-IN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ── Renewals Tab ──────────────────────────────────────────────────────────────
function RenewalsTab() {
  const queryClient = useQueryClient();
  const { data: renewals = [], isLoading } = useQuery({
    queryKey: aqk.renewals(),
    queryFn: () => apiClient.get('/admin/renewals').then(r => r.data),
    staleTime: 30_000,
  });

  const overrideMut = useMutation({
    mutationFn: (patientId: number) => apiClient.post(`/admin/renewals/${patientId}/override-approve`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aqk.renewals() });
      queryClient.invalidateQueries({ queryKey: aqk.stats() });
      toast.success('Renewal approved');
    },
    onError: () => toast.error('Failed to approve'),
  });

  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
      <div className="px-5 py-4 border-b border-[#E5E7EB] flex items-center justify-between">
        <p className="text-base font-medium text-[#111827]">Pending Renewals</p>
        <p className="text-xs text-[#9CA3AF]">{renewals.length} pending</p>
      </div>
      {isLoading ? (
        <div className="py-10 flex justify-center"><Loader2 size={20} className="animate-spin text-[#1E7C45]" /></div>
      ) : renewals.length === 0 ? (
        <div className="py-12 flex flex-col items-center">
          <CheckCircle size={32} className="text-[#34B164] mb-2" />
          <p className="text-sm text-[#6B7280]">No pending renewals</p>
        </div>
      ) : (
        <table className="w-full">
          <thead>
            <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
              {['Patient', 'Doctor', 'Token 1', 'Expiry', 'Requested At', 'Action'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {renewals.map((r: any) => (
              <tr key={r.patient_id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB]">
                <td className="px-4 py-4">
                  <p className="text-sm font-medium text-[#111827]">{r.patient_name}</p>
                  <p className="text-xs text-[#6B7280]">{r.patient_email}</p>
                </td>
                <td className="px-4 py-4 text-sm text-[#374151]">{r.doctor_name ?? '—'}</td>
                <td className="px-4 py-4 text-xs font-mono text-[#374151]">{r.token_1 ?? '—'}</td>
                <td className="px-4 py-4 text-xs text-[#B45309]">
                  {r.token_1_expiry ? new Date(r.token_1_expiry).toLocaleDateString('en-IN') : '—'}
                </td>
                <td className="px-4 py-4 text-xs text-[#9CA3AF]">
                  {r.renewal_requested_at ? new Date(r.renewal_requested_at).toLocaleDateString('en-IN') : '—'}
                </td>
                <td className="px-4 py-4">
                  <button onClick={() => overrideMut.mutate(r.patient_id)}
                    disabled={overrideMut.isPending}
                    className="flex items-center gap-1.5 h-7 px-2.5 rounded-md bg-[#1E7C45] text-white text-xs hover:bg-[#166534] disabled:opacity-50">
                    <CheckCircle size={11} /> Approve
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export function AdminBilling() {
  const [tab, setTab] = useState<BillingTab>('consultations');

  const { data: doctors = [] } = useQuery({
    queryKey: aqk.doctors(),
    queryFn: adminApi.listDoctors,
    staleTime: 60_000,
  });

  const TABS = [
    { id: 'consultations' as BillingTab, label: 'Consultation Tracker', icon: <BarChart2 size={14} /> },
    { id: 'codes'         as BillingTab, label: 'Activation Codes',     icon: <Key size={14} /> },
    { id: 'renewals'      as BillingTab, label: 'Renewals',             icon: <TrendingUp size={14} /> },
  ];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Codes &amp; Consultations</h1>
        <p className="text-sm text-[#6B7280] mt-0.5">Track visit royalties, manage activation codes and renewals</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-[#E5E7EB] mb-6">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id ? 'border-[#1E7C45] text-[#1E7C45]' : 'border-transparent text-[#6B7280] hover:text-[#374151]'
            }`}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {tab === 'consultations' && <ConsultationsTab />}
      {tab === 'codes'         && <CodesTab doctors={doctors as DoctorAdminView[]} />}
      {tab === 'renewals'      && <RenewalsTab />}
    </div>
  );
}
