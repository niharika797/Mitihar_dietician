import api from "../lib/axios";
import type { WeeklyPlan, WeekResponseV2, PlanHistoryItem, ShoppingListResponse, ConfirmChoiceResponse, PantryResponse, PantrySuggestion } from "../types";

// ── GET /meal-plan/week ────────────────────────────────────────────────────
export async function getWeeklyPlan(): Promise<WeeklyPlan | WeekResponseV2> {
  const { data } = await api.get("/meal-plan/week");
  // v2 plans: pass through as-is for caller to branch on generation_version
  if (data && data.generation_version === 2) {
    return data as WeekResponseV2;
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

// ── POST /meal-plan/confirm-choice ────────────────────────────────────────
export async function confirmMealChoice(body: {
  food_item_ids: number[];
  date: string;
  meal_type: string;
  weekly_combo_id?: number;
  bowl_size?: string;
}): Promise<ConfirmChoiceResponse> {
  const { data } = await api.post("/meal-plan/confirm-choice", body);
  return data;
}

// ── GET /meal-plan/choices/{date} ─────────────────────────────────────────
export interface DailyChoicesResponse {
  date: string;
  choices: Array<{
    meal_type: string;
    food_item_id: number;
    calories: number;
    weekly_combo_id: number | null;
    recipe_name: string;
    dishes: Array<{ food_item_id: number; slot_type: string; calories: number; recipe_name: string }>;
  }>;
}

export async function getDailyChoices(date: string): Promise<DailyChoicesResponse> {
  const { data } = await api.get(`/meal-plan/choices/${date}`);
  return data;
}

// ── POST /meal-plan/shopping-list/toggle ──────────────────────────────────
// Audit C-4: backend reads query params (not JSON body), and at_home is a required param.
// Callers must now pass the desired at_home boolean explicitly.
export async function toggleShoppingItem(ingredient_name: string, at_home: boolean) {
  const { data } = await api.post("/meal-plan/shopping-list/toggle", null, {
    params: { ingredient_name, at_home },
  });
  return data;
}

// ── Pantry (pantry-first meal planning) ──────────────────────────────────
export async function getPantry(search?: string): Promise<PantryResponse> {
  const { data } = await api.get("/meal-plan/pantry", { params: search ? { search } : {} });
  return data as PantryResponse;
}

// quantity_g is optional: omit it and the backend stores NULL, meaning "have it,
// amount unknown". Pass a number and the shopping list can subtract it and
// confirm-choice can draw it down.
export async function togglePantryItem(
  ingredient_id: number, have: boolean, quantity_g?: number | null,
) {
  const { data } = await api.post("/meal-plan/pantry/toggle", null, {
    params: {
      ingredient_id,
      have,
      ...(quantity_g == null ? {} : { quantity_g }),
    },
  });
  return data;
}

export async function getPantrySuggestions(): Promise<PantrySuggestion[]> {
  const { data } = await api.get("/meal-plan/pantry/suggestions");
  return (data?.items ?? []) as PantrySuggestion[];
}

// ── GET /meal-plan/combo/{comboId}/dishes ────────────────────────────────
export interface ComboDetailDish {
  food_item_id: number;
  recipe_name: string;
  slot_type: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  ingredients: { name: string; amount_g: number }[];
}

export interface ComboDetailResponse {
  combo_id: number;
  dishes: ComboDetailDish[];
}

export async function getComboDetails(comboId: number): Promise<ComboDetailResponse> {
  const { data } = await api.get(`/meal-plan/combo/${comboId}/dishes`);
  return data;
}

// ── GET /meal-plan/beverages ──────────────────────────────────────────────
// Session 22E: beverages are logged ad hoc (not auto-generated into slots).
export interface Beverage {
  food_item_id: number;
  recipe_name: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber: number;
}

export async function getBeverages(): Promise<Beverage[]> {
  const { data } = await api.get("/meal-plan/beverages");
  return data.beverages ?? [];
}
