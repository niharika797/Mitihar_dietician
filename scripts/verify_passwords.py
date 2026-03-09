import asyncio
import os
import asyncpg
from dotenv import load_dotenv

# Instead of using passlib directly (since it had issues with bcrypt earlier),
# we will use the application's actual security module (which monkeypatches bcrypt)
import bcrypt
import app.core.security as security

load_dotenv()

async def run():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    admin_row = await conn.fetchrow("SELECT hashed_password FROM admins WHERE email='admin@mityahar.com'")
    if admin_row:
        try:
            match = security.verify_password('admin123', admin_row['hashed_password'])
            print(f"Admin 'admin123' match: {match}")
        except Exception as e:
            print(f"Error checking admin: {e}")
    else:
        print("Admin email not found in admins table!")
        
    doctor_row = await conn.fetchrow("SELECT hashed_password FROM doctors WHERE email='testdoctor@mityahar.com'")
    if doctor_row:
        try:
            match = security.verify_password('password123', doctor_row['hashed_password'])
            print(f"Doctor 'password123' match: {match}")
        except Exception as e:
            print(f"Error checking doctor: {e}")
    else:
        print("Doctor email not found in doctors table!")
        
    await conn.close()

if __name__ == '__main__':
    asyncio.run(run())
