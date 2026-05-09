import sys
sys.path.insert(0, r"C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician")
from app.models.db_models import FoodItem
cols = [c.name for c in FoodItem.__table__.columns]
print("FoodItem columns:", cols)
assert "doctor_id" in cols, "doctor_id NOT found!"
print("OK: doctor_id confirmed in FoodItem columns.")
