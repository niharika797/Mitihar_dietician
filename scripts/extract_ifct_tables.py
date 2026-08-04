"""
Extract IFCT2017 tables faithfully to xlsx/json — text-layer, no OCR, fully local.

Strategy: PyMuPDF find_tables(strategy="text") on each page (the PDF is
borderless + has a no-extraction permission flag that camelot honours but
PyMuPDF ignores). Data rows are located by food-code regex; the trailing N
numeric cells are the nutrient values, so below-detectable-limit BLANKS keep
their column position (never coerced to 0). Column titles are the standardised
IFCT variable codes (hardcoded per table — the printed headers are rotated and
unreliable). Cell values are kept verbatim ("mean±SD") for faithfulness.

Run:  python -m scripts.extract_ifct_tables --table 1
      python -m scripts.extract_ifct_tables --table 1 --verify
"""
from __future__ import annotations
import argparse, json, re, os
import fitz  # PyMuPDF
import pandas as pd

PDF = os.path.join(os.path.dirname(__file__), "..", "IFCT2017.pdf")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "IFCT2017_extracted")
CODE_RE = re.compile(r"^[A-Z]\d{3}")   # prefix: some code tokens merge with the name ("A007Maize")

# Per-table: (1-based page range inclusive, ordered nutrient variable codes).
# Only Table 1 wired for the proof; the rest get added once Table 1 is signed off.
TABLES = {
    1: {
        "pages": (41, 68),
        "codes": ["WATER", "PROTCNT", "ASH", "FATCE", "FIBTG",
                  "FIBINS", "FIBSOL", "CHOAVLDF", "ENERC_KJ"],
        "layout": "dual",   # plant 9-col vs animal 5-col share one header
        "title": "Proximate Principles & Dietary Fibre (per 100g)",
    },
    2: {
        "pages": (71, 98),
        "codes": ["THIA", "RIBF", "NIA", "PANTAC", "VITB6A", "BIOT", "FOLSUM", "VITC"],
        "layout": "xband",  # single grid, below-detection blanks
        "title": "Water-soluble Vitamins (per 100g)",
    },
    3: {
        "pages": (101, 128),
        "codes": ["ERGCAL", "TOCPHA", "TOCPHB", "TOCPHG", "TOCPHD",
                  "TOCTRA", "TOCTRB", "TOCTRG", "TOCTRD", "VITE", "VITK1"],
        "layout": "xband",
        "title": "Fat-soluble Vitamins (per 100g)",
    },
    4: {
        "pages": (131, 147),
        "codes": ["LUTN", "ZEA", "LYCPN", "CRYPXB", "CARTG", "CARTA", "CARTB", "CARTOID"],
        "layout": "xband",
        "title": "Carotenoids (per 100g)",
    },
    5: {
        "pages": (151, 206),
        "layout": "wide2",   # each food spans two facing pages (left cols | right cols)
        "codes_left":  ["AL", "AS", "CD", "CA", "CR", "CO", "CU", "FE", "PB", "LI"],
        "codes_right": ["MG", "MN", "HG", "MO", "NI", "P", "K", "SE", "NA", "ZN"],
        "codes": ["AL", "AS", "CD", "CA", "CR", "CO", "CU", "FE", "PB", "LI",
                  "MG", "MN", "HG", "MO", "NI", "P", "K", "SE", "NA", "ZN"],
        "title": "Minerals & Trace Elements (per 100g)",
    },
    6: {
        "pages": (209, 226),
        "codes": ["CHOAVL", "STARCH", "FRUS", "GLUS", "SUCS", "MALS", "FRSUG"],
        "layout": "xband",
        "title": "Starch & Individual Sugars (per 100g)",
    },
    7: {
        "pages": (227, 296),
        "layout": "wide2",
        "codes_left":  ["F10D0", "F12D0", "F14D0", "F16D0", "F18D0", "F20D0",
                        "F22D0", "F24D0", "F14D1", "F16D1", "F18D1N9"],
        "codes_right": ["F20D1N9", "F22D1N9", "F24D1N9", "F18D2N6", "F20D2",
                        "F18D3N3", "F20D4N6", "FASAT", "FAMS", "FAPU"],
        "codes": ["F10D0", "F12D0", "F14D0", "F16D0", "F18D0", "F20D0", "F22D0",
                  "F24D0", "F14D1", "F16D1", "F18D1N9", "F20D1N9", "F22D1N9",
                  "F24D1N9", "F18D2N6", "F20D2", "F18D3N3", "F20D4N6",
                  "FASAT", "FAMS", "FAPU"],
        "title": "Fatty Acid Profile (per 100g)",
    },
}


def _fix(s: str) -> str:
    # PyMuPDF renders ± as U+FFFD in this PDF's encoding — restore it.
    return s.replace("�", "±").strip()


VAL_RE = re.compile(r"^([<]?\d|ND$|tr$|traces$)")   # a nutrient value token


def _bands_from_page(page) -> list[list]:
    """Group words into data rows, anchored on the food-code word (nearest-code
    by y). Returns each row as x-sorted word tuples. Drops the rotated left block
    via the 'right of code' filter. Values may be sparse (animal foods omit
    fibre/carb) — column assignment is by x, done later, so blanks stay in place."""
    words = page.get_text("words")
    coded = [w for w in words if CODE_RE.match(_fix(w[4]))]
    if not coded:
        return []
    ycs = [(cw[1] + cw[3]) / 2 for cw in coded]
    bands: list[list] = [[] for _ in coded]
    for w in words:
        yc = (w[1] + w[3]) / 2
        j = min(range(len(coded)), key=lambda k: abs(ycs[k] - yc))
        if abs(ycs[j] - yc) <= 8 and w[0] >= coded[j][0] - 1:
            bands[j].append(w)
    return [sorted(b, key=lambda w: w[0]) for b in bands]


def _parse_band(band) -> tuple | None:
    """(code, name, regions, [(x_right, value_text), ...]) from one row's words."""
    txt = [_fix(w[4]) for w in band]
    num_idx = [i for i in range(1, len(txt)) if VAL_RE.match(txt[i])]
    if not num_idx:
        return None
    r = num_idx[0]                                   # first numeric = No. of regions
    code = txt[0][:4]
    name = (txt[0][4:] + " " + " ".join(txt[1:r])).strip()
    values = [(band[i][2], txt[i]) for i in num_idx[1:]]   # (x1 right-edge, value)
    return code, name, txt[r], values


def _extract_pages(pidxs, codes, layout="xband") -> list[dict]:
    """Extract rows for a set of pages against one column schema. Shared by
    single-wide tables and by each half of a double-page-wide table."""
    n = len(codes)
    doc = fitz.open(PDF)
    parsed = []
    for pidx in pidxs:
        for band in _bands_from_page(doc[pidx]):
            p = _parse_band(band)
            if p:
                parsed.append(p)

    # Column x-anchors. Prefer the median x of each column taken from FULLY
    # populated rows (exact, collision-free). When too few full rows exist
    # (sparse vitamin/mineral tables), fall back to clustering all value
    # x-positions into N groups at the N-1 widest gaps.
    import statistics
    full = [vals for *_h, vals in parsed if len(vals) == n]
    if len(full) >= 8:   # enough fully-populated rows → exact per-column medians
        anchors = [statistics.median(row[k][0] for row in full) for k in range(n)]
    else:
        xs = sorted(x for *_h, vals in parsed for x, _v in vals)
        cuts = sorted(sorted(range(1, len(xs)), key=lambda i: xs[i] - xs[i - 1],
                             reverse=True)[:n - 1]) if len(xs) > n else []
        clusters, prev = [], 0
        for c in cuts + [len(xs)]:
            clusters.append(xs[prev:c])
            prev = c
        anchors = [statistics.median(c) for c in clusters] if clusters else [0] * n

    # Table 1 "dual": plant foods fill all 9 columns; animal foods (meat/fish) omit
    # the 4 fibre/carb columns and lay their 5 values on a *different* x-grid — so map
    # by value-count. "xband": single grid, below-detection blanks → map every value
    # to the nearest column anchor by x-position (blanks keep their slot).
    ANIMAL_SLOTS = [0, 1, 2, 3, n - 1]               # WATER,PROTCNT,ASH,FATCE,…,ENERC
    records, seen, flagged = [], set(), []
    for code, name, regions, values in parsed:
        if code in seen:
            continue
        seen.add(code)
        slots = [""] * n
        vals = [v for _x, v in values]
        if layout == "dual" and len(vals) == n:
            slots = vals[:]                          # full plant row → in order
        elif layout == "dual" and len(vals) == len(ANIMAL_SLOTS):
            for pos, v in zip(ANIMAL_SLOTS, vals):   # animal row → fixed sub-schema
                slots[pos] = v
        else:                                        # xband (default) or dual-oddball
            for x_right, v in values:
                slots[min(range(n), key=lambda k: abs(anchors[k] - x_right))] = v
            if len(vals) > n:
                flagged.append(code)                 # more values than columns — review
    # (record assembled below)
        rec = {"Food Code": code, "Food Name": name, "No_of_Regions": regions}
        rec.update(dict(zip(codes, slots)))
        records.append(rec)
    if flagged:
        print(f"  [!] {len(flagged)} rows had MORE values than columns (review): {flagged}")
    return records


def extract_table(tnum: int) -> pd.DataFrame:
    spec = TABLES[tnum]
    p0, p1 = spec["pages"]
    if spec.get("layout") == "wide2":
        # Double-page-wide: each food spans two facing pages. Even offset = left
        # column-set, odd offset = right. Extract each side, merge by food code.
        left_pg = [i for i in range(p0 - 1, p1) if (i - (p0 - 1)) % 2 == 0]
        right_pg = [i for i in range(p0 - 1, p1) if (i - (p0 - 1)) % 2 == 1]
        left = _extract_pages(left_pg, spec["codes_left"])
        right = {r["Food Code"]: r for r in _extract_pages(right_pg, spec["codes_right"])}
        records = []
        for l in left:
            m = dict(l)
            r = right.get(l["Food Code"], {})
            for c in spec["codes_right"]:
                m[c] = r.get(c, "")
            records.append(m)
        return pd.DataFrame(records)
    return pd.DataFrame(_extract_pages(range(p0 - 1, p1), spec["codes"], spec.get("layout", "xband")))


def verify(tnum: int, df: pd.DataFrame) -> None:
    """Confirm EVERY extracted value appears verbatim in the source text layer.

    Baseline is fitz's own full-page text (complete, no line-wrap loss — unlike
    pdfplumber, which drops values on long-name rows). Checks value presence, not
    column placement (column order is trusted from the header-code sequence)."""
    spec = TABLES[tnum]
    doc = fitz.open(PDF)
    text = " ".join((doc[i].get_text() or "")
                     for i in range(spec["pages"][0] - 1, spec["pages"][1])).replace("�", "±")
    checked = miss = 0
    misses = []
    for _, r in df.iterrows():
        for c in spec["codes"]:
            if r[c]:
                checked += 1
                if r[c] not in text:
                    miss += 1
                    misses.append((r["Food Code"], c, r[c]))
    print(f"verify: {checked - miss}/{checked} values present in source"
          + (f"  MISSES: {misses[:5]}" if misses else "  (exact)"))

    # A wrapped multi-line name that got word-scrambled shows its ')' before
    # its matching '(' (e.g. "seed, black (Amaranthus" ... "cruentus)"). Known
    # limitation: some multi-region rows wrap the species suffix onto a
    # separate text block whose reading order isn't recoverable from x/y
    # alone (see BUILD_TRACKER.md) — flagged, not fixed, so callers doing
    # name-matching against these rows should treat the parenthetical as
    # untrusted for the affected codes.
    scrambled = [r["Food Code"] for _, r in df.iterrows()
                 if ")" in r["Food Name"] and "(" in r["Food Name"]
                 and r["Food Name"].index(")") < r["Food Name"].index("(")]
    if scrambled:
        print(f"  [!] {len(scrambled)} Food Name values have scrambled word "
              f"order (paren mismatch): {scrambled[:5]}{'...' if len(scrambled) > 5 else ''}")


def probe(p0: int, p1: int) -> None:
    """Survey a page range: value-count distribution, column anchors, header codes,
    a sample data row. Used to design each table's schema before extraction."""
    from collections import Counter
    import statistics
    doc = fitz.open(PDF)
    counts, sample = Counter(), None
    fulls: list = []
    header_codes: list = []
    for pidx in range(p0 - 1, p1):
        # header variable-code tokens (uppercase, >=3 chars) on early pages
        if not header_codes:
            toks = [_fix(w[4]) for w in doc[pidx].get_text("words")]
            hc = [t for t in toks if re.fullmatch(r"[A-Z]{3,}[A-Z0-9]*", t)]
            if len(hc) >= 3:
                header_codes = hc
        for band in _bands_from_page(doc[pidx]):
            p = _parse_band(band)
            if not p:
                continue
            k = len(p[3])
            counts[k] += 1
            if sample is None and k == max(counts, key=counts.get):
                sample = p
    doc2 = fitz.open(PDF)
    for pidx in range(p0 - 1, p1):
        for band in _bands_from_page(doc2[pidx]):
            p = _parse_band(band)
            if p and len(p[3]) == counts.most_common(1)[0][0]:
                fulls.append(p[3])
    dom = counts.most_common(1)[0][0]
    anchors = [round(statistics.median(r[k][0] for r in fulls)) for k in range(dom)]
    total = sum(counts.values())
    print(f"pages {p0}-{p1}: {total} rows | value-count dist {dict(counts)}")
    print(f"  dominant cols={dom}  anchors={anchors}")
    print(f"  header codes seen: {header_codes[:20]}")
    if sample:
        print(f"  sample {sample[0]} '{sample[1][:24]}' regions={sample[2]} vals={[v for _,v in sample[3]]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", type=int, default=1)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--write", action="store_true", help="write xlsx/json to disk")
    ap.add_argument("--all", action="store_true", help="write every configured table to one workbook")
    a = ap.parse_args()

    if a.all:
        os.makedirs(OUT, exist_ok=True)
        combined = os.path.join(OUT, "IFCT2017_all_tables.xlsx")
        with pd.ExcelWriter(combined) as xw:
            for tn in sorted(TABLES):
                df = extract_table(tn)
                df.to_excel(xw, index=False, sheet_name=f"Table{tn}")
                with open(os.path.join(OUT, f"IFCT_Table{tn}.json"), "w", encoding="utf-8") as f:
                    json.dump(df.to_dict("records"), f, ensure_ascii=False, indent=2)
                print(f"  Table{tn}: {len(df)} rows")
                verify(tn, df)
        print(f"wrote {combined}")
        return

    df = extract_table(a.table)
    spec = TABLES[a.table]
    print(f"Table {a.table} — {spec['title']}")
    print(f"rows extracted: {len(df)}  (pages {spec['pages'][0]}-{spec['pages'][1]})")
    print(df.head(4).to_string(index=False, max_colwidth=16))

    if a.verify:
        verify(a.table, df)

    if a.write:
        os.makedirs(OUT, exist_ok=True)
        xlsx = os.path.join(OUT, f"IFCT_Table{a.table}.xlsx")
        df.to_excel(xlsx, index=False, sheet_name=f"Table{a.table}")
        with open(os.path.join(OUT, f"IFCT_Table{a.table}.json"), "w", encoding="utf-8") as f:
            json.dump(df.to_dict("records"), f, ensure_ascii=False, indent=2)
        print(f"wrote {xlsx}")


if __name__ == "__main__":
    main()
