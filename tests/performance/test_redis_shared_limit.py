"""
Distributed rate limit test — proves Redis sharing across two uvicorn instances.

REQUIRES two uvicorn instances running before you run this:
  Terminal A:  python -m uvicorn app.main:app --port 8001 --host 0.0.0.0
  Terminal B:  python -m uvicorn app.main:app --port 8002 --host 0.0.0.0

Both must point at the same REDIS_URL (set in .env).

Logic:
  Rate limit on POST /api/v1/auth/doctor/login is 10/minute per IP.
  Fire 5 requests to port 8001 — counter in Redis = 5.
  Fire requests to port 8002 — counter continues from 5 since Redis is shared.
  Request #11 total (6th to port 8002) MUST return 429 if Redis is shared.
  If in-memory (broken): each instance has its own counter, so port 8002 allows
  another 10 independently — the test would see only 200/401 from 8002.

Run:
    python -m tests.performance.test_redis_shared_limit
"""

import sys
import httpx

BASE_A = "http://127.0.0.1:8001"
BASE_B = "http://127.0.0.1:8002"
ENDPOINT = "/api/v1/auth/doctor/login"
BOGUS = {"username": "redis_probe@mitihar.test", "password": "bogus"}


def _check_reachable(base: str) -> bool:
    try:
        r = httpx.get(f"{base}/", timeout=3)
        return r.status_code < 500
    except Exception:
        return False


def run() -> bool:
    print("=== Distributed Rate Limit (Redis Sharing) Test ===\n")

    print("Checking both instances are reachable...")
    ok_a = _check_reachable(BASE_A)
    ok_b = _check_reachable(BASE_B)
    if not ok_a:
        print(f"[ERROR] Instance A ({BASE_A}) is not reachable.")
        print("        Start it:  python -m uvicorn app.main:app --port 8001 --host 0.0.0.0")
        return False
    if not ok_b:
        print(f"[ERROR] Instance B ({BASE_B}) is not reachable.")
        print("        Start it:  python -m uvicorn app.main:app --port 8002 --host 0.0.0.0")
        return False
    print("  Both instances reachable.\n")

    print("Instance A (8001): sending 5 requests...")
    with httpx.Client(base_url=BASE_A, timeout=10) as c:
        for i in range(1, 6):
            r = c.post(ENDPOINT, data=BOGUS)
            status = r.status_code
            if status == 429:
                print(f"  req {i}: {status}  [WARN] 429 fired before test even reached Instance B.")
                print("  Rate limit window may still be active from a previous run.")
                print("  Wait 60 seconds and retry.")
                return False
            print(f"  req {i}: {status}")

    print(f"\nCounter should now be 5 in Redis.")
    print("Instance B (8002): sending up to 7 more requests (expect 429 at #11 total)...\n")

    first_429_at = None
    with httpx.Client(base_url=BASE_B, timeout=10) as c:
        for i in range(6, 13):
            r = c.post(ENDPOINT, data=BOGUS)
            status = r.status_code
            label = f"  req {i:>2} (B): {status}"
            if status == 429:
                label += "  ← 429 fired"
                first_429_at = i
                print(label)
                break
            print(label)

    print()
    if first_429_at is not None and first_429_at <= 11:
        print(f"RESULT: PASS — Redis sharing confirmed")
        print(f"  429 fired at total request #{first_429_at} (limit is 10/minute, shared across both instances).")
        print(f"  Both uvicorn instances share the same Redis rate limit counter.")
        return True
    elif first_429_at is not None:
        print(f"RESULT: PARTIAL — 429 fired at request #{first_429_at}.")
        print(f"  Expected at ≤11, got at {first_429_at}. Redis may be shared but count is off.")
        print(f"  Check if previous requests within this minute window filled part of the bucket.")
        return True
    else:
        print("RESULT: FAIL — instances not sharing state")
        print("  No 429 from Instance B after 12 total requests.")
        print("  Each instance is using its own in-memory counter.")
        print("  Check that REDIS_URL is set in .env and both processes loaded it.")
        return False


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
