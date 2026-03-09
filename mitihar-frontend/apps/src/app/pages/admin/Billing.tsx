import React, { useState } from 'react';
import { CreditCard, Key, RefreshCw, CheckCircle } from 'lucide-react';
import { allDoctors } from '../../data/mockData';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { toast } from 'sonner';

type BillingTab = 'subscriptions' | 'codes';

const codeHistory = [
  { id: 'batch1', doctor: 'Dr. Ashok Sharma', count: 10, generatedAt: '2026-01-10', usedCount: 3 },
  { id: 'batch2', doctor: 'Dr. Priya Mehta', count: 10, generatedAt: '2026-01-15', usedCount: 6 },
  { id: 'batch3', doctor: 'Dr. Ravi Nair', count: 15, generatedAt: '2025-12-01', usedCount: 14 },
  { id: 'batch4', doctor: 'Dr. Sonal Desai', count: 5, generatedAt: '2026-02-01', usedCount: 3 },
  { id: 'batch5', doctor: 'Dr. Vikram Choudhary', count: 20, generatedAt: '2025-11-01', usedCount: 2 },
];

export function AdminBilling() {
  const [tab, setTab] = useState<BillingTab>('subscriptions');
  const [selectedDoctor, setSelectedDoctor] = useState('');
  const [codeCount, setCodeCount] = useState(10);
  const [doctors, setDoctors] = useState(allDoctors);

  const handleMarkPaid = (docId: string) => {
    setDoctors(prev => prev.map(d => d.id === docId ? { ...d, billingStatus: 'paid' as const } : d));
    const doc = doctors.find(d => d.id === docId);
    toast.success(`${doc?.name} marked as paid`);
  };

  const handleGenerateCodes = () => {
    if (!selectedDoctor) {
      toast.error('Please select a doctor');
      return;
    }
    const doc = doctors.find(d => d.id === selectedDoctor);
    toast.success(`${codeCount} codes generated for ${doc?.name}`);
    setSelectedDoctor('');
  };

  const totalRevenue = doctors.reduce((s, d) => s + d.revenue, 0);
  const totalPaid = doctors.filter(d => d.billingStatus === 'paid').reduce((s, d) => s + d.revenue, 0);
  const totalPending = doctors.filter(d => d.billingStatus !== 'paid').reduce((s, d) => s + d.revenue, 0);

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Codes & Billing</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">Manage subscriptions and activation codes</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-[#E5E7EB] mb-6">
        {[
          { id: 'subscriptions' as BillingTab, label: 'Subscriptions', icon: <CreditCard size={14} /> },
          { id: 'codes' as BillingTab, label: 'Activation Codes', icon: <Key size={14} /> },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? 'border-[#1E7C45] text-[#1E7C45]'
                : 'border-transparent text-[#6B7280] hover:text-[#374151]'
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'subscriptions' && (
        <div>
          {/* Summary cards */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            {[
              { label: 'Total Revenue (March)', value: `₹${totalRevenue.toLocaleString('en-IN')}`, color: 'text-[#111827]' },
              { label: 'Collected', value: `₹${totalPaid.toLocaleString('en-IN')}`, color: 'text-[#15803d]' },
              { label: 'Pending / Overdue', value: `₹${totalPending.toLocaleString('en-IN')}`, color: 'text-[#DC2626]' },
            ].map(stat => (
              <div key={stat.label} className="bg-white border border-[#E5E7EB] rounded-lg p-5">
                <p className="text-xs text-[#9CA3AF] uppercase tracking-wide mb-1.5">{stat.label}</p>
                <p className={`text-3xl font-bold tabular-nums ${stat.color}`}>{stat.value}</p>
              </div>
            ))}
          </div>

          {/* Billing table */}
          <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                  {['Doctor', 'Active Patients', 'Amount', 'Status', 'Action'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {doctors.map(doc => (
                  <tr key={doc.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                    <td className="px-4 py-4">
                      <p className="text-sm font-medium text-[#111827]">{doc.name}</p>
                      <p className="text-xs text-[#6B7280]">{doc.email}</p>
                    </td>
                    <td className="px-4 py-4 text-sm text-[#374151] tabular-nums">{doc.activePatients}</td>
                    <td className="px-4 py-4 text-sm font-medium text-[#111827] tabular-nums">
                      ₹{doc.revenue.toLocaleString('en-IN')}
                    </td>
                    <td className="px-4 py-4">
                      <StatusBadge status={doc.billingStatus} />
                    </td>
                    <td className="px-4 py-4">
                      {doc.billingStatus !== 'paid' ? (
                        <button
                          onClick={() => handleMarkPaid(doc.id)}
                          className="flex items-center gap-1.5 h-7 px-2.5 rounded-md bg-[#1E7C45] text-white text-xs hover:bg-[#166534] transition-colors"
                        >
                          <CheckCircle size={12} />
                          Mark Paid
                        </button>
                      ) : (
                        <span className="text-xs text-[#9CA3AF]">Settled</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'codes' && (
        <div>
          {/* Generate codes form */}
          <div className="bg-white border border-[#E5E7EB] rounded-lg p-5 mb-6">
            <h2 className="text-base font-medium text-[#111827] mb-4">Generate Activation Codes</h2>
            <div className="flex items-end gap-4 flex-wrap">
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1.5">Doctor</label>
                <select
                  value={selectedDoctor}
                  onChange={e => setSelectedDoctor(e.target.value)}
                  className="h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] min-w-[200px]"
                >
                  <option value="">Select doctor...</option>
                  {doctors.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1.5">Number of Codes</label>
                <select
                  value={codeCount}
                  onChange={e => setCodeCount(Number(e.target.value))}
                  className="h-10 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]"
                >
                  {[5, 10, 15, 20, 25, 50].map(n => <option key={n} value={n}>{n} codes</option>)}
                </select>
              </div>
              <button
                onClick={handleGenerateCodes}
                className="flex items-center gap-2 h-10 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors"
              >
                <RefreshCw size={14} />
                Generate Codes
              </button>
            </div>
          </div>

          {/* Code batches history */}
          <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
            <div className="px-5 py-3 bg-[#F9FAFB] border-b border-[#E5E7EB]">
              <p className="text-sm font-medium text-[#111827]">Code Generation History</p>
            </div>
            <table className="w-full">
              <thead>
                <tr className="border-b border-[#E5E7EB]">
                  {['Doctor', 'Generated On', 'Codes Issued', 'Used', 'Remaining'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {codeHistory.map(batch => (
                  <tr key={batch.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-[#111827]">{batch.doctor}</td>
                    <td className="px-4 py-3 text-sm text-[#6B7280] font-mono">{batch.generatedAt}</td>
                    <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">{batch.count}</td>
                    <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">{batch.usedCount}</td>
                    <td className="px-4 py-3">
                      <span className={`text-sm font-medium tabular-nums ${
                        batch.count - batch.usedCount <= 3 ? 'text-[#DC2626]' : 'text-[#15803d]'
                      }`}>
                        {batch.count - batch.usedCount}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
