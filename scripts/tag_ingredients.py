"""
Layer 1 — Ingredient tagging (clinical source of truth).

Tags each ingredient in the ingredients table based on inherent nutritional
and biochemical properties only. No dish context. No cooking method logic.

Usage:
    python -m scripts.tag_ingredients            # live run (writes to DB)
    python -m scripts.tag_ingredients --dry-run  # prints what would be written, no DB writes

Resumable: skips ingredients where avoid_tags is already non-empty.
Also skips measurement-phrase artifacts (NULL calories_per_100g).
Threshold: confidence >= 0.85 -> write to DB.
           0.25–0.84         -> append to docs/INGREDIENT_REVIEW.md.
           < 0.25            -> discard.
"""
import asyncio
import json
import re
import sys
import time
from pathlib import Path

import asyncpg
import httpx

# ── Config ────────────────────────────────────────────────────────────────────
DSN = "postgresql://admin:mityahar_dev@localhost:5432/mityahar_db"
LLAMA_URL = "http://localhost:11434/v1/chat/completions"
LLAMA_MODEL = "gemma"
REVIEW_PATH = Path(__file__).parent.parent / "docs" / "INGREDIENT_REVIEW.md"
BATCH_SIZE = 50
TIMEOUT_S = 90
AUTO_ACCEPT_THRESHOLD = 0.85
DISCARD_THRESHOLD = 0.25

VALID_TAGS = {
    "avoid_diabetes", "diabetes_friendly",
    "avoid_hypertension", "heart_friendly",
    "avoid_hypothyroid", "thyroid_support",
    "avoid_hyperthyroid",
    "avoid_pcos", "pcos_friendly",
    "avoid_highchol", "cholesterol_friendly",
    "avoid_kidney",
    "avoid_gluten", "gluten_free",
    "avoid_ibs", "gut_friendly",
    "avoid_fattyliver", "liver_friendly",
    "avoid_gout",
    "calcium_rich",
    "iron_rich",
    "avoid_heart",
}

AVOID_TAGS = {t for t in VALID_TAGS if t.startswith("avoid_")}
PREFER_TAGS = VALID_TAGS - AVOID_TAGS

# ── Ingredient-level system prompt ────────────────────────────────────────────
# Adapted from MEDICAL_TAGGING_KB_COMPACT.md.
# Cooking method rules, achaar override, and dish-context rules REMOVED.
# Only inherent ingredient biochemistry applies.

INGREDIENT_SYSTEM_PROMPT = """
You are a clinical nutrition tagging system evaluating INDIVIDUAL INGREDIENTS.

Given an ingredient name, assign tags that reflect the ingredient's INHERENT biochemical and nutritional properties only.
Output JSON only. No prose.

## EVALUATION RULES
- Evaluate the ingredient IN ISOLATION — no dish context, no cooking method.
- Cooking method rules (fried/baked/steamed effects) DO NOT APPLY.
- Pickle/achaar override rules DO NOT APPLY.
- Only the ingredient's inherent nutritional or biochemical properties matter.
- If your reasoning says an ingredient is safe or beneficial for a condition, do NOT assign the avoid tag for that condition. Reasoning and tag must be consistent.

## VALID TAGS (use ONLY these 22)
avoid_diabetes, diabetes_friendly, avoid_hypertension, heart_friendly,
avoid_hypothyroid, thyroid_support, avoid_hyperthyroid, avoid_pcos, pcos_friendly,
avoid_highchol, cholesterol_friendly, avoid_kidney, avoid_gluten, gluten_free,
avoid_ibs, gut_friendly, avoid_fattyliver, liver_friendly, avoid_gout,
calcium_rich, iron_rich, avoid_heart

## INGREDIENT TAG RULES

### High-GI / blood-sugar impact (avoid_diabetes)
- White sugar → avoid_diabetes, avoid_fattyliver (fructose), avoid_gout (fructose)
- Jaggery, honey → avoid_diabetes (high GI), avoid_fattyliver, iron_rich (jaggery only)
- Maida (refined wheat flour) → avoid_diabetes
- White rice → mild avoid_diabetes (high GI, moderate confidence ≤ 0.6)
- Potato → mild avoid_diabetes (high GI, confidence ≤ 0.5)

### Low-GI / diabetes-protective (diabetes_friendly)
- Karela (bitter gourd) → STRONG diabetes_friendly
- Methi (fenugreek) leaves or seeds → STRONG diabetes_friendly, STRONG pcos_friendly, iron_rich
- Oats, barley → diabetes_friendly, heart_friendly, cholesterol_friendly
- Bajra flour, jowar flour, ragi flour → diabetes_friendly, pcos_friendly, gluten_free
  (MILLET RULE: bajra/jowar/ragi are ALWAYS diabetes_friendly. NEVER assign avoid_diabetes to millets.)
- Moong dal, masoor dal, chana dal, arhar dal → diabetes_friendly, cholesterol_friendly
- Amla → STRONG diabetes_friendly, STRONG liver_friendly
- Cinnamon (dalchini) → pcos_friendly (moderate)
- Curry leaves → diabetes_friendly (moderate)
- Bhindi (okra) → cholesterol_friendly

### Sodium / hypertension (avoid_hypertension)
- Salt (table salt, rock salt, sea salt) → STRONG avoid_hypertension
- Baking soda, baking powder → avoid_hypertension (sodium source)
- Soy sauce → avoid_hypertension, avoid_gluten

### Heart-protective (heart_friendly)
- Garlic → STRONG heart_friendly, liver_friendly
- Oats, barley → heart_friendly
- Flaxseeds → heart_friendly, cholesterol_friendly, pcos_friendly
- Amla → heart_friendly

### Goitrogens / thyroid (avoid_hypothyroid)
- Bajra flour → avoid_hypothyroid (moderate, 0.6) — goitrogen when eaten in large daily quantities
- Jowar flour → avoid_hypothyroid (low, 0.4)
- Raw cabbage, raw cauliflower → avoid_hypothyroid (moderate)
- Tofu, soy milk → avoid_hypothyroid (moderate)
- NOTE: avoid_hypothyroid on millets does NOT mean avoid_diabetes or avoid_pcos

### Thyroid support (thyroid_support)
- Coconut oil, coconut milk → thyroid_support
- Methi (fenugreek) → thyroid_support
- Drumstick / moringa → thyroid_support

### Iodine / hyperthyroid (avoid_hyperthyroid)
- Prawn, crab, lobster, sea fish → avoid_hyperthyroid (high iodine)
- Kelp, seaweed → avoid_hyperthyroid

### PCOS (avoid_pcos / pcos_friendly)
- Avoid: same as diabetes avoids (sugar, maida, high-GI)
- Cream, malai, full-fat dairy in excess → avoid_pcos (moderate)
- Pcos_friendly: methi, oats, bajra/jowar/ragi, flaxseeds, cinnamon, karela

### Saturated/trans fat (avoid_highchol, avoid_heart)
- Vanaspati (hydrogenated fat) → STRONG avoid_highchol, STRONG avoid_heart
- Butter → avoid_highchol (moderate), avoid_heart (moderate)
- Ghee → avoid_highchol (moderate — saturated fat; confidence ≤ 0.65)
- Coconut oil → avoid_highchol (moderate — high saturated fat)
- Cream, malai, fresh cream → avoid_highchol (moderate)

### Kidney risk (avoid_kidney)
- Spinach (palak) → avoid_kidney (oxalate + potassium)
- Rajma (kidney beans) → STRONG avoid_kidney, iron_rich
- Chana (chickpeas) / chole → avoid_kidney (moderate — high phosphorus)
- Banana → avoid_kidney (moderate — high potassium)
- Tomato → avoid_kidney (low confidence ≤ 0.5 — oxalate, only when eaten in large amounts)
- Sattu (chickpea flour) → avoid_kidney (moderate)
- SAFE (do NOT tag avoid_kidney): lauki, cabbage, white rice, cucumber, moong dal

### Gluten (avoid_gluten / gluten_free)
- Wheat flour, atta, maida, suji/rava/semolina → STRONG avoid_gluten
- Oats → avoid_gluten (cross-contamination risk; NEVER tag oats as gluten_free)
- Barley → avoid_gluten
- Soy sauce → avoid_gluten
- Gluten-free: ragi flour, bajra flour, jowar flour, kuttu flour, besan (gram flour),
  rice flour, sabudana, poha, moong dal, all plain dals, all millets

### IBS / gut (avoid_ibs / gut_friendly)
- Onion, garlic → STRONG avoid_ibs (high FODMAP — fructans)
- Rajma, chole/chana → avoid_ibs (high FODMAP — GOS)
- Cauliflower (gobi) → avoid_ibs (polyols)
- Wheat (fructans) → avoid_ibs
- Sattu → avoid_ibs
- Gut_friendly: moong dal (lowest FODMAP dal), ajwain (carom seeds), cumin (jeera),
  ginger, curd/dahi (probiotic), chaas/buttermilk, lauki (bottle gourd)

### Fatty liver (avoid_fattyliver / liver_friendly)
- Sugar, jaggery, honey → avoid_fattyliver (fructose pathway)
- Vanaspati, cream → avoid_fattyliver
- Amla → STRONG liver_friendly
- Turmeric → liver_friendly
- Garlic → liver_friendly
- Lauki → liver_friendly
- Beets → liver_friendly
- Lemon → liver_friendly

### Gout (avoid_gout)
- Organ meats (liver, kidney meat, brain) → STRONG avoid_gout
- Red meat (mutton, lamb, beef) → avoid_gout (moderate)
- Sardines, mackerel, anchovies, herring → STRONG avoid_gout
- Jaggery, honey, sugar → avoid_gout (low-moderate — fructose pathway)
- Do NOT tag plain dal/legumes for gout (plant purines don't raise uric acid significantly)

### Calcium (calcium_rich)
- Sesame seeds (til) → STRONG calcium_rich (~975mg/100g)
- Ragi flour → STRONG calcium_rich (~344mg/100g)
- Paneer → STRONG calcium_rich (~480mg/100g)
- Curd/dahi → calcium_rich
- Milk → calcium_rich
- Drumstick leaves (moringa) → STRONG calcium_rich
- Rajgira (amaranth) → calcium_rich
- Almonds → calcium_rich (moderate)
- Bajra flour → calcium_rich (moderate)

### Iron (iron_rich)
- Methi leaves (dried) → STRONG iron_rich (~16mg/100g)
- Bajra flour → STRONG iron_rich (~11mg/100g)
- Jaggery → STRONG iron_rich (~11mg/100g)
- Sesame seeds → STRONG iron_rich (~14mg/100g)
- Masoor dal, moong dal, chana dal, arhar dal → iron_rich (moderate)
- Rajma → iron_rich
- Spinach (palak) → iron_rich (moderate, bioavailability reduced by oxalates)
- Dried dates (khajur), raisins → iron_rich (moderate)
- Pumpkin seeds → iron_rich (moderate)
""".strip()


USER_PROMPT_TMPL = """
Ingredient name: {name}

Evaluate this ingredient's INHERENT nutritional and biochemical properties only.
No cooking method. No dish context. Only what this ingredient IS.

CRITICAL RULES:
1. If your reasoning says this ingredient is safe or beneficial for a condition, do NOT assign the avoid tag for that condition. Tags must match reasoning.
2. Millets (bajra, jowar, ragi) are ALWAYS diabetes_friendly and pcos_friendly — NEVER assign avoid_diabetes or avoid_pcos to millets.
3. Oats always get avoid_gluten — NEVER tag oats as gluten_free.

Return ONLY this JSON (no prose, no markdown):
{{
  "tags": [
    {{"tag": "<tag>", "confidence": <0.0-1.0>, "reason": "<one sentence>"}}
  ]
}}

- Only tags from the valid 22-tag list.
- Omit tags where confidence < 0.25.
- If no tags apply: {{"tags": []}}.
""".strip()


# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_json(text: str) -> dict | None:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def validate_tags(raw: list[dict]) -> list[dict]:
    out = []
    for entry in raw:
        tag = entry.get("tag", "").strip()
        conf = float(entry.get("confidence", 0.0))
        reason = entry.get("reason", "").strip()
        if tag not in VALID_TAGS:
            continue
        conf = max(0.0, min(1.0, conf))
        if conf < DISCARD_THRESHOLD:
            continue
        out.append({"tag": tag, "confidence": round(conf, 2), "reason": reason})
    return out


def split_tags(tags: list[dict]) -> tuple[list[str], list[str], list[dict]]:
    """Return (avoid_list, prefer_list, review_list)."""
    accepted_avoid, accepted_prefer, review = [], [], []
    for t in tags:
        if t["confidence"] >= AUTO_ACCEPT_THRESHOLD:
            if t["tag"] in AVOID_TAGS:
                accepted_avoid.append(t["tag"])
            else:
                accepted_prefer.append(t["tag"])
        else:
            review.append(t)
    return accepted_avoid, accepted_prefer, review


def init_review_log() -> None:
    if not REVIEW_PATH.exists():
        REVIEW_PATH.write_text(
            "# Ingredient Tag Review Log\n\n"
            "Tags below confidence 0.85 — require manual review before writing to DB.\n\n"
            "| Ingredient | Tag | Confidence | Reason |\n"
            "|------------|-----|------------|--------|\n",
            encoding="utf-8",
        )


def append_review(name: str, review_tags: list[dict]) -> None:
    with REVIEW_PATH.open("a", encoding="utf-8") as f:
        for t in review_tags:
            reason = t["reason"].replace("|", "/")
            f.write(f"| {name} | `{t['tag']}` | {t['confidence']:.2f} | {reason} |\n")


async def call_llm(client: httpx.AsyncClient, name: str) -> str:
    payload = {
        "model": LLAMA_MODEL,
        "messages": [
            {"role": "system", "content": INGREDIENT_SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TMPL.format(name=name)},
        ],
        "temperature": 0.1,
        "max_tokens": 512,
    }
    resp = await client.post(LLAMA_URL, json=payload, timeout=TIMEOUT_S)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ── Main ──────────────────────────────────────────────────────────────────────

async def main(dry_run: bool) -> None:
    mode = "DRY RUN" if dry_run else "LIVE"
    print(f"Layer 1 — Ingredient tagging [{mode}]")
    print(f"Threshold: accept >= {AUTO_ACCEPT_THRESHOLD}, review >= {DISCARD_THRESHOLD}, discard < {DISCARD_THRESHOLD}\n")

    conn = await asyncpg.connect(DSN)

    # Fetch unprocessed ingredients (skip: already tagged OR NULL-nutrition artifacts)
    rows = await conn.fetch("""
        SELECT id, name
        FROM ingredients
        WHERE avoid_tags = '[]'::jsonb
          AND calories_per_100g IS NOT NULL
        ORDER BY id
    """)
    total = len(rows)
    print(f"Ingredients to process: {total}")

    if not dry_run:
        init_review_log()

    stats = {"written": 0, "review": 0, "no_tags": 0, "errors": 0}
    batches = [rows[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]

    async with httpx.AsyncClient() as client:
        for b_idx, batch in enumerate(batches):
            print(f"\n--- Batch {b_idx + 1}/{len(batches)} ---")
            for item in batch:
                ing_id = item["id"]
                name = item["name"]
                t0 = time.time()

                try:
                    raw = await call_llm(client, name)
                    elapsed = time.time() - t0
                    parsed = extract_json(raw)

                    if parsed is None:
                        print(f"  [{ing_id:4d}] '{name[:40]}' — PARSE ERROR ({elapsed:.1f}s)")
                        stats["errors"] += 1
                        continue

                    tags = validate_tags(parsed.get("tags", []))
                    avoid_list, prefer_list, review_tags = split_tags(tags)

                    tag_summary = (
                        f"avoid={avoid_list} prefer={prefer_list} review={[t['tag'] for t in review_tags]}"
                        if tags else "no tags"
                    )
                    print(f"  [{ing_id:4d}] '{name[:40]}' — {tag_summary} ({elapsed:.1f}s)")

                    if not tags:
                        stats["no_tags"] += 1
                        continue

                    if not dry_run:
                        if avoid_list or prefer_list:
                            await conn.execute(
                                """
                                UPDATE ingredients
                                SET avoid_tags = $1::jsonb, prefer_tags = $2::jsonb
                                WHERE id = $3
                                """,
                                json.dumps(avoid_list),
                                json.dumps(prefer_list),
                                ing_id,
                            )
                            stats["written"] += 1

                        if review_tags:
                            append_review(name, review_tags)
                            stats["review"] += len(review_tags)
                    else:
                        if avoid_list or prefer_list:
                            stats["written"] += 1
                        if review_tags:
                            stats["review"] += len(review_tags)

                except Exception as exc:
                    elapsed = time.time() - t0
                    print(f"  [{ing_id:4d}] '{name[:40]}' — ERROR: {exc} ({elapsed:.1f}s)")
                    stats["errors"] += 1

    await conn.close()

    print(f"\n{'='*60}")
    print(f"Layer 1 ingredient tagging [{mode}] complete")
    print(f"  Would write / written:   {stats['written']}")
    print(f"  Review queue additions:  {stats['review']}")
    print(f"  No tags assigned:        {stats['no_tags']}")
    print(f"  Errors:                  {stats['errors']}")
    print(f"  Review log:              {REVIEW_PATH}")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(main(dry_run))
