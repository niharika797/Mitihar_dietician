import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Activity, CheckCircle, XCircle, Loader2, RefreshCw, Flag } from 'lucide-react';
import { doctorApi, PatientVisit, FLAG_VISIT_REASONS, FlagVisitReason } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';
import { StatusBadge } from '../../../components/ui/StatusBadge';

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

  const [token2, setToken2] = useState('');

  const recordMut = useMutation({
    mutationFn: () => doctorApi.recordVisit(patientId, token2.trim()),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: qk.patientVisits(patientId) });
      setToken2('');
      // Show the backend's own message rather than rebuilding it here — the
      // charge amount lives in one constant server-side, and a second copy in
      // the UI is how the old "₹1,200" string drifted from the real ₹1,500.
      if (res.charged) toast.success(res.message);
      else toast.info(res.message);
    },
    // The backend returns genuinely actionable detail ("Token 2 does not
    // match…", "No active visit cycle…"); a generic string throws that away.
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail ?? 'Failed to record visit');
    },
  });

  const [flagReason, setFlagReason] = useState<FlagVisitReason>('phone_not_present');
  const [flagOther, setFlagOther] = useState('');
  const flagNeedsNote = flagReason === 'other' && flagOther.trim().length === 0;

  const flagMut = useMutation({
    mutationFn: () => doctorApi.flagVisit(patientId, flagReason, flagOther),
    onSuccess: (res) => {
      setFlagOther('');
      setFlagReason('phone_not_present');
      queryClient.invalidateQueries({ queryKey: qk.patientVisits(patientId) });
      queryClient.invalidateQueries({ queryKey: qk.patientFlaggedVisits(patientId) });
      toast.success(res.message);
    },
    onError: () => toast.error('Failed to flag visit'),
  });

  const { data: flagged = [] } = useQuery({
    queryKey: qk.patientFlaggedVisits(patientId),
    queryFn: () => doctorApi.getFlaggedVisits({ patientId }),
    staleTime: 30_000,
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

        <div className="flex items-center gap-3 flex-wrap">
          <input
            value={token2}
            onChange={(e) => setToken2(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && token2.trim().length >= 5 && !recordMut.isPending) {
                recordMut.mutate();
              }
            }}
            placeholder="Token 2 (e.g. TKN2-AB3K7)"
            aria-label="Token 2 shown by the patient"
            className="h-10 px-3 w-56 rounded-lg border border-[#E5E7EB] text-sm font-mono text-[#111827] placeholder:font-sans placeholder:text-[#9CA3AF] focus:outline-none focus:border-[#1E7C45]"
          />

          <button
            onClick={() => recordMut.mutate()}
            /* min 5 chars mirrors RecordVisitRequest.min_length — blocks a
               guaranteed 422 rather than round-tripping to find out. */
            disabled={recordMut.isPending || token2.trim().length < 5}
            className="flex items-center gap-2 h-10 px-5 rounded-lg bg-[#1E7C45] text-white text-sm font-medium hover:bg-[#166534] transition-colors disabled:opacity-50"
          >
            {recordMut.isPending
              ? <Loader2 size={16} className="animate-spin" />
              : <Activity size={16} />}
            Record Patient Visit
          </button>

        </div>

        {/* Flag path — separate row because it needs a reason before it can be
            submitted. The reason is shown to the patient, so it is a fixed list
            rather than free text. */}
        <div className="mt-4 pt-4 border-t border-[#F3F4F6]">
          <p className="text-xs text-[#6B7280] mb-2">
            Patient can't show Token 2? Pick a reason — they confirm in their app before anything is charged.
          </p>
          <div className="flex items-center gap-3 flex-wrap">
            <select
              value={flagReason}
              onChange={(e) => setFlagReason(e.target.value as FlagVisitReason)}
              aria-label="Reason the patient cannot show Token 2"
              className="h-10 px-3 rounded-lg border border-[#E5E7EB] bg-white text-sm text-[#374151] focus:outline-none focus:border-[#1E7C45]"
            >
              {FLAG_VISIT_REASONS.map(r => (
                <option key={r.code} value={r.code}>{r.label}</option>
              ))}
            </select>

            {flagReason === 'other' && (
              <input
                value={flagOther}
                onChange={(e) => setFlagOther(e.target.value)}
                maxLength={1000}
                placeholder="Describe the reason"
                aria-label="Reason description"
                className="h-10 px-3 w-64 rounded-lg border border-[#E5E7EB] text-sm text-[#111827] placeholder:text-[#9CA3AF] focus:outline-none focus:border-[#1E7C45]"
              />
            )}

            <button
              onClick={() => flagMut.mutate()}
              /* Mirrors the server rule: "other" requires a note. */
              disabled={flagMut.isPending || flagNeedsNote}
              title={flagNeedsNote ? 'Describe the reason first' : "Flag this visit for the patient to confirm"}
              className="flex items-center gap-2 h-10 px-5 rounded-lg border border-[#E5E7EB] bg-white text-[#374151] text-sm font-medium hover:bg-[#F9FAFB] transition-colors disabled:opacity-50"
            >
              {flagMut.isPending
                ? <Loader2 size={16} className="animate-spin" />
                : <Flag size={16} />}
              Flag Visit
            </button>
          </div>
        </div>

        {recordMut.data && (
          <div className={`mt-3 flex items-center gap-2 text-sm font-medium ${recordMut.data.charged ? 'text-[#1E7C45]' : 'text-[#6B7280]'}`}>
            {recordMut.data.charged ? <CheckCircle size={16} /> : <XCircle size={16} />}
            {recordMut.data.message}
          </div>
        )}
      </div>

      {/* Flagged visits — only rendered once at least one exists, so the tab
          stays clean for the normal Token-2 flow. */}
      {flagged.length > 0 && (
        <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
          <div className="px-5 py-4 border-b border-[#E5E7EB]">
            <p className="text-base font-medium text-[#111827]">Flagged Visits</p>
            <p className="text-xs text-[#6B7280] mt-0.5">
              Raised without Token 2 — {patientName} confirms or denies each from their app.
              Only a confirmed visit is charged.
            </p>
          </div>
          <table className="w-full">
            <thead>
              <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                {['Visit Date', 'Status', 'Answered', 'Reason'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {flagged.map(f => (
                <tr key={f.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB]">
                  <td className="px-4 py-3 text-sm text-[#374151]">
                    {new Date(f.visit_date).toLocaleDateString('en-IN')}
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={f.status} /></td>
                  <td className="px-4 py-3 text-sm text-[#374151]">
                    {f.responded_at
                      ? new Date(f.responded_at).toLocaleDateString('en-IN')
                      : <span className="text-[#9CA3AF]">Awaiting patient</span>}
                  </td>
                  <td className="px-4 py-3 text-sm text-[#6B7280]">
                    {f.reason_label}
                    {/* Free text only exists on "other", so show it as detail
                        under the label rather than as a competing column. */}
                    {f.doctor_note && (
                      <span className="block text-xs text-[#9CA3AF] mt-0.5">{f.doctor_note}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

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
