import asyncio
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

async def main():
    async with AsyncSessionLocal() as s:
        r = await s.execute(
            text("SELECT id, email, name, subscription_status, token_1, weight_kg, bmi FROM patients WHERE email=:e"),
            {"e": "testaudit@mityahar.com"}
        )
        row = r.fetchone()
        if row:
            print(dict(zip(r.keys(), row)))
        else:
            print("no patient found")

asyncio.run(main())
