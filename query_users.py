import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.db_models import Doctor, Admin

async def query():
    async with AsyncSessionLocal() as s:
        doc_res = await s.execute(select(Doctor))
        doctors = doc_res.scalars().all()
        print("Doctors:")
        for doc in doctors:
            print(f"ID: {doc.id}, Email: {doc.email}, Name: {doc.name}")
            
        admin_res = await s.execute(select(Admin))
        admins = admin_res.scalars().all()
        print("Admins:")
        for adm in admins:
            print(f"ID: {adm.id}, Email: {adm.email}, Name: {adm.name}")

if __name__ == "__main__":
    asyncio.run(query())
