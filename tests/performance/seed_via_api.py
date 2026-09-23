"""
Real API-path patient registration load test.
Fires 50 concurrent POST /api/v1/auth/register requests through the actual HTTP stack.

REQUIREMENTS:
  - Backend running:  python -m uvicorn app.main:app --port 8001 --host 0.0.0.0
  - .env must have:   TRUSTED_PROXY_CIDR=127.0.0.1
    (so X-Forwarded-For is trusted from loopback — lets us give each request a distinct IP
     and avoid the 3/hour per-IP rate limit blocking 47 of the 50 test users)

Run:
    python -m tests.performance.seed_via_api

Outputs:
    tests/performance/reports/api_load_test.json
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8001"
REGISTER_URL = f"{BASE_URL}/api/v1/auth/register"

# 50 distinct registrations — one per fake source IP so rate limiter treats each as a new IP.
# Email pattern avoids collision with existing test patients (testpatient### @mityahar-load.com).
TEST_PAYLOADS = [
    {
        "email": f"apiload{i:03d}@mityahar-load.com",
        "password": f"Load@2026!{i}",
        "name": f"API Load Patient {i:03d}",
        "gender": "Female" if i % 2 == 0 else "Male",
        "height": float(160 + (i % 15)),
        "weight": float(55 + (i % 25)),
        "activity_level": ["S", "LA", "MA", "VA"][i % 4],
        "diet": ["Vegetarian", "Non-Vegetarian", "Eggetarian"][i % 3],
        "health_condition": "Healthy",
        "gdpr_consent": True,
        "_xff": f"10.0.1.{i}",   # distinct fake client IP — only honored if TRUSTED_PROXY_CIDR=127.0.0.1
    }
    for i in range(1, 51)
]


async def _register_one(client: httpx.AsyncClient, payload: dict) -> dict:
    xff = payload.pop("_xff")
    t0 = time.perf_counter()
    try:
        r = await client.post(
            REGISTER_URL,
            json=payload,
            headers={"X-Forwarded-For": xff},
            timeout=20,
        )
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        body = {}
        try:
            body = r.json()
        except Exception:
            pass
        return {
            "email": payload["email"],
            "status": r.status_code,
            "elapsed_ms": elapsed_ms,
            "detail": body.get("detail") if r.status_code != 201 else None,
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        return {"email": payload["email"], "status": "ERROR", "elapsed_ms": elapsed_ms, "detail": str(exc)}


async def run() -> None:
    print("=== Real API-path Load Test: 50 concurrent patient registrations ===\n")
    print(f"Endpoint: POST {REGISTER_URL}")
    print("XFF: 10.0.1.1 – 10.0.1.50  (requires TRUSTED_PROXY_CIDR=127.0.0.1 in .env)\n")

    # Confirm server is up
    try:
        health = httpx.get(f"{BASE_URL}/health", timeout=5)
        print(f"Server /health: {health.status_code}")
    except Exception as e:
        print(f"[ERROR] Server not reachable at {BASE_URL}: {e}")
        print("        Start it first:  python -m uvicorn app.main:app --port 8001 --host 0.0.0.0")
        sys.exit(1)

    payloads = [dict(p) for p in TEST_PAYLOADS]   # copy so we can mutate (pop _xff)
    t_start = time.perf_counter()

    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*[_register_one(client, p) for p in payloads])

    total_s = round(time.perf_counter() - t_start, 2)

    # --- Tally ---
    by_status: dict[int | str, list] = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)

    print(f"\n--- Results: {len(results)} requests in {total_s}s ---")
    STATUS_LABELS = {
        200: "200/201 Created  (success)",
        201: "200/201 Created  (success)",
        409: "409 Conflict     (duplicate email)",
        422: "422 Unprocessable (validation error)",
        429: "429 Too Many     (rate limited — need TRUSTED_PROXY_CIDR=127.0.0.1)",
        400: "400 Bad Request  (compliance/age check)",
    }
    for status in sorted(by_status.keys(), key=lambda x: str(x)):
        label = STATUS_LABELS.get(status, f"{status} Other")
        count = len(by_status[status])
        print(f"  {label}: {count}")

    success = by_status.get(200, []) + by_status.get(201, [])
    duplicates = by_status.get(409, [])
    rate_limited = by_status.get(429, [])
    validation_errors = by_status.get(422, [])

    timings = sorted(r["elapsed_ms"] for r in results)
    n = len(timings)
    print(f"\nTiming (ms):  min={timings[0]}  p50={timings[n//2]}  p95={timings[int(n*0.95)]}  max={timings[-1]}")
    print(f"\nSuccesses:       {len(success)}/{len(results)}")
    print(f"Duplicates (409): {len(duplicates)}  — should be 0 (all emails are distinct)")
    print(f"Rate limited:     {len(rate_limited)}"
          + ("  ← add TRUSTED_PROXY_CIDR=127.0.0.1 to .env to fix" if rate_limited else ""))

    if validation_errors:
        print("\nValidation errors (first 3):")
        for r in validation_errors[:3]:
            print(f"  {r['email']}: {r['detail']}")

    # --- Pass/Fail ---
    pass_conditions = [
        len(success) == 50,
        len(duplicates) == 0,
        len(rate_limited) == 0,
        len(validation_errors) == 0,
    ]
    overall = all(pass_conditions)
    print(f"\nOVERALL: {'PASS' if overall else 'FAIL'}")
    if not overall:
        if len(success) < 50:
            print(f"  Expected 50 successes, got {len(success)}")
        if rate_limited:
            print(f"  {len(rate_limited)} requests rate-limited — is TRUSTED_PROXY_CIDR=127.0.0.1 in .env?")

    # --- Save report ---
    report_dir = Path(__file__).parent / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    out = report_dir / "api_load_test.json"
    out.write_text(json.dumps({
        "total": len(results),
        "total_elapsed_s": total_s,
        "by_status": {str(k): len(v) for k, v in by_status.items()},
        "timing_ms": {
            "min": timings[0],
            "p50": timings[n // 2],
            "p95": timings[int(n * 0.95)],
            "max": timings[-1],
        },
        "pass": overall,
        "results": results,
    }, indent=2))
    print(f"\nFull results -> {out}")


if __name__ == "__main__":
    asyncio.run(run())
