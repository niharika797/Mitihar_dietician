"""
test_weight_update_gap.py -- weight changes: once per 28 days, no plan regeneration.

Covers POST/PUT /progress/log/weight and PUT /users/me (weight_kg from the patient app).
Needs the local Postgres (DATABASE_URL in .env). Runs the app in-process. Not run in CI.

    python -m tests.test_weight_update_gap
"""
import asyncio
import sys
from datetime import date, timedelta

import bcrypt
from dotenv import load_dotenv

load_dotenv()

from app.core.security import create_access_token  # noqa: E402
from tests.test_generate_idempotent import client, sql  # noqa: E402

EMAIL = "wgap@wgap-test.local"
LOG = "/api/v1/progress/log/weight"
ME = "/api/v1/users/me"


async def make_patient(created_days_ago):
    await cleanup()
    h = bcrypt.hashpw(b"wgaptest", bcrypt.gensalt(rounds=4)).decode()
    pid = (await sql(
        "INSERT INTO patients (email, hashed_password, name, gender, height_cm, weight_kg, activity_level, diet_type, "
        "region, subscription_status, is_active, date_of_birth, created_at, user_type, health_goals, medical_conditions, "
        "food_allergies, dietary_preferences, meals_per_day, water_glasses, nonveg_meals_per_week, eating_habits) "
        "VALUES (:e, :h, 'Wgap Test', 'Male', 170, 70, 'MA', 'Vegetarian', 'North', 'active', TRUE, '1990-01-01', "
        "now() - make_interval(days => :d), 'standalone', '[]', '[]', '[]', '[]', 3, 8, 3, '[]') RETURNING id", e=EMAIL, h=h, d=created_days_ago))[0][0]
    return pid, create_access_token({"sub": EMAIL, "sub_status": "active", "patient_id": pid})


async def cleanup():
    await sql("DELETE FROM progress_logs WHERE patient_id IN (SELECT id FROM patients WHERE email=:e)", e=EMAIL)
    await sql("DELETE FROM recommendations WHERE patient_id IN (SELECT id FROM patients WHERE email=:e)", e=EMAIL)
    await sql("DELETE FROM patients WHERE email=:e", e=EMAIL)


async def state(pid):
    w, tdee = (await sql("SELECT weight_kg, tdee FROM patients WHERE id=:p", p=pid))[0]
    recs = (await sql("SELECT count(*) FROM recommendations WHERE patient_id=:p", p=pid))[0][0]
    return float(w), tdee, recs


async def main():
    fails = []

    def check(name, ok):
        print(("PASS " if ok else "FAIL ") + name)
        if not ok:
            fails.append(name)

    try:
        # old patient, no log yet: first weight log works, targets follow, no plan regenerated
        pid, tok = await make_patient(40)
        async with client(tok) as c:
            r = await c.put(LOG, json={"weight": 72})
            w, tdee, recs = await state(pid)
            check("first log: 200, weight and TDEE updated, no plan generated", r.status_code == 200 and w == 72 and tdee and recs == 0)

            r = await c.put(LOG, json={"weight": 71.5})
            check("same-day correction: 200", r.status_code == 200 and (await state(pid))[0] == 71.5)

            await sql("UPDATE progress_logs SET log_date=:d WHERE patient_id=:p", d=date.today() - timedelta(days=10), p=pid)
            r1 = await c.put(LOG, json={"weight": 70})
            r2 = await c.post(LOG, json={"weight": 70})
            r3 = await c.put(ME, json={"weight_kg": 75})
            check("10 days later: PUT, POST and profile edit all 409",
                  (r1.status_code, r2.status_code, r3.status_code) == (409, 409, 409) and (await state(pid))[0] == 71.5)

            r = await c.put(ME, json={"weight_kg": 71.5, "name": "Renamed"})
            check("profile edit with unchanged weight: 200", r.status_code == 200)

            await sql("UPDATE progress_logs SET log_date=:d WHERE patient_id=:p", d=date.today() - timedelta(days=29), p=pid)
            r = await c.put(ME, json={"weight_kg": 74})
            w, tdee, recs = await state(pid)
            logged = (await sql("SELECT count(*) FROM progress_logs WHERE patient_id=:p AND log_date=:d AND weight_kg=74",
                                p=pid, d=date.today()))[0][0]
            check("29 days later: profile edit 200, logged, no plan generated", r.status_code == 200 and w == 74 and logged == 1 and recs == 0)

        # new patient, no log yet: the signup date counts as the last entry (same-day fix of the signup weight is allowed)
        pid, tok = await make_patient(3)
        async with client(tok) as c:
            r = await c.post(LOG, json={"weight": 69})
            check("signed up 3 days ago: 409", r.status_code == 409 and (await state(pid))[0] == 70)
        pid, tok = await make_patient(0)
        async with client(tok) as c:
            r = await c.post(LOG, json={"weight": 69})
            check("signed up today: 200", r.status_code == 200 and (await state(pid))[0] == 69)
    finally:
        await cleanup()

    print("ALL PASSED" if not fails else f"FAILED: {fails}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    asyncio.run(main())
