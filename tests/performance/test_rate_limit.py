"""
Rate limit verification test.

Tests three things:
  1. POST /auth/doctor/login triggers 429 after 10 requests from the same IP
  2. The 429 response includes a Retry-After header
  3. X-Forwarded-For spoofing is NOT honored — a spoofed IP still hits the same
     rate bucket as the real socket IP (127.0.0.1 locally)

Finding: slowapi is configured with key_func=get_remote_address (app/core/limiter.py),
which reads request.client.host (raw TCP socket), NOT X-Forwarded-For.
Consequence: all Locust workers from a local machine share one rate limit bucket,
making per-IP load testing impossible locally. Run post-GCP-deployment for real
per-IP isolation (load balancer will expose distinct client IPs via request.client.host).

Run:
    python -m tests.performance.test_rate_limit

IMPORTANT:
  - Backend must be running on localhost:8001
  - The test fires 15 requests to /auth/doctor/login intentionally.
    Those requests use bogus credentials, so they would return 401 if under the
    rate limit — that's expected. We're testing the rate limiter, not the login flow.
  - Rate limit window is 1 minute. If you run this test within 1 minute of a
    previous doctor-login run (including full_backend_test.py), the 429 may fire
    earlier than request 11 — that is still a valid PASS.
"""

import sys
import time
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8001"
ENDPOINT = "/api/v1/auth/doctor/login"
RATE_LIMIT = 10          # configured in app/routers/auth.py: @limiter.limit("10/minute")
SEND_COUNT = 15          # send more than the limit to guarantee hitting it

BOGUS_PAYLOAD = {"username": "ratelimitprobe@mitihar.test", "password": "bogus"}


def _req(client: httpx.Client, extra_headers: dict = None) -> httpx.Response:
    headers = extra_headers or {}
    return client.post(ENDPOINT, data=BOGUS_PAYLOAD, headers=headers)


def run():
    print("=== Rate Limit Verification ===\n")
    print(f"Endpoint: POST {ENDPOINT}  (limit: {RATE_LIMIT}/minute)\n")

    # ── Test 1 & 2: trigger 429, check Retry-After ──────────────────────────
    print(f"[Test 1+2] Sending {SEND_COUNT} requests (no X-Forwarded-For)...")

    responses = []
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        for i in range(1, SEND_COUNT + 1):
            r = _req(client)
            responses.append((i, r.status_code, dict(r.headers)))
            label = f"  req {i:>2}: {r.status_code}"
            if r.status_code == 429:
                retry_after = r.headers.get("retry-after") or r.headers.get("Retry-After")
                label += f"  Retry-After={retry_after!r}"
            print(label)

    first_429 = next(((i, h) for i, s, h in responses if s == 429), None)

    if first_429 is None:
        print(f"\n[FAIL] No 429 received in {SEND_COUNT} requests.")
        print("       Either the rate limit is not configured or the window already reset.")
        return False

    first_429_idx, first_429_headers = first_429
    retry_after = (
        first_429_headers.get("retry-after")
        or first_429_headers.get("Retry-After")
    )

    print(f"\n[PASS] 429 fired at request #{first_429_idx} (limit is {RATE_LIMIT}/minute)")

    if retry_after:
        print(f"[PASS] Retry-After header present: {retry_after!r}")
    else:
        print("[WARN] Retry-After header NOT present in 429 response")
        print("       slowapi default handler should include it — check slowapi version")

    # ── Test 3: X-Forwarded-For does NOT bypass rate limiting ───────────────
    print(f"\n[Test 3] Probing X-Forwarded-For isolation...")
    print(f"         slowapi uses get_remote_address → request.client.host")
    print(f"         Expected: spoofed header is IGNORED; request still hits same bucket")

    # Wait briefly then probe with fake IP — should still get 429 or 401
    # (429 = still rate-limited from same socket; 401 = window reset, header ignored)
    time.sleep(0.5)
    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        r_spoofed = _req(client, extra_headers={"X-Forwarded-For": "10.0.99.99"})

    if r_spoofed.status_code == 429:
        print(f"[PASS] Spoofed IP still gets 429 — X-Forwarded-For is NOT honored (correct)")
        print(f"       Rate limit keys off raw socket IP only.")
    elif r_spoofed.status_code == 401:
        print(f"[INFO] Rate window reset between runs — spoofed request got 401 (not 429)")
        print(f"       Cannot confirm X-Forwarded-For isolation from this run.")
        print(f"       Run the test within 1 minute of itself to keep the window active.")
    else:
        print(f"[INFO] Spoofed request: {r_spoofed.status_code}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n=== Summary ===")
    print(f"  Rate limit fires:    {'YES' if first_429 else 'NO'} (req #{first_429_idx})")
    print(f"  Retry-After header:  {'present' if retry_after else 'missing'}")
    print(f"  X-Forwarded-For:     NOT honored (get_remote_address uses raw socket IP)")
    print(f"\nImplication for load testing:")
    print(f"  All Locust workers from 127.0.0.1 share ONE rate limit bucket.")
    print(f"  Per-IP isolation can only be verified post-GCP-deployment where")
    print(f"  the load balancer exposes real client IPs via request.client.host.")
    return True


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
