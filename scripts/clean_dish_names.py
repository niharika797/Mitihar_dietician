"""
Dish name cleanup pipeline — 4-pass hybrid approach.
Run with: python -m scripts.clean_dish_names

Passes:
  A — Soft-delete test artifacts (is_verified=False)
  B — Rule-based Title Case fix via PostgreSQL initcap()
  C — LLM rename for genuinely ambiguous names only (~85 dishes)
  D — Report: summary of all changes made

Safe to re-run: each pass checks state before acting.
Rollback: UPDATE food_items SET recipe_name = original_name WHERE original_name IS NOT NULL;
"""

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

from app.core.database import AsyncSessionLocal

# ── Constants ──────────────────────────────────────────────────────────────────

# Test artifacts confirmed from audit — soft-flag these, do not hard delete
# (hard delete risks breaking weekly_combos FK references)
TEST_ARTIFACT_NAMES = [
    'Global Test Recipe',
    'Test Dal Tadka',
    'Test Recipe',
    'Test Dish',
]

# Checkpoint file for Pass C (LLM pass) — resume-safe
LLM_CHECKPOINT_FILE = str(Path(__file__).resolve().parent.parent / "data" / "review" / "clean_dishes_llm_checkpoint.json")

# Batch size for LLM pass — small to stay within rate limits
LLM_BATCH_SIZE = 20

# Sleep between LLM batches (seconds)
LLM_BATCH_SLEEP = 3


# ── Pass A — Soft-flag test artifacts ─────────────────────────────────────────

async def pass_a_flag_test_artifacts(db):
    print("\n=== PASS A: Soft-flag test artifacts ===")

    placeholders = ", ".join(f":name_{i}" for i in range(len(TEST_ARTIFACT_NAMES)))
    params = {f"name_{i}": name for i, name in enumerate(TEST_ARTIFACT_NAMES)}

    # Count before
    result = await db.execute(
        text(f"SELECT count(*) FROM food_items WHERE recipe_name IN ({placeholders})"),
        params
    )
    count = result.scalar()
    print(f"  Found {count} test artifact rows")

    if count == 0:
        print("  Nothing to flag — skipping")
        return 0

    # Soft-flag: set is_verified=False so they're excluded from generation pool
    await db.execute(
        text(f"""
            UPDATE food_items
            SET is_verified = False
            WHERE recipe_name IN ({placeholders})
        """),
        params
    )
    await db.commit()

    print(f"  Flagged {count} rows as is_verified=False")
    return count


# ── Pass B — Rule-based Title Case fix ────────────────────────────────────────

async def pass_b_title_case(db):
    print("\n=== PASS B: Rule-based Title Case fix ===")

    # Count dishes where initcap would change the name
    result = await db.execute(text("""
        SELECT count(*) FROM food_items
        WHERE recipe_name != initcap(recipe_name)
          AND is_verified = True
    """))
    count = result.scalar()
    print(f"  Found {count} dishes with casing issues")

    if count == 0:
        print("  Nothing to fix — skipping")
        return 0

    # Preview sample before applying
    sample = await db.execute(text("""
        SELECT id, recipe_name, initcap(recipe_name) as fixed
        FROM food_items
        WHERE recipe_name != initcap(recipe_name)
          AND is_verified = True
        LIMIT 10
    """))
    rows = sample.fetchall()
    print("  Sample changes:")
    for row in rows:
        print(f"    [{row.id}] '{row.recipe_name}' → '{row.fixed}'")

    # Apply
    await db.execute(text("""
        UPDATE food_items
        SET recipe_name = initcap(recipe_name)
        WHERE recipe_name != initcap(recipe_name)
          AND is_verified = True
    """))
    await db.commit()

    print(f"  Fixed {count} dishes")
    return count


# ── Pass C — LLM rename for ambiguous names ───────────────────────────────────

def build_llm_prompt(dishes: list) -> str:
    """
    dishes: list of {id, recipe_name, slot_type, diet_type}
    """
    dish_json = json.dumps(
        {str(d["id"]): {
            "name": d["recipe_name"],
            "slot_type": d["slot_type"],
            "diet_type": d["diet_type"]
        } for d in dishes},
        ensure_ascii=False,
        indent=2
    )

    return f"""You are renaming dishes for a clinical Indian nutrition platform used by dietitians.

Rules:
- Rename ONLY if the name is too generic, single-word, or clearly incomplete.
- If the name is already specific and natural (e.g. "Masala Dosa", "Rajma Chawal"), return it UNCHANGED.
- Renamed dishes must be 2-4 words, authentic Indian name, Title Case.
- Use slot_type and diet_type as context clues:
  - slot_type "grain" → rice/roti/bread dishes
  - slot_type "dal_protein" → lentil/legume/protein dishes
  - slot_type "sabzi" → vegetable side dishes
  - slot_type "one_pot" → complete meal dishes
  - slot_type "main_dish" → primary meal items
- Never invent ingredients not implied by the name.
- Never add regional qualifiers unless the name implies it.

Return ONLY a JSON object mapping id (string) to renamed dish (string).
No explanation. No markdown. No extra keys. Just the JSON.

Example:
Input: {{"290": {{"name": "Rice", "slot_type": "grain", "diet_type": "Vegetarian"}}}}
Output: {{"290": "Steamed Basmati Rice"}}

Dishes to process:
{dish_json}"""


async def call_claude_cli(prompt: str) -> dict:
    """Call Claude Code CLI in non-interactive mode and return parsed JSON."""
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=120,
        encoding="utf-8"
    )

    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI error: {result.stderr.strip()}")

    raw = result.stdout.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        if raw.startswith("json"):
            raw = raw[4:].strip()

    return json.loads(raw.strip())


async def pass_c_llm_rename(db):
    print("\n=== PASS C: LLM rename for ambiguous names ===")

    # Load checkpoint
    done_ids = set()
    if os.path.exists(LLM_CHECKPOINT_FILE):
        with open(LLM_CHECKPOINT_FILE) as f:
            done_ids = set(json.load(f).get("done_ids", []))
        print(f"  Checkpoint: {len(done_ids)} already processed")

    # Fetch candidate dishes — short/single-word names only
    result = await db.execute(text("""
        SELECT id, recipe_name, slot_type, diet_type
        FROM food_items
        WHERE is_verified = True
          AND (
            length(recipe_name) <= 8
            OR recipe_name NOT LIKE '% %'
          )
        ORDER BY id
    """))
    candidates = [
        {"id": row.id, "recipe_name": row.recipe_name,
         "slot_type": row.slot_type, "diet_type": row.diet_type}
        for row in result.fetchall()
        if row.id not in done_ids
    ]

    print(f"  Candidates remaining: {len(candidates)}")
    if not candidates:
        print("  All candidates already processed — skipping")
        return 0

    total_changed = 0
    all_done_ids = list(done_ids)

    # Process in batches
    for i in range(0, len(candidates), LLM_BATCH_SIZE):
        batch = candidates[i:i + LLM_BATCH_SIZE]
        batch_ids = [d["id"] for d in batch]
        print(f"  Batch {i//LLM_BATCH_SIZE + 1}: IDs {batch_ids[0]}–{batch_ids[-1]}")

        try:
            prompt = build_llm_prompt(batch)
            renamed = await call_claude_cli(prompt)

            # Apply changes
            changed_in_batch = 0
            for dish in batch:
                dish_id = str(dish["id"])
                new_name = renamed.get(dish_id, dish["recipe_name"]).strip()

                if new_name and new_name != dish["recipe_name"]:
                    await db.execute(
                        text("UPDATE food_items SET recipe_name = :name WHERE id = :id"),
                        {"name": new_name, "id": dish["id"]}
                    )
                    print(f"    [{dish['id']}] '{dish['recipe_name']}' → '{new_name}'")
                    changed_in_batch += 1

            await db.commit()
            total_changed += changed_in_batch
            all_done_ids.extend(batch_ids)

            # Save checkpoint after every batch
            with open(LLM_CHECKPOINT_FILE, "w") as f:
                json.dump({"done_ids": all_done_ids, "last_run": datetime.now().isoformat()}, f)

            print(f"    Changed: {changed_in_batch}/{len(batch)}")

            if i + LLM_BATCH_SIZE < len(candidates):
                print(f"    Sleeping {LLM_BATCH_SLEEP}s...")
                time.sleep(LLM_BATCH_SLEEP)

        except Exception as e:
            print(f"  ERROR on batch starting {batch_ids[0]}: {e}")
            print("  Checkpoint saved. Re-run to resume from this batch.")
            break

    print(f"  Total renamed in Pass C: {total_changed}")
    return total_changed


# ── Pass D — Summary report ────────────────────────────────────────────────────

async def pass_d_report(db, a_count, b_count, c_count):
    print("\n=== PASS D: Final report ===")

    result = await db.execute(text("""
        SELECT
            count(*) as total,
            count(*) FILTER (WHERE is_verified = True) as verified,
            count(*) FILTER (WHERE is_verified = False) as unverified,
            count(*) FILTER (WHERE original_name != recipe_name) as changed,
            count(*) FILTER (WHERE original_name = recipe_name) as unchanged
        FROM food_items
    """))
    row = result.fetchone()

    print(f"""
  Total food_items      : {row.total}
  Verified (in pool)    : {row.verified}
  Unverified (excluded) : {row.unverified}
  Names changed         : {row.changed}
  Names unchanged       : {row.unchanged}

  Pass A (test artifacts flagged) : {a_count}
  Pass B (casing fixes)           : {b_count}
  Pass C (LLM renames)            : {c_count}
  Total changes                   : {a_count + b_count + c_count}
    """)

    # Sample of changed names
    sample = await db.execute(text("""
        SELECT id, original_name, recipe_name, slot_type
        FROM food_items
        WHERE original_name != recipe_name
        ORDER BY id
        LIMIT 20
    """))
    rows = sample.fetchall()
    if rows:
        print("  Sample of changes:")
        for r in rows:
            print(f"    [{r.id}] '{r.original_name}' → '{r.recipe_name}' ({r.slot_type})")


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    print(f"Dish name cleanup pipeline — started {datetime.now().isoformat()}")
    print("Rollback if needed: UPDATE food_items SET recipe_name = original_name WHERE original_name IS NOT NULL;\n")

    async with AsyncSessionLocal() as db:
        # Verify snapshot exists
        result = await db.execute(text(
            "SELECT count(*) FROM food_items WHERE original_name IS NOT NULL"
        ))
        snapshot_count = result.scalar()
        if snapshot_count == 0:
            print("ERROR: original_name snapshot is empty. Run the migration and snapshot first.")
            print("  alembic upgrade head")
            print("  UPDATE food_items SET original_name = recipe_name WHERE original_name IS NULL;")
            return

        print(f"Snapshot verified: {snapshot_count} rows have original_name set.")

        a = await pass_a_flag_test_artifacts(db)
        b = await pass_b_title_case(db)
        c = await pass_c_llm_rename(db)
        await pass_d_report(db, a, b, c)

    print(f"\nDone — {datetime.now().isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
