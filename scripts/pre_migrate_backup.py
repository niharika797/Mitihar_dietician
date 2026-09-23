"""
Pre-migration snapshot: pg_dump → timestamped file, then run alembic upgrade head.

Usage:
    python -m scripts.pre_migrate_backup

What it does:
  1. Creates backups/ directory if missing.
  2. Runs pg_dump via the mityahar_postgres Docker container.
     (No local pg_dump binary required — uses the pg_dump inside the container.)
  3. Writes backups/pre_migrate_<timestamp>.dump (custom format, ~5-10x compressed).
  4. Prints the backup path and size.
  5. Runs alembic upgrade head.

GCP Cloud SQL equivalent (no action needed locally):
  - Cloud SQL performs automated daily backups by default (retained 7 days).
  - Before any migration: Cloud SQL console → Instance → Backups → "Create backup".
  - For point-in-time recovery: enable "Enable point-in-time recovery" on instance
    (writes to Cloud Storage); recovery_window_days default = 7.
  - Runbook: (1) console backup, (2) run migration, (3) if broken → restore to backup
    via "Restore" button or gcloud sql backups restore <BACKUP_ID> --restore-instance=INSTANCE.
  - Reference: https://cloud.google.com/sql/docs/postgres/backup-recovery/restoring
"""

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).parents[1]
BACKUPS_DIR = BASE / "backups"
BACKUPS_DIR.mkdir(exist_ok=True)

DB_CONTAINER = "mityahar_postgres"
DB_NAME = "mityahar_db"
DB_USER = os.environ.get("POSTGRES_USER", "admin")
DB_PASS = os.environ.get("POSTGRES_PASSWORD", "")


def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_path = BACKUPS_DIR / f"pre_migrate_{ts}.dump"

    print(f"[backup] target: {dump_path}")
    print(f"[backup] DB: {DB_NAME} on container {DB_CONTAINER}")

    # pg_dump runs inside the container — no local pg_dump required.
    # Custom format (-Fc) is binary + compressed; restore via pg_restore.
    cmd = [
        "docker", "exec", "-e", f"PGPASSWORD={DB_PASS}",
        DB_CONTAINER,
        "pg_dump",
        "-U", DB_USER,
        "-d", DB_NAME,
        "-Fc",            # custom format: binary, compressed
        "--no-password",
    ]

    t0 = time.perf_counter()
    result = subprocess.run(cmd, capture_output=True)
    elapsed = time.perf_counter() - t0

    if result.returncode != 0:
        print(f"[backup] FAILED (exit {result.returncode})")
        print(result.stderr.decode(errors="replace"))
        sys.exit(1)

    dump_path.write_bytes(result.stdout)
    size_kb = dump_path.stat().st_size / 1024
    print(f"[backup] OK: {size_kb:.0f} KB in {elapsed:.1f}s -> {dump_path.name}")
    print(f"[backup] Restore: docker exec -i {DB_CONTAINER} pg_restore -U {DB_USER} -d {DB_NAME} -Fc < {dump_path}")

    print("\n[migrate] Running: alembic upgrade head")
    migrate = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BASE),
    )
    if migrate.returncode != 0:
        print(f"[migrate] FAILED — backup preserved at {dump_path}")
        sys.exit(migrate.returncode)

    print(f"[migrate] Done. Backup at: {dump_path}")


if __name__ == "__main__":
    main()
