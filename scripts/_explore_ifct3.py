"""Scan all IFCT pages, count food entries, identify categories and column structure."""
import pdfplumber, re

PDF = r"C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\IFCT2017.pdf"

# Food code pattern: letter(s) + 3-4 digits
CODE_RE = re.compile(r'^([A-Z]{1,2}\d{3,4})\s+(.*?)\s+(\d)\s+([\d.]+)', re.MULTILINE)

# For each row: CODE NAME N_REGIONS MOISTURE PROTEIN ASH FAT FIBTG FIBINS FIBSOL CARB ENERGY_KJ
# Values may have ±std
NUM_PAT = r'([\d.]+)(?:±[\d.]+)?'
ROW_RE  = re.compile(
    r'^([A-Z]{1,2}\d{3,4})\s+(.*?)\s+(\d)\s+' +
    r'\s+'.join([NUM_PAT] * 9),
    re.MULTILINE
)

with pdfplumber.open(PDF) as pdf:
    total = len(pdf.pages)
    print(f"Total pages: {total}")

    all_entries = []
    category_codes = {}
    data_page_range = [9999, 0]

    for i in range(total):
        text = pdf.pages[i].extract_text() or ""
        matches = ROW_RE.findall(text)
        if matches:
            if i+1 < data_page_range[0]: data_page_range[0] = i+1
            if i+1 > data_page_range[1]: data_page_range[1] = i+1
            for m in matches:
                code = m[0]
                name = m[1].strip()
                cat  = code[0]
                category_codes[cat] = category_codes.get(cat, 0) + 1
                all_entries.append({
                    "code": code, "name": name,
                    "moisture": float(m[3]), "protein": float(m[4]), "ash": float(m[5]),
                    "fat": float(m[6]), "fiber": float(m[7]),
                    "carbs": float(m[10]), "energy_kj": float(m[11])
                })

    print(f"\nData page range  : {data_page_range[0]} – {data_page_range[1]}")
    print(f"Total food entries: {len(all_entries)}")
    print(f"\nCategory breakdown:")
    for cat, cnt in sorted(category_codes.items()):
        print(f"  {cat}: {cnt} foods")

    print(f"\nSample entries (first 10):")
    for e in all_entries[:10]:
        kcal = e["energy_kj"] / 4.184
        print(f"  [{e['code']}] {e['name'][:50]}")
        print(f"    kcal={kcal:.0f} pro={e['protein']}g fat={e['fat']}g carb={e['carbs']}g fib={e['fiber']}g")

    print(f"\nSample O/P category (spices/oils):")
    for e in all_entries:
        if e["code"][0] in ("O", "P"):
            kcal = e["energy_kj"] / 4.184
            print(f"  [{e['code']}] {e['name'][:50]} | kcal={kcal:.0f} pro={e['protein']}g carb={e['carbs']}g fat={e['fat']}g")
            if all_entries.index(e) > 5 and e["code"][0] == "P":
                break

    # Quick match check against our ingredient names
    import os, sys
    sys.path.insert(0, r"C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician")
    from dotenv import load_dotenv; load_dotenv()
    from sqlalchemy import create_engine, text
    engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))
    with engine.connect() as conn:
        our_rows = conn.execute(text("SELECT id, name, name_normalized FROM ingredients")).fetchall()

    def norm(s):
        return re.sub(r'[^a-z0-9 ]', '', str(s).lower()).strip()

    # Build IFCT lookup: normalized_name → entry
    ifct_map = {}
    for e in all_entries:
        # Try various normalizations of IFCT name
        # "Dates, dry, pale brown (Phoenix dactylifera)" → "dates dry pale brown"
        clean = re.sub(r'\(.*?\)', '', e["name"])  # remove (scientific name)
        clean = norm(clean)
        ifct_map[clean] = e
        # Also: first word/phrase before first comma
        primary = norm(e["name"].split(",")[0])
        if primary not in ifct_map:
            ifct_map[primary] = e

    our_norms = [(r[0], r[1], r[2] if r[2] else norm(r[1])) for r in our_rows]

    exact_matches = [(r[0], r[1], ifct_map[r[2]]) for r in our_norms if r[2] in ifct_map]
    print(f"\n=== Quick match: {len(exact_matches)} / {len(our_rows)} ({len(exact_matches)/len(our_rows)*100:.1f}%) ===")
    print("Matched (first 20):")
    for m in exact_matches[:20]:
        e = m[2]
        kcal = e["energy_kj"] / 4.184
        print(f"  '{m[1]}' → [{e['code']}] {e['name'][:45]} | kcal={kcal:.0f}")
