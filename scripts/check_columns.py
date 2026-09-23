import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.models.db_models import FoodItem
cols = [c.name for c in FoodItem.__table__.columns]
print("FoodItem columns:", cols)
assert "doctor_id" in cols, "doctor_id NOT found!"
print("OK: doctor_id confirmed in FoodItem columns.")
