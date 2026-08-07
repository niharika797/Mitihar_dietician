"""
Generate + quality-check diet plans for every REAL patient in the DB.

Why this exists: tests/performance/bulk_generate_plans.py and
test_plan_quality.py only cover the 50 synthetic patients listed in
test_manifest.json. After the data-quality remediation (quantity rebuild,
ingredient dedup, IFCT nutrition, dish reclassification) the question is
whether *actual* patients get sane plans, which the synthetic set can't
answer -- real patients have real condition combinations, diet types and
anthropometrics.

Reuses the existing checks from tests/performance/test_plan_quality.py rather
than reimplementing them (calorie range, combo count, variety).

The avoid-tag check is NOT reused, deliberately. That module has its own
CONDITION_TAG_MAP keyed on the synthetic fixtures' labels ("Diabetic", "PCOS",
"Hypothyroid"), but real patients store the onboarding UI's labels ("Type 2
Diabetes", "PCOS/PCOD", "Hypothyroidism"). Feeding real labels to that map
returns an empty forbidden-tag list, and the check then passes vacuously --
reporting medical safety it never actually verified. This uses
app/services/meal_generator/tag_utils.get_avoid_tags instead: the same
function the generator uses to *exclude* those dishes, so the check tests the
real contract.

DESTRUCTIVE: generating replaces each patient's active plan (the generator
deactivates the previous one). Back up recommendations + weekly_combos first:
    pg_dump ... --table=recommendations --table=weekly_combos -f backup.sql

Usage:
    python -m scripts.bulk_generate_plans_real_patients --dry-run   # list only
    python -m scripts.bulk_generate_plans_real_patients --limit 10  # sample
    python -m scripts.bulk_generate_plans_real_patients
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.models.db_models import Patient
from app.services.diet_plan_service import DietPlanService
from app.services.meal_generator.calculations import calculate_bmr, calculate_tdee
from app.services.meal_generator.tag_utils import get_avoid_tags

from tests.performance.test_plan_quality import (
    _check_calorie_range_db,
    _check_combo_count,
    _check_plan_found,
    _check_variety_db,
)

REPORTS_DIR = PROJECT_ROOT / "tests" / "performance" / "reports"
OUT_JSON = REPORTS_DIR / "real_patient_quality.json"


def _compute_age(dob) -> int:
    if dob is None:
        return 30
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _user_data(p: Patient) -> dict:
    """Same shape doctor.py's accept_request handler passes to the generator."""
    return {
        "id": str(p.id),
        "email": p.email,
        "name": p.name,
        "gender": p.gender or "Other",
        "height": float(p.height_cm),
        "weight": float(p.weight_kg),
        "activity_level": p.activity_level or "LA",
        "diet": p.diet_type or "Vegetarian",
        "health_condition": p.health_condition or "Healthy",
        "region": p.region or "North",
        "nonveg_meals_per_week": p.nonveg_meals_per_week or 3,
        "health_goals": list(p.health_goals or []),
        "medical_conditions": list(p.medical_conditions or []),
        "food_allergies": list(p.food_allergies or []),
        "age": _compute_age(p.date_of_birth),
    }


def _tdee_for(p: Patient) -> float:
    """Stored tdee if the patient has one, else recompute the same way
    /calculations/tdee does."""
    if p.tdee:
        return float(p.tdee)
    bmr = calculate_bmr(
        gender=p.gender or "Other",
        weight=float(p.weight_kg),
        height=float(p.height_cm),
        age=_compute_age(p.date_of_birth),
    )
    return calculate_tdee(bmr, p.activity_level or "LA")


async def _load_patients(limit: int | None) -> list[Patient]:
    async with AsyncSessionLocal() as s:
        q = select(Patient).where(
            Patient.height_cm.is_not(None), Patient.weight_kg.is_not(None)
        ).order_by(Patient.id)
        if limit:
            q = q.limit(limit)
        return list((await s.execute(q)).scalars().all())


async def _generate(pid: int, svc: DietPlanService) -> dict:
    t0 = time.perf_counter()
    async with AsyncSessionLocal() as s:
        p = (await s.execute(select(Patient).where(Patient.id == pid))).scalars().first()
        if p is None:
            return {"ok": False, "error": "patient_not_found", "elapsed_s": 0.0}
        try:
            plan = await svc.generate_diet_plan(_user_data(p), s)
            rec_id = await svc.store_diet_plan(plan, session=s)
            await s.commit()
            return {"ok": True, "recommendation_id": rec_id,
                    "elapsed_s": round(time.perf_counter() - t0, 2)}
        except Exception as exc:
            await s.rollback()
            return {"ok": False, "error": str(exc)[:200],
                    "elapsed_s": round(time.perf_counter() - t0, 2)}


async def _avoid_tag_violations(patient_id: int, conditions: list[str]) -> tuple[list, list]:
    """Dishes in this patient's active plan carrying a tag their conditions
    forbid. Returns (violations, forbidden_tags) -- forbidden_tags is returned
    so the caller can tell "clean" apart from "nothing was actually checked"."""
    forbidden = get_avoid_tags(conditions)
    if not forbidden:
        return [], []

    async with AsyncSessionLocal() as s:
        rows = (await s.execute(text("""
            SELECT DISTINCT dish->>'name', fi.avoid_tags::text, wc.meal_type, wc.combo_index
            FROM weekly_combos wc
            JOIN recommendations r ON r.id = wc.recommendation_id
            CROSS JOIN jsonb_array_elements(wc.dishes) AS dish
            JOIN food_items fi ON fi.id = (dish->>'food_id')::integer
            WHERE r.patient_id = :pid AND r.is_active = true
              AND fi.avoid_tags IS NOT NULL AND fi.avoid_tags != '[]'::jsonb
        """), {"pid": patient_id})).fetchall()

    violations = []
    for name, tags_str, meal_type, combo_index in rows:
        try:
            tags = json.loads(tags_str) if tags_str else []
        except Exception:
            tags = []
        bad = [t for t in forbidden if t in tags]
        if bad:
            violations.append(f"{name} ({meal_type} combo#{combo_index}): {bad}")
    return violations, forbidden


async def _check(p: Patient) -> dict:
    pid = p.id
    conditions = list(p.medical_conditions or [])

    plan_found = await _check_plan_found(pid)
    cal_ok, avg_kcal, target = await _check_calorie_range_db(pid, _tdee_for(p))
    variety_ok, variety_issues = await _check_variety_db(pid)
    combo_ok, combo_count = await _check_combo_count(pid)
    violations, forbidden = await _avoid_tag_violations(pid, conditions)

    return {
        "patient_id": pid,
        "conditions": conditions,
        "diet_type": p.diet_type,
        "plan_found": plan_found,
        "calorie_ok": cal_ok,
        "avg_kcal": avg_kcal,
        "target_kcal": target,
        "combo_count": combo_count,
        "combo_ok": combo_ok,
        "avoid_tags_ok": not violations,
        "avoid_tags_enforced": bool(forbidden),   # False = no tags apply, nothing verified
        "forbidden_tags": forbidden,
        "avoid_violations": violations[:5],
        "variety_ok": variety_ok,
        "variety_issues": variety_issues[:3],
        "pass": bool(plan_found and cal_ok and combo_ok and not violations and variety_ok),
    }


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="list patients, generate nothing")
    ap.add_argument("--limit", type=int, help="only the first N patients")
    args = ap.parse_args()

    patients = await _load_patients(args.limit)
    print(f"{len(patients)} real patients with height+weight\n")

    if args.dry_run:
        for p in patients[:20]:
            print(f"  id={p.id:<5} {p.diet_type or '?':<14} "
                  f"conds={list(p.medical_conditions or []) or '-'}")
        if len(patients) > 20:
            print(f"  ... and {len(patients) - 20} more")
        print("\nDRY RUN -- nothing generated.")
        return

    svc = DietPlanService()
    gen_ok = gen_fail = 0
    results = []

    for i, p in enumerate(patients, 1):
        sys.stdout.write(f"  [{i}/{len(patients)}] pid={p.id:<5} ... ")
        sys.stdout.flush()
        g = await _generate(p.id, svc)
        if not g["ok"]:
            gen_fail += 1
            print(f"GEN FAIL  {g.get('error', '?')[:70]}")
            results.append({"patient_id": p.id, "generated": False,
                            "error": g.get("error"), "pass": False})
            continue
        gen_ok += 1
        r = await _check(p)
        r["generated"] = True
        r["elapsed_s"] = g["elapsed_s"]
        results.append(r)
        flags = "".join([
            "C" if r["calorie_ok"] else "c",
            "N" if r["combo_ok"] else "n",
            "A" if r["avoid_tags_ok"] else "a",
            "V" if r["variety_ok"] else "v",
        ])
        print(f"{'PASS' if r['pass'] else 'FAIL'} [{flags}] "
              f"{r['avg_kcal']:.0f}/{r['target_kcal']:.0f}kcal combos={r['combo_count']} "
              f"{g['elapsed_s']:.1f}s")

    checked = [r for r in results if r.get("generated")]
    passed = [r for r in checked if r["pass"]]
    print(f"\n=== {len(passed)}/{len(results)} pass "
          f"(generated {gen_ok}, gen-failed {gen_fail}) ===")
    for label, key in [("calorie", "calorie_ok"), ("combo count", "combo_ok"),
                       ("avoid tags", "avoid_tags_ok"), ("variety", "variety_ok")]:
        bad = [r for r in checked if not r.get(key)]
        print(f"  {label:<12} failures: {len(bad)}" + (f"  {[r['patient_id'] for r in bad][:10]}" if bad else ""))

    # Distinguish "avoid tags clean" from "no avoid tags applied" -- without this
    # a pool of patients whose conditions map to no tags reads as verified-safe.
    enforced = [r for r in checked if r.get("avoid_tags_enforced")]
    print(f"  avoid tags actually enforced for {len(enforced)}/{len(checked)} patients "
          f"(rest have conditions that map to no avoid tags)")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(
        {"total": len(results), "generated": gen_ok, "gen_failed": gen_fail,
         "passed": len(passed), "results": results}, indent=2))
    print(f"\nSaved: {OUT_JSON}")


if __name__ == "__main__":
    asyncio.run(main())
