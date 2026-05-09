"""
test_meal_generator.py
-----------------------
Runs the meal generator directly against the DB and prints a full
human-readable 7-day plan with per-meal calorie breakdown, slot details,
variety analysis, and a summary report.

Usage:
    venv\\Scripts\\python scripts\\test_meal_generator.py

Optional flags:
    --diet       Vegetarian | Non-Vegetarian | Eggetarian     (default: Vegetarian)
    --region     North | South | East | West                  (default: North)
    --plan       Healthy | Diabetic-Friendly | Gym-Friendly   (default: Healthy)
    --gender     male | female                                 (default: male)
    --age        integer                                       (default: 30)
    --weight     kg                                            (default: 75)
    --height     cm                                            (default: 175)
    --activity   S | LA | MA | VA | SA                        (default: MA)

Example:
    venv\\Scripts\\python scripts\\test_meal_generator.py --diet Non-Vegetarian --region South --plan Gym-Friendly
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.services.meal_generator.meal_generator import MealGenerator

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"
)

# ── Activity level labels ────────────────────────────────────────────────────
ACTIVITY_LABELS = {
    "S":  "Sedentary",
    "LA": "Lightly Active",
    "MA": "Moderately Active",
    "VA": "Very Active",
    "SA": "Super Active",
}

MEAL_ORDER = ["Breakfast", "MorningSnacks", "Lunch", "EveningSnacks", "Dinner"]
MEAL_LABELS = {
    "Breakfast":     "🌅 Breakfast",
    "MorningSnacks": "☕ Morning Snack",
    "Lunch":         "🍱 Lunch",
    "EveningSnacks": "🍵 Evening Snack",
    "Dinner":        "🌙 Dinner",
}

# ── Argument parser ──────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="Test the Mityahar meal generator")
    p.add_argument("--diet",     default="Vegetarian",
                   choices=["Vegetarian", "Non-Vegetarian", "Eggetarian"])
    p.add_argument("--region",   default="North",
                   choices=["North", "South", "East", "West"])
    p.add_argument("--plan",     default="Healthy",
                   choices=["Healthy", "Diabetic-Friendly", "Gym-Friendly"])
    p.add_argument("--gender",   default="male",   choices=["male", "female"])
    p.add_argument("--age",      default=30,        type=int)
    p.add_argument("--weight",   default=75,        type=float)
    p.add_argument("--height",   default=175,       type=float)
    p.add_argument("--activity", default="MA",
                   choices=["S", "LA", "MA", "VA", "SA"])
    return p.parse_args()


# ── Calorie check ────────────────────────────────────────────────────────────
def cal_status(actual: float, target: float) -> str:
    pct = (actual / target * 100) if target > 0 else 0
    if pct < 80:
        return f"⚠️  LOW  ({pct:.0f}% of target)"
    if pct > 120:
        return f"⚠️  HIGH ({pct:.0f}% of target)"
    return f"✅ OK   ({pct:.0f}% of target)"


# ── Main runner ──────────────────────────────────────────────────────────────
async def run(args):
    user_data = {
        "diet":           args.diet,
        "region":         args.region,
        "health_condition": args.plan,
        "gender":         args.gender,
        "age":            args.age,
        "weight":         args.weight,
        "height":         args.height,
        "activity_level": args.activity,
        "start_date":     datetime.now().strftime("%Y-%m-%d"),
    }

    # ── Print user profile ───────────────────────────────────────────────────
    print("\n" + "═" * 65)
    print("  MITYAHAR MEAL GENERATOR — TEST RUN")
    print("═" * 65)
    print(f"  Diet         : {args.diet}")
    print(f"  Region       : {args.region}")
    print(f"  Plan Type    : {args.plan}")
    print(f"  Gender       : {args.gender.title()}")
    print(f"  Age / Weight : {args.age} yrs / {args.weight} kg")
    print(f"  Height       : {args.height} cm")
    print(f"  Activity     : {ACTIVITY_LABELS[args.activity]}")
    print("═" * 65)

    # ── Calculate targets for display ───────────────────────────────────────
    from app.services.meal_generator.calculations import (
        calculate_bmi, calculate_bmr, calculate_tdee, calculate_macronutrients
    )
    bmi  = calculate_bmi(args.height, args.weight)
    bmr  = calculate_bmr(args.gender, args.weight, args.height, args.age)
    tdee = calculate_tdee(bmr, args.activity)
    protein, carbs, fiber, fat = calculate_macronutrients(tdee, args.plan)

    print(f"\n  📊 CALCULATED TARGETS")
    print(f"  BMI    : {bmi:.1f}")
    print(f"  BMR    : {bmr:.0f} kcal")
    print(f"  TDEE   : {tdee:.0f} kcal/day")
    print(f"  Protein: {protein:.0f}g/day  |  Carbs: {carbs:.0f}g/day  |  Fat: {fat:.0f}g/day  |  Fiber: {fiber:.0f}g/day")

    # ── Meal targets display ─────────────────────────────────────────────────
    meal_pcts = {
        "Healthy":          {"Breakfast":0.25,"MorningSnacks":0.05,"Lunch":0.30,"EveningSnacks":0.05,"Dinner":0.25},
        "Gym-Friendly":     {"Breakfast":0.25,"MorningSnacks":0.05,"Lunch":0.35,"EveningSnacks":0.05,"Dinner":0.30},
        "Diabetic-Friendly":{"Breakfast":0.25,"MorningSnacks":0.05,"Lunch":0.35,"EveningSnacks":0.05,"Dinner":0.30},
    }
    pcts = meal_pcts.get(args.plan, meal_pcts["Healthy"])
    print(f"\n  🎯 MEAL CALORIE TARGETS")
    for meal, pct in pcts.items():
        print(f"  {MEAL_LABELS[meal]:25} → {tdee * pct:>6.0f} kcal  ({int(pct*100)}%)")

    # ── Run generator ────────────────────────────────────────────────────────
    print("\n  ⚙️  Generating 7-day plan...\n")

    engine  = create_async_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    generator = MealGenerator()
    async with Session() as session:
        result = await generator.generate_meal_plan(user_data, session)

    await engine.dispose()

    meals     = result.get("meals", [])
    checklist = result.get("ingredient_checklist", [])

    if not meals:
        print("  ❌ No meals generated. Check DB data and templates.")
        return

    # ── Group by day ─────────────────────────────────────────────────────────
    days: dict[str, dict] = {}
    for meal in meals:
        date = meal["Date"]
        if date not in days:
            days[date] = {}
        days[date][meal["Meal Type"]] = meal

    # ── Print 7-day plan ─────────────────────────────────────────────────────
    weekly_cal   = 0.0
    daily_totals = []
    all_dishes   = []
    repeated     = defaultdict(int)

    for day_num, (date, day_meals) in enumerate(sorted(days.items()), 1):
        day_cal = sum(m["Total Calories"] for m in day_meals.values())
        weekly_cal += day_cal
        daily_totals.append(day_cal)

        print("─" * 65)
        print(f"  DAY {day_num}  —  {date}   |  Total: {day_cal:.0f} kcal  {cal_status(day_cal, tdee)}")
        print("─" * 65)

        for meal_type in MEAL_ORDER:
            if meal_type not in day_meals:
                print(f"  {MEAL_LABELS[meal_type]:25}  ❌ MISSING")
                continue

            m          = day_meals[meal_type]
            target_cal = tdee * pcts.get(meal_type, 0)
            dishes     = m["Menu Names"]
            cal        = m["Total Calories"]
            protein_g  = m["Total Protein"]
            carbs_g    = m["Total Carbs"]
            fat_g      = m["Total Fat"]
            fiber_g    = m["Total Fiber"]

            # Track for variety analysis
            for dish in dishes.split(" + "):
                d = dish.strip()
                all_dishes.append(d)
                repeated[d] += 1

            status = cal_status(cal, target_cal)
            print(f"  {MEAL_LABELS[meal_type]}")
            print(f"    Dishes  : {dishes}")
            print(f"    Calories: {cal:.0f} kcal  (target {target_cal:.0f})  {status}")
            print(f"    Macros  : Protein {protein_g:.1f}g  |  Carbs {carbs_g:.1f}g  |  Fat {fat_g:.1f}g  |  Fiber {fiber_g:.1f}g")

        print()

    # ── Weekly summary ───────────────────────────────────────────────────────
    print("═" * 65)
    print("  📋 WEEKLY SUMMARY")
    print("═" * 65)
    avg_daily = weekly_cal / len(daily_totals) if daily_totals else 0
    print(f"  Total meals generated : {len(meals)} / 35 expected")
    print(f"  Avg daily calories    : {avg_daily:.0f} kcal  (TDEE target: {tdee:.0f})")
    print(f"  Weekly calorie total  : {weekly_cal:.0f} kcal")
    print(f"  Daily range           : {min(daily_totals):.0f} – {max(daily_totals):.0f} kcal")

    # ── Variety analysis ─────────────────────────────────────────────────────
    print(f"\n  🔁 VARIETY ANALYSIS")
    repeats = {dish: count for dish, count in repeated.items() if count > 1}
    unique  = len(set(all_dishes))
    total   = len(all_dishes)

    print(f"  Unique dishes used    : {unique} / {total} total slots")
    if repeats:
        print(f"  Repeated dishes ({len(repeats)})  :")
        for dish, count in sorted(repeats.items(), key=lambda x: -x[1]):
            print(f"    • {dish} — {count}×")
    else:
        print(f"  ✅ No dishes repeated across the week!")

    # ── Missing meals check ──────────────────────────────────────────────────
    expected = 7 * 5   # 7 days × 5 meals
    missing  = expected - len(meals)
    if missing > 0:
        print(f"\n  ⚠️  MISSING MEALS: {missing} slots were not filled")
        print(f"     This usually means DB has insufficient items for some slots.")
        print(f"     Check logs above for '❌ MISSING' entries.")
    else:
        print(f"\n  ✅ All 35 meal slots filled successfully")

    # ── Top 10 ingredients from checklist ────────────────────────────────────
    if checklist:
        print(f"\n  🛒 TOP 10 SHOPPING LIST ITEMS (by weight)")
        items = sorted(checklist, key=lambda x: x.get("Total Amount (g)", 0), reverse=True)[:10]
        for item in items:
            name = item.get("Ingredient", "?")
            amt  = item.get("Total Amount (g)", 0)
            print(f"    • {name:<30} {amt:>8.0f} g")

    print("\n" + "═" * 65 + "\n")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args))
