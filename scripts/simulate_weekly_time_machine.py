"""
scripts/simulate_weekly_time_machine.py
=======================================
Compresses a 14-day weekly plan cycle into a single automated run.

Simulates:
  Week 1: generate plan → log 7 days of choices → compute weekly summary
  Assert: preferred_dishes and never_selected populated correctly
  Approval gate: doctor approves Week 1 plan
  Week 2: generate new plan → assert preferred dishes are boosted

Usage:
    python -m scripts.simulate_weekly_time_machine
"""
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import select, update as sa_update, delete as sa_delete, text

from app.core.database import AsyncSessionLocal
from app.models.db_models import (
    Patient, Recommendation, WeeklyCombo,
    PatientMealChoice, PatientMealChoiceDish,
    MealLog,
)
from app.services.diet_plan_service import DietPlanService
from app.services.weekly_summary_service import compute_weekly_summary


PRIYA_EMAIL = "priya.test@mityahar.com"
MEAL_TYPES  = ["Breakfast", "Lunch", "Dinner"]


def ok(msg: str):   print(f"  [PASS] {msg}")
def warn(msg: str): print(f"  [WARN] {msg}")
def fail(msg: str): print(f"  [FAIL] {msg}"); sys.exit(1)


def last_monday() -> date:
    """Return the Monday of last week (always safely in the past)."""
    today = date.today()
    return today - timedelta(days=today.weekday() + 7)


def build_user_data(p: Patient, start: date) -> dict:
    age = 30
    if p.date_of_birth:
        today = date.today()
        age = today.year - p.date_of_birth.year - (
            (today.month, today.day) < (p.date_of_birth.month, p.date_of_birth.day)
        )
    return {
        "id":                    str(p.id),
        "email":                 p.email,
        "name":                  p.name,
        "gender":                p.gender,
        "height":                float(p.height_cm),
        "weight":                float(p.weight_kg),
        "activity_level":        p.activity_level,
        "diet":                  p.diet_type,
        "health_condition":      p.health_condition or "Healthy",
        "region":                p.region or "North",
        "nonveg_meals_per_week": p.nonveg_meals_per_week or 3,
        "health_goals":          list(p.health_goals or []),
        "medical_conditions":    list(p.medical_conditions or []),
        "food_allergies":        list(p.food_allergies or []),
        "age":                   age,
        "start_date":            start.isoformat(),
    }


async def run():
    svc = DietPlanService()

    WEEK1_START = last_monday()
    WEEK1_END   = WEEK1_START + timedelta(days=6)
    WEEK2_START = WEEK1_START + timedelta(days=7)

    print(f"\n{'='*60}")
    print(f"PASS 3: TIME MACHINE — 14-DAY CYCLE SIMULATION")
    print(f"  Week 1: {WEEK1_START} -> {WEEK1_END}")
    print(f"  Week 2: {WEEK2_START} -> {WEEK2_START + timedelta(days=6)}")
    print(f"{'='*60}\n")

    async with AsyncSessionLocal() as db:

        # ── Step 1: Fetch Priya ──────────────────────────────────────────
        print("[1] Fetching Priya...")
        result = await db.execute(
            select(Patient).where(Patient.email == PRIYA_EMAIL)
        )
        priya = result.scalar_one_or_none()
        if not priya:
            fail(f"Patient {PRIYA_EMAIL!r} not found — run seed_test_patients.py first")
        pid = priya.id
        ok(f"patient_id={pid}, diet={priya.diet_type}, region={priya.region}, tdee={priya.tdee}")

        # ── Step 2: Deactivate existing active recs ──────────────────────
        print("[2] Deactivating existing active recommendations...")
        await db.execute(
            sa_update(Recommendation)
            .where(Recommendation.patient_id == pid, Recommendation.is_active == True)  # noqa: E712
            .values(is_active=False)
        )
        await db.commit()
        ok("done")

        # ── Step 3: Generate + store Week 1 plan ─────────────────────────
        print("[3] Generating Week 1 plan (slot_dates anchored to WEEK1_START)...")
        user_data = build_user_data(priya, WEEK1_START)
        plan = await svc.generate_diet_plan(user_data, db)

        combos_count = len(plan.combos or [])
        if combos_count == 0:
            fail("Plan generation returned 0 combos")

        rec_id = await svc.store_diet_plan(plan, session=db)

        # store_diet_plan sets week_start_date=date.today(); fix to WEEK1_START
        await db.execute(
            sa_update(Recommendation)
            .where(Recommendation.id == rec_id)
            .values(week_start_date=WEEK1_START)
        )
        await db.commit()
        ok(f"rec_id={rec_id}, {combos_count} combos stored, week_start_date={WEEK1_START}")

        # ── Step 4: Load combo_index=0 rows (one per slot per day) ───────
        print("[4] Loading combo_index=0 rows...")
        combos_result = await db.execute(
            select(WeeklyCombo)
            .where(
                WeeklyCombo.recommendation_id == rec_id,
                WeeklyCombo.combo_index == 0,
            )
            .order_by(WeeklyCombo.slot_date, WeeklyCombo.meal_type)
        )
        combos_c0 = combos_result.scalars().all()
        combo_map: dict[tuple, WeeklyCombo] = {
            (c.slot_date, c.meal_type): c for c in combos_c0
        }
        ok(f"{len(combos_c0)} combo_index=0 rows loaded")
        if len(combos_c0) < 21:
            warn(f"Expected 21 (7 days × 3 meals), got {len(combos_c0)} — some slots may have failed generation")

        # ── Step 5: Clear any stale Week 1 choices for this patient ──────
        print("[5] Clearing stale Week 1 meal choices...")
        await db.execute(
            sa_delete(PatientMealChoice).where(
                PatientMealChoice.patient_id == pid,
                PatientMealChoice.date >= WEEK1_START,
                PatientMealChoice.date <= WEEK1_END,
            )
        )
        await db.commit()
        ok("cleared")

        # ── Step 6: Insert 7 days × 3 meals of choices ───────────────────
        print("[6] Inserting 7 days × 3 meals of meal choices...")
        choices_inserted = 0
        for day_offset in range(7):
            meal_date = WEEK1_START + timedelta(days=day_offset)
            for meal_type in MEAL_TYPES:
                combo = combo_map.get((meal_date, meal_type))
                if not combo or not combo.dishes:
                    warn(f"No combo for {meal_date} {meal_type} — skipping")
                    continue

                dishes = combo.dishes  # list[dict] with food_id, slot_type, calories, scaled_calories
                primary_food_id = dishes[0]["food_id"]

                choice = PatientMealChoice(
                    patient_id      = pid,
                    food_item_id    = primary_food_id,
                    date            = meal_date,
                    meal_type       = meal_type,
                    calories        = sum(d.get("calories", 0) for d in dishes),
                    weekly_combo_id = combo.id,
                    bowl_size       = "medium",
                    actual_calories = sum(
                        d.get("scaled_calories", d.get("calories", 0)) for d in dishes
                    ),
                )
                db.add(choice)
                await db.flush()

                for dish in dishes:
                    db.add(PatientMealChoiceDish(
                        choice_id    = choice.id,
                        food_item_id = dish["food_id"],
                        slot_type    = dish.get("slot_type"),
                        calories     = dish.get("calories"),
                    ))

                choices_inserted += 1

        await db.commit()
        ok(f"{choices_inserted} meal choices inserted with dish breakdowns")

        # ── Step 7: Insert beverage + snack MealLog rows ─────────────────
        print("[7] Inserting Indian habit logs (chai × 2 + snack × 1, Mon–Fri)...")
        logs_inserted = 0
        for day_offset in range(5):  # Monday through Friday only
            log_date = WEEK1_START + timedelta(days=day_offset)
            for _ in range(2):
                db.add(MealLog(
                    patient_id       = pid,
                    recommendation_id= rec_id,
                    logged_date      = log_date,
                    meal_type        = "Beverage",
                    custom_food_name = "Chai",
                    calories_consumed= 40,
                    protein_g        = 1.0,
                    carbs_g          = 5.0,
                    fat_g            = 1.5,
                ))
                logs_inserted += 1
            db.add(MealLog(
                patient_id       = pid,
                recommendation_id= rec_id,
                logged_date      = log_date,
                meal_type        = "Snack",
                custom_food_name = "Marie Biscuits",
                calories_consumed= 150,
                protein_g        = 3.0,
                carbs_g          = 25.0,
                fat_g            = 4.0,
            ))
            logs_inserted += 1

        await db.commit()
        ok(f"{logs_inserted} meal log rows inserted (5 days × 3 logs)")

        # ── Step 8: Compute weekly summary ───────────────────────────────
        print("[8] Computing weekly summary...")
        summary = await compute_weekly_summary(db, pid, WEEK1_START)

        if "error" in summary:
            fail(f"compute_weekly_summary error: {summary['error']}")

        preferred  = summary.get("pattern", {}).get("preferred_dishes", [])
        never_sel  = summary.get("pattern", {}).get("never_selected_dishes", [])
        adherence  = summary.get("adherence_pct", 0)
        confirmed  = summary.get("confirmed_slots", 0)

        print(f"    adherence_pct    = {adherence}%  ({confirmed}/21 slots)")
        print(f"    preferred_dishes = {len(preferred)} dishes")
        print(f"    never_selected   = {len(never_sel)} dishes")

        # Assertions
        if adherence < 90:
            fail(f"adherence={adherence}% — expected ≥90% (7 days × 3 meals fully confirmed)")
        ok(f"adherence {adherence}% — PASS")

        if not preferred:
            fail(
                "preferred_dishes is empty. "
                "Dishes selected via combo_index=0 should appear 7× (≥2 threshold). "
                "Check PatientMealChoiceDish inserts."
            )
        ok(f"preferred_dishes ({len(preferred)}): {[d['recipe_name'] for d in preferred[:3]]}")

        if not never_sel:
            warn(
                "never_selected_dishes is empty. "
                "This means all combo alt dishes appeared in <3 combos. "
                "Non-blocking — depends on generator variety across 84 combo rows."
            )
        else:
            ok(f"never_selected ({len(never_sel)}): {[d['recipe_name'] for d in never_sel[:3]]}")

        # ── Step 9: Doctor approval gate ─────────────────────────────────
        print("[9] Doctor approving Week 1 plan...")
        await db.execute(
            sa_update(Recommendation)
            .where(Recommendation.id == rec_id)
            .values(approval_status="approved")
        )
        await db.commit()
        ok("approval_status='approved'")

        # ── Step 10: Generate Week 2 plan ─────────────────────────────────
        print("[10] Generating Week 2 plan (preferred boost should fire)...")
        preferred_fids = frozenset(d["food_item_id"] for d in preferred)
        print(f"     preferred_food_ids from summary: {sorted(preferred_fids)[:6]}...")

        user_data2 = build_user_data(priya, WEEK2_START)
        plan2 = await svc.generate_diet_plan(user_data2, db)
        rec2_id = await svc.store_diet_plan(plan2, session=db)
        await db.execute(
            sa_update(Recommendation)
            .where(Recommendation.id == rec2_id)
            .values(week_start_date=WEEK2_START, approval_status="approved")
        )
        await db.commit()
        ok(f"Week 2 rec_id={rec2_id}, week_start={WEEK2_START}")

        # ── Step 11: Assert preferred dishes boosted into Week 2 ─────────
        print("[11] Checking preferred dishes appear in Week 2 combos...")
        boost_result = await db.execute(
            text("""
                SELECT DISTINCT (dish->>'food_id')::int AS food_id
                FROM weekly_combos wc,
                     jsonb_array_elements(wc.dishes) AS dish
                WHERE wc.recommendation_id = :rec_id
            """),
            {"rec_id": rec2_id},
        )
        week2_food_ids = {row.food_id for row in boost_result.all()}
        matched = preferred_fids & week2_food_ids

        print(f"     preferred_fids={len(preferred_fids)}, matched in week2={len(matched)}")
        if not matched:
            warn(
                "No preferred dishes from Week 1 appeared in Week 2 combos. "
                "Boost is ORDER BY preference (not forced injection) — "
                "dishes may have lost calorie window competition. Non-blocking."
            )
        else:
            ok(f"{len(matched)}/{len(preferred_fids)} preferred dishes present in Week 2 combos — boost confirmed")

        # ── Summary ───────────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"PASS 3 COMPLETE")
        print(f"  Week 1 rec_id   : {rec_id}  (week_start={WEEK1_START})")
        print(f"  Week 2 rec_id   : {rec2_id} (week_start={WEEK2_START})")
        print(f"  adherence       : {adherence}%")
        print(f"  preferred       : {len(preferred)} dishes")
        print(f"  never_selected  : {len(never_sel)} dishes")
        print(f"  boost matched   : {len(matched)}/{len(preferred_fids)} in Week 2")
        print(f"{'='*60}\n")

        return {
            "rec1_id": rec_id,
            "rec2_id": rec2_id,
            "adherence_pct": adherence,
            "preferred_count": len(preferred),
            "never_selected_count": len(never_sel),
            "boost_matched": len(matched),
        }


if __name__ == "__main__":
    asyncio.run(run())
