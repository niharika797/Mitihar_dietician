# Restoring the Mityahar content database

The food / recipe / ingredient / meal-template data is **not** produced by the seed scripts
anymore. `seed_food_items.py` is broken (references the dropped `instructions` column) and
`seed_6k_recipes.py` needs a USDA API key + ~6000 live calls. Restore the committed content
dump instead — no API keys, no Firebase required.

**`db-backups/mityahar_content_2026-07-30.sql`** — data-only: ~2116 dishes, 950 ingredients
(with IFCT2017 nutrition), ~18k `recipe_ingredients`, 180 meal templates, plus the medical
`avoid_tags`/`prefer_tags`. **No patient/doctor data** — create your own accounts (step 4).
FK-clean (doctor links nulled) and sequences reset, so it restores into a fresh DB as-is.

## Setup (fresh clone)

1. Set your DB password and start Postgres (compose defaults: user `admin`, db `mityahar_db`):
   ```bash
   # .env must contain POSTGRES_PASSWORD=<something>  (no default)
   docker compose up -d
   ```
2. Create the schema — `alembic` is the source of truth (not the stale `schema_only.sql`):
   ```bash
   python -m alembic upgrade head
   ```
3. Restore the content dump:
   ```bash
   # bash
   docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" -i mityahar_postgres \
     psql -U admin -d mityahar_db < db-backups/mityahar_content_2026-07-30.sql
   ```
   ```powershell
   # PowerShell
   Get-Content db-backups\mityahar_content_2026-07-30.sql | `
     docker exec -e PGPASSWORD=$env:POSTGRES_PASSWORD -i mityahar_postgres psql -U admin -d mityahar_db
   ```
4. Seed your own accounts (plain inserts, no API):
   ```bash
   python -m scripts.seed_admin
   python -m scripts.seed_test_doctor
   python -m scripts.seed_test_patients
   ```
5. Run the backend:
   ```bash
   python -m uvicorn app.main:app --port 8001 --host 0.0.0.0
   ```

## Do NOT run
- `scripts/seed_food_items.py` — broken (dropped `instructions` column).
- `scripts/seed_6k_recipes.py` — needs a USDA API key + ~6000 live calls. Superseded by the dump.

## Refreshing the dump (maintainers, after content changes)
```bash
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" mityahar_postgres pg_dump -h localhost -U admin \
  -d mityahar_db --data-only --no-owner \
  --table=public.food_items --table=public.ingredients \
  --table=public.recipe_ingredients --table=public.meal_templates \
  > db-backups/mityahar_content_<date>.sql
```
Then null `food_items.doctor_id` in the dump if any doctor-authored dishes exist, to keep it
PII-free and FK-clean.
