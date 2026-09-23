import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as s:
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(days=30)
        await s.execute(
            text("""
                UPDATE patients SET
                    subscription_status = 'active',
                    token_1 = 'TKN1-PAT-AUDIT',
                    token_1_expiry = :expiry,
                    weight_kg = 65,
                    height_cm = 165,
                    target_weight_kg = 60,
                    bmi = 23.88,
                    bmr = 1380.25,
                    tdee = 2139.39,
                    gender = 'female',
                    activity_level = 'MA',
                    diet_type = 'Vegetarian',
                    region = 'North',
                    health_condition = 'Healthy',
                    health_goals = '["weight_loss"]',
                    medical_conditions = '[]',
                    food_allergies = '[]',
                    disclaimer_accepted_at = :now,
                    date_of_birth = '1998-04-15'
                WHERE email = 'testaudit@mityahar.com'
            """),
            {"expiry": expiry, "now": now}
        )
        await s.commit()
        r = await s.execute(text("SELECT id, subscription_status, token_1, weight_kg, bmi FROM patients WHERE email='testaudit@mityahar.com'"))
        print(dict(zip(r.keys(), r.fetchone())))

asyncio.run(main())
