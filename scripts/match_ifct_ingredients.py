"""
Match Mityahar `ingredients` rows -> IFCT2017 food codes. Produces a REVIEWABLE map;
writes nothing to the DB (that's populate_ingredient_nutrition.py).

Pipeline (each ingredient independently -> best IFCT food, many:1 allowed):
  1. deterministic  : exact / primary-segment / >=2-token overlap (ported from import_ifct.py)
  2. fuzzy          : rapidfuzz token_set_ratio top candidate; >=92 auto-accept
  3. llm (--llm)    : local Qwen3.6 validates the 70-92 borderline — "is ingredient X the
                      same food as candidate Y? pick a code or NONE" (precision guard, batched)

Output: data/IFCT2017_extracted/ingredient_ifct_map.csv
  ingredient_id, ingredient_name, ifct_code, ifct_name, strategy, confidence

Run: python -m scripts.match_ifct_ingredients          # deterministic + fuzzy only (free)
     python -m scripts.match_ifct_ingredients --llm    # + Gemini validation of borderline
"""
import csv, json, os, re, sys, urllib.request, urllib.error
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine, text
from rapidfuzz import process, fuzz

BASE = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
IFCT_JSON = os.path.join(BASE, "data", "IFCT2017_extracted", "IFCT_Table1.json")
OUT_CSV = os.path.join(BASE, "data", "IFCT2017_extracted", "ingredient_ifct_map.csv")
# Local Qwen3.6-35B-A3B via llama-server OpenAI endpoint (start_agent.ps1). No rate limits.
LLM_URL = os.environ.get("LOCAL_LLM_URL", "http://localhost:8080/v1/chat/completions")
LLM_MODEL = os.environ.get("LOCAL_LLM_MODEL", "local")   # llama-server ignores the value
FUZZY_ACCEPT = 92     # >= this token_set_ratio: auto-accept without LLM
FUZZY_FLOOR = 70      # < this: no plausible candidate, leave unmatched

NOISE = re.compile(r'[^a-z0-9 ]')
STOP = {"with", "from", "for", "and", "the", "raw", "dry", "fresh",
        "dried", "whole", "boiled", "cooked", "ground", "tender", "ripe"}
ARTIFACT_RE = re.compile(
    r'^\s*[\d/]'
    r'|tablespoon|teaspoon|\btbsp\b|\btsp\b|\bcup\b|\bcups\b|\bml\b|\bkg\b'
    r'|\b(or|to)\s+\d', re.IGNORECASE)


def normalize(s: str) -> str:
    s = re.sub(r'\([^)]*\)', '', str(s))
    s = NOISE.sub(' ', s.lower())
    return re.sub(r'\s+', ' ', s).strip()


def significant_tokens(s: str) -> set:
    return {w for w in normalize(s).split() if len(w) >= 4 and w not in STOP}


def llm(prompt: str) -> str | None:
    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 4096,
    }).encode()
    try:
        req = urllib.request.Request(LLM_URL, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=300) as r:   # 35B on 6GB is slow
            data = json.loads(r.read())
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  llm error: {e}")
        return None


def llm_validate(batch: list[dict]) -> dict[str, str]:
    """batch: [{iid, name, candidates:[(code,name,score)]}] -> {iid: code|''}."""
    lines = []
    for b in batch:
        cand = "; ".join(f"{c[0]}={c[1]}" for c in b["candidates"])
        lines.append(f'{b["iid"]}. "{b["name"]}"  candidates: {cand}')
    prompt = (
        "You match Indian food ingredient names to IFCT food-composition entries.\n"
        "For each ingredient, choose the candidate code that is THE SAME food "
        "(same edible item; ignore raw/cooked/brand wording). If none is the same "
        "food, answer NONE. Return ONLY JSON: {\"<id>\": \"<CODE or NONE>\"}. /no_think\n\n"
        + "\n".join(lines))
    resp = llm(prompt)
    if not resp:
        return {}
    resp = re.sub(r'<think>.*?</think>', '', resp, flags=re.DOTALL)   # strip qwen reasoning
    m = re.search(r'\{.*\}', resp, re.DOTALL)
    if not m:
        return {}
    try:
        raw = json.loads(m.group(0))
    except Exception:
        return {}
    return {str(k): ("" if str(v).upper().startswith("NONE") else str(v).strip())
            for k, v in raw.items()}


def main() -> None:
    use_llm = "--llm" in sys.argv
    ifct = [{"code": r["Food Code"], "name": r["Food Name"]}
            for r in json.load(open(IFCT_JSON, encoding="utf-8"))]
    by_norm: dict[str, dict] = {}
    for e in ifct:
        by_norm.setdefault(normalize(e["name"]), e)
        by_norm.setdefault(normalize(e["name"].split(",")[0]), e)
    ifct_norm_names = {normalize(e["name"]): e for e in ifct}
    fuzzy_choices = list(ifct_norm_names.keys())

    engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))
    with engine.connect() as conn:
        our = conn.execute(text(
            "SELECT id, name, name_normalized FROM ingredients ORDER BY id")).fetchall()

    def deterministic(name, norm):
        if norm in by_norm:
            return by_norm[norm], "exact", 1.0
        primary = normalize(norm.split(",")[0])
        if primary != norm and primary in by_norm:
            return by_norm[primary], "primary", 0.9
        toks = significant_tokens(name)
        best_n, best = 0, None
        for e in ifct:
            shared = toks & significant_tokens(e["name"])
            if len(shared) >= 2 and len(shared) > best_n:
                best_n, best = len(shared), e
        return (best, f"overlap{best_n}", 0.6) if best else (None, None, 0.0)

    results: dict[int, list] = {}      # iid -> [name, code, ifct_name, strategy, conf]
    borderline: list[dict] = []
    for iid, name, norm in our:
        norm = norm or normalize(name)
        if ARTIFACT_RE.search(name or norm):
            results[iid] = [name, "", "", "artifact", 0.0]
            continue
        e, strat, conf = deterministic(name, norm)
        if e:
            results[iid] = [name, e["code"], e["name"], strat, conf]
            continue
        # fuzzy: top-3 candidates
        cands = process.extract(norm, fuzzy_choices, scorer=fuzz.token_set_ratio, limit=3)
        top = cands[0] if cands else None
        if top and top[1] >= FUZZY_ACCEPT:
            e = ifct_norm_names[top[0]]
            results[iid] = [name, e["code"], e["name"], "fuzzy", round(top[1] / 100, 2)]
        elif top and top[1] >= FUZZY_FLOOR:
            results[iid] = [name, "", "", "unmatched", 0.0]   # provisional; LLM may fill
            borderline.append({"iid": iid, "name": name, "candidates":
                               [(ifct_norm_names[c[0]]["code"], ifct_norm_names[c[0]]["name"], c[1]) for c in cands]})
        else:
            results[iid] = [name, "", "", "unmatched", 0.0]

    if use_llm and borderline:
        print(f"LLM-validating {len(borderline)} borderline candidates via local Qwen ...", flush=True)
        code_to_name = {e["code"]: e["name"] for e in ifct}
        for i in range(0, len(borderline), 15):
            chunk = borderline[i:i + 15]
            picks = llm_validate(chunk)
            for b in chunk:
                code = picks.get(str(b["iid"]), "")
                if code and code in code_to_name:
                    results[b["iid"]] = [b["name"], code, code_to_name[code], "llm", 0.85]
            hits = sum(1 for b in chunk if picks.get(str(b["iid"])))
            print(f"  batch {i//15+1}: {hits}/{len(chunk)} validated "
                  f"({min(i+15, len(borderline))}/{len(borderline)})", flush=True)

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ingredient_id", "ingredient_name", "ifct_code", "ifct_name", "strategy", "confidence"])
        for iid in sorted(results):
            r = results[iid]
            w.writerow([iid, r[0], r[1], r[2], r[3], r[4]])

    total = len(our)
    by_strat: dict[str, int] = {}
    for r in results.values():
        by_strat[r[3]] = by_strat.get(r[3], 0) + 1
    matched = sum(v for k, v in by_strat.items() if k not in ("artifact", "unmatched"))
    print(f"\ningredients: {total} | MATCHED: {matched} ({matched/total*100:.1f}%) "
          f"| artifacts: {by_strat.get('artifact',0)} | unmatched: {by_strat.get('unmatched',0)}")
    print("by strategy:", {k: v for k, v in sorted(by_strat.items())})
    print(f"wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
