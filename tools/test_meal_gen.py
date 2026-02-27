import requests
import json
import sys

base_url = "http://localhost:8000/api/v1"

auth_data = {"username": "test@test.com", "password": "test123"}
res = requests.post(f"{base_url}/auth/token", data=auth_data)
if res.status_code != 200:
    print("Error getting token:", res.text)
    sys.exit(1)

token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
res = requests.get(f"{base_url}/diet-plans/my-plan", headers=headers)

if res.status_code != 200:
    print("Fetch Error:", res.text)
    sys.exit(1)

plan = res.json()
with open("meal_recommendation_output.json", "w") as f:
    json.dump(plan, f, indent=2)

print("Meal plan saved to meal_recommendation_output.json")
