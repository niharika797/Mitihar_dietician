import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Activity, CheckCircle, XCircle, Loader2, Flag } from 'lucide-react';
import { doctorApi, PatientVisit, FLAG_VISIT_REASONS, FlagVisitReason } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';
import { StatusBadge } from '../../../components/ui/StatusBadge';
import { Button } from '../../../components/ui/Button';
import { Card } from '../../../components/ui/Card';

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
      <Card className="p-5">
        <h3 className="text-base font-medium text-foreground mb-4">Current Visit Cycle (Token 2)</h3>
        {activeCycle ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
            {[
              { label: 'Token 2', value: activeCycle.token_2 },
              { label: 'Cycle Start', value: new Date(activeCycle.cycle_start).toLocaleDateString('en-IN') },
              { label: 'Cycle Expiry', value: new Date(activeCycle.cycle_expiry).toLocaleDateString('en-IN') },
              { label: 'Visits (Charged)', value: String(activeCycle.visit_counter) },
            ].map(item => (
              <div key={item.label} className="bg-input-background rounded-lg p-3">
                <p className="text-xs text-muted-foreground mb-1">{item.label}</p>
                <p className="text-sm font-medium text-foreground font-mono">{item.value}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground mb-5">No active cycle. Record a visit to start one.</p>
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
            className="h-10 px-3 w-56 rounded-lg border border-border bg-input-background text-sm font-mono text-foreground placeholder:font-sans placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />

          <Button
            variant="primary"
            size="lg"
            onClick={() => recordMut.mutate()}
            /* min 5 chars mirrors RecordVisitRequest.min_length — blocks a
               guaranteed 422 rather than round-tripping to find out. */
            disabled={recordMut.isPending || token2.trim().length < 5}
          >
            {recordMut.isPending
              ? <Loader2 size={16} className="animate-spin" />
              : <Activity size={16} />}
            Record Patient Visit
          </Button>
        </div>

        {/* Flag path — separate row because it needs a reason before it can be
            submitted. The reason is shown to the patient, so it is a fixed list
            rather than free text. */}
        <div className="mt-4 pt-4 border-t border-border">
          <p className="text-xs text-muted-foreground mb-2">
            Patient can't show Token 2? Pick a reason — they confirm in their app before anything is charged.
          </p>
          <div className="flex items-center gap-3 flex-wrap">
            <select
              value={flagReason}
              onChange={(e) => setFlagReason(e.target.value as FlagVisitReason)}
              aria-label="Reason the patient cannot show Token 2"
              className="h-10 px-3 rounded-lg border border-border bg-card text-sm text-secondary-foreground focus:outline-none focus:ring-2 focus:ring-ring"
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
                className="h-10 px-3 w-64 rounded-lg border border-border bg-input-background text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
            )}

            <Button
              variant="outline"
              size="lg"
              onClick={() => flagMut.mutate()}
              /* Mirrors the server rule: "other" requires a note. */
              disabled={flagMut.isPending || flagNeedsNote}
              title={flagNeedsNote ? 'Describe the reason first' : "Flag this visit for the patient to confirm"}
            >
              {flagMut.isPending
                ? <Loader2 size={16} className="animate-spin" />
                : <Flag size={16} />}
              Flag Visit
            </Button>
          </div>
        </div>

        {recordMut.data && (
          <div className={`mt-3 flex items-center gap-2 text-sm font-medium ${recordMut.data.charged ? 'text-primary' : 'text-muted-foreground'}`}>
            {recordMut.data.charged ? <CheckCircle size={16} /> : <XCircle size={16} />}
            {recordMut.data.message}
          </div>
        )}
      </Card>

      {/* Flagged visits — only rendered once at least one exists, so the tab
          stays clean for the normal Token-2 flow. */}
      {flagged.length > 0 && (
        <Card className="overflow-hidden">
          <div className="px-5 py-4 border-b border-border">
            <p className="text-base font-medium text-foreground">Flagged Visits</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Raised without Token 2 — {patientName} confirms or denies each from their app.
              Only a confirmed visit is charged.
            </p>
          </div>
          <table className="w-full">
            <thead>
              <tr className="bg-input-background border-b border-border">
                {['Visit Date', 'Status', 'Answered', 'Reason'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {flagged.map(f => (
                <tr key={f.id} className="border-b border-border last:border-0 hover:bg-input-background">
                  <td className="px-4 py-3 text-sm text-secondary-foreground">
                    {new Date(f.visit_date).toLocaleDateString('en-IN')}
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={f.status} /></td>
                  <td className="px-4 py-3 text-sm text-secondary-foreground">
                    {f.responded_at
                      ? new Date(f.responded_at).toLocaleDateString('en-IN')
                      : <span className="text-muted-foreground">Awaiting patient</span>}
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {f.reason_label}
                    {/* Free text only exists on "other", so show it as detail
                        under the label rather than as a competing column. */}
                    {f.doctor_note && (
                      <span className="block text-xs text-muted-foreground mt-0.5">{f.doctor_note}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* Visit history */}
      <Card className="overflow-hidden">
        <div className="px-5 py-4 border-b border-border">
          <p className="text-base font-medium text-foreground">All Visit Cycles</p>
        </div>
        {isLoading ? (
          <div className="py-10 flex justify-center"><Loader2 size={20} className="animate-spin text-primary" /></div>
        ) : visits.length === 0 ? (
          <div className="py-10 text-center text-sm text-muted-foreground">No visit history yet</div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="bg-input-background border-b border-border">
                {['Token 2', 'Cycle Start', 'Cycle Expiry', 'Last Charged', 'Visits'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visits.map((v: PatientVisit) => (
                <tr key={v.id} className="border-b border-border last:border-0 hover:bg-input-background">
                  <td className="px-4 py-3 text-xs font-mono text-foreground">{v.token_2}</td>
                  <td className="px-4 py-3 text-sm text-secondary-foreground">{new Date(v.cycle_start).toLocaleDateString('en-IN')}</td>
                  <td className="px-4 py-3 text-sm text-secondary-foreground">{new Date(v.cycle_expiry).toLocaleDateString('en-IN')}</td>
                  <td className="px-4 py-3 text-sm text-secondary-foreground">
                    {v.last_charged_at ? new Date(v.last_charged_at).toLocaleDateString('en-IN') : <span className="text-muted-foreground">—</span>}
                  </td>
                  <td className="px-4 py-3 text-sm font-semibold text-primary tabular-nums">{v.visit_counter}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
