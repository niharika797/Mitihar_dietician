# Plan: the four "fix before real patients" items

Source: `SECURITY_REVIEW_2026-10-28.md`. **Nothing here is built yet; waiting for the go.** Order is easiest and safest first, one commit each, all on `feature/api-remediation-v0.2`.

## 1. Turn off `/docs`, `/redoc`, `/openapi.json` outside development: **DEFERRED to deployment (user decision 2026-10-28)**
- Stays as is for now. Do this before the first real deployment; it is also listed in `TOMORROW_TASKS.md` section 4b.
- How, when the time comes: `app/main.py:86`: pass `docs_url=None, redoc_url=None, openapi_url=None` unless `settings.ENVIRONMENT == "development"`.
- I searched the backend, tests, scripts, infra and both frontends: nothing uses these URLs.
- Test: with `ENVIRONMENT=staging`, all three return 404; with `development` they return 200.

## 2. Upgrade packages
- Patient app and dashboard: `axios` to 1.16.0 or newer. Dashboard also: `react-router` to 7.18.0 or newer, and `lodash` (comes in through `recharts`).
- Patient app build-tool findings (`shell-quote` critical, `xmldom` high): add pnpm `overrides` to the fixed versions. These only run on the build machine, not in the shipped app. Optional; say if you want it left out.
- Check after: `pnpm audit --prod` again, dashboard `pnpm build`, patient app type check (same errors as before, no new ones), the headless login/tab smoke test.
- Not in this item: the 11 backend packages with advisories. They need sorting first (which actually apply). I'd do that as the next step.

## 3. Login and signup limits per IP **and** per email
- Today: login 5 per 15 min per IP, signup 3 per hour per IP. Shared mobile and clinic IPs get blocked.
- Change:
  - Per IP, looser: login 30 per 15 min, signup 20 per hour.
  - Per email, new: login 10 failed-or-successful tries per 15 min, signup 3 per hour. Counted in the same store as the current limiter (memory or Redis), inside the handler, because the email is in the request body.
  - Keep the existing account lockout (10 wrong passwords = 15 min). Per-email limits stop the repeat locking of one victim, and lockout stays as the last guard.
- Same rule for doctor and admin login (they are at 10 per minute per IP).
- **Friendly message when a limit is hit (user request):** the server's 429 answer becomes `{"detail": "<message>", "retry_after_seconds": N}` plus a `Retry-After` header, instead of slowapi's bare "Rate limit exceeded: 5 per 15 minute". The patient app shows a pop-up (and the dashboard login shows the same text) in a professional tone, for example: "Too many attempts. For your security, we have paused sign-in for a short while. Please take a break and try again in about 12 minutes." The minutes come from `retry_after_seconds`, rounded up. The same pop-up covers signup and the other limited actions (forgot-password, resend email).
- Tests: 11th try on one email is refused even from different IPs; 30 different emails from one IP all get through; limit resets after the window; the 429 answer carries the message and a sensible wait time.

## 4. Refresh tokens: rotate on every use, detect reuse, cancel on reset and logout
- **Where to keep the records: a new database table `refresh_tokens`** (id, token id, family id, user role and id, issued, expires, used_at, revoked_at). One Alembic migration, then a nightly cleanup in the existing prune cron. Chosen over Redis because it still works when Redis is down or absent (the "Standard" shape), and it survives restarts.
- Flow:
  - Login makes a token id and family id and stores a row.
  - `/auth/refresh`: unknown or revoked token = 401. Already-used token = someone has a copy, so revoke the whole family and return 401. Otherwise mark used and issue a new token in the same family.
  - Also check on refresh: user still active, and (patients) token issued after `password_changed_at`.
  - Password reset revokes all of that patient's families. New `POST /auth/logout` for patients revokes theirs; the app calls it on logout. Doctor and admin logout already exists and gets the same revoke.
- **10 second grace** for a token used twice at the same moment (two browser tabs, a retry). The second call gets a new access token only and the family is not revoked. After 10 s, reuse revokes the family.
- Old tokens without a token id (issued before the deploy): accepted once, if issued after the last password change, then replaced with a tracked one. Remove this after 7 days.
- Doctors and admins have no password-change time or change-password endpoint today, so for them reset-revocation does not apply yet. Noted, not built.
- Tests (added to the security suite): old token fails after use; reuse revokes the family and the newest token stops working; reset-password kills refresh; logout kills refresh; grace window; legacy token upgraded once; expired and revoked rows are cleaned up.
- Patient app: logout also calls the new endpoint. The existing refresh queue already stops the app from sending two refreshes at once.

## Decisions I need from you (my pick first)
1. Store refresh records in **the database** (pick) or Redis.
2. On reuse detected after the grace: **sign that user out everywhere** (pick) or just reject that one call.
3. Limits as above (30 per IP, 10 per email) or different numbers.
4. Include the build-tool overrides in item 2? (pick: yes)

## Not covered / needs GCP
- Applying the new table to staging needs the `mityahar-migrate` Cloud Run job, so it waits for GCP. Local dev and the rig DB get it now.
- Existing patients' stored sessions: after the deploy, everyone's app keeps working (legacy rule above), no forced logout.
- Time: roughly 3 to 4 hours of work including tests; items 1 and 2 first (under an hour).
