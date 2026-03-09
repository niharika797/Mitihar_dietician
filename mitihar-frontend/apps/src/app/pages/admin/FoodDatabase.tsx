import React, { useState } from 'react';
import { Search, CheckCircle, XCircle, Utensils } from 'lucide-react';
import { foodDatabase, FoodItem } from '../../data/mockData';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { toast } from 'sonner';

type FoodTab = 'all' | 'pending' | 'rejected';

export function FoodDatabase() {
  const [tab, setTab] = useState<FoodTab>('all');
  const [search, setSearch] = useState('');
  const [items, setItems] = useState<FoodItem[]>(foodDatabase);
  const [rejectDialogOpen, setRejectDialogOpen] = useState<string | null>(null);
  const [rejectNote, setRejectNote] = useState('');
  const [confirmApprove, setConfirmApprove] = useState<string | null>(null);

  const pendingItems = items.filter(i => i.status === 'pending');
  const rejectedItems = items.filter(i => i.status === 'rejected');

  const displayed = items
    .filter(i => {
      if (tab === 'pending') return i.status === 'pending';
      if (tab === 'rejected') return i.status === 'rejected';
      return true;
    })
    .filter(i =>
      i.name.toLowerCase().includes(search.toLowerCase()) ||
      i.category.toLowerCase().includes(search.toLowerCase())
    );

  const handleApprove = (id: string) => {
    setItems(prev => prev.map(i => i.id === id ? { ...i, status: 'approved' as const } : i));
    setConfirmApprove(null);
    const item = items.find(i => i.id === id);
    toast.success(`"${item?.name}" approved`);
  };

  const handleReject = (id: string) => {
    setItems(prev => prev.map(i => i.id === id
      ? { ...i, status: 'rejected' as const, rejectionReason: rejectNote || 'Rejected by admin' }
      : i
    ));
    setRejectDialogOpen(null);
    setRejectNote('');
    const item = items.find(i => i.id === id);
    toast.success(`"${item?.name}" rejected`);
  };

  const tabs: { id: FoodTab; label: string; count?: number }[] = [
    { id: 'all', label: 'All', count: items.length },
    { id: 'pending', label: 'Pending Approval', count: pendingItems.length },
    { id: 'rejected', label: 'Rejected', count: rejectedItems.length },
  ];

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Food Database</h1>
          <p className="text-sm text-[#6B7280] mt-0.5">{items.length} food items in database</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-[#E5E7EB] mb-4">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? 'border-[#1E7C45] text-[#1E7C45]'
                : 'border-transparent text-[#6B7280] hover:text-[#374151]'
            }`}
          >
            {t.label}
            {t.count != null && (
              <span className={`inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full text-[10px] font-semibold ${
                t.id === 'pending' && t.count > 0
                  ? 'bg-[#DC2626] text-white'
                  : 'bg-[#F3F4F6] text-[#6B7280]'
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
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search food items..."
          className="w-full h-9 pl-9 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45] focus:border-transparent"
        />
      </div>

      {/* Pending: inline approve/reject */}
      {tab === 'pending' && pendingItems.length > 0 && (
        <div className="space-y-3 mb-6">
          {pendingItems.filter(i => i.name.toLowerCase().includes(search.toLowerCase())).map(item => (
            <div key={item.id} className="bg-white border border-[#E5E7EB] rounded-lg p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-sm font-medium text-[#111827]">{item.name}</p>
                    <span className="px-2 py-0.5 rounded-full text-[11px] bg-[#FFFBEB] text-[#B45309] border border-[#FDE68A]">
                      {item.category}
                    </span>
                  </div>
                  <p className="text-xs text-[#6B7280] mb-2">Submitted by {item.submittedBy} · {item.submittedAt}</p>
                  <div className="flex items-center gap-4 text-xs text-[#6B7280]">
                    <span className="tabular-nums"><span className="font-medium text-[#111827]">{item.calories}</span> kcal</span>
                    <span className="tabular-nums">P: <span className="font-medium text-[#111827]">{item.protein}g</span></span>
                    <span className="tabular-nums">C: <span className="font-medium text-[#111827]">{item.carbs}g</span></span>
                    <span className="tabular-nums">F: <span className="font-medium text-[#111827]">{item.fat}g</span></span>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={() => setConfirmApprove(item.id)}
                    className="flex items-center gap-1.5 h-8 px-3 rounded-md bg-[#1E7C45] text-white text-xs hover:bg-[#166534] transition-colors"
                  >
                    <CheckCircle size={13} />
                    Approve
                  </button>
                  <button
                    onClick={() => setRejectDialogOpen(item.id)}
                    className="flex items-center gap-1.5 h-8 px-3 rounded-md border border-[#FECACA] text-[#DC2626] text-xs hover:bg-[#FEF2F2] transition-colors"
                  >
                    <XCircle size={13} />
                    Reject
                  </button>
                </div>
              </div>

              {/* Inline reject form */}
              {rejectDialogOpen === item.id && (
                <div className="mt-3 pt-3 border-t border-[#F3F4F6]">
                  <label className="block text-xs text-[#6B7280] mb-1.5">Rejection reason (will be sent to doctor):</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={rejectNote}
                      onChange={e => setRejectNote(e.target.value)}
                      placeholder="e.g. Nutritional values unverified"
                      autoFocus
                      className="flex-1 h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#DC2626] focus:border-transparent"
                    />
                    <button
                      onClick={() => handleReject(item.id)}
                      className="h-9 px-3 rounded-md bg-[#DC2626] text-white text-sm hover:bg-[#B91C1C] transition-colors"
                    >
                      Confirm
                    </button>
                    <button
                      onClick={() => { setRejectDialogOpen(null); setRejectNote(''); }}
                      className="h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm text-[#374151] hover:bg-[#F9FAFB] transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Table for all/rejected */}
      {tab !== 'pending' && (
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
                  {['Name', 'Category', 'Calories', 'Protein', 'Carbs', 'Fat', 'Submitted By', 'Status'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280]">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {displayed.map(item => (
                  <tr key={item.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-[#111827]">{item.name}</td>
                    <td className="px-4 py-3 text-sm text-[#6B7280]">{item.category}</td>
                    <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">{item.calories}</td>
                    <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">{item.protein}g</td>
                    <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">{item.carbs}g</td>
                    <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">{item.fat}g</td>
                    <td className="px-4 py-3 text-sm text-[#6B7280]">{item.submittedBy}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={item.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {tab === 'pending' && pendingItems.length === 0 && (
        <div className="bg-white border border-[#E5E7EB] rounded-lg py-16 flex flex-col items-center">
          <CheckCircle size={36} className="text-[#34B164] mb-3" />
          <p className="text-base font-medium text-[#374151]">All caught up!</p>
          <p className="text-sm text-[#6B7280] mt-1">No food items pending approval</p>
        </div>
      )}

      <ConfirmDialog
        open={confirmApprove !== null}
        title="Approve Food Item?"
        description={`"${items.find(i => i.id === confirmApprove)?.name}" will be added to the food database and available in patient plans.`}
        confirmLabel="Approve"
        onConfirm={() => confirmApprove && handleApprove(confirmApprove)}
        onCancel={() => setConfirmApprove(null)}
      />
    </div>
  );
}
