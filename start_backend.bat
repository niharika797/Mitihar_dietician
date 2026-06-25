@echo off
cd /d "C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician"
venv\Scripts\python.exe -m uvicorn app.main:app --port 8001 --host 127.0.0.1
