import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { doctorApi, MealLogEntry } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';
import { CheckCircle, XCircle, Loader2, ClipboardList } from 'lucide-react';

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
          <h2 className="text-lg font-semibold text-[#111827]">Activity Log</h2>
          <p className="text-sm text-[#6B7280]">Meal logs for {patientName}</p>
        </div>
        {/* Period selector */}
        <div className="flex items-center gap-1 border border-[#D1D5DB] rounded-md overflow-hidden">
          {DAY_OPTIONS.map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`h-8 px-3 text-xs font-medium transition-colors ${
                days === d ? 'bg-[#1E7C45] text-white' : 'text-[#6B7280] hover:bg-[#F3F4F6]'
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 size={24} className="animate-spin text-[#1E7C45]" />
        </div>
      ) : isError ? (
        <div className="bg-white border border-[#E5E7EB] rounded-lg py-14 text-center">
          <p className="text-base font-medium text-[#374151]">Could not load activity logs</p>
        </div>
      ) : sortedDates.length === 0 ? (
        <div className="bg-white border border-[#E5E7EB] rounded-lg py-16 text-center">
          <ClipboardList size={32} className="text-[#D1D5DB] mx-auto mb-3" />
          <p className="text-base font-medium text-[#374151]">No logs in the last {days} days</p>
          <p className="text-sm text-[#6B7280] mt-1">
            {patientName} hasn't logged any meals recently.
          </p>
        </div>
      ) : (
        <div className="space-y-5">
          {sortedDates.map(date => {
            const logs = grouped[date];
            const totalCals = logs.reduce((s, l) => s + (l.calories_consumed ?? 0), 0);

            return (
              <div key={date} className="bg-white border border-[#E5E7EB] rounded-lg overflow-hidden">
                <div className="px-5 py-3 bg-[#F9FAFB] border-b border-[#E5E7EB] flex items-center justify-between">
                  <p className="text-sm font-medium text-[#374151]">{formatDate(date)}</p>
                  <div className="flex items-center gap-3 text-xs text-[#6B7280]">
                    <span className="tabular-nums font-medium text-[#111827]">
                      {Math.round(totalCals)} kcal
                    </span>
                    <span className="text-[#9CA3AF]">{logs.length} entries</span>
                  </div>
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-[#F3F4F6]">
                      {['Meal', 'Food', 'Calories', 'Protein', 'Carbs', 'Fat'].map(h => (
                        <th
                          key={h}
                          className="px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280]"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map(log => (
                      <tr key={log.id} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB]">
                        <td className="px-4 py-3 text-sm text-[#6B7280]">{log.meal_type}</td>
                        <td className="px-4 py-3 text-sm text-[#111827]">
                          {log.custom_food_name ?? '—'}
                          {log.notes && (
                            <p className="text-xs text-[#9CA3AF] mt-0.5">{log.notes}</p>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">
                          {Math.round(log.calories_consumed)}
                        </td>
                        <td className="px-4 py-3 text-sm text-[#2563EB] tabular-nums">
                          {log.protein_g.toFixed(1)}g
                        </td>
                        <td className="px-4 py-3 text-sm text-[#F59E0B] tabular-nums">
                          {log.carbs_g.toFixed(1)}g
                        </td>
                        <td className="px-4 py-3 text-sm text-[#6B7280] tabular-nums">
                          {log.fat_g.toFixed(1)}g
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
