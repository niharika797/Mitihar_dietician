"""
Pre-mint access tokens for the load-test accounts and publish them to GCS.

Why pre-auth: the locustfile already caches one token per virtual user for that
user's whole lifetime, so logins only ever happen during ramp-up. But ramping to
1000 users means ~1000 logins in ~50s, and auth.py:242 rate-limits
POST /auth/token to 5 per 15 minutes. The locustfile spoofs a per-user
X-Forwarded-For to spread that across fake IPs, which works locally but is inert
behind GCLB — the real client IP wins, so every VU keys to one address and the
ramp mostly 429s. Minting out-of-band removes the burst entirely.

Tokens are built with the same helpers the login endpoints use
(_patient_token_data / _doctor_token_data shape + create_access_token), so they
are indistinguishable from real login output. This must run inside a Cloud Run
job because it needs to sign with staging's SECRET_KEY.

KNOWN COVERAGE GAP, state it in the results: a run using these tokens exercises
neither POST /auth/token nor POST /auth/refresh. Real clients hold a 15-minute
access token and let the axios interceptor refresh silently, so refresh traffic
exists in production and is absent here. Everything downstream of the
Authorization header is unaffected.

Run as a Cloud Run job (staging):
    --command python --args -m,scripts.mint_load_test_tokens
"""

import argparse
import asyncio
import json
import sys
from datetime import timedelta

from dotenv import load_dotenv
from sqlalchemy import select

load_dotenv()

from app.core.security import create_access_token  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models.db_models import Doctor, Patient  # noqa: E402

EMAIL_PREFIX = "loadtest%"
DEFAULT_BUCKET = "mityahar-staging-test-artifacts"
DEFAULT_OBJECT = "load-test/tokens.json"


async def main() -> int:
    ap = argparse.ArgumentParser()
    # Default 60m, not the app's 15m: the run plus ramp must finish well inside
    # the window, and nothing in the locustfile re-authenticates on a 401 — an
    # expiry mid-run would show up as a silent wall of auth failures that looks
    # like a capacity problem.
    ap.add_argument("--expire-minutes", type=int, default=60)
    ap.add_argument("--gcs-bucket", default=DEFAULT_BUCKET)
    ap.add_argument("--gcs-path", default=DEFAULT_OBJECT)
    ap.add_argument("--no-gcs", action="store_true")
    args = ap.parse_args()

    ttl = timedelta(minutes=args.expire_minutes)

    async with AsyncSessionLocal() as session:
        patients = (await session.execute(
            select(Patient).where(Patient.email.like(EMAIL_PREFIX)).order_by(Patient.id)
        )).scalars().all()
        doctors = (await session.execute(
            select(Doctor).where(Doctor.email.like(EMAIL_PREFIX)).order_by(Doctor.id)
        )).scalars().all()

        payload = {
            "expire_minutes": args.expire_minutes,
            "patients": [
                {
                    "email": p.email,
                    "patient_id": p.id,
                    "doctor_id": p.doctor_id,
                    "token": create_access_token({
                        "sub": p.email,
                        "role": "patient",
                        "user_type": p.user_type or "standalone",
                        "sub_status": p.subscription_status or "inactive",
                        "patient_id": p.id,
                    }, expires_delta=ttl),
                }
                for p in patients
            ],
            "doctors": [
                {
                    "email": d.email,
                    "doctor_id": d.id,
                    "token": create_access_token({
                        "sub": d.email,
                        "name": d.name,
                        "role": "doctor",
                        "user_type": "doctor",
                        "doctor_id": d.id,
                    }, expires_delta=ttl),
                }
                for d in doctors
            ],
        }

    print(f"minted patients={len(payload['patients'])} doctors={len(payload['doctors'])} "
          f"ttl={args.expire_minutes}m", flush=True)

    if payload["patients"]:
        print(f"sample patient token len={len(payload['patients'][0]['token'])}", flush=True)

    if args.no_gcs:
        print(json.dumps({k: v for k, v in payload.items() if k != "patients"})[:400])
    else:
        from google.cloud import storage
        blob = storage.Client().bucket(args.gcs_bucket).blob(args.gcs_path)
        blob.upload_from_string(json.dumps(payload), content_type="application/json")
        print(f"tokens -> gs://{args.gcs_bucket}/{args.gcs_path}", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
