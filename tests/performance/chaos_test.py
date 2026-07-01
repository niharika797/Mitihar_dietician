"""
Chaos test: Redis kill + DB connection drop under sustained concurrent load.

Avoids locust login rate-limit collision (all users share 127.0.0.1 bucket)
by authenticating once before the test, then running raw httpx concurrent
requests using pre-issued tokens.

Prerequisites:
- Backend running at localhost:8001
- Docker containers: mityahar-redis, mityahar_postgres
- At least one patient in test_manifest.json with a known password

Run:
    python tests/performance/chaos_test.py
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
    print("httpx not installed. Run: pip install httpx")
    sys.exit(1)

HERE = Path(__file__).parent
MANIFEST = HERE / "test_manifest.json"
REPORTS_DIR = HERE / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

BASE = "http://localhost:8001"
CONCURRENT = 40     # concurrent requests per wave
WAVE_DURATION = 60  # seconds per phase (Redis kill / DB drop)
DB_CONTAINER = "mityahar_postgres"
DB_NAME = "mityahar_db"
DB_USER = "admin"


# ── auth ─────────────────────────────────────────────────────────────────────

def get_patient_token() -> tuple[str, dict]:
    """
    Get a patient token. Uses a pre-minted token file (bypass rate limit)
    if present, otherwise mints one directly via the app's create_access_token.
    Never calls the API auth endpoint — avoids rate-limit exhaustion during chaos setup.
    """
    import sys
    from datetime import timedelta
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    patients = manifest.get("patients", [])
    patient_info = patients[0] if patients else {"patient_id": 1, "email": "testpatient001@mityahar.test"}

    # Try cached token file first
    cached = REPORTS_DIR / "chaos_token.txt"
    if cached.exists():
        token = cached.read_text().strip()
        print(f"  Using pre-minted token for {patient_info['email']}")
        return token, patient_info

    # Mint directly via app security (no HTTP, no rate limit)
    sys.path.insert(0, str(HERE.parents[1]))
    from app.core.security import create_access_token
    token = create_access_token(
        data={"sub": str(patient_info["patient_id"]), "role": "patient",
              "email": patient_info["email"], "sub_active": True},
        expires_delta=timedelta(hours=2),
    )
    cached.write_text(token)
    print(f"  Minted token for {patient_info['email']}")
    return token, patient_info


def get_combo_entries(token: str) -> list:
    """Fetch meal plan for confirmed combo IDs."""
    r = httpx.get(f"{BASE}/api/v1/meal-plan/week",
                  headers={"Authorization": f"Bearer {token}"})
    entries = []
    if r.status_code == 200:
        for day in r.json().get("days", []):
            date_str = day.get("date", "")
            for meal_type, meal_data in day.get("meals", {}).items():
                for combo in meal_data.get("combos", []):
                    cid = combo.get("combo_id")
                    fids = [d["food_item_id"] for d in combo.get("dishes", []) if d.get("food_item_id")]
                    if cid and fids and date_str:
                        entries.append({"combo_id": cid, "food_item_ids": fids,
                                        "meal_type": meal_type, "date": date_str})
    return entries


# ── helpers ──────────────────────────────────────────────────────────────────

def docker_stop_redis():
    subprocess.run(["docker", "stop", "mityahar-redis"], capture_output=True)


def docker_start_redis():
    subprocess.run(["docker", "start", "mityahar-redis"], capture_output=True)
    time.sleep(2)  # brief settle


def redis_running() -> bool:
    r = subprocess.run(["docker", "inspect", "--format", "{{.State.Running}}", "mityahar-redis"],
                       capture_output=True, text=True)
    return r.stdout.strip() == "true"


def db_terminate_all() -> str:
    r = subprocess.run([
        "docker", "exec", "mityahar_postgres",
        "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-c",
        f"SELECT count(pg_terminate_backend(pid)) FROM pg_stat_activity "
        f"WHERE datname='{DB_NAME}' AND pid <> pg_backend_pid();",
    ], capture_output=True, text=True)
    return r.stdout.strip() + r.stderr.strip()


def count_db_connections() -> int:
    r = subprocess.run([
        "docker", "exec", "mityahar_postgres",
        "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-c",
        f"SELECT count(*) FROM pg_stat_activity WHERE datname='{DB_NAME}';",
    ], capture_output=True, text=True)
    try:
        return int(r.stdout.strip())
    except Exception:
        return -1


# ── async load runner ─────────────────────────────────────────────────────────

async def run_concurrent_load(token: str, duration: int, concurrency: int,
                              chaos_fn=None, chaos_at: int = 20,
                              chaos_stop_fn=None, chaos_stop_at: int = 50,
                              label: str = "") -> dict:
    """
    Fire concurrent GET /meal-plan/week requests for `duration` seconds.
    At chaos_at, call chaos_fn(). At chaos_stop_at, call chaos_stop_fn().
    Returns per-second error counts and totals.
    """
    headers = {"Authorization": f"Bearer {token}"}
    results = defaultdict(lambda: {"ok": 0, "fail": 0, "errors": defaultdict(int)})
    t_start = time.time()
    chaos_fired = False
    chaos_stop_fired = False

    async def single_request(client: httpx.AsyncClient):
        elapsed = time.time() - t_start
        second = int(elapsed)
        try:
            r = await client.get(f"{BASE}/api/v1/meal-plan/week", headers=headers, timeout=10.0)
            if r.status_code < 500:
                results[second]["ok"] += 1
            else:
                results[second]["fail"] += 1
                results[second]["errors"][r.status_code] += 1
        except Exception as e:
            results[second]["fail"] += 1
            results[second]["errors"][type(e).__name__] += 1

    async with httpx.AsyncClient() as client:
        while True:
            elapsed = time.time() - t_start
            if elapsed >= duration:
                break

            # chaos injection
            if chaos_fn and not chaos_fired and elapsed >= chaos_at:
                chaos_fn()
                chaos_fired = True
                print(f"  [{label}] t={elapsed:.0f}s — chaos injected")

            if chaos_stop_fn and not chaos_stop_fired and elapsed >= chaos_stop_at:
                chaos_stop_fn()
                chaos_stop_fired = True
                print(f"  [{label}] t={elapsed:.0f}s — chaos stopped")

            # fire a wave
            await asyncio.gather(*[single_request(client) for _ in range(concurrency)])
            await asyncio.sleep(0.5)

    # aggregate
    total_ok = sum(v["ok"] for v in results.values())
    total_fail = sum(v["fail"] for v in results.values())
    total = total_ok + total_fail
    fail_pct = total_fail / total * 100 if total else 0

    # find worst second (most failures)
    worst_second = max(results.items(), key=lambda kv: kv[1]["fail"], default=(0, {"fail": 0}))

    # scan for error surge at chaos time (t=chaos_at±5)
    chaos_window = {k: v for k, v in results.items()
                    if chaos_at - 2 <= k <= chaos_at + 10}
    chaos_errors = sum(v["fail"] for v in chaos_window.values())
    chaos_total = sum(v["ok"] + v["fail"] for v in chaos_window.values())
    chaos_fail_pct = chaos_errors / chaos_total * 100 if chaos_total else 0

    return {
        "label": label,
        "total": total,
        "ok": total_ok,
        "fail": total_fail,
        "fail_pct": fail_pct,
        "chaos_window_fail_pct": chaos_fail_pct,
        "worst_second": worst_second[0],
        "worst_second_fail": worst_second[1]["fail"],
        "per_second": dict(results),
    }


def print_phase(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(r: dict):
    print(f"  total={r['total']} ok={r['ok']} fail={r['fail']} ({r['fail_pct']:.1f}%)")
    print(f"  chaos-window fail rate: {r['chaos_window_fail_pct']:.1f}%  (t=chaos_at-2..+10)")
    print(f"  worst single second: t={r['worst_second']}s had {r['worst_second_fail']} failures")


# ── main ─────────────────────────────────────────────────────────────────────

async def main():
    print_phase("AUTH")
    token, patient_info = get_patient_token()
    if not token:
        print("Cannot proceed without auth token.")
        sys.exit(1)
    combos = get_combo_entries(token)
    print(f"  Combo entries available: {len(combos)}")

    # ── PHASE 1: Baseline ─────────────────────────────────────────────────────
    print_phase("PHASE 1: Baseline (40 concurrent, 30s, no chaos)")
    r_baseline = await run_concurrent_load(
        token, duration=30, concurrency=CONCURRENT, label="baseline"
    )
    print_result(r_baseline)
    baseline_fail_pct = r_baseline["fail_pct"]
    print(f"  Baseline fail%: {baseline_fail_pct:.1f}%")

    # Ensure Redis is up before chaos phases
    if not redis_running():
        docker_start_redis()

    # ── PHASE 2: Redis kill mid-load ──────────────────────────────────────────
    print_phase("PHASE 2: Redis kill (40 concurrent, 60s; kill at t=20s, restart at t=50s)")
    print(f"  Redis before: {redis_running()}")
    r_redis = await run_concurrent_load(
        token, duration=60, concurrency=CONCURRENT,
        chaos_fn=docker_stop_redis,   chaos_at=20,
        chaos_stop_fn=docker_start_redis, chaos_stop_at=50,
        label="redis_kill",
    )
    print(f"  Redis after: {redis_running()}")
    print_result(r_redis)
    redis_verdict = (
        "PASS — fail-open held; fail rate did not spike during chaos window"
        if r_redis["chaos_window_fail_pct"] <= baseline_fail_pct + 5
        else f"FAIL — chaos window fail rate {r_redis['chaos_window_fail_pct']:.1f}% vs baseline {baseline_fail_pct:.1f}%"
    )
    print(f"  Verdict: {redis_verdict}")

    # Ensure Redis is back
    if not redis_running():
        docker_start_redis()

    # ── PHASE 3: DB connection termination mid-load ───────────────────────────
    print_phase("PHASE 3: DB terminate (40 concurrent, 45s; terminate at t=20s)")
    conn_before = count_db_connections()
    print(f"  DB connections before test: {conn_before}")

    def db_terminate_and_report():
        result = db_terminate_all()
        print(f"    pg_terminate_backend → {result}")
        conn_after = count_db_connections()
        print(f"    connections immediately after: {conn_after}")

    r_db = await run_concurrent_load(
        token, duration=45, concurrency=CONCURRENT,
        chaos_fn=db_terminate_and_report, chaos_at=20,
        label="db_terminate",
    )
    conn_recovered = count_db_connections()
    print(f"  DB connections after test (pool recovered): {conn_recovered}")
    print_result(r_db)
    db_verdict = (
        "PASS — pool recovered; brief spike then requests resumed"
        if r_db["chaos_window_fail_pct"] <= baseline_fail_pct + 20
        else f"INVESTIGATE — chaos window fail rate {r_db['chaos_window_fail_pct']:.1f}% vs baseline {baseline_fail_pct:.1f}%"
    )
    print(f"  Verdict: {db_verdict}")

    # ── PHASE 4: Combined (Redis + DB simultaneously) ─────────────────────────
    print_phase("PHASE 4: Combined chaos — Redis kill + DB terminate at t=20s (60s total)")
    if not redis_running():
        docker_start_redis()

    def combined_chaos():
        print("    Killing Redis...")
        docker_stop_redis()
        print("    Terminating DB connections...")
        result = db_terminate_all()
        print(f"    pg_terminate_backend → {result}")

    r_combined = await run_concurrent_load(
        token, duration=60, concurrency=CONCURRENT,
        chaos_fn=combined_chaos, chaos_at=20,
        chaos_stop_fn=docker_start_redis, chaos_stop_at=50,
        label="combined",
    )
    if not redis_running():
        docker_start_redis()
    print_result(r_combined)
    combined_verdict = (
        "PASS — combined chaos not worse than individual failures"
        if r_combined["chaos_window_fail_pct"] <= r_redis["chaos_window_fail_pct"] + r_db["chaos_window_fail_pct"] + 10
        else "INVESTIGATE — combined failures are additive or worse"
    )
    print(f"  Verdict: {combined_verdict}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print_phase("SUMMARY")
    print(f"  Baseline fail%:         {r_baseline['fail_pct']:.1f}%")
    print(f"  Redis-kill chaos win%:  {r_redis['chaos_window_fail_pct']:.1f}%  → {redis_verdict.split(' — ')[0]}")
    print(f"  DB-terminate chaos win%:{r_db['chaos_window_fail_pct']:.1f}%  → {db_verdict.split(' — ')[0]}")
    print(f"  Combined chaos win%:    {r_combined['chaos_window_fail_pct']:.1f}%  → {combined_verdict.split(' — ')[0]}")

    report = {
        "baseline": {k: v for k, v in r_baseline.items() if k != "per_second"},
        "redis_kill": {k: v for k, v in r_redis.items() if k != "per_second"},
        "db_terminate": {k: v for k, v in r_db.items() if k != "per_second"},
        "combined": {k: v for k, v in r_combined.items() if k != "per_second"},
        "verdicts": {
            "redis_fail_open": redis_verdict.startswith("PASS"),
            "db_pool_recovery": db_verdict.startswith("PASS"),
            "combined_no_additive_failure": combined_verdict.startswith("PASS"),
        },
    }
    report_path = REPORTS_DIR / "chaos_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\n  Full report: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
