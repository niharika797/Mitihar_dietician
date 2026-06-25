import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Users, Bell, BarChart2, AlertCircle, Clock, UserPlus, Key, ArrowRight, TrendingUp, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { doctorApi } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { useAuthStore } from '../../../stores/authStore';

export function DoctorOverview() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const doctorName = useAuthStore(s => s.user_name) ?? 'Doctor';
  const [attentionTab, setAttentionTab] = useState<'noActivity' | 'expiring'>('noActivity');
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean; reqId: number; action: 'accept' | 'reject'; name: string;
  }>({ open: false, reqId: 0, action: 'accept', name: '' });

  const today = new Date();
  const dayName = today.toLocaleDateString('en-IN', { weekday: 'long' });
  const dateStr = today.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });

  // ── Queries ──────────────────────────────────────────────────────────────
  const { data: dash, isLoading: dashLoading, isError: dashError } = useQuery({
    queryKey: qk.dashboard(),
    queryFn: doctorApi.getDashboard,
  });

  const { data: requests = [], isLoading: reqLoading } = useQuery({
    queryKey: qk.requests(),
    queryFn: doctorApi.listRequests,
  });

  // ── Mutations ────────────────────────────────────────────────────────────
  const acceptMutation = useMutation({
    mutationFn: (id: number) => doctorApi.acceptRequest(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.requests() });
      queryClient.invalidateQueries({ queryKey: qk.dashboard() });
      toast.success(`Patient request accepted`);
    },
    onError: () => toast.error('Failed to accept request'),
  });

  const rejectMutation = useMutation({
    mutationFn: (id: number) => doctorApi.rejectRequest(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.requests() });
      queryClient.invalidateQueries({ queryKey: qk.dashboard() });
      toast.success('Request rejected');
    },
    onError: () => toast.error('Failed to reject request'),
  });

  const handleRequestAction = (reqId: number, name: string, action: 'accept' | 'reject') => {
    setConfirmDialog({ open: true, reqId, action, name });
  };

  const confirmAction = () => {
    if (confirmDialog.action === 'accept') {
      acceptMutation.mutate(confirmDialog.reqId);
    } else {
      rejectMutation.mutate(confirmDialog.reqId);
    }
    setConfirmDialog({ open: false, reqId: 0, action: 'accept', name: '' });
  };

  // ── Loading / Error ──────────────────────────────────────────────────────
  if (dashLoading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-[400px]">
        <Loader2 size={28} className="animate-spin text-[#1E7C45]" />
      </div>
    );
  }

  if (dashError || !dash) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
        <AlertCircle size={36} className="text-[#DC2626] mb-3" />
        <p className="text-base font-medium text-[#374151]">Could not load dashboard</p>
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: qk.dashboard() })}
          className="mt-3 text-sm text-[#1E7C45] hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  const pendingRequests = requests.filter(r => r.status === 'pending');

  return (
    <div className="p-6 max-w-[1400px]">
      {/* Greeting */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">
            Good morning, Dr. {doctorName.split(' ').pop()} 👋
          </h1>
          <p className="text-sm text-[#6B7280] mt-0.5">{dayName}, {dateStr}</p>
        </div>
      </div>

      {/* Top row: stat cards + quick actions */}
      <div className="grid grid-cols-12 gap-5 mb-6">
        <div className="col-span-12 lg:col-span-8 grid grid-cols-3 gap-4">
          <StatCard icon={<Users size={18} className="text-[#1E7C45]" />} value={dash.active_patients} label="Active Patients" />
          <StatCard icon={<Bell size={18} className="text-[#2563EB]" />} value={dash.pending_requests} label="Pending Requests" />
          <StatCard icon={<BarChart2 size={18} className="text-[#F59E0B]" />} value={dash.plans_generated_this_week} label="Plans This Week" />
        </div>

        {/* Quick Actions */}
        <div className="col-span-12 lg:col-span-4 bg-white border border-[#E5E7EB] rounded-lg p-5">
          <p className="text-base font-medium text-[#111827] mb-3">Quick Actions</p>
          <div className="flex flex-col gap-2">
            <button
              onClick={() => navigate('/doctor/requests')}
              className="flex items-center gap-2.5 h-9 px-3 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors"
            >
              <UserPlus size={15} />
              Accept Patient Request
            </button>
            <button
              onClick={() => navigate('/doctor/settings?tab=codes')}
              className="flex items-center gap-2.5 h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-[#374151] text-sm hover:bg-[#F9FAFB] transition-colors"
            >
              <Key size={15} />
              Manage Codes
            </button>
            <button
              onClick={() => navigate('/doctor/recipes')}
              className="flex items-center gap-2.5 h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-[#374151] text-sm hover:bg-[#F9FAFB] transition-colors"
            >
              <ArrowRight size={15} />
              Browse Recipes
            </button>
          </div>
        </div>
      </div>

      {/* Bottom row: needs attention + pending requests */}
      <div className="grid grid-cols-12 gap-5">
        {/* Needs Attention — 60% */}
        <div className="col-span-12 lg:col-span-7 bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
          <div className="px-5 pt-4 pb-0 flex items-center justify-between">
            <p className="text-base font-medium text-[#111827]">Needs Attention</p>
            <button
              onClick={() => navigate('/doctor/patients')}
              className="text-xs text-[#1E7C45] hover:underline flex items-center gap-1"
            >
              View all patients <ArrowRight size={12} />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-0 px-5 mt-3 border-b border-[#E5E7EB]">
            {[
              { id: 'noActivity' as const, label: 'No Activity', count: dash.inactive_patients.length, color: 'bg-[#FEF2F2] text-[#DC2626]' },
              { id: 'expiring' as const, label: 'Expiring Soon', count: dash.expiring_soon.length, color: 'bg-[#FFFBEB] text-[#B45309]' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setAttentionTab(tab.id)}
                className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
                  attentionTab === tab.id
                    ? 'border-[#1E7C45] text-[#1E7C45]'
                    : 'border-transparent text-[#6B7280] hover:text-[#374151]'
                }`}
              >
                {tab.label}
                <span className={`inline-flex items-center justify-center w-4 h-4 rounded-full ${tab.color} text-[10px] font-semibold`}>
                  {tab.count}
                </span>
              </button>
            ))}
          </div>

          <div className="divide-y divide-[#F3F4F6]">
            {attentionTab === 'noActivity' ? (
              dash.inactive_patients.length === 0 ? (
                <div className="py-8 text-center">
                  <CheckCircle size={32} className="text-[#34B164] mx-auto mb-2" />
                  <p className="text-sm text-[#6B7280]">All patients are active — no attention needed.</p>
                </div>
              ) : (
                dash.inactive_patients.map(p => (
                  <div key={p.patient_id} className="flex items-center gap-3 px-5 py-3.5 hover:bg-[#F9FAFB] transition-colors">
                    <span className="w-2 h-2 rounded-full bg-[#DC2626] flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-[#111827]">{p.name}</p>
                      <p className="text-xs text-[#6B7280]">{p.email}</p>
                    </div>
                    <button
                      onClick={() => navigate(`/doctor/patients/${p.patient_id}`)}
                      className="flex items-center gap-1 text-xs text-[#1E7C45] font-medium hover:underline flex-shrink-0"
                    >
                      View <ArrowRight size={12} />
                    </button>
                  </div>
                ))
              )
            ) : (
              dash.expiring_soon.length === 0 ? (
                <div className="py-8 text-center">
                  <CheckCircle size={32} className="text-[#34B164] mx-auto mb-2" />
                  <p className="text-sm text-[#6B7280]">No plans expiring soon.</p>
                </div>
              ) : (
                dash.expiring_soon.map(p => (
                  <div key={p.patient_id} className="flex items-center gap-3 px-5 py-3.5 hover:bg-[#F9FAFB] transition-colors">
                    <span className="w-2 h-2 rounded-full bg-[#F59E0B] flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-[#111827]">{p.name}</p>
                      <p className="text-xs text-[#6B7280]">Expires {p.subscription_end_date}</p>
                    </div>
                    <button
                      onClick={() => navigate(`/doctor/patients/${p.patient_id}`)}
                      className="flex items-center gap-1 text-xs text-[#1E7C45] font-medium hover:underline flex-shrink-0"
                    >
                      View <ArrowRight size={12} />
                    </button>
                  </div>
                ))
              )
            )}
          </div>
        </div>

        {/* Pending Requests — 40% */}
        <div className="col-span-12 lg:col-span-5 bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
          <div className="px-5 pt-4 pb-3 flex items-center justify-between border-b border-[#E5E7EB]">
            <p className="text-base font-medium text-[#111827]">Pending Requests</p>
            <button
              onClick={() => navigate('/doctor/requests')}
              className="text-xs text-[#1E7C45] hover:underline flex items-center gap-1"
            >
              View all <ArrowRight size={12} />
            </button>
          </div>

          <div className="divide-y divide-[#F3F4F6]">
            {reqLoading ? (
              <div className="py-10 flex justify-center">
                <Loader2 size={20} className="animate-spin text-[#1E7C45]" />
              </div>
            ) : pendingRequests.length === 0 ? (
              <div className="py-10 text-center px-6">
                <Bell size={32} className="text-[#D1D5DB] mx-auto mb-2" />
                <p className="text-sm text-[#6B7280]">No pending requests</p>
                <p className="text-xs text-[#9CA3AF] mt-1">New requests will appear here</p>
              </div>
            ) : (
              pendingRequests.slice(0, 4).map(req => (
                <div key={req.id} className="px-5 py-3.5">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <p className="text-sm font-medium text-[#111827]">{req.patient.name}</p>
                      <p className="text-xs text-[#6B7280] flex items-center gap-1">
                        <Clock size={11} />
                        {new Date(req.requested_at).toLocaleDateString('en-IN')}
                      </p>
                    </div>
                    <StatusBadge status="pending" />
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleRequestAction(req.id, req.patient.name, 'accept')}
                      disabled={acceptMutation.isPending || rejectMutation.isPending}
                      className="flex items-center gap-1.5 h-7 px-3 rounded text-xs bg-[#1E7C45] text-white hover:bg-[#166534] transition-colors disabled:opacity-50"
                    >
                      <CheckCircle size={12} />
                      Accept
                    </button>
                    <button
                      onClick={() => handleRequestAction(req.id, req.patient.name, 'reject')}
                      disabled={acceptMutation.isPending || rejectMutation.isPending}
                      className="flex items-center gap-1.5 h-7 px-3 rounded text-xs border border-[#D1D5DB] text-[#DC2626] hover:bg-[#FEF2F2] transition-colors disabled:opacity-50"
                    >
                      <XCircle size={12} />
                      Reject
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={confirmDialog.open}
        title={confirmDialog.action === 'accept' ? 'Accept Patient Request?' : 'Reject Patient Request?'}
        description={
          confirmDialog.action === 'accept'
            ? `This will add ${confirmDialog.name} to your patient list.`
            : `${confirmDialog.name}'s request will be rejected. They will be notified.`
        }
        confirmLabel={confirmDialog.action === 'accept' ? 'Accept Request' : 'Reject Request'}
        variant={confirmDialog.action === 'reject' ? 'danger' : 'default'}
        onConfirm={confirmAction}
        onCancel={() => setConfirmDialog({ open: false, reqId: 0, action: 'accept', name: '' })}
      />
    </div>
  );
}

function StatCard({
  icon,
  value,
  label,
}: {
  icon: React.ReactNode;
  value: number;
  label: string;
}) {
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg p-5 shadow-[0_1px_3px_0_rgb(0_0_0/0.05)]">
      <div className="flex items-start justify-between mb-3">
        <div className="w-10 h-10 rounded-full bg-[#F0FDF4] flex items-center justify-center">
          {icon}
        </div>
      </div>
      <p className="text-3xl font-bold text-[#111827] tabular-nums">{value}</p>
      <p className="text-sm text-[#6B7280] mt-0.5">{label}</p>
    </div>
  );
}
