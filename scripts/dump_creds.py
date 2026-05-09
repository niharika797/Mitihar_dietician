import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def run():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    
    rows = await conn.fetch("SELECT email, is_active FROM doctors")
    print("Doctors:")
    for r in rows:
        print(dict(r))
        
    rows = await conn.fetch("SELECT email, is_active FROM admins")
    print("Admins:")
    for r in rows:
        print(dict(r))
        
    await conn.close()

asyncio.run(run())
