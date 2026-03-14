import { create } from "zustand";
import type { TodaySummary, WeightEntry } from "../types";

interface ProgressState {
  // ── Server-synced today snapshot (hydrated by TanStack Query) ──────────
  today: TodaySummary | null;

  // ── Optimistic local counters for instant UI feedback ─────────────────
  localWater: number | null;       // glasses — null = use server value
  localSteps: number | null;       // steps
  localWeight: number | null;      // kg — today's entry
  weightHistory: WeightEntry[];

  // ── Actions ────────────────────────────────────────────────────────────
  hydrateSummary: (summary: TodaySummary) => void;
  setLocalWater: (glasses: number) => void;
  setLocalSteps: (steps: number) => void;
  setLocalWeight: (kg: number) => void;
  appendWeightEntry: (entry: WeightEntry) => void;
  hydrateWeightHistory: (entries: WeightEntry[]) => void;
  reset: () => void;
}

export const useProgressStore = create<ProgressState>((set) => ({
  today: null,
  localWater: null,
  localSteps: null,
  localWeight: null,
  weightHistory: [],

  hydrateSummary: (summary) => set({ today: summary }),

  setLocalWater: (glasses) => set({ localWater: glasses }),
  setLocalSteps: (steps) => set({ localSteps: steps }),
  setLocalWeight: (kg) => set({ localWeight: kg }),

  appendWeightEntry: (entry) =>
    set((s) => ({ weightHistory: [...s.weightHistory, entry] })),

  hydrateWeightHistory: (entries) => set({ weightHistory: entries }),

  reset: () =>
    set({ today: null, localWater: null, localSteps: null, localWeight: null, weightHistory: [] }),
}));

// ── Selectors ──────────────────────────────────────────────────────────────
// Use these to get the effective (optimistic-or-server) value in components.
export const selectWater = (s: ProgressState) =>
  s.localWater ?? s.today?.water ?? 0;

export const selectSteps = (s: ProgressState) =>
  s.localSteps ?? s.today?.steps ?? 0;
