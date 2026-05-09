import api from "../lib/axios";
import type { TodaySummary, MealLogEntry, WeightEntry, WeeklyReport } from "../types";

// ── GET /progress/today ────────────────────────────────────────────────────
export async function getTodaySummary(): Promise<TodaySummary> {
  const { data } = await api.get("/progress/today");
  return data;
}

// ── POST /progress/log/meal ────────────────────────────────────────────────────
export interface LogMealPayload {
  meal_type: string;
  calories_consumed: number;
  protein_g?: number;
  carbs_g?: number;
  fat_g?: number;
  fiber_g?: number;
  logged_date?: string;
  notes?: string;
}

export async function logMeal(payload: LogMealPayload): Promise<MealLogEntry> {
  const { data } = await api.post("/progress/log/meal", payload); // Audit C-3: backend route is /log/meal, not /meal
  return data;
}

// ── PUT /progress/log/meal/{id} ───────────────────────────────────────────
export async function editMealLog(id: number, payload: Partial<LogMealPayload>) {
  const { data } = await api.put(`/progress/log/meal/${id}`, payload);
  return data;
}

// ── DELETE /progress/log/meal/{id} ────────────────────────────────────────
export async function deleteMealLog(id: number) {
  await api.delete(`/progress/log/meal/${id}`);
}

// ── PUT /progress/log/water ───────────────────────────────────────────────
export async function logWater(glasses: number) {
  const { data } = await api.put("/progress/log/water", { glasses });
  return data;
}

// ── PUT /progress/log/steps ───────────────────────────────────────────────
export async function logSteps(steps: number) {
  const { data } = await api.put("/progress/log/steps", { steps });
  return data;
}

// ── PUT /progress/log/weight ──────────────────────────────────────────────
export async function logWeight(weight_kg: number) {
  const { data } = await api.put("/progress/log/weight", { weight_kg });
  return data;
}

// ── GET /progress/weight-history ─────────────────────────────────────────
export async function getWeightHistory(days = 30): Promise<WeightEntry[]> {
  const { data } = await api.get(`/progress/weight-history?days=${days}`);
  // Backend returns { days: N, entries: [...] } — unwrap the array
  if (data && Array.isArray(data.entries)) return data.entries;
  if (Array.isArray(data)) return data;
  return [];
}

// ── GET /progress/weekly-report ───────────────────────────────────────────
export async function getWeeklyReport(): Promise<WeeklyReport> {
  const { data } = await api.get("/progress/weekly-report");
  return data;
}

// ── GET /progress/streak ──────────────────────────────────────────────────
export async function getStreak(): Promise<{ streak_days: number; last_logged: string }> {
  const { data } = await api.get("/progress/streak");
  return data;
}

// ── Phase 8 Tier 0: meal ratings ─────────────────────────────────────────

export interface MealRating {
  id: number;
  food_item_id: number;
  recommendation_id: number | null;
  rating: 1 | -1;
  rated_at: string;
}

export async function rateMeal(
  food_item_id: number,
  rating: 1 | -1,
  recommendation_id?: number | null,
): Promise<MealRating> {
  const { data } = await api.post("/progress/meal/rate", {
    food_item_id,
    rating,
    recommendation_id: recommendation_id ?? null,
  });
  return data;
}

export async function getMyRatings(): Promise<MealRating[]> {
  const { data } = await api.get("/progress/meal/ratings");
  return data;
}
