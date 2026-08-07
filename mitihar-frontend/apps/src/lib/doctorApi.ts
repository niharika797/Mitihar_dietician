/**
 * doctorApi.ts
 * All TypeScript types and API functions for the Doctor Dashboard.
 * Types mirror the FastAPI Pydantic schemas in app/schemas/doctor.py exactly.
 */

import apiClient from './axios';

// ── Response types ────────────────────────────────────────────────────────────

export interface PatientSummary {
  id: number;
  name: string;
  email: string;
  gender: string;
  subscription_status: string;
  user_type: string;
  date_of_birth: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  target_weight_kg: number | null;
  bmi: number | null;
  bmr: number | null;
  tdee: number | null;
  activity_level: string | null;
  diet_type: string | null;
  health_condition: string | null;
  health_goals: string[];
  medical_conditions: string[];
  food_allergies: string[];
  meals_per_day: number;
  // Token 1 fields
  token_1: string | null;
  token_1_active: boolean;
  token_1_expiry: string | null;
  renewal_requested: boolean;
  renewal_requested_at: string | null;
  expiring_soon: boolean;
}


export interface PatientVisit {
  id: number;
  patient_id: number;
  doctor_id: number;
  token_2: string;
  cycle_start: string;
  cycle_expiry: string;
  last_charged_at: string | null;
  visit_counter: number;
  created_at: string;
}

/** Why Token 2 could not be shown.
 *  Mirrors FLAG_VISIT_REASONS in app/schemas/doctor.py and the
 *  ck_pva_reason_code constraint — the server rejects anything else, so a
 *  drifted list here fails loudly with a 422 rather than storing junk. */
export const FLAG_VISIT_REASONS = [
  { code: 'phone_not_present', label: 'Phone not with patient' },
  { code: 'battery_dead',      label: 'Phone battery dead' },
  { code: 'app_issue',         label: "App issue — couldn't show Token 2" },
  { code: 'signed_out',        label: 'Patient signed out / login trouble' },
  { code: 'other',             label: 'Other (describe below)' },
] as const;

export type FlagVisitReason = (typeof FLAG_VISIT_REASONS)[number]['code'];

/** A visit the doctor flagged because Token 2 could not be shown, plus the
 *  patient's answer. status: pending until they respond, then approved/rejected. */
export interface FlaggedVisit {
  id: number;
  patient_id: number;
  patient_name: string;
  status: 'pending' | 'approved' | 'rejected';
  visit_date: string;
  reason_code: FlagVisitReason | null;
  /** Server-resolved display text, so both clients show identical wording. */
  reason_label: string;
  /** Only ever set when reason_code === 'other'. */
  doctor_note: string | null;
  responded_at: string | null;
  created_at: string | null;
}

export interface RecordVisitResponse {
  charged: boolean;
  visit_counter: number;
  last_charged_at: string | null;
  message: string;
}

export interface RenewalApproveResponse {
  message: string;
  token_1: string;
  token_2: string;
  token_1_expiry: string;
}

export interface BulkRenewalResponse {
  approved_count: number;
  patient_ids: number[];
}

export interface PendingRenewalItem {
  patient_id: number;
  patient_name: string;
  patient_email: string;
  token_1: string | null;
  renewal_requested_at: string | null;
  token_1_expiry: string | null;
}


export interface PaginatedPatients {
  patients: PatientSummary[];
  total: number;
  page: number;
  page_size: number;
}

export interface Dish {
  food_id: number | null;
  recipe_name: string;
  slot_type: string;
  calories: number;
  // Session 22E (Bug 2): calories stays unscaled per-serving; scaled_calories =
  // calories × factor is the portion-adjusted value to display. Optional for
  // legacy dishes generated before 22E.
  scaled_calories?: number;
  factor?: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber: number;
  is_custom_override?: boolean;
}

export interface MealEntry {
  Date: string;
  'Meal Type': string;
  'Menu Names': string;
  'Diet Type': string;
  'Total Calories': number;
  'Total Protein': number;
  'Total Carbs': number;
  'Total Fat': number;
  'Total Fiber': number;
  // Session 22E (Bug 2): the slot's generation-time budget target. 'Total Calories'
  // is now Σ(scaled_calories); 'Target Calories' is what it used to represent and
  // anchors the doctor >10% divergence warning. Optional for legacy plans.
  'Target Calories'?: number;
  doctor_note?: string;
  food_id?: number;
  dishes?: Dish[];
  recommendation_id?: number;
}

export interface RecommendationDetail {
  id: number;
  patient_id: number;
  week_start_date: string | null;
  meals: MealEntry[];
  ingredient_checklist: unknown[];
  is_active: boolean;
  generated_by: string;
  doctor_notes: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface PatientRequestDetail {
  id: number;
  patient_id: number;
  doctor_id: number;
  status: string;
  rejection_note: string | null;
  requested_at: string;
  responded_at: string | null;
  patient: PatientSummary;
}

export interface SubscriptionCodeDetail {
  id: number;
  code: string;
  is_used: boolean;
  used_by_patient_id: number | null;
  used_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface MealLogEntry {
  id: number;
  logged_date: string;
  meal_type: string;
  calories_consumed: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  recommendation_id: number | null;
  custom_food_name: string | null;
  notes: string | null;
}

export interface PatientLogsResponse {
  patient_id: number;
  period_days: number;
  meal_logs: MealLogEntry[];
}

export interface PatientProgressEntry {
  log_date: string;
  weight_kg: number | null;
  water_glasses: number | null;
  steps: number | null;
  streak_days: number;
}

export interface PatientProgressResponse {
  patient_id: number;
  period_days: number;
  progress_logs: PatientProgressEntry[];
}

export interface ClinicalNoteResponse {
  id: number;
  doctor_id: number;
  patient_id: number;
  note_type: string;
  content: string;
  is_private: boolean;
  created_at: string;
  updated_at: string;
}

export interface FoodItemSummary {
  id: number;
  recipe_name: string;
  slot_type: string;
  serving_weight_g: number | null;
  sodium_per_serving: number | null;
  cal_per_serving: number;
  protein_per_serving: number;
  carbs_per_serving: number;
  fat_per_serving: number;
  fiber_per_serving: number;
  diet_type: string;
  meal_time_tags: string[];
  plan_type_tags: string[];
  avoid_tags: string[];
  prefer_tags: string[];
  source: string;
  is_verified: boolean;
  image_url: string | null;
}

export interface RecipeTagsResponse {
  food_item_id: number;
  recipe_name: string;
  avoid_tags: string[];
  prefer_tags: string[];
  is_verified: boolean;
}

export interface DishPreference {
  food_id: number;
  recipe_name: string;
  calories_per_serving: number;
  slot_type: string;
}

export interface MealConfigResponse {
  meal_split: { Breakfast: number; Lunch: number; Dinner: number };
  buffer_pct: number;
  pinned_dishes: DishPreference[];
  blocked_dishes: DishPreference[];
}

export interface MealConfigPatchResult extends MealConfigResponse {
  config_saved: boolean;
  plan_regenerated: boolean;
  error?: string;
}

export interface DashboardStats {
  total_patients: number;
  active_patients: number;
  pending_requests: number;
  plans_generated_this_week: number;
  inactive_patients: { patient_id: number; name: string; email: string }[];
  expiring_soon: { patient_id: number; name: string; subscription_end_date: string }[];
}

// ── v2 weekly plan types ─────────────────────────────────────────────────────

export interface DishInCombo {
  food_id: number | null;
  recipe_name: string;
  slot_type: string;
  calories: number;
}

export interface ComboEntry {
  combo_id: number;
  combo_index: number;
  total_calories: number;
  slot_composition: string;
  dishes: DishInCombo[];
}

export interface WeeklyPlanResponse {
  recommendation_id: number;
  generation_version: number;
  approval_status: string;
  week_start: string;
  combos_available: boolean;
  plan: Record<string, Record<string, ComboEntry[]>>;
}

export interface WeeklySummaryDay {
  date: string;
  planned_calories: number;
  confirmed_calories: number;
  meals_confirmed: number;
  meals_total: number;
  bowl_size_breakdown: Record<string, number>;
  breakfast_confirmed: boolean;
  lunch_confirmed: boolean;
  dinner_confirmed: boolean;
}

export interface DishFrequencyEntry {
  food_item_id: number;
  recipe_name: string;
  times_selected: number;
  times_offered: number;
  bowl_sizes: string[];
}

export interface WeeklySummaryData {
  week_start: string;
  week_end: string;
  total_slots: number;
  confirmed_slots: number;
  days_with_all_confirmed: number;
  adherence_pct: number;
  per_day: WeeklySummaryDay[];
  dish_frequency: DishFrequencyEntry[];
  pattern: {
    preferred_dishes: { food_item_id: number; recipe_name: string }[];
    never_selected_dishes: { food_item_id: number; recipe_name: string }[];
    most_selected_dish: DishFrequencyEntry | null;
    least_selected_dish: DishFrequencyEntry | null;
  };
  week_totals: {
    planned_calories: number;
    confirmed_calories: number;
    avg_bowl_size: string;
  };
  error?: string;
}

/** @deprecated Use WeeklySummaryData */
export interface WeeklySummaryResponse {
  week_start: string;
  days: WeeklySummaryDay[];
  week_totals: {
    planned_calories: number;
    confirmed_calories: number;
    avg_bowl_size: string;
  };
}

export interface PendingApproval {
  patient_id: number;
  patient_name: string;
  recommendation_id: number;
}

export interface PendingApprovalsResponse {
  pending: PendingApproval[];
}

export interface RecipeCreateBody {
  recipe_name: string;
  slot_type: string;
  cal_per_serving: number;
  protein_per_serving: number;
  carbs_per_serving: number;
  fat_per_serving: number;
  fiber_per_serving: number;
  serving_weight_g: number;
  sodium_per_serving?: number;
  diet_type: string;
  meal_time_tags: string[];
  plan_type_tags: string[];
  ingredients: { name: string; amount_g: number }[];
  region_tags: string[];
  submit_to_global: boolean;  // false = library only, true = also pending admin approval for global
}

// ── API functions ─────────────────────────────────────────────────────────────

export const doctorApi = {
  // Dashboard
  getDashboard: () =>
    apiClient.get<DashboardStats>('/doctor/dashboard').then(r => r.data),

  // Patients
  listPatients: (page: number, search: string) =>
    apiClient
      .get<PaginatedPatients>('/doctor/patients', {
        params: { page, page_size: 10, ...(search.trim() ? { search: search.trim() } : {}) },
      })
      .then(r => r.data),

  getPatient: (id: number) =>
    apiClient.get<PatientSummary>(`/doctor/patients/${id}`).then(r => r.data),

  // Plans
  getPatientPlan: (id: number) =>
    apiClient
      .get<RecommendationDetail>(`/doctor/patients/${id}/plan`)
      .then(r => r.data),

  // Logs
  getPatientLogs: (id: number, days = 7) =>
    apiClient
      .get<PatientLogsResponse>(`/doctor/patients/${id}/logs`, { params: { days } })
      .then(r => r.data),

  // Notes
  getPatientNotes: (id: number) =>
    apiClient
      .get<ClinicalNoteResponse[]>(`/doctor/patients/${id}/notes`)
      .then(r => r.data),

  addPatientNote: (id: number, content: string, note_type = 'general') =>
    apiClient
      .post<ClinicalNoteResponse>(`/doctor/patients/${id}/notes`, {
        content,
        note_type,
        is_private: true,
      })
      .then(r => r.data),

  // Requests
  listRequests: () =>
    apiClient.get<PatientRequestDetail[]>('/doctor/requests').then(r => r.data),

  acceptRequest: (id: number) =>
    apiClient.post(`/doctor/requests/${id}/accept`).then(r => r.data),

  rejectRequest: (id: number, rejection_note?: string) =>
    apiClient
      .post(`/doctor/requests/${id}/reject`, { rejection_note: rejection_note ?? null })
      .then(r => r.data),

  // Subscription codes
  listCodes: () =>
    apiClient
      .get<SubscriptionCodeDetail[]>('/doctor/subscription-codes')
      .then(r => r.data),

  generateCodes: (count: number, expires_in_days = 30) =>
    apiClient
      .post<SubscriptionCodeDetail[]>('/doctor/subscription-codes', {
        count,
        expires_in_days,
      })
      .then(r => r.data),

  // Plan override
  overridePlan: (id: number, body: { meals?: unknown[]; doctor_notes?: string }) =>
    apiClient.put<RecommendationDetail>(`/doctor/patients/${id}/plan`, body).then(r => r.data),

  // Recipe assign
  assignRecipe: (
    recipeId: number,
    body: { patient_ids: number[]; meal_type: string; meal_date: string; note?: string },
  ) => apiClient.post(`/doctor/recipes/${recipeId}/assign`, body).then(r => r.data),

  // MFA setup flow (auth endpoints, not doctor endpoints)
  mfaSetup: () =>
    apiClient
      .post<{ message: string; totp_uri: string }>('/auth/doctor/mfa-setup')
      .then(r => r.data),

  mfaConfirm: (totp_code: string) =>
    apiClient
      .post<{ message: string }>('/auth/doctor/mfa-confirm', { totp_code })
      .then(r => r.data),

  mfaDisable: (totp_code: string) =>
    apiClient
      .post<{ message: string }>('/auth/doctor/mfa-disable', { totp_code })
      .then(r => r.data),

  // Fetch all patients (for assign modal — page_size=100)
  listAllPatients: () =>
    apiClient
      .get<PaginatedPatients>('/doctor/patients', { params: { page: 1, page_size: 100 } })
      .then(r => r.data.patients),

  // Recipes
  browseRecipes: (params: { search?: string; meal_time?: string; is_verified?: boolean; page?: number }) =>
    apiClient
      .get<FoodItemSummary[]>('/doctor/recipes', {
        params: { page_size: 20, page: 1, ...params },
      })
      .then(r => r.data),

  addRecipe: (body: RecipeCreateBody) =>
    apiClient.post<FoodItemSummary>('/doctor/recipes', body).then(r => r.data),

  // Browse doctor's personal recipe library (own unverified submissions)
  browseMyLibrary: (params: { search?: string; meal_time?: string; page?: number }) =>
    apiClient
      .get<FoodItemSummary[]>('/doctor/recipes', {
        params: { page_size: 50, page: 1, my_library: true, ...params },
      })
      .then(r => r.data),

  patchDish: (
    patientId: number,
    date: string,
    mealType: string,
    dishIndex: number,
    body: {
      action: 'swap' | 'remove' | 'add';
      replacement_food_id?: number | null;
      custom_dish?: {
        recipe_name: string;
        calories: number;
        protein?: number;
        carbs?: number;
        fat?: number;
        fiber?: number;
      } | null;
      flag_for_database?: boolean;
      slot_type?: string;
    },
  ) =>
    apiClient
      .patch(
        `/doctor/patients/${patientId}/plan/meals/${date}/${mealType}/dishes/${dishIndex}`,
        body,
      )
      .then(r => r.data),

  patchWeeklyDish: (
    patientId: number,
    comboId: number,
    dishIndex: number,
    body: {
      action: 'swap' | 'add' | 'remove';
      food_item_id?: number;
      doctor_note?: string;
    },
  ) =>
    apiClient
      .patch(
        `/doctor/patients/${patientId}/weekly-plan/combos/${comboId}/dishes/${dishIndex}`,
        body,
      )
      .then(r => r.data),

  // Add a custom dish directly to a patient's meal JSONB (no food_items record created by default)
  addCustomDish: (
    patientId: number,
    date: string,
    mealType: string,
    body: {
      recipe_name: string;
      calories: number;
      protein: number;
      carbs: number;
      fat: number;
      fiber: number;
      diet_type?: string;
      slot_type?: string;
      add_to_library?: boolean;
      serving_weight_g?: number;
      combo_index?: number;
    },
  ) =>
    apiClient
      .post(`/doctor/patients/${patientId}/plan/meals/${date}/${mealType}/add`, body)
      .then(r => r.data),

  // Add a note to a specific meal slot in a patient's active plan
  addMealNote: (patientId: number, meal_date: string, meal_type: string, note: string) =>
    apiClient
      .post(`/doctor/patients/${patientId}/plan/notes`, { meal_date, meal_type, note })
      .then(r => r.data),

  // Visit recording. token_2 is REQUIRED by the endpoint (RecordVisitRequest,
  // min_length=5) — it is the fraud check: the patient reads it off their app
  // and the doctor types it here. Omitting it 422s.
  recordVisit: (patientId: number, token_2: string) =>
    apiClient
      .post<RecordVisitResponse>(`/doctor/patients/${patientId}/record-visit`, { token_2 })
      .then(r => r.data),

  // Fallback when the patient can't show Token 2 (phone forgotten/lost). Creates a
  // PendingVisitApproval instead of charging immediately — the patient confirms in
  // their app before the visit is recorded.
  // doctor_note is only accepted when reason_code === 'other'; the server drops
  // it otherwise, so the patient never sees free text beside a charge request.
  flagVisit: (patientId: number, reason_code: FlagVisitReason, doctor_note?: string) =>
    apiClient
      .post<{ message: string; pending_visit_id: number }>(
        `/doctor/patients/${patientId}/flag-visit`,
        { reason_code, doctor_note: doctor_note?.trim() || null },
      )
      .then(r => r.data),

  // Flagged visits + whatever the patient answered. Without this the doctor
  // could raise a flag but never see the confirm/deny that decides billing.
  getFlaggedVisits: (params?: { patientId?: number; answeredOnly?: boolean; limit?: number }) =>
    apiClient
      .get<FlaggedVisit[]>('/doctor/flagged-visits', {
        params: {
          patient_id: params?.patientId,
          answered_only: params?.answeredOnly,
          limit: params?.limit,
        },
      })
      .then(r => r.data),

  getPatientVisits: (patientId: number) =>
    apiClient.get<PatientVisit[]>(`/doctor/patients/${patientId}/visits`).then(r => r.data),

  // Renewals
  requestRenewal: (patientId: number) =>
    apiClient.post(`/doctor/patients/${patientId}/request-renewal`).then(r => r.data),

  approveRenewal: (patientId: number) =>
    apiClient.post<RenewalApproveResponse>(`/doctor/patients/${patientId}/approve-renewal`).then(r => r.data),

  approveAllRenewals: () =>
    apiClient.post<BulkRenewalResponse>('/doctor/patients/approve-all-renewals').then(r => r.data),

  getPendingRenewals: () =>
    apiClient.get<PendingRenewalItem[]>('/doctor/pending-renewals').then(r => r.data),

  // Two Gemini nutrition routes exist and BOTH are live — do not treat either as dead:
  //   /doctor/recipes/estimate — field `dish_name`, rate-limited 10/hour. Used here
  //     and by pages/doctor/Recipes.tsx.
  //   /doctor/recipes/lookup   — field `food_name`, no rate limit. Used by its own
  //     local helper in patient-tabs/PlanTab.tsx.
  // An earlier note here claimed /recipes/lookup did not exist and that `food_name`
  // was a wrong field name. Both claims were incorrect: the route is defined at
  // app/routers/doctor.py:2650 and its RecipeLookupRequest declares `food_name`.
  // This function deliberately uses /recipes/estimate; PlanTab's caller is not a bug.
  fetchNutritionFromGemini: (dishName: string) =>
    apiClient
      .post<{
        dish_name: string;
        calories: string;
        protein: string;
        carbs: string;
        fat: string;
        fiber: string;
      }>('/doctor/recipes/estimate', { dish_name: dishName })
      .then(r => r.data),

  // Meal config
  getMealConfig: (patientId: number) =>
    apiClient.get<MealConfigResponse>(`/doctor/patients/${patientId}/meal-config`).then(r => r.data),

  patchMealConfig: (
    patientId: number,
    body: { meal_split?: { Breakfast: number; Lunch: number; Dinner: number } | null; regenerate_plan?: boolean },
  ) =>
    apiClient.patch<MealConfigPatchResult>(`/doctor/patients/${patientId}/meal-config`, body).then(r => r.data),

  pinDish: (patientId: number, food_id: number) =>
    apiClient.post(`/doctor/patients/${patientId}/meal-config/pin`, { food_id }).then(r => r.data),

  unpinDish: (patientId: number, food_id: number) =>
    apiClient.delete(`/doctor/patients/${patientId}/meal-config/pin/${food_id}`).then(r => r.data),

  blockDish: (patientId: number, food_id: number) =>
    apiClient.post(`/doctor/patients/${patientId}/meal-config/block`, { food_id }).then(r => r.data),

  unblockDish: (patientId: number, food_id: number) =>
    apiClient.delete(`/doctor/patients/${patientId}/meal-config/block/${food_id}`).then(r => r.data),

  patchRecipeTags: (id: number, body: { avoid_tags: string[]; prefer_tags: string[] }) =>
    apiClient.patch<RecipeTagsResponse>(`/doctor/recipes/${id}/tags`, body).then(r => r.data),

  // v2 weekly plan
  getWeeklyPlan: (patientId: number) =>
    apiClient.get<WeeklyPlanResponse>(`/doctor/patients/${patientId}/weekly-plan`).then(r => r.data),

  approveWeeklyPlan: (patientId: number) =>
    apiClient.post(`/doctor/patients/${patientId}/weekly-plan/approve`, {}).then(r => r.data),

  swapCombo: (patientId: number, comboId: number) =>
    apiClient.post(`/doctor/patients/${patientId}/weekly-plan/combos/${comboId}/swap`).then(r => r.data),

  getWeeklySummary: (patientId: number, weekStart?: string) =>
    apiClient.get<WeeklySummaryData>(
      `/doctor/patients/${patientId}/weekly-summary`,
      weekStart ? { params: { week_start: weekStart } } : undefined,
    ).then(r => r.data),

  getPendingApprovals: () =>
    apiClient.get<PendingApprovalsResponse>('/doctor/pending-approvals').then(r => r.data),

  // ── Data Review (shared-data governance: read-only list + flag-only writes) ──
  dataReviewDishes: (search?: string, page = 1) =>
    apiClient.get<DataReviewDish[]>('/doctor/data-review/dishes', {
      params: { page, page_size: 50, ...(search ? { search } : {}) },
    }).then(r => r.data),

  flagDish: (body: { food_item_id: number; field?: string; reason: string; suggested_value?: string }) =>
    apiClient.post('/doctor/data-review/flag', body).then(r => r.data),

  myFlags: () =>
    apiClient.get<MyFlag[]>('/doctor/data-review/my-flags').then(r => r.data),
};

export interface DataReviewDish {
  id: number;
  recipe_name: string;
  slot_type: string;
  diet_type: string;
  cal_per_serving: number;
  is_verified: boolean;
  source: string;
}

export interface MyFlag {
  id: number;
  target_id: number;
  field_changed: string;
  reason: string;
  status: string;
  created_at: string | null;
  reviewed_at: string | null;
}
