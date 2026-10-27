"""
Locust scenarios for the capacity rig. Runs INSIDE the load container on the rig network (no Docker Desktop port-forward hop).
Pick classes on the command line, e.g.  locust -f locustfile_perf.py SteadyMix
Env: GENERATE_ON_MEALS=1 (as-built: Meals-tab mount calls POST /diet-plans/generate) | 0 (proposed fix: no auto-generate)
Every class carries the label of what it models. Request-mix weights come from MEASURED journeys; session pacing is ASSUMED.
"""
import datetime as dt
import itertools
import json
import os
import random
import time

from locust import HttpUser, LoadTestShape, between, constant_throughput, task
from locust.exception import StopUser

TOK = json.load(open("/out/tokens.json"))
ASBUILT = os.environ.get("GENERATE_ON_MEALS", "1") == "1"
TODAY = dt.date.today().isoformat()
SPREAD = float(os.environ.get("SPREAD_S", "300"))
THINK = float(os.environ.get("THINK_S", "8"))
PID_BASE = int(os.environ.get("PID_BASE", "11"))       # skip the 10 first template patients
_ctr = itertools.count()
_dctr = itertools.count()


def env_int(k, d):
    return int(os.environ.get(k, d))


class PatientBase(HttpUser):
    abstract = True
    host = os.environ.get("TARGET", "http://mitihar-perf-api:8001")

    def on_start(self):
        self.pid = PID_BASE + next(_ctr) % (1000 - PID_BASE + 1)
        self.h = {"Authorization": "Bearer " + TOK["patients"][str(self.pid)], "X-Forwarded-For": f"10.{self.pid >> 8}.{self.pid & 255}.7"}
        self.combo = None

    # ── request primitives (names = route templates, so stats group like the server does) ──
    def g(self, path, name=None, **kw):
        return self.client.get("/api/v1" + path, headers=self.h, name=name or ("GET " + path), **kw)

    def j(self, method, path, body, name=None):
        return self.client.request(method, "/api/v1" + path, json=body, headers=self.h, name=name or (method + " " + path))

    def cold_open(self):
        self.g("/users/me")
        self.g("/progress/today")
        self.g("/patients/my-visit")
        self.g(f"/meal-plan/choices/{TODAY}", name="GET /meal-plan/choices/{date}")
        self.g("/progress/streak")
        r = self.g("/meal-plan/week")
        try:
            c = r.json()["days"][0]["meals"]["Breakfast"]["combos"][0]
            self.combo = (c["combo_id"], [d.get("food_item_id") or d.get("food_id") for d in c["dishes"]])
        except Exception:
            self.combo = None
        self.g("/patients/pending-visits")
        self.g("/meal-plan/shopping-list")
        self.j("POST", "/auth/register-fcm-token", {"fcm_token": f"perf-{self.pid}"})      # native only (DERIVED)

    def meals_tab(self):
        if ASBUILT:
            self.j("POST", "/diet-plans/generate", None)
        if self.combo:
            self.j("POST", "/meal-plan/confirm-choice", {"food_item_ids": self.combo[1], "date": TODAY, "meal_type": "Breakfast", "weekly_combo_id": self.combo[0]})
            self.g(f"/meal-plan/choices/{TODAY}", name="GET /meal-plan/choices/{date}")
            self.g("/meal-plan/week")

    def log_meal(self):
        self.j("POST", "/progress/log/meal", {"meal_type": "Lunch", "calories": 500, "protein": 20, "carbs": 60, "fat": 15,
                                              "food_id": self.combo[1][0] if self.combo else None})
        self.g("/progress/today")

    def warm(self):
        self.g("/progress/today")
        self.g(f"/meal-plan/choices/{TODAY}", name="GET /meal-plan/choices/{date}")


# ── 1. steady total rate (MEASURED request mix; users x TPUT = target rps) ──
MIX = [("users/me", 3), ("today", 6), ("my-visit", 3), ("choices", 4), ("streak", 3), ("week", 4), ("pending", 3), ("shopping", 3),
       ("confirm", 1.5), ("logmeal", 2.5), ("fcm", 3)] + ([("generate", 1.5)] if ASBUILT else [])


class SteadyMix(PatientBase):
    """Constant aggregate rate: N users x TPUT req/s each. Stateless single-request draws from the measured per-session mix."""
    wait_time = constant_throughput(float(os.environ.get("TPUT", "0.2")))

    @task
    def one(self):
        k = random.choices([m[0] for m in MIX], [m[1] for m in MIX])[0]
        if self.combo is None:
            self.cold_open()
            return
        {"users/me": lambda: self.g("/users/me"), "today": lambda: self.g("/progress/today"),
         "my-visit": lambda: self.g("/patients/my-visit"), "choices": lambda: self.g(f"/meal-plan/choices/{TODAY}", name="GET /meal-plan/choices/{date}"),
         "streak": lambda: self.g("/progress/streak"), "week": lambda: self.g("/meal-plan/week"),
         "pending": lambda: self.g("/patients/pending-visits"), "shopping": lambda: self.g("/meal-plan/shopping-list"),
         "confirm": lambda: self.j("POST", "/meal-plan/confirm-choice", {"food_item_ids": self.combo[1], "date": TODAY, "meal_type": "Breakfast", "weekly_combo_id": self.combo[0]}),
         "logmeal": lambda: self.j("POST", "/progress/log/meal", {"meal_type": "Lunch", "calories": 500, "food_id": self.combo[1][0]}),
         "fcm": lambda: self.j("POST", "/auth/register-fcm-token", {"fcm_token": f"perf-{self.pid}"}),
         "generate": lambda: self.j("POST", "/diet-plans/generate", None)}[k]()


# ── 3. meal-time spike: each patient starts a cold session at a random offset in SPREAD seconds ──
class Spike(PatientBase):
    """ORGANIC (SPREAD_S=300) or SYNCHRONIZED (SPREAD_S=30). Cold session, Meals tab (+generate if as-built), meal log, 2 warm returns (ASSUMED pacing)."""
    wait_time = between(1, 2)

    @task
    def session(self):
        time.sleep(random.uniform(0, SPREAD))
        self.cold_open(); time.sleep(random.uniform(1, 3))
        self.meals_tab(); time.sleep(random.uniform(1, 3))
        self.log_meal()
        for _ in range(2):
            time.sleep(random.uniform(20, 40)); self.warm()
        raise StopUser()


# ── 4. doctor weekly review ──
class DoctorReview(HttpUser):
    """Each doctor pages through 10 list pages then opens each of their 100 patients (detail, plan, weekly-plan, logs, weekly-summary)."""
    host = os.environ.get("TARGET", "http://mitihar-perf-api:8001")
    wait_time = between(0.5, 1)

    @task
    def review(self):
        d = 1 + next(_dctr) % 10
        h = {"Authorization": "Bearer " + TOK["doctors"][str(d)], "X-Forwarded-For": f"10.200.0.{d}"}
        g = lambda p, n=None: self.client.get("/api/v1" + p, headers=h, name=n or ("GET " + p))
        g("/doctor/dashboard")
        for pg in range(1, 11):
            g(f"/doctor/patients?page={pg}&page_size=10", "GET /doctor/patients (page)")
        for k in range(100):
            pid = d + 10 * k
            for p, n in ((f"/doctor/patients/{pid}", "GET /doctor/patients/{id}"), (f"/doctor/patients/{pid}/plan", "GET /doctor/patients/{id}/plan"),
                         (f"/doctor/patients/{pid}/weekly-plan", "GET /doctor/patients/{id}/weekly-plan"),
                         (f"/doctor/patients/{pid}/logs?days=7", "GET /doctor/patients/{id}/logs"),
                         (f"/doctor/patients/{pid}/weekly-summary", "GET /doctor/patients/{id}/weekly-summary")):
                g(p, n)
            time.sleep(THINK)
        raise StopUser()


# ── 5. plan regeneration under browsing ──
class WeightLogger(PatientBase):
    """Weight log (server field name `weight`; the shipped client's `weight_kg` is rejected with 422) -> background plan regeneration."""
    wait_time = constant_throughput(float(os.environ.get("WL_TPUT", "0.0167")))
    fixed_count = env_int("WL_USERS", 0) or None

    @task
    def log_weight(self):
        self.j("PUT", "/progress/log/weight", {"weight": round(70 + random.random() * 10, 1)})


class Browser(SteadyMix):
    """Steady browsing users (read-mostly mix) while WeightLogger runs."""
    fixed_count = env_int("BR_USERS", 0) or None


class SessionLoop(PatientBase):
    """Normal sessions in a loop (cold open, Meals tab, meal log), pacing ASSUMED: one session per PACE_S on average."""
    wait_time = between(0.5, 1)
    fixed_count = env_int("SL_USERS", 0) or None

    @task
    def loop(self):
        time.sleep(random.uniform(0, float(os.environ.get("PACE_S", "120"))))
        self.cold_open(); time.sleep(1); self.meals_tab(); time.sleep(1); self.log_meal()


class WeightOnce(PatientBase):
    """Exactly one weight log per user at a random offset in SPREAD_S (spec: 100 weight logs in 60 s)."""
    wait_time = between(1, 2)
    fixed_count = env_int("WO_USERS", 0) or None

    @task
    def once(self):
        time.sleep(random.uniform(0, SPREAD))
        self.j("PUT", "/progress/log/weight", {"weight": round(70 + random.random() * 10, 1)})
        raise StopUser()


# ── 6. login storm ──
class LoginStorm(HttpUser):
    """N logins spread over SPREAD_S (bcrypt ~205 ms CPU each), each followed by the cold-open call set."""
    host = os.environ.get("TARGET", "http://mitihar-perf-api:8001")
    wait_time = between(1, 2)

    @task
    def login(self):
        pid = 1 + next(_ctr) % 1000
        time.sleep(random.uniform(0, SPREAD))
        xff = {"X-Forwarded-For": f"10.{pid >> 8}.{pid & 255}.9"}
        r = self.client.post("/api/v1/auth/token", data={"username": f"perfpat{pid:04d}@mityahar-perf.test", "password": "PerfTest@2026"},
                             headers=xff, name="POST /auth/token (login)")
        if r.status_code != 200:
            raise StopUser()
        h = {"Authorization": "Bearer " + r.json()["access_token"], **xff}
        for p in ("/users/me", "/progress/today", "/patients/my-visit", f"/meal-plan/choices/{TODAY}", "/progress/streak",
                  "/meal-plan/week", "/patients/pending-visits", "/meal-plan/shopping-list"):
            self.client.get("/api/v1" + p, headers=h, name="GET " + p.replace(TODAY, "{date}"))
        raise StopUser()


# ── 7. weekly cron during traffic ──
class CronOnce(HttpUser):
    host = os.environ.get("TARGET", "http://mitihar-perf-api:8001")
    fixed_count = 1 if os.environ.get("CRON_AT") else None
    wait_time = between(1, 2)

    @task
    def fire(self):
        time.sleep(float(os.environ.get("CRON_AT", "30")))
        self.client.post("/internal/cron/complete-expired-plans", headers={"X-Cron-Secret": os.environ["CRON_SECRET"]},
                         timeout=300, name="POST /internal/cron/complete-expired-plans")
        raise StopUser()


# ── 8. refresh storm (single-use refresh tokens: each call is SELECT FOR UPDATE + UPDATE + INSERT) ──
class RefreshStorm(HttpUser):
    """
    Each virtual patient logs in once (spread over SPREAD_S), then rotates its refresh token every
    REFRESH_EVERY_S seconds with the cold-open calls in between: the app's real cycle (access token 15 min,
    here compressed so the rotation path is the load). A 401/refused refresh is a failure.
    """
    host = os.environ.get("TARGET", "http://mitihar-perf-api:8001")
    wait_time = constant_throughput(0.05)  # one pass every ~20 s per user, set REFRESH_EVERY_S via users/rate if needed

    def on_start(self):
        self.pid = 1 + next(_ctr) % 1000
        self.xff = {"X-Forwarded-For": f"10.{self.pid >> 8}.{self.pid & 255}.11"}
        time.sleep(random.uniform(0, SPREAD))
        r = self.client.post("/api/v1/auth/token", data={"username": f"perfpat{self.pid:04d}@mityahar-perf.test", "password": "PerfTest@2026"},
                             headers=self.xff, name="POST /auth/token (login)")
        if r.status_code != 200:
            raise StopUser()
        self.rt = r.json()["refresh_token"]

    @task
    def rotate(self):
        r = self.client.post("/api/v1/auth/refresh", json={"refresh_token": self.rt}, headers=self.xff, name="POST /auth/refresh")
        if r.status_code == 200 and r.json().get("refresh_token"):
            self.rt = r.json()["refresh_token"]
            self.client.get("/api/v1/users/me", headers={"Authorization": "Bearer " + r.json()["access_token"], **self.xff}, name="GET /users/me")


# ── 9. login flood (attacker) ──
class LoginFlood(HttpUser):
    """
    Attacker traffic next to normal users. Half the users hammer ONE email from many IPs (the per-email limit
    must stop it), half hammer many emails from ONE IP (the per-IP limit must stop it). 429 is the expected
    answer and counts as success here; what is measured is what the flood does to everyone else's latency.
    """
    host = os.environ.get("TARGET", "http://mitihar-perf-api:8001")
    fixed_count = env_int("FLOOD_USERS", 40)   # the rest of --users are the normal-traffic class
    wait_time = between(0.05, 0.2)

    def on_start(self):
        self.n = next(_ctr)
        self.mode = "one_email_many_ips" if self.n % 2 == 0 else "one_ip_many_emails"

    @task
    def attack(self):
        if self.mode == "one_email_many_ips":
            email, xff = "victim.target@mityahar-perf.test", f"172.20.{random.randint(0, 255)}.{random.randint(1, 254)}"
        else:
            email, xff = f"guess{random.randint(0, 10**9)}@mityahar-perf.test", "172.21.0.99"
        with self.client.post("/api/v1/auth/token", data={"username": email, "password": "Wrong#Guess1"},
                              headers={"X-Forwarded-For": xff}, name=f"POST /auth/token (flood, {self.mode})",
                              catch_response=True) as r:
            if r.status_code in (401, 429):
                r.success()
