from fastapi.testclient import TestClient
from app.main import app
from app.services.user_service import get_current_user
from app.models.user import User

client = TestClient(app)

# Mocked user for testing
mock_user = User(
    gender="male",
    weight=70.0,
    height=175.0,
    age=25,
    activity_level="MA",
    meal_plan_purchased=True,
    name="Test User",
    email="test@example.com",
    password="password123",
    diet="Vegetarian",
    region="North Indian",
    health_condition="Healthy"
)

def get_mock_user():
    return mock_user

# Override dependency
app.dependency_overrides[get_current_user] = get_mock_user

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Diet Plan API"}

def test_get_bmi_endpoint():
    response = client.get("/api/v1/calculations/bmi")
    assert response.status_code == 200
    assert response.json() == {"bmi": 22.86}

def test_get_bmr_endpoint():
    response = client.get("/api/v1/calculations/bmr")
    assert response.status_code == 200
    assert response.json() == {"bmr": 1735.78}

def test_get_tdee_endpoint():
    response = client.get("/api/v1/calculations/tdee")
    assert response.status_code == 200
    assert response.json() == {"tdee": 2690.45}
