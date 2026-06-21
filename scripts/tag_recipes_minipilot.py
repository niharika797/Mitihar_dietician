"""
Session 18B — Mini-Pilot Verification Script
10 recipes targeting the 4 error types found in Session 18A pilot.
Outputs to docs/MINI_PILOT_VERIFICATION.md. Does NOT write to DB.
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
KB_PATH = Path(__file__).parent.parent / "docs" / "MEDICAL_TAGGING_KB_COMPACT.md"
OUT_PATH = Path(__file__).parent.parent / "docs" / "MINI_PILOT_VERIFICATION.md"

# 10 recipes targeting specific error types from Session 18A pilot
MINI_IDS = [
    355,   # Jowar roti         — FIX 1: must get diabetes_friendly, NOT avoid_diabetes
    359,   # Bajra roti         — FIX 1: must get diabetes_friendly, NOT avoid_diabetes
    840,   # Arbi Achaar        — FIX 2: must get ONLY avoid_hypertension (no gut_friendly/liver_friendly)
    1134,  # Stuffed Mango Pickle — FIX 2: must get ONLY avoid_hypertension (no diabetes_friendly)
    608,   # Oats Moong Dal     — FIX 3: must get avoid_gluten, NOT gluten_free
    427,   # Lauki Paneer       — FIX 4: must NOT get avoid_kidney
    316,   # Karela bhujia      — SANITY: must still get diabetes_friendly at high confidence
    254,   # Dal                — REGRESSION: simple green gram dal → diabetes_friendly
    257,   # Luchi              — REGRESSION: wheat flour + oil fried → avoid_diabetes, avoid_gluten, avoid_heart
    268,   # Bhindi masala      — REGRESSION: bhindi → cholesterol_friendly
]

# Expected outcomes per recipe (used for pass/fail annotation in output)
EXPECTATIONS = {
    355:  {"must_have": ["diabetes_friendly"], "must_not_have": ["avoid_diabetes", "avoid_pcos"]},
    359:  {"must_have": ["diabetes_friendly"], "must_not_have": ["avoid_diabetes", "avoid_pcos"]},
    840:  {"must_have": ["avoid_hypertension"], "must_not_have": ["gut_friendly", "liver_friendly", "diabetes_friendly", "heart_friendly"]},
    1134: {"must_have": ["avoid_hypertension"], "must_not_have": ["diabetes_friendly", "heart_friendly", "gut_friendly"]},
    608:  {"must_have": ["avoid_gluten"], "must_not_have": ["gluten_free"]},
    427:  {"must_have": [], "must_not_have": ["avoid_kidney"]},
    316:  {"must_have": ["diabetes_friendly"], "must_not_have": []},
    254:  {"must_have": ["diabetes_friendly"], "must_not_have": []},
    257:  {"must_have": ["avoid_diabetes", "avoid_gluten"], "must_not_have": []},
    268:  {"must_have": ["cholesterol_friendly"], "must_not_have": []},
}

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

TIMEOUT_S = 120

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


def load_kb() -> str:
    return KB_PATH.read_text(encoding="utf-8")


def format_ingredients(ingredients_jsonb) -> str:
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


def validate_tags(raw_tags: list[dict]) -> list[dict]:
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


def check_expectations(recipe_id: int, tags: list[dict]) -> tuple[bool, list[str]]:
    exp = EXPECTATIONS.get(recipe_id)
    if not exp:
        return True, []
    assigned = {t["tag"] for t in tags}
    failures = []
    for required in exp["must_have"]:
        if required not in assigned:
            failures.append(f"MISSING required tag `{required}`")
    for forbidden in exp["must_not_have"]:
        if forbidden in assigned:
            conf = next(t["confidence"] for t in tags if t["tag"] == forbidden)
            failures.append(f"WRONG tag `{forbidden}` (conf={conf}) — must not be assigned")
    return len(failures) == 0, failures


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
    return resp.json()["choices"][0]["message"]["content"]


async def main() -> None:
    print("Loading knowledge base...", flush=True)
    system_prompt = load_kb()
    print(f"KB loaded: {len(system_prompt)} chars", flush=True)

    conn = await asyncpg.connect(DSN)
    rows = await conn.fetch(
        "SELECT id, recipe_name, slot_type, is_verified, ingredients "
        "FROM food_items WHERE id = ANY($1) ORDER BY id",
        MINI_IDS,
    )
    await conn.close()

    id_to_row = {r["id"]: r for r in rows}
    missing = [i for i in MINI_IDS if i not in id_to_row]
    if missing:
        print(f"WARNING: IDs not found in DB: {missing}", flush=True)

    results = []
    print(f"\nTagging {len(MINI_IDS)} recipes...\n", flush=True)

    async with httpx.AsyncClient() as client:
        for idx, recipe_id in enumerate(MINI_IDS, 1):
            row = id_to_row.get(recipe_id)
            if not row:
                print(f"  [{idx:02d}/10] ID={recipe_id} NOT FOUND — skipping")
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
                    print(f"  [{idx:02d}/10] ID={recipe_id} '{name}' — JSON parse FAILED ({elapsed:.1f}s)")
                    results.append({
                        "id": recipe_id, "name": name, "slot": slot, "verified": verified,
                        "ingredient_str": ingredient_str, "tags": [], "error": "json_parse_failed",
                    })
                    continue

                tags = validate_tags(parsed.get("tags", []))
                passed, failures = check_expectations(recipe_id, tags)
                status = "PASS" if passed else f"FAIL ({len(failures)} issues)"
                print(f"  [{idx:02d}/10] ID={recipe_id} '{name[:35]}' — {len(tags)} tags — {status} ({elapsed:.1f}s)")
                results.append({
                    "id": recipe_id, "name": name, "slot": slot, "verified": verified,
                    "ingredient_str": ingredient_str, "tags": tags, "error": None,
                    "passed": passed, "failures": failures,
                })
            except Exception as exc:
                elapsed = time.time() - t0
                print(f"  [{idx:02d}/10] ID={recipe_id} '{name}' — ERROR: {exc} ({elapsed:.1f}s)")
                results.append({
                    "id": recipe_id, "name": name, "slot": slot, "verified": verified,
                    "ingredient_str": ingredient_str, "tags": [], "error": str(exc),
                    "passed": False, "failures": [str(exc)],
                })

    print("\nWriting results...", flush=True)
    write_results(results)
    print(f"Done. Results at: {OUT_PATH}", flush=True)

    # Print pass/fail summary
    total = len(results)
    passed_count = sum(1 for r in results if r.get("passed"))
    print(f"\nPASS: {passed_count}/{total}")
    for r in results:
        if not r.get("passed"):
            print(f"  FAIL ID={r['id']} {r['name']}: {r.get('failures', [])}")


def write_results(results: list[dict]) -> None:
    lines = [
        "# Mini-Pilot Verification — Session 18B",
        "**Purpose:** Verify the 4 compact KB fixes from Session 18A pilot quality review.",
        f"**Recipes tested:** {len(results)}",
        "",
        "## Pass/Fail Legend",
        "- ✅ PASS — All required tags present, no forbidden tags assigned",
        "- ❌ FAIL — Missing required tag or forbidden tag assigned",
        "",
        "---",
        "",
    ]

    for r in results:
        exp = EXPECTATIONS.get(r["id"], {})
        must_have = exp.get("must_have", [])
        must_not_have = exp.get("must_not_have", [])

        v_badge = "✓ Verified" if r["verified"] else "○ Unverified"
        pass_icon = "✅ PASS" if r.get("passed") else "❌ FAIL"

        lines.append(f"## ID={r['id']} — {r['name']}  {pass_icon}")
        lines.append(f"**Slot:** {r['slot']} | **{v_badge}**")
        lines.append(f"**Ingredients:** {r['ingredient_str']}")

        if must_have or must_not_have:
            lines.append(f"**Expected:** must have `{'`, `'.join(must_have) if must_have else '—'}` | must NOT have `{'`, `'.join(must_not_have) if must_not_have else '—'}`")

        lines.append("")

        if r.get("error"):
            lines.append(f"> ⚠ Error: `{r['error']}`")
            lines.append("")
            lines.append("---")
            lines.append("")
            continue

        if not r["tags"]:
            lines.append("**Tags assigned:** none")
        else:
            lines.append("| Tag | Confidence | Reason |")
            lines.append("|-----|-----------|--------|")
            for t in r["tags"]:
                conf_bar = "▓" * int(t["confidence"] * 10) + "░" * (10 - int(t["confidence"] * 10))
                lines.append(f"| `{t['tag']}` | {t['confidence']:.2f} {conf_bar} | {t['reason']} |")

        if r.get("failures"):
            lines.append("")
            lines.append("**Issues:**")
            for f in r["failures"]:
                lines.append(f"- ❌ {f}")

        lines.append("")
        lines.append("---")
        lines.append("")

    # Summary table
    total = len(results)
    passed = sum(1 for r in results if r.get("passed"))
    lines += [
        "## Summary",
        "",
        f"**{passed}/{total} PASS**",
        "",
        "| ID | Recipe | Fix Tested | Result |",
        "|----|--------|------------|--------|",
    ]
    fix_labels = {
        355:  "Fix 1 — millet diabetes_friendly",
        359:  "Fix 1 — millet diabetes_friendly",
        840:  "Fix 2 — achaar override",
        1134: "Fix 2 — achaar override",
        608:  "Fix 3 — oats avoid_gluten",
        427:  "Fix 4 — self-contradiction guard",
        316:  "Sanity check — karela",
        254:  "Regression — plain dal",
        257:  "Regression — fried flatbread",
        268:  "Regression — bhindi sabzi",
    }
    for r in results:
        icon = "✅" if r.get("passed") else "❌"
        fix = fix_labels.get(r["id"], "—")
        lines.append(f"| {r['id']} | {r['name']} | {fix} | {icon} |")

    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
