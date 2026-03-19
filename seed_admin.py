"""
seed_admin.py — Creates the initial admin account.

Password is read from ADMIN_SEED_PASSWORD environment variable.
NEVER hardcode credentials in source files.

Usage:
    set ADMIN_SEED_PASSWORD=your-strong-password
    venv\Scripts\python seed_admin.py
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_SEED_EMAIL", "admin@mityahar.com")
ADMIN_PASSWORD = os.getenv("ADMIN_SEED_PASSWORD")
ADMIN_NAME = os.getenv("ADMIN_SEED_NAME", "Super Admin")

if not ADMIN_PASSWORD:
    raise RuntimeError(
        "ADMIN_SEED_PASSWORD is not set.\n"
        "Set it in your .env file or as an environment variable before running:\n"
        "  ADMIN_SEED_PASSWORD=your-strong-password venv\\Scripts\\python seed_admin.py"
    )

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.db_models import Admin


async def seed():
    async with AsyncSessionLocal() as s:
        s.add(Admin(
            email=ADMIN_EMAIL,
            hashed_password=get_password_hash(ADMIN_PASSWORD),
            name=ADMIN_NAME,
        ))
        await s.commit()
    print(f"Admin created: {ADMIN_EMAIL}")


asyncio.run(seed())
