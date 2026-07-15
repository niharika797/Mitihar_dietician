"""
Admin API live verification — 2026-04-04
Covers Steps 1-7 as specified in the QA task.
"""
import json
import requests

BASE = "http://localhost:8000"
ADMIN_EMAIL = "admin@mityahar.com"
ADMIN_PASS = "Mityahar@2026"
PATIENT_EMAIL = "admin.crosstest.qa@gmail.com"
PATIENT_PASS = "CrossTest@2026"
DOCTOR_EMAIL = "dr.ashok.mehta@mitihar.test"
DOCTOR_PASS = "DoctorTest@2026"

results = []

def record(num, endpoint, method, status, expected, ok, notes=""):
    tag = "PASS" if ok else "FAIL"
    results.append({
        "num": num,
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "expected": expected,
        "result": tag,
        "notes": notes,
    })
    print(f"[{tag}] #{num} {method} {endpoint} → {status} (expected {expected}) | {notes[:120]}")

# ─── STEP 1: Admin Login ──────────────────────────────────────────────────────
print("\n=== STEP 1: Admin Login ===")
r = requests.post(
    f"{BASE}/api/v1/auth/admin/login",
    data={"username": ADMIN_EMAIL, "password": ADMIN_PASS},
)
ok = r.status_code == 200
admin_token = None
if ok:
    body = r.json()
    admin_token = body.get("access_token")
    record(1, "/api/v1/auth/admin/login", "POST", r.status_code, 200, ok,
           f"token_type={body.get('token_type')} mfa_required={body.get('mfa_required', False)}")
else:
    record(1, "/api/v1/auth/admin/login", "POST", r.status_code, 200, ok, r.text[:200])
    print("FATAL: Cannot proceed without admin token.")
    import sys; sys.exit(1)

ADMIN_HEADERS = {"Authorization": f"Bearer {admin_token}"}

# ─── STEP 2: IP Whitelist Verification ────────────────────────────────────────
print("\n=== STEP 2: IP Whitelist / Stats ===")
r = requests.get(f"{BASE}/api/v1/admin/stats", headers=ADMIN_HEADERS)
ok = r.status_code == 200
ip_notes = ""
if ok:
    body = r.json()
    ip_notes = (f"IP OK (127.0.0.1 allowed). patients={body.get('total_patients')} "
                f"doctors={body.get('total_doctors')} active_subs={body.get('active_subscriptions')} "
                f"plans={body.get('total_plans_generated')}")
elif r.status_code == 403 and "IP" in r.text:
    ip_notes = "IP NOT WHITELISTED — 127.0.0.1 blocked. Fix needed."
else:
    ip_notes = r.text[:200]
record(2, "/api/v1/admin/stats", "GET", r.status_code, 200, ok, ip_notes)

# ─── STEP 3: Patient & Doctor Management ──────────────────────────────────────
print("\n=== STEP 3: Patient & Doctor Management ===")

# 3a: List patients
r = requests.get(f"{BASE}/api/v1/admin/patients", headers=ADMIN_HEADERS)
ok = r.status_code == 200
patient_id = None
if ok:
    body = r.json()
    total = body.get("total", 0)
    patients = body.get("patients", [])
    if patients:
        patient_id = patients[0].get("id")
    record(3, "/api/v1/admin/patients", "GET", r.status_code, 200, ok,
           f"total={total} page_size={body.get('page_size')} first_id={patient_id}")
else:
    record(3, "/api/v1/admin/patients", "GET", r.status_code, 200, ok, r.text[:200])

# 3b: List doctors
r = requests.get(f"{BASE}/api/v1/admin/doctors", headers=ADMIN_HEADERS)
ok = r.status_code == 200
doctor_id = None
if ok:
    body = r.json()
    if isinstance(body, list) and body:
        doctor_id = body[0].get("id")
    record(4, "/api/v1/admin/doctors", "GET", r.status_code, 200, ok,
           f"count={len(body) if isinstance(body, list) else '?'} first_id={doctor_id}")
else:
    record(4, "/api/v1/admin/doctors", "GET", r.status_code, 200, ok, r.text[:200])

# 3c: Fetch one doctor detail
if doctor_id:
    r = requests.get(f"{BASE}/api/v1/admin/doctors/{doctor_id}", headers=ADMIN_HEADERS)
    ok = r.status_code == 200
    body = r.json() if ok else {}
    record(5, f"/api/v1/admin/doctors/{{id}}", "GET", r.status_code, 200, ok,
           f"id={doctor_id} name={body.get('name','?')} patient_count={body.get('patient_count','?')}")
else:
    record(5, "/api/v1/admin/doctors/{id}", "GET", "N/A", 200, False, "No doctor_id available")

# 3d: Patients pagination check
r = requests.get(f"{BASE}/api/v1/admin/patients?page=1&page_size=5", headers=ADMIN_HEADERS)
ok = r.status_code == 200
if ok:
    body = r.json()
    record(6, "/api/v1/admin/patients?page=1&page_size=5", "GET", r.status_code, 200, ok,
           f"total={body.get('total')} returned={len(body.get('patients',[]))} page={body.get('page')}")
else:
    record(6, "/api/v1/admin/patients?page=1&page_size=5", "GET", r.status_code, 200, ok, r.text[:200])

# ─── STEP 4: Subscription / Token Management ──────────────────────────────────
print("\n=== STEP 4: Subscription / Token Management ===")

# 4a: List all codes
r = requests.get(f"{BASE}/api/v1/admin/codes", headers=ADMIN_HEADERS)
ok = r.status_code == 200
if ok:
    body = r.json()
    code_count = len(body)
    unused = sum(1 for c in body if not c.get("is_used"))
    record(7, "/api/v1/admin/codes", "GET", r.status_code, 200, ok,
           f"count={code_count} unused={unused}")
else:
    record(7, "/api/v1/admin/codes", "GET", r.status_code, 200, ok, r.text[:200])

# 4b: Codes filtered by is_used=false
r = requests.get(f"{BASE}/api/v1/admin/codes?is_used=false", headers=ADMIN_HEADERS)
ok = r.status_code == 200
if ok:
    body = r.json()
    all_unused = all(not c.get("is_used") for c in body)
    record(8, "/api/v1/admin/codes?is_used=false", "GET", r.status_code, 200, ok,
           f"count={len(body)} all_unused={all_unused}")
else:
    record(8, "/api/v1/admin/codes?is_used=false", "GET", r.status_code, 200, ok, r.text[:200])

# 4c: Billing overview
r = requests.get(f"{BASE}/api/v1/admin/billing", headers=ADMIN_HEADERS)
ok = r.status_code == 200
if ok:
    body = r.json()
    record(9, "/api/v1/admin/billing", "GET", r.status_code, 200, ok,
           f"total_codes={body.get('total_codes_issued')} used={body.get('total_codes_used')} "
           f"doctors_count={len(body.get('doctors', []))}")
else:
    record(9, "/api/v1/admin/billing", "GET", r.status_code, 200, ok, r.text[:200])

# 4d: Subscription override — non-existent patient should 404
r = requests.patch(
    f"{BASE}/api/v1/admin/patients/999999/subscription/override?status=active&days=1",
    headers=ADMIN_HEADERS,
)
ok = r.status_code == 404
record(10, "/api/v1/admin/patients/999999/subscription/override", "PATCH", r.status_code, 404, ok,
       f"Non-existent patient returns 404: {r.json().get('detail','') if ok else r.text[:80]}")

# ─── STEP 5: Audit Logs ───────────────────────────────────────────────────────
print("\n=== STEP 5: Audit Logs ===")
r = requests.get(f"{BASE}/api/v1/admin/audit-logs", headers=ADMIN_HEADERS)
ok = r.status_code == 200
if ok:
    body = r.json()
    logs = body.get("logs", [])
    total = body.get("total", 0)
    fields_ok = False
    create_doctor_found = False
    deactivate_doctor_found = False
    recent_admin_action = None
    if logs:
        first = logs[0]
        required_fields = {"id", "actor_id", "actor_role", "action", "created_at"}
        fields_ok = required_fields.issubset(set(first.keys()))
        recent_admin_action = first.get("action")
        for log in logs:
            if log.get("action") == "create_doctor":
                create_doctor_found = True
            if log.get("action") == "deactivate_doctor":
                deactivate_doctor_found = True
    record(11, "/api/v1/admin/audit-logs", "GET", r.status_code, 200, ok,
           f"total={total} returned={len(logs)} fields_ok={fields_ok} "
           f"recent_action='{recent_admin_action}' create_doctor={create_doctor_found}")
else:
    record(11, "/api/v1/admin/audit-logs", "GET", r.status_code, 200, ok, r.text[:200])

# Audit log filter by actor_role=admin
r = requests.get(f"{BASE}/api/v1/admin/audit-logs?actor_role=admin&page_size=10",
                 headers=ADMIN_HEADERS)
ok = r.status_code == 200
if ok:
    body = r.json()
    all_admin = all(l.get("actor_role") == "admin" for l in body.get("logs", []))
    record(12, "/api/v1/admin/audit-logs?actor_role=admin", "GET", r.status_code, 200, ok,
           f"returned={len(body.get('logs',[]))} all_actor_role_admin={all_admin}")
else:
    record(12, "/api/v1/admin/audit-logs?actor_role=admin", "GET", r.status_code, 200, ok, r.text[:200])

# ─── STEP 6: Cross-Role Protection ────────────────────────────────────────────
print("\n=== STEP 6: Cross-Role Protection ===")

# 6a: Use an existing known throwaway patient (registered in a prior run)
# PATIENT_EMAIL = admin.crosstest.qa@gmail.com is already in DB
reg_note = "register=SKIP(existing account used)"

# 6b: Login as patient
r_tok = requests.post(
    f"{BASE}/api/v1/auth/token",
    data={"username": PATIENT_EMAIL, "password": PATIENT_PASS},
)
patient_token = None
if r_tok.status_code == 200:
    patient_token = r_tok.json().get("access_token")
    reg_note += " login=200"
else:
    reg_note += f" login={r_tok.status_code} {r_tok.text[:80]}"

if patient_token:
    r = requests.get(
        f"{BASE}/api/v1/admin/patients",
        headers={"Authorization": f"Bearer {patient_token}"},
    )
    ok = r.status_code in (401, 403)
    try:
        detail = r.json().get("detail", "")
    except Exception:
        detail = r.text[:80]
    record(13, "/api/v1/admin/patients (patient JWT)", "GET", r.status_code, "401/403", ok,
           f"{reg_note} → cross-role blocked={ok} detail='{detail}'")
else:
    record(13, "/api/v1/admin/patients (patient JWT)", "GET", "N/A", "401/403", False,
           f"Could not obtain patient token: {reg_note}")

# 6c: Doctor login
r_doc = requests.post(
    f"{BASE}/api/v1/auth/doctor/login",
    data={"username": DOCTOR_EMAIL, "password": DOCTOR_PASS},
)
doctor_token = None
if r_doc.status_code == 200:
    doc_body = r_doc.json()
    doctor_token = doc_body.get("access_token")
    doc_note = f"doctor login=200 mfa_required={doc_body.get('mfa_required', False)}"
else:
    doc_note = f"doctor login={r_doc.status_code}: {r_doc.text[:100]}"

if doctor_token:
    r = requests.get(
        f"{BASE}/api/v1/admin/patients",
        headers={"Authorization": f"Bearer {doctor_token}"},
    )
    ok = r.status_code in (401, 403)
    try:
        detail = r.json().get("detail", "")
    except Exception:
        detail = r.text[:80]
    record(14, "/api/v1/admin/patients (doctor JWT)", "GET", r.status_code, "401/403", ok,
           f"{doc_note} → cross-role blocked={ok} detail='{detail}'")
else:
    record(14, "/api/v1/admin/patients (doctor JWT)", "GET", "N/A", "401/403", False, doc_note)

# ─── STEP 7: Food Database ────────────────────────────────────────────────────
print("\n=== STEP 7: Food Database ===")
r = requests.get(f"{BASE}/api/v1/admin/food", headers=ADMIN_HEADERS)
ok = r.status_code == 200
if ok:
    body = r.json()
    record(15, "/api/v1/admin/food", "GET", r.status_code, 200, ok,
           f"count={len(body)} (page 1, page_size=50 default)")
else:
    record(15, "/api/v1/admin/food", "GET", r.status_code, 200, ok, r.text[:200])

# Food with filter
r = requests.get(f"{BASE}/api/v1/admin/food?is_verified=true&page_size=5", headers=ADMIN_HEADERS)
ok = r.status_code == 200
if ok:
    body = r.json()
    all_verified = all(f.get("is_verified") for f in body)
    record(16, "/api/v1/admin/food?is_verified=true", "GET", r.status_code, 200, ok,
           f"count={len(body)} all_verified={all_verified}")
else:
    record(16, "/api/v1/admin/food?is_verified=true", "GET", r.status_code, 200, ok, r.text[:200])

# Non-existent food approve — should 404
r = requests.patch(f"{BASE}/api/v1/admin/food/999999/approve", headers=ADMIN_HEADERS)
ok = r.status_code == 404
record(17, "/api/v1/admin/food/999999/approve", "PATCH", r.status_code, 404, ok,
       f"Non-existent food 404 guard: {r.text[:80]}")

# ─── Summary ──────────────────────────────────────────────────────────────────
print("\n=== SUMMARY ===")
pass_count = sum(1 for r in results if r["result"] == "PASS")
fail_count = sum(1 for r in results if r["result"] == "FAIL")
skip_count = sum(1 for r in results if r["result"] == "SKIP")
print(f"Total: {len(results)} | PASS: {pass_count} | FAIL: {fail_count} | SKIP: {skip_count}")

# Dump raw JSON for log writing
print("\n=== RAW JSON ===")
print(json.dumps(results, indent=2))
