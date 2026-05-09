"""
verify_passwords.py — Dev utility to check hashed passwords in the DB.
Reads test passwords from env vars — never hardcode credentials in source.

Usage:
    set VERIFY_ADMIN_PASSWORD=your-admin-password
    set VERIFY_DOCTOR_PASSWORD=your-doctor-password
    venv\Scripts\python scripts\verify_passwords.py
"""
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

import app.core.security as security

load_dotenv()

ADMIN_EMAIL   = os.getenv("ADMIN_SEED_EMAIL",    "admin@mityahar.com")
DOCTOR_EMAIL  = os.getenv("TEST_DOCTOR_EMAIL",   "testdoctor@mityahar.com")
ADMIN_PW      = os.getenv("VERIFY_ADMIN_PASSWORD")
DOCTOR_PW     = os.getenv("VERIFY_DOCTOR_PASSWORD")


async def run():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))

    if ADMIN_PW:
        row = await conn.fetchrow(
            "SELECT hashed_password FROM admins WHERE email=$1", ADMIN_EMAIL
        )
        if row:
            match = security.verify_password(ADMIN_PW, row["hashed_password"])
            print(f"Admin '{ADMIN_EMAIL}' password match: {match}")
        else:
            print(f"Admin '{ADMIN_EMAIL}' not found in DB")
    else:
        print("Skipping admin check — VERIFY_ADMIN_PASSWORD not set")

    if DOCTOR_PW:
        row = await conn.fetchrow(
            "SELECT hashed_password FROM doctors WHERE email=$1", DOCTOR_EMAIL
        )
        if row:
            match = security.verify_password(DOCTOR_PW, row["hashed_password"])
            print(f"Doctor '{DOCTOR_EMAIL}' password match: {match}")
        else:
            print(f"Doctor '{DOCTOR_EMAIL}' not found in DB")
    else:
        print("Skipping doctor check — VERIFY_DOCTOR_PASSWORD not set")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(run())
