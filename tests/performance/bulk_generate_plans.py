"""
Bulk diet plan generator — calls DietPlanService directly, no HTTP, no rate limiter.

Intended for test data seeding only. Reads test_manifest.json and generates (or
regenerates) plans for all 50 patients by calling the same internal path that
doctor.py's accept_request handler uses.

Run:
    python -m tests.performance.bulk_generate_plans

Saves: tests/performance/reports/bulk_generation.json
Next: python -m tests.performance.test_plan_quality
"""

import asyncio
import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.db_models import Patient
from app.services.diet_plan_service import DietPlanService

MANIFEST_PATH = Path(__file__).parent / "test_manifest.json"
REPORTS_DIR = Path(__file__).parent / "reports"


def _compute_age(dob) -> int:
    if dob is None:
        return 30
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


async def _generate_for_patient(patient_id: int, diet_service: DietPlanService) -> dict:
    t0 = time.perf_counter()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Patient).where(Patient.id == patient_id))
        patient = result.scalars().first()

        if patient is None:
            return {
                "patient_id": patient_id,
                "ok": False,
                "error": "patient_not_found",
                "elapsed_s": round(time.perf_counter() - t0, 2),
            }

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
            diet_plan = await diet_service.generate_diet_plan(user_data, session)
            rec_id = await diet_service.store_diet_plan(diet_plan, session=session)
            await session.commit()
            elapsed = round(time.perf_counter() - t0, 2)
            return {"patient_id": patient_id, "ok": True, "recommendation_id": rec_id, "elapsed_s": elapsed}
        except Exception as exc:
            await session.rollback()
            elapsed = round(time.perf_counter() - t0, 2)
            return {"patient_id": patient_id, "ok": False, "error": str(exc), "elapsed_s": elapsed}


async def main():
    if not MANIFEST_PATH.exists():
        print(f"[ERROR] {MANIFEST_PATH} not found. Run seed_test_patients.py first.")
        sys.exit(1)

    manifest = json.loads(MANIFEST_PATH.read_text())
    patients = manifest["patients"]

    print(f"Bulk generating plans for {len(patients)} patients (direct service call — no HTTP/rate limiter)\n")

    diet_service = DietPlanService()
    results = []
    passed = failed = 0

    for p in patients:
        pid = p["patient_id"]
        cond = p.get("condition", "?")
        sys.stdout.write(f"  P{p['index']:03d} pid={pid:<5} {cond:<24} ... ")
        sys.stdout.flush()

        r = await _generate_for_patient(pid, diet_service)
        r["index"] = p["index"]
        r["condition"] = cond
        results.append(r)

        if r["ok"]:
            passed += 1
            print(f"OK  {r['elapsed_s']:.1f}s  rec_id={r.get('recommendation_id')}")
        else:
            failed += 1
            print(f"FAIL  {r.get('error', '?')[:80]}")

    elapsed_total = sum(r["elapsed_s"] for r in results)
    print(f"\nResult: {passed}/{len(patients)} OK, {failed} FAIL  (total {elapsed_total:.0f}s)")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / "bulk_generation.json"
    out.write_text(json.dumps(
        {"passed": passed, "failed": failed, "total": len(patients), "results": results},
        indent=2,
    ))
    print(f"Saved: {out}")
    print("\nNext: python -m tests.performance.test_plan_quality")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
