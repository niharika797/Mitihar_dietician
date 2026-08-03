# SECRET_KEY Rotation Procedure

**Last updated:** 2026-07-03

---

## What SECRET_KEY Does

`SECRET_KEY` is the HS256 signing key for all JWTs (access + refresh tokens).  
It is read from `.env` / `.env.production` by `app/core/config.py` → `settings.SECRET_KEY`.  
Minimum length: 32 characters (enforced by `validate_secret_key` validator at startup).

---

## How to Generate a New Key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

This produces a 64-character hex string (256-bit entropy).

---

## Where to Update

| Environment | Location |
|---|---|
| Local dev | `.env` → `SECRET_KEY=<new-value>` |
| Production (Cloud Run) | GCP Secret Manager or Cloud Run env var override |
| Template | `.env.production` → update the placeholder |

---

## What Breaks on Rotation

**All active access tokens and refresh tokens are immediately invalidated.**

- Every logged-in user (patients, doctors, admins) will receive 401 on their next API call.
- Refresh token rotation will also fail — users must log in again.
- No data loss occurs. Only session state is affected.

### Impact Scope

- Patient mobile app: forced re-login on next API call.
- Doctor/Admin web dashboard: forced re-login.
- Cron endpoints: unaffected (use `X-Cron-Secret`, not JWT).

---

## Rotation Steps

### 1. Pre-rotation

- [ ] Choose a low-traffic window (e.g., 02:00–04:00 IST).
- [ ] Communicate to active users if possible (in-app banner or email).
- [ ] Ensure the new key is generated and ready.

### 2. Deploy New Key

```bash
# Cloud Run — update the secret
gcloud run services update mityahar-api \
  --update-env-vars SECRET_KEY=<new-64-char-hex>

# OR via Secret Manager (if using secret references)
echo -n "<new-64-char-hex>" | gcloud secrets versions add mityahar-secret-key --data-file=-
```

Cloud Run will restart instances with the new key. Old instances drain gracefully.

### 3. Post-rotation Verification

- [ ] Hit `GET /health` — confirm 200 (app started successfully with new key).
- [ ] Attempt login — confirm new JWT is issued and works.
- [ ] Confirm old tokens return 401.

---

## Rollback if Rotation Fails Mid-Deploy

If the new key causes startup failures (e.g., validation error, typo):

1. **Revert the env var** to the previous SECRET_KEY value:
   ```bash
   gcloud run services update mityahar-api \
     --update-env-vars SECRET_KEY=<old-key>
   ```
2. Cloud Run will roll back to serving with the old key.
3. Users who were logged in before rotation will still have valid sessions.
4. Any tokens issued during the brief window with the new key will become invalid — those users must log in again.

### If Both Old and New Keys Are Lost

- Generate a fresh key and deploy it. All users must re-login.
- No data is lost — only session state.

---

## Recommended Rotation Frequency

- **Mandatory rotation:** If key compromise is suspected.
- **Scheduled rotation:** Every 90 days is a reasonable cadence for a health-data application.
- **After team changes:** Rotate if any team member with key access leaves.
