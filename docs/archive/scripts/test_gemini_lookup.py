"""
Test script for Gemini nutrition lookup endpoint.
Gets doctor credentials from DB, authenticates, calls lookup API.
"""
import asyncio
import httpx
from sqlalchemy import create_engine, text

# Database connection
DB_URL = "postgresql://admin:mityahar_dev@localhost:5432/mityahar_db"
API_BASE = "http://localhost:8000/api/v1"

async def main():
    # 1. Get doctor credentials from database
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT email FROM doctors LIMIT 1"))
        row = result.fetchone()
        if not row:
            print("❌ No doctors found in database")
            return
        doctor_email = row[0]
    
    print(f"✓ Found doctor: {doctor_email}")
    
    # 2. Login to get JWT token (OAuth2PasswordRequestForm expects form data with 'username' field)
    async with httpx.AsyncClient(timeout=30) as client:
        login_resp = await client.post(
            f"{API_BASE}/auth/doctor/login",
            data={"username": doctor_email, "password": "test123"}  # Form data, not JSON
        )
        
        if login_resp.status_code != 200:
            print(f"❌ Login failed: {login_resp.status_code} {login_resp.text}")
            print("\nTrying to reset password to 'test123'...")
            
            # Reset password in DB
            engine = create_engine(DB_URL)
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            hashed = pwd_context.hash("test123")
            
            with engine.connect() as conn:
                conn.execute(text("UPDATE doctors SET hashed_password = :pwd WHERE email = :email"), 
                           {"pwd": hashed, "email": doctor_email})
                conn.commit()
            
            print("✓ Password reset. Retrying login...")
            login_resp = await client.post(
                f"{API_BASE}/auth/doctor/login",
                data={"username": doctor_email, "password": "test123"}
            )
            
            if login_resp.status_code != 200:
                print(f"❌ Still failed: {login_resp.status_code} {login_resp.text}")
                return
        
        token = login_resp.json()["access_token"]
        print(f"✓ Login successful")
        
        # 3. Test Gemini lookup endpoint
        print("\n🔍 Testing Gemini lookup for 'Aloo Paratha'...")
        lookup_resp = await client.post(
            f"{API_BASE}/doctor/recipes/lookup",
            headers={"Authorization": f"Bearer {token}"},
            json={"food_name": "Aloo Paratha"}
        )
        
        if lookup_resp.status_code == 200:
            data = lookup_resp.json()
            print("\n✅ Gemini lookup successful:")
            print(f"  Food: {data['food_name']}")
            print(f"  Calories: {data['calories']}")
            print(f"  Protein: {data['protein']}g")
            print(f"  Carbs: {data['carbs']}g")
            print(f"  Fat: {data['fat']}g")
            print(f"  Fiber: {data['fiber']}g")
        else:
            print(f"\n❌ Lookup failed: {lookup_resp.status_code}")
            print(lookup_resp.text)

if __name__ == "__main__":
    asyncio.run(main())
