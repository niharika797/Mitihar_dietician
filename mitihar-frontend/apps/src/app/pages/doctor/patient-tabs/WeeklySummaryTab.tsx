import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Loader2, AlertCircle, BarChart2, ChevronDown, ChevronRight } from 'lucide-react';
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
  const [expandedDays, setExpandedDays] = useState<Set<string>>(new Set());

  const { data, isLoading, isError } = useQuery({
    queryKey: qk.weeklySummary(patientId),
    queryFn: () => doctorApi.getWeeklySummary(patientId),
  });

  const toggleDay = (dateStr: string) => {
    setExpandedDays(prev => {
      const next = new Set(prev);
      if (next.has(dateStr)) next.delete(dateStr);
      else next.add(dateStr);
      return next;
    });
  };

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

  const perDay = data.per_day ?? [];
  const noActivity = perDay.every(d => d.confirmed_calories === 0);
  const dishFrequency = data.dish_frequency ?? [];
  const pattern = data.pattern;

  const hasDishData    = dishFrequency.length > 0;
  const hasSelections  = dishFrequency.some(d => d.times_selected > 0);

  return (
    <div className="max-w-3xl space-y-6">

      {/* ── Adherence Table ───────────────────────────────────────────── */}
      <div>
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
              {perDay.map(day => {
                const adherencePct = day.planned_calories > 0
                  ? Math.round((day.confirmed_calories / day.planned_calories) * 100)
                  : null;
                const bowlSizes = Object.entries(day.bowl_size_breakdown)
                  .filter(([, count]) => count > 0)
                  .map(([size, count]) => `${size}: ${count}`)
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
          <div className="mt-3 flex items-center gap-2 text-xs text-[#9CA3AF]">
            <BarChart2 size={12} />
            Adherence % = confirmed ÷ planned calories per day
          </div>
        )}
      </div>

      {/* ── Section A: This Week's Choices ───────────────────────────── */}
      {hasSelections && (
        <div>
          <h3 className="text-sm font-semibold text-[#111827] mb-3">This Week's Choices</h3>
          <div className="bg-white border border-[#E5E7EB] rounded-lg divide-y divide-[#F3F4F6]">
            {perDay.map(day => {
              const isExpanded = expandedDays.has(day.date);
              const hasAnyConfirmed = day.meals_confirmed > 0;
              const slots = [
                { label: 'Breakfast', confirmed: day.breakfast_confirmed },
                { label: 'Lunch',     confirmed: day.lunch_confirmed },
                { label: 'Dinner',    confirmed: day.dinner_confirmed },
              ];

              return (
                <div key={day.date}>
                  <button
                    type="button"
                    onClick={() => toggleDay(day.date)}
                    className="w-full flex items-center justify-between px-4 py-3 hover:bg-[#F9FAFB] text-left"
                  >
                    <div className="flex items-center gap-3">
                      {isExpanded
                        ? <ChevronDown size={14} className="text-[#6B7280]" />
                        : <ChevronRight size={14} className="text-[#6B7280]" />
                      }
                      <span className="text-sm text-[#374151]">{formatDate(day.date)}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      {hasAnyConfirmed
                        ? <span className="text-xs text-[#15803d] font-medium">{day.meals_confirmed}/3 meals confirmed</span>
                        : <span className="text-xs text-[#9CA3AF]">No confirmations</span>
                      }
                    </div>
                  </button>
                  {isExpanded && (
                    <div className="px-10 pb-3 flex flex-col gap-1.5">
                      {slots.map(s => (
                        <div key={s.label} className="flex items-center gap-2 text-xs">
                          <span className={`w-3 h-3 rounded-full flex-shrink-0 ${s.confirmed ? 'bg-[#22c55e]' : 'bg-[#E5E7EB]'}`} />
                          <span className={s.confirmed ? 'text-[#374151]' : 'text-[#9CA3AF]'}>
                            {s.label} {s.confirmed ? '✓' : '—'}
                          </span>
                        </div>
                      ))}
                      <div className="mt-1 text-xs text-[#9CA3AF]">
                        {Math.round(day.confirmed_calories)} kcal confirmed
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Section B: Patterns This Week ────────────────────────────── */}
      {hasDishData && pattern && (
        <div>
          <h3 className="text-sm font-semibold text-[#111827] mb-3">Patterns This Week</h3>
          <div className="bg-white border border-[#E5E7EB] rounded-lg p-4 space-y-4">

            {pattern.preferred_dishes.length > 0 && (
              <div>
                <p className="text-xs font-medium text-[#6B7280] mb-2">Consistently chosen (≥2×)</p>
                <div className="flex flex-wrap gap-2">
                  {pattern.preferred_dishes.map(d => (
                    <span key={d.food_item_id} className="text-xs px-2.5 py-1 rounded-full bg-[#DCFCE7] text-[#15803d] font-medium">
                      {d.recipe_name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {pattern.never_selected_dishes.length > 0 && (
              <div>
                <p className="text-xs font-medium text-[#6B7280] mb-2">Offered but never chosen (≥3 offers)</p>
                <div className="flex flex-wrap gap-2">
                  {pattern.never_selected_dishes.map(d => (
                    <span key={d.food_item_id} className="text-xs px-2.5 py-1 rounded-full bg-[#FFFBEB] text-[#B45309] font-medium">
                      {d.recipe_name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {pattern.preferred_dishes.length === 0 && pattern.never_selected_dishes.length === 0 && (
              <p className="text-xs text-[#9CA3AF]">Not enough data to show patterns yet.</p>
            )}

          </div>
        </div>
      )}

    </div>
  );
}
