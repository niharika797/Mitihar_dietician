# Current State

_Last updated: 2026-08-07 (later same day). Overwritten each session — no history here. Full narrative in docs/BUILD_TRACKER_ARCHIVE.md._

## Done this session
- Ran 4 isolated 1000-user load tests against staging to find the abort-condition-clearing config, changing one variable per run: Run 1 (1 worker/1 vCPU) failed p95; Run 2 (2 workers/2 vCPU) fixed Cloud Run but pegged Postgres CPU (55s p95>3s streak); Run 3 (1 worker/2 vCPU) proved worker count, not vCPU, relieves Cloud Run (272s streak, worst of all); Run 4 (2 workers/2 vCPU + Postgres bumped to `db-custom-4-15360`) cleared **both** abort conditions (0.0088% sustained error rate, ~4s p95>3s streak vs the 30s threshold).
- Enabled `pg_stat_statements` on staging (no restart needed — confirmed empirically) and identified `/meal-plan/week`'s `selectinload` combo-materialization query as ~77% of top-5 query total time — the dominant cost driver, not evenly spread.
- Working config candidate: Cloud Run 2 workers/2 vCPU, `DB_POOL_SIZE=12`/`DB_MAX_OVERFLOW=7`, Postgres `db-custom-4-15360`.

## Blockers / pending
- Known coverage gap: pre-minted tokens skip `POST /auth/token` and `POST /auth/refresh` entirely, unlike real client traffic.
- `/meal-plan/week`'s selectinload cost concentration is now confirmed but not yet addressed — no fix applied this session.

## Next action
PR opened `feature/api-remediation-v0.2` → `main` (not merged) with the Run 4 config as the recommended baseline. Await review/merge decision.
