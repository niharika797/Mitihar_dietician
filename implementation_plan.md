# Fix Patient Onboarding: Gender, BMR, TDEE, and Weights

## Root Cause Analysis

The patient onboarding flow has a data gap between registration and onboarding:

1. **Registration** ([register.tsx:48-50](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/mitihar-patient-app/app/%28auth%29/register.tsx#L48-L50)) hardcodes **placeholder** values:
   - `gender: "Other"`, `height: 160`, `weight: 60`

2. **Onboarding Step 1** ([personal-info.tsx](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/mitihar-patient-app/app/%28onboarding%29/personal-info.tsx)) collects the real `gender`, `height_cm`, `weight_kg`, `target_weight_kg` from the user.

3. **Mobile [toPayload()](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/mitihar-patient-app/store/useOnboardingStore.ts#49-78)** ([useOnboardingStore.ts:54-58](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/mitihar-patient-app/store/useOnboardingStore.ts#L54-L58)) sends `gender`, `height_cm`, `weight_kg`, `activity_level`, `diet_type`, [region](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/diet_plan_service.py#34-40) to the API.

4. **Backend [OnboardingRequest](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/patients.py#5-32)** ([patients.py:5-24](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/patients.py#L5-L24)) does **NOT** accept `gender`, `height_cm`, `weight_kg`, `activity_level`, `diet_type`, or [region](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/diet_plan_service.py#34-40). These fields are **silently dropped** by Pydantic.

5. **BMR calculation** ([calculations.py:7-12](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/calculations.py#L7-L12)) returns `0.0` when `gender` is neither `'male'` nor `'female'` — so `gender='Other'` → `BMR=0` → `TDEE=0`.

6. **Doctor dashboard** reads directly from the DB, so it shows the stale `gender='Other'`, `BMR=0 kcal/day`, `TDEE=0 kcal/day`.

---

## Proposed Changes

### Backend — Pydantic Schema

#### [MODIFY] [patients.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/patients.py)

Add the missing fields to [OnboardingRequest](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/patients.py#5-32) so the backend accepts them:

```diff
 class OnboardingRequest(BaseModel):
     date_of_birth: date
+    gender: str
+    height_cm: float = Field(..., gt=0)
+    weight_kg: float = Field(..., gt=0)
+    activity_level: str = Field(default="LA")
+    diet_type: str = Field(default="Vegetarian")
+    region: str = Field(default="North")
+    health_condition: str = Field(default="Healthy")
     health_goals: list[str] = Field(default_factory=list)
```

---

### Backend — Onboarding Endpoint

#### [MODIFY] [patients.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/patients.py)

Update the `/onboarding` endpoint to:
1. **Store** the new fields (`gender`, `height_cm`, `weight_kg`, `activity_level`, `diet_type`, [region](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/diet_plan_service.py#34-40), `health_condition`) from the onboarding body
2. **Use the body values** (not the stale DB values) for BMR/TDEE/BMI calculations

```diff
-    bmr = calculate_bmr(
-        patient.gender,
-        float(patient.weight_kg),
-        float(patient.height_cm),
-        age,
-    )
-    tdee = calculate_tdee(bmr, patient.activity_level)
-    bmi = calculate_bmi(float(patient.height_cm), float(patient.weight_kg))
+    bmr = calculate_bmr(body.gender, body.weight_kg, body.height_cm, age)
+    tdee = calculate_tdee(bmr, body.activity_level)
+    bmi = calculate_bmi(body.height_cm, body.weight_kg)

     await session.execute(
         update(Patient)
         .where(Patient.id == patient.id)
         .values(
+            gender=body.gender,
+            height_cm=body.height_cm,
+            weight_kg=body.weight_kg,
+            activity_level=body.activity_level,
+            diet_type=body.diet_type,
+            region=body.region,
+            health_condition=body.health_condition,
             date_of_birth=body.date_of_birth,
```

Also update the auto-generate diet plan's `user_data` dict to use the newly stored values.

---

### Doctor Dashboard — PatientSummary

#### [MODIFY] [doctor.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/doctor.py)

Add `height_cm`, `weight_kg`, `target_weight_kg`, `activity_level` to the [PatientSummary](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/doctor.py#5-18) schema so the doctor dashboard can display them:

```diff
 class PatientSummary(BaseModel):
     id: int
     name: str
     email: str
     gender: str
+    height_cm: Optional[float]
+    weight_kg: Optional[float]
+    target_weight_kg: Optional[float]
+    activity_level: str
     subscription_status: str
```

#### [MODIFY] [doctorApi.ts](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/mitihar-frontend/apps/src/lib/doctorApi.ts)

Add matching fields to the TypeScript [PatientSummary](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/doctor.py#5-18) interface.

#### [MODIFY] [ProfileTab.tsx](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/mitihar-frontend/apps/src/app/pages/doctor/patient-tabs/ProfileTab.tsx)

Add Height, Weight, Target Weight, Activity Level rows to the Health Metrics card.

---

## Verification Plan

### Automated Tests

Run existing test suite:
```
cd c:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician
python -m pytest tests/test_calculations.py -v
```

### Manual Verification

After changes, use the patient app to:
1. Register a new test patient (name, email, password only)
2. Complete onboarding Step 1 (select **Female**, height **162**, current weight **74**, target weight **68**)
3. Complete remaining onboarding steps
4. Log into the doctor dashboard and navigate to that patient's profile
5. Verify:
   - Gender shows **Female** (not "Other")
   - BMI shows a calculated value (not "—")
   - BMR shows a non-zero value (should be ~1400+ kcal/day)
   - TDEE shows a non-zero value
   - Height, Weight, Target Weight are displayed correctly
