"""
Get this session's local-only data fixes (quantity rebuild, ingredient dedup,
IFCT wiring) onto staging.

Why this can't just be "re-run the fix scripts against staging DATABASE_URL":
  - rebuild_ingredient_quantities.py diffs against a local-only backup file
    (db-backups/mityahar_content_2026-07-31.sql) and writes a CSV that a human
    reviews before scripts/import_recipe_ingredients_review.py applies it --
    not a single re-runnable step.
  - populate_ingredient_nutrition.py reads data/IFCT2017_extracted/*.csv/json
    -- `data/` is entirely gitignored (see .gitignore:79), so none of that is
    in the deployed image; a Cloud Run job can't read files that were never
    shipped.
  - merge_duplicate_ingredients.py IS a clean re-runnable DB-only operation,
    but on its own it's only 1 of the 3 fixes.

So the actual portable unit is the *result* already sitting in the local DB,
not the scripts that produced it. This follows the pattern already used in
this repo (db-backups/RESTORE.md): a data-only pg_dump of the affected
tables, restored on the other side. Cloud SQL is private-IP only -- the
restore step has to run from inside the VPC (a Cloud Run job), not from here.

This script only does the LOCAL, safe half: dumps ingredients,
recipe_ingredients, and food_items (data-only) from DATABASE_URL into
db-backups/. It does not touch staging and does not run any gcloud command --
that's a separate, explicit step (printed at the end) because it needs a
human to pick the GCS bucket and confirm the target is really staging.

Usage:
    python -m scripts.promote_data_fixes_to_staging
"""
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

TABLES = ["ingredients", "recipe_ingredients", "food_items"]
OUT_DIR = PROJECT_ROOT / "db-backups"


def local_pg_dump_args(stamp: str) -> tuple[list[str], Path]:
    url = urlparse(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    out = OUT_DIR / f"data_fixes_{stamp}.sql"
    args = [
        "pg_dump",
        "--data-only", "--column-inserts",
        "-h", url.hostname or "localhost",
        "-p", str(url.port or 5432),
        "-U", url.username or "admin",
        "-d", (url.path or "/mityahar_db").lstrip("/"),
    ]
    for t in TABLES:
        args += ["--table", t]
    args += ["-f", str(out)]
    return args, out


def main() -> None:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    args, out_path = local_pg_dump_args(stamp)

    env = os.environ.copy()
    url = urlparse(os.environ["DATABASE_URL"].replace("+asyncpg", ""))
    if url.password:
        env["PGPASSWORD"] = url.password

    print(f"Dumping {', '.join(TABLES)} (data-only) from local DATABASE_URL...")
    result = subprocess.run(args, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        raise SystemExit("pg_dump failed -- is the local Postgres container running?")
    print(f"wrote {out_path} ({out_path.stat().st_size:,} bytes)")

    print("""
NOT run automatically (needs a human to confirm bucket + target):

  1. Upload the dump somewhere the Cloud Run job can read it, e.g.:
       gcloud storage cp "{out}" gs://<staging-artifacts-bucket>/data_fixes_{stamp}.sql

  2. Execute the migrate job with a command override that pulls the file and
     restores it against staging's DATABASE_URL (private-IP Cloud SQL, only
     reachable from inside mityahar-vpc):
       gcloud run jobs execute mityahar-migrate --region asia-south1 \\
         --command bash --args -c,"gcloud storage cp gs://<bucket>/data_fixes_{stamp}.sql /tmp/f.sql && psql \\$DATABASE_URL -f /tmp/f.sql"

  3. Re-run scripts/audit_dangling_weekly_combos.py and
     scripts/find_dropped_recipe_ingredients.py against staging's
     DATABASE_URL afterwards to confirm the numbers moved.

Before step 2: confirm with the user this is really meant to run against
staging (not local dev again) -- this overwrites staging's ingredients/
recipe_ingredients/food_items rows with the local dev versions.
""".format(out=out_path, stamp=stamp))


if __name__ == "__main__":
    main()
