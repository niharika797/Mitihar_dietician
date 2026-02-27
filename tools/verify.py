import httpx
import json

def run_verification():
    print("--- Verification API Checks ---")
    
    user_payload = {
        'email':'test_final@test.com',
        'name':'Test',
        'password':'test123',
        'age':30,
        'gender':'male',
        'height':175,
        'weight':75,
        'activity_level':'MA',
        'diet':'Vegetarian',
        'health_condition':'Healthy',
        'region':'North'
    }
    
    # Register
    print("1. Register user POST /api/v1/auth/register")
    try:
        res = httpx.post('http://localhost:8000/api/v1/auth/register', json=user_payload)
        print("   Result:", res.status_code, res.text)
    except Exception as e:
        print("   Error:", e)
        return

    # Login
    print("\n2. Login user POST /api/v1/auth/token")
    try:
        login = httpx.post('http://localhost:8000/api/v1/auth/token', data={'username':'test_final@test.com', 'password':'test123'})
        print("   Result:", login.status_code)
        if login.status_code != 200:
            print("   Response:", login.text)
            return
        token = login.json()['access_token']
    except Exception as e:
        print("   Error:", e)
        return

    # Generate
    print("\n3. Generate plan POST /api/v1/diet-plans/generate (Expected: 35 meals)")
    try:
        gen = httpx.post(
            'http://localhost:8000/api/v1/diet-plans/generate', 
            headers={'Authorization': f'Bearer {token}'}, 
            timeout=60.0
        )
        print("   Result:", gen.status_code)
        
        data = gen.json()
        if 'meals' in data:
            print(f"   Success! Generated {len(data['meals'])} meals.")
        else:
            print("   Unexpected Response:", json.dumps(data, indent=2))
            
    except Exception as e:
        print("   Error:", e)

if __name__ == '__main__':
    run_verification()
