"""
ai_clean_recipe_names.py
------------------------
Three-level fallback AI recipe name cleaner:
  Level 1 — Gemini Key 1
  Level 2 — Gemini Key 2
  Level 3 — Ollama qwen3.5:4b (local GPU, unlimited)

If no Gemini keys set → goes straight to Ollama.

Usage:
    venv\Scripts\python scripts\ai_clean_recipe_names.py

Env vars (optional — skips to Ollama if not set):
    GEMINI_API_KEY_1
    GEMINI_API_KEY_2
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.models.db_models import FoodItem

# ── Config ────────────────────────────────────────────────────────────────────
DATABASE_URL     = os.getenv("DATABASE_URL", "postgresql+psycopg2://admin:mityahar_dev@localhost:5432/mityahar_db")
API_KEYS         = [k for k in [os.getenv("GEMINI_API_KEY_1"), os.getenv("GEMINI_API_KEY_2")] if k]
PASS1_MODEL      = "gemini-2.5-flash-lite"
PASS2_MODEL      = "gemini-2.5-flash"
PASS1_BATCH_SIZE = 20
PASS1_SLEEP      = 8
PASS2_SLEEP      = 15
OLLAMA_URL       = "http://localhost:11434/api/generate"
OLLAMA_MODEL     = "qwen3.5:4b"
OLLAMA_SLEEP     = 3

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


# ── Key manager ───────────────────────────────────────────────────────────────
class KeyManager:
    def __init__(self, keys):
        self.keys       = keys
        self.current    = 0
        self.use_ollama = len(keys) == 0  # go straight to Ollama if no keys

        if self.use_ollama:
            log.info("  No Gemini keys set — using Ollama directly")
        else:
            log.info(f"  Loaded {len(self.keys)} Gemini key(s) + Ollama fallback")

    def active_key(self):
        if self.use_ollama or self.current >= len(self.keys):
            return None
        return self.keys[self.current]

    def switch_key(self):
        self.current += 1
        if self.current < len(self.keys):
            log.info(f"  Switched to Gemini Key {self.current + 1}/{len(self.keys)}")
        else:
            log.warning("  All Gemini keys exhausted — switching to Ollama (local GPU)")
            self.use_ollama = True

    def is_ollama(self):
        return self.use_ollama or self.current >= len(self.keys)

    def label(self):
        if self.is_ollama():
            return "Ollama"
        return f"Gemini Key {self.current + 1}/{len(self.keys)}"


# ── Detectors ─────────────────────────────────────────────────────────────────
def looks_weird(name):
    n = name.lower()
    if any(w in n for w in ["recipe", "style", " - ", "hindi", "inspired", "homestyle", "restaurant"]):
        return True
    if "(" in name or ")" in name:
        return True
    if len(name) > 50:
        return True
    if re.search(r'\d', name):
        return True
    return False

def already_clean(name):
    return not looks_weird(name) and len(name) <= 40


# ── Ollama caller ─────────────────────────────────────────────────────────────
def call_ollama(prompt):
    payload = json.dumps({
        "model":  OLLAMA_MODEL,
        "prompt": "/no_think\n" + prompt,
        "stream": False,
        "think":  False,
        "options": {"temperature": 0.1, "num_predict": 30}
    }).encode("utf-8")
    try:
        req = urllib.request.Request(OLLAMA_URL, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read()).get("response", "").strip()
    except Exception as e:
        log.warning(f"  Ollama error: {e}")
        return None


# ── Gemini caller ─────────────────────────────────────────────────────────────
def call_gemini(prompt, model, km, thinking=False):
    key = km.active_key()
    if not key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    cfg = {"temperature": 0.1, "maxOutputTokens": 2048}
    if thinking:
        cfg["thinkingConfig"] = {"thinkingBudget": 512}
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": cfg}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=45) as r:
            return json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        log.warning(f"  Gemini HTTP {e.code} on {km.label()} — switching...")
        km.switch_key()
        return None
    except Exception as e:
        log.warning(f"  Gemini error: {e}")
        return None


# ── Unified caller ────────────────────────────────────────────────────────────
def call_ai(prompt, km, model, thinking=False):
    if km.is_ollama():
        return call_ollama(prompt)
    resp = call_gemini(prompt, model, km, thinking)
    if resp is None and km.is_ollama():
        log.info("  Retrying with Ollama...")
        return call_ollama(prompt)
    return resp


# ── Pass 1: Bulk clean ────────────────────────────────────────────────────────
def pass1_clean(rows, session, km):
    dirty    = [r for r in rows if not already_clean(r.recipe_name)]
    skipped  = len(rows) - len(dirty)
    updated  = errors = 0
    examples = []

    log.info(f"\n{'='*65}")
    log.info(f"  PASS 1 — Bulk clean | {len(dirty)} to process | {skipped} already clean")
    log.info(f"  Using: {km.label()}")
    log.info(f"{'='*65}")

    if not dirty:
        log.info("  Nothing to process!")
        return 0, skipped, 0

    for i in range(0, len(dirty), PASS1_BATCH_SIZE):
        batch = dirty[i : i + PASS1_BATCH_SIZE]
        names = [r.recipe_name for r in batch]

        if km.is_ollama():
            # Ollama: one at a time
            cleaned_names = []
            for name in names:
                p = f"""Clean this Indian recipe name. 
Rules: remove "Recipe", "Style", region prefixes like "Kerala Style", subtitles after " - ", text in parentheses. Fix OCR errors. Keep authentic Indian dish names. Max 5 words. Return ONLY the name.

Name: {name}"""
                result = call_ollama(p) or name
                cleaned_names.append(result.strip())
                time.sleep(OLLAMA_SLEEP)
                log.info(f"  [{km.label()}] '{name[:35]}' → '{cleaned_names[-1]}'")
        else:
            numbered = "\n".join(f"{i+1}. {n}" for i, n in enumerate(names))
            prompt = f"""Clean these Indian recipe names for a diet app.

Rules:
- Remove: "Recipe", "Style", "Inspired", "Homestyle", "Restaurant Style", "Hindi"
- Remove region prefixes: "Karnataka Style", "Kerala Style", "Tamil Nadu Style" etc.
- Remove everything after " - "
- Remove parenthetical text like "(Recipe In Hindi)"
- Fix OCR/typo errors e.g. "Darts Masala" → "Dry Masala"
- Keep authentic Indian names as-is: Dal Makhani, Palak Paneer, Aloo Gobi etc.
- Max 5 words
- If already clean, return unchanged

Return ONLY a JSON array, same order, no markdown:
["name1", "name2", ...]

Input:
{numbered}"""

            resp = call_ai(prompt, km, PASS1_MODEL)
            if resp is None:
                log.warning(f"  Batch {i//PASS1_BATCH_SIZE+1} failed — skipping")
                errors += len(batch)
                time.sleep(PASS1_SLEEP)
                continue
            try:
                text = resp.replace("```json","").replace("```","").strip()
                cleaned_names = json.loads(text)
                if not isinstance(cleaned_names, list) or len(cleaned_names) != len(names):
                    raise ValueError("mismatch")
            except Exception as e:
                log.warning(f"  Parse error: {e}")
                errors += len(batch)
                time.sleep(PASS1_SLEEP)
                continue

        for item, orig, clean in zip(batch, names, cleaned_names):
            clean = str(clean).strip()
            if not clean or len(clean) < 3:
                skipped += 1
                continue
            if len(examples) < 20 and orig.lower() != clean.lower():
                examples.append((orig, clean))
            item.recipe_name = clean
            updated += 1

        try:
            session.commit()
            log.info(f"  Batch {i//PASS1_BATCH_SIZE+1} ✅ [{km.label()}] | updated={updated}")
        except Exception as e:
            session.rollback()
            log.error(f"  Commit failed: {e}")
            errors += len(batch)

        if not km.is_ollama():
            time.sleep(PASS1_SLEEP)

    if examples:
        print(f"\n  PASS 1 SAMPLE CHANGES ({len(examples)} shown):")
        print("  " + "-"*61)
        for o, c in examples:
            print(f"  BEFORE : {o[:55]}")
            print(f"  AFTER  : {c}")
            print()

    return updated, skipped, errors


# ── Pass 2: Edge cases ────────────────────────────────────────────────────────
def pass2_clean(rows, session, km):
    edges    = [r for r in rows if looks_weird(r.recipe_name)]
    updated  = skipped = 0
    examples = []

    log.info(f"\n{'='*65}")
    log.info(f"  PASS 2 — Edge cases | {len(edges)} flagged | Using: {km.label()}")
    log.info(f"{'='*65}")

    if not edges:
        log.info("  No edge cases — all clean!")
        return 0, 0

    for i, item in enumerate(edges):
        orig   = item.recipe_name
        prompt = f"""Clean this dish name for a diet app.
What is the actual dish? Fix any OCR errors or typos. Return the shortest natural name.
Max 5 words. Return ONLY the name, nothing else.

Name: "{orig}" """

        resp = call_ai(prompt, km, PASS2_MODEL, thinking=not km.is_ollama())
        sleep = OLLAMA_SLEEP if km.is_ollama() else PASS2_SLEEP
        time.sleep(sleep)

        if not resp:
            skipped += 1
            continue

        clean = resp.strip().strip('"').strip("'")
        if not clean or len(clean) < 3:
            skipped += 1
            continue

        if len(examples) < 15:
            examples.append((orig, clean))

        item.recipe_name = clean
        updated += 1
        try:
            session.commit()
            log.info(f"  [{i+1}/{len(edges)}] [{km.label()}] '{orig[:30]}' → '{clean}'")
        except Exception as e:
            session.rollback()
            skipped += 1

    if examples:
        print(f"\n  PASS 2 SAMPLE CHANGES ({len(examples)} shown):")
        print("  " + "-"*61)
        for o, c in examples:
            print(f"  BEFORE : {o[:55]}")
            print(f"  AFTER  : {c}")
            print()

    return updated, skipped


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    km      = KeyManager(API_KEYS)
    engine  = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    log.info("Fetching 6k_dataset rows...")
    rows = session.query(FoodItem).filter(FoodItem.source == "6k_dataset").all()
    log.info(f"Found {len(rows)} rows")

    p1_u, p1_s, p1_e = pass1_clean(rows, session, km)
    rows = session.query(FoodItem).filter(FoodItem.source == "6k_dataset").all()
    p2_u, p2_s = pass2_clean(rows, session, km)

    session.close()

    print("\n" + "="*65)
    print("  FINAL SUMMARY")
    print(f"  Pass 1 — Updated: {p1_u} | Skipped: {p1_s} | Errors: {p1_e}")
    print(f"  Pass 2 — Updated: {p2_u} | Skipped: {p2_s}")
    print(f"  Total cleaned   : {p1_u + p2_u}")
    if km.is_ollama():
        print("  Ollama was used")
    print("="*65)

if __name__ == "__main__":
    main()
