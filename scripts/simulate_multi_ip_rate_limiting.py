"""
simulate_multi_ip_rate_limiting.py
====================================
Pass 2 of the Mityahar Verification Playbook.

Verifies that the gcp_aware_key rate limiter correctly:
  1. Locks out a single spoofed IP after 10 requests/minute (lockout check).
  2. Allows 50 distinct IPs to each fire one request concurrently without
     triggering cross-tenant throttling (scale check).

Target endpoint: POST /api/v1/auth/doctor/login  (limit: 10/minute)

Prerequisites:
  - Backend running on port 8001 (python -m uvicorn app.main:app --reload --port 8001)
  - TRUSTED_PROXY_CIDR=127.0.0.1 in .env (trusts loopback -> reads XFF header)
  - Redis running (mityahar-redis Docker container or REDIS_URL in .env)

Usage:
    python -m scripts.simulate_multi_ip_rate_limiting
    python -m scripts.simulate_multi_ip_rate_limiting --port 8001
"""

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass, field
from typing import List

import httpx

BASE_URL_DEFAULT = "http://127.0.0.1:8001"
LOGIN_ENDPOINT = "/api/v1/auth/doctor/login"
RATE_LIMIT = 10          # requests per minute on this endpoint
LOCKOUT_TOTAL = 12       # we'll send this many to confirm 429 fires at 11+
SCALE_IP_COUNT = 50      # distinct IPs for scale check

# OAuth2PasswordRequestForm expects form data (not JSON).
# Credentials are wrong on purpose; we test the limiter, not auth.
# The rate limiter fires before DB credential lookup -> expect 401 (not 422).
DUMMY_FORM = {"username": "probe@mityahar.test", "password": "probe_pass"}


@dataclass
class Result:
    index: int
    xff: str
    status: int
    elapsed_ms: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _xff_headers(ip: str) -> dict:
    return {"X-Forwarded-For": ip}


async def _post_login(client: httpx.AsyncClient, idx: int, xff_ip: str) -> Result:
    start = time.perf_counter()
    resp = await client.post(
        LOGIN_ENDPOINT,
        data=DUMMY_FORM,  # OAuth2PasswordRequestForm expects form data
        headers=_xff_headers(xff_ip),
    )
    elapsed = (time.perf_counter() - start) * 1000
    return Result(index=idx, xff=xff_ip, status=resp.status_code, elapsed_ms=elapsed)


# ---------------------------------------------------------------------------
# Lockout Check
# ---------------------------------------------------------------------------

async def run_lockout_check(base_url: str) -> bool:
    """
    Send LOCKOUT_TOTAL sequential requests from one spoofed IP.
    Expect:
      - Requests 1–10: non-429 (likely 401 wrong creds or 422)
      - Requests 11–12: 429 Too Many Requests
    """
    print("\n-- LOCKOUT CHECK --------------------------------------------------")
    print(f"  Sending {LOCKOUT_TOTAL} sequential requests from 192.168.1.50")

    results: List[Result] = []
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        for i in range(1, LOCKOUT_TOTAL + 1):
            r = await _post_login(client, i, "192.168.1.50")
            results.append(r)
            tag = "429 BLOCKED [PASS]" if r.status == 429 else f"{r.status}"
            print(f"  [{i:>2}] {r.xff}  ->  {tag}  ({r.elapsed_ms:.0f}ms)")

    non_429 = [r for r in results if r.status != 429]
    blocked = [r for r in results if r.status == 429]

    first_block_idx = blocked[0].index if blocked else None

    # Pass conditions:
    # 1. Requests 1-10 must all be non-429
    early_non_429 = [r for r in results[:RATE_LIMIT] if r.status != 429]
    first_10_ok = len(early_non_429) == RATE_LIMIT

    # 2. Requests 11+ must all be 429
    late_blocked = [r for r in results[RATE_LIMIT:] if r.status == 429]
    overflow_ok = len(late_blocked) == (LOCKOUT_TOTAL - RATE_LIMIT)

    passed = first_10_ok and overflow_ok

    print(f"\n  First 10 requests non-429: {'OK' if first_10_ok else 'FAIL'} ({len(early_non_429)}/10)")
    print(f"  Requests 11-{LOCKOUT_TOTAL} returned 429: {'OK' if overflow_ok else 'FAIL'} ({len(late_blocked)}/{LOCKOUT_TOTAL - RATE_LIMIT})")
    print(f"  First block at request #{first_block_idx}" if first_block_idx else "  No 429 received at all!")
    print(f"\n  LOCKOUT CHECK: {'PASS' if passed else 'FAIL'}")

    if not passed and not blocked:
        print("\n  [!] No 429s received. Likely causes:")
        print("    - TRUSTED_PROXY_CIDR not set in .env (backend reads raw TCP IP 127.0.0.1 for ALL requests)")
        print("    - Backend not restarted after .env change")
        print("    - Redis not running (counters not shared if in-memory per-worker)")

    return passed


# ---------------------------------------------------------------------------
# Scale Check
# ---------------------------------------------------------------------------

async def run_scale_check(base_url: str) -> bool:
    """
    Fire SCALE_IP_COUNT concurrent requests, each from a distinct spoofed IP.
    Expect: all receive non-429 status (each IP has its own fresh bucket).
    """
    print("\n-- SCALE CHECK ----------------------------------------------------")
    print(f"  Firing {SCALE_IP_COUNT} concurrent requests from {SCALE_IP_COUNT} distinct IPs")

    ips = [f"192.168.1.{i}" for i in range(1, SCALE_IP_COUNT + 1)]

    async with httpx.AsyncClient(base_url=base_url, timeout=20.0) as client:
        tasks = [_post_login(client, i + 1, ip) for i, ip in enumerate(ips)]
        results: List[Result] = await asyncio.gather(*tasks)

    throttled = [r for r in results if r.status == 429]
    allowed = [r for r in results if r.status != 429]

    status_counts: dict = {}
    for r in results:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1

    print(f"\n  Status distribution:")
    for code, count in sorted(status_counts.items()):
        label = "THROTTLED [FAIL]" if code == 429 else "ok"
        print(f"    HTTP {code}: {count} requests  {label}")

    passed = len(throttled) == 0

    print(f"\n  Throttled (cross-tenant bleed): {len(throttled)}")
    print(f"  Allowed (distinct IP buckets):  {len(allowed)}")
    print(f"\n  SCALE CHECK: {'PASS' if passed else 'FAIL'}")

    if not passed:
        print(f"\n  [FAIL] {len(throttled)} requests throttled -- IPs sharing a rate bucket.")
        print("    Check that gcp_aware_key is active and TRUSTED_PROXY_CIDR is set.")

    return passed


# ---------------------------------------------------------------------------
# Connectivity pre-flight
# ---------------------------------------------------------------------------

async def preflight(base_url: str) -> bool:
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
            r = await client.get("/api/v1/auth/health-check")
            # Any response proves backend is up; 404 is fine.
            print(f"  Backend reachable: HTTP {r.status_code}")
            return True
    except httpx.ConnectError:
        print(f"  [FAIL] Cannot reach backend at {base_url}")
        print("    Start it with: python -m uvicorn app.main:app --reload --port 8001")
        return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(base_url: str) -> None:
    print("=" * 65)
    print("  Mityahar - Pass 2: Multi-IP Rate Limit Simulation")
    print("=" * 65)
    print(f"\n  Backend: {base_url}")
    print(f"  Endpoint: {LOGIN_ENDPOINT}  (limit: {RATE_LIMIT}/minute)")

    print("\n-- Pre-flight -----------------------------------------------------")
    if not await preflight(base_url):
        sys.exit(1)

    lockout_ok = await run_lockout_check(base_url)

    # Wait for rate-limit window to reset before scale check so prior
    # lock-out state from 192.168.1.50 doesn't pollute the scale run.
    print("\n  Waiting 62s for rate-limit window to reset before scale check...")
    await asyncio.sleep(62)

    scale_ok = await run_scale_check(base_url)

    print("\n== SUMMARY " + "=" * 54)
    print(f"  Lockout Check:  {'PASS' if lockout_ok else 'FAIL'}")
    print(f"  Scale Check:    {'PASS' if scale_ok else 'FAIL'}")
    overall = lockout_ok and scale_ok
    print(f"\n  Pass 2 Overall: {'PASS' if overall else 'FAIL'}")
    print("=" * 65 + "\n")

    if not overall:
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-IP rate limit simulation - Mityahar Pass 2")
    parser.add_argument("--port", type=int, default=8001, help="Backend port (default: 8001)")
    args = parser.parse_args()

    asyncio.run(main(f"http://127.0.0.1:{args.port}"))
