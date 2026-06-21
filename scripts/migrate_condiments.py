"""
Layer 2 — Condiment migration.

Default (dry-run): prints every recipe that would be migrated.
--commit:          runs the UPDATE after confirmation log.

Keywords use PostgreSQL word-boundary regex (\y) so that:
  - 'achaar' matches "Arbi Achaar"  ✓
  - 'achar'  matches "Mango Achar"  ✓
  - 'achar'  does NOT match "Achari Paneer"  ✓  (achari ≠ achar as whole word)
  - 'sev'    matches "Haldiram Sev"  ✓
  - 'sev'    does NOT match "Served rice" (if it existed)  ✓
"""
import asyncio
import sys

import asyncpg

DSN = "postgresql://admin:mityahar_dev@localhost:5432/mityahar_db"

# Word-boundary regex patterns — achari explicitly excluded by \y boundary
CONDIMENT_PATTERNS = [
    r"\yachaar\y",
    r"\yachar\y",
    r"\ypickle\y",
    r"\ychutney\y",
    r"\ypapad\y",
    r"\ynamkeen\y",
    r"\ybhujia\y",
    r"\ysev\y",
    r"\ychakli\y",
]

# Build WHERE clause using positional params
EXCLUSION_PATTERNS = [
    "% with %",       # "Dahi Vada With Sweet & Spicy Chutney"
    "%dosa%",         # "Masala Dosa With Red Chutney"
    "%idli%",         # "Mini Rava Idli With Tomato Chutney"
    "%chaat%",        # "Green Chutney Aloo Chaat"
    "%sandwich%",     # "Tomato Cucumber Chutney Sandwich"
    "%dhokla%",       # "Green Chutney Rava Dhokla"
    "%pakora%",       # "Crispy Paneer Pakora With Garlic Chutney"
    "%sadam%",        # "Chutney Podi Sadam"
    "%tapioca%",      # "Tapioca With Coconut Curd Chutney"
    "%bhel%",         # "Sookha Bhujia Bhel"
    "%paratha%",      # "Papad Parathas"
    "%puri%",         # "Sev Puri"
    "%dalna%",        # "Papad Er Dalna"
    "%tamatar%",      # "Sev Tamatar", "Rajasthani Sev Tamatar Ki Sabzi"
    "%sabzi%",        # "Rajasthani Sev Tamatar Ki Sabzi"
]

EXCLUSION_IDS = [
    316,   # Karela bhujia — vegetable stir-fry, not namkeen
    2695,  # Bihari Shakarkand Bhujia — sweet potato sabzi, not namkeen
    2767,  # South Indian Papad Curry — curry dish, not a condiment
]


def _build_where(start: int = 1) -> tuple[str, list]:
    include = " OR ".join(
        f"recipe_name ~* ${start + i}" for i in range(len(CONDIMENT_PATTERNS))
    )
    p = start + len(CONDIMENT_PATTERNS)
    exclude = " AND ".join(
        f"LOWER(recipe_name) NOT LIKE ${p + i}" for i in range(len(EXCLUSION_PATTERNS))
    )
    id_list = ", ".join(str(i) for i in EXCLUSION_IDS)
    params = list(CONDIMENT_PATTERNS) + list(EXCLUSION_PATTERNS)
    where = (
        f"({include})"
        f" AND ({exclude})"
        f" AND id NOT IN ({id_list})"
        f" AND slot_type != 'condiment'"
    )
    return where, params


async def run(commit: bool) -> None:
    conn = await asyncpg.connect(DSN)

    where_clause, params = _build_where(1)

    # ── Fetch candidates ──────────────────────────────────────────────────────
    select_sql = f"""
        SELECT id, recipe_name, slot_type
        FROM food_items
        WHERE {where_clause}
        ORDER BY recipe_name
    """
    rows = await conn.fetch(select_sql, *params)

    print(f"Condiment migration — {'DRY RUN' if not commit else 'COMMIT MODE'}")
    print(f"Recipes to migrate: {len(rows)}\n")
    print(f"{'ID':>6}  {'Current slot_type':18}  Recipe name")
    print("-" * 72)
    for r in rows:
        print(f"{r['id']:>6}  {r['slot_type']:18}  {r['recipe_name']}")

    if not commit:
        print("\n[DRY RUN] No changes made. Re-run with --commit to apply.")
        await conn.close()
        return

    # ── Commit ────────────────────────────────────────────────────────────────
    print(f"\nApplying UPDATE to {len(rows)} rows...")
    update_sql = f"""
        UPDATE food_items
        SET slot_type = 'condiment'
        WHERE {where_clause}
    """
    result = await conn.execute(update_sql, *params)
    count = int(result.split()[-1])
    print(f"Updated: {count} rows")

    # Verify
    verify_count = await conn.fetchval(
        "SELECT COUNT(*) FROM food_items WHERE slot_type = 'condiment'"
    )
    print(f"food_items with slot_type='condiment': {verify_count}")

    await conn.close()


if __name__ == "__main__":
    commit = "--commit" in sys.argv
    asyncio.run(run(commit))
