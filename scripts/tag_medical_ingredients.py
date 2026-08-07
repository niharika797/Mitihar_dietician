"""
Medical ingredient tagging — avoid_pcos and avoid_gout.

Sends all 950 ingredients to Claude CLI in batches of 50.
Claude identifies which ingredients should carry avoid_pcos / avoid_gout tags.
Updates ingredients.avoid_tags JSONB column in DB.
Propagates updated tags to food_items via scripts/derive_recipe_tags.py.

Run: python -m scripts.tag_medical_ingredients
Checkpoint: data/review/tag_medical_checkpoint.json
Rollback: UPDATE ingredients SET avoid_tags = '[]' WHERE avoid_tags ?| array['avoid_pcos','avoid_gout'];
"""

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.core.database import AsyncSessionLocal

CHECKPOINT_FILE = str(Path(__file__).resolve().parent.parent / "data" / "review" / "tag_medical_checkpoint.json")
BATCH_SIZE = 50
BATCH_SLEEP = 3


# ── Prompt ────────────────────────────────────────────────────────────────────

def build_tag_prompt(ingredients: list[dict]) -> str:
    ing_json = json.dumps(
        {str(i["id"]): i["name"] for i in ingredients},
        ensure_ascii=False,
        indent=2
    )
    return f"""You are a clinical dietitian tagging ingredients for an Indian nutrition platform.

For each ingredient, determine if it should carry these medical avoidance tags:

avoid_pcos: Tag ingredients that worsen PCOS symptoms. Include:
- Refined carbohydrates: maida, white rice (not brown), white bread, refined flour,
  corn syrup, white pasta, semolina (unless whole grain)
- High-GI foods: potato (in large amounts), white sugar, jaggery (moderate — only
  tag if clearly high-GI refined sugar)
- Full-fat dairy in excess: cream, butter, ghee (tag only if primary ingredient)
- Processed/refined oils and trans fats
- Refined sugar, candy, sweets base ingredients
Do NOT tag: whole grains, vegetables, lentils, spices, herbs, most fruits,
lean proteins, low-fat dairy

avoid_gout: Tag ingredients that trigger gout flares. Include:
- Organ meats: liver, kidney, brain, heart
- Red meat: mutton, lamb, goat (high purine)
- Shellfish: prawns, shrimp, crab, lobster, oyster
- Oily fish: sardines, anchovies, mackerel, herring
- High-purine pulses: rajma (red kidney beans), urad dal, masoor dal
  (tag only if clearly high-purine variant)
- Yeast extracts, beer-based ingredients
Do NOT tag: most vegetables, low-purine lentils (moong, chana), fruits,
dairy, eggs, most spices

Rules:
- Only tag if clearly indicated — when in doubt, do NOT tag
- An ingredient can have both tags, one tag, or no tags
- Indian ingredient names may appear in Hindi/regional — use your knowledge
- Return ONLY a JSON object mapping id (string) to array of applicable tags

Example output:
{{
  "12": ["avoid_pcos"],
  "45": ["avoid_gout"],
  "67": ["avoid_pcos", "avoid_gout"],
  "89": []
}}

Every id in the input must appear in the output (empty array if no tags).
No explanation. No markdown. Just the JSON.

Ingredients to tag:
{ing_json}"""


# ── Claude CLI ────────────────────────────────────────────────────────────────

def call_claude_cli(prompt: str) -> dict:
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True,
        text=True,
        timeout=180,
        encoding="utf-8"
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI error: {result.stderr.strip()}")
    raw = result.stdout.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        if raw.startswith("json"):
            raw = raw[4:].strip()
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Extract first complete JSON object — handles trailing text after the JSON
        start = raw.index("{")
        end = raw.rindex("}") + 1
        return json.loads(raw[start:end])


# ── Checkpoint ────────────────────────────────────────────────────────────────

def load_checkpoint() -> set:
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return set(json.load(f).get("done_ids", []))
    return set()


def save_checkpoint(done_ids: set) -> None:
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"done_ids": list(done_ids), "last_run": datetime.now().isoformat()}, f)


# ── Main ─────────────────────────────────────────────────────────────────────

async def main() -> None:
    print(f"Medical ingredient tagging — started {datetime.now().isoformat()}")
    print("Rollback: UPDATE ingredients SET avoid_tags = '[]' WHERE avoid_tags ?| array['avoid_pcos','avoid_gout'];\n")

    async with AsyncSessionLocal() as db:
        # Step 1: load all ingredients
        result = await db.execute(text(
            "SELECT id, name, avoid_tags, prefer_tags FROM ingredients ORDER BY id"
        ))
        rows = result.fetchall()
        ingredients = [
            {
                "id": r.id,
                "name": r.name,
                "current_avoid_tags": list(r.avoid_tags or []),
                "current_prefer_tags": list(r.prefer_tags or []),
            }
            for r in rows
        ]
        print(f"Total ingredients: {len(ingredients)}")

        # Step 2: load checkpoint
        done_ids = load_checkpoint()
        remaining = [i for i in ingredients if i["id"] not in done_ids]
        print(f"Already processed: {len(done_ids)} | Remaining: {len(remaining)}\n")

        # Step 3: process in batches
        newly_tagged_pcos = 0
        newly_tagged_gout = 0
        newly_tagged_both = 0
        sample_tagged = []

        for batch_start in range(0, len(remaining), BATCH_SIZE):
            batch = remaining[batch_start:batch_start + BATCH_SIZE]
            batch_ids = [i["id"] for i in batch]
            print(f"Batch {batch_start // BATCH_SIZE + 1}: IDs {batch_ids[0]}–{batch_ids[-1]}")

            try:
                prompt = build_tag_prompt(batch)
                tag_result = call_claude_cli(prompt)

                # Step 4: apply tags — union with existing, write only if changed
                changed_in_batch = 0
                for ing in batch:
                    ing_id = str(ing["id"])
                    new_tags = set(tag_result.get(ing_id, []))
                    if not new_tags:
                        continue

                    existing = set(ing["current_avoid_tags"])
                    merged = sorted(existing | new_tags)

                    if merged != sorted(existing):
                        await db.execute(
                            text("UPDATE ingredients SET avoid_tags = :tags WHERE id = :id"),
                            {"tags": json.dumps(merged), "id": ing["id"]}
                        )
                        changed_in_batch += 1

                        has_pcos = "avoid_pcos" in new_tags
                        has_gout = "avoid_gout" in new_tags
                        if has_pcos and has_gout:
                            newly_tagged_both += 1
                        elif has_pcos:
                            newly_tagged_pcos += 1
                        elif has_gout:
                            newly_tagged_gout += 1

                        if len(sample_tagged) < 10:
                            sample_tagged.append((ing["id"], ing["name"], sorted(new_tags)))

                await db.commit()
                done_ids.update(batch_ids)
                save_checkpoint(done_ids)
                print(f"  Tagged {changed_in_batch}/{len(batch)} ingredients in this batch")

                if batch_start + BATCH_SIZE < len(remaining):
                    print(f"  Sleeping {BATCH_SLEEP}s...")
                    time.sleep(BATCH_SLEEP)

            except Exception as e:
                print(f"  ERROR on batch starting {batch_ids[0]}: {e}")
                print("  Checkpoint saved. Re-run to resume from this batch.")
                return

    # Step 5: propagate to food_items via derive_recipe_tags.py
    print("\nPropagating to food_items via derive_recipe_tags.py...")
    proc = subprocess.run(
        ["python", "-m", "scripts.derive_recipe_tags"],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    if proc.returncode != 0:
        print(f"  ERROR in derive_recipe_tags: {proc.stderr.strip()}")
    else:
        print(proc.stdout)

    # Step 7: final report
    print("=== Final Report ===")
    print(f"  Ingredients tagged avoid_pcos only : {newly_tagged_pcos}")
    print(f"  Ingredients tagged avoid_gout only : {newly_tagged_gout}")
    print(f"  Ingredients tagged both            : {newly_tagged_both}")
    print(f"  Total newly tagged                 : {newly_tagged_pcos + newly_tagged_gout + newly_tagged_both}")
    if sample_tagged:
        print("\n  Sample (up to 10 newly tagged ingredients):")
        for ing_id, name, tags in sample_tagged:
            print(f"    [{ing_id}] {name}: {tags}")

    print(f"\nDone — {datetime.now().isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
