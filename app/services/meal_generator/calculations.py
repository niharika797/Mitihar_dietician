from typing import Optional

def calculate_bmi(height: float, weight: float) -> float:
    height_m = height / 100
    return weight / (height_m ** 2)

def calculate_bmr(gender: str, weight: float, height: float, age: int) -> float:
    if gender.lower() == 'male':
        return (10 * weight) + (6.25 * height) - (5 * age) + 5
    elif gender.lower() == 'female':
        return (10 * weight) + (6.25 * height) - (5 * age) - 161
    else:
        # "Other" / unknown gender — use average of male and female formulas
        male_bmr   = (10 * weight) + (6.25 * height) - (5 * age) + 5
        female_bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
        return (male_bmr + female_bmr) / 2

def calculate_tdee(bmr: float, activity_level: str) -> float:
    multipliers = {
        'S': 1.2, 'LA': 1.375,
        'MA': 1.55, 'VA': 1.725, 'SA': 1.9
    }
    return bmr * multipliers.get(activity_level, 1.2)

def calculate_macronutrients(
    tdee: float,
    health_condition: Optional[str] = None,
    health_sub_goal: Optional[str] = None,
    medical_conditions: Optional[list] = None,
):
    """
    Calculate macronutrient targets from TDEE.

    health_condition:   'Healthy' | 'Gym-Friendly' | 'Diabetic-Friendly'
    health_sub_goal:    Gym    → 'weight_loss' | 'muscle_gain' | 'maintenance'
                        Diabet → 'controlled'   | 'uncontrolled'
    medical_conditions: list of strings from patient onboarding, e.g. ["PCOS/PCOD"]
                        Applied AFTER health_condition — PCOS/Thyroid override macros
                        while keeping plan_type="Healthy" for food/template lookups.
    """
    # ── Step 1: Base macros from health_condition ──────────────────────────
    # Defaults (Healthy)
    protein = (tdee * 0.2)  / 4
    carbs   = (tdee * 0.55) / 4
    fat     = (tdee * 0.25) / 9

    if health_condition == 'Gym-Friendly':
        if health_sub_goal == 'weight_loss':
            protein = (tdee * 0.45) / 4
            carbs   = (tdee * 0.35) / 4
            fat     = (tdee * 0.2)  / 9
        elif health_sub_goal == 'muscle_gain':
            protein = (tdee * 0.4) / 4
            carbs   = (tdee * 0.4) / 4
            fat     = (tdee * 0.2) / 9
        else:  # maintenance or unspecified
            protein = (tdee * 0.35) / 4
            carbs   = (tdee * 0.4)  / 4
            fat     = (tdee * 0.25) / 9

    elif health_condition == 'Diabetic-Friendly':
        if health_sub_goal == 'uncontrolled':
            protein = (tdee * 0.3)  / 4
            carbs   = (tdee * 0.4)  / 4
            fat     = (tdee * 0.25) / 9
        else:  # controlled or unspecified
            protein = (tdee * 0.25) / 4
            carbs   = (tdee * 0.45) / 4
            fat     = (tdee * 0.25) / 9

    # ── Step 2: Medical condition overrides ───────────────────────────────
    # These override the base macros above.
    # Priority order: PCOS > Hypothyroid > Hyperthyroid (if multiple selected).
    # plan_type for food/template queries remains unchanged — only macros differ.
    if medical_conditions:
        mc = [c.lower() for c in medical_conditions]
        has_pcos        = any("pcos" in c or "pcod" in c for c in mc)
        has_hypothyroid = any("hypothyroid" in c for c in mc)
        has_hyperthyroid = any("hyperthyroid" in c for c in mc)

        if has_pcos:
            # PCOS: insulin resistance management — higher protein, reduced carbs
            # Rationale: low-GI diet with 30% protein, 40% carbs, 30% fat
            # Source: clinical consensus (PMC peer-reviewed, multiple sources)
            protein = (tdee * 0.30) / 4
            carbs   = (tdee * 0.40) / 4
            fat     = (tdee * 0.30) / 9

        elif has_hypothyroid:
            # Hypothyroid: modest protein increase, quality (low-GI) carbs
            # Rationale: supports thyroid hormone production and metabolism
            # Source: conservative clinical guidance
            protein = (tdee * 0.28) / 4
            carbs   = (tdee * 0.47) / 4
            fat     = (tdee * 0.25) / 9

        elif has_hyperthyroid:
            # Hyperthyroid: elevated metabolism needs more carbs for energy
            # Rationale: prevent muscle wasting with adequate protein + carb energy
            protein = (tdee * 0.22) / 4
            carbs   = (tdee * 0.58) / 4
            fat     = (tdee * 0.20) / 9

    fiber = (tdee * 14) / 1000
    return protein, carbs, fiber, fat