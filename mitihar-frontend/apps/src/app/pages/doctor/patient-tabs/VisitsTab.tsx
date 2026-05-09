import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Activity, CheckCircle, XCircle, Loader2, RefreshCw } from 'lucide-react';
import { doctorApi, PatientVisit } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';

interface VisitsTabProps {
  patientId: number;
  patientName: string;
}

export function VisitsTab({ patientId, patientName }: VisitsTabProps) {
  const queryClient = useQueryClient();

  const { data: visits = [], isLoading } = useQuery({
    queryKey: qk.patientVisits(patientId),
    queryFn: () => doctorApi.getPatientVisits(patientId),
    staleTime: 30_000,
  });

  const recordMut = useMutation({
    mutationFn: () => doctorApi.recordVisit(patientId),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: qk.patientVisits(patientId) });
      if (res.charged) {
        toast.success(`Visit charged ₹1,200 · Total visits: ${res.visit_counter}`);
      } else {
        toast.info(res.message);
      }
    },
    onError: () => toast.error('Failed to record visit'),
  });

  // Active cycle = most recent visit row
  const activeCycle: PatientVisit | null = visits[0] ?? null;
  const now = Date.now();
  const cycleActive = activeCycle ? new Date(activeCycle.cycle_expiry).getTime() > now : false;

  return (
    <div className="max-w-3xl space-y-6">

      {/* Current cycle card */}
      <div className="bg-white border border-[#E5E7EB] rounded-lg p-5">
        <h3 className="text-base font-medium text-[#111827] mb-4">Current Visit Cycle (Token 2)</h3>
        {activeCycle ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
            {[
              { label: 'Token 2', value: activeCycle.token_2 },
              { label: 'Cycle Start', value: new Date(activeCycle.cycle_start).toLocaleDateString('en-IN') },
              { label: 'Cycle Expiry', value: new Date(activeCycle.cycle_expiry).toLocaleDateString('en-IN') },
              { label: 'Visits (Charged)', value: String(activeCycle.visit_counter) },
            ].map(item => (
              <div key={item.label} className="bg-[#F9FAFB] rounded-lg p-3">
                <p className="text-xs text-[#9CA3AF] mb-1">{item.label}</p>
                <p className="text-sm font-medium text-[#111827] font-mono">{item.value}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-[#9CA3AF] mb-5">No active cycle. Record a visit to start one.</p>
        )}

        <button
          onClick={() => recordMut.mutate()}
          disabled={recordMut.isPending}
          className="flex items-center gap-2 h-10 px-5 rounded-lg bg-[#1E7C45] text-white text-sm font-medium hover:bg-[#166534] transition-colors disabled:opacity-50"
        >
          {recordMut.isPending
            ? <Loader2 size={16} className="animate-spin" />
            : <Activity size={16} />}
          Record Patient Visit
        </button>

        {recordMut.data && (
          <div className={`mt-3 flex items-center gap-2 text-sm font-medium ${recordMut.data.charged ? 'text-[#1E7C45]' : 'text-[#6B7280]'}`}>
            {recordMut.data.charged ? <CheckCircle size={16} /> : <XCircle size={16} />}
            {recordMut.data.message}
          </div>
        )}
      </div>

      {/* Visit history */}
      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
        <div className="px-5 py-4 border-b border-[#E5E7EB]">
          <p className="text-base font-medium text-[#111827]">All Visit Cycles</p>
        </div>
        {isLoading ? (
          <div className="py-10 flex justify-center"><Loader2 size={20} className="animate-spin text-[#1E7C45]" /></div>
        ) : visits.length === 0 ? (
          <div className="py-10 text-center text-sm text-[#9CA3AF]">No visit history yet</div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                {['Token 2', 'Cycle Start', 'Cycle Expiry', 'Last Charged', 'Visits'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visits.map((v: PatientVisit) => (
                <tr key={v.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB]">
                  <td className="px-4 py-3 text-xs font-mono text-[#111827]">{v.token_2}</td>
                  <td className="px-4 py-3 text-sm text-[#374151]">{new Date(v.cycle_start).toLocaleDateString('en-IN')}</td>
                  <td className="px-4 py-3 text-sm text-[#374151]">{new Date(v.cycle_expiry).toLocaleDateString('en-IN')}</td>
                  <td className="px-4 py-3 text-sm text-[#374151]">
                    {v.last_charged_at ? new Date(v.last_charged_at).toLocaleDateString('en-IN') : <span className="text-[#9CA3AF]">—</span>}
                  </td>
                  <td className="px-4 py-3 text-sm font-semibold text-[#1E7C45] tabular-nums">{v.visit_counter}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
