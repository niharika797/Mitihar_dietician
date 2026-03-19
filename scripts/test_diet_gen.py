import asyncio
import requests
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.db_models import Patient
from app.core.security import create_access_token

async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Patient).where(Patient.is_active == True).limit(1)
        )
        patient = result.scalar_one_or_none()
        if not patient:
            print("No active patients found in local DB.")
            return

        print(f"Patient: {patient.email}")

        token_data = {
            "sub": patient.email,
            "role": "patient",
            "user_type": patient.user_type or "standalone",
            "sub_status": patient.subscription_status or "inactive",
            "patient_id": patient.id,
        }
        token = create_access_token(data=token_data)

        print("Calling /generate ...")
        resp = requests.post(
            "http://127.0.0.1:8000/api/v1/diet-plans/generate",
            headers={"Authorization": f"Bearer {token}"},
            timeout=120,
        )
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            meals = data.get("meals", [])
            checklist = data.get("ingredient_checklist", [])
            print(f"Meals count: {len(meals)}")
            print(f"Ingredient checklist count: {len(checklist)}")
            if meals:
                print(f"First meal: {meals[0]}")
            print("SUCCESS: Diet plan generated!")
        else:
            print(f"FAILED: {resp.text[:300]}")

if __name__ == "__main__":
    asyncio.run(main())
