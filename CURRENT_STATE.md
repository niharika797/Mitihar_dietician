# Current State

_Last updated: 2026-08-06. Overwritten each session — no history here. Full narrative in docs/BUILD_TRACKER_ARCHIVE.md._

## Done this session
- Removed dead `GOOGLE_REDIRECT_URI` config (`app/core/config.py`, `CLAUDE.md`); kept `GOOGLE_CLIENT_SECRET` since `scripts/audit_google_oauth.py` checks it via `hasattr()`.
- Deleted unused `app/crud/__init__.py` and stale Mongo-based `tools/tester.py` (695 lines).
- Reconciled `infra/cloud_scheduler_jobs.sh` with the 3 live staging jobs — renamed jobs to match (`flag-expiring-patients`/`deactivate-expired-patients`/`complete-expired-plans`), `TZ`→`Etc/UTC`, `--oauth-service-account-email`→`--oidc-service-account-email`; script now hits `ALREADY_EXISTS` instead of double-firing. Updated `app/routers/internal.py` comments to match (jobs deployed, names diverge from script).
- Applied the `complete-expired-plans` Sunday→Monday fix via `gcloud scheduler jobs update` (`0 1 * * 1`, `Etc/UTC`); documented that the `X-Cron-Secret` header, not OIDC, is the real gate (Cloud Run ingress is `allUsers`).

## Blockers / pending
- `PendingVisitSection.tsx` (patient app) never run in an emulator — typechecks only.
- **Pre-existing, untouched:** `approve-renewal` 500s for any patient with NULL `token_1`.

## Next action
Confirm the live `complete-expired-plans` job shows the updated Monday/`Etc/UTC` schedule (`gcloud scheduler jobs describe`), then exercise `PendingVisitSection.tsx` in an emulator.
