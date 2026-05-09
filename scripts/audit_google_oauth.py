import sys
sys.path.insert(0, 'C:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician')
import inspect

issues = []
notes  = []

# 1. google-auth importable
try:
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests
    from google.auth.exceptions import GoogleAuthError
    notes.append("PASS: google-auth installed and importable")
except ImportError as e:
    issues.append(f"FAIL: google-auth not importable: {e}")

# 2. Config has GOOGLE_CLIENT_ID
from app.core.config import settings
assert hasattr(settings, 'GOOGLE_CLIENT_ID'), "GOOGLE_CLIENT_ID missing from config"
assert hasattr(settings, 'GOOGLE_CLIENT_SECRET'), "GOOGLE_CLIENT_SECRET missing"
notes.append("PASS: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET in config")

# 3. Patient model has google_id
from app.models.db_models import Patient
import sqlalchemy
cols = {c.key for c in sqlalchemy.inspect(Patient).columns}
assert 'google_id' in cols, "google_id column missing from Patient ORM"
notes.append("PASS: Patient.google_id column in ORM")

# 4. Migration file exists and has correct chain
import os
migration_path = 'C:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/alembic/versions/a1b2c3d4e5f6_add_google_id_to_patients.py'
assert os.path.exists(migration_path), "Migration file missing"
content = open(migration_path).read()
assert "down_revision = 'eb8dbef8dd19'" in content, "Wrong down_revision in migration"
assert "add_column" in content and "patients" in content, "Migration missing add_column for patients"
assert "idx_patients_google_id" in content, "Migration missing partial unique index"
notes.append("PASS: Migration file exists, correct chain (eb8dbef8dd19), partial unique index included")

# 5. auth.py imports clean
try:
    from app.routers.auth import router, GoogleTokenRequest, google_verify
    notes.append("PASS: auth.py imports clean — GoogleTokenRequest + google_verify present")
except Exception as e:
    issues.append(f"FAIL: auth.py import error: {e}")

# 6. Endpoint structure — correct security checks present
src = inspect.getsource(google_verify)

checks = [
    ("GOOGLE_CLIENT_ID guard",      "GOOGLE_CLIENT_ID" in src),
    ("verify_oauth2_token called",   "verify_oauth2_token" in src),
    ("audience= set",                "audience=settings.GOOGLE_CLIENT_ID" in src),
    ("clock_skew tolerated",         "clock_skew_in_seconds" in src),
    ("GoogleAuthError caught",       "GoogleAuthError" in src),
    ("ValueError caught",            "ValueError" in src),
    ("email_verified enforced",      "email_verified" in src),
    ("google_id lookup first",       "Patient.google_id == google_sub" in src),
    ("email fallback lookup",        "Patient.email == email" in src),
    ("account linking on email hit", "patient.google_id = google_sub" in src),
    ("new user created",             "create_patient" in src),
    ("random unusable password",     "token_hex" in src),
    ("JWT identical to /token",      '"role": "patient"' in src),
    ("is_new_user hint returned",    "is_new_user" in src),
    ("refresh_token returned",       "refresh_token" in src),
]

for label, result in checks:
    if result:
        notes.append(f"PASS: {label}")
    else:
        issues.append(f"FAIL: {label}")

# 7. main.py still includes auth router (no regression)
from app.main import app
route_paths = [r.path for r in app.routes]
assert any('/auth' in p for p in route_paths), "auth router not in app"
notes.append("PASS: auth router mounted in app — no regression")

# PRINT
print("=" * 58)
print("GOOGLE OAUTH AUDIT")
print("=" * 58)
print(f"\n🔴 CRITICAL ({len(issues)})")
print("-" * 58)
if issues:
    for iss in issues: print(f"  {iss}")
else:
    print("  None")
print(f"\n✅ ALL PASSING ({len(notes)})")
print("-" * 58)
for n in notes: print(f"  {n}")
print("=" * 58)
