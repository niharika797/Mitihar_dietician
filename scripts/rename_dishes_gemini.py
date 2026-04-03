"""
scripts/rename_dishes_gemini.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Task 5 — One-time batch job: rename all food_items to simple
Indian names using Gemini 2.5 Flash-Lite (free tier).

BILLING SAFETY
──────────────
This script uses the FREE tier only. As long as your Google Cloud
project has NO billing account linked, you CANNOT be charged.
The API will return HTTP 429 when the daily cap is hit — the
script will stop cleanly and resume next run from a checkpoint.

FREE TIER LIMITS (per project, not per key)
────────────────────────────────────────────
  • 15 RPM  (requests per minute)
  • ~1500 RPD (requests per day — resets midnight Pacific)

At 20 dishes per batch → up to 30,000 dishes per day.
The script enforces a 5s delay between batches (12 RPM) to stay
well under the 15 RPM cap with comfortable headroom.

USAGE
─────
  # Preview what would change — no DB writes:
  python -m scripts.rename_dishes_gemini --dry-run

  # Apply changes:
  python -m scripts.rename_dishes_gemini

RESUMING
────────
Progress is saved to rename_checkpoint.json after every batch.
If the script stops (rate limit, crash, Ctrl+C), just re-run it —
it picks up exactly where it left off. Never re-processes a dish.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import (
    create_async_engine, async_sessionmaker, AsyncSession,
)

# ── Config ────────────────────────────────────────────────────
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    sys.exit("❌  DATABASE_URL not found in .env")

# Use only ONE key — all keys share the same project quota.
# Rotation across keys gives zero extra RPD/RPM.
GEMINI_KEY = next(
    (v for k, v in sorted(os.environ.items())
     if k.startswith("GEMINI_API_KEY") and v.strip()),
    None,
)
if not GEMINI_KEY:
    sys.exit("❌  No GEMINI_API_KEY_* found in .env")

MODEL         = "gemini-2.5-flash-lite"   # current free-tier model
BATCH_SIZE    = 20                         # dishes per API call
DELAY_SECS    = 5.0                        # between batches → 12 RPM (safe under 15)
MAX_RETRIES   = 3                          # on 429 / transient errors
DRY_RUN       = "--dry-run" in sys.argv

CHECKPOINT    = Path("rename_checkpoint.json")
BACKUP        = Path("rename_dishes_backup.json")

PROMPT_TEMPLATE = """You are a nutrition expert who knows Indian food very well.
Below is a numbered list of Indian dish names. Some have awkward English translations.
For each dish, provide the simple, commonly used Indian name people actually call it.
Keep it short (2-5 words). If the name is already natural and simple, return it unchanged.
Return ONLY a valid JSON object mapping each number (as a string key) to the simplified name.
No explanation. No markdown fences. Just the raw JSON.

Example output: {{"1": "Masala Dosa", "2": "Dal Tadka", "3": "Aloo Sabzi"}}

Dishes:
{dishes}"""

# ── Checkpoint helpers ────────────────────────────────────────

def load_checkpoint() -> set[int]:
    """Return set of food_item IDs already processed."""
    if CHECKPOINT.exists():
        data = json.loads(CHECKPOINT.read_text())
        return set(data.get("done_ids", []))
    return set()

def save_checkpoint(done_ids: set[int]) -> None:
    CHECKPOINT.write_text(
        json.dumps({"done_ids": sorted(done_ids)}, indent=2)
    )

# ── Gemini API call with retry ────────────────────────────────

async def call_gemini(
    dish_batch: list[tuple[int, str]],
) -> dict[int, str]:
    """
    Send a batch of (food_id, name) to Gemini.
    Returns {food_id: new_name} for dishes that should be renamed.
    Returns {} on unrecoverable error (batch is skipped, not retried).
    """
    numbered = "\n".join(
        f"{i+1}. {name}" for i, (_, name) in enumerate(dish_batch)
    )
    prompt  = PROMPT_TEMPLATE.format(dishes=numbered)
    url     = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent?key={GEMINI_KEY}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, json=payload)

            if resp.status_code == 429:
                # Rate limited — could be RPM or RPD cap
                retry_after = int(resp.headers.get("Retry-After", 60))
                if attempt < MAX_RETRIES:
                    print(
                        f"\n  ⏳  Rate limited (429). "
                        f"Waiting {retry_after}s before retry {attempt}/{MAX_RETRIES-1}…"
                    )
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    print(
                        "\n  🛑  Daily quota likely exhausted. "
                        "Re-run tomorrow to continue from checkpoint."
                    )
                    sys.exit(0)   # clean exit — checkpoint already saved

            if resp.status_code != 200:
                print(f"\n  ⚠️  HTTP {resp.status_code} — skipping batch")
                return {}

            # Parse response
            raw = (
                resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            ).strip()
            # Strip markdown fences if Gemini wraps output
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1] if len(parts) > 1 else raw
                if raw.startswith("json"):
                    raw = raw[4:]
            mapping: dict[str, str] = json.loads(raw.strip())

            # Map back to food_ids
            result: dict[int, str] = {}
            for i, (food_id, _) in enumerate(dish_batch):
                new_name = mapping.get(str(i + 1))
                if new_name and isinstance(new_name, str):
                    result[food_id] = new_name.strip()
            return result

        except (json.JSONDecodeError, KeyError) as e:
            print(f"\n  ⚠️  Parse error ({e}) — skipping batch")
            return {}
        except httpx.TimeoutException:
            if attempt < MAX_RETRIES:
                print(f"\n  ⚠️  Timeout — retrying ({attempt}/{MAX_RETRIES-1})…")
                await asyncio.sleep(5 * attempt)
            else:
                print("\n  ⚠️  Timeout after max retries — skipping batch")
                return {}

    return {}

# ── Main ──────────────────────────────────────────────────────

async def main() -> None:
    engine  = create_async_engine(DATABASE_URL, echo=False, future=True)
    Session = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    from app.models.db_models import FoodItem

    # Load all dishes
    async with Session() as session:
        result = await session.execute(
            select(FoodItem.id, FoodItem.recipe_name).order_by(FoodItem.id)
        )
        all_rows: list[tuple[int, str]] = list(result.all())  # type: ignore

    total = len(all_rows)
    print(f"\n📦  Total dishes in DB : {total}")
    print(f"🔍  Mode               : {'DRY RUN (no DB writes)' if DRY_RUN else 'LIVE'}")
    print(f"⚙️   Model              : {MODEL}")
    print(f"⏱️   Delay between calls: {DELAY_SECS}s  (~{60/DELAY_SECS:.0f} RPM)\n")

    # Backup originals once
    if not BACKUP.exists():
        BACKUP.write_text(
            json.dumps(
                {str(r[0]): r[1] for r in all_rows},
                ensure_ascii=False, indent=2,
            )
        )
        print(f"💾  Backup saved → {BACKUP}")

    # Load checkpoint — skip already processed dishes
    done_ids = load_checkpoint()
    pending  = [r for r in all_rows if r[0] not in done_ids]
    skipped_already = total - len(pending)

    if skipped_already:
        print(f"⏭️   Already processed  : {skipped_already} dishes (from checkpoint)")
    print(f"📋  Remaining          : {len(pending)} dishes\n")

    if not pending:
        print("✅  All dishes already processed. Nothing to do.")
        return

    batches = [
        pending[i : i + BATCH_SIZE]
        for i in range(0, len(pending), BATCH_SIZE)
    ]
    print(f"📬  Batches to process : {len(batches)} × {BATCH_SIZE} dishes each")
    print(f"⏳  Est. time          : ~{len(batches) * DELAY_SECS / 60:.1f} minutes\n")

    renamed = 0
    unchanged = 0

    async with Session() as session:
        for b_idx, batch in enumerate(batches, 1):
            print(
                f"  [{b_idx:>3}/{len(batches)}] "
                f"{batch[0][1][:30]:.<35}",
                end=" ",
                flush=True,
            )

            mapping = await call_gemini(batch)

            batch_renamed = 0
            for food_id, original_name in batch:
                new_name = mapping.get(food_id)

                # Skip if no suggestion or same name
                if not new_name or new_name.lower() == original_name.lower():
                    unchanged += 1
                    done_ids.add(food_id)
                    continue

                print(f"\n      🔄  {original_name!r:40} → {new_name!r}")
                if not DRY_RUN:
                    await session.execute(
                        update(FoodItem)
                        .where(FoodItem.id == food_id)
                        .values(recipe_name=new_name)
                    )
                renamed += 1
                batch_renamed += 1
                done_ids.add(food_id)

            if not DRY_RUN:
                await session.commit()

            # Save checkpoint after every batch
            if not DRY_RUN:
                save_checkpoint(done_ids)

            if batch_renamed == 0:
                print("✅ (no changes)")
            else:
                print(f"✅ ({batch_renamed} renamed)")

            # Respectful delay — stay under 15 RPM free tier limit
            if b_idx < len(batches):
                await asyncio.sleep(DELAY_SECS)

    await engine.dispose()

    print(f"\n{'═'*50}")
    print(f"✅  Renamed   : {renamed}")
    print(f"⏭️   Unchanged : {unchanged}")
    if DRY_RUN:
        print("\n⚠️  DRY RUN — no changes written to DB")
    else:
        print(f"\n💾  Checkpoint saved → {CHECKPOINT}")
        print("    Re-run any time to process remaining dishes.")
    print("Done.\n")


if __name__ == "__main__":
    asyncio.run(main())
