"""
1000-user asymmetric load test: 10 doctors + 990 patients.

Key differences from locustfile.py:
  - DoctorUser.weight=1, PatientUser.weight=99 → ~1% doctors, 99% patients
  - Every user injects a unique X-Forwarded-For header (per-user IP from 10.0.x.y)
    so the rate limiter sees distinct client IPs (requires TRUSTED_PROXY_CIDR=127.0.0.1)
  - Spawn rate 20/s → 50s ramp to 1000 users (realistic, not instant burst)
  - Designed for --run-time 5m sustained test

Setup (run once before this test):
    Set TRUSTED_PROXY_CIDR=127.0.0.1 in .env so localhost is a trusted proxy →
    X-Forwarded-For headers are honoured for rate-limit keying.

Run:
    locust -f tests/performance/locustfile_1000users.py \\
      --host http://localhost:8001 \\
      --users 1000 --spawn-rate 20 --run-time 5m --headless \\
      --csv tests/performance/reports/load_1000users

Staging target (point --host at the Cloud Run service URL; note X-Forwarded-For
spoofing only works where TRUSTED_PROXY_CIDR trusts the caller — behind GCLB the
real client IP wins, so per-user IP injection is a local-only mechanism):
    locust -f tests/performance/locustfile_1000users.py \\
      --host https://<staging-service-url> \\
      --users 1000 --spawn-rate 20 --run-time 5m --headless \\
      --csv tests/performance/reports/load_1000users_staging

Items tested:
    1 — Multi-IP auth latency at scale (p50/p95/p99 for auth endpoints)
    4 — Asymmetric doctor reads + patient writes concurrently for 5 minutes
"""

import json
import random
import threading
from pathlib import Path

from locust import HttpUser, between, task

MANIFEST_PATH = Path(__file__).parent / "test_manifest.json"

_manifest_data = None
_manifest_lock = threading.Lock()

# Global atomic counter for unique per-user IP assignment
_user_counter = 0
_counter_lock = threading.Lock()


def _load_manifest():
    global _manifest_data
    with _manifest_lock:
        if _manifest_data is None:
            if MANIFEST_PATH.exists():
                _manifest_data = json.loads(MANIFEST_PATH.read_text())
            else:
                _manifest_data = {"patients": [], "doctors": []}
    return _manifest_data


def _next_user_id() -> int:
    global _user_counter
    with _counter_lock:
        _user_counter += 1
        return _user_counter


def _user_id_to_xff(uid: int) -> str:
    """Map integer user ID → unique 10.x.x.x IP string."""
    # 10.0.0.1 → 10.3.255.255 supports 262143 unique IPs
    b3 = (uid >> 8) & 0xFF
    b4 = uid & 0xFF
    b2 = (uid >> 16) & 0x03
    return f"10.{b2}.{b3}.{b4}"


class PatientUser(HttpUser):
    """990 patients hitting read + write endpoints."""

    wait_time = between(1, 3)
    weight = 99  # 99% of 1000 users = ~990 patients

    def on_start(self):
        self._uid = _next_user_id()
        self._xff = _user_id_to_xff(self._uid)
        self._xff_headers = {"X-Forwarded-For": self._xff}

        manifest = _load_manifest()
        patients = manifest.get("patients", [])
        if patients:
            p = random.choice(patients)
            email = p["email"]
            password = manifest.get("patient_password", "TestPat@2026")
            self._patient_id = p["patient_id"]
        else:
            email = "testpatient001@mityahar.test"
            password = "TestPat@2026"
            self._patient_id = 1

        self._token = ""
        r = self.client.post(
            "/api/v1/auth/token",
            data={"username": email, "password": password},
            headers=self._xff_headers,
            name="POST /auth/token [patient]",
        )
        self._combo_entries = []  # [{combo_id, food_item_ids, meal_type, date}]
        if r.status_code == 200:
            self._token = r.json().get("access_token", "")
            r2 = self.client.get(
                "/api/v1/meal-plan/week",
                headers=self._auth(),
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

    def _auth(self):
        headers = dict(self._xff_headers)
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    @task(4)
    def view_meal_plan(self):
        self.client.get(
            "/api/v1/meal-plan/week",
            headers=self._auth(),
            name="GET /meal-plan/week",
        )

    @task(2)
    def view_progress(self):
        self.client.get(
            "/api/v1/progress/today",
            headers=self._auth(),
            name="GET /progress/today",
        )

    @task(1)
    def view_profile(self):
        self.client.get(
            "/api/v1/users/me",
            headers=self._auth(),
            name="GET /users/me",
        )

    @task(2)
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
    """10 doctors hitting read-heavy dashboard + summary endpoints."""

    wait_time = between(3, 8)
    weight = 1  # 1% of 1000 users = ~10 doctors

    def on_start(self):
        self._uid = _next_user_id()
        self._xff = _user_id_to_xff(self._uid)
        self._xff_headers = {"X-Forwarded-For": self._xff}

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
            headers=self._xff_headers,
            name="POST /auth/doctor/login [doctor]",
        )
        if r.status_code == 200:
            self._token = r.json().get("access_token", "")

        patients = manifest.get("patients", [])
        self._patient_id = patients[0]["patient_id"] if patients else 2

    def _auth(self):
        headers = dict(self._xff_headers)
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    @task(4)
    def view_patient_list(self):
        self.client.get(
            "/api/v1/doctor/patients",
            headers=self._auth(),
            name="GET /doctor/patients",
        )

    @task(3)
    def view_dashboard(self):
        self.client.get(
            "/api/v1/doctor/dashboard",
            headers=self._auth(),
            name="GET /doctor/dashboard",
        )

    @task(3)
    def view_weekly_summary(self):
        self.client.get(
            f"/api/v1/doctor/patients/{self._patient_id}/weekly-summary",
            headers=self._auth(),
            name="GET /doctor/patients/{id}/weekly-summary",
        )

    @task(2)
    def view_weekly_plan(self):
        self.client.get(
            f"/api/v1/doctor/patients/{self._patient_id}/weekly-plan",
            headers=self._auth(),
            name="GET /doctor/patients/{id}/weekly-plan",
        )

    @task(1)
    def approve_plan(self):
        self.client.post(
            f"/api/v1/doctor/patients/{self._patient_id}/weekly-plan/approve",
            json={},
            headers=self._auth(),
            name="POST /doctor/.../weekly-plan/approve",
        )
