import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Search, Flag, Loader2, CheckCircle2 } from 'lucide-react';
import { doctorApi, DataReviewDish, MyFlag } from '../../../lib/doctorApi';

type Tab = 'dishes' | 'my-flags';

export function DataReview() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>('dishes');
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [flagId, setFlagId] = useState<number | null>(null);
  const [reason, setReason] = useState('');
  const [suggested, setSuggested] = useState('');

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  const { data: dishes = [], isLoading } = useQuery({
    queryKey: ['doctor', 'data-review', 'dishes', debounced],
    queryFn: () => doctorApi.dataReviewDishes(debounced || undefined),
    staleTime: 30_000,
  });
  const { data: flags = [] } = useQuery({
    queryKey: ['doctor', 'data-review', 'my-flags'],
    queryFn: doctorApi.myFlags,
    staleTime: 30_000,
  });

  const flag = useMutation({
    mutationFn: (body: { food_item_id: number; reason: string; suggested_value?: string }) =>
      doctorApi.flagDish(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['doctor', 'data-review', 'my-flags'] });
      toast.success('Flag submitted for admin review');
      setFlagId(null); setReason(''); setSuggested('');
    },
    onError: () => toast.error('Failed to submit flag'),
  });

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[#111827] tracking-tight">Data Review</h1>
        <p className="text-sm text-[#6B7280] mt-0.5">
          Spotted a wrong value in the shared dish database? Flag it for admin review. You can't edit shared data directly.
        </p>
      </div>

      <div className="flex gap-0 border-b border-[#E5E7EB] mb-4">
        {([['dishes', 'Browse Dishes'], ['my-flags', `My Flags${flags.length ? ` (${flags.length})` : ''}`]] as [Tab, string][]).map(([id, label]) => (
          <button key={id} onClick={() => setTab(id)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === id ? 'border-[#1E7C45] text-[#1E7C45]' : 'border-transparent text-[#6B7280] hover:text-[#374151]'
            }`}>{label}</button>
        ))}
      </div>

      {tab === 'dishes' ? (
        <>
          <div className="relative w-72 mb-4">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search dishes..."
              className="w-full h-9 pl-9 pr-3 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1E7C45]" />
          </div>
          {isLoading ? (
            <div className="flex justify-center py-16"><Loader2 size={24} className="animate-spin text-[#1E7C45]" /></div>
          ) : (
            <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                    {['Name', 'Slot', 'Diet', 'Calories', 'Status', ''].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(dishes as DataReviewDish[]).map(d => (
                    <React.Fragment key={d.id}>
                      <tr className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB] transition-colors">
                        <td className="px-4 py-3 text-sm font-medium text-[#111827]">{d.recipe_name}</td>
                        <td className="px-4 py-3 text-sm text-[#6B7280]">{d.slot_type}</td>
                        <td className="px-4 py-3 text-sm text-[#6B7280]">{d.diet_type}</td>
                        <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">{Math.round(d.cal_per_serving)} kcal</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                            d.is_verified ? 'bg-[#DCFCE7] text-[#15803d]' : 'bg-[#FEF3C7] text-[#B45309]'}`}>
                            {d.is_verified ? 'In pool' : 'Parked'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button onClick={() => { setFlagId(flagId === d.id ? null : d.id); setReason(''); setSuggested(''); }}
                            className="inline-flex items-center gap-1.5 h-8 px-3 rounded-md border border-[#E5E7EB] text-[#B45309] text-xs hover:bg-[#FFFBEB] transition-colors">
                            <Flag size={13} /> Flag
                          </button>
                        </td>
                      </tr>
                      {flagId === d.id && (
                        <tr className="bg-[#FFFBEB]">
                          <td colSpan={6} className="px-4 py-3">
                            <div className="flex flex-col gap-2">
                              <textarea value={reason} onChange={e => setReason(e.target.value)}
                                placeholder="What looks wrong? (required, min 5 chars)"
                                rows={2}
                                className="w-full px-3 py-2 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#B45309]" />
                              <div className="flex gap-2">
                                <input value={suggested} onChange={e => setSuggested(e.target.value)}
                                  placeholder="Suggested value (optional)"
                                  className="flex-1 h-9 px-3 rounded-md border border-[#D1D5DB] bg-white text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#B45309]" />
                                <button
                                  onClick={() => flag.mutate({ food_item_id: d.id, reason, suggested_value: suggested || undefined })}
                                  disabled={flag.isPending || reason.trim().length < 5}
                                  className="h-9 px-4 rounded-md bg-[#B45309] text-white text-sm hover:bg-[#92400E] disabled:opacity-50">
                                  {flag.isPending ? <Loader2 size={14} className="animate-spin" /> : 'Submit flag'}
                                </button>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : (
        (flags as MyFlag[]).length === 0 ? (
          <div className="bg-white border border-[#E5E7EB] rounded-lg py-16 flex flex-col items-center">
            <CheckCircle2 size={36} className="text-[#34B164] mb-3" />
            <p className="text-base font-medium text-[#374151]">No flags yet</p>
            <p className="text-sm text-[#6B7280] mt-1">Flag a dish from the Browse tab and it shows here with its status.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {(flags as MyFlag[]).map(f => (
              <div key={f.id} className="bg-white border border-[#E5E7EB] rounded-lg p-4 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-sm text-[#374151]">{f.reason}</p>
                  <p className="text-xs text-[#9CA3AF] mt-0.5">
                    Dish #{f.target_id} · field {f.field_changed}
                    {f.created_at ? ` · ${new Date(f.created_at).toLocaleDateString('en-IN')}` : ''}
                  </p>
                </div>
                <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium flex-shrink-0 ${
                  f.status === 'approved' ? 'bg-[#DCFCE7] text-[#15803d]' :
                  f.status === 'rejected' ? 'bg-[#FEE2E2] text-[#DC2626]' :
                  'bg-[#FEF3C7] text-[#B45309]'}`}>
                  {f.status}
                </span>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}
