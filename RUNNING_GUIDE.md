# Mitihar Dietician - Running & Testing Guide

*For installation and setup, see README.md*

---

## 1. PREREQUISITES

Ensure the following software is installed on your system:

| Software | Version | Purpose | Download Link |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10+ | Application Runtime | [Download Python](https://www.python.org/downloads/) |
| **MongoDB** | 5.0+ | Database | [Download MongoDB Community](https://www.mongodb.com/try/download/community) |
| **PowerShell** | 7.0+ | Terminal (Recommended) | Pre-installed on Windows |

---

## 2. COMMON ERRORS & FIXES

| Issue | Solution |
| :--- | :--- |
| **MongoDB Connection Failed** | Ensure MongoDB service is running: `Start-Service MongoDB` |
| **Port 8001 in use** | Find and kill the process: `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8001).OwningProcess` |
| **Import Error** | Re-run `pip install -r requirements.txt` within the active venv. |
| **JWT Invalid** | Ensure `SECRET_KEY` matches in `.env` and tokens haven't expired. |
| **Rate limit hit during tests** | Wait 60s between full suite runs |

---

## 3. TESTING THE API MANUALLY

Use the **Swagger UI** (`/docs`) or `curl` to test endpoints in this recommended order:

### **Step 1: Register**
- **Method**: `POST`
- **Route**: `/api/v1/auth/register`
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
- **Route**: `/api/v1/auth/token`
- **Purpose**: Get a JWT token.
- **Form Data**: `username=user@example.com`, `password=password123`

### **Step 3: Generate Meal Plan**
- **Method**: `POST`
- **Route**: `/api/v1/diet-plans/generate`
- **Auth**: Bearer Token required.
- **Purpose**: Creates the initial 7-day plan.

### **Step 4: View Profile & Calculations**
- `/api/v1/users/me` (GET): View your details.
- `/api/v1/calculations/tdee` (GET): View your calculated daily calorie target.
