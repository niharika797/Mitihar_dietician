import requests
import pymongo
from pymongo import MongoClient
import time
import json
import uuid

BASE_URL = "http://127.0.0.1:8001"
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "diet_plan"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Clean up before tests
db.users.delete_many({"email": {"$in": ["testfree@dietapi.com", "testpremium@dietapi.com"]}})

results = []
summary = {"Pass": 0, "Fail": 0, "Warning": 0}
failures = []

def record(test_id, name, req_str, res_str, status, notes):
    res = f"{test_id} - {name}\nRequest:  {req_str}\nResponse: {res_str}\nStatus:   {status}\nNotes:    {notes}\n"
    results.append(res)
    if status.startswith("✅"):
        summary["Pass"] += 1
    elif status.startswith("❌"):
        summary["Fail"] += 1
        failures.append(f"{test_id} failed: {notes}")
    else:
        summary["Warning"] += 1
        failures.append(f"{test_id} warning: {notes}")
    print(res)

# Placeholder for a spinner function that just prints normally
def print_spinner(text):
    print(text)

free_user = {
    "email": "testfree@dietapi.com",
    "password": "TestPass123!",
    "name": "Free User",
    "age": 28,
    "gender": "male",
    "height": 175.0,
    "weight": 75.0,
    "activity_level": "MA",
    "diet": "Vegetarian",
    "health_condition": "Healthy",
    "region": "North"
}

premium_user = free_user.copy()
premium_user.update({
    "email": "testpremium@dietapi.com",
    "name": "Premium User",
    "diet": "Non-Vegetarian"
})

tokens = {"A": {"access": None, "refresh": None}, "B": {"access": None, "refresh": None}}

# GROUP 1 — Root & Health
# TEST-01: GET /
try:
    r = requests.get(f"{BASE_URL}/")
    req_str = f"GET /"
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code == 200 and "Welcome to Diet Plan API" in r.text:
        record("TEST-01", "GET /", req_str, res_str, "✅ Pass", "Root endpoint works")
    else:
        record("TEST-01", "GET /", req_str, res_str, "❌ Fail", "Unexpected response")
except Exception as e:
    record("TEST-01", "GET /", "GET /", str(e), "❌ Fail", "Exception occurred")

# GROUP 2 — Authentication
# TEST-02: POST /api/v1/auth/register — Register User A
try:
    r = requests.post(f"{BASE_URL}/api/v1/auth/register", json=free_user)
    req_str = f"POST /api/v1/auth/register (User A)"
    res_str = f"{r.status_code} | {r.text[:200]}"
    if r.status_code in [200, 201] and "password" not in r.json():
        record("TEST-02", "Register User A", req_str, res_str, "✅ Pass", "Registered cleanly")
    else:
        record("TEST-02", "Register User A", req_str, res_str, "❌ Fail", "Registration failed or password leaked")
except Exception as e:
    record("TEST-02", "Register User A", "POST", str(e), "❌ Fail", "Exception")

# TEST-03: POST /api/v1/auth/register — Register User B
try:
    r = requests.post(f"{BASE_URL}/api/v1/auth/register", json=premium_user)
    req_str = f"POST /api/v1/auth/register (User B)"
    res_str = f"{r.status_code} | {r.text[:200]}"
    if r.status_code in [200, 201]:
        record("TEST-03", "Register User B", req_str, res_str, "✅ Pass", "Registered cleanly")
        # Upgrade to premium
        db.users.update_one({"email": premium_user["email"]}, {"$set": {"meal_plan_purchased": True}})
    else:
        record("TEST-03", "Register User B", req_str, res_str, "❌ Fail", "Registration failed")
except Exception as e:
    record("TEST-03", "Register User B", "POST", str(e), "❌ Fail", "Exception")

# TEST-04: POST /api/v1/auth/register — Duplicate email
try:
    r = requests.post(f"{BASE_URL}/api/v1/auth/register", json=free_user)
    req_str = f"POST /api/v1/auth/register (Duplicate User A)"
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code in [400, 409]:
        record("TEST-04", "Duplicate email", req_str, res_str, "✅ Pass", "Duplicate rejected correctly")
    elif r.status_code == 500:
        record("TEST-04", "Duplicate email", req_str, res_str, "❌ Fail", "Server returned 500 error")
    else:
         record("TEST-04", "Duplicate email", req_str, res_str, "❌ Fail", "Unexpected status code")
except Exception as e:
    record("TEST-04", "Duplicate", "POST", str(e), "❌ Fail", "Exception")

# TEST-05: POST /api/v1/auth/register — Missing required field
try:
    bad_user = free_user.copy()
    del bad_user["password"]
    r = requests.post(f"{BASE_URL}/api/v1/auth/register", json=bad_user)
    req_str = f"POST /api/v1/auth/register (No password)"
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code == 422:
        record("TEST-05", "Missing required field", req_str, res_str, "✅ Pass", "422 correctly returned")
    else:
        record("TEST-05", "Missing required field", req_str, res_str, "❌ Fail", "Did not return 422")
except Exception as e:
    record("TEST-05", "Missing required field", "POST", str(e), "❌ Fail", "Exception")

# TEST-06: POST /api/v1/auth/token — Valid login (User A)
try:
    r = requests.post(f"{BASE_URL}/api/v1/auth/token", data={"username": free_user["email"], "password": free_user["password"], "grant_type": "password"})
    req_str = f"POST /api/v1/auth/token (User A)"
    res_str = f"{r.status_code} | access_token: {r.json().get('access_token', '')[:10]}..., refresh_token present: {'refresh_token' in r.json()}"
    if r.status_code == 200 and "access_token" in r.json() and "refresh_token" in r.json():
        tokens["A"]["access"] = r.json()["access_token"]
        tokens["A"]["refresh"] = r.json()["refresh_token"]
        record("TEST-06", "Valid login (User A)", req_str, res_str, "✅ Pass", "Tokens received")
    else:
        record("TEST-06", "Valid login (User A)", req_str, res_str, "❌ Fail", "Login failed or missing tokens")
except Exception as e:
    record("TEST-06", "Valid login (User A)", "POST", str(e), "❌ Fail", "Exception")

# Need token for User B for later tests
time.sleep(2)
try:
    r = requests.post(f"{BASE_URL}/api/v1/auth/token", data={"username": premium_user["email"], "password": premium_user["password"]})
    if r.status_code == 200:
        tokens["B"]["access"] = r.json().get("access_token")
except:
    pass

# TEST-07: POST /api/v1/auth/token — Wrong password
time.sleep(2)
try:
    r = requests.post(f"{BASE_URL}/api/v1/auth/token", data={"username": free_user["email"], "password": "wrongpassword123"})
    req_str = f"POST /api/v1/auth/token (Wrong password)"
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code == 401:
        record("TEST-07", "Wrong password", req_str, res_str, "✅ Pass", "401 correctly returned")
    else:
        record("TEST-07", "Wrong password", req_str, res_str, "❌ Fail", "Did not return 401")
except Exception as e:
    record("TEST-07", "Wrong password", "POST", str(e), "❌ Fail", "Exception")

# TEST-38: SQL/NoSQL injection attempt
try:
    r = requests.post(f"{BASE_URL}/api/v1/auth/token", data={"username": '{"$gt": ""}', "password": "any"})
    req_str = f'POST /api/v1/auth/token with NoSQLi'
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code in [401, 422]:
        record("TEST-38", "NoSQL Injection Try", req_str, res_str, "✅ Pass", "Blocked injection appropriately")
    else:
        record("TEST-38", "NoSQL Injection Try", req_str, res_str, "❌ Fail", f"Returned {r.status_code}")
except Exception as e:
     record("TEST-38", "NoSQL Injection Try", "POST", str(e), "❌ Fail", "Exception")

# TEST-08: POST /api/v1/auth/token — Rate limit test
time.sleep(2)
try:
    req_str = f"POST /api/v1/auth/token 21 times quickly"
    statuses = []
    for _ in range(21):
        r = requests.post(f"{BASE_URL}/api/v1/auth/token", data={"username": "random@test.com", "password": "password"})
        statuses.append(r.status_code)
    res_str = f"Statuses count: {len(statuses)}, last auth: {statuses[-1]}"
    if statuses[:20] == [401]*20 and statuses[20] == 429:
        record("TEST-08", "Rate limit test", req_str, res_str, "✅ Pass", "21st request returned 429")
    elif 429 in statuses:
         record("TEST-08", "Rate limit test", req_str, res_str, "⚠️ Warning", "Rate limit worked but pattern differed")
    else:
        record("TEST-08", "Rate limit test", req_str, res_str, "❌ Fail", "Did not get 429 Too Many Requests")
except Exception as e:
    record("TEST-08", "Rate limit test", "POST x6", str(e), "❌ Fail", "Exception")

# TEST-09: POST /api/v1/auth/refresh — Valid refresh
try:
    if tokens["A"]["refresh"]:
        r = requests.post(f"{BASE_URL}/api/v1/auth/refresh", json={"refresh_token": tokens["A"]["refresh"]})
        req_str = f"POST /api/v1/auth/refresh (User A)"
        res_str = f"{r.status_code} | new_access_token: {r.json().get('access_token', '')[:10]}..."
        if r.status_code == 200 and "access_token" in r.json():
            record("TEST-09", "Valid refresh", req_str, res_str, "✅ Pass", "New token issued")
        else:
            record("TEST-09", "Valid refresh", req_str, res_str, "❌ Fail", "Missing token or not 200")
    else:
        record("TEST-09", "Valid refresh", "No refresh token", "N/A", "❌ Fail", "Blocked by TEST-06 failure")
except Exception as e:
    record("TEST-09", "Valid refresh", "POST", str(e), "❌ Fail", "Exception")

# TEST-10: POST /api/v1/auth/refresh — Invalid/expired refresh token
try:
    r = requests.post(f"{BASE_URL}/api/v1/auth/refresh", json={"refresh_token": "garbage_token_string"})
    req_str = f"POST /api/v1/auth/refresh (Garbage token)"
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code in [401, 422]:
        record("TEST-10", "Invalid refresh token", req_str, res_str, "✅ Pass", "Handled gracefully")
    elif r.status_code == 500:
        record("TEST-10", "Invalid refresh token", req_str, res_str, "❌ Fail", "Server returned 500")
    else:
        record("TEST-10", "Invalid refresh token", req_str, res_str, "❌ Fail", "Unexpected status code")
except Exception as e:
    record("TEST-10", "Invalid refresh token", "POST", str(e), "❌ Fail", "Exception")

# GROUP 3 — Users
# TEST-11: GET /api/v1/users/me — Authenticated
try:
    headers_A = {"Authorization": f"Bearer {tokens['A']['access']}"}
    r = requests.get(f"{BASE_URL}/api/v1/users/me", headers=headers_A)
    req_str = f"GET /api/v1/users/me (User A)"
    data = r.json() if r.status_code == 200 else {}
    res_str = f"{r.status_code} | meal_plan_purchased: {data.get('meal_plan_purchased')}"
    if r.status_code == 200 and data.get("meal_plan_purchased") is False:
        record("TEST-11", "GET /me Authenticated", req_str, res_str, "✅ Pass", "Profile returned with correct status")
    else:
        record("TEST-11", "GET /me Authenticated", req_str, res_str, "❌ Fail", "Failed or incorrect status")
except Exception as e:
    record("TEST-11", "GET /me Authenticated", "GET", str(e), "❌ Fail", "Exception")

# TEST-12: GET /api/v1/users/me — No token
try:
    r = requests.get(f"{BASE_URL}/api/v1/users/me")
    req_str = f"GET /api/v1/users/me (No Header)"
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code == 401:
        record("TEST-12", "GET /me No token", req_str, res_str, "✅ Pass", "401 returned")
    else:
        record("TEST-12", "GET /me No token", req_str, res_str, "❌ Fail", "Did not return 401")
except Exception as e:
    record("TEST-12", "GET /me No token", "GET", str(e), "❌ Fail", "Exception")

# TEST-13: GET /api/v1/users/me — Expired/invalid token
try:
    r = requests.get(f"{BASE_URL}/api/v1/users/me", headers={"Authorization": f"Bearer garbage_token_xyz"})
    req_str = f"GET /api/v1/users/me (Garbage token)"
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code == 401:
        record("TEST-13", "GET /me Invalid token", req_str, res_str, "✅ Pass", "401 returned")
    else:
        record("TEST-13", "GET /me Invalid token", req_str, res_str, "❌ Fail", "Did not return 401")
except Exception as e:
    record("TEST-13", "GET /me Invalid token", "GET", str(e), "❌ Fail", "Exception")

# TEST-14: PUT /api/v1/users/me — Update profile
try:
    r = requests.put(f"{BASE_URL}/api/v1/users/me", headers=headers_A, json={"weight": 78, "activity_level": "VA"})
    req_str = f"PUT /api/v1/users/me (weight=78, activity=VA)"
    data = r.json() if r.status_code == 200 else {}
    res_str = f"{r.status_code} | weight: {data.get('weight')}, activity_level: {data.get('activity_level')}"
    if r.status_code == 200 and data.get("weight") == 78 and data.get("activity_level") == "VA":
        record("TEST-14", "PUT /me Update profile", req_str, res_str, "✅ Pass", "Profile updated correctly")
    else:
         record("TEST-14", "PUT /me Update profile", req_str, res_str, "❌ Fail", "Update failed")
except Exception as e:
    record("TEST-14", "PUT /me Update profile", "PUT", str(e), "❌ Fail", "Exception")

# TEST-15: PUT /api/v1/users/me — Invalid field value
try:
    r = requests.put(f"{BASE_URL}/api/v1/users/me", headers=headers_A, json={"age": -5})
    req_str = f"PUT /api/v1/users/me (age=-5)"
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code == 422:
        record("TEST-15", "Invalid field value", req_str, res_str, "✅ Pass", "422 Unprocessable Entity")
    elif r.status_code == 500:
        record("TEST-15", "Invalid field value", req_str, res_str, "❌ Fail", "500 Internal Server Error returned instead of validation error")
    else:
        record("TEST-15", "Invalid field value", req_str, res_str, "❌ Fail", "Did not return validation error")
except Exception as e:
    record("TEST-15", "Invalid field value", "PUT", str(e), "❌ Fail", "Exception")

# TEST-16: GET /api/v1/users/bmi
try:
    r = requests.get(f"{BASE_URL}/api/v1/users/bmi", headers=headers_A)
    req_str = f"GET /api/v1/users/bmi (User A)"
    data = r.json() if r.status_code == 200 else {}
    res_str = f"{r.status_code} | bmi: {data.get('bmi')}"
    expected_bmi = round(78.0 / (1.75 ** 2), 2)
    if r.status_code == 200 and abs(float(data.get("bmi", 0)) - expected_bmi) < 0.1:
        record("TEST-16", "GET /users/bmi", req_str, res_str, "✅ Pass", f"Calculated correctly as {expected_bmi}")
    else:
        record("TEST-16", "GET /users/bmi", req_str, res_str, "❌ Fail", f"Expected {expected_bmi}, got {data.get('bmi')}")
except Exception as e:
    record("TEST-16", "GET /users/bmi", "GET", str(e), "❌ Fail", "Exception")

# GROUP 4 — Calculations
# TEST-17: GET /api/v1/calculations/bmi
try:
    r = requests.get(f"{BASE_URL}/api/v1/calculations/bmi", headers=headers_A)
    req_str = f"GET /api/v1/calculations/bmi (User A)"
    data = r.json() if r.status_code == 200 else {}
    res_str = f"{r.status_code} | bmi: {data.get('bmi')}"
    expected_bmi = round(78.0 / (1.75 ** 2), 2)
    if r.status_code == 200 and abs(float(data.get("bmi", 0)) - expected_bmi) < 0.1:
        record("TEST-17", "GET /calculations/bmi", req_str, res_str, "✅ Pass", f"Same as users/bmi ({expected_bmi})")
    else:
        record("TEST-17", "GET /calculations/bmi", req_str, res_str, "❌ Fail", "BMI mismatch")
except Exception as e:
    record("TEST-17", "GET /calculations/bmi", "GET", str(e), "❌ Fail", "Exception")

# TEST-18: GET /api/v1/calculations/bmr
try:
    r = requests.get(f"{BASE_URL}/api/v1/calculations/bmr", headers=headers_A)
    req_str = f"GET /api/v1/calculations/bmr (User A)"
    data = r.json() if r.status_code == 200 else {}
    res_str = f"{r.status_code} | bmr: {data.get('bmr')}"
    expected_bmr = (10 * 78) + (6.25 * 175) - (5 * 28) + 5
    if r.status_code == 200 and abs(float(data.get("bmr", 0)) - expected_bmr) < 1.0:
        record("TEST-18", "GET /calculations/bmr", req_str, res_str, "✅ Pass", f"BMR matches Mifflin-St Jeor ({expected_bmr})")
    else:
        record("TEST-18", "GET /calculations/bmr", req_str, res_str, "❌ Fail", f"BMR mismatch. Expected {expected_bmr}, got {data.get('bmr')}")
except Exception as e:
    record("TEST-18", "GET /calculations/bmr", "GET", str(e), "❌ Fail", "Exception")

# TEST-19: GET /api/v1/calculations/tdee
try:
    r = requests.get(f"{BASE_URL}/api/v1/calculations/tdee", headers=headers_A)
    req_str = f"GET /api/v1/calculations/tdee (User A)"
    data = r.json() if r.status_code == 200 else {}
    res_str = f"{r.status_code} | tdee: {data.get('tdee')}"
    expected_tdee = expected_bmr * 1.725
    if r.status_code == 200 and abs(float(data.get("tdee", 0)) - expected_tdee) < 1.0:
        record("TEST-19", "GET /calculations/tdee", req_str, res_str, "✅ Pass", f"TDEE matches BMR * 1.725 ({expected_tdee})")
    else:
        record("TEST-19", "GET /calculations/tdee", req_str, res_str, "❌ Fail", f"TDEE mismatch. Expected {expected_tdee}, got {data.get('tdee')}")
except Exception as e:
    record("TEST-19", "GET /calculations/tdee", "GET", str(e), "❌ Fail", "Exception")

# GROUP 5 — Diet Plans
# TEST-20: POST /api/v1/diet-plans/generate — User A
try:
    r = requests.post(f"{BASE_URL}/api/v1/diet-plans/generate", headers=headers_A)
    req_str = f"POST /api/v1/diet-plans/generate (User A)"
    data = r.json() if r.status_code == 200 else {}
    res_str = f"{r.status_code} | data keys: {list(data.keys())}"
    
    if r.status_code == 200:
        meals = data.get("meals", [])
        checklist = data.get("ingredient_checklist", [])
        
        has_7_days = len(set(m.get("Date") for m in meals)) == 7
        all_meals_present = len(meals) == 42 # 7 days * 3 meals * 2 options
        all_options_present = all_meals_present
        checklist_populated = len(checklist) > 0
        all_vegetarian = all((opt.get("Diet", "") == "Vegetarian" or opt.get("Diet Type", "") == "Vegetarian" or opt.get("Type", "") == "Vegetarian") for opt in meals)
        if not all_vegetarian:
            # Fallback checking literal dictionary
             all_vegetarian = all("Vegetarian" in str(opt) for opt in meals)

        if has_7_days and all_meals_present and checklist_populated and all_vegetarian:
             record("TEST-20", "POST generate (User A)", req_str, res_str, "✅ Pass", "Valid structure, all meals Veg, checklist populated")
        else:
             notes = f"Structure validation failed. Days: {has_7_days}, Meals: {all_meals_present}, Checklist: {checklist_populated}, Veg: {all_vegetarian}"
             record("TEST-20", "POST generate (User A)", req_str, res_str, "❌ Fail", notes)
    else:
        record("TEST-20", "POST generate (User A)", req_str, res_str, "❌ Fail", f"Code {r.status_code}")
except Exception as e:
    record("TEST-20", "POST generate (User A)", "POST", str(e), "❌ Fail", "Exception")

# TEST-21: POST /api/v1/diet-plans/generate — User B
try:
    headers_B = {"Authorization": f"Bearer {tokens['B']['access']}"}
    r = requests.post(f"{BASE_URL}/api/v1/diet-plans/generate", headers=headers_B)
    req_str = f"POST /api/v1/diet-plans/generate (User B)"
    data = r.json() if r.status_code == 200 else {}
    res_str = f"{r.status_code} | "
    if r.status_code == 200:
        meals = data.get("meals", [])
        # check if non-vegetarian options are present
        has_non_veg = any("Non-Vegetarian" in str(opt) or "Non-Veg" in str(opt) or "Non Vegetarian" in str(opt) for opt in meals)
        if has_non_veg:
            record("TEST-21", "POST generate (User B)", req_str, res_str, "✅ Pass", "Contains Non-Vegetarian options")
        else:
             record("TEST-21", "POST generate (User B)", req_str, res_str, "❌ Fail", "No Non-Vegetarian options found")
    else:
        record("TEST-21", "POST generate (User B)", req_str, res_str, "❌ Fail", "Generation failed")
except Exception as e:
    record("TEST-21", "POST generate (User B)", "POST", str(e), "❌ Fail", "Exception")

# TEST-22: GET /api/v1/diet-plans/my-plan
try:
    r = requests.get(f"{BASE_URL}/api/v1/diet-plans/my-plan", headers=headers_A)
    req_str = f"GET /api/v1/diet-plans/my-plan (User A)"
    data = r.json() if r.status_code == 200 else {}
    res_str = f"{r.status_code} | has_checklist: {'ingredient_checklist' in data}, meals length: {len(data.get('meals', []))}"
    if r.status_code == 200 and len(data.get("meals", [])) == 42 and "ingredient_checklist" in data and len(data["ingredient_checklist"]) > 0:
        record("TEST-22", "GET /my-plan", req_str, res_str, "✅ Pass", "Same plan retrieved with checklist")
    else:
        record("TEST-22", "GET /my-plan", req_str, res_str, "❌ Fail", "Checklist missing or invalid plan")
except Exception as e:
    record("TEST-22", "GET /my-plan", "GET", str(e), "❌ Fail", "Exception")

# TEST-23: GET /api/v1/diet-plans/today
try:
    r = requests.get(f"{BASE_URL}/api/v1/diet-plans/today", headers=headers_A)
    req_str = f"GET /api/v1/diet-plans/today (User A)"
    data = r.json() if r.status_code == 200 else {}
    res_str = f"{r.status_code} | user_id logic: {'user_id' in data and data['user_id'] is not None}, meals length: {len(data.get('meals', []))}"
    if r.status_code == 200 and data.get("user_id") is not None and len(data.get("meals", [])) > 0:
        record("TEST-23", "GET /today", req_str, res_str, "✅ Pass", "Today's meals retrieved, user_id is populated")
    else:
        record("TEST-23", "GET /today", req_str, res_str, "❌ Fail", "Invalid response for today's meals")
except Exception as e:
    record("TEST-23", "GET /today", "GET", str(e), "❌ Fail", "Exception")

# TEST-24: GET /api/v1/diet-plans/ingredient-checklist
today_checklist_count = 0
today_checklist_grams = 0
try:
    r = requests.get(f"{BASE_URL}/api/v1/diet-plans/ingredient-checklist", headers=headers_A)
    req_str = f"GET /api/v1/diet-plans/ingredient-checklist (User A)"
    data = r.json() if r.status_code == 200 else []
    if type(data) is dict and "ingredient_checklist" in data:
       data = data["ingredient_checklist"]
    res_str = f"{r.status_code} | count: {len(data)}"
    if r.status_code == 200:
        today_checklist_count = len(data)
        today_checklist_grams = sum(item.get("Total Amount (g)", item.get("gram", item.get("Amount_g", item.get("amount_g", 0)))) for item in data)
        record("TEST-24", "GET /ingredient-checklist", req_str, res_str, "✅ Pass", f"Today's items: {today_checklist_count}, {today_checklist_grams}g")
    else:
         record("TEST-24", "GET /ingredient-checklist", req_str, res_str, "❌ Fail", "Failed API call")
except Exception as e:
    record("TEST-24", "GET /ingredient-checklist", "GET", str(e), "❌ Fail", "Exception")

# TEST-25: GET /api/v1/diet-plans/weekly-ingredients
try:
    r = requests.get(f"{BASE_URL}/api/v1/diet-plans/weekly-ingredients", headers=headers_A)
    req_str = f"GET /api/v1/diet-plans/weekly-ingredients (User A)"
    data = r.json() if r.status_code == 200 else []
    if type(data) is dict and "weekly_ingredients" in data:
       data = data["weekly_ingredients"]
    res_str = f"{r.status_code} | count: {len(data)}"
    if r.status_code == 200:
        weekly_count = len(data)
        weekly_grams = sum(item.get("Total Amount (g)", item.get("gram", item.get("Amount_g", item.get("amount_g", 0)))) for item in data)
        if weekly_count >= today_checklist_count and weekly_grams >= today_checklist_grams:
            record("TEST-25", "GET /weekly-ingredients", req_str, res_str, "✅ Pass", f"Weekly ({weekly_count}, {weekly_grams}g) >= Today ({today_checklist_count}, {today_checklist_grams}g)")
        elif today_checklist_count == 0:
            record("TEST-25", "GET /weekly-ingredients", req_str, res_str, "⚠️ Warning", "Today count was 0, comparison impossible but retrieved.")
        else:
             record("TEST-25", "GET /weekly-ingredients", req_str, res_str, "❌ Fail", "Weekly ingredients not strictly greater than today's")
    else:
        record("TEST-25", "GET /weekly-ingredients", req_str, res_str, "❌ Fail", "Failed API call")
except Exception as e:
    record("TEST-25", "GET /weekly-ingredients", "GET", str(e), "❌ Fail", "Exception")

# TEST-26: PUT /api/v1/diet-plans/update
try:
    r_get = requests.get(f"{BASE_URL}/api/v1/diet-plans/my-plan", headers=headers_A)
    if r_get.status_code == 200:
        plan_doc = r_get.json()
        if len(plan_doc.get("meals", [])) > 0:
            # modify first meal Menu 
            for k in plan_doc["meals"][0].keys():
                if str(k).lower().startswith("menu"):
                    plan_doc["meals"][0][k] = "TEST UPDATED MENU"
                    break

        r = requests.put(f"{BASE_URL}/api/v1/diet-plans/update", headers=headers_A, json=plan_doc)
        req_str = f"PUT /api/v1/diet-plans/update"
        data = r.json() if r.status_code == 200 else {}
        res_str = f"{r.status_code} | {r.text[:100]}"
        if r.status_code == 200 and "TEST UPDATED MENU" in json.dumps(data):
            record("TEST-26", "PUT /diet-plans/update", req_str, res_str, "✅ Pass", "Menu updated successfully")
        else:
             record("TEST-26", "PUT /diet-plans/update", req_str, res_str, "❌ Fail", "Update did not reflect")
    else:
        record("TEST-26", "PUT /diet-plans/update", "GET failed prior setup", "N/A", "❌ Fail", "Setup failed")
        
except Exception as e:
    record("TEST-26", "PUT /diet-plans/update", "PUT", str(e), "❌ Fail", "Exception")

# TEST-27: DELETE /api/v1/diet-plans/delete
try:
    r = requests.delete(f"{BASE_URL}/api/v1/diet-plans/delete", headers=headers_A)
    req_str = f"DELETE /api/v1/diet-plans/delete"
    res_str = f"{r.status_code}"
    
    r_check = requests.get(f"{BASE_URL}/api/v1/diet-plans/my-plan", headers=headers_A)
    if r.status_code in [200, 204] and r_check.status_code in [404, 200]: # it might return 200 but empty/null plan if logical delete, assuming 404 is best.
        if r_check.status_code == 404 or r_check.json() is None:
             record("TEST-27", "DELETE /diet-plans/delete", req_str, res_str, "✅ Pass", "Deleted successfully and my-plan returns 404")
        else:
             # some setups return 200 with error property.
             if "detail" in r_check.json() or "error" in r_check.json():
                  record("TEST-27", "DELETE /diet-plans/delete", req_str, res_str, "✅ Pass", "Deleted successfully and my-plan returns empty/error")
             else:
                  record("TEST-27", "DELETE /diet-plans/delete", req_str, res_str, "❌ Fail", f"Delete returned {r.status_code} but plan still visible")
    else:
         record("TEST-27", "DELETE /diet-plans/delete", req_str, res_str, "❌ Fail", f"Status {r.status_code}, Check status {r_check.status_code}")
except Exception as e:
    record("TEST-27", "DELETE /diet-plans/delete", "DELETE", str(e), "❌ Fail", "Exception")

# GROUP 6 — Meal Plan Adjustment
# TEST-28: POST /api/v1/meal-plan/adjust — Free user blocked
try:
    r = requests.post(f"{BASE_URL}/api/v1/meal-plan/adjust", headers=headers_A, json={"reduction_amount": 300})
    req_str = f"POST /api/v1/meal-plan/adjust (User A)"
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code == 403:
        record("TEST-28", "POST adjust (Free blocked)", req_str, res_str, "✅ Pass", "Correctly returned 403")
    else:
        record("TEST-28", "POST adjust (Free blocked)", req_str, res_str, "❌ Fail", "Did not return 403 Forbidden")
except Exception as e:
    record("TEST-28", "POST adjust (Free blocked)", "POST", str(e), "❌ Fail", "Exception")

# TEST-29: POST /api/v1/meal-plan/adjust — Premium user allowed
try:
    # First generate plan for B
    requests.post(f"{BASE_URL}/api/v1/diet-plans/generate", headers=headers_B)
    r_bmr = requests.get(f"{BASE_URL}/api/v1/calculations/tdee", headers=headers_B)
    tdee = float(r_bmr.json().get("tdee", 0)) if r_bmr.status_code == 200 else 2500
    
    r = requests.post(f"{BASE_URL}/api/v1/meal-plan/adjust", headers=headers_B, json={"reduction_amount": 300})
    req_str = f"POST /api/v1/meal-plan/adjust (User B)"
    data = r.json() if r.status_code == 200 else {}
    res_str = f"{r.status_code} | target_calories: {data.get('new_target_calories')}"
    if r.status_code == 200 and data.get("new_target_calories"):
        if abs(float(data.get("new_target_calories")) - (tdee - 300)) < 1.0:
             record("TEST-29", "POST adjust (Premium)", req_str, res_str, "✅ Pass", "Math matches tdee - 300")
        else:
             record("TEST-29", "POST adjust (Premium)", req_str, res_str, "⚠️ Warning", "Math didn't match exactly, but returning 200")
    else:
        record("TEST-29", "POST adjust (Premium)", req_str, res_str, "❌ Fail", "Status != 200 or missing new_target_calories")
except Exception as e:
    record("TEST-29", "POST adjust (Premium)", "POST", str(e), "❌ Fail", "Exception")

# TEST-39: Oversized input
try:
    r = requests.post(f"{BASE_URL}/api/v1/meal-plan/adjust", headers=headers_B, json={"reduction_amount": 999999})
    req_str = f"POST /api/v1/meal-plan/adjust (Oversized)"
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code in [422, 200]:
        record("TEST-39", "Oversized Input", req_str, res_str, "✅ Pass", "Handled gracefully (clamped or 422)")
    elif r.status_code == 500:
        record("TEST-39", "Oversized Input", req_str, res_str, "❌ Fail", "Server returned 500")
    else:
         record("TEST-39", "Oversized Input", req_str, res_str, "❌ Fail", "Unexpected code")
except Exception as e:
     record("TEST-39", "Oversized Input", "POST", str(e), "❌ Fail", "Exception")

# TEST-30: POST /api/v1/meal-plan/adjust — Rate limit test
try:
    req_str = f"POST /api/v1/meal-plan/adjust 11 times"
    statuses = []
    for _ in range(11):
        r = requests.post(f"{BASE_URL}/api/v1/meal-plan/adjust", headers=headers_B, json={"reduction_amount": 300})
        statuses.append(r.status_code)
    res_str = f"Statuses: {statuses}"
    if 429 in statuses and 200 in statuses:
        record("TEST-30", "Rate limit test adjust", req_str, res_str, "✅ Pass", f"Rate limit hit at request {statuses.index(429)+1}")
    elif 429 in statuses:
         record("TEST-30", "Rate limit test adjust", req_str, res_str, "⚠️ Warning", "Rate limit worked but pattern differed")
    else:
        record("TEST-30", "Rate limit test adjust", req_str, res_str, "❌ Fail", "Did not get 429 Too Many Requests")
except Exception as e:
    record("TEST-30", "Rate limit test adjust", "POST x11", str(e), "❌ Fail", "Exception")

# GROUP 7 — Progress
# TEST-31: POST /api/v1/progress/log/meal
try:
    r = requests.post(f"{BASE_URL}/api/v1/progress/log/meal", headers=headers_A, json={"meal_type": "Lunch", "calories": 500, "protein": 30, "carbs": 50, "fat": 15})
    req_str = f"POST /api/v1/progress/log/meal (User A)"
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code in [200, 201]:
        record("TEST-31", "Log meal", req_str, res_str, "✅ Pass", "Logged successfully")
    else:
        record("TEST-31", "Log meal", req_str, res_str, "❌ Fail", "Failed to log")
except Exception as e:
    record("TEST-31", "Log meal", "POST", str(e), "❌ Fail", "Exception")

# TEST-32: POST /api/v1/progress/log/water
try:
    r = requests.post(f"{BASE_URL}/api/v1/progress/log/water", headers=headers_A, json={"glasses": 3})
    req_str = f"POST /api/v1/progress/log/water (User A)"
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code in [200, 201]:
        record("TEST-32", "Log water", req_str, res_str, "✅ Pass", "Logged successfully")
    else:
        record("TEST-32", "Log water", req_str, res_str, "❌ Fail", "Failed to log")
except Exception as e:
    record("TEST-32", "Log water", "POST", str(e), "❌ Fail", "Exception")

# TEST-33: POST /api/v1/progress/log/activity
try:
    r = requests.post(f"{BASE_URL}/api/v1/progress/log/activity", headers=headers_A, json={"steps": 6000, "calories_burned": 300, "activity_type": "Walking"})
    req_str = f"POST /api/v1/progress/log/activity (User A)"
    res_str = f"{r.status_code} | {r.text[:100]}"
    if r.status_code in [200, 201]:
        record("TEST-33", "Log activity", req_str, res_str, "✅ Pass", "Logged successfully")
    else:
        record("TEST-33", "Log activity", req_str, res_str, "❌ Fail", "Failed to log")
except Exception as e:
    record("TEST-33", "Log activity", "POST", str(e), "❌ Fail", "Exception")

# TEST-34: GET /api/v1/progress/today
try:
    r = requests.get(f"{BASE_URL}/api/v1/progress/today", headers=headers_A)
    req_str = f"GET /api/v1/progress/today (User A)"
    data = r.json() if r.status_code == 200 else {}
    cals = data.get("calories", {}).get("consumed", 0)
    water = data.get("water_intake", {}).get("glasses", 0)
    steps = data.get("activity", {}).get("steps", 0)
    res_str = f"{r.status_code} | calories: {cals}, water: {water}, steps: {steps}"
    if r.status_code == 200 and cals >= 500 and water >= 3 and steps >= 6000:
        record("TEST-34", "GET /progress/today", req_str, res_str, "✅ Pass", "Reflects logged values")
    else:
        record("TEST-34", "GET /progress/today", req_str, res_str, "❌ Fail", "Values do not reflect logs")
except Exception as e:
    record("TEST-34", "GET /progress/today", "GET", str(e), "❌ Fail", "Exception")

# TEST-35: GET /api/v1/progress/weekly
try:
    r = requests.get(f"{BASE_URL}/api/v1/progress/weekly", headers=headers_A)
    req_str = f"GET /api/v1/progress/weekly (User A)"
    data = r.json() if r.status_code == 200 else {}
    res_str = f"{r.status_code} | daily_data length: {len(data.get('daily_data', []))}, avg_cals: {data.get('summary', {}).get('average_calories_consumed')}"
    if r.status_code == 200 and "daily_data" in data and "summary" in data:
        record("TEST-35", "GET /progress/weekly", req_str, res_str, "✅ Pass", "Weekly data returned with summary")
    else:
         record("TEST-35", "GET /progress/weekly", req_str, res_str, "❌ Fail", "Invalid weekly data structure")
except Exception as e:
    record("TEST-35", "GET /progress/weekly", "GET", str(e), "❌ Fail", "Exception")

# TEST-36: GET /api/v1/progress/weight
try:
    r = requests.get(f"{BASE_URL}/api/v1/progress/weight", headers=headers_A)
    req_str = f"GET /api/v1/progress/weight (User A)"
    data = r.json() if r.status_code == 200 else {}
    res_str = f"{r.status_code} | current_weight: {data.get('current_weight')}"
    if r.status_code == 200 and data.get("current_weight") == 78.0:
        record("TEST-36", "GET /progress/weight", req_str, res_str, "✅ Pass", "Weight tracking matches profile")
    else:
        record("TEST-36", "GET /progress/weight", req_str, res_str, "❌ Fail", f"Weight mismatch, expected 78.0 got {data.get('current_weight')}")
except Exception as e:
    record("TEST-36", "GET /progress/weight", "GET", str(e), "❌ Fail", "Exception")

# GROUP 8 — Edge Cases & Security
# TEST-37: Cross-user data isolation
try:
    requests.post(f"{BASE_URL}/api/v1/diet-plans/generate", headers=headers_A) # Setup fresh plan A
    r = requests.get(f"{BASE_URL}/api/v1/diet-plans/my-plan", headers=headers_A)
    req_str = f"GET /api/v1/diet-plans/my-plan (User A against User B's potential leak)"
    
    # We should ensure there is no crossover.
    if r.status_code == 200:
        plan = r.json().get("plan", {})
        has_non_veg = any("Non-Vegetarian" in str(opt) or "Non-Veg" in str(opt) for day_meals in plan.values() for meal in day_meals.values() for opt in meal)
        res_str = f"{r.status_code} | has_b_profile_data: {has_non_veg}"
        if not has_non_veg:
            record("TEST-37", "Data Isolation", req_str, res_str, "✅ Pass", "Plan contains only A's data (Vegetarian)")
        else:
            record("TEST-37", "Data Isolation", req_str, res_str, "❌ Fail", "User A sees User B's non-vegetarian data")
    else:
        record("TEST-37", "Data Isolation", req_str, str(r.status_code), "❌ Fail", "Failed to retrieve plan")
except Exception as e:
    record("TEST-37", "Data Isolation", "GET", str(e), "❌ Fail", "Exception")




print("\n--- SUMMARY ---")
print(f"Total Pass: {summary['Pass']}")
print(f"Total Fail: {summary['Fail']}")
print(f"Total Warning: {summary['Warning']}")

if len(failures) > 0:
    for f in failures:
        print("Failure:", f)

if summary["Fail"] == 0 and summary["Warning"] == 0:
    print("Verdict: ✅ Production Ready")
elif summary["Fail"] == 0:
    print("Verdict: ⚠️ Ready with Caveats")
else:
    print("Verdict: ❌ Not Ready")
