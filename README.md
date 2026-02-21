# Mitihar Dietician — Diet Plan API

A personalized diet planning REST API built with FastAPI and MongoDB.

## Features
- JWT authentication with refresh tokens
- Automated 7-day meal plan generation based on user profile
- Region-aware Indian cuisine meal selection (North, South, East, West)
- Nutritional calculations: BMI, BMR, TDEE
- Progress tracking: meals, water intake, steps, weight history
- Weekly ingredient checklist / shopping list
- Rate limiting on sensitive endpoints
- API versioning under `/api/v1/`

## Tech Stack
- **Framework:** FastAPI (Python)
- **Database:** MongoDB
- **Auth:** JWT (HS256) with refresh tokens
- **Server:** Uvicorn
- **Rate Limiting:** slowapi

## Getting Started

### Prerequisites
- Python 3.9+
- MongoDB running locally or a connection URI

### Installation
```bash
git clone <repo-url>
cd Mitihar_dietician
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration
```bash
cp .env.example .env
# Edit .env and fill in your values
```

### Run
```bash
uvicorn app.main:app --reload --port 8001
```
API docs available at: http://127.0.0.1:8001/docs

### Running Tests
```bash
pytest tests/
```

## API Overview

| Tag | Base Path | Description |
| :--- | :--- | :--- |
| auth | /api/v1/auth | Register, login, refresh token |
| users | /api/v1/users | Profile management |
| diet-plans | /api/v1/diet-plans | Plan generation and retrieval |
| calculations | /api/v1/calculations | BMI, BMR, TDEE |
| progress | /api/v1/progress | Daily and weekly tracking |
| meal-plan | /api/v1/meal-plan | Calorie-adjusted plans (premium) |

## Notes
- Rate limiter uses in-memory storage by default. Switch to Redis before multi-worker deployment (see TODO in main.py).
- Set CORS_ORIGINS in .env for your frontend domain before production deployment.
