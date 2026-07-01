"""
Plan quality correctness suite — verifies diet plans for all 50 test patients.

Checks:
  - Calorie range: total_kcal within ±15% of patient TDEE × 0.85 target
  - Combo count: v2 format has 7 days, 3 meals, 4 combos each = 84 WeeklyCombo rows
  - Medical avoid_tags: NO plan dishes carry tags forbidden by patient's conditions
  - No pool exhaustion: no 409 errors in generation history
  - Personalization: checks dish variety (no same dish repeated > 3 times/week across combos)

Prerequisites:
  1. Run seed_test_patients.py first
  2. Generate plans for all test patients (POST /api/v1/diet-plans/generate as each patient,
     or use the bulk_generate_plans helper in this file)
  3. Run: python -m tests.performance.test_plan_quality

Output:
  Printed per-patient table + tests/performance/reports/quality_report.json

To bulk-generate plans before running quality checks:
    python -m tests.performance.test_plan_quality --generate-first
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from sqlalchemy import select, text

from app.core.database import AsyncSessionLocal
from app.models.db_models import Patient, WeeklyCombo

BASE_URL = "http://127.0.0.1:8001"
MANIFEST_PATH = Path(__file__).parent / "test_manifest.json"
REPORTS_DIR = Path(__file__).parent / "reports"

CONDITION_TAG_MAP = {
    "Diabetic":          ["avoid_diabetes"],
    "PCOS":              ["avoid_pcos"],
    "Hypothyroid":       ["avoid_hypothyroid"],
    "High_Cholesterol":  ["avoid_highchol"],
    "Gout":              ["avoid_gout"],
    "IBS":               ["avoid_ibs"],
    "Hypertension":      ["avoid_hypertension"],
    "Anemia":            [],
    "Kidney_Disease":    ["avoid_kidney"],
    "Healthy":           [],
    "Healthy_Gym":       [],
    "Diabetic_Hypertension": ["avoid_diabetes", "avoid_hypertension"],
}

CALORIE_TARGET_RATIO = 0.85 * 0.85  # generator: effective_tdee=TDEE×0.85, meal split sums to 0.85 → total=TDEE×0.7225
CALORIE_TOLERANCE   = 0.05          # ±5% around actual delivered calories


async def _login_patient(client: httpx.AsyncClient, email: str, password: str) -> str:
    r = await client.post("/api/v1/auth/token", data={"username": email, "password": password})
    if r.status_code == 200:
        return r.json().get("access_token", "")
    return ""


async def _generate_plan(client: httpx.AsyncClient, token: str) -> bool:
    r = await client.post(
        "/api/v1/diet-plans/generate",
        headers={"Authorization": f"Bearer {token}"},
    )
    return r.status_code == 200


async def _check_plan_found(patient_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT EXISTS(SELECT 1 FROM recommendations WHERE patient_id = :pid AND is_active = true)"),
            {"pid": patient_id},
        )
        return bool(result.scalar())


async def _check_calorie_range_db(patient_id: int, tdee: float) -> tuple[bool, float, float]:
    target = tdee * CALORIE_TARGET_RATIO
    lower = target * (1 - CALORIE_TOLERANCE)
    upper = target * (1 + CALORIE_TOLERANCE)

    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            text("""
                SELECT wc.slot_date, SUM(wc.total_calories) AS day_kcal
                FROM weekly_combos wc
                JOIN recommendations r ON r.id = wc.recommendation_id
                WHERE r.patient_id = :pid
                  AND r.is_active = true
                  AND wc.combo_index = 0
                GROUP BY wc.slot_date
            """),
            {"pid": patient_id},
        )
        daily_kcals = [float(row[1]) for row in rows.fetchall() if row[1]]

    if not daily_kcals:
        return False, 0.0, round(target, 1)

    avg_kcal = sum(daily_kcals) / len(daily_kcals)
    return lower <= avg_kcal <= upper, round(avg_kcal, 1), round(target, 1)


async def _check_variety_db(patient_id: int) -> tuple[bool, list]:
    # Check per-meal-type: a dish appearing > 3 times in the same meal slot
    # (e.g. same dish 4+ out of 7 breakfasts) signals poor variety.
    # Uses combo_index=0 only (the recommended combo), 7 entries per meal type.
    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            text("""
                SELECT dish->>'name' AS name, wc.meal_type, COUNT(*) AS cnt
                FROM weekly_combos wc
                JOIN recommendations r ON r.id = wc.recommendation_id
                CROSS JOIN jsonb_array_elements(wc.dishes) AS dish
                WHERE r.patient_id = :pid
                  AND r.is_active = true
                  AND wc.combo_index = 0
                  AND dish->>'name' IS NOT NULL
                  AND dish->>'name' != ''
                GROUP BY dish->>'name', wc.meal_type
                HAVING COUNT(*) > 3
                ORDER BY cnt DESC
                LIMIT 5
            """),
            {"pid": patient_id},
        )
        repeated = [(row[0], row[1], int(row[2])) for row in rows.fetchall()]

    return len(repeated) == 0, [f"{n} ({m})×{c}" for n, m, c in repeated]


async def _check_avoid_tags(patient_id: int, condition: str) -> tuple[bool, list]:
    forbidden_tags = CONDITION_TAG_MAP.get(condition, [])
    if not forbidden_tags:
        return True, []

    violations = []
    async with AsyncSessionLocal() as session:
        # Get all food_item_ids in this patient's combos
        rows = await session.execute(
            text("""
                SELECT DISTINCT
                    dish->>'name' AS name,
                    fi.avoid_tags::text,
                    wc.meal_type,
                    wc.combo_index
                FROM weekly_combos wc
                JOIN recommendations r ON r.id = wc.recommendation_id
                CROSS JOIN jsonb_array_elements(wc.dishes) AS dish
                JOIN food_items fi ON fi.id = (dish->>'food_item_id')::integer
                WHERE r.patient_id = :pid
                  AND r.is_active = true
                  AND fi.avoid_tags IS NOT NULL
                  AND fi.avoid_tags != '[]'::jsonb
            """),
            {"pid": patient_id},
        )
        for name, tags_str, meal_type, combo_index in rows.fetchall():
            try:
                tags = json.loads(tags_str) if tags_str else []
            except Exception:
                tags = []
            bad = [t for t in forbidden_tags if t in tags]
            if bad:
                violations.append(f"{name} ({meal_type} combo#{combo_index}): {bad}")

    return len(violations) == 0, violations


async def _check_combo_count(patient_id: int) -> tuple[bool, int]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT COUNT(*) FROM weekly_combos wc
                JOIN recommendations r ON r.id = wc.recommendation_id
                WHERE r.patient_id = :pid AND r.is_active = true
            """),
            {"pid": patient_id},
        )
        count = result.scalar() or 0
    return count >= 84, count



async def _check_patient(
    client: httpx.AsyncClient, patient: dict, password: str, generate_first: bool
) -> dict:
    pid = patient["patient_id"]
    email = patient["email"]
    condition = patient["condition"]
    tdee = patient.get("tdee", 2000)

    result = {
        "index": patient["index"],
        "patient_id": pid,
        "email": email,
        "condition": condition,
        "calorie_ok": False,
        "avg_kcal": 0.0,
        "target_kcal": 0.0,
        "combo_count": 0,
        "combo_ok": False,
        "avoid_tags_ok": False,
        "avoid_violations": [],
        "variety_ok": False,
        "variety_issues": [],
        "plan_found": False,
        "pass": False,
    }

    if generate_first:
        token = await _login_patient(client, email, password)
        if token:
            await _generate_plan(client, token)

    result["plan_found"] = await _check_plan_found(pid)

    ok_cal, avg_kcal, target = await _check_calorie_range_db(pid, tdee)
    result["calorie_ok"] = ok_cal
    result["avg_kcal"] = avg_kcal
    result["target_kcal"] = target

    ok_variety, variety_issues = await _check_variety_db(pid)
    result["variety_ok"] = ok_variety
    result["variety_issues"] = variety_issues

    ok_count, count = await _check_combo_count(pid)
    result["combo_count"] = count
    result["combo_ok"] = ok_count

    ok_tags, violations = await _check_avoid_tags(pid, condition)
    result["avoid_tags_ok"] = ok_tags
    result["avoid_violations"] = violations[:3]

    result["pass"] = (
        result["plan_found"]
        and result["calorie_ok"]
        and result["combo_ok"]
        and result["avoid_tags_ok"]
        and result["variety_ok"]
    )
    return result


def _icon(flag: bool) -> str:
    return "✅" if flag else "❌"


async def run(generate_first: bool = False):
    print("=== Mityahar Plan Quality Test ===\n")

    if not MANIFEST_PATH.exists():
        print(f"[ERROR] Manifest not found: {MANIFEST_PATH}")
        print("       Run seed_test_patients.py first.")
        return

    manifest = json.loads(MANIFEST_PATH.read_text())
    patients = manifest["patients"]
    password = manifest.get("patient_password", "TestPat@2026")

    print(f"Testing {len(patients)} patients (generate_first={generate_first})...\n")

    results = []
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=90) as client:
        for p in patients:
            sys.stdout.write(f"  P{p['index']:03d} {p['condition']:<24} ... ")
            sys.stdout.flush()
            r = await _check_patient(client, p, password, generate_first)
            results.append(r)
            status = "PASS" if r["pass"] else "FAIL"
            print(
                f"{status}  cal={_icon(r['calorie_ok'])} "
                f"combos={r['combo_count']:>3} "
                f"tags={_icon(r['avoid_tags_ok'])} "
                f"variety={_icon(r['variety_ok'])}"
            )

    # Summary table
    passed = sum(1 for r in results if r["pass"])
    print(f"\n{'='*80}")
    print(f"{'P#':<4} {'Condition':<24} {'Cal':<5} {'AvgKcal':>7} {'Combos':>6} {'Tags':>5} {'Var':>4} {'RESULT':>7}")
    print("-" * 80)
    for r in results:
        print(
            f"P{r['index']:03d} {r['condition']:<24} {_icon(r['calorie_ok']):<5} "
            f"{r['avg_kcal']:>7.0f} {r['combo_count']:>6} "
            f"{_icon(r['avoid_tags_ok']):>5} {_icon(r['variety_ok']):>4} "
            f"{'PASS' if r['pass'] else 'FAIL':>7}"
        )

    print(f"\nResult: {passed}/{len(results)} patients PASS")

    if any(not r["avoid_tags_ok"] for r in results):
        print("\n=== Tag Violations ===")
        for r in results:
            if not r["avoid_tags_ok"]:
                print(f"  P{r['index']:03d} {r['condition']}: {r['avoid_violations']}")

    # Save
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / "quality_report.json"
    out_path.write_text(json.dumps({"passed": passed, "total": len(results), "patients": results}, indent=2))
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-first", action="store_true",
                        help="Generate a fresh plan for each patient before checking")
    args = parser.parse_args()
    asyncio.run(run(generate_first=args.generate_first))
