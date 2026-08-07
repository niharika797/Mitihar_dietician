#!/usr/bin/env bash
#
# RECONCILED (2026-08-06): job names, timezone, and schedules below now match
# the 3 ENABLED jobs live in mityahar-staging exactly (previously this script
# used different names/timezone — see CLAUDE.md "Cron endpoints" section for
# history). Re-running this script now correctly hits ALREADY_EXISTS on all
# three; use `gcloud scheduler jobs update http <name>` to change a schedule
# instead of deleting and recreating.
#
# Run manually after a staging/prod deploy:
#     bash infra/cloud_scheduler_jobs.sh
#
# ─── Auth caveat — read before running ──────────────────────────────────────
# These endpoints authenticate with a shared secret in the X-Cron-Secret header
# (app/routers/internal.py:20, constant-time compare against settings.CRON_SECRET).
# Cloud Scheduler cannot resolve a header value from Secret Manager at delivery
# time, so CRON_SECRET is read from your shell below and stored *in the job
# config*, readable by anyone with roles/cloudscheduler.viewer on the project.
#
# The live jobs also carry an OIDC identity token (--oidc-service-account-email
# below) as belt-and-suspenders, but it adds no real protection here: the Cloud
# Run service's ingress is allUsers/public (roles/run.invoker), so IAM never
# rejects an unauthenticated call — the X-Cron-Secret header is the only actual
# gate. Tightening this (removing allUsers, relying on OIDC alone) is a
# deliberate design change and is NOT made here.
# ────────────────────────────────────────────────────────────────────────────

set -euo pipefail

PROJECT="mityahar-staging"
REGION="asia-south1"
BASE_URL="https://mityahar-api-759811872653.asia-south1.run.app"
SA="mityahar-scheduler-sa@mityahar-staging.iam.gserviceaccount.com"
TZ="Etc/UTC"

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
        --oidc-service-account-email="$SA" \
        --attempt-deadline=300s \
        --max-retry-attempts=3 \
        --min-backoff=30s \
        --description="$description"
}

# Flag patients whose token_1_expiry falls within 4 days (expiring_soon=True) and
# push an FCM warning. Idempotent: WHERE expiring_soon=False means a re-run is a
# no-op.
create_cron_job \
    "flag-expiring-patients" \
    "/internal/cron/flag-expiring-patients" \
    "0 1 * * *" \
    "Daily 01:00 UTC - flag patients expiring within 4 days + FCM push"

# Deactivate patients whose token_1_expiry has already passed.
create_cron_job \
    "deactivate-expired-patients" \
    "/internal/cron/deactivate-expired-patients" \
    "5 1 * * *" \
    "Daily 01:05 UTC - deactivate patients past token_1_expiry"

# Snapshot weekly summaries for the week that just ended.
# MUST run on a Monday: internal.py:141 computes
#   last_monday = today - (today.weekday() + 7)
# so a Monday run targets the Mon-Sun week that just closed. Running this on any
# other weekday still resolves to a *previous* Monday and would silently snapshot
# the wrong week. (Live job fired on Sundays until 2026-08-06 — fixed via
# `gcloud scheduler jobs update`; this script now matches the corrected value.)
create_cron_job \
    "complete-expired-plans" \
    "/internal/cron/complete-expired-plans" \
    "0 1 * * 1" \
    "Mondays 01:00 UTC - snapshot weekly summaries for the week that just ended"

echo
echo "Done. Verify with:"
echo "  gcloud scheduler jobs list --project=$PROJECT --location=$REGION"
echo "Trigger one immediately to smoke-test:"
echo "  gcloud scheduler jobs run flag-expiring-patients --project=$PROJECT --location=$REGION"
