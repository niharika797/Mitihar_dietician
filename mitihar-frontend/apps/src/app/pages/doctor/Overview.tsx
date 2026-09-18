import React, { useState } from 'react';
import { useNavigate } from 'react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Users, Bell, BarChart2, AlertCircle, Clock, UserPlus, Key, ArrowRight, TrendingUp, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { doctorApi } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
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
        <Loader2 size={20} className="animate-spin text-primary" />
      </div>
    );
  }

  if (dashError || !dash) {
    return (
      <div className="p-6 flex flex-col items-center justify-center min-h-[400px]">
        <AlertCircle size={20} className="text-destructive mb-3" />
        <p className="text-base font-medium text-secondary-foreground">Could not load dashboard</p>
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: qk.dashboard() })}
          className="mt-3 text-sm text-primary hover:underline"
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
          <h1 data-tour="tour-overview" className="text-2xl font-semibold text-foreground tracking-tight">
            Good morning, Dr. {doctorName.split(' ').pop()} 👋
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">{dayName}, {dateStr}</p>
        </div>
      </div>

      {/* Top row: stat cards + quick actions */}
      <div className="grid grid-cols-12 gap-5 mb-6">
        <div className="col-span-12 lg:col-span-8 grid grid-cols-3 gap-4">
          <StatCard icon={<Users size={18} className="text-primary" />} value={dash.active_patients} label="Active Patients" />
          <StatCard icon={<Bell size={18} className="text-blue-600" />} value={dash.pending_requests} label="Pending Requests" />
          <StatCard icon={<BarChart2 size={18} className="text-amber-500" />} value={dash.plans_generated_this_week} label="Plans This Week" />
        </div>

        {/* Quick Actions */}
        <Card className="col-span-12 lg:col-span-4 p-5">
          <p className="text-base font-medium text-foreground mb-3">Quick Actions</p>
          <div className="flex flex-col gap-2">
            <Button variant="primary" size="md" onClick={() => navigate('/doctor/requests')} className="justify-start">
              <UserPlus size={16} />
              Accept Patient Request
            </Button>
            <Button variant="outline" size="md" onClick={() => navigate('/doctor/settings?tab=codes')} className="justify-start">
              <Key size={16} />
              Manage Codes
            </Button>
            <Button variant="outline" size="md" onClick={() => navigate('/doctor/recipes')} className="justify-start">
              <ArrowRight size={16} />
              Browse Recipes
            </Button>
          </div>
        </Card>
      </div>

      {/* Bottom row: needs attention + pending requests */}
      <div className="grid grid-cols-12 gap-5">
        {/* Needs Attention — 60% */}
        <Card className="col-span-12 lg:col-span-7 overflow-hidden">
          <div className="px-5 pt-4 pb-0 flex items-center justify-between">
            <p className="text-base font-medium text-foreground">Needs Attention</p>
            <button
              onClick={() => navigate('/doctor/patients')}
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              View all patients <ArrowRight size={14} />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-0 px-5 mt-3 border-b border-border">
            {[
              { id: 'noActivity' as const, label: 'No Activity', count: dash.inactive_patients.length, color: 'bg-red-50 text-destructive' },
              { id: 'expiring' as const, label: 'Expiring Soon', count: dash.expiring_soon.length, color: 'bg-amber-50 text-amber-700' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setAttentionTab(tab.id)}
                className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
                  attentionTab === tab.id
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-secondary-foreground'
                }`}
              >
                {tab.label}
                <span className={`inline-flex items-center justify-center w-4 h-4 rounded-full ${tab.color} text-[10px] font-semibold`}>
                  {tab.count}
                </span>
              </button>
            ))}
          </div>

          <div className="divide-y divide-border">
            {attentionTab === 'noActivity' ? (
              dash.inactive_patients.length === 0 ? (
                <div className="py-8 text-center">
                  <CheckCircle size={20} className="text-brand-400 mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">All patients are active — no attention needed.</p>
                </div>
              ) : (
                dash.inactive_patients.map(p => (
                  <div key={p.patient_id} className="flex items-center gap-3 px-5 py-3.5 hover:bg-input-background transition-colors">
                    <span className="w-2 h-2 rounded-full bg-destructive flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground">{p.name}</p>
                      <p className="text-xs text-muted-foreground">{p.email}</p>
                    </div>
                    <button
                      onClick={() => navigate(`/doctor/patients/${p.patient_id}`)}
                      className="flex items-center gap-1 text-xs text-primary font-medium hover:underline flex-shrink-0"
                    >
                      View <ArrowRight size={14} />
                    </button>
                  </div>
                ))
              )
            ) : (
              dash.expiring_soon.length === 0 ? (
                <div className="py-8 text-center">
                  <CheckCircle size={20} className="text-brand-400 mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">No plans expiring soon.</p>
                </div>
              ) : (
                dash.expiring_soon.map(p => (
                  <div key={p.patient_id} className="flex items-center gap-3 px-5 py-3.5 hover:bg-input-background transition-colors">
                    <span className="w-2 h-2 rounded-full bg-amber-500 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground">{p.name}</p>
                      <p className="text-xs text-muted-foreground">Expires {p.subscription_end_date}</p>
                    </div>
                    <button
                      onClick={() => navigate(`/doctor/patients/${p.patient_id}`)}
                      className="flex items-center gap-1 text-xs text-primary font-medium hover:underline flex-shrink-0"
                    >
                      View <ArrowRight size={14} />
                    </button>
                  </div>
                ))
              )
            )}
          </div>
        </Card>

        {/* Pending Requests — 40% */}
        <Card className="col-span-12 lg:col-span-5 overflow-hidden">
          <div className="px-5 pt-4 pb-3 flex items-center justify-between border-b border-border">
            <p className="text-base font-medium text-foreground">Pending Requests</p>
            <button
              onClick={() => navigate('/doctor/requests')}
              className="text-xs text-primary hover:underline flex items-center gap-1"
            >
              View all <ArrowRight size={14} />
            </button>
          </div>

          <div className="divide-y divide-border">
            {reqLoading ? (
              <div className="py-10 flex justify-center">
                <Loader2 size={20} className="animate-spin text-primary" />
              </div>
            ) : pendingRequests.length === 0 ? (
              <div className="py-10 text-center px-6">
                <Bell size={20} className="text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">No pending requests</p>
                <p className="text-xs text-muted-foreground mt-1">New requests will appear here</p>
              </div>
            ) : (
              pendingRequests.slice(0, 4).map(req => (
                <div key={req.id} className="px-5 py-3.5">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <p className="text-sm font-medium text-foreground">{req.patient.name}</p>
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock size={14} />
                        {new Date(req.requested_at).toLocaleDateString('en-IN')}
                      </p>
                    </div>
                    <StatusBadge status="pending" />
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleRequestAction(req.id, req.patient.name, 'accept')}
                      disabled={acceptMutation.isPending || rejectMutation.isPending}
                    >
                      <CheckCircle size={14} />
                      Accept
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleRequestAction(req.id, req.patient.name, 'reject')}
                      disabled={acceptMutation.isPending || rejectMutation.isPending}
                    >
                      <XCircle size={14} />
                      Reject
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
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
    <Card className="p-5">
      <div className="flex items-start justify-between mb-3">
        <div className="w-10 h-10 rounded-full bg-brand-50 flex items-center justify-center">
          {icon}
        </div>
      </div>
      <p className="text-3xl font-bold text-foreground tabular-nums">{value}</p>
      <p className="text-sm text-muted-foreground mt-0.5">{label}</p>
    </Card>
  );
}
