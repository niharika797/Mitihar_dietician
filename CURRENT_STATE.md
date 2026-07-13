# Current State

_Last updated: 2026-07-03. Overwritten each session — no history here. Full narrative in BUILD_TRACKER_ARCHIVE.md._

## Done this session (2026-07-03)

- `ENVIRONMENT=development|staging|production` explicit flag replaces fragile hostname heuristic (`app/core/config.py` + `app/main.py`)
- Weight log `_handle_weight_change` converted to `asyncio.create_task` background task — Gemini regen no longer blocks the HTTP response
- `REQUIRE_EMAIL_VERIFICATION` production startup warning added to `app/main.py` lifespan
- Dedup non-determinism fixed in `POST /doctor/recipes` — `ORDER BY id DESC` added; pre/post-cleanup added to `full_backend_test.py` Section 12
- `DEPLOY_CHECKLIST.md` expanded with APScheduler resolution and "Must flip before public launch" section
- `full_backend_test.py`: 98/98 ✅

## Blockers / pending

- GCP Cloud Run not yet deployed; `gcloud` CLI not installed locally
- EAS build placeholders unset (`EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_SENTRY_DSN`, `EXPO_PUBLIC_GOOGLE_CLIENT_ID`)

## Next action

GCP deployment phase — Cloud Run + Cloud SQL + Memorystore + Scheduler jobs.  
**Critical:** `ENVIRONMENT=production` must be injected explicitly as a Cloud Run env var (not defaulted).
