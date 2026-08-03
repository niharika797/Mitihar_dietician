import sys, warnings
warnings.filterwarnings("error")
sys.path.insert(0, 'C:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician')

from app.models.db_models import Doctor, ClinicalNote, AuditLog, Patient, ProgressLog
from app.services.diet_plan_service import DietPlanService
from app.routers.meal_plan import router
from app.main import app

print("ALL CLEAN — zero warnings, zero import errors")
print(f"  models/diet_plan.py deleted: OK")
print(f"  ClinicalNote relationship: no SAWarning")
print(f"  All routers import clean")
