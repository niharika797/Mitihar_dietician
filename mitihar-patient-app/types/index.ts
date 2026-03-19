// ─── Core domain types — mirrors FastAPI response shapes ──────────────────

// ── Auth ──────────────────────────────────────────────────────────────────
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface GoogleVerifyResponse {
  access_token: string;
  refresh_token: string;
  is_new_user: boolean;
}

// ── Patient / Profile ─────────────────────────────────────────────────────
export type Gender = "Male" | "Female" | "Other";
export type ActivityLevel = "S" | "LA" | "MA" | "VA" | "SA";
export type DietType = "Vegetarian" | "Non-Vegetarian" | "Eggetarian";
export type Region = "North" | "South" | "East" | "West";
export type PacePreference = "slow" | "moderate" | "fast";
export type SubscriptionStatus = "active" | "inactive";
export type UserType = "standalone" | "doctor_assigned";

export interface PatientProfile {
  id: number;
  email: string;
  name: string;
  phone?: string;
  date_of_birth?: string;
  gender: Gender;
  height_cm: number;
  weight_kg: number;
  activity_level: ActivityLevel;
  diet_type: DietType;
  region: Region;
  health_condition: string;
  bmi?: number;
  bmr?: number;
  tdee?: number;
  target_weight_kg?: number;
  health_goals: string[];
  medical_conditions: string[];
  food_allergies: string[];
  dietary_preferences: string[];
  meals_per_day: number;
  fasting_days: string[];
  sleep_hours?: number;
  water_glasses: number;
  occupation?: string;
  smoking: boolean;
  alcohol: boolean;
  user_type: UserType;
  doctor_id?: number;
  subscription_status: SubscriptionStatus;
  subscription_end_date?: string;
  disclaimer_accepted_at?: string;
  nonveg_meals_per_week: number;
  pace_preference?: PacePreference;
  eating_habits: string[];
  // Token 1 fields
  token_1?: string | null;
  token_1_active?: boolean;
  token_1_expiry?: string | null;
  renewal_requested?: boolean;
  expiring_soon?: boolean;
}

// ── Onboarding ────────────────────────────────────────────────────────────
export interface OnboardingPayload {
  date_of_birth: string;
  gender: Gender;
  height_cm: number;
  weight_kg: number;
  activity_level: ActivityLevel;
  diet_type: DietType;
  region: Region;
  health_condition: string;
  target_weight_kg?: number;
  health_goals: string[];
  medical_conditions: string[];
  food_allergies: string[];
  dietary_preferences: string[];
  meals_per_day: 3 | 5;
  fasting_days: string[];
  sleep_hours: number;
  water_glasses: number;
  occupation: string;
  smoking: boolean;
  alcohol: boolean;
  nonveg_meals_per_week: number;
  pace_preference: PacePreference;
  eating_habits: string[];
}

// Local onboarding wizard state (not sent to API yet)
export interface OnboardingWizardState {
  dob_day: string;
  dob_month: string;
  dob_year: string;
  gender: string;
  height_cm: string;
  weight_kg: string;
  target_weight_kg: string;
  activity_level: string;
  health_goals: string[];
  goal_pace: string;
  medical_conditions: string[];
  food_allergies: string[];
  diet_type: string;
  region: string;
  meals_per_day: string;
  fasting_days: string[];
  sleep_hours: number;
  water_glasses: number;
  occupation: string;
  smoking: boolean;
  alcohol: boolean;
  nonveg_meals_per_week: number;
  eating_habits: string[];
  dietary_preferences: string[];
  health_condition: string;
  disclaimer_accepted: boolean;
}

// ── Meal Plan ─────────────────────────────────────────────────────────────
export interface Meal {
  Date: string;
  "Meal Type": string;
  "Menu Names": string;
  "Diet Type": string;
  "Total Calories": number;
  "Total Protein": number;
  "Total Carbs": number;
  "Total Fat": number;
  "Total Fiber": number;
  doctor_note?: string;
  food_id?: number | null;
  recommendation_id?: number | null;
}

// ── Meal Ratings (Phase 8 Tier 0) ─────────────────────────────────────────
export interface MealRating {
  id: number;
  patient_id: number;
  food_item_id: number;
  recommendation_id: number | null;
  rating: 1 | -1;
  rated_at: string;
}

export interface WeeklyPlan {
  [date: string]: Meal[];
}

export interface PlanHistoryItem {
  id: number;
  week_start_date: string;
  version: number;
  is_active: boolean;
  created_at: string;
}

export interface ShoppingItem {
  ingredient_name: string;
  quantity: number;
  unit: string;
  category: string;
  have_at_home: boolean;
}

export interface ShoppingListResponse {
  [category: string]: ShoppingItem[];
}

// ── Progress ──────────────────────────────────────────────────────────────
export interface TodaySummary {
  tdee: number;
  calories_consumed: number;
  water: number;
  steps: number;
  streak: number;
}

export interface MealLogEntry {
  id: number;
  logged_date: string;
  meal_type: string;
  calories_consumed: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
  notes?: string;
}

export interface WeightEntry {
  date: string;
  weight_kg: number;
}

export interface WeeklyReport {
  [date: string]: {
    calories_consumed: number;
    water_glasses: number;
    steps: number;
    weight_kg?: number;
  };
}

export interface BMIResponse {
  bmi: number;
  category: "Underweight" | "Normal" | "Overweight" | "Obese";
}

// ── Doctor Connection ─────────────────────────────────────────────────────
export type RequestStatus = "pending" | "accepted" | "rejected" | "none";

export interface RequestStatusResponse {
  status: RequestStatus;
}

export interface ActivateResponse {
  message: string;
  doctor_name?: string;
  access_token?: string;
  token_type?: string;
}

// ── Notifications (local only — FCM Phase 5) ──────────────────────────────
export type NotificationType = "plan_update" | "reminder" | "streak" | "info";

export interface AppNotification {
  id: number | string;
  type: NotificationType;
  title: string;
  body: string;
  time: string;
  date?: string;   // "today" | "yesterday" | "YYYY-MM-DD"
  read: boolean;
}

// ── Computed health stats (derived from PatientProfile) ───────────────────
export interface HealthStats {
  bmi: number;
  bmiCategory: "Underweight" | "Normal" | "Overweight" | "Obese";
  bmr: number;
  tdee: number;
  dailyTarget: number;
}
