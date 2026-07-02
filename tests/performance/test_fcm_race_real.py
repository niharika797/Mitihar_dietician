"""
test_fcm_race_real.py — FCM double-fire race test with live contestable data.

Prerequisites:
  1. Backend running on port 8001 with TEST_RACE_DELAY_SECONDS=0.1 in .env
     (add it, then: python -m uvicorn app.main:app --reload --port 8001 --host 0.0.0.0)
  2. DB accessible at localhost:5432

What this proves:
  - Seeds 5 patients eligible for flag-expiring (token_1_expiry = now+2d, expiring_soon=False)
  - Fires the cron endpoint twice via asyncio.gather (genuine concurrency)
  - The 100ms TEST_RACE_DELAY_SECONDS holds UPDATE row locks during the window,
    guaranteeing the second caller's UPDATE blocks until first commits
  - Verdict: c1 + c2 must equal 5 with no overlap (c1=5,c2=0 or c1=0,c2=5)
  - Cleans up all @race-test.local patients afterward
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

import asyncpg
import bcrypt
import httpx
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
CRON_SECRET = os.environ.get("CRON_SECRET", "")
ENDPOINT = "http://localhost:8001/internal/cron/flag-expiring-patients"
HEADERS = {"X-Cron-Secret": CRON_SECRET}
TEST_EMAILS = [f"race{i}@race-test.local" for i in range(1, 6)]

# Pre-compute a cheap bcrypt hash once (rounds=4 for speed; test-only)
_FAKE_HASH = bcrypt.hashpw(b"racetest", bcrypt.gensalt(rounds=4)).decode()


async def seed(conn, expiry):
    for email in TEST_EMAILS:
        await conn.execute("DELETE FROM patients WHERE email = $1", email)
        await conn.execute("""
            INSERT INTO patients (
                email, hashed_password, name, gender,
                height_cm, weight_kg, activity_level, diet_type, region,
                token_1_active, token_1_expiry, expiring_soon
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """,
            email, _FAKE_HASH, f"RaceTest {email.split('@')[0]}",
            "Male", 170.0, 70.0, "MA", "Veg", "North",
            True, expiry, False,
        )
    print(f"  Seeded {len(TEST_EMAILS)} patients (expiry={expiry.date()})")


async def count_eligible(conn, now, cutoff):
    return await conn.fetchval("""
        SELECT COUNT(*) FROM patients
        WHERE token_1_active = TRUE
          AND token_1_expiry IS NOT NULL
          AND token_1_expiry <= $1
          AND token_1_expiry > $2
          AND expiring_soon = FALSE
          AND email LIKE '%@race-test.local'
    """, cutoff, now)


async def fire_concurrent():
    async with httpx.AsyncClient(timeout=30) as client:
        r1, r2 = await asyncio.gather(
            client.post(ENDPOINT, headers=HEADERS),
            client.post(ENDPOINT, headers=HEADERS),
        )
    return r1.json(), r2.json()


async def check_db_state(conn):
    rows = await conn.fetch("""
        SELECT id, email, expiring_soon FROM patients
        WHERE email LIKE '%@race-test.local'
    """)
    return rows


async def cleanup(conn):
    await conn.execute("DELETE FROM patients WHERE email LIKE '%@race-test.local'")
    remaining = await conn.fetchval(
        "SELECT COUNT(*) FROM patients WHERE email LIKE '%@race-test.local'"
    )
    return remaining


async def main():
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=2)   # inside the 4-day warning window
    cutoff = now + timedelta(days=4)

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # ── 1. SEED ───────────────────────────────────────────────────────────
        print("\n=== SEED ===")
        await seed(conn, expiry)

        # ── 2. ELIGIBILITY CONFIRMATION ───────────────────────────────────────
        print("\n=== ELIGIBILITY CHECK (pre-race) ===")
        n_eligible = await count_eligible(conn, now, cutoff)
        print(f"  Eligible patients matched by cron WHERE clause: {n_eligible}")
        if n_eligible != 5:
            print(f"  ABORT: expected 5 eligible, got {n_eligible}")
            await cleanup(conn)
            sys.exit(1)
        print("  Confirmed: 5 patients would be picked up by flag-expiring cron [ok]")

        # ── 3. RACE ───────────────────────────────────────────────────────────
        print("\n=== RACE EXECUTION ===")
        print("  Firing endpoint twice via asyncio.gather (genuinely concurrent)...")
        print("  Server must have TEST_RACE_DELAY_SECONDS=0.1 to guarantee lock contention.")
        d1, d2 = await fire_concurrent()
        c1 = d1.get("flagged", -1)
        c2 = d2.get("flagged", -1)
        print(f"  Caller 1 ->flagged={c1}")
        print(f"  Caller 2 ->flagged={c2}")
        print(f"  Sum: {c1 + c2} (expected: 5)")

        # ── 4. DB STATE ───────────────────────────────────────────────────────
        rows = await check_db_state(conn)
        all_flagged = all(r["expiring_soon"] for r in rows)
        print(f"\n=== DB STATE ===")
        for r in rows:
            print(f"  id={r['id']} email={r['email']} expiring_soon={r['expiring_soon']}")

        # ── 5. VERDICT ────────────────────────────────────────────────────────
        print("\n=== VERDICT ===")
        overlap = (c1 > 0 and c2 > 0)
        fail = False

        if c1 + c2 != 5:
            print(f"  FAIL: sum {c1 + c2} != 5 — rows lost or miscounted")
            fail = True
        if overlap:
            print(f"  FAIL: c1={c1}, c2={c2} — BOTH callers got rows.")
            print(f"        FCM would fire {c1 + c2} times for 5 patients (double-fire).")
            fail = True
        if not all_flagged:
            print(f"  FAIL: not all 5 patients have expiring_soon=True in DB")
            fail = True
        if not fail:
            winner, loser = ("Caller 1", "Caller 2") if c1 > 0 else ("Caller 2", "Caller 1")
            print(f"  PASS")
            print(f"  c1={c1}, c2={c2}, total={c1 + c2}")
            print(f"  {winner} won the row lock ->flagged all 5, sent 5 FCM pushes")
            print(f"  {loser} blocked ->got 0 rows ->sent 0 FCM pushes")
            print(f"  DB: all 5 patients expiring_soon=True [ok]")
            print(f"  FCM fire count: exactly 5 (no double-fire) [ok]")

    finally:
        # ── 6. CLEANUP ────────────────────────────────────────────────────────
        print("\n=== CLEANUP ===")
        remaining = await cleanup(conn)
        if remaining == 0:
            print(f"  Deleted all @race-test.local patients. Remaining: 0 [ok]")
        else:
            print(f"  WARNING: {remaining} @race-test.local patients NOT deleted — delete manually")
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
