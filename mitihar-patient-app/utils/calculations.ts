import type { ActivityLevel, Gender, HealthStats } from "../types";

// Activity multipliers matching the backend's TDEE logic
const ACTIVITY_MULTIPLIERS: Record<ActivityLevel, number> = {
  S:  1.2,    // Sedentary
  LA: 1.375,  // Lightly Active
  MA: 1.55,   // Moderately Active
  VA: 1.725,  // Very Active
  SA: 1.9,    // Super Active
};

// Maps onboarding string keys → ActivityLevel
const ACTIVITY_MAP: Record<string, ActivityLevel> = {
  sedentary:          "S",
  lightly_active:     "LA",
  moderately_active:  "MA",
  very_active:        "VA",
  super_active:       "SA",
  S: "S", LA: "LA", MA: "MA", VA: "VA", SA: "SA",
};

export function calcBMI(weight_kg: number, height_cm: number): number {
  const h = height_cm / 100;
  return parseFloat((weight_kg / (h * h)).toFixed(1));
}

export function bmiCategory(bmi: number): HealthStats["bmiCategory"] {
  if (bmi < 18.5) return "Underweight";
  if (bmi < 25)   return "Normal";
  if (bmi < 30)   return "Overweight";
  return "Obese";
}

// Mifflin-St Jeor formula — matches backend and reference app exactly
export function calcBMR(weight_kg: number, height_cm: number, age: number, gender: Gender): number {
  if (gender === "Male") {
    return Math.round(88.36 + 13.4 * weight_kg + 4.8 * height_cm - 5.7 * age);
  }
  return Math.round(447.6 + 9.2 * weight_kg + 3.1 * height_cm - 4.3 * age);
}

export function calcTDEE(bmr: number, activityLevel: string): number {
  const key = ACTIVITY_MAP[activityLevel] ?? "LA";
  return Math.round(bmr * ACTIVITY_MULTIPLIERS[key]);
}

// Daily calorie target = TDEE - 400 kcal deficit (moderate weight loss)
export function calcDailyTarget(tdee: number): number {
  return tdee - 400;
}

export function calcAgeFromDOB(dob: string): number {
  const birthYear = new Date(dob).getFullYear();
  return new Date().getFullYear() - birthYear;
}

export function computeHealthStats(params: {
  weight_kg: number;
  height_cm: number;
  date_of_birth: string;
  gender: Gender;
  activity_level: string;
}): HealthStats {
  const { weight_kg, height_cm, date_of_birth, gender, activity_level } = params;
  const age = calcAgeFromDOB(date_of_birth);
  const bmi = calcBMI(weight_kg, height_cm);
  const bmr = calcBMR(weight_kg, height_cm, age, gender);
  const tdee = calcTDEE(bmr, activity_level);
  return {
    bmi,
    bmiCategory: bmiCategory(bmi),
    bmr,
    tdee,
    dailyTarget: calcDailyTarget(tdee),
  };
}
