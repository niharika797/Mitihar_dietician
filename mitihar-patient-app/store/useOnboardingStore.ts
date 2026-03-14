import { create } from "zustand";
import type { OnboardingWizardState, OnboardingPayload, Gender, ActivityLevel, DietType, Region, PacePreference } from "../types";

const DEFAULT_STATE: OnboardingWizardState = {
  dob_day: "", dob_month: "", dob_year: "",
  gender: "",
  height_cm: "", weight_kg: "", target_weight_kg: "",
  activity_level: "lightly_active",
  health_goals: ["weight_loss"],
  goal_pace: "moderate",
  medical_conditions: [],
  food_allergies: ["None"],
  diet_type: "Vegetarian",
  region: "North",
  meals_per_day: "3",
  fasting_days: [],
  sleep_hours: 7,
  water_glasses: 8,
  occupation: "",
  smoking: false,
  alcohol: false,
  nonveg_meals_per_week: 0,
  eating_habits: [],
  dietary_preferences: [],
  disclaimer_accepted: false,
};

const ACTIVITY_MAP: Record<string, ActivityLevel> = {
  sedentary: "S", lightly_active: "LA",
  moderately_active: "MA", very_active: "VA", super_active: "SA",
};

interface OnboardingStore {
  data: OnboardingWizardState;
  update: (partial: Partial<OnboardingWizardState>) => void;
  reset: () => void;
  // Converts wizard state → API payload. Throws if required fields missing.
  toPayload: () => OnboardingPayload;
}

export const useOnboardingStore = create<OnboardingStore>((set, get) => ({
  data: DEFAULT_STATE,

  update: (partial) =>
    set((s) => ({ data: { ...s.data, ...partial } })),

  reset: () => set({ data: DEFAULT_STATE }),

  toPayload: (): OnboardingPayload => {
    const d = get().data;
    const dob = `${d.dob_year}-${d.dob_month.padStart(2, "0")}-${d.dob_day.padStart(2, "0")}`;
    return {
      date_of_birth:         dob,
      gender:                d.gender as Gender,
      height_cm:             parseFloat(d.height_cm),
      weight_kg:             parseFloat(d.weight_kg),
      activity_level:        ACTIVITY_MAP[d.activity_level] ?? "LA",
      diet_type:             d.diet_type as DietType,
      region:                d.region as Region,
      health_condition:      "Healthy",
      target_weight_kg:      parseFloat(d.target_weight_kg),
      health_goals:          d.health_goals,
      medical_conditions:    d.medical_conditions,
      food_allergies:        d.food_allergies,
      dietary_preferences:   d.dietary_preferences,
      meals_per_day:         parseInt(d.meals_per_day) as 3 | 5,
      fasting_days:          d.fasting_days,
      sleep_hours:           d.sleep_hours,
      water_glasses:         d.water_glasses,
      occupation:            d.occupation,
      smoking:               d.smoking,
      alcohol:               d.alcohol,
      nonveg_meals_per_week: d.nonveg_meals_per_week,
      pace_preference:       d.goal_pace as PacePreference,
      eating_habits:         d.eating_habits,
    };
  },
}));
