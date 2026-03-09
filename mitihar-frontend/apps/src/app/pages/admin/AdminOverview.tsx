import React from 'react';
import { useNavigate } from 'react-router';
import { TrendingUp, AlertTriangle, CheckCircle, ArrowRight } from 'lucide-react';
import { allDoctors, patients } from '../../data/mockData';
import { StatusBadge } from '../../components/ui/StatusBadge';

const monthlyRevenue = allDoctors.reduce((s, d) => s + d.revenue, 0);
const lastMonthRevenue = 55100;
const revenueGrowth = (((monthlyRevenue - lastMonthRevenue) / lastMonthRevenue) * 100).toFixed(1);
const activeDoctors = allDoctors.filter(d => d.status === 'active').length;
const totalPatients = patients.length;
const activePatients = patients.filter(p => p.status === 'active').length;

const alerts = [
  { id: 'a1', type: 'error', message: 'Dr. Sonal Desai billing overdue — ₹2,250 pending', action: 'Mark Paid', to: '/admin/billing' },
  { id: 'a2', type: 'warning', message: '3 food items pending approval', action: 'Review', to: '/admin/food-database' },
  { id: 'a3', type: 'warning', message: 'Dr. Sonal Desai has only 2 codes left', action: 'Generate', to: '/admin/billing' },
];

export function AdminOverview() {
  const navigate = useNavigate();

  const today = new Date('2026-03-08');
  const monthYear = today.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });

  return (
    <div className="p-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">{monthYear} · Admin Dashboard</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">Platform-wide overview and health metrics</p>
        </div>
      </div>

      {/* Revenue + Platform health row */}
      <div className="grid grid-cols-12 gap-5 mb-5">
        {/* Revenue headline */}
        <div className="col-span-12 md:col-span-5 bg-white border border-[#E5E7EB] rounded-lg p-6">
          <p className="text-sm font-medium text-[#6B7280] uppercase tracking-wide mb-2">Revenue This Month</p>
          <p className="text-4xl font-bold text-[#111827] tabular-nums mb-2">
            ₹{monthlyRevenue.toLocaleString('en-IN')}
          </p>
          <div className="flex items-center gap-1.5 text-sm text-[#15803d]">
            <TrendingUp size={15} />
            <span className="font-medium">↑ {revenueGrowth}% vs last month</span>
          </div>
          <p className="text-xs text-[#9CA3AF] mt-1">vs ₹{lastMonthRevenue.toLocaleString('en-IN')} in February</p>
        </div>

        {/* Platform health */}
        <div className="col-span-12 md:col-span-7 bg-white border border-[#E5E7EB] rounded-lg p-6">
          <p className="text-sm font-medium text-[#6B7280] uppercase tracking-wide mb-4">Platform Health</p>
          <div className="grid grid-cols-3 gap-5">
            {[
              { value: `${allDoctors.length}`, sub: `${activeDoctors} active`, label: 'Doctors' },
              { value: `${totalPatients}`, sub: `${activePatients} active`, label: 'Patients' },
              { value: '93%', sub: 'this cycle', label: 'Subscription Renewal' },
            ].map(stat => (
              <div key={stat.label}>
                <p className="text-3xl font-bold text-[#111827] tabular-nums">{stat.value}</p>
                <p className="text-sm text-[#6B7280]">{stat.label}</p>
                <p className="text-xs text-[#9CA3AF] mt-0.5">{stat.sub}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="mb-5 space-y-2">
          {alerts.map(alert => (
            <div
              key={alert.id}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${
                alert.type === 'error'
                  ? 'bg-[#FEF2F2] border-[#FECACA]'
                  : 'bg-[#FFFBEB] border-[#FDE68A]'
              }`}
            >
              <AlertTriangle size={15} className={alert.type === 'error' ? 'text-[#DC2626]' : 'text-[#F59E0B]'} />
              <p className={`flex-1 text-sm ${alert.type === 'error' ? 'text-[#DC2626]' : 'text-[#B45309]'}`}>
                {alert.message}
              </p>
              <button
                onClick={() => navigate(alert.to)}
                className={`text-xs font-medium px-2.5 py-1 rounded border transition-colors ${
                  alert.type === 'error'
                    ? 'border-[#FECACA] text-[#DC2626] hover:bg-[#FEF2F2]'
                    : 'border-[#FDE68A] text-[#B45309] hover:bg-[#FFFBEB]'
                }`}
              >
                {alert.action}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Doctor Performance Table */}
      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
        <div className="px-5 py-4 border-b border-[#E5E7EB] flex items-center justify-between">
          <p className="text-base font-medium text-[#111827]">Doctor Performance</p>
          <button
            onClick={() => navigate('/admin/doctors')}
            className="flex items-center gap-1 text-xs text-[#1E7C45] hover:underline"
          >
            View all <ArrowRight size={12} />
          </button>
        </div>
        <table className="w-full">
          <thead>
            <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
              {['Doctor', 'Active Patients', 'Revenue', 'Codes Left', 'Billing', 'Action'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280]">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {allDoctors.map(doc => (
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
                      <p className="text-xs text-[#6B7280]">{doc.specialty}</p>
                    </div>
                  </div>
                </td>
                <td className="px-4 py-4 text-sm text-[#374151] tabular-nums">{doc.activePatients}</td>
                <td className="px-4 py-4 text-sm font-medium text-[#111827] tabular-nums">
                  ₹{doc.revenue.toLocaleString('en-IN')}
                </td>
                <td className="px-4 py-4">
                  <span className={`text-sm tabular-nums ${doc.codesRemaining <= 3 ? 'text-[#DC2626] font-medium' : 'text-[#374151]'}`}>
                    {doc.codesRemaining}
                    {doc.codesRemaining <= 3 && ' ⚠️'}
                  </span>
                </td>
                <td className="px-4 py-4">
                  <StatusBadge status={doc.billingStatus} />
                </td>
                <td className="px-4 py-4">
                  <button
                    onClick={() => navigate('/admin/doctors')}
                    className="h-7 px-2.5 rounded border border-[#D1D5DB] text-xs text-[#374151] hover:border-[#1E7C45] hover:text-[#1E7C45] transition-colors"
                  >
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
