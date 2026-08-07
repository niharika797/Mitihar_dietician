import asyncio, json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

DB = "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"

async def main():
    engine = create_async_engine(DB)
    async with AsyncSession(engine) as s:
        # 1. All tables
        r = await s.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY table_name"
        ))
        print("TABLES:", [row[0] for row in r.all()])

        # 2. Recommendation schema
        r = await s.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name='recommendations' ORDER BY ordinal_position"
        ))
        print("\nRECOMMENDATIONS SCHEMA:")
        for row in r.all():
            print(" ", row[0], "-", row[1])

        # 3. Priya's plans
        r = await s.execute(text(
            "SELECT id, patient_id, week_start_date, is_active, generated_by "
            "FROM recommendations WHERE patient_id=5 ORDER BY id DESC LIMIT 3"
        ))
        print("\nPRIYA PLANS (patient_id=5):", r.all())

        # 4. Full meals JSONB — latest active plan
        r = await s.execute(text(
            "SELECT id, meals FROM recommendations "
            "WHERE patient_id=5 AND is_active=true ORDER BY id DESC LIMIT 1"
        ))
        row = r.fetchone()
        if row:
            rec_id, meals = row[0], row[1]
            print(f"\nREC ID: {rec_id}  |  TOTAL MEALS: {len(meals)}")
            # Show all meals for the first date that has a Breakfast
            breakfast_dates = [m.get("Date") for m in meals if m.get("Meal Type") == "Breakfast"]
            if breakfast_dates:
                target_date = breakfast_dates[0]
                print(f"\nSHOWING ALL MEALS FOR DATE: {target_date}")
                for m in meals:
                    if m.get("Date") == target_date:
                        print("\n--- MEAL SLOT ---")
                        print(json.dumps(m, indent=2, default=str))

asyncio.run(main())
