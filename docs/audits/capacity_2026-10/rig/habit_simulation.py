"""
Simulation of ingredient-habit learning on the rig DB.
compute_weekly_summary commits, so this WRITES to the rig DB: reset it afterwards (rig/reset_db.sh).

  PERF_ENV=<perf.env> venv/Scripts/python.exe docs/audits/capacity_2026-10/rig/habit_simulation.py

A synthetic patient (env DIET) eats a breakfast with HABIT every day for 4 weeks. We compare the plan generated
before and after, and check the safety cases: allergy, thin pool, idempotent weekly job, is_usual.
"""
import asyncio, json, os, random, re, sys, time
from datetime import date, timedelta

sys.path.insert(0, os.getcwd())
pw = re.search(r"^PERF_PG_PASSWORD=(.*)$", open(os.environ["PERF_ENV"]).read(), re.M).group(1).strip()
os.environ["DATABASE_URL"] = f"postgresql+asyncpg://admin:{pw}@localhost:15432/mityahar_db"

from sqlalchemy import select, event, delete
from app.core.database import AsyncSessionLocal, engine
from app.models.db_models import (
    Patient, Recommendation, FoodItem, Ingredient, RecipeIngredient, PatientMealChoice,
    PatientMealChoiceDish, WeeklyPatientSummary, PatientPantry,
)
from app.routers import meal_plan as mp
from app.services.diet_plan_service import DietPlanService
from app.services.ingredient_habits import load_habits
from app.services.weekly_summary_service import compute_weekly_summary

HABIT = os.environ.get("HABIT", "paneer")    # ingredient the synthetic patient keeps eating
DIET = os.environ.get("DIET", "Vegetarian")
stmts = [0]
event.listen(engine.sync_engine, "before_cursor_execute", lambda *a, **k: stmts.__setitem__(0, stmts[0] + 1))


def user_data(p, allergies=None):
    dob = p.date_of_birth
    age = date.today().year - dob.year - ((date.today().month, date.today().day) < (dob.month, dob.day)) if dob else 30
    return {
        "id": str(p.id), "email": p.email, "name": p.name, "gender": p.gender,
        "height": float(p.height_cm), "weight": float(p.weight_kg), "activity_level": p.activity_level,
        "diet": p.diet_type, "health_condition": p.health_condition or "Healthy", "region": p.region or "North",
        "nonveg_meals_per_week": p.nonveg_meals_per_week or 3, "health_goals": list(p.health_goals or []),
        "medical_conditions": list(p.medical_conditions or []),
        "food_allergies": allergies if allergies is not None else list(p.food_allergies or []), "age": age,
    }


def has_habit(dishes):
    return any(HABIT in " ".join(i["name"].lower().split()) for d in dishes for i in d["ingredients"])


async def gen(s, p, label, *, allergies=None, mutate=None):
    ud = user_data(p, allergies)
    random.seed(7)
    stmts[0] = 0
    t = time.perf_counter()
    plan = await DietPlanService().generate_diet_plan(ud, s) if mutate is None else await mutate(ud, s)
    dt, n = time.perf_counter() - t, stmts[0]
    c = plan.combos
    bf1 = [x for x in c if x["meal_type"] == "Breakfast" and x["combo_index"] == 1]
    bf_all = [x for x in c if x["meal_type"] == "Breakfast"]
    print(f"[{label}] combos={len(c)} time={dt:.2f}s statements={n} "
          f"breakfast combo1 with habit={sum(has_habit(x['dishes']) for x in bf1)}/{len(bf1)} "
          f"all breakfast combos with habit={sum(has_habit(x['dishes']) for x in bf_all)}/{len(bf_all)}")
    return plan


async def main():
    async with AsyncSessionLocal() as s:
        p = (await s.execute(
            select(Patient).join(Recommendation, Recommendation.patient_id == Patient.id)
            .where(Patient.email.like("perfpat%"), Patient.diet_type == DIET,
                   Recommendation.is_active == True, Recommendation.generation_version == 2).limit(1)  # noqa: E712
        )).scalars().first()
        rec = (await s.execute(select(Recommendation).where(
            Recommendation.patient_id == p.id, Recommendation.is_active == True))).scalars().first()  # noqa: E712
        await s.execute(delete(WeeklyPatientSummary).where(WeeklyPatientSummary.patient_id == p.id))
        await s.execute(delete(PatientPantry).where(PatientPantry.patient_id == p.id))
        await s.execute(delete(PatientMealChoice).where(PatientMealChoice.patient_id == p.id))
        print(f"patient {p.id} diet={p.diet_type} allergies={p.food_allergies} habit ingredient='{HABIT}'")

        print("\n== 1. Before: no history, empty pantry ==")
        a = await gen(s, p, "before")
        a_bf0 = {x["slot_date"]: [d["food_id"] for d in x["dishes"]] for x in a.combos if x["meal_type"] == "Breakfast" and x["combo_index"] == 0}

        print("\n== 2. Patient eats a habit breakfast every day for 4 weeks ==")
        egg_dishes = (await s.execute(
            select(FoodItem.id).join(RecipeIngredient, RecipeIngredient.food_item_id == FoodItem.id)
            .join(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
            .where(FoodItem.is_verified == True, FoodItem.diet_type == DIET,  # noqa: E712
                   FoodItem.meal_time_tags.any("Breakfast"), FoodItem.slot_type == "main_dish",
                   Ingredient.name.ilike(f"{HABIT}%")).distinct().limit(1)
        )).scalars().all()
        lunch_dinner = {(x["meal_type"]): [d["food_id"] for d in x["dishes"]] for x in a.combos if x["combo_index"] == 0 and x["meal_type"] != "Breakfast"}
        monday = date.today() - timedelta(days=date.today().weekday())
        for w in range(4, 0, -1):
            wk = monday - timedelta(weeks=w)
            for d in range(7):
                day = wk + timedelta(days=d)
                for mt, ids in (("Breakfast", [egg_dishes[0]]), ("Lunch", lunch_dinner["Lunch"]), ("Dinner", lunch_dinner["Dinner"])):
                    ch = PatientMealChoice(patient_id=p.id, food_item_id=ids[0], date=day, meal_type=mt, calories=300, bowl_size="medium", actual_calories=300)
                    s.add(ch); await s.flush()
                    for fid in ids:
                        s.add(PatientMealChoiceDish(choice_id=ch.id, food_item_id=fid, calories=100))
            await s.flush()
            summ = await compute_weekly_summary(s, p.id, wk)
            assert "error" not in summ, summ
            # compute_weekly_summary stores (and commits) the summary when that week has a plan; otherwise store it here
            if not (await s.execute(select(WeeklyPatientSummary.id).where(
                    WeeklyPatientSummary.patient_id == p.id, WeeklyPatientSummary.week_start_date == wk))).first():
                s.add(WeeklyPatientSummary(patient_id=p.id, recommendation_id=rec.id, week_start_date=wk, summary_data=summ))
                await s.flush()
        h = await load_habits(s, p.id)
        print(f"weeks of summaries={h.weeks} habit ingredients={sorted(h.summary_names)}")
        again = await compute_weekly_summary(s, p.id, monday - timedelta(weeks=1))
        print("weekly job re-run gives identical ingredient_intake:",
              json.dumps(again["ingredient_intake"], sort_keys=True) == json.dumps(summ["ingredient_intake"], sort_keys=True))
        nt = summ["nutrient_totals"]
        print("one week's nutrient totals:", {k: nt[k]["total"] for k in nt}, "| protein mostly from:",
              [t["name"] for t in nt["protein_g"]["top"]], "| ingredients without nutrient data:", summ["nutrient_data_missing"])

        print("\n== 3. After 4 weeks of history ==")
        b = await gen(s, p, "after ")
        b_bf0 = {x["slot_date"]: [d["food_id"] for d in x["dishes"]] for x in b.combos if x["meal_type"] == "Breakfast" and x["combo_index"] == 0}
        print("breakfast combo 0 (health baseline) unchanged on", sum(a_bf0[k] == b_bf0.get(k) for k in a_bf0), "of", len(a_bf0), "days")

        print("\n== 4. is_usual in /meal-plan/week ==")
        await DietPlanService().store_diet_plan(b, session=s)
        wk_resp = await mp.get_week_plan(current_user=p, session=s)
        usual = [c for d in wk_resp["days"] for m in d["meals"].values() for c in m["combos"] if c["is_usual"]]
        total = sum(len(m["combos"]) for d in wk_resp["days"] for m in d["meals"].values())
        print(f"options flagged 'Your usual': {len(usual)} of {total}")

        print("\n== 5. Generation cost (RUNS runs each, median) ==")

        async def off(ud, sess):          # same code path, habit signals switched off
            from types import SimpleNamespace
            from app.services.meal_generator.meal_generator import meal_generator
            ud["preferred_food_ids"] = frozenset(); ud["avoided_food_ids"] = frozenset(); ud["habit_ingredient_ids"] = frozenset()
            return SimpleNamespace(combos=(await meal_generator.generate_meal_plan(ud, sess))["combos"])

        import statistics
        fns = {"habits on": DietPlanService().generate_diet_plan, "habits off": off}
        ts = {k: [] for k in fns}; ns = {k: [] for k in fns}
        for _ in range(int(os.environ.get("RUNS", "5"))):
            for label, fn in fns.items():          # interleaved, so machine noise hits both equally
                random.seed(7); stmts[0] = 0; t = time.perf_counter()
                await fn(user_data(p), s)
                ts[label].append(time.perf_counter() - t); ns[label].append(stmts[0])
        res = {k: (statistics.median(ts[k]), statistics.median(ns[k])) for k in fns}
        for label in fns:
            print(f"{label}: median {res[label][0]:.2f}s, {res[label][1]:.0f} statements")
        print(f"habits add {100 * (res['habits on'][0] / res['habits off'][0] - 1):+.0f}% time (spec limit about +10%)")

        print("\n== 6. Safety ==")
        c = await gen(s, p, f"{HABIT} allergy", allergies=[HABIT])
        print("   habit dishes served to a patient allergic to it:", sum(has_habit(x["dishes"]) for x in c.combos), "(must be 0)")

        async def thin(ud, sess):
            all_ids = (await sess.execute(select(FoodItem.id))).scalars().all()
            orig = DietPlanService.generate_diet_plan

            from app.services.meal_generator.meal_generator import meal_generator
            ud["preferred_food_ids"] = frozenset(); ud["habit_ingredient_ids"] = frozenset()
            ud["avoided_food_ids"] = frozenset(all_ids)      # every dish is "avoided"
            plan = await meal_generator.generate_meal_plan(ud, sess)
            from types import SimpleNamespace
            return SimpleNamespace(combos=plan["combos"])
        d = await gen(s, p, "all dishes avoided (thin pool)", mutate=thin)
        print("   still produced all 84 combos:", len(d.combos) == 84)

        await s.rollback()
        print("\ndone (rig DB now holds synthetic choices/summaries: reset it with rig/reset_db.sh)")

asyncio.run(main())
