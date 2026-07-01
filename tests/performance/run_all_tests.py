"""
Master test runner — executes all performance + quality modules in order.

Usage:
    python -m tests.performance.run_all_tests [--skip-seed] [--skip-locust] [--generate-plans]

Options:
    --skip-seed       Skip Module 1 (patient seeding — use if already seeded)
    --skip-locust     Skip Module 3 (Locust — requires manual launch for UI mode)
    --generate-plans  Pass --generate-first to Module 4 (re-generate plans before quality check)

Run order:
    1. seed_test_patients.py          → writes test_manifest.json
    2. benchmark_api.py               → writes reports/benchmark_baseline.json
    3. locustfile.py (headless ramp)  → writes reports/ramp_test.html
    4. test_plan_quality.py           → writes reports/quality_report.json
    5. E2E (Playwright)               → cd e2e && npx playwright test
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PERF_DIR = Path(__file__).parent
REPORTS_DIR = PERF_DIR / "reports"
PYTHON = sys.executable


def _run(cmd: list[str], label: str, timeout: int = 300) -> dict:
    print(f"\n{'='*60}")
    print(f"[{label}] Running: {' '.join(cmd)}")
    print("=" * 60)
    t0 = time.perf_counter()
    result = subprocess.run(cmd, timeout=timeout)
    elapsed = time.perf_counter() - t0
    status = "PASS" if result.returncode == 0 else "FAIL"
    print(f"\n[{label}] {status} in {elapsed:.1f}s")
    return {"label": label, "status": status, "elapsed_s": round(elapsed, 1), "returncode": result.returncode}


def _locust_headless_ramp() -> dict:
    cmd = [
        PYTHON, "-m", "locust",
        "-f", str(PERF_DIR / "locustfile.py"),
        "--host", "http://127.0.0.1:8001",
        "--users", "50",
        "--spawn-rate", "5",
        "--run-time", "3m",
        "--headless",
        "--html", str(REPORTS_DIR / "ramp_test.html"),
        "--csv", str(REPORTS_DIR / "ramp_test"),
    ]
    return _run(cmd, "Locust Ramp Test", timeout=240)


def main():
    parser = argparse.ArgumentParser(description="Mityahar performance test master runner")
    parser.add_argument("--skip-seed", action="store_true")
    parser.add_argument("--skip-locust", action="store_true")
    parser.add_argument("--generate-plans", action="store_true")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Mityahar Performance Suite — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    run_log = []

    # Module 1 — Seed
    if not args.skip_seed:
        r = _run([PYTHON, "-m", "tests.performance.seed_test_patients"], "Module 1: Seed")
        run_log.append(r)
    else:
        print("\n[Module 1: Seed] SKIPPED")
        run_log.append({"label": "Module 1: Seed", "status": "SKIPPED"})

    # Module 2 — Benchmark
    r = _run([PYTHON, "-m", "tests.performance.benchmark_api"], "Module 2: Benchmark", timeout=180)
    run_log.append(r)

    # Module 3 — Locust
    if not args.skip_locust:
        r = _locust_headless_ramp()
        run_log.append(r)
    else:
        print("\n[Module 3: Locust] SKIPPED — run manually:")
        print("  locust -f tests/performance/locustfile.py --host http://localhost:8001")
        run_log.append({"label": "Module 3: Locust", "status": "SKIPPED"})

    # Module 4 — Quality
    quality_cmd = [PYTHON, "-m", "tests.performance.test_plan_quality"]
    if args.generate_plans:
        quality_cmd.append("--generate-first")
    r = _run(quality_cmd, "Module 4: Quality", timeout=600)
    run_log.append(r)

    # Module 5 — Playwright E2E
    e2e_dir = PERF_DIR / "e2e"
    if e2e_dir.exists() and (e2e_dir / "playwright.config.ts").exists():
        r = _run(
            ["npx", "playwright", "test", "--reporter=list"],
            "Module 5: Playwright E2E",
            timeout=120,
        )
        run_log.append(r)
    else:
        print("\n[Module 5: Playwright E2E] SKIPPED — e2e/ not configured")
        run_log.append({"label": "Module 5: Playwright E2E", "status": "SKIPPED"})

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("=" * 60)
    for entry in run_log:
        status = entry.get("status", "?")
        elapsed = f"  ({entry['elapsed_s']}s)" if "elapsed_s" in entry else ""
        print(f"  {entry['label']:<30} {status}{elapsed}")

    passed = sum(1 for e in run_log if e.get("status") == "PASS")
    skipped = sum(1 for e in run_log if e.get("status") == "SKIPPED")
    failed = sum(1 for e in run_log if e.get("status") == "FAIL")
    print(f"\n  PASS={passed}  FAIL={failed}  SKIP={skipped}")

    # Load quality report for top-level number
    quality_path = REPORTS_DIR / "quality_report.json"
    if quality_path.exists():
        qr = json.loads(quality_path.read_text())
        print(f"\n  Plan quality: {qr['passed']}/{qr['total']} patients PASS")

    report_path = REPORTS_DIR / "master_report.json"
    report_path.write_text(json.dumps({
        "run_at": datetime.now().isoformat(),
        "modules": run_log,
    }, indent=2))
    print(f"\nFull report: {report_path}")
    print("Locust report: tests/performance/reports/ramp_test.html")
    print("Playwright report: tests/performance/reports/playwright-report/index.html")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
