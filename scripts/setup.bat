@echo off
setlocal enabledelayedexpansion

echo ==============================================
echo Mityahar Local Development Setup Script
echo ==============================================

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python 3.10+ before continuing.
    exit /b 1
)
echo [OK] Python is installed.

:: Check for Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker Desktop is not installed or not running.
    echo Please download and install Docker Desktop:
    echo https://www.docker.com/products/docker-desktop/
    echo Make sure Docker Desktop is currently running before restarting this script.
    exit /b 1
)
echo [OK] Docker is installed and accessible.

:: Setup Virtual Environment
if not exist "venv\" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
) else (
    echo [INFO] Virtual environment already exists.
)

echo [INFO] Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

:: Setup Environment Variables
if not exist ".env" (
    echo [INFO] Creating .env file from .env.example...
    copy .env.example .env
) else (
    echo [INFO] .env file already exists.
)

:: Start Database
echo [INFO] Starting PostgreSQL database via Docker...
docker-compose up -d

echo [INFO] Waiting 5 seconds for PostgreSQL to initialize...
timeout /t 5 /nobreak >nul

:: Run Migrations
echo [INFO] Running Alembic migrations to create tables...
alembic upgrade head

:: Seed Database
echo [INFO] Running database seeders...
echo Seeding Food Items...
python scripts\seed_food_items.py
echo Seeding Meal Templates...
python scripts\seed_meal_templates.py
echo Seeding 6k Recipes...
python scripts\seed_6k_recipes.py

echo ==============================================
echo Setup Complete!
echo You can now run the app with: uvicorn app.main:app --reload
echo ==============================================
pause
