import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { CheckCircle, XCircle, Bell, Mail, Clock, Loader2, AlertCircle } from 'lucide-react';
import { doctorApi } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { StatusBadge } from '../../components/ui/StatusBadge';

export function Requests() {
  const queryClient = useQueryClient();
  const [rejectNote, setRejectNote] = useState<Record<number, string>>({});
  const [rejectOpen, setRejectOpen] = useState<number | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean; reqId: number; action: 'accept' | 'reject'; name: string;
  }>({ open: false, reqId: 0, action: 'accept', name: '' });

  const { data: requests = [], isLoading, isError } = useQuery({
    queryKey: qk.requests(),
    queryFn: doctorApi.listRequests,
  });

  const acceptMutation = useMutation({
    mutationFn: (id: number) => doctorApi.acceptRequest(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: qk.requests() });
      queryClient.invalidateQueries({ queryKey: qk.dashboard() });
      toast.success('Patient accepted — they have been added to your list');
    },
    onError: () => toast.error('Failed to accept request'),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, note }: { id: number; note?: string }) =>
      doctorApi.rejectRequest(id, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: qk.requests() });
      queryClient.invalidateQueries({ queryKey: qk.dashboard() });
      toast.success('Request rejected');
    },
    onError: () => toast.error('Failed to reject request'),
  });

  const handleAction = (reqId: number, name: string, action: 'accept' | 'reject') => {
    setConfirmDialog({ open: true, reqId, action, name });
  };

  const confirm = () => {
    if (confirmDialog.action === 'accept') {
      acceptMutation.mutate(confirmDialog.reqId);
    } else {
      rejectMutation.mutate({
        id: confirmDialog.reqId,
        note: rejectNote[confirmDialog.reqId],
      });
    }
    setConfirmDialog({ open: false, reqId: 0, action: 'accept', name: '' });
    setRejectOpen(null);
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString('en-IN', {
        day: 'numeric', month: 'short', year: 'numeric',
      });
    } catch {
      return iso;
    }
  };

  const isMutating = acceptMutation.isPending || rejectMutation.isPending;

  return (
    <div className="p-6 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Patient Requests</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">
            {isLoading ? 'Loading…' : `${requests.length} pending`}
          </p>
        </div>
      </div>

      {/* Pending requests */}
      {isLoading ? (
        <div className="bg-white border border-[#E5E7EB] rounded-lg py-16 flex justify-center">
          <Loader2 size={24} className="animate-spin text-[#1E7C45]" />
        </div>
      ) : isError ? (
        <div className="bg-white border border-[#E5E7EB] rounded-lg py-16 flex flex-col items-center text-center">
          <AlertCircle size={32} className="text-[#DC2626] mb-3" />
          <p className="text-base font-medium text-[#374151]">Could not load requests</p>
        </div>
      ) : requests.length === 0 ? (
        <div className="bg-white border border-[#E5E7EB] rounded-lg py-16 text-center mb-6">
          <Bell size={36} className="text-[#D1D5DB] mx-auto mb-3" />
          <p className="text-base font-medium text-[#374151]">No pending requests</p>
          <p className="text-sm text-[#6B7280] mt-1">New patient requests will appear here</p>
        </div>
      ) : (
        <div className="space-y-4">
          {requests.map(req => (
            <div key={req.id} className="bg-white border border-[#E5E7EB] rounded-lg p-5">
              {/* Header */}
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-[#F0FDF4] flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-semibold text-[#1E7C45]">
                      {req.patient.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <p className="text-base font-medium text-[#111827]">{req.patient.name}</p>
                    <p className="text-xs text-[#6B7280]">
                      {req.patient.gender} · {req.patient.email}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <StatusBadge status="pending" />
                  <span className="flex items-center gap-1 text-xs text-[#9CA3AF]">
                    <Clock size={11} /> {formatDate(req.requested_at)}
                  </span>
                </div>
              </div>

              {/* Contact */}
              <div className="flex flex-wrap gap-4 mb-3 text-sm text-[#374151]">
                <span className="flex items-center gap-1.5">
                  <Mail size={13} className="text-[#9CA3AF]" />
                  {req.patient.email}
                </span>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-3">
                <button
                  onClick={() => handleAction(req.id, req.patient.name, 'accept')}
                  disabled={isMutating}
                  className="flex items-center gap-2 h-9 px-4 rounded-md bg-[#1E7C45] text-white text-sm hover:bg-[#166534] transition-colors disabled:opacity-50"
                >
                  <CheckCircle size={15} />
                  Accept
                </button>
                <button
                  onClick={() => setRejectOpen(rejectOpen === req.id ? null : req.id)}
                  disabled={isMutating}
                  className="flex items-center gap-2 h-9 px-4 rounded-md border border-[#FECACA] text-[#DC2626] text-sm hover:bg-[#FEF2F2] transition-colors disabled:opacity-50"
                >
                  <XCircle size={15} />
                  Reject
                </button>
              </div>

              {/* Inline reject note */}
              {rejectOpen === req.id && (
                <div className="mt-3 pt-3 border-t border-[#F3F4F6]">
                  <p className="text-xs text-[#6B7280] mb-1.5">
                    Optional rejection note (sent to patient):
                  </p>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={rejectNote[req.id] ?? ''}
                      onChange={e =>
                        setRejectNote(prev => ({ ...prev, [req.id]: e.target.value }))
                      }
                      placeholder="e.g. Not accepting new patients at this time"
                      className="flex-1 h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#DC2626] focus:border-transparent"
                    />
                    <button
                      onClick={() => handleAction(req.id, req.patient.name, 'reject')}
                      disabled={isMutating}
                      className="h-9 px-3 rounded-md bg-[#DC2626] text-white text-sm hover:bg-[#B91C1C] transition-colors disabled:opacity-50"
                    >
                      {rejectMutation.isPending ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        'Confirm Reject'
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={confirmDialog.open}
        title={confirmDialog.action === 'accept' ? 'Accept Request?' : 'Reject Request?'}
        description={
          confirmDialog.action === 'accept'
            ? `This will add ${confirmDialog.name} to your patient list.`
            : `${confirmDialog.name}'s request will be rejected. They will be notified.`
        }
        confirmLabel={confirmDialog.action === 'accept' ? 'Accept' : 'Reject'}
        variant={confirmDialog.action === 'reject' ? 'danger' : 'default'}
        onConfirm={confirm}
        onCancel={() => setConfirmDialog({ open: false, reqId: 0, action: 'accept', name: '' })}
      />
    </div>
  );
}
