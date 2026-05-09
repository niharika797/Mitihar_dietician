import React, { Suspense, lazy } from 'react';
import { Patient } from '../../../data/mockData';
import { TrendingDown, Target, Droplets, Loader2 } from 'lucide-react';

/**
 * Both lazy imports point at the same file — Vite deduplicates them into
 * one shared chunk. recharts is NOT in the main bundle; it downloads
 * on-demand the first time a doctor opens this tab.
 */
const LazyWeightChart = lazy(() =>
  import('./ProgressCharts').then(m => ({ default: m.WeightChart }))
);
const LazyWaterChart = lazy(() =>
  import('./ProgressCharts').then(m => ({ default: m.WaterChart }))
);

function ChartSkeleton({ height }: { height: number }) {
  return (
    <div className="flex items-center justify-center" style={{ height }}>
      <Loader2 size={20} className="animate-spin text-[#D1D5DB]" />
    </div>
  );
}

interface ProgressTabProps {
  patient: Patient;
}

export function ProgressTab({ patient }: ProgressTabProps) {
  const latestWeight = patient.weightHistory[patient.weightHistory.length - 1]?.value ?? patient.weight;
  const firstWeight  = patient.weightHistory[0]?.value ?? patient.weight;
  const weightLost   = (firstWeight - latestWeight).toFixed(1);

  return (
    <div className="max-w-4xl space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-[#111827]">Progress Charts</h2>
        <p className="text-sm text-[#6B7280]">Trend data for {patient.name}</p>
      </div>

      <div className="grid grid-cols-12 gap-5">

        {/* Weight chart — recharts loads lazily here */}
        <div className="col-span-12 md:col-span-8 bg-white border border-[#E5E7EB] rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-base font-medium text-[#111827]">Weight Trend</p>
              <p className="text-xs text-[#6B7280]">Target: {patient.targetWeight} kg</p>
            </div>
            <div className="flex items-center gap-1.5 text-sm text-[#15803d]">
              <TrendingDown size={15} />
              <span className="tabular-nums font-medium">−{weightLost} kg</span>
            </div>
          </div>
          <Suspense fallback={<ChartSkeleton height={200} />}>
            <LazyWeightChart patient={patient} />
          </Suspense>
        </div>

        {/* Stat cards — no recharts, renders instantly */}
        <div className="col-span-12 md:col-span-4 flex flex-col gap-4">
          <div className="bg-white border border-[#E5E7EB] rounded-lg p-4">
            <div className="w-8 h-8 rounded-full bg-[#F0FDF4] flex items-center justify-center mb-3">
              <TrendingDown size={15} className="text-[#1E7C45]" />
            </div>
            <p className="text-2xl font-bold text-[#111827] tabular-nums">{latestWeight} kg</p>
            <p className="text-sm text-[#6B7280]">Current weight</p>
          </div>
          <div className="bg-white border border-[#E5E7EB] rounded-lg p-4">
            <div className="w-8 h-8 rounded-full bg-[#EFF6FF] flex items-center justify-center mb-3">
              <Target size={15} className="text-[#2563EB]" />
            </div>
            <p className="text-2xl font-bold text-[#111827] tabular-nums">{patient.targetWeight} kg</p>
            <p className="text-sm text-[#6B7280]">Target weight</p>
          </div>
        </div>

        {/* Water chart — same recharts chunk, already cached after WeightChart loads */}
        <div className="col-span-12 bg-white border border-[#E5E7EB] rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-base font-medium text-[#111827]">Water Intake — This Week</p>
              <p className="text-xs text-[#6B7280]">Daily target: {patient.waterHistory[0]?.target ?? 2.5}L</p>
            </div>
            <Droplets size={15} className="text-[#2563EB]" />
          </div>
          <Suspense fallback={<ChartSkeleton height={160} />}>
            <LazyWaterChart patient={patient} />
          </Suspense>
        </div>

      </div>
    </div>
  );
}
