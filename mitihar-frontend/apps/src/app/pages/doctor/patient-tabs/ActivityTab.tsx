import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { doctorApi, MealLogEntry } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';
import { Loader2, ClipboardList } from 'lucide-react';
import { Card } from '../../../components/ui/Card';

interface ActivityTabProps {
  patientId: number;
  patientName: string;
}

const DAY_OPTIONS = [7, 14, 30] as const;

export function ActivityTab({ patientId, patientName }: ActivityTabProps) {
  const [days, setDays] = useState<7 | 14 | 30>(7);

  const { data, isLoading, isError } = useQuery({
    queryKey: qk.patientLogs(patientId, days),
    queryFn: () => doctorApi.getPatientLogs(patientId, days),
  });

  // Group by logged_date
  const grouped = (data?.meal_logs ?? []).reduce((acc, log) => {
    if (!acc[log.logged_date]) acc[log.logged_date] = [];
    acc[log.logged_date].push(log);
    return acc;
  }, {} as Record<string, MealLogEntry[]>);

  const sortedDates = Object.keys(grouped).sort((a, b) =>
    new Date(b).getTime() - new Date(a).getTime()
  );

  const formatDate = (d: string) => {
    try {
      return new Date(d).toLocaleDateString('en-IN', {
        weekday: 'long', day: 'numeric', month: 'long',
      });
    } catch {
      return d;
    }
  };

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Activity Log</h2>
          <p className="text-sm text-muted-foreground">Meal logs for {patientName}</p>
        </div>
        {/* Period selector */}
        <div className="flex items-center gap-1 border border-border rounded-md overflow-hidden">
          {DAY_OPTIONS.map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`h-8 px-3 text-xs font-medium transition-colors ${
                days === d ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 size={20} className="animate-spin text-primary" />
        </div>
      ) : isError ? (
        <Card className="py-14 text-center">
          <p className="text-base font-medium text-secondary-foreground">Could not load activity logs</p>
        </Card>
      ) : sortedDates.length === 0 ? (
        <Card className="py-16 text-center">
          <ClipboardList size={20} className="text-slate-300 mx-auto mb-3" />
          <p className="text-base font-medium text-secondary-foreground">No logs in the last {days} days</p>
          <p className="text-sm text-muted-foreground mt-1">
            {patientName} hasn't logged any meals recently.
          </p>
        </Card>
      ) : (
        <div className="space-y-5">
          {sortedDates.map(date => {
            const logs = grouped[date];
            const totalCals = logs.reduce((s, l) => s + (l.calories_consumed ?? 0), 0);

            return (
              <Card key={date} className="overflow-hidden">
                <div className="px-5 py-3 bg-input-background border-b border-border flex items-center justify-between">
                  <p className="text-sm font-medium text-secondary-foreground">{formatDate(date)}</p>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="tabular-nums font-medium text-foreground">
                      {Math.round(totalCals)} kcal
                    </span>
                    <span className="text-muted-foreground">{logs.length} entries</span>
                  </div>
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      {['Meal', 'Food', 'Calories', 'Protein', 'Carbs', 'Fat'].map(h => (
                        <th
                          key={h}
                          className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-muted-foreground"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map(log => (
                      <tr key={log.id} className="border-b border-border last:border-0 hover:bg-input-background">
                        <td className="px-4 py-3 text-sm text-muted-foreground">{log.meal_type}</td>
                        <td className="px-4 py-3 text-sm text-foreground">
                          {log.custom_food_name ?? '—'}
                          {log.notes && (
                            <p className="text-xs text-muted-foreground mt-0.5">{log.notes}</p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-secondary-foreground tabular-nums">
                          {Math.round(log.calories_consumed)}
                        </td>
                        <td className="px-4 py-3 text-sm text-blue-600 tabular-nums">
                          {log.protein_g.toFixed(1)}g
                        </td>
                        <td className="px-4 py-3 text-sm text-amber-500 tabular-nums">
                          {log.carbs_g.toFixed(1)}g
                        </td>
                        <td className="px-4 py-3 text-sm text-muted-foreground tabular-nums">
                          {log.fat_g.toFixed(1)}g
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
