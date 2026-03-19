"""
check_db_state.py
-----------------
Quick read-only audit of food_items and meal_templates tables.
Tells us exactly what data is in the DB right now.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text

_url = os.getenv("DATABASE_URL")
if not _url:
    raise RuntimeError("DATABASE_URL is not set. Add it to your .env file.")
DATABASE_URL = _url.replace("+asyncpg", "+psycopg2")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("=" * 60)
    print("  FOOD_ITEMS TABLE")
    print("=" * 60)

    total = conn.execute(text("SELECT COUNT(*) FROM food_items")).scalar()
    print(f"  Total rows: {total}")

    by_source = conn.execute(text(
        "SELECT source, COUNT(*) as cnt FROM food_items GROUP BY source ORDER BY cnt DESC"
    )).fetchall()
    print(f"\n  By source:")
    for row in by_source:
        print(f"    {row[0] or 'NULL':<20} {row[1]} rows")

    by_diet = conn.execute(text(
        "SELECT diet_type, COUNT(*) as cnt FROM food_items GROUP BY diet_type ORDER BY cnt DESC"
    )).fetchall()
    print(f"\n  By diet_type:")
    for row in by_diet:
        print(f"    {row[0] or 'NULL':<25} {row[1]} rows")

    by_verified = conn.execute(text(
        "SELECT is_verified, COUNT(*) FROM food_items GROUP BY is_verified"
    )).fetchall()
    print(f"\n  By is_verified:")
    for row in by_verified:
        print(f"    {str(row[0]):<10} {row[1]} rows")

    by_slot = conn.execute(text(
        "SELECT slot_type, COUNT(*) FROM food_items GROUP BY slot_type ORDER BY COUNT(*) DESC"
    )).fetchall()
    print(f"\n  By slot_type:")
    for row in by_slot:
        print(f"    {row[0] or 'NULL':<20} {row[1]} rows")

    cal_stats = conn.execute(text(
        "SELECT ROUND(AVG(cal_per_serving),1), ROUND(MIN(cal_per_serving),1), ROUND(MAX(cal_per_serving),1) FROM food_items"
    )).fetchone()
    print(f"\n  Calories per serving — avg: {cal_stats[0]}, min: {cal_stats[1]}, max: {cal_stats[2]}")

    sample = conn.execute(text(
        "SELECT recipe_name, source, diet_type, slot_type, cal_per_serving FROM food_items LIMIT 10"
    )).fetchall()
    print(f"\n  Sample rows (first 10):")
    for r in sample:
        print(f"    [{r[1]}] {r[0]:<40} | {r[2]:<18} | {r[3]:<15} | {r[4]} kcal")

    print("\n" + "=" * 60)
    print("  MEAL_TEMPLATES TABLE")
    print("=" * 60)

    tmpl_total = conn.execute(text("SELECT COUNT(*) FROM meal_templates")).scalar()
    print(f"  Total rows: {tmpl_total}")

    if tmpl_total > 0:
        by_meal = conn.execute(text(
            "SELECT meal_time, COUNT(*) FROM meal_templates GROUP BY meal_time ORDER BY meal_time"
        )).fetchall()
        print(f"\n  By meal_time:")
        for row in by_meal:
            print(f"    {row[0]:<20} {row[1]} rows")
