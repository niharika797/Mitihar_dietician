import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  CreditCard, Key, RefreshCw, CheckCircle, Loader2,
  ChevronDown, ChevronUp,
} from 'lucide-react';
import { adminApi, DoctorAdminView, BillingDoctor } from '../../../lib/adminApi';
import { aqk } from '../../../lib/queryKeys';

type BillingTab = 'overview' | 'codes';

// ── Generate Codes Panel ──────────────────────────────────────────────────────
function GenerateCodesPanel({ doctors }: { doctors: DoctorAdminView[] }) {
  const queryClient = useQueryClient();
  const [selectedDoctorId, setSelectedDoctorId] = useState<number | ''>('');
  const [count, setCount] = useState(10);
  const [expiryDays, setExpiryDays] = useState(30);

  const generateMutation = useMutation({
    mutationFn: adminApi.generateCodes,
    onSuccess: (codes) => {
      queryClient.invalidateQueries({ queryKey: aqk.billing() });
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
          <label className="block text-sm font-medium text-[#374151] mb-1.5">Doctor</label>
          <select
            value={selectedDoctorId}
            onChange={e => setSelectedDoctorId(e.target.value === '' ? '' : Number(e.target.value))}
            className="h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] min-w-[200px]"
          >
            <option value="">Select doctor…</option>
            {doctors.filter(d => d.is_active).map(d => (
              <option key={d.id} value={d.id}>{d.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-[#374151] mb-1.5">Number of Codes</label>
          <select
            value={count}
            onChange={e => setCount(Number(e.target.value))}
            className="h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
          >
            {[5, 10, 15, 20, 25, 50].map(n => <option key={n} value={n}>{n} codes</option>)}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-[#374151] mb-1.5">Valid For</label>
          <select
            value={expiryDays}
            onChange={e => setExpiryDays(Number(e.target.value))}
            className="h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
          >
            {[7, 14, 30, 60, 90, 180, 365].map(n => <option key={n} value={n}>{n} days</option>)}
          </select>
        </div>
        <button
          onClick={() => {
            if (!selectedDoctorId) { toast.error('Select a doctor first'); return; }
            generateMutation.mutate({ doctor_id: Number(selectedDoctorId), count, expires_in_days: expiryDays });
          }}
          disabled={!selectedDoctorId || generateMutation.isPending}
          className="flex items-center gap-2 h-10 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors disabled:opacity-50"
        >
          {generateMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          Generate Codes
        </button>
      </div>
    </div>
  );
}

// ── Mark Paid Modal ───────────────────────────────────────────────────────────
function MarkPaidModal({
  doctorId, doctorName, onClose,
}: { doctorId: number; doctorName: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState('');
  const [notes, setNotes] = useState('');
  const today = new Date().toISOString().slice(0, 7); // YYYY-MM
  const [period, setPeriod] = useState(today);

  const markPaidMutation = useMutation({
    mutationFn: () =>
      adminApi.markPaid(doctorId, {
        amount: amount ? Number(amount) : undefined,
        notes: notes || undefined,
        period: period || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: aqk.billing() });
      toast.success(`Payment recorded for ${doctorName}`);
      onClose();
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? 'Failed'),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-sm p-6">
        <p className="text-base font-semibold text-[#111827] mb-1">Record Payment</p>
        <p className="text-sm text-[#6B7280] mb-4">{doctorName}</p>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-[#374151] mb-1.5">Amount (₹)</label>
            <input
              type="number" value={amount} onChange={e => setAmount(e.target.value)}
              placeholder="e.g. 5000"
              className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#374151] mb-1.5">Period</label>
            <input
              type="month" value={period} onChange={e => setPeriod(e.target.value)}
              className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#374151] mb-1.5">Notes (optional)</label>
            <input
              type="text" value={notes} onChange={e => setNotes(e.target.value)}
              placeholder="e.g. March invoice — UPI"
              className="w-full h-9 px-3 rounded-md border border-[#D1D5DB] text-sm focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
            />
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button onClick={onClose} className="flex-1 h-9 rounded-md border border-[#D1D5DB] text-sm text-[#374151] hover:bg-[#F9FAFB]">
            Cancel
          </button>
          <button
            onClick={() => markPaidMutation.mutate()}
            disabled={markPaidMutation.isPending}
            className="flex-1 flex items-center justify-center gap-1.5 h-9 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] disabled:opacity-50"
          >
            {markPaidMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle size={14} />}
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export function AdminBilling() {
  const [tab, setTab] = useState<BillingTab>('overview');
  const [markPaidDoctor, setMarkPaidDoctor] = useState<{ id: number; name: string } | null>(null);
  const [expandedDoctorId, setExpandedDoctorId] = useState<number | null>(null);

  const { data: billing, isLoading: billingLoading } = useQuery({
    queryKey: aqk.billing(),
    queryFn: adminApi.getBilling,
    staleTime: 60_000,
  });

  const { data: doctors = [], isLoading: doctorsLoading } = useQuery({
    queryKey: aqk.doctors(),
    queryFn: adminApi.listDoctors,
    staleTime: 60_000,
  });

  const { data: codes = [], isLoading: codesLoading } = useQuery({
    queryKey: aqk.codes(),
    queryFn: () => adminApi.listCodes(),
    staleTime: 30_000,
    enabled: tab === 'codes',
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Codes &amp; Billing</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">Manage subscriptions and activation codes</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-[#E5E7EB] mb-6">
        {[
          { id: 'overview' as BillingTab, label: 'Billing Overview', icon: <CreditCard size={14} /> },
          { id: 'codes'    as BillingTab, label: 'Activation Codes', icon: <Key size={14} /> },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id ? 'border-[#1E7C45] text-[#1E7C45]' : 'border-transparent text-[#6B7280] hover:text-[#374151]'
            }`}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* ── Overview tab ── */}
      {tab === 'overview' && (
        <div>
          {/* Summary cards */}
          {billingLoading ? (
            <div className="flex justify-center py-10"><Loader2 size={22} className="animate-spin text-[#1E7C45]" /></div>
          ) : (
            <>
              <div className="grid grid-cols-3 gap-4 mb-6">
                {[
                  { label: 'Total Codes Issued', value: billing?.total_codes_issued ?? 0, color: 'text-[#111827]' },
                  { label: 'Codes Redeemed',     value: billing?.total_codes_used ?? 0,   color: 'text-[#15803d]' },
                  { label: 'Codes Unused',        value: billing?.unused_codes ?? 0,        color: billing && billing.unused_codes > 0 ? 'text-[#2563EB]' : 'text-[#9CA3AF]' },
                ].map(stat => (
                  <div key={stat.label} className="bg-white border border-[#E5E7EB] rounded-lg p-5">
                    <p className="text-xs text-[#9CA3AF] uppercase tracking-wide mb-1.5">{stat.label}</p>
                    <p className={`text-3xl font-bold tabular-nums ${stat.color}`}>{stat.value}</p>
                  </div>
                ))}
              </div>

              {/* Per-doctor breakdown */}
              <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
                <div className="px-5 py-4 border-b border-[#E5E7EB]">
                  <p className="text-base font-medium text-[#111827]">Per-Doctor Code Usage</p>
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                      {['Doctor', 'Email', 'Issued', 'Used', 'Remaining', 'Action'].map(h => (
                        <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(billing?.doctors ?? []).map((d: BillingDoctor) => {
                      const remaining = d.codes_issued - d.codes_used;
                      return (
                        <tr key={d.doctor_id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                          <td className="px-4 py-4 text-sm font-medium text-[#111827]">{d.name}</td>
                          <td className="px-4 py-4 text-sm text-[#6B7280]">{d.email}</td>
                          <td className="px-4 py-4 text-sm text-[#374151] tabular-nums">{d.codes_issued}</td>
                          <td className="px-4 py-4 text-sm text-[#374151] tabular-nums">{d.codes_used}</td>
                          <td className="px-4 py-4">
                            <span className={`text-sm font-medium tabular-nums ${remaining <= 3 ? 'text-[#DC2626]' : 'text-[#15803d]'}`}>
                              {remaining}
                              {remaining <= 3 && remaining > 0 && ' ⚠️'}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <button
                              onClick={() => setMarkPaidDoctor({ id: d.doctor_id, name: d.name })}
                              className="flex items-center gap-1.5 h-7 px-2.5 rounded-md bg-[#1E7C45] text-white text-xs hover:bg-[#166534] transition-colors"
                            >
                              <CheckCircle size={11} /> Mark Paid
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Codes tab ── */}
      {tab === 'codes' && (
        <div>
          <GenerateCodesPanel doctors={doctors as DoctorAdminView[]} />

          <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
            <div className="px-5 py-3 bg-[#F9FAFB] border-b border-[#E5E7EB] flex items-center justify-between">
              <p className="text-sm font-medium text-[#111827]">All Codes</p>
              <p className="text-xs text-[#9CA3AF]">{codes.length} codes</p>
            </div>
            {codesLoading ? (
              <div className="py-10 flex justify-center">
                <Loader2 size={20} className="animate-spin text-[#1E7C45]" />
              </div>
            ) : codes.length === 0 ? (
              <div className="py-12 text-center text-sm text-[#9CA3AF]">No codes generated yet</div>
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
                    <tr key={c.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                      <td className="px-4 py-3">
                        <code className="text-xs font-mono font-semibold text-[#111827] tracking-wider">{c.code}</code>
                      </td>
                      <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">{c.doctor_id}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          c.is_used ? 'bg-[#F3F4F6] text-[#6B7280]' : 'bg-[#DCFCE7] text-[#15803d]'
                        }`}>
                          {c.is_used ? 'Used' : 'Available'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">
                        {c.used_by_patient_id ?? <span className="text-[#9CA3AF]">—</span>}
                      </td>
                      <td className="px-4 py-3 text-xs text-[#9CA3AF] tabular-nums whitespace-nowrap">
                        {c.expires_at
                          ? new Date(c.expires_at).toLocaleDateString('en-IN')
                          : '—'}
                      </td>
                      <td className="px-4 py-3 text-xs text-[#9CA3AF] tabular-nums whitespace-nowrap">
                        {new Date(c.created_at).toLocaleDateString('en-IN')}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Mark Paid Modal */}
      {markPaidDoctor && (
        <MarkPaidModal
          doctorId={markPaidDoctor.id}
          doctorName={markPaidDoctor.name}
          onClose={() => setMarkPaidDoctor(null)}
        />
      )}
    </div>
  );
}
