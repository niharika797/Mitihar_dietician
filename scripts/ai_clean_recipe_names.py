"""
ai_clean_recipe_names.py
------------------------
Three-level fallback AI recipe name cleaner:

Level 1 — Gemini 2.5 Flash-Lite (fast, free, bulk)
Level 2 — Gemini 2.5 Flash-Lite Key 2 (auto-switches on 429)
Level 3 — Ollama qwen3.5:4b locally (unlimited, no API key, runs on GPU)

PASS 1 — Bulk clean all dirty rows in batches of 20
PASS 2 — Edge cases one by one with thinking

Usage:
    venv\Scripts\python scripts\ai_clean_recipe_names.py

Env vars:
    GEMINI_API_KEY_1   — First Google AI Studio key
    GEMINI_API_KEY_2   — Second Google AI Studio key
    GEMINI_API_KEY_3   — Third Google AI Studio key
    GEMINI_API_KEY_4   — Fourth Google AI Studio key
    DATABASE_URL       — PostgreSQL DSN (optional)

Ollama must be running:
    ollama serve
"""

import os
import re
import sys
import time
import json
import logging
import urllib.request
import urllib.error
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.models.db_models import FoodItem

# ── Config ────────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://admin:mityahar_dev@localhost:5432/mityahar_db"
)

API_KEYS = [
    os.getenv("GEMINI_API_KEY_1", "YOUR_FIRST_KEY_HERE"),
    os.getenv("GEMINI_API_KEY_2", "YOUR_SECOND_KEY_HERE"),
    os.getenv("GEMINI_API_KEY_3", "YOUR_THIRD_KEY_HERE"),
    os.getenv("GEMINI_API_KEY_4", "YOUR_FOURTH_KEY_HERE"),
]

# Pass 1 — bulk fast model
PASS1_MODEL      = "gemini-2.5-flash-lite"
PASS1_BATCH_SIZE = 20
PASS1_SLEEP      = 8

# Pass 2 — thinking model for edge cases
PASS2_MODEL      = "gemini-2.5-flash"
PASS2_SLEEP      = 15

# Ollama fallback config
OLLAMA_URL       = "http://localhost:11434/api/generate"
OLLAMA_MODEL     = "qwen3.5:4b"
OLLAMA_SLEEP     = 3

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


# ── Key manager with Ollama fallback ─────────────────────────────────────────
class KeyManager:
    def __init__(self, keys: list[str]):
        self.keys      = [k for k in keys if k and "YOUR_" not in k]
        self.current   = 0
        self.use_ollama = False
        self.exhausted  = False

        log.info(f"  Loaded {len(self.keys)} Gemini API key(s) + Ollama fallback")

    def active_key(self) -> str | None:
        if self.use_ollama or self.exhausted:
            return None
        if self.current < len(self.keys):
            return self.keys[self.current]
        return None

    def switch_key(self) -> bool:
        next_idx = self.current + 1
        if next_idx < len(self.keys):
            self.current = next_idx
            log.info(f"  🔑 Switched to Gemini Key {self.current + 1}/{len(self.keys)}")
            return True
        else:
            log.warning("  ⚠️  All Gemini keys exhausted — switching to Ollama (local GPU)")
            self.use_ollama = True
            return True   # still True — Ollama is available

    def is_ollama(self) -> bool:
        return self.use_ollama

    def key_label(self) -> str:
        if self.use_ollama:
            return "Ollama (local)"
        return f"Gemini Key {self.current + 1}/{len(self.keys)}"


# ── Edge case / clean detectors ───────────────────────────────────────────────
def looks_weird(name: str) -> bool:
    name_lower = name.lower()
    garbage_words = ["recipe", "style", " - ", "hindi", "inspired",
                     "homestyle", "restaurant", "printers"]
    if any(w in name_lower for w in garbage_words):
        return True
    if "(" in name or ")" in name:
        return True
    if len(name) > 50:
        return True
    if re.search(r'\d', name):
        return True
    return False


def already_clean(name: str) -> bool:
    return not looks_weird(name) and len(name) <= 40


# ── Ollama caller ─────────────────────────────────────────────────────────────
def call_ollama(prompt: str) -> str | None:
    """Call local Ollama API. No rate limits, runs on GPU."""
    payload = json.dumps({
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 20
        },
        "think": False
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        return data.get("response", "").strip()

    except Exception as e:
        log.warning(f"  Ollama call failed: {e}")
        log.warning("  Make sure Ollama is running: ollama serve")
        return None


# ── Gemini caller ─────────────────────────────────────────────────────────────
def call_gemini(prompt: str, model: str, km: KeyManager,
                thinking: bool = False) -> str | None:
    key = km.active_key()
    if key is None:
        return None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )

    generation_config = {"temperature": 0.1, "maxOutputTokens": 2048}
    if thinking:
        generation_config["thinkingConfig"] = {"thinkingBudget": 512}

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": generation_config,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read())
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    except urllib.error.HTTPError as e:
        if e.code == 429:
            log.warning(f"  ⚠️  Rate limit on {km.key_label()} — switching...")
            km.switch_key()
            return None
        if e.code == 400:
            log.warning(f"  ⚠️  400 error on {km.key_label()} — switching to next key or Ollama...")
            km.switch_key()
            return None
        log.warning(f"  Gemini HTTP error: {e.code}")
        km.switch_key()
        return None
    except Exception as e:
        log.warning(f"  Gemini error: {e}")
        return None


# ── Unified caller — tries Gemini first, falls back to Ollama ─────────────────
def call_ai(prompt: str, km: KeyManager, model: str,
            thinking: bool = False, batch_mode: bool = False) -> str | None:
    """
    Unified AI caller.
    - If Gemini keys available: use Gemini
    - If all Gemini keys exhausted: use Ollama
    batch_mode=True means response is expected as JSON array (Pass 1)
    batch_mode=False means response is a single name (Pass 2)
    """
    if km.is_ollama():
        return call_ollama(prompt)
    else:
        response = call_gemini(prompt, model, km, thinking)
        # If key just switched to Ollama mid-call, retry with Ollama
        if response is None and km.is_ollama():
            log.info(f"  Retrying with Ollama...")
            return call_ollama(prompt)
        return response


# ── Pass 1: Bulk clean ────────────────────────────────────────────────────────
def pass1_clean(rows: list, session, km: KeyManager) -> tuple[int, int, int]:
    needs_clean = [r for r in rows if not already_clean(r.recipe_name)]
    pre_clean   = len(rows) - len(needs_clean)

    total    = len(needs_clean)
    updated  = 0
    skipped  = pre_clean
    errors   = 0
    examples = []

    log.info(f"\n{'='*65}")
    log.info(f"  PASS 1 — Bulk clean")
    log.info(f"  {len(rows)} total | {pre_clean} already clean | {total} to process")
    log.info(f"  Starting with: {km.key_label()}")
    log.info(f"{'='*65}")

    if total == 0:
        log.info("  Nothing to process in Pass 1!")
        return 0, skipped, 0

    for batch_start in range(0, total, PASS1_BATCH_SIZE):
        batch    = needs_clean[batch_start : batch_start + PASS1_BATCH_SIZE]
        names    = [item.recipe_name for item in batch]
        numbered = "\n".join(f"{i+1}. {name}" for i, name in enumerate(names))

        is_ollama_batch = km.is_ollama()

        if is_ollama_batch:
            # Ollama: send one at a time (more reliable than batch JSON)
            log.info(f"  Processing batch {batch_start//PASS1_BATCH_SIZE+1} via Ollama one-by-one...")
            cleaned_names = []
            for name in names:
                single_prompt = f"""/no_think
Clean this Indian recipe name for a Bihar diet app patient.
Remove: "Recipe", "Style", region prefixes, subtitles after " - ", parentheses.
Keep authentic Indian dish names as-is.
Return ONLY the cleaned name, maximum 5 words, nothing else.

Name: {name}"""
                result = call_ollama(single_prompt)
                cleaned_names.append(result.strip() if result else name)
                time.sleep(OLLAMA_SLEEP)
        else:
            prompt = f"""You are cleaning Indian recipe names for a diet app used by everyday patients in Bihar, India.
These patients are regular people — farmers, housewives, office workers.
The dish name should feel like something they would naturally say at home.

Rules:
- Remove words: "Recipe", "Style", "Inspired", "Homestyle", "Restaurant Style", "Hindi"
- Remove region prefixes: "Karnataka Style", "Kerala Style", "Tamil Nadu Style", "Bengali Style" etc.
- Remove everything after " - " (subtitles)
- Remove parenthetical descriptions like "(Recipe In Hindi)" or "(Stir Fried Yam)"
- Fix obvious OCR/typo errors (e.g. "Darts Masala" → "Dry Masala", "Printers" → remove it)
- Translate Tamil/Bengali dish names to simple Hindi/English if Bihar patient won't recognize them
- Keep well-known Hindi/Indian names as-is: Dal Makhani, Palak Paneer, Aloo Gobi, Rajma etc.
- Maximum 5 words in output
- If name is already clean and short, return it unchanged

Return ONLY a JSON array, same order as input, no markdown, no explanation:
["cleaned name 1", "cleaned name 2", ...]

Input:
{numbered}"""

            response = call_ai(prompt, km, PASS1_MODEL, batch_mode=True)

            if response is None:
                log.warning(f"  Batch {batch_start//PASS1_BATCH_SIZE+1} failed — skipping")
                errors += len(batch)
                time.sleep(PASS1_SLEEP)
                continue

            try:
                text = response.replace("```json", "").replace("```", "").strip()
                cleaned_names = json.loads(text)
                if not isinstance(cleaned_names, list) or len(cleaned_names) != len(names):
                    raise ValueError("Length mismatch")
            except Exception as e:
                log.warning(f"  Parse error batch {batch_start//PASS1_BATCH_SIZE+1}: {e}")
                errors += len(batch)
                time.sleep(PASS1_SLEEP)
                continue

        for item, original, cleaned in zip(batch, names, cleaned_names):
            cleaned = str(cleaned).strip()
            if not cleaned or len(cleaned) < 3:
                skipped += 1
                continue
            if len(examples) < 20 and original.lower() != cleaned.lower():
                examples.append((original, cleaned))
            item.recipe_name = cleaned
            updated += 1

        try:
            session.commit()
            log.info(f"  Batch {batch_start//PASS1_BATCH_SIZE+1} ✅ [{km.key_label()}] | updated={updated}")
        except Exception as e:
            session.rollback()
            log.error(f"  Commit failed: {e}")
            errors += len(batch)

        if not is_ollama_batch:
            time.sleep(PASS1_SLEEP)

    if examples:
        print(f"\n  PASS 1 SAMPLE CHANGES ({len(examples)} shown):")
        print("  " + "-" * 61)
        for orig, clean in examples:
            print(f"  BEFORE : {orig[:55]}")
            print(f"  AFTER  : {clean}")
            print()

    return updated, skipped, errors


# ── Pass 2: Edge cases ────────────────────────────────────────────────────────
def pass2_clean(rows: list, session, km: KeyManager) -> tuple[int, int]:
    edge_cases = [item for item in rows if looks_weird(item.recipe_name)]

    log.info(f"\n{'='*65}")
    log.info(f"  PASS 2 — Edge cases deep clean")
    log.info(f"  {len(edge_cases)} rows flagged")
    log.info(f"  Using: {km.key_label()}")
    log.info(f"{'='*65}")

    if not edge_cases:
        log.info("  No edge cases — everything is clean!")
        return 0, 0

    updated  = 0
    skipped  = 0
    examples = []

    for i, item in enumerate(edge_cases):
        original = item.recipe_name

        prompt = f"""/no_think
You are a food expert for patients in Bihar, India.
Clean this dish name for a regular Bihar household patient.

Name: "{original}"

Think:
1. What is the actual dish?
2. Would a Bihar patient recognize it?
3. Any OCR errors or typos to fix?
4. Best short natural name in Indian English or Hindi?

Return ONLY the cleaned name, maximum 5 words, nothing else."""

        if km.is_ollama():
            response = call_ollama(prompt)
            time.sleep(OLLAMA_SLEEP)
        else:
            response = call_ai(prompt, km, PASS2_MODEL, thinking=True)
            time.sleep(PASS2_SLEEP)

        if response is None:
            skipped += 1
            continue

        cleaned = response.strip().strip('"').strip("'")
        if not cleaned or len(cleaned) < 3:
            skipped += 1
            continue

        if len(examples) < 15:
            examples.append((original, cleaned))

        item.recipe_name = cleaned
        updated += 1

        try:
            session.commit()
            log.info(f"  [{i+1}/{len(edge_cases)}] [{km.key_label()}] '{original[:30]}' → '{cleaned}'")
        except Exception as e:
            session.rollback()
            skipped += 1

    if examples:
        print(f"\n  PASS 2 SAMPLE CHANGES ({len(examples)} shown):")
        print("  " + "-" * 61)
        for orig, clean in examples:
            print(f"  BEFORE : {orig[:55]}")
            print(f"  AFTER  : {clean}")
            print()

    return updated, skipped


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    km = KeyManager(API_KEYS)

    engine  = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    log.info("Fetching all 6k_dataset rows...")
    rows = session.query(FoodItem).filter(FoodItem.source == "6k_dataset").all()
    log.info(f"Found {len(rows)} rows")

    # Pass 1
    p1_updated, p1_skipped, p1_errors = pass1_clean(rows, session, km)

    # Re-fetch
    rows = session.query(FoodItem).filter(FoodItem.source == "6k_dataset").all()

    # Pass 2
    p2_updated, p2_skipped = pass2_clean(rows, session, km)

    session.close()

    print("\n" + "=" * 65)
    print("  FINAL SUMMARY")
    print(f"  Pass 1 — Updated: {p1_updated} | Skipped: {p1_skipped} | Errors: {p1_errors}")
    print(f"  Pass 2 — Updated: {p2_updated} | Skipped: {p2_skipped}")
    print(f"  Total cleaned   : {p1_updated + p2_updated}")
    if km.is_ollama():
        print("  ✅ Ollama fallback was used successfully")
    print("=" * 65)
    print("  Next: verify in pgAdmin, then mark trusted rows is_verified=True")
    print("=" * 65)


if __name__ == "__main__":
    main()
