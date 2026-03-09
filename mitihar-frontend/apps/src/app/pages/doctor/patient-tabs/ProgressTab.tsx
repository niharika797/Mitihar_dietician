import React from 'react';
import { Patient } from '../../../data/mockData';
import {
  ResponsiveContainer, LineChart, Line, AreaChart, Area,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine
} from 'recharts';
import { TrendingDown, Droplets, Target } from 'lucide-react';

interface ProgressTabProps {
  patient: Patient;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-lg shadow-[0_10px_25px_-5px_rgb(0_0_0/0.1)] px-3 py-2">
      <p className="text-xs font-medium text-[#374151] mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} className="text-sm" style={{ color: p.color }}>
          {p.value} {p.unit}
        </p>
      ))}
    </div>
  );
};

export function ProgressTab({ patient }: ProgressTabProps) {
  const latestWeight = patient.weightHistory[patient.weightHistory.length - 1]?.value ?? patient.weight;
  const firstWeight = patient.weightHistory[0]?.value ?? patient.weight;
  const weightLost = (firstWeight - latestWeight).toFixed(1);

  return (
    <div className="max-w-4xl space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-[#111827]">Progress Charts</h2>
        <p className="text-sm text-[#6B7280]">Trend data for {patient.name}</p>
      </div>

      <div className="grid grid-cols-12 gap-5">
        {/* Weight Chart */}
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

          {patient.weightHistory.length === 0 ? (
            <div className="h-48 flex items-center justify-center">
              <p className="text-sm text-[#9CA3AF]">{patient.name} hasn't logged any weight data yet.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={patient.weightHistory} margin={{ top: 5, right: 5, bottom: 0, left: -10 }}>
                <defs>
                  <linearGradient id="weightGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#1E7C45" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#1E7C45" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="4 4" stroke="#E5E7EB" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} unit=" kg" />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={patient.targetWeight} stroke="#34B164" strokeDasharray="4 4" label={{ value: 'Target', position: 'insideRight', fontSize: 10, fill: '#34B164' }} />
                <Area type="monotone" dataKey="value" stroke="#1E7C45" strokeWidth={2} fill="url(#weightGrad)" dot={false} activeDot={{ r: 4, fill: '#1E7C45' }} unit=" kg" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Summary stats */}
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

        {/* Water intake chart */}
        <div className="col-span-12 bg-white border border-[#E5E7EB] rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-base font-medium text-[#111827]">Water Intake — This Week</p>
              <p className="text-xs text-[#6B7280]">Daily target: {patient.waterHistory[0]?.target ?? 2.5}L</p>
            </div>
            <div className="flex items-center gap-1.5 text-sm text-[#2563EB]">
              <Droplets size={15} />
            </div>
          </div>

          {patient.waterHistory.length === 0 ? (
            <div className="h-36 flex items-center justify-center">
              <p className="text-sm text-[#9CA3AF]">{patient.name} hasn't logged water data yet.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={patient.waterHistory} margin={{ top: 5, right: 5, bottom: 0, left: -10 }}>
                <CartesianGrid strokeDasharray="4 4" stroke="#E5E7EB" vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} unit="L" domain={[0, 3]} />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={patient.waterHistory[0]?.target} stroke="#F59E0B" strokeDasharray="4 4" />
                <Bar dataKey="value" fill="#2563EB" radius={[3, 3, 0, 0]} unit="L" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
