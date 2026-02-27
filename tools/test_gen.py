import httpx
import json

def test_api():
    try:
        print("Registering...")
        res = httpx.post('http://localhost:8000/api/v1/auth/register', json={
            'email':'test7@test.com',
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
        })
        print('Register:', res.status_code, res.text)

        print("Logging in...")
        login = httpx.post('http://localhost:8000/api/v1/auth/token', data={'username':'test7@test.com', 'password':'test123'})
        print('Login:', login.status_code)
        token = login.json()['access_token']

        print("Generating...")
        gen = httpx.post('http://localhost:8000/api/v1/diet-plans/generate', headers={'Authorization': f'Bearer {token}'}, timeout=60.0)
        print('Generate:', gen.status_code)
        
        data = gen.json()
        if 'meals' in data:
            print('Meals len:', len(data['meals']))
        else:
            print('Response:', json.dumps(data, indent=2))
            
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    test_api()
