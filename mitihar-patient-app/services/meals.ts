import api from "../lib/axios";
import type { WeeklyPlan, PlanHistoryItem, ShoppingListResponse } from "../types";

// ── GET /meal-plan/week ────────────────────────────────────────────────────
export async function getWeeklyPlan(): Promise<WeeklyPlan> {
  const { data } = await api.get("/meal-plan/week");
  return data;
}

// ── GET /meal-plan/history ─────────────────────────────────────────────────
export async function getPlanHistory(): Promise<PlanHistoryItem[]> {
  const { data } = await api.get("/meal-plan/history");
  return data;
}

// ── GET /meal-plan/shopping-list ──────────────────────────────────────────
export async function getShoppingList(): Promise<ShoppingListResponse> {
  const { data } = await api.get("/meal-plan/shopping-list");
  return data;
}

// ── POST /meal-plan/shopping-list/toggle ──────────────────────────────────
export async function toggleShoppingItem(ingredient_name: string) {
  const { data } = await api.post("/meal-plan/shopping-list/toggle", { ingredient_name });
  return data;
}
