"""
Duplicate email race condition test.

Fires 10 concurrent POST /api/v1/auth/register requests with IDENTICAL email.
Expected result: exactly 1 account created (201), rest are 409 or 429.
The DB UNIQUE constraint on patients.email is the final guard — even if two
requests slip past the app-level check simultaneously, PostgreSQL serialises
the INSERT and the second one gets an IntegrityError → 409.

Evidence:
  Migration 4e5124b3e103 creates patients table with:
      sa.UniqueConstraint('email')
  auth.py:175:
      except IntegrityError:
          raise HTTPException(status_code=409, detail="Email already registered")

REQUIREMENTS:
  - Backend running:  python -m uvicorn app.main:app --port 8001 --host 0.0.0.0
  - TRUSTED_PROXY_CIDR=127.0.0.1 in .env  (gives each request a distinct rate-limit bucket)

Run:
    python -m tests.performance.test_duplicate_email
"""

import asyncio
import sys
import time

import httpx

BASE_URL = "http://127.0.0.1:8001"
REGISTER_URL = f"{BASE_URL}/api/v1/auth/register"

RACE_EMAIL = "race.test.dup2@mityahar-load.com"
RACE_PAYLOAD = {
    "email": RACE_EMAIL,
    "password": "Race@2026!1",
    "name": "Race Condition Test",
    "gender": "Other",
    "height": 165.0,
    "weight": 65.0,
    "activity_level": "MA",
    "diet": "Vegetarian",
    "health_condition": "Healthy",
    "gdpr_consent": True,
}
CONCURRENT = 10


async def _fire_one(client: httpx.AsyncClient, index: int) -> dict:
    xff = f"10.2.0.{index}"   # distinct IP per request so rate limiter doesn't interfere
    t0 = time.perf_counter()
    try:
        r = await client.post(
            REGISTER_URL,
            json=RACE_PAYLOAD,
            headers={"X-Forwarded-For": xff},
            timeout=15,
        )
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        body = {}
        try:
            body = r.json()
        except Exception:
            pass
        return {"index": index, "status": r.status_code, "elapsed_ms": elapsed, "detail": body.get("detail")}
    except Exception as exc:
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        return {"index": index, "status": "ERROR", "elapsed_ms": elapsed, "detail": str(exc)}


async def run() -> None:
    print("=== Duplicate Email Race Condition Test ===\n")
    print(f"Email:       {RACE_EMAIL}")
    print(f"Concurrency: {CONCURRENT} simultaneous requests\n")

    # Verify server is up
    try:
        httpx.get(f"{BASE_URL}/health", timeout=5)
    except Exception as e:
        print(f"[ERROR] Server not reachable: {e}")
        sys.exit(1)

    async with httpx.AsyncClient() as client:
        tasks = [_fire_one(client, i) for i in range(1, CONCURRENT + 1)]
        results = await asyncio.gather(*tasks)

    print("Results:")
    by_status: dict = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)
        status_label = {201: "201 Created", 200: "200 OK", 409: "409 Conflict", 429: "429 Rate limit"}.get(
            r["status"], str(r["status"])
        )
        print(f"  req {r['index']:>2}: {status_label:20s}  {r['elapsed_ms']}ms"
              + (f"  [{r['detail']}]" if r["detail"] else ""))

    created = len(by_status.get(201, [])) + len(by_status.get(200, []))
    conflicts = len(by_status.get(409, []))
    rate_limited = len(by_status.get(429, []))
    errors = len(by_status.get("ERROR", []))

    print(f"\nSummary:")
    print(f"  Created (201/200): {created}   <- must be exactly 1")
    print(f"  Conflict (409):    {conflicts}  <- DB UNIQUE constraint fired")
    print(f"  Rate limited (429): {rate_limited}")
    print(f"  Errors:            {errors}")

    # Pass condition: exactly 1 account created, no server errors
    passed = created == 1 and errors == 0 and rate_limited == 0
    print(f"\nOVERALL: {'PASS' if passed else 'FAIL'}")
    if not passed:
        if created == 0:
            print("  No accounts created — server error or all rate-limited?")
        if created > 1:
            print(f"  CRITICAL: {created} accounts created for the same email — UNIQUE constraint not working!")
        if rate_limited:
            print(f"  {rate_limited} rate-limited — is TRUSTED_PROXY_CIDR=127.0.0.1 in .env?")

    # DB UNIQUE constraint evidence line for the report
    print(f"\nDB constraint evidence: patients.email has sa.UniqueConstraint('email')")
    print(f"  Source: alembic/versions/4e5124b3e103_add_all_user_tables.py line 80")
    print(f"IntegrityError handler: auth.py:175 -> 409 'Email already registered'")


if __name__ == "__main__":
    asyncio.run(run())
