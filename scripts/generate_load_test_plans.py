"""
Generate meal plans for the seeded load-test patients, then mark them approved.

Companion to scripts/seed_load_test_data.py. Same reason for living under
scripts/ rather than tests/: `tests/` is excluded by .dockerignore, so it is not
in the container image, and staging Cloud SQL is private-IP-only — a Cloud Run
job is the only way to reach it.

Reuses the per-patient core of tests/performance/bulk_generate_plans.py
(DietPlanService.generate_diet_plan -> store_diet_plan -> commit, with
per-patient rollback), with two changes:

  - Patients come from a `loadtest%` email query instead of the local
    test_manifest.json, which does not exist inside the job container.

  - Plans are flipped to approval_status='approved' at the end. This matters:
    diet_plan_service.py:133 writes 'draft' for every v2 plan, and
    meal_plan.py:160-178 responds to a draft-with-no-approved-sibling by
    returning HTTP 200 with an EMPTY days list rather than an error. A load test
    against draft plans would therefore look perfectly healthy while never
    exercising a single write — the locustfile's confirm_combo task builds its
    entries from that empty list and silently no-ops. The UPDATE is scoped by
    email to load-test rows only; real patients keep the draft default.

Run as a Cloud Run job (staging). Needs ~15+ min, so raise --task-timeout first.

Locally:
    python -m scripts.generate_load_test_plans --limit 5
"""

import argparse
import asyncio
import sys
import time
from datetime import date

from dotenv import load_dotenv
from sqlalchemy import select, text

# Must precede app.core.database — that module reads DATABASE_URL at import time.
load_dotenv()

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.db_models import Patient  # noqa: E402
from app.services.diet_plan_service import DietPlanService  # noqa: E402

EMAIL_PREFIX = "loadtest%"


def _compute_age(dob) -> int:
    if dob is None:
        return 30
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


async def _generate_for_patient(patient_id: int, diet_service: DietPlanService) -> dict:
    t0 = time.perf_counter()
    async with AsyncSessionLocal() as session:
        patient = (
            await session.execute(select(Patient).where(Patient.id == patient_id))
        ).scalars().first()
        if patient is None:
            return {"patient_id": patient_id, "ok": False, "error": "patient_not_found"}

        user_data = {
            "id": str(patient.id),
            "email": patient.email,
            "name": patient.name,
            "gender": patient.gender or "Other",
            "height": float(patient.height_cm),
            "weight": float(patient.weight_kg),
            "activity_level": patient.activity_level or "LA",
            "diet": patient.diet_type or "Vegetarian",
            "health_condition": patient.health_condition or "Healthy",
            "region": patient.region or "North",
            "nonveg_meals_per_week": patient.nonveg_meals_per_week or 3,
            "health_goals": list(patient.health_goals or []),
            "medical_conditions": list(patient.medical_conditions or []),
            "food_allergies": list(patient.food_allergies or []),
            "age": _compute_age(patient.date_of_birth),
        }

        try:
            plan = await diet_service.generate_diet_plan(user_data, session)
            rec_id = await diet_service.store_diet_plan(plan, session=session)
            await session.commit()
            return {"patient_id": patient_id, "ok": True, "recommendation_id": rec_id,
                    "elapsed_s": round(time.perf_counter() - t0, 2)}
        except Exception as exc:
            await session.rollback()
            return {"patient_id": patient_id, "ok": False, "error": str(exc)[:200],
                    "elapsed_s": round(time.perf_counter() - t0, 2)}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0 = all load-test patients")
    ap.add_argument("--skip-approve", action="store_true")
    args = ap.parse_args()

    async with AsyncSessionLocal() as session:
        stmt = select(Patient.id).where(Patient.email.like(EMAIL_PREFIX)).order_by(Patient.id)
        if args.limit:
            stmt = stmt.limit(args.limit)
        patient_ids = [r[0] for r in (await session.execute(stmt)).all()]

    total = len(patient_ids)
    print(f"generating plans for {total} load-test patients", flush=True)
    if total == 0:
        print("ERROR: no patients matched — was the seeder run?", flush=True)
        return 1

    diet_service = DietPlanService()
    passed = failed = 0
    errors: list[str] = []
    t_start = time.perf_counter()

    for i, pid in enumerate(patient_ids, 1):
        r = await _generate_for_patient(pid, diet_service)
        if r["ok"]:
            passed += 1
        else:
            failed += 1
            if len(errors) < 10:
                errors.append(f"pid={pid}: {r.get('error')}")
        if i % 50 == 0 or i == total:
            rate = (time.perf_counter() - t_start) / i
            print(f"  {i}/{total}  ok={passed} fail={failed}  {rate:.2f}s/plan", flush=True)

    for e in errors:
        print(f"  ERROR {e}", flush=True)

    approved = 0
    if not args.skip_approve:
        # See module docstring: draft plans render as 200-with-empty-days, which
        # would make the load test silently read-only.
        async with AsyncSessionLocal() as session:
            res = await session.execute(text("""
                UPDATE recommendations SET approval_status = 'approved'
                WHERE approval_status = 'draft'
                  AND patient_id IN (SELECT id FROM patients WHERE email LIKE :p)
            """), {"p": EMAIL_PREFIX})
            approved = res.rowcount
            await session.commit()
        print(f"approved {approved} draft plans (load-test patients only)", flush=True)

    print(f"DONE total={total} ok={passed} failed={failed} approved={approved} "
          f"elapsed={time.perf_counter() - t_start:.0f}s", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
