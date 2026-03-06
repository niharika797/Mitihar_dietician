import asyncio
from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.db_models import Admin
async def seed():
    async with AsyncSessionLocal() as s:
        s.add(Admin(email='admin@mityahar.com', hashed_password=get_password_hash('admin1234'), name='Super Admin'))
        await s.commit()
asyncio.run(seed())
