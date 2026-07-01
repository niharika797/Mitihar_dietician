"""
API Response Time Baseline — single-user sequential benchmark.
Measures p50/p95/p99 for each endpoint with 10 requests each.

Run:
    python -m tests.performance.benchmark_api

Output:
    Printed table + tests/performance/reports/benchmark_baseline.json

Note: Run BEFORE and AFTER a Locust load test to see if generation time degrades
under concurrent load — mirrors the "model performance vs load" comparison angle.

Note on "Generate plan" endpoint:
    The spec referenced POST /doctor/patients/{id}/weekly-plan/generate which does
    not exist. This benchmark uses POST /api/v1/diet-plans/generate (patient-scoped)
    as the plan generation timing proxy. This endpoint deletes the existing plan
    and regenerates — run against a TEST patient only (testpatient001@mityahar.test).
"""

import json
import statistics
import sys
import time
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8001"
REPORTS_DIR = Path(__file__).parent / "reports"

DOCTOR_EMAIL = "dr.ashok.mehta@mitihar.test"
DOCTOR_PASSWORD = "DoctorTest@2026"
PATIENT_EMAIL = "testpatient001@mityahar.test"
PATIENT_PASSWORD = "TestPat@2026"

REQUESTS_PER_ENDPOINT = 10
AUTH, DOCTOR, PATIENT = "auth", "doctor", "patient"


def _login_doctor() -> str:
    r = requests.post(
        f"{BASE_URL}/api/v1/auth/doctor/login",
        data={"username": DOCTOR_EMAIL, "password": DOCTOR_PASSWORD},
        timeout=30,
    )
    if r.status_code != 200:
        print(f"  [WARN] Doctor login failed: {r.status_code} {r.text[:120]}")
        return ""
    return r.json().get("access_token", "")


def _login_patient() -> str:
    r = requests.post(
        f"{BASE_URL}/api/v1/auth/token",
        data={"username": PATIENT_EMAIL, "password": PATIENT_PASSWORD},
        timeout=30,
    )
    if r.status_code != 200:
        print(f"  [WARN] Patient login failed: {r.status_code} {r.text[:120]}")
        return ""
    return r.json().get("access_token", "")


def _percentile(sorted_data: list, pct: float) -> float:
    if not sorted_data:
        return 0.0
    idx = min(int(len(sorted_data) * pct), len(sorted_data) - 1)
    return sorted_data[idx]


def _benchmark_endpoint(method: str, path: str, headers: dict, body=None) -> dict:
    url = f"{BASE_URL}{path}"
    times_ms = []
    success = 0
    last_status = 0
    total_bytes = 0

    for _ in range(REQUESTS_PER_ENDPOINT):
        t0 = time.perf_counter()
        try:
            if method == "POST":
                r = requests.post(url, headers=headers, json=body, timeout=60)
            else:
                r = requests.get(url, headers=headers, timeout=60)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            last_status = r.status_code
            if r.status_code < 400:
                success += 1
                total_bytes += len(r.content)
            times_ms.append(elapsed_ms)
        except Exception as e:
            times_ms.append(60_000)  # timeout sentinel
            print(f"    [ERR] {path}: {e}")

    times_ms.sort()
    return {
        "p50_ms": round(_percentile(times_ms, 0.50), 1),
        "p95_ms": round(_percentile(times_ms, 0.95), 1),
        "p99_ms": round(_percentile(times_ms, 0.99), 1),
        "success": f"{success}/{REQUESTS_PER_ENDPOINT}",
        "avg_bytes": total_bytes // max(success, 1),
        "last_status": last_status,
    }


def run() -> dict:
    print("=== Mityahar API Benchmark (single user) ===\n")

    print("Authenticating...")
    doctor_token = _login_doctor()
    patient_token = _login_patient()

    doctor_h = {"Authorization": f"Bearer {doctor_token}"} if doctor_token else {}
    patient_h = {"Authorization": f"Bearer {patient_token}"} if patient_token else {}

    # Find a real patient_id from manifest if available
    manifest_path = Path(__file__).parent / "test_manifest.json"
    patient_id = 2  # fallback (Priya)
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("patients"):
            patient_id = manifest["patients"][0]["patient_id"]

    ENDPOINTS = [
        # (method, path, label, auth_type, body)
        ("POST", "/api/v1/auth/doctor/login",                            "Doctor login",       AUTH,    None),
        ("GET",  "/api/v1/doctor/dashboard",                             "Doctor dashboard",   DOCTOR,  None),
        ("GET",  "/api/v1/doctor/patients",                              "Patient list",       DOCTOR,  None),
        ("GET",  f"/api/v1/doctor/patients/{patient_id}/weekly-plan",   "Weekly plan",        DOCTOR,  None),
        ("GET",  f"/api/v1/doctor/patients/{patient_id}/weekly-summary","Weekly summary",     DOCTOR,  None),
        ("POST", f"/api/v1/doctor/patients/{patient_id}/weekly-plan/approve",
                                                                         "Approve plan",       DOCTOR,  {}),
        ("GET",  "/api/v1/meal-plan/week",                               "Patient meal week",  PATIENT, None),
        ("GET",  "/api/v1/progress/today",                               "Progress today",     PATIENT, None),
        ("GET",  "/api/v1/doctor/recipes",                               "Recipe library",     DOCTOR,  None),
        # Plan generation is deliberately last — it's destructive (deletes + rebuilds plan).
        # Comment this line out if testpatient001 has a plan you want to preserve.
        ("POST", "/api/v1/diet-plans/generate",                          "Generate plan",      PATIENT, None),
    ]

    print(f"Running {REQUESTS_PER_ENDPOINT} requests per endpoint ({len(ENDPOINTS)} endpoints)...\n")

    results = []
    for method, path, label, auth_type, body in ENDPOINTS:
        if auth_type == AUTH:
            h = {}
            b = {"username": DOCTOR_EMAIL, "password": DOCTOR_PASSWORD}
            sys.stdout.write(f"  {label:<22} ... ")
            sys.stdout.flush()
            # Login benchmark uses form data
            url = f"{BASE_URL}{path}"
            times_ms = []
            success = 0
            for _ in range(REQUESTS_PER_ENDPOINT):
                t0 = time.perf_counter()
                try:
                    r = requests.post(url, data=b, timeout=30)
                    times_ms.append((time.perf_counter() - t0) * 1000)
                    if r.status_code < 400:
                        success += 1
                except Exception:
                    times_ms.append(30_000)
            times_ms.sort()
            stats = {
                "p50_ms": round(_percentile(times_ms, 0.50), 1),
                "p95_ms": round(_percentile(times_ms, 0.95), 1),
                "p99_ms": round(_percentile(times_ms, 0.99), 1),
                "success": f"{success}/{REQUESTS_PER_ENDPOINT}",
                "avg_bytes": 0,
                "last_status": 200 if success > 0 else 0,
            }
        else:
            h = doctor_h if auth_type == DOCTOR else patient_h
            sys.stdout.write(f"  {label:<22} ... ")
            sys.stdout.flush()
            stats = _benchmark_endpoint(method, path, h, body)

        print(f"p50={stats['p50_ms']:>7.1f}ms  p95={stats['p95_ms']:>7.1f}ms  p99={stats['p99_ms']:>7.1f}ms  {stats['success']}")
        results.append({"label": label, "method": method, "path": path, **stats})

    # Summary table
    print("\n" + "=" * 75)
    print(f"{'Endpoint':<24} {'p50':>8} {'p95':>8} {'p99':>8} {'Success':>8}")
    print("-" * 75)
    for r in results:
        print(f"{r['label']:<24} {r['p50_ms']:>7.0f}ms {r['p95_ms']:>7.0f}ms {r['p99_ms']:>7.0f}ms {r['success']:>8}")

    fastest = min(results, key=lambda x: x["p50_ms"])
    slowest = max(results, key=lambda x: x["p50_ms"])
    print(f"\nFastest: {fastest['label']} → {fastest['p50_ms']}ms p50")
    print(f"Slowest: {slowest['label']} → {slowest['p50_ms']}ms p50")

    # Save JSON
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS_DIR / "benchmark_baseline.json"
    out_path.write_text(json.dumps({"endpoints": results}, indent=2))
    print(f"\nSaved: {out_path}")
    return {"endpoints": results}


if __name__ == "__main__":
    run()
