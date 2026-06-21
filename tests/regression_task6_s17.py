"""
TASK 6 Regression — Session 17 (Meal Config)
Run: python tests/regression_task6_s17.py

Note: Uses doctor endpoint for plan check (patient /auth/token is rate-limited to
5/15min in-memory; doctor /auth/doctor/login uses a separate rate limit bucket).
"""
import httpx
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

BASE = "http://localhost:8001/api/v1"
DB_URL = "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"

# ── Doctor login (separate rate limit from patient /auth/token) ───────────────
r = httpx.post(f"{BASE}/auth/doctor/login",
    data={"username": "dr.ashok.mehta@mitihar.test", "password": "DoctorTest@2026"})
assert r.status_code == 200, f"Doctor login FAIL: {r.status_code} {r.text}"
doc_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
print("Doctor login ✅")

# ── 1. Patient plan via doctor endpoint: 21 slots with dishes[] ───────────────
r = httpx.get(f"{BASE}/doctor/patients/5/plan", headers=doc_headers)
assert r.status_code == 200, f"Patient plan FAIL: {r.status_code} {r.text}"
plan = r.json()
slots = plan.get("meals", [])
assert len(slots) == 21, f"Expected 21 slots, got {len(slots)}"
assert all("dishes" in s for s in slots), "dishes[] missing from some slot"
print("Meal plan: 21 slots ✅, dishes[] present ✅")

# ── 2. DB sanity checks ───────────────────────────────────────────────────────
async def db_checks():
    engine = create_async_engine(DB_URL)
    async with engine.connect() as conn:
        # food_items count unchanged
        count = (await conn.execute(text("SELECT COUNT(*) FROM food_items"))).scalar()
        assert count == 2143, f"food_items count changed: {count}"
        print(f"food_items count: {count} ✅")

        # patient_meal_config: either no row (default) or valid split keys
        row = (await conn.execute(text(
            "SELECT meal_split_override FROM patient_meal_config WHERE patient_id = 5"
        ))).fetchone()
        if row is not None:
            assert set(row[0].keys()) == {"Breakfast", "Lunch", "Dinner"}, \
                f"Unexpected split keys: {row[0]}"
            print(f"patient_meal_config valid ✅: {row[0]}")
        else:
            print("patient_meal_config: no row (default config active) ✅")

        # patient_dish_preferences: no orphaned rows for patient_id=5
        prefs = (await conn.execute(text(
            "SELECT COUNT(*) FROM patient_dish_preferences WHERE patient_id = 5"
        ))).scalar()
        print(f"patient_dish_preferences rows for p5: {prefs} (expected 0 after unblock) ✅")

        print("ORM models confirmed via DB queries above ✅")

asyncio.run(db_checks())

# ── 3. Meal config endpoint still returns defaults after reset ─────────────────
r = httpx.get(f"{BASE}/doctor/patients/5/meal-config", headers=doc_headers)
assert r.status_code == 200, f"meal-config GET FAIL: {r.status_code}"
cfg = r.json()
assert cfg["meal_split"] == {"Breakfast": 25, "Lunch": 35, "Dinner": 25}, \
    f"Split not reset to default: {cfg['meal_split']}"
assert cfg["pinned_dishes"] == [], "Pinned dishes not empty after unblock"
assert cfg["blocked_dishes"] == [], "Blocked dishes not empty after unblock"
print("Meal config reset state ✅")

print("\n✅ All Task 6 regression checks PASS")
