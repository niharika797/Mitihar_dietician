"""
Task 4 — Seed nutrition values for ingredients with NULL nutrition.

Strategy: batch 20 ingredients per LLM call, parse JSON array response.
Uses llama-server on http://localhost:11434 (OpenAI-compatible /v1/chat/completions).
Marks source as 'estimated_llm'.
Saves checkpoint after every batch — safe to re-run.
"""
import asyncio
import json
import sys
import os
import re
import time

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal

LLAMA_URL = "http://localhost:11434/v1/chat/completions"
BATCH_SIZE = 20


PROMPT_TEMPLATE = """\
You are a nutrition database. For each Indian cooking ingredient listed, \
return ONLY a JSON array (no markdown, no extra text) where each element has:
{{"name": "<exact input name>", "calories": <number>, "protein_g": <number>, \
"carbs_g": <number>, "fat_g": <number>, "fiber_g": <number>}}
All values are per 100g of the raw ingredient as used in Indian cooking.
Use 0.0 for negligible values. Never use null.

Ingredients:
{ingredient_list}"""


def parse_llm_response(content: str) -> list[dict]:
    """Extract JSON array from model output, tolerating markdown fences."""
    # Strip markdown code fences if present
    content = re.sub(r'```(?:json)?\s*', '', content).strip()
    # Find first '[' to last ']'
    start = content.find('[')
    end = content.rfind(']')
    if start == -1 or end == -1:
        return []
    try:
        return json.loads(content[start:end + 1])
    except json.JSONDecodeError:
        return []


async def call_llm(names: list[str]) -> list[dict]:
    ingredient_list = "\n".join(f"- {n}" for n in names)
    payload = {
        "model": "gemma",
        "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(ingredient_list=ingredient_list)}],
        "temperature": 0.1,
        "max_tokens": 2048,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(LLAMA_URL, json=payload)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return parse_llm_response(content)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # Load all ingredients with NULL nutrition
        result = await db.execute(text("""
            SELECT id, name FROM ingredients
            WHERE calories_per_100g IS NULL
            ORDER BY name
        """))
        pending = result.fetchall()
        print(f"Ingredients needing nutrition: {len(pending)}")

        if not pending:
            print("All ingredients already have nutrition. Nothing to do.")
            return

        total = len(pending)
        done = 0
        failed_names: list[str] = []

        for batch_start in range(0, total, BATCH_SIZE):
            batch = pending[batch_start:batch_start + BATCH_SIZE]
            names = [row[1] for row in batch]
            id_by_name = {row[1]: row[0] for row in batch}

            print(f"Batch {batch_start // BATCH_SIZE + 1}/{(total + BATCH_SIZE - 1) // BATCH_SIZE}: {names[0]} ... {names[-1]}")

            try:
                results = await call_llm(names)
            except Exception as e:
                print(f"  LLM call failed: {e}")
                failed_names.extend(names)
                continue

            matched = 0
            for item in results:
                name = item.get("name", "")
                if name not in id_by_name:
                    # Try case-insensitive match
                    lower_map = {k.lower(): k for k in id_by_name}
                    if name.lower() in lower_map:
                        name = lower_map[name.lower()]
                    else:
                        continue

                ing_id = id_by_name[name]
                await db.execute(text("""
                    UPDATE ingredients SET
                        calories_per_100g = :cal,
                        protein_per_100g  = :pro,
                        carbs_per_100g    = :carb,
                        fat_per_100g      = :fat,
                        fiber_per_100g    = :fib,
                        source            = 'estimated_llm'
                    WHERE id = :id
                """), {
                    "cal":  float(item.get("calories", 0) or 0),
                    "pro":  float(item.get("protein_g", 0) or 0),
                    "carb": float(item.get("carbs_g", 0) or 0),
                    "fat":  float(item.get("fat_g", 0) or 0),
                    "fib":  float(item.get("fiber_g", 0) or 0),
                    "id":   ing_id,
                })
                matched += 1
                done += 1

            await db.commit()
            print(f"  Matched and saved: {matched}/{len(batch)}")

            # Brief pause to avoid GPU thermal throttle
            time.sleep(0.5)

        print(f"\nDone. Total saved: {done}/{total}")
        if failed_names:
            print(f"Failed batches ({len(failed_names)} ingredients): {failed_names[:10]}...")

        # Final stats
        stats = await db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE calories_per_100g IS NOT NULL) AS filled,
                COUNT(*) FILTER (WHERE calories_per_100g IS NULL)     AS still_null,
                COUNT(*)                                               AS total
            FROM ingredients
        """))
        row = stats.fetchone()
        print(f"Final: {row[0]} filled / {row[1]} still NULL / {row[2]} total")


if __name__ == "__main__":
    asyncio.run(main())
