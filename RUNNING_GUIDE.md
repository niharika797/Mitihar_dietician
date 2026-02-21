# Mitihar Dietician - Running & Testing Guide

This guide provides step-by-step instructions for setting up, running, and testing the Mitihar Dietician API locally on a Windows machine.

---

## 1. PREREQUISITES

Ensure the following software is installed on your system:

| Software | Version | Purpose | Download Link |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10+ | Application Runtime | [Download Python](https://www.python.org/downloads/) |
| **MongoDB** | 5.0+ | Database | [Download MongoDB Community](https://www.mongodb.com/try/download/community) |
| **PowerShell** | 7.0+ | Terminal (Recommended) | Pre-installed on Windows |

---

## 2. SETUP (One-Time)

Follow these steps to initialize the project:

1.  **Clone the Repository** (If not already done)
    ```powershell
    git clone <repository-url>
    cd Mitihar_dietician
    ```

2.  **Create a Virtual Environment**
    ```powershell
    python -m venv venv
    ```

3.  **Activate the Virtual Environment**
    ```powershell
    .\venv\Scripts\Activate.ps1
    ```

4.  **Upgrade pip and Install Dependencies**
    ```powershell
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

---

## 3. ENVIRONMENT CONFIGURATION

1.  **Create `.env` file**
    Copy the `.env.example` file to `.env`:
    ```powershell
    cp .env.example .env
    ```

2.  **Required Variables**
    Open `.env` and ensure the following variables are set:

| Variable | Description | Example Value |
| :--- | :--- | :--- |
| `MONGO_URI` | MongoDB connection string | `mongodb://localhost:27017` |
| `DATABASE_NAME` | Name of the database | `diet_plan` |
| `SECRET_KEY` | JWT signing key | `your-super-secret-key-here` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token validity in minutes | `1440` |
| `CORS_ORIGINS` | Allowed frontend URLs | `http://localhost:3000` |

---

## 4. RUNNING THE APP

1.  **Start the Server**
    ```powershell
    uvicorn app.main:app --reload --port 8001
    ```

2.  **Confirm Execution**
    You should see output similar to:
    ```text
    INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
    INFO:     Application startup complete.
    ```

3.  **Access Links**
    - **API Base**: [http://localhost:8001](http://localhost:8001)
    - **Interactive Documentation (Swagger)**: [http://localhost:8001/docs](http://localhost:8001/docs)

---

## 5. TESTING THE API MANUALLY

Use the **Swagger UI** (`/docs`) or `curl` to test endpoints in this recommended order:

### **Step 1: Register**
- **Method**: `POST`
- **Route**: `/api/auth/register`
- **Purpose**: Create a new account.
- **Payload**:
  ```json
  {
    "email": "user@example.com",
    "password": "password123",
    "name": "Jane Doe",
    "age": 30,
    "gender": "female",
    "height": 165,
    "weight": 60,
    "activity_level": "MA",
    "diet": "Vegetarian",
    "health_condition": "Healthy",
    "region": "North Indian"
  }
  ```

### **Step 2: Login**
- **Method**: `POST`
- **Route**: `/api/auth/token`
- **Purpose**: Get a JWT token.
- **Form Data**: `username=user@example.com`, `password=password123`

### **Step 3: Generate Meal Plan**
- **Method**: `POST`
- **Route**: `/api/diet-plans/generate`
- **Auth**: Bearer Token required.
- **Purpose**: Creates the initial 7-day plan.

### **Step 4: View Profile & Calculations**
- `/api/users/me` (GET): View your details.
- `/api/calculations/tdee` (GET): View your calculated daily calorie target.

---

## 6. RUNNING AUTOMATED TESTS

To ensure everything is working correctly:

1.  **Run All Tests**
    ```powershell
    pytest tests/ -v
    ```

2.  **Expected Outcome**
    ```text
    ======================== 10 passed in 1.80s ========================
    ```

---

## 7. COMMON ERRORS & FIXES

| Issue | Solution |
| :--- | :--- |
| **MongoDB Connection Failed** | Ensure MongoDB service is running: `Start-Service MongoDB` |
| **Port 8001 in use** | Find and kill the process: `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8001).OwningProcess` |
| **Import Error** | Re-run `pip install -r requirements.txt` within the active venv. |
| **JWT Invalid** | Ensure `SECRET_KEY` matches in `.env` and tokens haven't expired. |
