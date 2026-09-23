import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { CheckCircle, XCircle, Bell, Mail, Clock, Loader2, AlertCircle } from 'lucide-react';
import { doctorApi } from '../../../lib/doctorApi';
import { qk } from '../../../lib/queryKeys';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';

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
          <h1 data-tour="tour-requests" className="text-2xl font-semibold text-foreground tracking-tight">Patient Requests</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {isLoading ? 'Loading…' : `${requests.length} pending`}
          </p>
        </div>
      </div>

      {/* Pending requests */}
      {isLoading ? (
        <Card className="py-16 flex justify-center">
          <Loader2 size={20} className="animate-spin text-primary" />
        </Card>
      ) : isError ? (
        <Card className="py-16 flex flex-col items-center text-center">
          <AlertCircle size={20} className="text-destructive mb-3" />
          <p className="text-base font-medium text-secondary-foreground">Could not load requests</p>
        </Card>
      ) : requests.length === 0 ? (
        <Card className="py-16 text-center mb-6">
          <Bell size={20} className="text-muted-foreground mx-auto mb-3" />
          <p className="text-base font-medium text-secondary-foreground">No pending requests</p>
          <p className="text-sm text-muted-foreground mt-1">New patient requests will appear here</p>
        </Card>
      ) : (
        <div className="space-y-4">
          {requests.map(req => (
            <Card key={req.id} className="p-5">
              {/* Header */}
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-brand-50 flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-semibold text-primary">
                      {req.patient.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <p className="text-base font-medium text-foreground">{req.patient.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {req.patient.gender} · {req.patient.email}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <StatusBadge status="pending" />
                  <span className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock size={14} /> {formatDate(req.requested_at)}
                  </span>
                </div>
              </div>

              {/* Contact */}
              <div className="flex flex-wrap gap-4 mb-3 text-sm text-secondary-foreground">
                <span className="flex items-center gap-1.5">
                  <Mail size={14} className="text-muted-foreground" />
                  {req.patient.email}
                </span>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-3">
                <Button
                  variant="primary"
                  size="md"
                  onClick={() => handleAction(req.id, req.patient.name, 'accept')}
                  disabled={isMutating}
                >
                  <CheckCircle size={16} />
                  Accept
                </Button>
                <Button
                  variant="destructive"
                  size="md"
                  onClick={() => setRejectOpen(rejectOpen === req.id ? null : req.id)}
                  disabled={isMutating}
                >
                  <XCircle size={16} />
                  Reject
                </Button>
              </div>

              {/* Inline reject note */}
              {rejectOpen === req.id && (
                <div className="mt-3 pt-3 border-t border-border">
                  <p className="text-xs text-muted-foreground mb-1.5">
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
                      className="flex-1 h-9 px-3 rounded-md border border-border bg-input-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-destructive focus:border-transparent"
                    />
                    <Button
                      variant="destructive"
                      size="md"
                      onClick={() => handleAction(req.id, req.patient.name, 'reject')}
                      disabled={isMutating}
                    >
                      {rejectMutation.isPending ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        'Confirm Reject'
                      )}
                    </Button>
                  </div>
                </div>
              )}
            </Card>
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
