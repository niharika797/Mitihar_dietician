# Security review, 2026-10-28 (report only, no code changed)

Scope: the backend (`app/`), the patient app (`mitihar-patient-app/`), the doctor/admin dashboard (`mitihar-frontend/apps/`), and the Docker image. Done by reading code, running dependency checks, and comparing with published checklists. **This is a review, not a penetration test.** Nothing was attacked and nothing was changed. It cannot promise that no one can get in.

Not checked (needs GCP or a real test): Cloud Run ingress and IAM, Cloud Armor, Secret Manager rotation, backups and encryption settings, Redis TLS, live scanning of the staging URL, reverse-engineering the Android build. The earlier `SECURITY_AUDIT.md` (April) is still the record for its own fixes.

## What we checked against
- OWASP API Security Top 10 2023: broken object-level authorization, broken authentication, unrestricted resource consumption, security misconfiguration, improper inventory, and so on ([list](https://apisecurity.io/owasp-api-security-top-10/)).
- OWASP Mobile Top 10 2024 and MASVS 2.1: credential handling, insecure storage, insecure communication, binary protections, privacy controls ([summary](https://approov.io/blog/2024-owasp-mobile-top-ten-risks)).
- Login protection guidance: per-account lockout alone is weak against password spraying; add per-source limits, breached-password screening and MFA; lockout itself can be abused to lock out a victim ([OWASP testing guide](https://wstg.owasp.org/latest/4-Web_Application_Security_Testing/04-Authentication_Testing/03-Testing_for_Weak_Lock_Out_Mechanism)).
- Refresh tokens: rotation only helps with server-side state and reuse detection ([secondary sources](https://www.techinterview.org/post/3233468216/lld-token-refresh/)).
- Cloud Run: restrict ingress, least-privilege service accounts, Secret Manager, Cloud Armor for rate limits ([guide](https://www.accountablehq.com/post/google-cloud-run-healthcare-security-configuration-step-by-step-guide-and-hipaa-best-practices)).
- India's DPDP Rules 2025: reasonable security safeguards, breach report to the Board within 72 hours, logs kept at least a year; most obligations start about 18 months after the 14 Nov 2025 notification ([summary](https://www.scconline.com/blog/post/2025/12/26/digital-personal-data-protection-rules-2025-key-highlights/)).
- Caveat: most of these are summaries from vendor blogs, not the standards themselves. Check the official text before relying on a number.

## Fix before real patients
1. **Login and signup limits are per IP address only.** Patient login allows 5 tries per 15 minutes per IP, signup 3 per hour per IP. Mobile carriers and clinic Wi-Fi put many people behind one IP, so real patients will be blocked. A spread-out attacker is not slowed at all. Fix: limit per IP and per email together, keep a looser per-IP cap, add a breached-password check. (`app/routers/auth.py`, `app/core/limiter.py`)
2. **A stolen refresh token cannot be cancelled, and a password reset does not cancel it.** `/auth/refresh` never checks `password_changed_at`, so an old refresh token still mints fresh access tokens after a reset. Logout does not revoke it either, and it lives 7 days. Fix: store token ids (Redis or DB), rotate on every use, revoke the whole family if an old one is reused, and check the password-change time on refresh. (`app/routers/auth.py:544`) *From code reading; not exercised.*
3. **Dependencies with known problems.**
   - Both frontends ship `axios` with about 14 high advisories (fix: 1.16.0 or newer). The dashboard also has `react-router` (fix: 7.18.0 or newer) and `lodash` via recharts.
   - Patient app: 1 critical and 64 high in total, but the critical one (`shell-quote`) and the `xmldom` ones come in through build tools (Expo, devtools), not the shipped app.
   - Backend: 11 of 78 packages in `requirements.lock` have advisories (`anyio`, `certifi`, `cryptography`, `ecdsa`, `h2`, `mako`, `pillow`, `pyasn1`, `pyjwt`, `python-jose`, `urllib3`). I did not triage which apply.
   - `python-jose` 3.5.0: algorithm-confusion advisory (CVE-2024-33663). We only use HS256 with a fixed algorithm list, so it is probably not exploitable, but the library is poorly maintained. Plan a move to PyJWT.
4. **API documentation is public.** `FastAPI(...)` is created with default settings, so `/docs`, `/redoc` and `/openapi.json` list every endpoint in staging and production. Turn them off outside development.

## Fix soon
5. No `Strict-Transport-Security` (HSTS) header from the app. Add it, or confirm the load balancer sets it. The other headers (CSP, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy) are set.
6. Admin IP whitelist is disabled when the list is empty, and lets the request through if its own database lookup fails. For admin this should fail closed. (`app/core/middleware.py:238-303`)
7. Rate limiter fails open if Redis goes down (by design). Someone who can knock Redis over also turns off login limits. Consider failing closed on login and signup. Redis has a password but no encryption in transit.
8. Lockout can be used against a victim: anyone who knows an email can lock that account for 15 minutes, again and again. Pair lockout with the per-email limits in item 1 and tell the user by email.
9. Small information leaks: signup says "already registered" (409); doctor login says "locked" (423) for real accounts.
10. Cloud Run is publicly reachable (`allUsers`); the admin whitelist, cron secret and JWTs are the only gates. Put it behind a load balancer with Cloud Armor rate limits when GCP is available.
11. `/auth/refresh` has no rate limit.

## Phone app and privacy
- Native builds keep tokens in SecureStore (Android Keystore): good. The Expo **web** build uses `localStorage`: do not ship the web build to patients.
- No certificate pinning, no root or integrity check, no explicit `allowBackup` setting. Optional for a first release; worth adding for health data.
- Sentry is on with default settings (no extra personal data sent). Add a `beforeSend` scrubber before turning on session replay or breadcrumbs.
- Backend logs write patient emails (for example failed logins). Decide how long logs are kept; the DPDP Rules point to at least a year.
- DPDP readiness: a real erasure path (hard delete is off, and Google-signup patients are told to contact support), a written breach-notification process (72 hours), and consent records (a `gdpr_consent` flag exists).
- Docker container runs as root (no `USER` line). Low risk; easy to fix.

## Already good (verified in code or tests)
Passwords hashed with bcrypt. JWTs carry exp, iat, nbf; access and refresh are separate types; refresh cannot be used as access. `SECRET_KEY` must be 32+ characters and the default is refused. Doctor and admin refresh tokens are HttpOnly cookies, with a startup guard on `COOKIE_SECURE`. CORS lists explicit origins, no wildcard. SQL goes through the ORM, with no string-built queries found. The cron endpoints use a constant-time secret check. Secrets are git-ignored and untracked, and the image copies only `app/`, `alembic/`, `scripts/`. Google sign-in is checked on the server against our client ID. Forgot-password gives the same answer for any email. There are no file uploads and no fetching of user-supplied URLs, so the SSRF surface is small. Doctor and admin MFA exists. The security test suite (204 checks, including cross-doctor access tests) passes.
