import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { CheckCircle, XCircle, ClipboardCheck, Loader2 } from 'lucide-react';
import { adminApi, DataChangeRequestView } from '../../../lib/adminApi';

type ReqTab = 'pending' | 'approved' | 'rejected';

export function DataReview() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<ReqTab>('pending');
  const [rejectId, setRejectId] = useState<number | null>(null);
  const [rejectNote, setRejectNote] = useState('');

  const { data: reqs = [], isLoading } = useQuery({
    queryKey: ['admin', 'data-requests', tab],
    queryFn: () => adminApi.listDataRequests({ status: tab, page_size: 100 }),
    staleTime: 30_000,
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ['admin', 'data-requests'] });

  const approve = useMutation({
    mutationFn: (id: number) => adminApi.reviewDataRequest(id, { action: 'approve' }),
    onSuccess: () => { invalidate(); toast.success('Request approved'); },
    onError: () => toast.error('Failed to approve'),
  });
  const reject = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason?: string }) =>
      adminApi.reviewDataRequest(id, { action: 'reject', admin_reason: reason }),
    onSuccess: () => { invalidate(); toast.success('Request rejected'); setRejectId(null); setRejectNote(''); },
    onError: () => toast.error('Failed to reject'),
  });

  const tabs: { id: ReqTab; label: string }[] = [
    { id: 'pending', label: 'Pending' },
    { id: 'approved', label: 'Approved' },
    { id: 'rejected', label: 'Rejected' },
  ];

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Data Review</h1>
        <p className="text-sm text-[#6B7280] mt-0.5">
          Dish conflicts & doctor-flagged corrections. Nothing here auto-applies — you decide.
        </p>
      </div>

      <div className="flex gap-0 border-b border-[#E5E7EB] mb-4">
        {tabs.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id ? 'border-[#1E7C45] text-[#1E7C45]' : 'border-transparent text-[#6B7280] hover:text-[#374151]'
            }`}>
            {t.label}
            {t.id === 'pending' && tab === 'pending' && reqs.length > 0 && (
              <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full text-[10px] font-semibold bg-[#DC2626] text-white">
                {reqs.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16"><Loader2 size={24} className="animate-spin text-[#1E7C45]" /></div>
      ) : reqs.length === 0 ? (
        <div className="bg-white border border-[#E5E7EB] rounded-lg py-16 flex flex-col items-center">
          <ClipboardCheck size={36} className="text-[#34B164] mb-3" />
          <p className="text-base font-medium text-[#374151]">Nothing {tab}</p>
          <p className="text-sm text-[#6B7280] mt-1">The {tab} review queue is empty.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {(reqs as DataChangeRequestView[]).map(r => {
            const suggested = r.new_value && typeof r.new_value === 'object'
              ? (r.new_value as any).suggested ?? (r.new_value as any).cal_per_serving
              : null;
            const doctorFlag = !r.proposed_by.startsWith('system:');
            return (
              <div key={r.id} className="bg-white border border-[#E5E7EB] rounded-lg p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <p className="text-sm font-medium text-[#111827]">
                        {r.target?.recipe_name ?? `${r.target_table} #${r.target_id}`}
                      </p>
                      <span className="px-2 py-0.5 rounded-full text-[11px] bg-[#F3F4F6] text-[#6B7280]">
                        field: {r.field_changed}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-[11px] ${
                        doctorFlag ? 'bg-[#EFF6FF] text-[#1D4ED8] border border-[#BFDBFE]'
                                   : 'bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]'}`}>
                        {doctorFlag ? `doctor #${r.proposed_by}` : r.proposed_by.replace('system:', 'auto: ')}
                      </span>
                    </div>
                    <p className="text-xs text-[#374151] mb-2">{r.proposal_reason}</p>
                    <div className="flex items-center gap-3 text-xs text-[#6B7280]">
                      {r.target && <span>current: <span className="font-medium text-[#374151]">{Math.round(r.target.cal_per_serving)} kcal</span></span>}
                      {suggested != null && <span>proposed: <span className="font-medium text-[#374151]">{String(suggested)}</span></span>}
                      {r.target && <span className={r.target.is_verified ? 'text-[#15803d]' : 'text-[#B45309]'}>
                        {r.target.is_verified ? 'in pool' : 'parked'}
                      </span>}
                    </div>
                  </div>
                  {tab === 'pending' && (
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <button onClick={() => approve.mutate(r.id)} disabled={approve.isPending}
                        className="flex items-center gap-1.5 h-8 px-3 rounded-md bg-[#1E7C45] text-white text-xs hover:bg-[#166534] disabled:opacity-50 transition-colors">
                        <CheckCircle size={13} /> Approve
                      </button>
                      <button onClick={() => { setRejectId(r.id); setRejectNote(''); }}
                        className="flex items-center gap-1.5 h-8 px-3 rounded-md border border-[#FECACA] text-[#DC2626] text-xs hover:bg-[#FEF2F2] transition-colors">
                        <XCircle size={13} /> Reject
                      </button>
                    </div>
                  )}
                  {tab !== 'pending' && (
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${
                      r.status === 'approved' ? 'bg-[#DCFCE7] text-[#15803d]' : 'bg-[#FEE2E2] text-[#DC2626]'}`}>
                      {r.status}
                    </span>
                  )}
                </div>
                {rejectId === r.id && (
                  <div className="mt-3 pt-3 border-t border-[#F3F4F6]">
                    <div className="flex gap-2">
                      <input value={rejectNote} onChange={e => setRejectNote(e.target.value)}
                        placeholder="Reason (optional)"
                        className="flex-1 h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#DC2626]" />
                      <button onClick={() => reject.mutate({ id: r.id, reason: rejectNote || undefined })}
                        disabled={reject.isPending}
                        className="h-9 px-3 rounded-md bg-[#DC2626] text-white text-sm hover:bg-[#B91C1C] disabled:opacity-50">
                        {reject.isPending ? <Loader2 size={14} className="animate-spin" /> : 'Confirm'}
                      </button>
                      <button onClick={() => { setRejectId(null); setRejectNote(''); }}
                        className="h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#374151] hover:bg-[#F9FAFB]">
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
