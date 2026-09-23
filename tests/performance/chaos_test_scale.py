"""
Scaled chaos test: 200 and 1000 concurrent.

Hypothesis:
- 200 concurrent: pool (40 conns) handles fast GET reads with latency spikes.
  Redis fail-open marginally increases DB pressure; likely holds.
- 1000 concurrent: prior run showed QueuePool exhaustion (size=20+overflow=20).
  Redis fail-open at 1000 concurrent should make exhaustion WORSE — previously
  rate-limited requests now also hit the pool, reducing time-to-first-failure.
  This is the specific interaction being hunted: fail-open + pool exhaustion = faster crash.

Run: python tests/performance/chaos_test_scale.py
"""

import asyncio
import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

try:
    import httpx
except ImportError:
    print("httpx not installed")
    sys.exit(1)

HERE = Path(__file__).parent
MANIFEST = HERE / "test_manifest.json"
REPORTS_DIR = HERE / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

BASE = "http://localhost:8001"
DB_CONTAINER = "mityahar_postgres"
DB_NAME = "mityahar_db"
DB_USER = "admin"


def get_patient_token() -> str:
    cached = REPORTS_DIR / "chaos_token.txt"
    if cached.exists():
        return cached.read_text().strip()
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    patients = manifest.get("patients", [])
    patient_info = patients[0] if patients else {"patient_id": 1, "email": "testpatient001@mityahar.test"}
    sys.path.insert(0, str(HERE.parents[1]))
    from app.core.security import create_access_token
    from datetime import timedelta
    token = create_access_token(
        data={"sub": str(patient_info["patient_id"]), "role": "patient",
              "email": patient_info["email"], "sub_active": True},
        expires_delta=timedelta(hours=2),
    )
    cached.write_text(token)
    return token


def docker_stop_redis():
    subprocess.run(["docker", "stop", "mityahar-redis"], capture_output=True)


def docker_start_redis():
    subprocess.run(["docker", "start", "mityahar-redis"], capture_output=True)
    time.sleep(2)


def redis_running() -> bool:
    r = subprocess.run(["docker", "inspect", "--format", "{{.State.Running}}", "mityahar-redis"],
                       capture_output=True, text=True)
    return r.stdout.strip() == "true"


def db_terminate_all() -> str:
    r = subprocess.run([
        "docker", "exec", DB_CONTAINER,
        "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-c",
        f"SELECT count(pg_terminate_backend(pid)) FROM pg_stat_activity "
        f"WHERE datname='{DB_NAME}' AND pid <> pg_backend_pid();",
    ], capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


def count_db_connections() -> int:
    r = subprocess.run([
        "docker", "exec", DB_CONTAINER,
        "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-c",
        f"SELECT count(*) FROM pg_stat_activity WHERE datname='{DB_NAME}';",
    ], capture_output=True, text=True)
    try:
        return int(r.stdout.strip())
    except Exception:
        return -1


async def run_load(token: str, duration: int, concurrency: int,
                   chaos_fn=None, chaos_at: int = 15,
                   chaos_stop_fn=None, chaos_stop_at: int = 45,
                   label: str = "") -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    results = defaultdict(lambda: {"ok": 0, "fail": 0, "errors": defaultdict(int)})
    t_start = time.time()
    chaos_fired = False
    chaos_stop_fired = False

    async def single_req(client):
        elapsed = time.time() - t_start
        second = int(elapsed)
        try:
            r = await client.get(f"{BASE}/api/v1/meal-plan/week",
                                 headers=headers, timeout=15.0)
            if r.status_code < 500:
                results[second]["ok"] += 1
            else:
                results[second]["fail"] += 1
                results[second]["errors"][r.status_code] += 1
        except Exception as e:
            results[second]["fail"] += 1
            results[second]["errors"][type(e).__name__] += 1

    # Use a semaphore to cap true concurrency — asyncio.gather with 1000 tasks
    # still creates 1000 simultaneous coroutines but the semaphore limits how many
    # actually hold a connection slot at once.
    sem = asyncio.Semaphore(concurrency)

    async def guarded_req(client):
        async with sem:
            await single_req(client)

    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=concurrency + 50,
                                                      max_keepalive_connections=concurrency)) as client:
        while True:
            elapsed = time.time() - t_start
            if elapsed >= duration:
                break

            if chaos_fn and not chaos_fired and elapsed >= chaos_at:
                chaos_fn()
                chaos_fired = True
                print(f"  [{label}] t={elapsed:.0f}s — chaos injected")

            if chaos_stop_fn and not chaos_stop_fired and elapsed >= chaos_stop_at:
                chaos_stop_fn()
                chaos_stop_fired = True
                print(f"  [{label}] t={elapsed:.0f}s — chaos stopped")

            wave = [guarded_req(client) for _ in range(concurrency)]
            await asyncio.gather(*wave)
            # no sleep — waves back-to-back to maximize pressure

    total_ok = sum(v["ok"] for v in results.values())
    total_fail = sum(v["fail"] for v in results.values())
    total = total_ok + total_fail
    fail_pct = total_fail / total * 100 if total else 0

    # chaos window: from chaos_at to chaos_at+15s
    chaos_window = {k: v for k, v in results.items() if chaos_at <= k <= chaos_at + 15}
    cw_ok = sum(v["ok"] for v in chaos_window.values())
    cw_fail = sum(v["fail"] for v in chaos_window.values())
    cw_total = cw_ok + cw_fail
    chaos_fail_pct = cw_fail / cw_total * 100 if cw_total else 0

    # errors breakdown
    all_errors = defaultdict(int)
    for v in results.values():
        for k, cnt in v["errors"].items():
            all_errors[k] += cnt

    return {
        "label": label,
        "concurrency": concurrency,
        "total": total,
        "ok": total_ok,
        "fail": total_fail,
        "fail_pct": fail_pct,
        "chaos_window_fail_pct": chaos_fail_pct,
        "chaos_window_requests": cw_total,
        "errors": dict(all_errors),
    }


def hdr(label, concurrency):
    print(f"\n{'='*60}")
    print(f"  {label}  [concurrency={concurrency}]")
    print(f"{'='*60}")


def show(r):
    print(f"  total={r['total']}  ok={r['ok']}  fail={r['fail']}  ({r['fail_pct']:.1f}%)")
    print(f"  chaos-window ({r['chaos_window_requests']} reqs): {r['chaos_window_fail_pct']:.1f}% fail")
    if r["errors"]:
        print(f"  error breakdown: {dict(r['errors'])}")


async def run_scale(concurrency: int, token: str, results_store: dict):
    tag = str(concurrency)
    hdr(f"BASELINE — no chaos", concurrency)
    baseline = await run_load(token, duration=20, concurrency=concurrency, label=f"baseline_{tag}")
    show(baseline)

    if not redis_running():
        docker_start_redis()

    hdr("PHASE: Redis kill (chaos at t=15s, restart at t=45s, total 60s)", concurrency)
    print(f"  Redis before: {redis_running()}")
    r_redis = await run_load(
        token, duration=60, concurrency=concurrency,
        chaos_fn=docker_stop_redis, chaos_at=15,
        chaos_stop_fn=docker_start_redis, chaos_stop_at=45,
        label=f"redis_{tag}",
    )
    print(f"  Redis after: {redis_running()}")
    show(r_redis)

    if not redis_running():
        docker_start_redis()

    hdr("PHASE: DB terminate (chaos at t=15s, total 45s)", concurrency)
    conn_before = count_db_connections()
    print(f"  DB connections before: {conn_before}")

    def db_chaos():
        out = db_terminate_all()
        print(f"    pg_terminate_backend -> {out}")
        print(f"    connections after terminate: {count_db_connections()}")

    r_db = await run_load(
        token, duration=45, concurrency=concurrency,
        chaos_fn=db_chaos, chaos_at=15,
        label=f"db_{tag}",
    )
    print(f"  DB connections recovered: {count_db_connections()}")
    show(r_db)

    hdr("PHASE: Combined Redis+DB (chaos at t=15s, Redis restart t=45s, total 60s)", concurrency)
    if not redis_running():
        docker_start_redis()

    def combined_chaos():
        print("    Stopping Redis...")
        docker_stop_redis()
        out = db_terminate_all()
        print(f"    pg_terminate_backend -> {out}")

    r_combined = await run_load(
        token, duration=60, concurrency=concurrency,
        chaos_fn=combined_chaos, chaos_at=15,
        chaos_stop_fn=docker_start_redis, chaos_stop_at=45,
        label=f"combined_{tag}",
    )
    if not redis_running():
        docker_start_redis()
    show(r_combined)

    # Verdict: does combined > redis alone? That's the interaction we're hunting.
    redis_cw = r_redis["chaos_window_fail_pct"]
    combined_cw = r_combined["chaos_window_fail_pct"]
    db_cw = r_db["chaos_window_fail_pct"]

    print(f"\n  --- Verdict @ concurrency={concurrency} ---")
    print(f"  Baseline fail%:           {baseline['fail_pct']:.1f}%")
    print(f"  Redis-kill chaos window:  {redis_cw:.1f}%")
    print(f"  DB-terminate chaos window:{db_cw:.1f}%")
    print(f"  Combined chaos window:    {combined_cw:.1f}%")

    # The key question: is combined significantly worse than redis alone?
    # If combined_cw > redis_cw + 10: the interaction amplifies failures.
    interaction_amplified = combined_cw > redis_cw + 10
    if interaction_amplified:
        print(f"  INTERACTION CONFIRMED: combined fail ({combined_cw:.1f}%) > redis-only ({redis_cw:.1f}%) + 10pp")
        print(f"  Fail-open under DB-exhausted load amplifies failures — not additive, multiplicative.")
    else:
        print(f"  No interaction amplification: combined ({combined_cw:.1f}%) <= redis ({redis_cw:.1f}%) + 10pp")

    results_store[concurrency] = {
        "baseline": baseline,
        "redis": r_redis,
        "db": r_db,
        "combined": r_combined,
        "interaction_amplified": interaction_amplified,
    }


async def main():
    print("Getting auth token...")
    token = get_patient_token()
    print(f"Token: {'*' * 20}...{token[-6:]}\n")

    all_results = {}

    # Run at 200 concurrent
    await run_scale(200, token, all_results)

    # Brief cooldown — let pool recover and Redis stabilize
    print("\nCooldown 10s before 1000-concurrent run...")
    await asyncio.sleep(10)
    if not redis_running():
        docker_start_redis()
        await asyncio.sleep(3)

    # Run at 1000 concurrent
    await run_scale(1000, token, all_results)

    # Final comparison
    print(f"\n{'='*60}")
    print("  FINAL COMPARISON: 200 vs 1000 concurrent")
    print(f"{'='*60}")
    for c in [200, 1000]:
        r = all_results.get(c, {})
        if r:
            bl = r["baseline"]["fail_pct"]
            comb = r["combined"]["chaos_window_fail_pct"]
            amp = r.get("interaction_amplified", False)
            print(f"  concurrency={c}: baseline={bl:.1f}%  combined-chaos-window={comb:.1f}%  "
                  f"interaction={'AMPLIFIED' if amp else 'not amplified'}")

    report_path = REPORTS_DIR / "chaos_scale_report.json"
    report_path.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\n  Report: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
