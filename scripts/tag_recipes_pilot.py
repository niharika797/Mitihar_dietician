"""
Session 18A — Pilot Recipe Tagging Script
Runs 50 approved pilot recipes through Gemma (llama-server port 11434).
Outputs to docs/PILOT_TAGGING_RESULTS.md. Does NOT write to the database.
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
LLAMA_MODEL = "gemma"  # llama-server ignores the model field; any string works
KB_PATH = Path(__file__).parent.parent / "docs" / "MEDICAL_TAGGING_KB_COMPACT.md"
OUT_PATH = Path(__file__).parent.parent / "docs" / "PILOT_TAGGING_RESULTS.md"

PILOT_IDS = [
    # Bucket A — Clearly AVOID
    192, 198, 212, 214, 233, 379, 931, 1357, 1211, 300, 840, 1134,
    # Bucket B — Clearly PREFER / BENEFICIAL
    316, 1561, 258, 261, 266, 304, 356, 230, 276, 305, 264, 398, 282, 228,
    # Bucket C — AMBIGUOUS / EDGE CASES
    217, 219, 274, 281, 347, 189, 362, 306, 355, 359, 608, 349,
    # Bucket D — CONDITION-SPECIFIC
    271, 241, 427, 869, 623, 548, 1313, 1119, 1067, 480, 309, 1166,
]

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

TIMEOUT_S = 120  # seconds per LLM call

# ── Prompt templates ──────────────────────────────────────────────────────────
USER_PROMPT_TMPL = """
Recipe name: {recipe_name}
Ingredients: {ingredients}

Apply the medical tagging rules from the knowledge base to this recipe.
IMPORTANT: If your reasoning for a condition concludes that an ingredient or dish is safe or beneficial for that condition, do NOT assign the avoid tag for that condition. Your tag assignment must be consistent with your reasoning. A contradiction between your reasoning and your tag is always wrong.
Return ONLY a JSON object in this exact format — no prose, no markdown, just the JSON:

{{
  "tags": [
    {{"tag": "<tag_string>", "confidence": <0.0-1.0>, "reason": "<one brief sentence>"}}
  ]
}}

Rules:
- Only use tags from the valid tag list in the knowledge base.
- Omit a tag entirely if confidence would be below 0.25.
- If no tags apply, return {{"tags": []}}.
- Do not invent tags outside the valid list.
""".strip()

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_kb() -> str:
    return KB_PATH.read_text(encoding="utf-8")


def format_ingredients(ingredients_jsonb) -> str:
    """Convert JSONB ingredient list to a plain comma-separated string."""
    try:
        if isinstance(ingredients_jsonb, str):
            ings = json.loads(ingredients_jsonb)
        else:
            ings = ingredients_jsonb or []
        names = [i.get("name", "").strip() for i in ings if i.get("name")]
        return ", ".join(names) if names else "unknown"
    except Exception:
        return "unknown"


def extract_json(text: str) -> dict | None:
    """Extract JSON from LLM response, tolerating markdown code fences."""
    text = text.strip()
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    # Find first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def validate_tags(raw_tags: list[dict]) -> list[dict]:
    """Filter out invalid tags and clamp confidence to [0, 1]."""
    result = []
    for entry in raw_tags:
        tag = entry.get("tag", "").strip()
        conf = entry.get("confidence", 0.0)
        reason = entry.get("reason", "").strip()
        if tag not in VALID_TAGS:
            continue
        conf = max(0.0, min(1.0, float(conf)))
        if conf < 0.25:
            continue
        result.append({"tag": tag, "confidence": round(conf, 2), "reason": reason})
    return result


async def call_llm(client: httpx.AsyncClient, system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": LLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }
    resp = await client.post(LLAMA_URL, json=payload, timeout=TIMEOUT_S)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    print("Loading knowledge base...", flush=True)
    system_prompt = load_kb()
    print(f"KB loaded: {len(system_prompt)} chars", flush=True)

    print("Connecting to database...", flush=True)
    conn = await asyncpg.connect(DSN)
    rows = await conn.fetch(
        "SELECT id, recipe_name, slot_type, is_verified, ingredients "
        "FROM food_items WHERE id = ANY($1) ORDER BY id",
        PILOT_IDS,
    )
    await conn.close()

    id_to_row = {r["id"]: r for r in rows}
    missing = [i for i in PILOT_IDS if i not in id_to_row]
    if missing:
        print(f"WARNING: IDs not found in DB: {missing}", flush=True)

    results = []
    print(f"\nTagging {len(PILOT_IDS)} recipes...\n", flush=True)

    async with httpx.AsyncClient() as client:
        for idx, recipe_id in enumerate(PILOT_IDS, 1):
            row = id_to_row.get(recipe_id)
            if not row:
                print(f"  [{idx:02d}/50] ID={recipe_id} NOT FOUND — skipping")
                continue

            name = row["recipe_name"]
            slot = row["slot_type"]
            verified = row["is_verified"]
            ingredient_str = format_ingredients(row["ingredients"])

            user_prompt = USER_PROMPT_TMPL.format(
                recipe_name=name,
                ingredients=ingredient_str,
            )

            t0 = time.time()
            try:
                raw = await call_llm(client, system_prompt, user_prompt)
                elapsed = time.time() - t0
                parsed = extract_json(raw)
                if parsed is None:
                    print(f"  [{idx:02d}/50] ID={recipe_id} '{name}' — JSON parse FAILED ({elapsed:.1f}s)")
                    results.append({
                        "id": recipe_id, "name": name, "slot": slot,
                        "verified": verified, "ingredient_str": ingredient_str,
                        "tags": [], "error": "json_parse_failed", "raw": raw[:300],
                    })
                    continue

                tags = validate_tags(parsed.get("tags", []))
                print(f"  [{idx:02d}/50] ID={recipe_id} '{name[:40]}' — {len(tags)} tags ({elapsed:.1f}s)")
                results.append({
                    "id": recipe_id, "name": name, "slot": slot,
                    "verified": verified, "ingredient_str": ingredient_str,
                    "tags": tags, "error": None,
                })
            except Exception as exc:
                elapsed = time.time() - t0
                print(f"  [{idx:02d}/50] ID={recipe_id} '{name}' — ERROR: {exc} ({elapsed:.1f}s)")
                results.append({
                    "id": recipe_id, "name": name, "slot": slot,
                    "verified": verified, "ingredient_str": ingredient_str,
                    "tags": [], "error": str(exc),
                })

    print("\nWriting results...", flush=True)
    write_results(results)
    print(f"Done. Results at: {OUT_PATH}", flush=True)


def write_results(results: list[dict]) -> None:
    lines = [
        "# Pilot Tagging Results — Session 18A",
        f"**Recipes tagged:** {len(results)}",
        "",
        "---",
        "",
    ]

    for r in results:
        v_badge = "✓ Verified" if r["verified"] else "○ Unverified"
        lines.append(f"## ID={r['id']} — {r['name']}")
        lines.append(f"**Slot:** {r['slot']} | **{v_badge}**")
        lines.append(f"**Ingredients:** {r['ingredient_str']}")
        lines.append("")

        if r.get("error"):
            lines.append(f"> ⚠ Error: `{r['error']}`")
            if "raw" in r:
                lines.append(f"> Raw snippet: `{r['raw']}`")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        if not r["tags"]:
            lines.append("**Tags assigned:** none")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        lines.append("| Tag | Confidence | Reason |")
        lines.append("|-----|-----------|--------|")
        for t in r["tags"]:
            conf_bar = "▓" * int(t["confidence"] * 10) + "░" * (10 - int(t["confidence"] * 10))
            lines.append(f"| `{t['tag']}` | {t['confidence']:.2f} {conf_bar} | {t['reason']} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # ── Summary analysis ──────────────────────────────────────────────────────
    tagged = [r for r in results if r["tags"]]
    all_confs = [t["confidence"] for r in results for t in r["tags"]]
    high = [c for c in all_confs if c >= 0.8]
    mid  = [c for c in all_confs if 0.5 <= c < 0.8]
    low  = [c for c in all_confs if c < 0.5]

    errors = [r for r in results if r.get("error")]
    zero_tags = [r for r in results if not r["tags"] and not r.get("error")]

    # Tag frequency
    tag_freq: dict[str, int] = {}
    for r in results:
        for t in r["tags"]:
            tag_freq[t["tag"]] = tag_freq.get(t["tag"], 0) + 1
    tag_freq_sorted = sorted(tag_freq.items(), key=lambda x: -x[1])

    lines += [
        "---",
        "",
        "# Summary Analysis",
        "",
        f"- **Recipes with ≥1 tag:** {len(tagged)} / {len(results)}",
        f"- **Recipes with 0 tags:** {len(zero_tags)}",
        f"- **Errors (LLM/parse failures):** {len(errors)}",
        f"- **Total tag assignments:** {len(all_confs)}",
        "",
        "## Confidence Distribution",
        "",
        f"| Range | Count | % |",
        f"|-------|-------|---|",
        f"| ≥ 0.8 (auto-accept candidate) | {len(high)} | {100*len(high)//max(len(all_confs),1)}% |",
        f"| 0.5–0.79 (review recommended) | {len(mid)} | {100*len(mid)//max(len(all_confs),1)}% |",
        f"| 0.25–0.49 (low, flag for Claude review) | {len(low)} | {100*len(low)//max(len(all_confs),1)}% |",
        "",
        "## Tag Frequency",
        "",
        "| Tag | # Recipes |",
        "|-----|-----------|",
    ]
    for tag, count in tag_freq_sorted:
        lines.append(f"| `{tag}` | {count} |")

    lines += [
        "",
        "## Recipes with 0 Tags",
        "",
    ]
    for r in zero_tags:
        lines.append(f"- ID={r['id']} **{r['name']}** ({r['slot']})")

    lines += [
        "",
        "## Errors",
        "",
    ]
    for r in errors:
        lines.append(f"- ID={r['id']} **{r['name']}**: `{r.get('error')}`")

    lines += [
        "",
        "## Recommended Confidence Threshold",
        "",
        "*(To be filled in after manual review of results above)*",
        "",
        "- **Auto-accept threshold:** TBD",
        "- **Claude API review threshold:** TBD",
        "- **Discard threshold:** < 0.25 (already filtered)",
        "",
    ]

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
