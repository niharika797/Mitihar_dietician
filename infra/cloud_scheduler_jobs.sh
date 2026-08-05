#!/usr/bin/env bash
#
# TODO(deploy): NOT APPLIED. These three Cloud Scheduler jobs do not exist in
# GCP yet. The /internal/cron/* endpoints are live, tested, and idempotent, but
# nothing calls them in production until someone runs this file by hand.
#
# Run manually after a staging/prod deploy:
#     bash infra/cloud_scheduler_jobs.sh
#
# Re-running is safe to the extent that `jobs create` fails on an existing job
# (ALREADY_EXISTS); use `gcloud scheduler jobs update http <name>` to change a
# schedule instead of deleting and recreating.
#
# ─── Auth caveat — read before running ──────────────────────────────────────
# These endpoints authenticate with a shared secret in the X-Cron-Secret header
# (app/routers/internal.py:20, constant-time compare against settings.CRON_SECRET).
# Cloud Scheduler cannot resolve a header value from Secret Manager at delivery
# time, so CRON_SECRET is read from your shell below and stored *in the job
# config*, readable by anyone with roles/cloudscheduler.viewer on the project.
#
# The stronger alternative is OIDC (--oidc-service-account-email), which needs
# no shared secret — but it would require changing the endpoints' auth from a
# header check to token verification. That is a deliberate design change and is
# NOT made here.
# ────────────────────────────────────────────────────────────────────────────

set -euo pipefail

PROJECT="mityahar-staging"
REGION="asia-south1"
BASE_URL="https://mityahar-api-759811872653.asia-south1.run.app"
SA="mityahar-scheduler-sa@mityahar-staging.iam.gserviceaccount.com"
TZ="Asia/Kolkata"

if [[ -z "${CRON_SECRET:-}" ]]; then
    echo "ERROR: CRON_SECRET is not set in the environment." >&2
    echo "Fetch it first:" >&2
    echo "  export CRON_SECRET=\$(gcloud secrets versions access latest --secret=CRON_SECRET --project=$PROJECT)" >&2
    exit 1
fi

create_cron_job() {
    local name="$1" path="$2" schedule="$3" description="$4"
    echo "Creating $name ($schedule $TZ) -> $path"
    gcloud scheduler jobs create http "$name" \
        --project="$PROJECT" \
        --location="$REGION" \
        --schedule="$schedule" \
        --time-zone="$TZ" \
        --uri="${BASE_URL}${path}" \
        --http-method=POST \
        --update-headers="X-Cron-Secret=${CRON_SECRET}" \
        --oauth-service-account-email="$SA" \
        --attempt-deadline=300s \
        --max-retry-attempts=3 \
        --min-backoff=30s \
        --description="$description"
}

# Flag patients whose token_1_expiry falls within 4 days (expiring_soon=True) and
# push an FCM warning. Idempotent: WHERE expiring_soon=False means a re-run is a
# no-op. Morning slot so the push lands at a reasonable local hour.
create_cron_job \
    "mityahar-flag-expiring" \
    "/internal/cron/flag-expiring-patients" \
    "0 9 * * *" \
    "Daily 09:00 IST - flag patients expiring within 4 days + FCM push"

# Deactivate patients whose token_1_expiry has already passed. Runs just after
# midnight so a subscription expires on the correct calendar day.
create_cron_job \
    "mityahar-deactivate-expired" \
    "/internal/cron/deactivate-expired-patients" \
    "30 0 * * *" \
    "Daily 00:30 IST - deactivate patients past token_1_expiry"

# Snapshot weekly summaries for the week that just ended.
# MUST run on a Monday: internal.py:134 computes
#   last_monday = today - (today.weekday() + 7)
# so a Monday run targets the Mon-Sun week that just closed. Running this on any
# other weekday still resolves to a *previous* Monday and would silently snapshot
# the wrong week.
create_cron_job \
    "mityahar-complete-plans" \
    "/internal/cron/complete-expired-plans" \
    "0 1 * * 1" \
    "Mondays 01:00 IST - snapshot weekly summaries for the week that just ended"

echo
echo "Done. Verify with:"
echo "  gcloud scheduler jobs list --project=$PROJECT --location=$REGION"
echo "Trigger one immediately to smoke-test:"
echo "  gcloud scheduler jobs run mityahar-flag-expiring --project=$PROJECT --location=$REGION"
