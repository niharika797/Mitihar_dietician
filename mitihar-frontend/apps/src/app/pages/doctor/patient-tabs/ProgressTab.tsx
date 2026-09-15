import React, { Suspense, lazy } from 'react';
import { Patient } from '../../../data/mockData';
import { TrendingDown, Target, Droplets, Loader2 } from 'lucide-react';
import { Card } from '../../../components/ui/Card';

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
      <Loader2 size={20} className="animate-spin text-muted-foreground" />
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
        <h2 className="text-lg font-semibold text-foreground">Progress Charts</h2>
        <p className="text-sm text-muted-foreground">Trend data for {patient.name}</p>
      </div>

      <div className="grid grid-cols-12 gap-5">

        {/* Weight chart — recharts loads lazily here */}
        <Card className="col-span-12 md:col-span-8 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-base font-medium text-foreground">Weight Trend</p>
              <p className="text-xs text-muted-foreground">Target: {patient.targetWeight} kg</p>
            </div>
            <div className="flex items-center gap-1.5 text-sm text-primary">
              <TrendingDown size={14} />
              <span className="tabular-nums font-medium">−{weightLost} kg</span>
            </div>
          </div>
          <Suspense fallback={<ChartSkeleton height={200} />}>
            <LazyWeightChart patient={patient} />
          </Suspense>
        </Card>

        {/* Stat cards — no recharts, renders instantly */}
        <div className="col-span-12 md:col-span-4 flex flex-col gap-4">
          <Card className="p-4">
            <div className="w-8 h-8 rounded-full bg-brand-50 flex items-center justify-center mb-3">
              <TrendingDown size={14} className="text-primary" />
            </div>
            <p className="text-2xl font-bold text-foreground tabular-nums">{latestWeight} kg</p>
            <p className="text-sm text-muted-foreground">Current weight</p>
          </Card>
          <Card className="p-4">
            <div className="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center mb-3">
              <Target size={14} className="text-blue-600" />
            </div>
            <p className="text-2xl font-bold text-foreground tabular-nums">{patient.targetWeight} kg</p>
            <p className="text-sm text-muted-foreground">Target weight</p>
          </Card>
        </div>

        {/* Water chart — same recharts chunk, already cached after WeightChart loads */}
        <Card className="col-span-12 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-base font-medium text-foreground">Water Intake — This Week</p>
              <p className="text-xs text-muted-foreground">Daily target: {patient.waterHistory[0]?.target ?? 2.5}L</p>
            </div>
            <Droplets size={14} className="text-blue-600" />
          </div>
          <Suspense fallback={<ChartSkeleton height={160} />}>
            <LazyWaterChart patient={patient} />
          </Suspense>
        </Card>

      </div>
    </div>
  );
}
