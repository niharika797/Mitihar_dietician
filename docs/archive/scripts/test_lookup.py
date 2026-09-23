import requests

# Step 1: Login as doctor to get token
login_resp = requests.post(
    "http://localhost:8000/api/v1/auth/doctor/login",
    json={"email": "doctor@example.com", "password": "doctor123"}
)

if login_resp.status_code != 200:
    print(f"Login failed: {login_resp.status_code} {login_resp.text}")
    exit(1)

token = login_resp.json()["access_token"]
print(f"✓ Got token: {token[:20]}...")

# Step 2: Test the lookup endpoint
lookup_resp = requests.post(
    "http://localhost:8000/api/v1/doctor/recipes/lookup",
    headers={"Authorization": f"Bearer {token}"},
    json={"food_name": "Aloo Paratha"}
)

print(f"\n{'='*60}")
print(f"Status: {lookup_resp.status_code}")
print(f"Response:\n{lookup_resp.text}")
print(f"{'='*60}")
