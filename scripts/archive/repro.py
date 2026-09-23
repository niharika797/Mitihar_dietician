import asyncio
from app.main import app
from httpx import AsyncClient

async def main():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        res = await ac.post("/api/v1/auth/admin/login", data={"username": "admin@mityahar.com", "password": "admin1234"})
        admin_token = res.json()["access_token"]
        print("Admin:", res.status_code)
        
        pat_email = "test8123281@gmail.com"
        res = await ac.post("/api/v1/auth/register", json={
            "email": pat_email, "password": "Patient@123", "name": "Rahul",
            "age": 28, "gender": "Male", "height": 175, "weight": 72, "activity_level": "MA", 
            "diet": "Vegetarian", "health_condition": "Healthy", "region": "North"
        })
        print("Pat reg:", res.status_code)
        
        pat_token = (await ac.post("/api/v1/auth/token", data={"username": pat_email, "password": "Patient@123"})).json()["access_token"]
        pat_auth = {"Authorization": f"Bearer {pat_token}"}
        
        doc_email = "doc8123282@gmail.com"
        res_doc = await ac.post("/api/v1/admin/doctors", json={
            "email": doc_email, "password": "Doctor@1234", "name": "Dr. Priya Mehta",
            "phone": "987111222", "specialization": "Dietitian", "clinic_name": "Healthy Roots", "city": "Mumbai"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        doc_id = res_doc.json()["id"]
        
        res = await ac.post("/api/v1/patients/request-doctor", json={"doctor_id": doc_id}, headers=pat_auth)
        print("Request Doc:", res.status_code)
        print(res.text)

if __name__ == "__main__":
    asyncio.run(main())
