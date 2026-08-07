import requests
BASE_URL = "http://localhost:8000/api/v1"
if __name__ == "__main__":
    res = requests.post(f"{BASE_URL}/auth/admin/login", data={"username": "admin@mityahar.com", "password": "admin1234"})
    admin_token = res.json()["access_token"]
    admin_auth = {"Authorization": f"Bearer {admin_token}"}

    import time
    ts = int(time.time())
    pat_email = f"test_{ts}@gmail.com"
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": pat_email, "password": "Patient@123", "name": "Rahul",
        "age": 28, "gender": "Male", "height": 175, "weight": 72, "activity_level": "MA", 
        "diet": "Vegetarian", "health_condition": "Healthy", "region": "North"
    })
    
    pat_token = requests.post(f"{BASE_URL}/auth/token", data={"username": pat_email, "password": "Patient@123"}).json()["access_token"]
    pat_auth = {"Authorization": f"Bearer {pat_token}"}
    
    doc_email = f"doc_{ts}@gmail.com"
    res_doc = requests.post(f"{BASE_URL}/admin/doctors", json={
        "email": doc_email, "password": "Doctor@1234", "name": "Dr. Priya Mehta",
        "phone": f"987{ts%1000000:06}", "specialization": "Dietitian", "clinic_name": "Healthy Roots", "city": "Mumbai"
    }, headers=admin_auth)
    doc_id = res_doc.json()["id"]
    
    res = requests.post(f"{BASE_URL}/patients/request-doctor", json={"doctor_id": doc_id}, headers=pat_auth)
    print("STATUS", res.status_code)
    try:
        print(res.json())
    except:
        print(res.text)
