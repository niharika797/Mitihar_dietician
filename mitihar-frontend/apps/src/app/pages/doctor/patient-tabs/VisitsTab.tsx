import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Activity, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { doctorApi, PatientVisit } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';
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

        <Button variant="primary" size="lg" onClick={() => recordMut.mutate()} disabled={recordMut.isPending}>
          {recordMut.isPending
            ? <Loader2 size={16} className="animate-spin" />
            : <Activity size={16} />}
          Record Patient Visit
        </Button>

        {recordMut.data && (
          <div className={`mt-3 flex items-center gap-2 text-sm font-medium ${recordMut.data.charged ? 'text-primary' : 'text-muted-foreground'}`}>
            {recordMut.data.charged ? <CheckCircle size={16} /> : <XCircle size={16} />}
            {recordMut.data.message}
          </div>
        )}
      </Card>

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
