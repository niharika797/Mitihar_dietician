"""
Locust load test — 50 concurrent patients + 6 doctors.

Install:
    pip install locust

Run (UI at http://localhost:8089):
    locust -f tests/performance/locustfile.py --host http://localhost:8001

Headless ramp test:
    locust -f tests/performance/locustfile.py --host http://localhost:8001 \
      --users 50 --spawn-rate 5 --run-time 5m --headless \
      --html tests/performance/reports/ramp_test.html

Spike test:
    locust -f tests/performance/locustfile.py --host http://localhost:8001 \
      --users 50 --spawn-rate 50 --run-time 2m --headless \
      --html tests/performance/reports/spike_test.html

Scenario notes:
    Scenario A — Ramp: use --spawn-rate 5 --users 50
    Scenario B — Spike: use --spawn-rate 50 --users 50
    Scenario C — time-of-day: run at 08:00, 12:00, 20:00 IST; record timestamp in report filename

Metrics to compare with friend's AWS run:
    - RPS at 50 users (local laptop vs AWS t3.medium)
    - p95 latency gap (plan generation is the outlier to watch)
    - Failure rate (0% target for read endpoints, <1% for generation)

RATE LIMIT NOTE — X-Forwarded-For is NOT honored locally:
    slowapi is configured with key_func=get_remote_address (app/core/limiter.py),
    which reads request.client.host (raw TCP socket IP), NOT X-Forwarded-For.
    All 50 Locust workers from a local machine share the same 127.0.0.1 rate limit
    bucket. This means local load tests cannot verify per-IP rate limit isolation.
    Per-IP behavior can only be confirmed post-GCP-deployment, where the load
    balancer exposes real distinct client IPs via request.client.host.
    See: tests/performance/test_rate_limit.py for a direct rate limit verification test.
"""

import json
import random
from pathlib import Path

from locust import HttpUser, between, task

MANIFEST_PATH = Path(__file__).parent / "test_manifest.json"

_manifest_data = None


def _load_manifest():
    global _manifest_data
    if _manifest_data is None:
        if MANIFEST_PATH.exists():
            _manifest_data = json.loads(MANIFEST_PATH.read_text())
        else:
            _manifest_data = {"patients": [], "doctors": []}
    return _manifest_data


class PatientUser(HttpUser):
    """Simulates a patient using the mobile app."""

    wait_time = between(1, 4)

    def on_start(self):
        manifest = _load_manifest()
        patients = manifest.get("patients", [])
        if not patients:
            # Fallback to known test patient if manifest missing
            email = "testpatient001@mityahar.test"
            password = "TestPat@2026"
        else:
            p = random.choice(patients)
            email = p["email"]
            password = manifest.get("patient_password", "TestPat@2026")
            self._patient_id = p["patient_id"]

        self._token = ""
        self._combo_entries = []  # [{combo_id, food_item_ids, meal_type, date}]
        r = self.client.post(
            "/api/v1/auth/token",
            data={"username": email, "password": password},
            name="POST /auth/token",
        )
        if r.status_code == 200:
            self._token = r.json().get("access_token", "")
            r2 = self.client.get(
                "/api/v1/meal-plan/week",
                headers={"Authorization": f"Bearer {self._token}"},
                name="GET /meal-plan/week [setup]",
            )
            if r2.status_code == 200:
                for day in r2.json().get("days", []):
                    date_str = day.get("date", "")
                    for meal_type, meal_data in day.get("meals", {}).items():
                        for combo in meal_data.get("combos", []):
                            cid = combo.get("combo_id")
                            fids = [
                                d["food_item_id"]
                                for d in combo.get("dishes", [])
                                if d.get("food_item_id")
                            ]
                            if cid and fids and date_str:
                                self._combo_entries.append({
                                    "combo_id": cid,
                                    "food_item_ids": fids,
                                    "meal_type": meal_type,
                                    "date": date_str,
                                })
        else:
            # Auth failed — mark all requests as failed so Locust tracks it
            self._token = ""

    def _auth(self):
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    @task(3)
    def view_meal_plan(self):
        self.client.get("/api/v1/meal-plan/week", headers=self._auth(), name="GET /meal-plan/week")

    @task(2)
    def view_progress_today(self):
        self.client.get("/api/v1/progress/today", headers=self._auth(), name="GET /progress/today")

    @task(1)
    def view_profile(self):
        self.client.get("/api/v1/users/me", headers=self._auth(), name="GET /users/me")

    @task(1)
    def confirm_combo(self):
        if not self._combo_entries:
            return
        entry = random.choice(self._combo_entries)
        self.client.post(
            "/api/v1/meal-plan/confirm-choice",
            json={
                "date": entry["date"],
                "meal_type": entry["meal_type"],
                "weekly_combo_id": entry["combo_id"],
                "food_item_ids": entry["food_item_ids"],
                "bowl_size": random.choice(["small", "medium", "large"]),
            },
            headers=self._auth(),
            name="POST /meal-plan/confirm-choice",
        )


class DoctorUser(HttpUser):
    """Simulates a doctor using the web dashboard."""

    wait_time = between(2, 6)

    # Fewer doctors in pool — they do heavier read operations
    weight = 1

    def on_start(self):
        manifest = _load_manifest()
        doctors = manifest.get("doctors", [])
        if doctors:
            d = random.choice(doctors)
            email = d["email"]
            password = d.get("password", "DoctorTest@2026")
        else:
            email = "dr.ashok.mehta@mityahar-perf.com"
            password = "DoctorTest@2026"

        self._token = ""
        r = self.client.post(
            "/api/v1/auth/doctor/login",
            data={"username": email, "password": password},
            name="POST /auth/doctor/login",
        )
        if r.status_code == 200:
            self._token = r.json().get("access_token", "")

        # Pick a test patient to operate on
        patients = manifest.get("patients", [])
        self._patient_id = patients[0]["patient_id"] if patients else 2

    def _auth(self):
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    @task(3)
    def view_patient_list(self):
        self.client.get("/api/v1/doctor/patients", headers=self._auth(), name="GET /doctor/patients")

    @task(2)
    def view_patient_plan(self):
        self.client.get(
            f"/api/v1/doctor/patients/{self._patient_id}/weekly-plan",
            headers=self._auth(),
            name="GET /doctor/patients/{id}/weekly-plan",
        )

    @task(2)
    def view_weekly_summary(self):
        self.client.get(
            f"/api/v1/doctor/patients/{self._patient_id}/weekly-summary",
            headers=self._auth(),
            name="GET /doctor/patients/{id}/weekly-summary",
        )

    @task(2)
    def view_dashboard(self):
        self.client.get("/api/v1/doctor/dashboard", headers=self._auth(), name="GET /doctor/dashboard")

    @task(1)
    def approve_plan(self):
        self.client.post(
            f"/api/v1/doctor/patients/{self._patient_id}/weekly-plan/approve",
            json={},
            headers=self._auth(),
            name="POST /doctor/patients/{id}/weekly-plan/approve",
        )

    @task(1)
    def browse_recipes(self):
        self.client.get(
            "/api/v1/doctor/recipes?limit=20",
            headers=self._auth(),
            name="GET /doctor/recipes",
        )
