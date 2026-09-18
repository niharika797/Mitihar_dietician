/**
 * ProgressCharts — lazy-loaded recharts chunk.
 *
 * This file is the sole import point for recharts in the dashboard.
 * Loaded via React.lazy() in ProgressTab — Vite code-splits recharts
 * into a separate chunk, keeping it out of the main bundle.
 *
 * Pattern in ProgressTab:
 *   const LazyWeightChart = lazy(() =>
 *     import('./ProgressCharts').then(m => ({ default: m.WeightChart }))
 *   );
 *
 * Vite deduplicates the two dynamic imports into a single shared chunk.
 * Do NOT import recharts anywhere else in the dashboard.
 *
 * Colors: Recharts stroke/fill/style props need real CSS color strings
 * (Tailwind utility classes don't apply to SVG attributes), so series
 * colors reference the theme's CSS custom properties directly via var() —
 * these resolve per-theme at paint time from theme.css's :root/.dark
 * cascade, same as the Tailwind-generated classes elsewhere in the app.
 */
import React from 'react';
import {
  ResponsiveContainer,
  AreaChart, Area,
  BarChart, Bar,
  XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine,
} from 'recharts';
import { Patient } from '../../../data/mockData';

// ── Shared tooltip ────────────────────────────────────────────────────────────
const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-lg shadow-[var(--shadow-card)] px-3 py-2">
      <p className="text-xs font-medium text-secondary-foreground mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} className="text-sm" style={{ color: p.color }}>
          {p.value} {p.unit}
        </p>
      ))}
    </div>
  );
};

// ── Named export: WeightChart ─────────────────────────────────────────────────
export function WeightChart({ patient }: { patient: Patient }) {
  if (patient.weightHistory.length === 0) {
    return (
      <div className="h-48 flex items-center justify-center">
        <p className="text-sm text-muted-foreground">{patient.name} hasn't logged any weight data yet.</p>
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={patient.weightHistory} margin={{ top: 5, right: 5, bottom: 0, left: -10 }}>
        <defs>
          <linearGradient id="weightGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="var(--color-chart-1)" stopOpacity={0.2} />
            <stop offset="95%" stopColor="var(--color-chart-1)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="4 4" stroke="var(--color-border)" vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--color-muted-foreground)' }} axisLine={false} tickLine={false} />
        <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11, fill: 'var(--color-muted-foreground)' }} axisLine={false} tickLine={false} unit=" kg" />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine
          y={patient.targetWeight} stroke="var(--color-brand-400)" strokeDasharray="4 4"
          label={{ value: 'Target', position: 'insideRight', fontSize: 10, fill: 'var(--color-brand-400)' }}
        />
        <Area type="monotone" dataKey="value" stroke="var(--color-chart-1)" strokeWidth={2}
          fill="url(#weightGrad)" dot={false} activeDot={{ r: 4, fill: 'var(--color-chart-1)' }} unit=" kg" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// ── Named export: WaterChart ──────────────────────────────────────────────────
export function WaterChart({ patient }: { patient: Patient }) {
  if (patient.waterHistory.length === 0) {
    return (
      <div className="h-36 flex items-center justify-center">
        <p className="text-sm text-muted-foreground">{patient.name} hasn't logged water data yet.</p>
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={160}>
      <BarChart data={patient.waterHistory} margin={{ top: 5, right: 5, bottom: 0, left: -10 }}>
        <CartesianGrid strokeDasharray="4 4" stroke="var(--color-border)" vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--color-muted-foreground)' }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: 'var(--color-muted-foreground)' }} axisLine={false} tickLine={false} unit="L" domain={[0, 3]} />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={patient.waterHistory[0]?.target} stroke="var(--color-chart-3)" strokeDasharray="4 4" />
        <Bar dataKey="value" fill="var(--color-chart-2)" radius={[3, 3, 0, 0]} unit="L" />
      </BarChart>
    </ResponsiveContainer>
  );
}
