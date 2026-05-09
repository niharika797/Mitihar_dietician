// Central query key factory — prevents typos and enables targeted invalidation
export const QUERY_KEYS = {
  // Profile
  ME:             ["me"] as const,
  BMI:            ["bmi"] as const,
  REQUEST_STATUS: ["request-status"] as const,

  // Doctor directory
  DOCTORS:        (search?: string) => ["doctors", search ?? ""] as const,

  // Meal plan
  WEEK_PLAN:      ["meal-plan", "week"] as const,
  PLAN_HISTORY:   ["meal-plan", "history"] as const,
  SHOPPING_LIST:  ["meal-plan", "shopping-list"] as const,

  // Progress
  TODAY:          ["progress", "today"] as const,
  WEEKLY_REPORT:  ["progress", "weekly-report"] as const,
  WEIGHT_HISTORY: (days: number) => ["progress", "weight-history", days] as const,
  STREAK:         ["progress", "streak"] as const,

  // Phase 8 Tier 0 — meal ratings
  MY_RATINGS:     ["progress", "meal-ratings"] as const,

  // Doctor visit / Token 2
  MY_VISIT:       ["my-visit"] as const,
} as const;
