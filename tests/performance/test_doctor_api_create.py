"""
Item 7: Doctor creation via real API endpoint.

Tests two things:
1. Sequential creation of 6 doctors through POST /api/v1/admin/doctors
   (the real onboarding path, not direct ORM insert)
2. Concurrent same-email doctor creation — verifies 409 on duplicate

Run:
    python -m tests.performance.test_doctor_api_create

Requires:
    - Backend running on port 8001
    - ADMIN_SEED_PASSWORD in .env (or env var)
    - Admin account seeded: python -m scripts.seed_admin
"""

import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import httpx

BASE = "http://127.0.0.1:8001/api/v1"
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@mityahar.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_SEED_PASSWORD", "")

# NOTE: .test TLD is RFC-2606 reserved — EmailStr rejects it.
# seed_test_patients.py bypasses this via direct ORM (no Pydantic validation).
# This test uses .com TLD to exercise the real API path with valid emails.
DOCTOR_DEFS = [
    {"email": "dr.ashok.mehta@mityahar-perf.com",  "name": "Dr. Ashok Mehta",  "password": "DoctorTest@2026", "specialization": "General Dietetics"},
    {"email": "dr.priya.sharma@mityahar-perf.com", "name": "Dr. Priya Sharma", "password": "DoctorTest@2026", "specialization": "General Dietetics"},
    {"email": "dr.rahul.verma@mityahar-perf.com",  "name": "Dr. Rahul Verma",  "password": "DoctorTest@2026", "specialization": "General Dietetics"},
    {"email": "dr.sunita.nair@mityahar-perf.com",  "name": "Dr. Sunita Nair",  "password": "DoctorTest@2026", "specialization": "General Dietetics"},
    {"email": "dr.amit.joshi@mityahar-perf.com",   "name": "Dr. Amit Joshi",   "password": "DoctorTest@2026", "specialization": "General Dietetics"},
    {"email": "dr.kavita.reddy@mityahar-perf.com", "name": "Dr. Kavita Reddy", "password": "DoctorTest@2026", "specialization": "General Dietetics"},
]


async def get_admin_token(client: httpx.AsyncClient) -> str:
    r = await client.post(f"{BASE}/auth/admin/login", data={
        "username": ADMIN_EMAIL, "password": ADMIN_PASSWORD
    })
    if r.status_code != 200:
        print(f"[FAIL] Admin login: {r.status_code} {r.text}")
        sys.exit(1)
    token = r.json()["access_token"]
    print(f"[OK]   Admin login - token obtained")
    return token


async def create_doctor_via_api(
    client: httpx.AsyncClient,
    token: str,
    defn: dict,
    label: str = "",
) -> tuple[int, dict]:
    t0 = time.perf_counter()
    r = await client.post(
        f"{BASE}/admin/doctors",
        json={
            "email": defn["email"],
            "name": defn["name"],
            "password": defn["password"],
            "specialization": defn.get("specialization", "General Dietetics"),
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return r.status_code, r.json(), elapsed_ms


async def test_sequential_doctor_creation():
    print("\n=== TEST 1: Sequential doctor creation via POST /api/v1/admin/doctors ===")
    created = 0
    existed = 0
    failed = 0

    async with httpx.AsyncClient(timeout=30) as client:
        token = await get_admin_token(client)
        for defn in DOCTOR_DEFS:
            status, body, ms = await create_doctor_via_api(client, token, defn)
            if status == 201:
                print(f"  [CREATED {ms:6.1f}ms] {defn['email']} id={body.get('id')}")
                created += 1
            elif status == 409:
                print(f"  [EXISTS  {ms:6.1f}ms] {defn['email']} (409 — already in DB)")
                existed += 1
            else:
                print(f"  [FAIL    {ms:6.1f}ms] {defn['email']} → {status} {body}")
                failed += 1

    print(f"\nResult: {created} created, {existed} already existed, {failed} failed")
    return failed == 0


async def test_concurrent_duplicate_doctor():
    print("\n=== TEST 2: 10 concurrent requests for same doctor email ===")
    target = {"email": "dr.conctest@mityahar-perf.com", "name": "Dr. Concurrent Test", "password": "DoctorTest@2026"}

    async with httpx.AsyncClient(timeout=30) as client:
        token = await get_admin_token(client)

        async def attempt(i: int):
            status, body, ms = await create_doctor_via_api(client, token, target, f"worker-{i}")
            return status, ms

        t0 = time.perf_counter()
        results = await asyncio.gather(*[attempt(i) for i in range(10)])
        total_ms = (time.perf_counter() - t0) * 1000

    statuses = [r[0] for r in results]
    created_count = statuses.count(201)
    conflict_count = statuses.count(409)

    print(f"  Statuses: {statuses}")
    print(f"  Created: {created_count} | Conflicts (409): {conflict_count}")
    print(f"  Wall clock: {total_ms:.1f}ms")

    pass_condition = created_count == 1 and conflict_count == 9
    print(f"\n  {'PASS' if pass_condition else 'FAIL'} — expected 1×201 + 9×409")

    # Cleanup: note the test email stays in DB; idempotent next run
    return pass_condition


async def main():
    if not ADMIN_PASSWORD:
        print("[ERROR] ADMIN_SEED_PASSWORD not set in .env — cannot authenticate as admin.")
        print("        Run: python -m scripts.seed_admin first.")
        sys.exit(1)

    ok1 = await test_sequential_doctor_creation()
    ok2 = await test_concurrent_duplicate_doctor()

    print(f"\n{'='*50}")
    print(f"Sequential creation:   {'PASS' if ok1 else 'FAIL'}")
    print(f"Concurrent duplicate:  {'PASS' if ok2 else 'FAIL'}")
    overall = ok1 and ok2
    print(f"Overall:               {'PASS' if overall else 'FAIL'}")
    sys.exit(0 if overall else 1)


if __name__ == "__main__":
    asyncio.run(main())
