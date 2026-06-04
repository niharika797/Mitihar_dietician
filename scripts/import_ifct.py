"""
Extract Table 1 (Proximate Principles) from IFCT2017.pdf.
Match against ingredients table via 3-pass strategy.
Dry-runs first; writes to DB only if match rate >= 30%.

Column order in Table 1 (per 100g edible portion):
  moisture | protein | ash | fat | fiber_total | fiber_ins | fiber_sol | carbs | energy_KJ

Usage:
  python -m scripts.import_ifct           # dry run (always safe)
  python -m scripts.import_ifct --write   # write to DB if rate >= 30%
"""
import pdfplumber, re, os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine, text

PDF = r"C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\IFCT2017.pdf"
MATCH_THRESHOLD = 0.30

# ── 1. Extract Table 1 rows from PDF ────────────────────────────────────────

# Each food row starts with a food code: 1-2 uppercase letters + 3-4 digits
FOOD_CODE_RE = re.compile(r'^([A-Z]{1,2}\d{3,4})\s+', re.MULTILINE)
# Single integer = region count, appears between name and first decimal
# Use greedy match up to the first decimal cluster
ROW_RE = re.compile(
    r'^([A-Z]{1,2}\d{3,4})\s+'     # food code
    r'(.*?)\s+'                      # food name (non-greedy)
    r'(\d)\s+'                       # region count (single digit)
    r'([\d.±\s]+)$',                 # all numeric values
    re.MULTILINE
)


def parse_row(line: str) -> dict | None:
    m = ROW_RE.match(line.rstrip())
    if not m:
        return None
    code     = m.group(1)
    raw_name = m.group(2).strip()
    # Strip scientific name in parentheses
    name = re.sub(r'\s*\([^)]*\)\s*', ' ', raw_name).strip().strip(',').strip()
    # Strip ±std parts BEFORE extracting values — otherwise stds are captured as extra columns
    cleaned = re.sub(r'±[\d.]+', '', m.group(4))
    # Now capture both decimals and integers (energy like 1340 has no decimal point)
    nums = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', cleaned)]
    if len(nums) < 6:
        return None
    # Map columns based on count
    if len(nums) >= 9:
        # moisture[0] protein[1] ash[2] fat[3] fibtotal[4] fibins[5] fibsol[6] carbs[7] ekj[8]
        protein, fat, fiber, carbs, ekj = nums[1], nums[3], nums[4], nums[7], nums[8]
    elif len(nums) == 8:
        # likely missing one fiber sub-column
        protein, fat, fiber, carbs, ekj = nums[1], nums[3], nums[4], nums[6], nums[7]
    elif len(nums) == 7:
        protein, fat, fiber, carbs, ekj = nums[1], nums[3], nums[4], nums[5], nums[6]
    else:   # 6 columns — no fiber breakdown
        protein, fat, fiber, carbs, ekj = nums[1], nums[3], 0.0, nums[4], nums[5]

    kcal = ekj / 4.184
    return {"code": code, "name": name, "protein": protein, "fat": fat,
            "fiber": fiber, "carbs": carbs, "kcal": kcal}


def is_table1_row(entry: dict) -> bool:
    """Filter out mineral/vitamin table rows that sneak through via same food codes."""
    return (
        entry["kcal"] > 10 and
        entry["protein"] + entry["fat"] + entry["carbs"] > 3 and
        entry["protein"] < 100 and
        entry["fat"] < 100 and
        entry["carbs"] < 100
    )


print("Extracting Table 1 rows from IFCT2017.pdf ...")
ifct_raw: dict[str, dict] = {}   # code → entry (first valid Table 1 hit wins)

with pdfplumber.open(PDF) as pdf:
    for page in pdf.pages:
        page_text = page.extract_text() or ""
        for line in page_text.splitlines():
            if not FOOD_CODE_RE.match(line):
                continue
            entry = parse_row(line)
            if entry is None:
                continue
            if not is_table1_row(entry):
                continue
            code = entry["code"]
            if code not in ifct_raw:   # first valid hit wins (Table 1 comes before Table 2)
                ifct_raw[code] = entry

print(f"  Extracted {len(ifct_raw)} valid Table 1 entries")

# ── 2. Build IFCT lookup maps ────────────────────────────────────────────────

NOISE = re.compile(r'[^a-z0-9 ]')
STOP  = {"with", "from", "for", "and", "the", "raw", "dry", "fresh",
         "dried", "whole", "boiled", "cooked", "ground", "tender", "ripe"}

# Skip measurement-phrase ingredient names (data-entry artifacts where
# quantity is baked into the name, e.g. "1/2 cups whole wheat flour").
# Note: deliberately excludes "gram/gm" to preserve legumes like "Bengal gram".
ARTIFACT_RE = re.compile(
    r'^\s*[\d/]'
    r'|tablespoon|teaspoon|\btbsp\b|\btsp\b|\bcup\b|\bcups\b|\bml\b|\bkg\b'
    r'|\b(or|to)\s+\d',
    re.IGNORECASE
)


def normalize(s: str) -> str:
    s = re.sub(r'\([^)]*\)', '', str(s))   # drop (scientific names)
    s = NOISE.sub(' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()


def significant_tokens(s: str) -> set[str]:
    return {w for w in normalize(s).split() if len(w) >= 4 and w not in STOP}


# Map: normalized_name → entry  (multiple keys per entry)
ifct_by_norm: dict[str, dict] = {}
for entry in ifct_raw.values():
    full_norm = normalize(entry["name"])
    ifct_by_norm.setdefault(full_norm, entry)
    # also index by first comma-segment
    primary = normalize(entry["name"].split(",")[0])
    ifct_by_norm.setdefault(primary, entry)

# ── 3. Load our ingredients ──────────────────────────────────────────────────

engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))
with engine.connect() as conn:
    our_rows = conn.execute(text(
        "SELECT id, name, name_normalized FROM ingredients ORDER BY id"
    )).fetchall()

print(f"  Our ingredients : {len(our_rows)}")

# ── 4. Three-pass matching ───────────────────────────────────────────────────

matches: list[tuple] = []   # (our_id, our_name, ifct_entry, strategy)
used_ifct: set[str] = set() # ifct codes already assigned

def try_match(our_id, our_name, our_norm) -> tuple | None:
    # Pass 1: exact normalized name
    if our_norm in ifct_by_norm:
        e = ifct_by_norm[our_norm]
        if e["code"] not in used_ifct:
            return (our_id, our_name, e, "exact")

    # Pass 2: primary segment of our name matches any IFCT key
    primary_our = normalize(our_norm.split(",")[0])
    if primary_our != our_norm and primary_our in ifct_by_norm:
        e = ifct_by_norm[primary_our]
        if e["code"] not in used_ifct:
            return (our_id, our_name, e, "primary")

    # Pass 3: ≥2 significant word overlap
    our_toks = significant_tokens(our_name)
    if len(our_toks) < 1:
        return None
    best_overlap, best_entry = 0, None
    for entry in ifct_raw.values():
        if entry["code"] in used_ifct:
            continue
        shared = our_toks & significant_tokens(entry["name"])
        if len(shared) >= 2 and len(shared) > best_overlap:
            best_overlap = len(shared)
            best_entry = entry
    if best_entry:
        return (our_id, our_name, best_entry, f"overlap({best_overlap})")

    return None


for r in our_rows:
    our_id, our_name = r[0], r[1]
    our_norm = r[2] if r[2] else normalize(our_name)
    if ARTIFACT_RE.search(our_name or our_norm):
        continue
    result = try_match(our_id, our_name, our_norm)
    if result:
        matches.append(result)
        used_ifct.add(result[2]["code"])

# ── 5. Print full match list ─────────────────────────────────────────────────

rate = len(matches) / len(our_rows)
print(f"\n{'='*65}")
print(f"MATCH RESULTS: {len(matches)} / {len(our_rows)} ({rate*100:.1f}%)")
print(f"{'='*65}")
print(f"{'Strategy':<20} {'Count'}")
by_strat: dict[str, int] = {}
for m in matches:
    k = m[3].split("(")[0]
    by_strat[k] = by_strat.get(k, 0) + 1
for k, v in sorted(by_strat.items()):
    print(f"  {k:<18} {v}")

print(f"\n--- Full match list ({len(matches)} entries) ---")
for m in sorted(matches, key=lambda x: x[1]):
    e = m[2]
    print(f"  [{m[3]:12}] '{m[1][:30]:30}' → [{e['code']}] {e['name'][:40]:40} "
          f"| kcal={e['kcal']:5.0f} P={e['protein']:.1f} F={e['fat']:.1f} "
          f"C={e['carbs']:.1f} Fib={e['fiber']:.1f}")

# ── 6. Apply blocklist — known wrong variety or clearly bad kcal ────────────

BLOCKLIST = {
    ("onion",   "D058"),   # Onion, stalk = spring onion; not regular bulb onion
    ("egg",     "M001"),   # kcal=12 — clearly wrong for whole egg
    ("prawns",  "S009"),   # kcal=19 — too low, likely micro-nutrient table row
    ("pork",    "O053"),   # Pork, liver — wrong cut for generic "pork"
}

def is_clean(m: tuple) -> bool:
    our_key  = (m[1].lower().strip(), m[2]["code"])
    if our_key in BLOCKLIST:
        return False
    if m[2]["kcal"] < 10:      # absolute floor — no real food macronutrient table has < 10 kcal
        return False
    return True

clean_matches = [m for m in matches if is_clean(m)]
blocked_count = len(matches) - len(clean_matches)
print(f"\nBlocklisted / below kcal floor : {blocked_count} removed")
print(f"Final clean matches            : {len(clean_matches)}")

print(f"\n--- FINAL CLEAN LIST ({len(clean_matches)} entries) ---")
for m in sorted(clean_matches, key=lambda x: x[1]):
    e = m[2]
    print(f"  [{m[3]:12}] '{m[1][:30]:30}' → [{e['code']}] {e['name'][:40]:40} "
          f"| kcal={e['kcal']:5.0f} P={e['protein']:.1f} F={e['fat']:.1f} "
          f"C={e['carbs']:.1f} Fib={e['fiber']:.1f}")

# ── 7. Write to DB if rate >= threshold ─────────────────────────────────────

write_mode = "--write" in sys.argv

if not write_mode:
    print("\nDry run — pass --write to apply changes.")
    sys.exit(0)

print(f"\nWriting {len(clean_matches)} ingredient updates to DB (source='IFCT2017') ...")
with engine.begin() as conn:
    for m in clean_matches:
        our_id, our_name, e = m[0], m[1], m[2]
        conn.execute(text("""
            UPDATE ingredients
            SET calories_per_100g = :kcal,
                protein_per_100g  = :pro,
                fat_per_100g      = :fat,
                carbs_per_100g    = :carb,
                fiber_per_100g    = :fib,
                source            = 'IFCT2017',
                is_verified       = true
            WHERE id = :id
        """), {"kcal": round(e["kcal"], 2), "pro": e["protein"], "fat": e["fat"],
               "carb": e["carbs"],           "fib": e["fiber"],  "id": our_id})

print(f"Done. {len(clean_matches)} ingredients upgraded to IFCT2017.")
print("Next: re-run scripts/recalculate_recipe_nutrition.py to propagate to food_items.")
