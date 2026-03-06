"""
clean_recipe_names.py
---------------------
1. Cleans recipe_name in food_items (source='6k_dataset'):
   - Strips region prefixes (Karnataka Style, Kerala Style, etc.)
   - Removes " Recipe" word
   - Removes everything after " - " (subtitles)
   - Removes parenthetical descriptions
   - Trims whitespace and trailing punctuation

2. Replaces instructions column with a YouTube search URL
   based on the cleaned dish name.

Usage:
    venv\\Scripts\\python scripts\\clean_recipe_names.py

Env vars (optional):
    DATABASE_URL  — PostgreSQL DSN
"""

import os
import re
import sys
import logging
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.models.db_models import FoodItem

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://admin:mityahar_dev@localhost:5432/mityahar_db"
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ── Region/style prefixes to strip ───────────────────────────────────────────
REGION_PREFIXES = [
    "karnataka style", "kerala style", "tamil nadu style", "tamil style",
    "andhra style", "bengali style", "gujarati style", "maharashtrian style",
    "punjabi style", "rajasthani style", "mughlai style", "goan style",
    "hyderabadi style", "himachali style", "uttarakhand style", "bihari style",
    "north indian style", "south indian style", "restaurant style",
    "homestyle", "home style", "traditional style", "classic style",
    "indian style", "desi style",
]


def clean_name(raw: str) -> str:
    """
    Clean a raw recipe name into a short, user-friendly display name.

    Steps:
    1. Take only the part before " - " (drop subtitle)
    2. Remove parenthetical descriptions
    3. Strip region/style prefixes
    4. Remove the word "Recipe" (standalone)
    5. Strip trailing punctuation and extra whitespace
    6. Title case
    """
    name = raw.strip()

    # Step 1: drop everything after first " - " or " – "
    name = re.split(r'\s+[-–]\s+', name)[0].strip()

    # Step 2: remove parenthetical content
    name = re.sub(r'\s*\(.*?\)', '', name).strip()

    # Step 3: strip known region/style prefixes (case-insensitive)
    name_lower = name.lower()
    for prefix in REGION_PREFIXES:
        if name_lower.startswith(prefix):
            name = name[len(prefix):].strip()
            name_lower = name.lower()
            break

    # Step 4: remove standalone "Recipe" word (anywhere)
    name = re.sub(r'\bRecipe\b', '', name, flags=re.IGNORECASE).strip()

    # Step 5: remove trailing/leading punctuation and extra spaces
    name = re.sub(r'\s+', ' ', name).strip(" -–,.")

    # Step 6: title case
    name = name.title()

    return name


def youtube_link(clean: str) -> str:
    """Generate a YouTube search URL for the dish name."""
    query = quote_plus(clean + " recipe")
    return f"https://www.youtube.com/results?search_query={query}"


def main():
    engine  = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    log.info("Fetching all 6k_dataset rows...")
    rows = session.query(FoodItem).filter(FoodItem.source == "6k_dataset").all()
    log.info(f"Found {len(rows)} rows")

    updated  = 0
    skipped  = 0
    errors   = 0
    examples = []   # store first 15 changes for preview

    for item in rows:
        try:
            original = item.recipe_name
            cleaned  = clean_name(original)

            if not cleaned or len(cleaned) < 3:
                skipped += 1
                continue

            yt_link = youtube_link(cleaned)

            # Collect examples for preview printout
            if len(examples) < 15:
                examples.append((original, cleaned))

            item.recipe_name  = cleaned
            item.instructions = yt_link   # replace instructions with YouTube link
            updated += 1

        except Exception as e:
            session.rollback()
            log.debug(f"Error on '{item.recipe_name}': {e}")
            errors += 1
            continue

    try:
        session.commit()
        log.info("All changes committed.")
    except Exception as e:
        session.rollback()
        log.error(f"Commit failed: {e}")
        errors += len(rows)
    finally:
        session.close()

    # ── Print summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  CLEAN COMPLETE")
    print(f"  Updated:  {updated}")
    print(f"  Skipped:  {skipped}")
    print(f"  Errors:   {errors}")
    print("=" * 65)

    print("\n  SAMPLE — Before vs After (first 15):")
    print("  " + "-" * 61)
    for orig, clean in examples:
        print(f"  BEFORE : {orig[:55]}")
        print(f"  AFTER  : {clean}")
        print(f"  YOUTUBE: https://www.youtube.com/results?search_query={quote_plus(clean + ' recipe')}")
        print()

    print("=" * 65)
    print("  Instructions column now contains YouTube search links.")
    print("  Verify a few rows in pgAdmin before marking is_verified=True.")
    print("=" * 65)


if __name__ == "__main__":
    main()
