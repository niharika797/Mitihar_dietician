import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Search, CheckCircle, XCircle, Utensils, Loader2 } from 'lucide-react';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { adminApi, FoodAdminView } from '../../../lib/adminApi';
import { aqk } from '../../../lib/queryKeys';

type FoodTab = 'pending' | 'all' | 'rejected';

export function FoodDatabase() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<FoodTab>('pending');
  const [search, setSearch] = useState('');
  const [rejectOpenId, setRejectOpenId] = useState<number | null>(null);
  const [rejectNote, setRejectNote] = useState('');
  const [confirmApproveId, setConfirmApproveId] = useState<number | null>(null);

  // Query params by tab
  const queryParams =
    tab === 'pending'  ? { source: 'doctor', is_verified: false } :
    tab === 'rejected' ? { source: 'rejected' } :
    {};

  const { data: items = [], isLoading, refetch } = useQuery({
    queryKey: aqk.food(queryParams),
    queryFn: () => adminApi.listFood({ ...queryParams, page_size: 100 }),
    staleTime: 30_000,
  });

  // Also fetch pending count for badge (always)
  const { data: pendingItems = [] } = useQuery({
    queryKey: aqk.pendingFood(),
    queryFn: () => adminApi.listFood({ source: 'doctor', is_verified: false, page_size: 100 }),
    staleTime: 30_000,
  });

  const approveMutation = useMutation({
    mutationFn: adminApi.approveFood,
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'food'] });
      const item = items.find((i: FoodAdminView) => i.id === id);
      toast.success(`"${item?.recipe_name ?? 'Item'}" approved`);
      setConfirmApproveId(null);
    },
    onError: () => toast.error('Failed to approve'),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason?: string }) =>
      adminApi.rejectFood(id, reason),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'food'] });
      const item = items.find((i: FoodAdminView) => i.id === id);
      toast.success(`"${item?.recipe_name ?? 'Item'}" rejected`);
      setRejectOpenId(null);
      setRejectNote('');
    },
    onError: () => toast.error('Failed to reject'),
  });

  const displayed = items.filter((i: FoodAdminView) =>
    i.recipe_name.toLowerCase().includes(search.toLowerCase()) ||
    i.diet_type.toLowerCase().includes(search.toLowerCase())
  );

  const tabs: { id: FoodTab; label: string; count?: number }[] = [
    { id: 'pending',  label: 'Pending Approval', count: pendingItems.length },
    { id: 'all',      label: 'All Items' },
    { id: 'rejected', label: 'Rejected' },
  ];

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Food Database</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">Manage and moderate food items</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-[#E5E7EB] mb-4">
        {tabs.map(t => (
          <button key={t.id} onClick={() => { setTab(t.id); setSearch(''); }}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id ? 'border-[#1E7C45] text-[#1E7C45]' : 'border-transparent text-[#6B7280] hover:text-[#374151]'
            }`}>
            {t.label}
            {t.count != null && (
              <span className={`inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full text-[10px] font-semibold ${
                t.id === 'pending' && t.count > 0 ? 'bg-[#DC2626] text-white' : 'bg-[#F3F4F6] text-[#6B7280]'
              }`}>
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative w-64 mb-4">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search food items..."
          className="w-full h-9 pl-9 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 size={24} className="animate-spin text-[#1E7C45]" />
        </div>
      ) : tab === 'pending' ? (
        /* ── Pending: card + inline approve/reject ── */
        displayed.length === 0 ? (
          <div className="bg-white border border-[#E5E7EB] rounded-lg py-16 flex flex-col items-center">
            <CheckCircle size={36} className="text-[#34B164] mb-3" />
            <p className="text-base font-medium text-[#374151]">All caught up!</p>
            <p className="text-sm text-[#6B7280] mt-1">No food items pending approval</p>
          </div>
        ) : (
          <div className="space-y-3">
            {(displayed as FoodAdminView[]).map(item => (
              <div key={item.id} className="bg-white border border-[#E5E7EB] rounded-lg p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-sm font-medium text-[#111827]">{item.recipe_name}</p>
                      <span className="px-2 py-0.5 rounded-full text-[11px] bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]">
                        {item.slot_type}
                      </span>
                      <span className="px-2 py-0.5 rounded-full text-[11px] bg-[#F3F4F6] text-[#6B7280]">
                        {item.diet_type}
                      </span>
                    </div>
                    <p className="text-xs text-[#6B7280] mb-2">
                      Source: {item.source} · Added {new Date(item.created_at).toLocaleDateString('en-IN')}
                    </p>
                    <p className="text-xs text-[#374151]">
                      <span className="font-medium">{Math.round(item.cal_per_serving)}</span> kcal / serving
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => setConfirmApproveId(item.id)}
                      className="flex items-center gap-1.5 h-8 px-3 rounded-md bg-[#1E7C45] text-white text-xs hover:bg-[#166534] transition-colors"
                    >
                      <CheckCircle size={13} /> Approve
                    </button>
                    <button
                      onClick={() => { setRejectOpenId(item.id); setRejectNote(''); }}
                      className="flex items-center gap-1.5 h-8 px-3 rounded-md border border-[#FECACA] text-[#DC2626] text-xs hover:bg-[#FEF2F2] transition-colors"
                    >
                      <XCircle size={13} /> Reject
                    </button>
                  </div>
                </div>
                {/* Inline reject form */}
                {rejectOpenId === item.id && (
                  <div className="mt-3 pt-3 border-t border-[#F3F4F6]">
                    <label className="block text-xs text-[#6B7280] mb-1.5">
                      Rejection reason (optional):
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={rejectNote}
                        onChange={e => setRejectNote(e.target.value)}
                        placeholder="e.g. Nutritional values unverified"
                        autoFocus
                        className="flex-1 h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#DC2626]"
                      />
                      <button
                        onClick={() => rejectMutation.mutate({ id: item.id, reason: rejectNote || undefined })}
                        disabled={rejectMutation.isPending}
                        className="h-9 px-3 rounded-md bg-[#DC2626] text-white text-sm hover:bg-[#B91C1C] disabled:opacity-50 transition-colors"
                      >
                        {rejectMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : 'Confirm'}
                      </button>
                      <button
                        onClick={() => { setRejectOpenId(null); setRejectNote(''); }}
                        className="h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#374151] hover:bg-[#F9FAFB]"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )
      ) : (
        /* ── All / Rejected: table ── */
        <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
          {displayed.length === 0 ? (
            <div className="py-16 flex flex-col items-center">
              <Utensils size={32} className="text-[#D1D5DB] mb-3" />
              <p className="text-base font-medium text-[#374151]">No items found</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                  {['Name', 'Slot Type', 'Diet Type', 'Calories', 'Source', 'Verified', 'Added'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(displayed as FoodAdminView[]).map(item => (
                  <tr key={item.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-[#111827]">{item.recipe_name}</td>
                    <td className="px-4 py-3 text-sm text-[#6B7280]">{item.slot_type}</td>
                    <td className="px-4 py-3 text-sm text-[#6B7280]">{item.diet_type}</td>
                    <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">{Math.round(item.cal_per_serving)} kcal</td>
                    <td className="px-4 py-3 text-sm text-[#6B7280] capitalize">{item.source}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                        item.is_verified ? 'bg-[#DCFCE7] text-[#15803d]' : 'bg-[#FEF3C7] text-[#B45309]'
                      }`}>
                        {item.is_verified ? 'Verified' : 'Unverified'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-[#9CA3AF] tabular-nums whitespace-nowrap">
                      {new Date(item.created_at).toLocaleDateString('en-IN')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Approve confirm dialog */}
      <ConfirmDialog
        open={confirmApproveId !== null}
        title="Approve Food Item?"
        description={`"${items.find((i: FoodAdminView) => i.id === confirmApproveId)?.recipe_name ?? ''}" will be added to the food database and available for meal plans.`}
        confirmLabel="Approve"
        onConfirm={() => confirmApproveId && approveMutation.mutate(confirmApproveId)}
        onCancel={() => setConfirmApproveId(null)}
      />
    </div>
  );
}
