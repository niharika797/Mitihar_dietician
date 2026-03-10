import React from 'react';
import { useNavigate } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp, ArrowRight, Users, Stethoscope,
  ClipboardList, Activity, Loader2, AlertTriangle,
} from 'lucide-react';
import { adminApi, DoctorAdminView } from '../../../lib/adminApi';
import { aqk } from '../../../lib/queryKeys';

function StatCard({
  label, value, sub, icon, accent = false,
}: { label: string; value: string | number; sub?: string; icon: React.ReactNode; accent?: boolean }) {
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg p-6 flex items-start gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${accent ? 'bg-[#F0FDF4]' : 'bg-[#F9FAFB]'}`}>
        <span className={accent ? 'text-[#1E7C45]' : 'text-[#6B7280]'}>{icon}</span>
      </div>
      <div>
        <p className="text-xs text-[#9CA3AF] uppercase tracking-wide mb-1">{label}</p>
        <p className="text-3xl font-bold text-[#111827] tabular-nums leading-none">{value}</p>
        {sub && <p className="text-xs text-[#6B7280] mt-1">{sub}</p>}
      </div>
    </div>
  );
}

function DoctorInitials({ name }: { name: string }) {
  const parts = name.split(' ');
  const initials = parts.length >= 2
    ? (parts[parts.length - 2][0] + parts[parts.length - 1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
  return (
    <div className="w-8 h-8 rounded-full bg-[#F0FDF4] flex items-center justify-center flex-shrink-0">
      <span className="text-xs font-semibold text-[#1E7C45]">{initials}</span>
    </div>
  );
}

export function AdminOverview() {
  const navigate = useNavigate();

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: aqk.stats(),
    queryFn: adminApi.getStats,
    staleTime: 60_000,
  });

  const { data: doctors = [], isLoading: doctorsLoading } = useQuery({
    queryKey: aqk.doctors(),
    queryFn: adminApi.listDoctors,
    staleTime: 60_000,
  });

  const { data: pendingFood = [] } = useQuery({
    queryKey: aqk.pendingFood(),
    queryFn: () => adminApi.listFood({ source: 'doctor', is_verified: false, page_size: 100 }),
    staleTime: 60_000,
  });

  const today = new Date();
  const monthYear = today.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' });

  const isLoading = statsLoading || doctorsLoading;

  // Alerts derived from real data
  const alerts: { id: string; type: 'error' | 'warning'; message: string; action: string; to: string }[] = [];
  if (pendingFood.length > 0) {
    alerts.push({
      id: 'food',
      type: 'warning',
      message: `${pendingFood.length} food item${pendingFood.length > 1 ? 's' : ''} pending approval`,
      action: 'Review',
      to: '/admin/food-database',
    });
  }

  return (
    <div className="p-6 max-w-[1400px]">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">{monthYear} · Admin Dashboard</h1>
        <p className="text-sm text-[#6B7280] mt-0.5">Platform-wide overview and health metrics</p>
      </div>

      {/* Stats grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <Loader2 size={24} className="animate-spin text-[#1E7C45]" />
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard
            label="Total Patients"
            value={stats?.total_patients ?? 0}
            sub={`${stats?.active_subscriptions ?? 0} active subscriptions`}
            icon={<Users size={18} />}
            accent
          />
          <StatCard
            label="Total Doctors"
            value={stats?.total_doctors ?? 0}
            sub={`${doctors.filter(d => d.is_active).length} active`}
            icon={<Stethoscope size={18} />}
          />
          <StatCard
            label="Active Subscriptions"
            value={stats?.active_subscriptions ?? 0}
            sub="currently active"
            icon={<Activity size={18} />}
            accent
          />
          <StatCard
            label="Active Plans"
            value={stats?.total_plans_generated ?? 0}
            sub="meal plans in use"
            icon={<ClipboardList size={18} />}
          />
        </div>
      )}

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="mb-5 space-y-2">
          {alerts.map(alert => (
            <div
              key={alert.id}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg border ${
                alert.type === 'error' ? 'bg-[#FEF2F2] border-[#FECACA]' : 'bg-[#FFFBEB] border-[#FDE68A]'
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

      {/* Doctor table */}
      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
        <div className="px-5 py-4 border-b border-[#E5E7EB] flex items-center justify-between">
          <p className="text-base font-medium text-[#111827]">Registered Doctors</p>
          <button
            onClick={() => navigate('/admin/doctors')}
            className="flex items-center gap-1 text-xs text-[#1E7C45] hover:underline"
          >
            View all <ArrowRight size={12} />
          </button>
        </div>

        {doctorsLoading ? (
          <div className="py-10 flex justify-center">
            <Loader2 size={20} className="animate-spin text-[#1E7C45]" />
          </div>
        ) : doctors.length === 0 ? (
          <div className="py-12 flex flex-col items-center">
            <Stethoscope size={28} className="text-[#D1D5DB] mb-2" />
            <p className="text-sm text-[#9CA3AF]">No doctors onboarded yet</p>
          </div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                {['Doctor', 'Specialization', 'City', 'Status'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(doctors as DoctorAdminView[]).slice(0, 8).map(doc => (
                <tr key={doc.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-2.5">
                      <DoctorInitials name={doc.name} />
                      <div>
                        <p className="text-sm font-medium text-[#111827]">{doc.name}</p>
                        <p className="text-xs text-[#6B7280]">{doc.email}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-sm text-[#374151]">{doc.specialization ?? '—'}</td>
                  <td className="px-4 py-4 text-sm text-[#374151]">{doc.city ?? '—'}</td>
                  <td className="px-4 py-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                      doc.is_active ? 'bg-[#DCFCE7] text-[#15803d]' : 'bg-[#F3F4F6] text-[#6B7280]'
                    }`}>
                      {doc.is_active ? 'Active' : 'Inactive'}
                    </span>
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
