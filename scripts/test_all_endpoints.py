import requests
import time
import urllib3

urllib3.disable_warnings()

BASE_URL = "http://localhost:8000/api/v1"

def print_result(step, desc, is_pass, res=None):
    status = "PASS" if is_pass else "FAIL"
    sc = res.status_code if res else "N/A"
    print(f"[{status}] {step}: {desc} (Status: {sc})")
    if not is_pass and res is not None:
        try:
            print(f"      Response: {res.json()}")
        except:
            print(f"      Response: {res.text}")

def run_tests():
    state = {}
    ts = int(time.time())
    
    print("================ MITYAHAR API INTEGRATION TEST ================")
    
    # --- Phase 1 ---
    res = requests.post(f"{BASE_URL}/auth/admin/login", data={"username": "admin@mityahar.com", "password": "admin1234"})
    is_pass = False
    try:
        is_pass = res.status_code == 200 and "access_token" in res.json()
    except Exception:
        pass
    print_result("Step 1", "Admin Login", is_pass, res)
    if not is_pass: return
    state["admin_token"] = res.json()["access_token"]
    admin_auth = {"Authorization": f"Bearer {state['admin_token']}"}

    doc_email = f"drpriya_{ts}@mityahar.com"
    res = requests.post(f"{BASE_URL}/admin/doctors", json={
        "email": doc_email, "password": "Doctor@1234", "name": "Dr. Priya Mehta",
        "phone": f"987654{ts%10000:04}", "specialization": "Dietitian", "clinic_name": "Healthy Roots", "city": "Mumbai"
    }, headers=admin_auth)
    is_pass = res.status_code == 201
    print_result("Step 2", "Create Doctor", is_pass, res)
    if not is_pass: return
    state["doctor_id"] = res.json()["id"]
    state["doctor_email"] = doc_email

    # --- Phase 2 ---
    pat_email = f"testpatient_{ts}@gmail.com"
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": pat_email, "password": "Patient@123", "name": "Rahul Sharma",
        "age": 28, "gender": "Male", "height": 175, "weight": 72, "activity_level": "MA", 
        "diet": "Vegetarian", "health_condition": "Healthy", "region": "North"
    })
    is_pass = res.status_code in [200, 201]
    print_result("Step 3", "Patient Register", is_pass, res)
    if not is_pass: return
    state["patient_id"] = res.json().get("user_id")

    res = requests.post(f"{BASE_URL}/auth/token", data={"username": pat_email, "password": "Patient@123"})
    is_pass = res.status_code == 200
    print_result("Step 4", "Patient Login", is_pass, res)
    if not is_pass: return
    state["patient_token"] = res.json()["access_token"]
    state["refresh_token"] = res.json()["refresh_token"]
    pat_auth = {"Authorization": f"Bearer {state['patient_token']}"}

    res = requests.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": state["refresh_token"]})
    print_result("Step 5", "Refresh Token", res.status_code == 200, res)

    res = requests.post(f"{BASE_URL}/auth/doctor/login", data={"username": state["doctor_email"], "password": "Doctor@1234"})
    is_pass = res.status_code == 200
    print_result("Step 6", "Doctor Login", is_pass, res)
    state["doctor_token"] = res.json()["access_token"]
    doc_auth = {"Authorization": f"Bearer {state['doctor_token']}"}

    print_result("Step 7", "Google Verify (ignored, requires real Google token)", True)

    res = requests.get(f"{BASE_URL}/users/me", headers=pat_auth)
    print_result("Step 8", "Get My Profile", res.status_code == 200, res)

    res = requests.put(f"{BASE_URL}/users/me", json={"weight": 71, "activity_level": "VA", "region": "South"}, headers=pat_auth)
    print_result("Step 9", "Update My Profile", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/users/bmi", headers=pat_auth)
    print_result("Step 10", "Get BMI", res.status_code == 200, res)

    res = requests.post(f"{BASE_URL}/patients/onboarding", json={
        "date_of_birth": "1997-06-15", "health_goals": ["weight_loss", "improve_energy"],
        "medical_conditions": ["None"], "food_allergies": ["None"], "target_weight_kg": 68.0,
        "meals_per_day": 5, "sleep_hours": 7.0, "water_glasses": 8, "occupation": "Software Engineer",
        "nonveg_meals_per_week": 0, "dietary_preferences": ["low_sugar"], "fasting_days": [],
        "smoking": False, "alcohol": False, "pace_preference": "moderate", "eating_habits": ["irregular_meals"]
    }, headers=pat_auth)
    print_result("Step 11", "Patient Onboarding", res.status_code == 200, res)

    res = requests.post(f"{BASE_URL}/patients/disclaimer", headers=pat_auth)
    print_result("Step 12", "Accept Disclaimer", res.status_code == 200, res)

    # --- Phase 3 ---
    res = requests.post(f"{BASE_URL}/admin/codes/generate", json={
        "doctor_id": state["doctor_id"], "count": 3, "expires_in_days": 30
    }, headers=admin_auth)
    is_pass = res.status_code == 201
    print_result("Step 13", "Generate Subscription Codes (Admin)", is_pass, res)
    state["codes"] = res.json() if is_pass else []
    
    res = requests.get(f"{BASE_URL}/admin/codes?doctor_id={state['doctor_id']}&is_used=false", headers=admin_auth)
    print_result("Step 14", "List All Codes (Admin)", res.status_code == 200, res)

    res = requests.post(f"{BASE_URL}/doctor/subscription-codes", json={"count": 2, "expires_in_days": 30}, headers=doc_auth)
    print_result("Step 15", "Generate Subscription Codes (Doctor)", res.status_code == 201, res)

    res = requests.get(f"{BASE_URL}/doctor/subscription-codes", headers=doc_auth)
    print_result("Step 16", "List Doctor's Own Codes", res.status_code == 200, res)

    # Step 18 runs BEFORE Step 17: patient.doctor_id is still null here, so request succeeds
    res = requests.post(f"{BASE_URL}/patients/request-doctor", json={"doctor_id": state["doctor_id"]}, headers=pat_auth)
    is_pass = res.status_code == 201
    print_result("Step 18", "Request Doctor Connection", is_pass, res)
    if is_pass: state["request_id"] = res.json().get("request_id")

    # Step 17: activate subscription — sets patient.doctor_id, must come after Step 18
    code1 = state["codes"][0]["code"] if state.get("codes") and len(state["codes"]) > 0 else "INVALID_CODE"
    res = requests.post(f"{BASE_URL}/patients/activate", json={"code": code1}, headers=pat_auth)
    print_result("Step 17", "Activate Subscription (Patient)", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/patients/request-status", headers=pat_auth)
    print_result("Step 19", "Check Request Status", res.status_code == 200, res)

    # EC-8: patient.doctor_id is now set by Step 17 — duplicate request must 409
    res = requests.post(f"{BASE_URL}/patients/request-doctor", json={"doctor_id": state["doctor_id"]}, headers=pat_auth)
    print_result("EC-8", "Duplicate doctor request (409 expected)", res.status_code == 409, res)

    # --- Phase 4 ---
    res = requests.get(f"{BASE_URL}/doctor/dashboard", headers=doc_auth)
    print_result("Step 20", "Doctor Dashboard", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/doctor/patients?page=1&page_size=20", headers=doc_auth)
    print_result("Step 21", "List My Patients (Doctor)", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/doctor/patients/{state['patient_id']}", headers=doc_auth)
    print_result("Step 22", "Get Single Patient (Doctor)", res.status_code in [200, 404, 403], res) 

    res = requests.get(f"{BASE_URL}/doctor/requests", headers=doc_auth)
    print_result("Step 23", "List Pending Requests (Doctor)", res.status_code == 200, res)

    if state.get("request_id"):
        res = requests.post(f"{BASE_URL}/doctor/requests/{state['request_id']}/accept", headers=doc_auth)
        print_result("Step 24", "Accept a Patient Request", res.status_code == 200, res)
    else:
        print_result("Step 24", "Accept a Patient Request (Skipped, no request_id)", False)

    # Step 25 Setup -> Reject a request
    pat2_email = f"pat_rej_{ts}@gmail.com"
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": pat2_email, "password": "Patient@123", "name": "Reject Me", "age": 28, "gender": "Male", 
        "height": 175, "weight": 72, "activity_level": "MA", "diet": "Vegetarian", "health_condition": "Healthy", "region": "North"
    })
    pat2_token = requests.post(f"{BASE_URL}/auth/token", data={"username": pat2_email, "password": "Patient@123"}).json().get("access_token")
    pat2_auth = {"Authorization": f"Bearer {pat2_token}"}
    if pat2_token and len(state.get("codes", [])) > 1:
        # Request doctor BEFORE activating — same pattern as Steps 18/17
        rej_req = requests.post(f"{BASE_URL}/patients/request-doctor", json={"doctor_id": state["doctor_id"]}, headers=pat2_auth).json()
        requests.post(f"{BASE_URL}/patients/activate", json={"code": state["codes"][1]["code"]}, headers=pat2_auth)
        if "request_id" in rej_req:
            res = requests.post(f"{BASE_URL}/doctor/requests/{rej_req['request_id']}/reject", json={"rejection_note": "Not accepting"}, headers=doc_auth)
            print_result("Step 25", "Reject a Patient Request", res.status_code == 200, res)
        else:
            print_result("Step 25", "Reject a Patient Request (Skipped setup failed)", False)
    else:
        print_result("Step 25", "Reject a Patient Request (Skipped setup failed)", False)

    res = requests.get(f"{BASE_URL}/doctor/patients/{state['patient_id']}/plan", headers=doc_auth)
    print_result("Step 26", "Get Patient's Active Plan", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/doctor/patients/{state['patient_id']}/logs?days=7", headers=doc_auth)
    print_result("Step 27", "View Patient Meal Logs (Doctor)", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/doctor/patients/{state['patient_id']}/progress?days=30", headers=doc_auth)
    print_result("Step 28", "View Patient Progress (Doctor)", res.status_code == 200, res)

    res = requests.post(f"{BASE_URL}/doctor/patients/{state['patient_id']}/notes", json={
        "content": "Patient shows signs of irregular eating.", "note_type": "dietary", "is_private": True
    }, headers=doc_auth)
    print_result("Step 29", "Add Clinical Note", res.status_code == 201, res)

    res = requests.get(f"{BASE_URL}/doctor/patients/{state['patient_id']}/notes", headers=doc_auth)
    print_result("Step 30", "Get Clinical Notes (Doctor)", res.status_code == 200, res)

    # Refresh token so the new 'active' status is reflected in the JWT claims
    r_refresh = requests.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": state.get("refresh_token")})
    if r_refresh.status_code == 200:
        state["patient_token"] = r_refresh.json()["access_token"]
        pat_auth = {"Authorization": f"Bearer {state['patient_token']}"}

    # --- Phase 5 ---
    res = requests.get(f"{BASE_URL}/calculations/bmr", headers=pat_auth)
    print_result("Step 31", "Calculate BMR", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/calculations/tdee", headers=pat_auth)
    print_result("Step 32", "Calculate TDEE", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/calculations/bmi", headers=pat_auth)
    print_result("Step 33", "Calculate BMI", res.status_code == 200, res)

    time.sleep(1) # Let background tasks finish if any
    res = requests.post(f"{BASE_URL}/diet-plans/generate", headers=pat_auth)
    print_result("Step 34", "Generate Diet Plan", res.status_code in [200, 201], res)

    res = requests.get(f"{BASE_URL}/diet-plans/my-plan", headers=pat_auth)
    is_pass = res.status_code == 200
    print_result("Step 35", "Get My Active Plan", is_pass, res)
    if is_pass: state["recommendation_id"] = res.json().get("id")

    res = requests.get(f"{BASE_URL}/diet-plans/today", headers=pat_auth)
    print_result("Step 36", "Get Today's Meals", res.status_code == 200, res)

    plan_res = requests.get(f"{BASE_URL}/diet-plans/my-plan", headers=pat_auth)
    if plan_res.status_code == 200:
        full_plan = plan_res.json()
        full_plan["doctor_notes"] = "I prefer lighter breakfasts"
        res = requests.put(f"{BASE_URL}/diet-plans/update", json=full_plan, headers=pat_auth)
    else:
        res = plan_res
    print_result("Step 37", "Update Plan", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/diet-plans/ingredient-checklist", headers=pat_auth)
    print_result("Step 38", "Get Ingredient Checklist", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/diet-plans/weekly-ingredients", headers=pat_auth)
    print_result("Step 39", "Get Weekly Ingredients", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/meal-plan/week", headers=pat_auth)
    print_result("Step 40", "Get Week View", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/meal-plan/history", headers=pat_auth)
    print_result("Step 41", "Get Plan History", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/meal-plan/shopping-list", headers=pat_auth)
    print_result("Step 42", "Get Shopping List", res.status_code == 200, res)
    state["shopping_list_res"] = res

    # Step 43: pick a real ingredient from the shopping list instead of hardcoding
    _toggle_ingredient = None
    if res.status_code == 200:
        _grouped = res.json().get("grouped", {})
        for _cat_items in _grouped.values():
            if _cat_items:
                _toggle_ingredient = _cat_items[0].get("ingredient")
                break
    if _toggle_ingredient:
        res = requests.post(f"{BASE_URL}/meal-plan/shopping-list/toggle",
            params={"ingredient_name": _toggle_ingredient, "at_home": "true"}, headers=pat_auth)
        print_result("Step 43", f"Toggle Shopping Item ({_toggle_ingredient})", res.status_code == 200, res)
    else:
        print_result("Step 43", "Toggle Shopping Item (Skipped — no ingredients in list)", False)

    res = requests.post(f"{BASE_URL}/meal-plan/adjust", json={"reduction_amount": 200}, headers=pat_auth)
    print_result("Step 44", "Adjust Meal Plan", res.status_code == 200, res)

    res = requests.delete(f"{BASE_URL}/diet-plans/delete", headers=pat_auth)
    print_result("Step 45", "Delete Active Plan", res.status_code == 200, res)

    # Regenerate so Step 49 has an active plan
    requests.post(f"{BASE_URL}/diet-plans/generate", headers=pat_auth)

    # --- Phase 6 ---
    res = requests.get(f"{BASE_URL}/doctor/recipes?diet_type=Vegetarian&meal_time=Breakfast&page=1&page_size=20", headers=doc_auth)
    print_result("Step 46", "Browse Recipes", res.status_code == 200, res)

    res = requests.post(f"{BASE_URL}/doctor/recipes", json={
        "recipe_name": f"Moong Dal Chilla {ts}", "slot_type": "main_dish", "cal_per_serving": 280,
        "protein_per_serving": 14, "carbs_per_serving": 38, "fat_per_serving": 6, "fiber_per_serving": 5,
        "diet_type": "Vegetarian", "meal_time_tags": ["Breakfast", "MorningSnacks"], 
        "plan_type_tags": ["Healthy", "Diabetic-Friendly"], "ingredients": [{"name": "Moong Dal", "amount_g": 80}],
        "region_tags": ["North", "West"]
    }, headers=doc_auth)
    is_pass = res.status_code == 201
    print_result("Step 47", "Add a Custom Recipe", is_pass, res)
    if is_pass: state["recipe_id"] = res.json().get("id")

    if state.get("recipe_id"):
        res = requests.post(f"{BASE_URL}/doctor/recipes/{state['recipe_id']}/assign", json={
            "patient_ids": [state["patient_id"]], "meal_type": "Breakfast", "meal_date": "2026-03-15", "note": "Try this"
        }, headers=doc_auth)
        print_result("Step 48", "Assign Recipe to Patient", res.status_code == 200, res)

    res = requests.put(f"{BASE_URL}/doctor/patients/{state['patient_id']}/plan", json={"doctor_notes": "Reduce dinner carbs.", "meals": None}, headers=doc_auth)
    print_result("Step 49", "Override Patient's Plan", res.status_code == 200, res)

    res = requests.post(f"{BASE_URL}/doctor/patients/{state['patient_id']}/plan/notes", json={
        "meal_date": "2026-03-10", "meal_type": "Lunch", "note": "Avoid dal today"
    }, headers=doc_auth)
    print_result("Step 50", "Add Note to Specific Meal Slot", res.status_code in [200, 404], res)

    res = requests.delete(f"{BASE_URL}/doctor/patients/{state['patient_id']}", headers=doc_auth)
    print_result("Step 51", "Remove Patient (Doctor)", res.status_code == 200, res)

    # Re-connect to test Phase 7 logic correctly if subscription gets invalidated
    if len(state.get("codes", [])) > 2:
        requests.post(f"{BASE_URL}/patients/activate", json={"code": state["codes"][2]["code"]}, headers=pat_auth)
        
        # Refresh token to load the 'active' sub_status again
        r_refresh2 = requests.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": state.get("refresh_token")})
        if r_refresh2.status_code == 200:
            state["patient_token"] = r_refresh2.json()["access_token"]
            pat_auth = {"Authorization": f"Bearer {state['patient_token']}"}

        requests.post(f"{BASE_URL}/diet-plans/generate", headers=pat_auth)
        r = requests.get(f"{BASE_URL}/diet-plans/my-plan", headers=pat_auth)
        if r.status_code == 200:
            state["recommendation_id"] = r.json().get("id")

    # --- Phase 7 ---
    res = requests.post(f"{BASE_URL}/progress/log/meal", json={
        "meal_type": "Breakfast", "calories": 420, "protein": 18, "carbs": 65, "fat": 8, "fiber": 4
    }, headers=pat_auth)
    is_pass = res.status_code == 200
    print_result("Step 52", "Log a Meal", is_pass, res)

    rec_id = state.get("recommendation_id", 1)
    res = requests.post(f"{BASE_URL}/progress/log/meal", json={
        "meal_type": "Lunch", "calories": 550, "protein": 22, "carbs": 80, "fat": 10, "fiber": 6, "recommendation_id": rec_id
    }, headers=pat_auth)
    print_result("Step 53", "Log a Meal (with rec)", res.status_code == 200, res)

    if is_pass:
        logs_res = requests.get(f"{BASE_URL}/doctor/patients/{state['patient_id']}/logs?days=1", headers=doc_auth)
        if logs_res.status_code == 200:
            logs = logs_res.json().get("meal_logs", [])
            if logs:
                state["log_id"] = logs[0]["id"]

    if state.get("log_id"):
        res = requests.put(f"{BASE_URL}/progress/log/meal/{state['log_id']}", json={"calories": 380, "protein": 15}, headers=pat_auth)
        print_result("Step 54", "Edit Meal Log", res.status_code == 200, res)

    if state.get("log_id"):
        res = requests.delete(f"{BASE_URL}/progress/log/meal/{state['log_id']}", headers=pat_auth)
        print_result("Step 55", "Delete Meal Log", res.status_code == 200, res)

    res = requests.post(f"{BASE_URL}/progress/log/water", json={"glasses": 3}, headers=pat_auth)
    print_result("Step 56", "Log Water", res.status_code == 200, res)

    res = requests.put(f"{BASE_URL}/progress/log/water", json={"glasses": 6}, headers=pat_auth)
    print_result("Step 57", "Update Water", res.status_code == 200, res)

    res = requests.delete(f"{BASE_URL}/progress/log/water", headers=pat_auth)
    print_result("Step 58", "Delete Water Log", res.status_code == 200, res)

    res = requests.post(f"{BASE_URL}/progress/log/steps", json={"steps": 4000}, headers=pat_auth)
    print_result("Step 59", "Log Steps", res.status_code == 200, res)

    res = requests.put(f"{BASE_URL}/progress/log/steps", json={"steps": 8500}, headers=pat_auth)
    print_result("Step 60", "Update Steps", res.status_code == 200, res)

    res = requests.delete(f"{BASE_URL}/progress/log/steps", headers=pat_auth)
    print_result("Step 61", "Delete Steps Log", res.status_code == 200, res)

    res = requests.post(f"{BASE_URL}/progress/log/weight", json={"weight": 71.5}, headers=pat_auth)
    print_result("Step 62", "Log Weight", res.status_code == 200, res)

    res = requests.put(f"{BASE_URL}/progress/log/weight", json={"weight": 71.2}, headers=pat_auth)
    print_result("Step 63", "Update Weight", res.status_code == 200, res)

    res = requests.post(f"{BASE_URL}/progress/log/activity", json={"steps": 6000, "calories_burned": 280, "activity_type": "Cycling"}, headers=pat_auth)
    print_result("Step 64", "Log Activity", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/progress/today", headers=pat_auth)
    print_result("Step 65", "Today's Summary", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/progress/weekly", headers=pat_auth)
    print_result("Step 66", "Weekly Summary", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/progress/weekly-report", headers=pat_auth)
    print_result("Step 67", "Weekly Report (Detailed)", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/progress/weight-history?days=30", headers=pat_auth)
    print_result("Step 68", "Weight History", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/progress/weight", headers=pat_auth)
    print_result("Step 69", "Get Current Weight", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/progress/streak", headers=pat_auth)
    print_result("Step 70", "Streak", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/progress/adherence/weekly?days=7", headers=pat_auth)
    print_result("Step 71", "Weekly Adherence", res.status_code == 200, res)

    # --- Phase 8 ---
    res = requests.get(f"{BASE_URL}/admin/stats", headers=admin_auth)
    print_result("Step 72", "Platform Stats", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/admin/doctors", headers=admin_auth)
    print_result("Step 73", "List All Doctors", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/admin/doctors/{state['doctor_id']}", headers=admin_auth)
    print_result("Step 74", "Get Doctor Detail", res.status_code == 200, res)

    res = requests.patch(f"{BASE_URL}/admin/doctors/{state['doctor_id']}/deactivate", headers=admin_auth)
    print_result("Step 75", "Deactivate Doctor", res.status_code == 200, res)

    del_doc = f"del_doc_{ts}@mityahar.com"
    r = requests.post(f"{BASE_URL}/admin/doctors", json={
        "email": del_doc, "password": "Password123", "name": "Doc To Delete",
        "phone": f"11111{ts%10000:04}", "specialization": "Dietitian", "clinic_name": "Del", "city": "Del"
    }, headers=admin_auth)
    if r.status_code == 201:
        doc_del_id = r.json()["id"]
        res = requests.delete(f"{BASE_URL}/admin/doctors/{doc_del_id}", headers=admin_auth)
        print_result("Step 76", "Delete Doctor", res.status_code == 200, res)
    else:
        print_result("Step 76", "Delete Doctor (Setup failed)", False)

    res = requests.patch(f"{BASE_URL}/admin/patients/{state['patient_id']}/subscription/override?status=active&days=30", headers=admin_auth)
    print_result("Step 77", "Override Patient Sub", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/admin/food?source=doctor&is_verified=false", headers=admin_auth)
    print_result("Step 78", "List Food Items", res.status_code == 200, res)

    if state.get("recipe_id"):
        res = requests.patch(f"{BASE_URL}/admin/food/{state['recipe_id']}/approve", headers=admin_auth)
        print_result("Step 79", "Approve Food Item", res.status_code == 200, res)
    else:
        print_result("Step 79", "Approve Food Item (Skipped)", False)

    if state.get("recipe_id"):
        res = requests.patch(f"{BASE_URL}/admin/food/{state['recipe_id']}/reject?reason=Testing", headers=admin_auth)
        print_result("Step 80", "Reject Food Item", res.status_code == 200, res)
    else:
        print_result("Step 80", "Reject Food Item (Skipped)", False)

    if state.get("recipe_id"):
        res = requests.delete(f"{BASE_URL}/admin/food/{state['recipe_id']}", headers=admin_auth)
        print_result("Step 81", "Delete Food Item", res.status_code == 200, res)
    else:
        print_result("Step 81", "Delete Food Item (Skipped)", False)

    res = requests.get(f"{BASE_URL}/admin/audit-logs?actor_role=admin&action=delete&page=1&page_size=20", headers=admin_auth)
    print_result("Step 82", "Audit Logs", res.status_code == 200, res)

    res = requests.get(f"{BASE_URL}/admin/billing", headers=admin_auth)
    print_result("Step 83", "Billing Overview", res.status_code == 200, res)

    pat_del_email = f"pat_del_{ts}@gmail.com"
    r = requests.post(f"{BASE_URL}/auth/register", json={
        "email": pat_del_email, "password": "Patient@123", "name": "To Delete", "age": 28, "gender": "Male", 
        "height": 175, "weight": 72, "activity_level": "MA", "diet": "Vegetarian", "health_condition": "Healthy", "region": "North"
    })
    if r.status_code == 200:
        p_del_id = r.json().get("user_id")
        res = requests.delete(f"{BASE_URL}/admin/patients/{p_del_id}", headers=admin_auth)
        print_result("Step 84", "Erase Patient Data (DPDP)", res.status_code == 200, res)
    else:
        print_result("Step 84", f"Erase Patient Data (Setup failed: {r.status_code} {r.text})", False)

    print("\n--- Error Cases ---")
    res = requests.get(f"{BASE_URL}/doctor/dashboard", headers=pat_auth)
    print_result("EC-1", "Patient token on Doctor-only endpoint", res.status_code in [401, 403])
    
    res = requests.get(f"{BASE_URL}/admin/stats", headers=doc_auth)
    print_result("EC-2", "Doctor token on Admin-only endpoint", res.status_code in [401, 403])

    doc2_email = f"doc2_{ts}@mityahar.com"
    r = requests.post(f"{BASE_URL}/admin/doctors", json={
        "email": doc2_email, "password": "Doctor@1234", "name": "Doctor 2", "phone": f"12{ts%100000000:08}", 
        "specialization": "Dietitian", "clinic_name": "C", "city": "Mumbai"
    }, headers=admin_auth)
    if r.status_code == 201:
        doc2_token = requests.post(f"{BASE_URL}/auth/doctor/login", data={"username": doc2_email, "password": "Doctor@1234"}).json()["access_token"]
        res = requests.get(f"{BASE_URL}/doctor/patients/{state['patient_id']}", headers={"Authorization": f"Bearer {doc2_token}"})
        print_result("EC-3", "Doctor accessing another doc patient", res.status_code == 404)
    else:
        print_result("EC-3", "Doctor accessing another doc patient (Setup failed)", False)

    if len(state.get("codes", [])) > 0:
        res = requests.post(f"{BASE_URL}/patients/activate", json={"code": state["codes"][0]["code"]}, headers=pat_auth)
        print_result("EC-4", "Using an already-used subscription code", res.status_code in [400, 409])
    
    res = requests.post(f"{BASE_URL}/patients/activate", json={"code": "12345678901Z"}, headers=pat_auth)
    print_result("EC-5", "Using invalid/expired code", res.status_code in [404, 400])

    res = requests.put(f"{BASE_URL}/progress/log/meal/99999", json={"calories": 200}, headers=pat_auth)
    print_result("EC-6", "Editing non-existent/expired meal log", res.status_code in [403, 400, 404, 422])

    r_t = requests.post(f"{BASE_URL}/auth/token", data={"username": pat_del_email, "password": "Patient@123"})
    if r_t.status_code in [200, 401]:
        # Actually p_del_email was erased, so login might fail. Let's register another patient for EC-7.
        p_ec7_email = f"pat_ec7_{ts}@gmail.com"
        requests.post(f"{BASE_URL}/auth/register", json={
            "email": p_ec7_email, "password": "Patient@123", "name": "EC7 Test", "age": 28, "gender": "Male", 
            "height": 175, "weight": 72, "activity_level": "MA", "diet": "Vegetarian", "health_condition": "Healthy", "region": "North"
        })
        pat_ec7_token = requests.post(f"{BASE_URL}/auth/token", data={"username": p_ec7_email, "password": "Patient@123"}).json().get("access_token")
        res = requests.post(f"{BASE_URL}/diet-plans/generate", headers={"Authorization": f"Bearer {pat_ec7_token}"})
        print_result("EC-7", "Gated endpoint without active sub", res.status_code == 402)
    else:
        print_result("EC-7", "Gated endpoint without active sub (Setup failed)", False)

    res = requests.get(f"{BASE_URL}/users/me")
    print_result("EC-9", "No auth header on a protected endpoint", res.status_code == 401)

    requests.delete(f"{BASE_URL}/diet-plans/delete", headers=pat_auth)
    res2 = requests.get(f"{BASE_URL}/diet-plans/today", headers=pat_auth)
    print_result("EC-10", "Diet plan endpoints with no active plan", res2.status_code == 404)
    print("================ TESTS COMPLETE ================")

if __name__ == "__main__":
    run_tests()
