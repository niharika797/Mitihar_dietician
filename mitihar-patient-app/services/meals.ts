import api from "../lib/axios";
import type { WeeklyPlan, PlanHistoryItem, ShoppingListResponse } from "../types";

// ── GET /meal-plan/week ────────────────────────────────────────────────────
export async function getWeeklyPlan(): Promise<WeeklyPlan> {
  const { data } = await api.get("/meal-plan/week");
  // Backend now returns flat { "2026-03-18": [...], "2026-03-19": [...] }
  // Guard: if old shape { days: {...} } is returned, unwrap it
  if (data && typeof data === "object" && !Array.isArray(data) && data.days) {
    return data.days as WeeklyPlan;
  }
  return (data ?? {}) as WeeklyPlan;
}

// ── POST /diet-plans/generate ──────────────────────────────────────────────
export async function generatePlan(): Promise<void> {
  await api.post("/diet-plans/generate");
}

// ── GET /meal-plan/history ─────────────────────────────────────────────────
export async function getPlanHistory(): Promise<PlanHistoryItem[]> {
  const { data } = await api.get("/meal-plan/history");
  // Backend returns { plans: [...], count: N } — unwrap the array
  if (data && Array.isArray(data.plans)) return data.plans;
  if (Array.isArray(data)) return data;
  return [];
}

// ── GET /meal-plan/shopping-list ──────────────────────────────────────────
export async function getShoppingList(): Promise<ShoppingListResponse> {
  const { data } = await api.get("/meal-plan/shopping-list");
  // Backend returns { total_items: N, grouped: { "Vegetables": [...], ... } }
  // Unwrap so the frontend gets { "Vegetables": [...], ... } directly
  if (data && data.grouped && typeof data.grouped === "object") return data.grouped;
  if (data && typeof data === "object" && !data.total_items) return data;
  return {};
}

// ── POST /meal-plan/shopping-list/toggle ──────────────────────────────────
export async function toggleShoppingItem(ingredient_name: string) {
  const { data } = await api.post("/meal-plan/shopping-list/toggle", { ingredient_name });
  return data;
}
