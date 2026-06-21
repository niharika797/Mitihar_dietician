"""
TASK 5 E2E — Meal Config endpoints (Session 17)
Run: python tests/e2e_task5_meal_config.py
"""
import httpx
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

BASE = "http://localhost:8001/api/v1"
DB_URL = "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"

# 1. Doctor login
r = httpx.post(f"{BASE}/auth/doctor/login",
    data={"username": "dr.ashok.mehta@mitihar.test", "password": "DoctorTest@2026"})
assert r.status_code == 200, f"Doctor login FAIL: {r.status_code} {r.text}"
doc_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
print("Doctor login ✅")

# 2. GET meal-config returns defaults for Priya (patient_id=5)
r = httpx.get(f"{BASE}/doctor/patients/5/meal-config", headers=doc_headers)
assert r.status_code == 200, f"GET meal-config FAIL: {r.status_code} {r.text}"
cfg = r.json()
assert cfg["meal_split"] == {"Breakfast": 25, "Lunch": 35, "Dinner": 25}, \
    f"Expected default split, got {cfg['meal_split']}"
assert cfg["buffer_pct"] == 15
print(f"GET meal-config defaults ✅: {cfg['meal_split']}")

# 3. Validation rejects bad split (sum = 90, not 85)
r = httpx.patch(f"{BASE}/doctor/patients/5/meal-config", headers=doc_headers,
    json={"meal_split": {"Breakfast": 30, "Lunch": 40, "Dinner": 20}})
assert r.status_code == 422, f"Expected 422 on bad split, got {r.status_code} {r.text}"
print("422 on bad split (90 ≠ 85) ✅")

# 4. Valid split saves and regenerates
r = httpx.patch(f"{BASE}/doctor/patients/5/meal-config", headers=doc_headers,
    json={"meal_split": {"Breakfast": 25, "Lunch": 40, "Dinner": 20},
          "regenerate_plan": True}, timeout=90)
assert r.status_code == 200, f"PATCH meal-config FAIL: {r.status_code} {r.text}"
result = r.json()
assert result["config_saved"] is True, f"config_saved not True: {result}"
print(f"PATCH meal-config ✅: plan_regenerated={result.get('plan_regenerated')}, error={result.get('error')}")

# 5 & 6. DB checks
async def check_db():
    engine = create_async_engine(DB_URL)
    async with engine.connect() as conn:
        row = (await conn.execute(text(
            "SELECT meal_split_override FROM patient_meal_config WHERE patient_id = 5"
        ))).fetchone()
        assert row is not None, "No patient_meal_config row for patient_id=5"
        print(f"DB meal_split_override: {row[0]} ✅")

        row = (await conn.execute(text(
            "SELECT jsonb_array_length(meals::jsonb), created_at "
            "FROM recommendations WHERE patient_id = 5 "
            "ORDER BY created_at DESC LIMIT 1"
        ))).fetchone()
        assert row is not None, "No recommendations row for patient_id=5"
        assert row[0] == 21, f"Expected 21 slots, got {row[0]}"
        print(f"Regenerated plan: 21 slots ✅, created_at={row[1]}")

asyncio.run(check_db())

# 7. Pin a dish (food_id=276)
r = httpx.post(f"{BASE}/doctor/patients/5/meal-config/pin",
    headers=doc_headers, json={"food_id": 276})
assert r.status_code == 200, f"Pin FAIL: {r.status_code} {r.text}"
print("Pin dish 276 ✅")

# 8. Confirm pin appears in GET
r = httpx.get(f"{BASE}/doctor/patients/5/meal-config", headers=doc_headers)
assert r.status_code == 200
pinned = [d["food_id"] for d in r.json()["pinned_dishes"]]
assert 276 in pinned, f"Dish 276 not in pinned_dishes: {pinned}"
print("Pinned dish appears in GET ✅")

# 9. Block a dish (food_id=276 — switches pin→block atomically)
r = httpx.post(f"{BASE}/doctor/patients/5/meal-config/block",
    headers=doc_headers, json={"food_id": 276})
assert r.status_code == 200, f"Block FAIL: {r.status_code} {r.text}"
print("Block dish 276 (pin→block switch) ✅")

# 10. Confirm dish moved from pinned to blocked
r = httpx.get(f"{BASE}/doctor/patients/5/meal-config", headers=doc_headers)
cfg2 = r.json()
assert 276 not in [d["food_id"] for d in cfg2["pinned_dishes"]], "276 still in pinned after block"
assert 276 in [d["food_id"] for d in cfg2["blocked_dishes"]], "276 not in blocked"
print("Pin→block switch verified in GET ✅")

# 11. Unblock
r = httpx.delete(f"{BASE}/doctor/patients/5/meal-config/block/276", headers=doc_headers)
assert r.status_code == 200, f"Unblock FAIL: {r.status_code} {r.text}"
print("Unblock dish 276 ✅")

# 12. Reset to default
r = httpx.patch(f"{BASE}/doctor/patients/5/meal-config", headers=doc_headers,
    json={"meal_split": None, "regenerate_plan": False})
assert r.status_code == 200, f"Reset FAIL: {r.status_code} {r.text}"
reset_cfg = r.json()
assert reset_cfg["meal_split"] == {"Breakfast": 25, "Lunch": 35, "Dinner": 25}, \
    f"Reset did not return defaults: {reset_cfg['meal_split']}"
print("Reset to default ✅")

print("\n✅ All Task 5 checks PASS")
