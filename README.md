# Mityahar Local Development Setup

Welcome to the development environment for **Mityahar**! This backend service provides AI-powered customized meal recommendations, patient-doctor management, progress tracking, and diet administration.

To get started easily, please follow this step-by-step setup guide. This document is written specifically for Windows users looking to test the dataset, database, and backend service locally.

---

## 🛠 Prerequisites

Before running any code, you **must** have these three critical dependencies installed on your machine.
If you skip this, the automation scripts and the backend will fail.

1.  **Python 3.10+**: Download and install from [python.org](https://www.python.org/downloads/windows/). Make sure to check the box "Add Python to PATH" during installation.
2.  **Docker Desktop**: Required to run the PostgreSQL database locally.
    *   ⬇️ **Download**: [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
    *   *Note: Open Docker Desktop after installing and ensure it is visibly running in your system tray before proceeding.*
3.  **pgAdmin 4**: The graphical user interface you will use to view the datasets and tables inside the database.
    *   ⬇️ **Download**: [Download pgAdmin4-9.12-x64.exe (214.7 MB)](https://www.postgresql.org/ftp/pgadmin/pgadmin4/v9.12/windows/)

---

## 🧱 Key Features & Architecture

Mityahar operates with a multi-role structure:

*   **Patients**: Have personal profiles, log meals and progress (weight, steps, water), and receive AI-generated meal plans. Can connect to doctors.
*   **Doctors**: Have specialized dashboards. Can generate subscription codes, approve patient requests, view connected patient's progress, and write private/public clinical notes.
*   **Admins**: Manage platform integrity. IP-whitelisted role capable of overseeing billing, global data erasure, and overseeing user activity.

**Authentication & Security**:
*   JWT-based role authentication (`/api/v1/auth/token`).
*   Google OAuth login support for patients.
*   Layered Middleware protecting routes: `SubscriptionCheckMiddleware` enforces active subscriptions for diet generation, `DoctorIsolationMiddleware` restricts doctor access strictly to their *own* connected patients, and `AdminIPWhitelistMiddleware` secures admin tools.

**Diet Engine**: 
*   Powered by a `6000+` recipe database and `meal_generator` services.
*   Dynamic slot distribution and strict calorie adherence depending on user diet types (Vegetarian, Non-Veg, Keto, Diabetic, etc.) and regional cuisines.

---

## 🚀 Quick Setup (Automated)

We have created an automation script to handle creating the virtual environment, downloading Python libraries, starting the database, and inserting the base data.

1.  Open your terminal or command prompt.
2.  Navigate to the root of this project folder.
3.  Ensure **Docker Desktop** is open and running in the background.
4.  Run the setup script:

```cmd
setup.bat
```

**What this script does:**
*   Verifies Python and Docker are installed.
*   Creates a `venv` folder (Python virtual environment).
*   Installs dependencies from `requirements.txt`.
*   Creates a `.env` file from `.env.example` (See below for manual overrides).
*   Spins up a local PostgreSQL database container on port `5432`.
*   Runs `alembic` to create all the necessary tables (Patients, Doctors, Progress, Mappings, etc.).
*   Runs python scripts inside the `scripts/` folder to populate the database with food items, properties, and 6000+ recipes.

---

## 🔐 Environment Variables

The `setup.bat` script copies `.env.example` to `.env`. Ensure your `.env` contains the required keys. 
*Note: Make sure to add your Google OAuth Client credentials if testing Google Sign-in.*

```env
DATABASE_URL=postgresql://mityahar_user:mityahar_password@localhost:5432/mityahar_db
SECRET_KEY=your-super-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

---

## 🐘 Viewing the Dataset (pgAdmin 4)

Once the setup script finishes, your database is live and filled with recipes and user schemas.

To view the data:
1.  Open **pgAdmin 4** (the application you downloaded in the prerequisites).
2.  Click **"Add New Server"** in the Quick Links on the dashboard.
3.  **General Tab**: Name the server whatever you want (e.g., "Mityahar Local DB").
4.  **Connection Tab**:
    *   **Host name/address**: `localhost`
    *   **Port**: `5432`
    *   **Maintenance database**: `postgres`
    *   **Username**: `mityahar_user`
    *   **Password**: `mityahar_password`
5.  Click **Save**.
6.  On the left sidebar, expand your new server -> Databases -> `mityahar_db` -> Schemas -> `public` -> Tables.
7.  Right-click on tables like `food_items`, `recipes`, `patients`, or `doctors` and select **View/Edit Data -> All Rows** to explore the dataset!

---

## 💻 Running the Application

To start the FastAPI backend service:

1.  Activate your virtual environment: 
    ```cmd
    venv\Scripts\activate
    ```
2.  Start the Uvicorn server: 
    ```cmd
    python -m uvicorn app.main:app --reload
    ```
3.  Open your browser to [http://localhost:8000/docs](http://localhost:8000/docs) to view the interactive API playground (Swagger UI).

Please see [RUNNING_GUIDE.md](RUNNING_GUIDE.md) for detailed instructions on testing out the various roles and endpoints.
