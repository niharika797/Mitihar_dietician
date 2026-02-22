# Mitihar Dietician — Diet Plan API

A personalized diet planning REST API built with FastAPI and MongoDB.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)
![MongoDB](https://img.shields.io/badge/MongoDB-%234ea94b.svg?style=flat&logo=mongodb&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Build](https://img.shields.io/badge/build-passing-brightgreen.svg)

## OVERVIEW

The Mitihar Dietician API automatically generates personalized, 7-day Indian cuisine meal plans tailored to user biometrics and dietary preferences. It performs rapid nutritional calculations to determine a user's BMR and TDEE, mapping these against an extensively categorized food dataset. The system features a robust, retrying generation engine that guarantees exactly 42 meals per week alongside a consolidated ingredient shopping list.

- **JWT authentication with refresh tokens**: Secures endpoints using HS256 JWTs with a dedicated refresh token flow for long-lived sessions.
- **Automated 7-day meal plan generation based on user profile**: Dynamically crafts a week of meals constrained by the user's BMI, calculated caloric targets, and chosen dietary type.
- **Region-aware Indian cuisine meal selection (North, South, East, West)**: Filters datasets prior to meal selection to prioritize dishes authentic to the user's preferred geographic region.
- **Nutritional calculations: BMI, BMR, TDEE**: Accurately computes Basal Metabolic Rate via the Mifflin-St Jeor equation and scales it into Total Daily Energy Expenditure.
- **Progress tracking: meals, water intake, steps, weight history**: Enables users to log daily activity parameters to track their adherence and health trajectory over time.
- **Weekly ingredient checklist / shopping list**: Extracts and aggregates raw ingredient amounts across the 7-day plan to provide a ready-to-use grocery list.
- **Rate limiting on sensitive endpoints**: Protects authentication and heavy computational routes using slowapi to prevent abuse.
- **API versioning under `/api/v1/`**: Maintains a clean separation of concerns and versioning structure for future compatibility.

## ARCHITECTURE & HOW GENERATION WORKS

The application is built on top of a modern, asynchronous Python backend utilizing FastAPI for high-performance routing and Pydantic for strict data validation. It connects seamlessly to a NoSQL MongoDB instance asynchronously (using Motor) to flexibly store dynamic user profiles, progress logs, and generated structured meal plans.

**Meal Generation Pipeline:**
1. **User Profile**: User submits biometrics (age, weight, height, gender, activity level).
2. **Nutritional Target Calculation (BMR/TDEE)**: The system computes daily caloric requirements based on the Mifflin-St Jeor formula.
3. **Dataset Filtering (region + diet)**: Curated food datasets (pandas DataFrames) are filtered by the user's explicit diet (`Vegetarian`, `Non-Vegetarian`, `Eggetarian`) and paired with regional preferences.
4. **Meal Selection**: The engine randomly selects meals to fulfill the structure of 7 days × 3 meals (Breakfast, Lunch, Dinner) × 2 options = 42 total meals.
5. **Ingredient Checklist Generation**: The system iterates over the 42 selected meals, parsing and aggregating ingredient metadata to construct a consolidated shopping list.

*Note: The generation layer includes a strict validation layer that retries the process up to 3 times if constraints are missed (e.g., missing meals or invalid diet types). If all 3 attempts fail, an HTTP 503 error is returned.*

## TECH STACK TABLE

| Layer | Technology |
| :--- | :--- |
| **Runtime** | Python 3.10+ |
| **Framework** | FastAPI |
| **Database** | MongoDB (Motor Asyncio) |
| **Auth** | JWT (HS256) + Passlib (Bcrypt) |
| **Rate Limiting** | SlowAPI |
| **Data Processing** | Pandas, Numpy |
| **Server** | Uvicorn |

## QUICK START

### Prerequisites
- Python 3.10+
- MongoDB 5.0+ running locally or a connection URI
- PowerShell 7.0+ (Recommended for Windows)

### Installation
```bash
git clone <repository-url>
cd Mitihar_dietician
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

### Configuration
Copy the sample environment file to `.env`:
```bash
cp .env.example .env
```
| Variable | Description | Example Value |
| :--- | :--- | :--- |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `DATABASE_NAME` | Name of the database | `diet_plan` |
| `SECRET_KEY` | JWT signing key | `your-super-secret-key-here` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token validity in minutes | `1440` |
| `CORS_ORIGINS` | Allowed frontend URLs | `http://localhost:3000` |

### Run
```bash
uvicorn app.main:app --reload --port 8001
```

- **Swagger UI**: [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)
- **ReDoc**: [http://127.0.0.1:8001/redoc](http://127.0.0.1:8001/redoc)

## CORE USER JOURNEY

1. **Register** a new account (`POST /api/v1/auth/register`)
2. **Login** with credentials (`POST /api/v1/auth/token`)
3. **Get Token** to use in Bearer Auth headers
4. **Generate Plan** mapping biometrics to 42 meals (`POST /api/v1/diet-plans/generate`)
5. **View My Plan** with the ingredient checklist (`GET /api/v1/diet-plans/my-plan`)
6. **Track Progress** via water, activity, and weight logs (`POST /api/v1/progress/...`)

## API REFERENCE TABLE

| Method | Endpoint | Auth Required | Description |
| :--- | :--- | :---: | :--- |
| **POST** | `/api/v1/auth/register` | No | Register a new user profile |
| **POST** | `/api/v1/auth/token` | No | Login and retrieve access and refresh tokens |
| **POST** | `/api/v1/auth/refresh` | No | Refresh an expired access token |
| **GET** | `/api/v1/users/me` | Yes | Get the current authenticated user's profile |
| **PUT** | `/api/v1/users/me` | Yes | Update profile biometrics |
| **GET** | `/api/v1/users/bmi` | Yes | Calculate and return current BMI |
| **GET** | `/api/v1/calculations/bmi` | Yes | Calculate BMI (calculation group) |
| **GET** | `/api/v1/calculations/bmr` | Yes | Calculate Basal Metabolic Rate |
| **GET** | `/api/v1/calculations/tdee` | Yes | Calculate Total Daily Energy Expenditure |
| **POST** | `/api/v1/diet-plans/generate` | Yes | Generate a customized 7-day meal plan |
| **GET** | `/api/v1/diet-plans/my-plan` | Yes | Retrieve the fully generated 7-day meal plan |
| **GET** | `/api/v1/diet-plans/today` | Yes | Retrieve the standard 6 options for the current date |
| **GET** | `/api/v1/diet-plans/ingredient-checklist` | Yes | Get today's required ingredient list |
| **GET** | `/api/v1/diet-plans/weekly-ingredients` | Yes | Get the full 7-day required ingredient list |
| **PUT** | `/api/v1/diet-plans/update` | Yes | Modify existing meals in the generated plan |
| **DELETE** | `/api/v1/diet-plans/delete` | Yes | Delete the current diet plan |
| **POST** | `/api/v1/meal-plan/adjust` | Yes | Adjust target calories parameter (premium feature) |
| **POST** | `/api/v1/progress/log/meal` | Yes | Log a consumed meal |
| **POST** | `/api/v1/progress/log/water` | Yes | Log water intake |
| **POST** | `/api/v1/progress/log/activity` | Yes | Log physical activity |
| **GET** | `/api/v1/progress/today` | Yes | View today's tracked progress |
| **GET** | `/api/v1/progress/weekly` | Yes | View a 7-day summary of tracked progress |
| **GET** | `/api/v1/progress/weight` | Yes | Retrieve weight tracking history |

## TESTING

To run the robust sequence verification script against a live local server:
```bash
python tester.py
```
**Expected Output (Snippet):**
```text
--- SUMMARY ---
Total Pass: 38
Total Fail: 0
Total Warning: 1
Failure: TEST-08 warning: Rate limit worked but pattern differed
Verdict: ⚠️ Ready with Caveats
```

To run the standard isolated test suite:
```bash
pytest tests/ -v
```
**Expected Output:**
```text
======================== 10 passed in 1.80s ========================
```

## COMMON ISSUES & FIXES

| Issue | Solution |
| :--- | :--- |
| **MongoDB Connection Failed** | Ensure MongoDB service is running: `Start-Service MongoDB` |
| **Port 8001 in use** | Find and kill the process: `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8001).OwningProcess` |
| **Import Error** | Re-run `pip install -r requirements.txt` within the active venv. |
| **JWT Invalid** | Ensure `SECRET_KEY` matches in `.env` and tokens haven't expired. |
| **Rate limit hit during tests** | Wait 60s between full suite runs |

---
*Built with FastAPI · Powered by Indian cuisine datasets*
