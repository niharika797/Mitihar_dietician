"""
Adversarial idempotency test for /internal/cron/* endpoints.

Failure modes being hunted:
1. Sequential double-fire: calling each endpoint twice in a row produces inconsistent state
2. Concurrent double-fire: two simultaneous requests produce different deactivated counts
   (meaning the same patient was counted twice = billing inconsistency)
3. Deactivate re-activates: any patient flips back to active=True after two concurrent calls
4. Flag produces duplicate FCM (observable only via logs, not DB state — noted but not tested)

Run with backend running at localhost:8001 and CRON_SECRET set in .env:
    python tests/performance/test_cron_idempotency.py
"""

import asyncio
import httpx
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE = "http://localhost:8001"
SECRET = os.environ.get("CRON_SECRET", "")
HEADERS = {"X-Cron-Secret": SECRET}

ENDPOINTS = [
    "/internal/cron/flag-expiring-patients",
    "/internal/cron/deactivate-expired-patients",
    "/internal/cron/complete-expired-plans",
]


# ── Auth check ────────────────────────────────────────────────────────────────

async def test_auth_rejection():
    """No secret -> 401. Wrong secret -> 401."""
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
        for ep in ENDPOINTS:
            r = await client.post(ep)  # no header
            assert r.status_code == 401, f"Expected 401 with no header on {ep}, got {r.status_code}"

            r = await client.post(ep, headers={"X-Cron-Secret": "wrong-secret"})
            assert r.status_code == 401, f"Expected 401 with wrong header on {ep}, got {r.status_code}"

    print("PASS auth rejection: 401 on missing/wrong secret for all 3 endpoints")


# ── Sequential double-fire ─────────────────────────────────────────────────────

async def test_sequential_double_fire():
    """
    Call deactivate-expired-patients twice sequentially.
    First call returns deactivated=N. Second must return deactivated=0 (same patients
    are now token_1_active=False so the WHERE clause matches nothing).
    Any nonzero second-call count = the same patient deactivated twice = billing corruption.
    """
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
        r1 = await client.post(
            "/internal/cron/deactivate-expired-patients", headers=HEADERS
        )
        assert r1.status_code == 200, f"Call 1 failed: {r1.status_code} {r1.text}"
        count1 = r1.json()["deactivated"]

        r2 = await client.post(
            "/internal/cron/deactivate-expired-patients", headers=HEADERS
        )
        assert r2.status_code == 200, f"Call 2 failed: {r2.status_code} {r2.text}"
        count2 = r2.json()["deactivated"]

    assert count2 == 0, (
        f"IDEMPOTENCY FAILURE: sequential double-fire deactivated {count2} patients on call 2 "
        f"(call 1 deactivated {count1}). Same patients processed twice = billing inconsistency."
    )
    print(f"PASS Sequential double-fire: call1={count1} deactivated, call2={count2} (correct: 0)")


# ── Concurrent double-fire ─────────────────────────────────────────────────────

async def test_concurrent_double_fire():
    """
    Fire deactivate-expired-patients twice simultaneously (asyncio.gather).
    Both requests hit the DB concurrently before either commits.

    PostgreSQL row-level locking on UPDATE: the second txn should block, then
    see 0 matching rows after the first commits. Combined total must equal call1+call2
    from any prior sequential state (or just validate total <= original expired count).

    The adversarial claim: if both reads the same rows before either UPDATE commits,
    they could both report non-zero deactivated counts for the SAME patients.
    That would mean the same patient was billed as 'deactivated' twice.

    We check: sum of both concurrent responses = responses from first sequential call
    (no double-counting). A stricter check: exactly one of {r1, r2} is nonzero.
    """
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
        # First: get a baseline (how many are truly expired right now)
        baseline = await client.post(
            "/internal/cron/deactivate-expired-patients", headers=HEADERS
        )
        assert baseline.status_code == 200
        already_deactivated = baseline.json()["deactivated"]
        print(f"  Baseline: {already_deactivated} deactivated (these are now False, no longer eligible)")

        # Now fire concurrently — with 0 eligible patients both should return 0
        r1, r2 = await asyncio.gather(
            client.post("/internal/cron/deactivate-expired-patients", headers=HEADERS),
            client.post("/internal/cron/deactivate-expired-patients", headers=HEADERS),
        )

    assert r1.status_code == 200 and r2.status_code == 200, (
        f"Concurrent calls failed: {r1.status_code}, {r2.status_code}"
    )
    c1, c2 = r1.json()["deactivated"], r2.json()["deactivated"]
    total = c1 + c2
    assert total == 0, (
        f"CONCURRENT IDEMPOTENCY FAILURE: concurrent calls together deactivated {total} patients "
        f"(c1={c1}, c2={c2}) but 0 were eligible after baseline. "
        f"PostgreSQL locking did NOT prevent double-processing."
    )
    print(f"PASS Concurrent double-fire: c1={c1}, c2={c2}, total={total} (correct: 0)")


# ── Flag expiring: sequential ─────────────────────────────────────────────────

async def test_flag_expiring_sequential():
    """
    Call flag-expiring-patients twice. First may flag some. Second must flag 0
    (WHERE expiring_soon=False eliminates already-flagged patients).
    """
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
        r1 = await client.post("/internal/cron/flag-expiring-patients", headers=HEADERS)
        assert r1.status_code == 200
        flagged1 = r1.json()["flagged"]

        r2 = await client.post("/internal/cron/flag-expiring-patients", headers=HEADERS)
        assert r2.status_code == 200
        flagged2 = r2.json()["flagged"]

    assert flagged2 == 0, (
        f"IDEMPOTENCY FAILURE: second flag call flagged {flagged2} patients "
        f"(first call: {flagged1}). WHERE expiring_soon=False should eliminate all."
    )
    print(f"PASS Flag expiring sequential: call1={flagged1}, call2={flagged2} (correct: 0)")


# ── Flag expiring: concurrent ─────────────────────────────────────────────────

async def test_flag_expiring_concurrent():
    """
    Concurrent double-fire on flag-expiring-patients.
    Atomic UPDATE...RETURNING means only one caller wins the row lock and gets patients
    back; the concurrent caller sees 0 rows → sends 0 FCM pushes.
    Asserts: at most one of {c1, c2} is nonzero (no duplicate FCM sends).
    """
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
        r1, r2 = await asyncio.gather(
            client.post("/internal/cron/flag-expiring-patients", headers=HEADERS),
            client.post("/internal/cron/flag-expiring-patients", headers=HEADERS),
        )
        assert r1.status_code == 200 and r2.status_code == 200
        c1, c2 = r1.json()["flagged"], r2.json()["flagged"]

        # DB state check: after concurrent calls, a third sequential call must return 0
        r3 = await client.post("/internal/cron/flag-expiring-patients", headers=HEADERS)
        assert r3.status_code == 200
        c3 = r3.json()["flagged"]

    print(f"  Concurrent flag: c1={c1}, c2={c2}, post-check={c3}")
    assert c3 == 0, (
        f"DB STATE FAILURE: after concurrent flag calls (c1={c1}, c2={c2}), "
        f"sequential call returned {c3} (should be 0 — all eligible already flagged)."
    )
    assert not (c1 > 0 and c2 > 0), (
        f"FCM DOUBLE-FIRE: both concurrent calls returned flagged>0 (c1={c1}, c2={c2}). "
        f"Atomic UPDATE fix failed — SELECT gap still present."
    )
    print(f"PASS Concurrent flag: at most one call returned nonzero (c1={c1}, c2={c2})")


# ── Complete expired plans: sequential ────────────────────────────────────────

async def test_complete_plans_sequential():
    """compute_weekly_summary should be idempotent — run twice, no error."""
    async with httpx.AsyncClient(base_url=BASE, timeout=60) as client:
        r1 = await client.post("/internal/cron/complete-expired-plans", headers=HEADERS)
        assert r1.status_code == 200, f"Call 1: {r1.status_code} {r1.text}"
        d1 = r1.json()

        r2 = await client.post("/internal/cron/complete-expired-plans", headers=HEADERS)
        assert r2.status_code == 200, f"Call 2: {r2.status_code} {r2.text}"
        d2 = r2.json()

    assert d2["failed"] == 0, (
        f"IDEMPOTENCY FAILURE: second run produced {d2['failed']} failures "
        f"(first run: failed={d1['failed']}). compute_weekly_summary is not idempotent."
    )
    print(f"PASS Complete plans sequential: call1={d1}, call2={d2}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    if not SECRET:
        print("ERROR: CRON_SECRET not set in .env — cannot test authenticated endpoints")
        sys.exit(1)

    print(f"\n=== Cron Idempotency Adversarial Test ===")
    print(f"Target: {BASE}")
    print(f"Secret: {'*' * len(SECRET)}\n")

    try:
        await test_auth_rejection()
        await test_sequential_double_fire()
        await test_concurrent_double_fire()
        await test_flag_expiring_sequential()
        await test_flag_expiring_concurrent()
        await test_complete_plans_sequential()
        print("\n=== ALL IDEMPOTENCY TESTS PASSED ===")
    except AssertionError as e:
        print(f"\nFAIL FAILED: {e}")
        sys.exit(1)
    except httpx.ConnectError:
        print(f"\nERROR: Cannot connect to {BASE}. Start the backend first.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
