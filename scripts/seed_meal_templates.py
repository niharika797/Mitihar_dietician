import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to sys path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.db_models import MealTemplate

DATABASE_URL = "postgresql+psycopg2://admin:mityahar_dev@localhost:5432/mityahar_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

LUNCH_DINNER_SLOTS = [
    {"slot_type": "grain",         "calorie_pct": 0.35, "required": True},
    {"slot_type": "dal_protein",   "calorie_pct": 0.28, "required": True},
    {"slot_type": "sabzi",         "calorie_pct": 0.22, "required": True},
    {"slot_type": "accompaniment", "calorie_pct": 0.15, "required": False},
]

BREAKFAST_SLOTS = [
    {"slot_type": "main_dish",      "calorie_pct": 0.70, "required": True},
    {"slot_type": "accompaniment",  "calorie_pct": 0.20, "required": True},
    {"slot_type": "beverage",       "calorie_pct": 0.10, "required": False},
]

SNACK_SLOTS = [
    {"slot_type": "snack_item", "calorie_pct": 1.0, "required": True},
]

MEAL_TIMES = ["Breakfast", "Lunch", "Dinner", "Morning_Snack"]
REGIONS = ["North", "South", "East", "West"]
DIET_TYPES = ["Vegetarian", "Non-Vegetarian", "Eggetarian"]
PLAN_TYPES = ["Healthy", "Diabetic-Friendly", "Gym-Friendly"]

def get_slots_for_meal(meal_time: str) -> list[dict]:
    if meal_time == "Breakfast":
        return BREAKFAST_SLOTS
    elif meal_time in ["Lunch", "Dinner"]:
        return LUNCH_DINNER_SLOTS
    elif meal_time == "Morning_Snack":
        return SNACK_SLOTS
    return []

def main():
    session = SessionLocal()
    inserted_count = 0

    try:
        for meal_time in MEAL_TIMES:
            slots = get_slots_for_meal(meal_time)
            for region in REGIONS:
                for diet_type in DIET_TYPES:
                    for plan_type in PLAN_TYPES:
                        
                        existing = session.query(MealTemplate.id).filter(
                            MealTemplate.meal_time == meal_time,
                            MealTemplate.region == region,
                            MealTemplate.diet_type == diet_type,
                            MealTemplate.plan_type == plan_type
                        ).first()

                        if existing:
                            continue
                        
                        template = MealTemplate(
                            meal_time=meal_time,
                            region=region,
                            diet_type=diet_type,
                            plan_type=plan_type,
                            slots=slots
                        )
                        session.add(template)
                        try:
                            session.commit()
                            inserted_count += 1
                        except Exception as e:
                            session.rollback()
                            print(f"Failed to insert template {meal_time} {region}: {e}")

        print(f"Seeded {inserted_count} meal_template rows")

    finally:
        session.close()

if __name__ == "__main__":
    main()
