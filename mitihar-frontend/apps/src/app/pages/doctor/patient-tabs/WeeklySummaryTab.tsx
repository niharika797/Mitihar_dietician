import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, AlertCircle, BarChart2 } from 'lucide-react';
import { doctorApi } from '../../../../lib/doctorApi';
import { qk } from '../../../../lib/queryKeys';

interface WeeklySummaryTabProps {
  patientId: number;
}

function formatDate(d: string): string {
  try {
    return new Date(d).toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' });
  } catch { return d; }
}

export function WeeklySummaryTab({ patientId }: WeeklySummaryTabProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: qk.weeklySummary(patientId),
    queryFn: () => doctorApi.getWeeklySummary(patientId),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 size={24} className="animate-spin text-[#1E7C45]" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="bg-white border border-[#E5E7EB] rounded-lg py-16 flex flex-col items-center">
        <AlertCircle size={32} className="text-[#9CA3AF] mb-3" />
        <p className="text-sm font-medium text-[#374151]">Could not load weekly summary</p>
      </div>
    );
  }

  const noActivity = data.days.every(d => d.confirmed_calories === 0);

  return (
    <div className="max-w-3xl">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#111827]">Weekly Adherence</h2>
          <p className="text-sm text-[#6B7280]">Week of {formatDate(data.week_start)}</p>
        </div>
        {noActivity && (
          <span className="text-xs text-[#9CA3AF] italic">No confirmed choices this week yet</span>
        )}
      </div>

      <div className="bg-white border border-[#E5E7EB] rounded-lg overflow-x-auto">
        <table className="w-full min-w-[540px]">
          <thead>
            <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
              {['Date', 'Planned kcal', 'Confirmed kcal', 'Meals confirmed', 'Bowl sizes'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-[#6B7280] whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.days.map(day => {
              const adherencePct = day.planned_calories > 0
                ? Math.round((day.confirmed_calories / day.planned_calories) * 100)
                : null;
              const bowlSizes = Object.entries(day.bowl_size_breakdown)
                .map(([meal, size]) => `${meal}: ${size}`)
                .join(', ');

              return (
                <tr key={day.date} className="border-b border-[#F3F4F6] last:border-0 hover:bg-[#F9FAFB]">
                  <td className="px-4 py-3 text-sm text-[#374151] whitespace-nowrap">{formatDate(day.date)}</td>
                  <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">{Math.round(day.planned_calories)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm tabular-nums text-[#374151]">{Math.round(day.confirmed_calories)}</span>
                      {adherencePct !== null && day.confirmed_calories > 0 && (
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                          adherencePct >= 80
                            ? 'bg-[#DCFCE7] text-[#15803d]'
                            : adherencePct >= 50
                            ? 'bg-[#FFFBEB] text-[#B45309]'
                            : 'bg-[#FEF2F2] text-[#DC2626]'
                        }`}>{adherencePct}%</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-[#374151] tabular-nums">
                    {day.meals_confirmed}/{day.meals_total}
                  </td>
                  <td className="px-4 py-3 text-xs text-[#6B7280]">
                    {bowlSizes || '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr className="bg-[#F9FAFB] border-t border-[#E5E7EB]">
              <td className="px-4 py-3 text-xs font-semibold text-[#374151]">Week Total</td>
              <td className="px-4 py-3 text-sm font-semibold text-[#374151] tabular-nums">
                {Math.round(data.week_totals.planned_calories)}
              </td>
              <td className="px-4 py-3 text-sm font-semibold text-[#374151] tabular-nums">
                {Math.round(data.week_totals.confirmed_calories)}
              </td>
              <td className="px-4 py-3 text-xs text-[#6B7280]">—</td>
              <td className="px-4 py-3 text-xs text-[#6B7280]">
                Avg: {data.week_totals.avg_bowl_size || '—'}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {!noActivity && (
        <div className="mt-4 flex items-center gap-2 text-xs text-[#9CA3AF]">
          <BarChart2 size={12} />
          Adherence % = confirmed ÷ planned calories per day
        </div>
      )}
    </div>
  );
}
