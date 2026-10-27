"""
test_generate_idempotent.py -- POST /diet-plans/generate reuses a valid plan.
Design: docs/designs/idempotent-generate.md

Needs the local Postgres (DATABASE_URL in .env) with the recipe pool loaded.
Runs the app in-process (httpx ASGITransport), so no server is required and the
generator can be patched. Not run in CI (CI has no database).

    python -m tests.test_generate_idempotent
"""
import asyncio
import itertools
import sys
from datetime import date, timedelta
from unittest.mock import patch

import bcrypt
import httpx
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import diet_plans  # noqa: E402

EMAIL = "idem@idem-test.local"
_ip = itertools.count(1)  # distinct client IP per call (the limit is per patient now; kept to prove that)


async def sql(q, **p):
    async with AsyncSessionLocal() as s:
        r = await s.execute(text(q), p)
        await s.commit()
        return r.fetchall() if r.returns_rows else None


async def make_patient():
    await sql("DELETE FROM patients WHERE email=:e", e=EMAIL)
    h = bcrypt.hashpw(b"idemtest", bcrypt.gensalt(rounds=4)).decode()
    pid = (await sql(
        "INSERT INTO patients (email, hashed_password, name, gender, height_cm, weight_kg, "
        "activity_level, diet_type, region, subscription_status, is_active) "
        "VALUES (:e, :h, 'Idem Test', 'Male', 170, 70, 'MA', 'Vegetarian', 'North', 'active', TRUE) RETURNING id",
        e=EMAIL, h=h))[0][0]
    tok = create_access_token({"sub": EMAIL, "sub_status": "active", "patient_id": pid})
    return pid, tok


async def plans(pid):
    return await sql("SELECT id, version, is_active, week_start_date, approval_status FROM recommendations "
                     "WHERE patient_id=:p ORDER BY id", p=pid)


def client(tok):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t",
                             headers={"Authorization": f"Bearer {tok}"})


async def gen(c, ip=None):
    return await c.post("/api/v1/diet-plans/generate", headers={"X-Forwarded-For": ip or f"10.9.9.{next(_ip)}"})


async def back(pid, days):
    await sql("UPDATE recommendations SET week_start_date = :d WHERE patient_id=:p",
              d=date.today() - timedelta(days=days), p=pid)


async def main():
    pid, tok = await make_patient()
    fails = []

    def check(name, ok, detail=""):
        print(("PASS " if ok else "FAIL ") + name + ("" if ok or not detail else f"  [{detail}]"))
        if not ok:
            fails.append(name)

    try:
        async with client(tok) as c:
            # 1 no plan -> one plan
            r = await gen(c)
            p = await plans(pid)
            check("no plan: 200 and one plan", r.status_code == 200 and len(p) == 1)

            # 2 valid plan -> reused, nothing written
            combos = (await sql("SELECT count(*) FROM weekly_combos WHERE recommendation_id=:r", r=p[0][0]))[0][0]
            r = await gen(c)
            p2 = await plans(pid)
            combos2 = (await sql("SELECT count(*) FROM weekly_combos WHERE recommendation_id=:r", r=p[0][0]))[0][0]
            check("valid plan: reused (same id, same combos)", r.status_code == 200 and p2 == p and combos2 == combos)

            # 3 expired plan -> new active plan (the router deletes the old plan first, so version is not bumped)
            await back(pid, 8)
            r = await gen(c)
            p3 = await plans(pid)
            act = [x for x in p3 if x[2]]
            check("expired plan: one new active plan", r.status_code == 200 and len(act) == 1 and act[0][0] != p[0][0])

            # 4 draft plan inside window -> reused
            await sql("UPDATE recommendations SET approval_status='draft' WHERE patient_id=:p AND is_active", p=pid)
            before = await plans(pid)
            await gen(c)
            check("draft plan: reused", await plans(pid) == before)

            # 5 null week_start_date -> treated as expired
            await sql("UPDATE recommendations SET week_start_date=NULL WHERE patient_id=:p", p=pid)
            n = len(await plans(pid))
            await gen(c)
            check("null date: new plan", len(await plans(pid)) == n + 1)

            # 6 two active plans, newest expired, older valid -> new plan
            await sql("UPDATE recommendations SET is_active=FALSE WHERE patient_id=:p", p=pid)
            await sql("INSERT INTO recommendations (patient_id, week_start_date, is_active, generation_version, approval_status, meals, "
                      "created_at) SELECT patient_id, current_date, TRUE, generation_version, approval_status, '[]'::jsonb, now() - interval '2 day' "
                      "FROM recommendations WHERE patient_id=:p ORDER BY id DESC LIMIT 1", p=pid)
            await sql("INSERT INTO recommendations (patient_id, week_start_date, is_active, generation_version, approval_status, meals, "
                      "created_at) SELECT patient_id, current_date - 9, TRUE, generation_version, approval_status, '[]'::jsonb, now() "
                      "FROM recommendations WHERE patient_id=:p ORDER BY id DESC LIMIT 1", p=pid)
            n = len(await plans(pid))
            await gen(c)
            check("newest expired, older valid: new plan", len(await plans(pid)) == n + 1)

        # 7 two simultaneous calls on an expired plan -> exactly one new plan
        await back(pid, 8)
        n = len(await plans(pid))
        async with client(tok) as c1, client(tok) as c2:
            r1, r2 = await asyncio.gather(gen(c1), gen(c2))
        check("concurrent: one new plan", r1.status_code == r2.status_code == 200 and len(await plans(pid)) == n + 1)

        # 8 generator fails -> 503, old active plan survives (rollback)
        await back(pid, 8)
        before = await plans(pid)

        async def boom(*a, **k):
            raise RuntimeError("forced")

        with patch.object(diet_plans.diet_plan_service, "generate_diet_plan", boom):
            async with client(tok) as c:
                r = await gen(c)
        check("generator fails: 503 and old plan still active", r.status_code == 503 and await plans(pid) == before)

        # 9 reusing the stored plan is free: 12 calls from ONE IP never hit the limit (it used to be 10/hour per IP)
        async with client(tok) as c:
            r = await gen(c)  # real generation: puts a valid plan back (counts as one of the 10)
            ok_first = r.status_code == 200
            codes = [(await gen(c, ip="10.8.8.8")).status_code for _ in range(12)]
        check("reuse is never counted: 12 calls from one IP all 200", ok_first and codes == [200] * 12)

        # 10 real generations are limited per PATIENT (10/hour), whatever the IP, with the friendly 429
        await back(pid, 8)  # expired again, so every call is a real generation attempt
        statuses, last = [], None
        with patch.object(diet_plans.diet_plan_service, "generate_diet_plan", boom):
            async with client(tok) as c:
                for _ in range(8):
                    last = await gen(c, ip="10.7.7.7" if len(statuses) % 2 else None)
                    statuses.append(last.status_code)
                    if last.status_code == 429:
                        break
        body = last.json() if last is not None and last.status_code == 429 else {}
        check("real generations: refused with 429 once the patient has used 10 in an hour (any IP)",
              statuses[-1] == 429 and statuses[:-1] and all(s == 503 for s in statuses[:-1]), str(statuses))
        check("429 answer is the friendly one with a wait time",
              "take a break" in body.get("detail", "") and isinstance(body.get("retry_after_seconds"), int)
              and last.headers.get("retry-after") == str(body.get("retry_after_seconds")), str(body))
    finally:
        await sql("DELETE FROM weekly_combos WHERE recommendation_id IN (SELECT id FROM recommendations WHERE patient_id=:p)", p=pid)
        await sql("DELETE FROM recommendations WHERE patient_id=:p", p=pid)
        await sql("DELETE FROM patients WHERE id=:p", p=pid)
    print("FAILED: " + ", ".join(fails) if fails else "ALL PASSED")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
