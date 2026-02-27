import os
import sys
import re
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to sys path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.db_models import FoodItem

DATABASE_URL = "postgresql+psycopg2://admin:mityahar_dev@localhost:5432/mityahar_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

DIET_MAP = {
    "vegetarian":     "Vegetarian",
    "vegetarian ":    "Vegetarian",
    "non vegetarian": "Non-Vegetarian",
    "non-vegetarian": "Non-Vegetarian",
    "eggetarian":     "Eggetarian",
}

SLOT_MAP = {
    "rice": "grain", "roti": "grain", "paratha": "grain", "bread": "grain",
    "pulao": "grain", "biryani": "grain", "khichdi": "grain", "litti": "grain",
    "dum cooked rice": "grain", "pongal": "grain", "rice dish": "grain",
    "roti and curry": "grain",
    "curry and rice": "grain",
    "dal": "dal_protein", "dal based soup": "dal_protein",
    "curry": "dal_protein", "non vegetarian dish": "dal_protein",
    "non veg dish": "dal_protein",
    "vegetable": "sabzi", "vegetable dish": "sabzi",
    "salad": "accompaniment", "accompaniment": "accompaniment",
    "beverage": "accompaniment", "curd": "accompaniment", "chutney": "accompaniment",
    "veg": "main_dish", "snack": "main_dish", "wrap": "main_dish",
    "sandwich": "main_dish", "chilla": "main_dish", "pancake": "main_dish",
    "pancakes": "main_dish", "pudding": "main_dish", "sweet": "main_dish",
    "chaat": "main_dish", "dumpling": "main_dish", "breakfast": "main_dish",
}

FILE_CONFIG = {
    "Breakfast.xlsx": {
        "meal_time_tags": ["Breakfast"],
        "force_slot": None,
    },
    "Lunch.xlsx": {
        "meal_time_tags": ["Lunch", "Dinner"],
        "force_slot": None,
    },
    "Dinner.xlsx": {
        "meal_time_tags": ["Dinner"],
        "force_slot": None,
    },
    "Morning_Snack (1).xlsx": {
        "meal_time_tags": ["Morning_Snack", "Evening_Snack"], # Assuming snacks might apply to both
        "force_slot": "snack_item",
    },
}

# The prompt specifically says meal_time_tags for Morning_Snack (1).xlsx is ["Morning_Snack"]. Let's follow it perfectly.
FILE_CONFIG["Morning_Snack (1).xlsx"]["meal_time_tags"] = ["Morning_Snack"]


def parse_ingredients(ingredient_str, amount_str) -> list[dict]:
    if not isinstance(ingredient_str, str):
        return []
    names = [n.strip() for n in ingredient_str.split(",") if n.strip()]
    amounts = []
    if isinstance(amount_str, str):
        amounts = [float(a.strip()) if a.strip().replace(".", "", 1).isdigit() else 0.0
                   for a in amount_str.split(",")]
    elif isinstance(amount_str, (int, float)):
        amounts = [float(amount_str)]
    while len(amounts) < len(names):
        amounts.append(0.0)
    return [{"name": n, "amount_g": a} for n, a in zip(names, amounts) if n]

def parse_serving_weight(df_row) -> float:
    # Handle the fact that Morning_Snack has a double space
    weight_str = None
    if 'TOTAL WEIGHT AFTER COOKING (approx.)' in df_row.index:
        weight_str = df_row['TOTAL WEIGHT AFTER COOKING (approx.)']
    elif 'TOTAL WEIGHT AFTER COOKING  (approx.)' in df_row.index:
        weight_str = df_row['TOTAL WEIGHT AFTER COOKING  (approx.)']
    else:
        # Fallback if there's any other slight variation
        for col in df_row.index:
            if 'TOTAL WEIGHT AFTER COOKING' in str(col).upper():
                weight_str = df_row[col]
                break

    if pd.isna(weight_str):
        return 0.0
    
    match = re.search(r"(\d+\.?\d*)", str(weight_str))
    if match:
        return float(match.group(1))
    return 0.0

def main():
    base_data_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'services', 'meal_generator', 'data')
    session = SessionLocal()
    inserted_count = 0

    try:
        for filename, config in FILE_CONFIG.items():
            filepath = os.path.join(base_data_path, filename)
            if not os.path.exists(filepath):
                print(f"Warning: File not found {filepath}")
                continue
            
            df = pd.read_excel(filepath)
            
            for _, row in df.iterrows():
                recipe_name = str(row.get('MENU', '')).strip()
                if not recipe_name or pd.isna(row.get('MENU')):
                    continue
                
                cal = row.get('calories')
                if pd.isna(cal):
                    cal = row.get('Calories')
                
                # Coerce to float just in case it's a string or something
                try:
                    cal = float(cal)
                except (ValueError, TypeError):
                    cal = 0.0

                if pd.isna(cal) or cal == 0:
                    print(f"Skipped {recipe_name}: zero calories")
                    continue
                
                # Normalize Diet
                raw_diet = str(row.get('DIET', '')).strip().lower()
                diet_type = DIET_MAP.get(raw_diet, "Vegetarian")

                # Determine slot
                if config["force_slot"]:
                    slot_type = config["force_slot"]
                else:
                    raw_cat = str(row.get('CATEGORY', '')).strip().lower()
                    if filename == 'Breakfast.xlsx' and raw_cat == 'beverage':
                        slot_type = 'beverage'
                    else:
                        slot_type = SLOT_MAP.get(raw_cat, "accompaniment")
                
                # Determine regions
                if 'Region' in df.columns and not pd.isna(row['Region']):
                    region_tags = [str(row['Region']).strip()]
                else:
                    region_tags = ["North", "South", "East", "West"]

                # Parse serving weight
                serving_weight_g = parse_serving_weight(row)

                # Parse ingredients
                ingredients = parse_ingredients(row.get('INGREDIENT'), row.get('AMOUNT (g)'))

                # Plan types
                plan_types = ["Healthy", "Diabetic-Friendly", "Gym-Friendly"]

                # Other macros (with defaults)
                protein = float(row.get('Protein', 0)) if not pd.isna(row.get('Protein')) else 0.0
                carbs = float(row.get('Carbs', 0)) if not pd.isna(row.get('Carbs')) else 0.0
                fat = float(row.get('Fat', 0)) if not pd.isna(row.get('Fat')) else 0.0
                fiber = float(row.get('Fibre', 0)) if not pd.isna(row.get('Fibre')) else 0.0

                # Check existence before insert (Idempotency)
                # Since regions/meal_tags might be arrays, we do a simple check by recipe_name and diet_type
                existing = session.query(FoodItem.id).filter(
                    FoodItem.recipe_name == recipe_name,
                    FoodItem.diet_type == diet_type,
                    FoodItem.slot_type == slot_type
                ).first()

                if existing:
                    continue

                food_item = FoodItem(
                    recipe_name=recipe_name,
                    slot_type=slot_type,
                    cal_per_serving=cal,
                    protein_per_serving=protein,
                    carbs_per_serving=carbs,
                    fat_per_serving=fat,
                    fiber_per_serving=fiber,
                    serving_weight_g=serving_weight_g,
                    diet_type=diet_type,
                    region_tags=region_tags,
                    meal_time_tags=config["meal_time_tags"],
                    plan_type_tags=plan_types,
                    ingredients=ingredients,
                    instructions="",
                    source="excel",
                    is_verified=True, # Verified from excel logic
                )
                session.add(food_item)
                # commit individually or flush to catch errors easily
                try:
                    session.commit()
                    inserted_count += 1
                except Exception as e:
                    session.rollback()
                    print(f"Failed to insert {recipe_name}: {e}")

        print(f"Seeded {inserted_count} food_items rows")

    finally:
        session.close()

if __name__ == "__main__":
    main()
