# Mitihar — Open Questions Resolution Report

Date: 2026-05-01  
Auditor: Claude Code — read-only  
Source: Docker PostgreSQL (`mityahar_postgres`, port 5432) + `.env` + `app/` source inspection  
Container confirmed: `docker ps` shows `mityahar_postgres` (Up, port 5432)  
DB credentials: user=`admin`, db=`mityahar_db` (from `.env` line 4)

---

## Q1 — Muskmelon Smoothie in `food_items`

**Query run:**
```sql
SELECT id, recipe_name, cal_per_serving, protein_per_serving, fat_per_serving, fiber_per_serving, carbs_per_serving
FROM food_items WHERE recipe_name ILIKE '%muskmelon%';
```
**Result:** `(0 rows)`

**Zero-calorie safety check:**
```sql
SELECT id, recipe_name, cal_per_serving FROM food_items
WHERE cal_per_serving = 0 OR cal_per_serving IS NULL;
```
**Result:** `(0 rows)`

**Context:** The original finding (audit obs 535) flagged muskmelon smoothie data quality in the markdown files at `app/graphify-out/`. Per `CLAUDE.md`, the `MealGenerator` queries PostgreSQL exclusively — it does not read from those markdown files. The markdown files appear to be reference/documentation artifacts used during the data import phase.

**Verdict: ✅ Safe**  
No muskmelon smoothie record exists in the live `food_items` table. No zero-calorie or null-calorie items exist. The markdown data quality issue is inert with respect to the live meal generator.

**Bonus observation — unverified recipe ratio:**  
```sql
SELECT COUNT(*) total, COUNT(*) FILTER (WHERE is_verified = true) verified
FROM food_items;
-- Result: total=2141, verified=197
```
92% of the recipe pool (1,944 of 2,141 items) is `is_verified = false`. Grep of `app/services/meal_generator/meal_generator.py` found no filter on `is_verified`, meaning unverified recipes are eligible for all generated meal plans. This is not a breaking bug but means nutritional accuracy relies on the quality of unverified seed data.

---

## Q2 — Gemini Model Availability

**Finding:** The codebase uses **two different Gemini models** in two distinct endpoints:

| Location | Model | Endpoint purpose |
|----------|-------|-----------------|
| `app/routers/doctor.py:1106` | `gemini-2.0-flash` | Nutrition estimation fallback for custom dish lookup |
| `app/routers/doctor.py:1660` | `gemini-2.5-flash-lite` | Food name → macros estimation for doctor recipe builder |

**Live tests (GEMINI_API_KEY_1 from `.env`):**

| Model | HTTP status | Interpretation |
|-------|-------------|----------------|
| `gemini-2.0-flash` | **429** | Rate-limited — model exists and is accessible |
| `gemini-2.5-flash-lite` | **200** | Alive and responding |

**API keys:** `GEMINI_API_KEY_1` through `_4` all set in `.env`. `config.py` maps only `GEMINI_API_KEY_1`–`4` as `Optional[str]`; the `doctor.py:1080` path uses only `settings.GEMINI_API_KEY_1`, while `doctor.py:1652` uses a `_key_cycle` iterator over all four keys.

**Verdict: ✅ Both models alive**  
`gemini-2.5-flash-lite` is confirmed working. `gemini-2.0-flash` returns 429 (rate limit), confirming the model endpoint exists and is reachable. Note: `CLAUDE.md` references `gemini-2.0-flash-lite` as the retired model (March 2026), not `gemini-2.0-flash`. The `gemini-2.0-flash` at line 1106 is the standard (non-lite) variant and appears to remain available.

---

## Q3 — Firebase Credentials

**`.env` entry:**
```
FIREBASE_SERVICE_ACCOUNT_PATH=./firebase_service_account.json
```

**File existence check:**
```
ls -la ./firebase_service_account.json
-rw-r--r-- 1 Lenovo 197121 2376 Apr  4 21:35 firebase_service_account.json
```

**Result:** File exists, size 2,376 bytes (consistent with a Google service account JSON), last modified April 4, 2026. File is readable.

**Startup behavior** (`app/main.py:136`): `init_firebase()` is called in the lifespan context. If the file is missing, Firebase Admin SDK init fails silently (notifications disabled without crashing the server). In this environment, the file is present.

**Verdict: ✅ Credentials present**  
`firebase_service_account.json` exists and is readable. Push notifications are enabled in this environment.

---

## Q4 — MealTemplate Table Population

**Count query:**
```sql
SELECT COUNT(*) AS total_templates FROM meal_templates;
-- Result: 180
```

**Breakdown:**
```sql
SELECT meal_time, diet_type, plan_type, COUNT(*) AS count
FROM meal_templates
GROUP BY meal_time, diet_type, plan_type
ORDER BY meal_time, diet_type;
```

**Result:** 45 rows, each with `count = 4`

**Coverage matrix:**

| Dimension | Values present |
|-----------|----------------|
| `meal_time` (5) | Breakfast, Dinner, Evening_Snack, Lunch, Morning_Snack |
| `diet_type` (3) | Eggetarian, Non-Vegetarian, Vegetarian |
| `plan_type` (3) | Diabetic-Friendly, Gym-Friendly, Healthy |
| `region` (4) | East, North, South, West |

**Total:** 5 × 3 × 3 × 4 = **180** — matches row count exactly.

The unique constraint `uq_template` on `(meal_time, region, diet_type, plan_type)` enforces one template per combination, and the count confirms all 180 combinations are populated with no duplicates and no gaps.

**Verdict: ✅ Fully seeded**  
All meal times, diet types, plan types, and regions are covered. The meal generator will never encounter a missing template for a valid patient profile combination.

---

## Q5 — Admin IP Whitelist

**Query:**
```sql
SELECT id, name, email, allowed_ips, mfa_enabled FROM admins;
```

**Result:**

| id | name | email | allowed_ips | mfa_enabled |
|----|------|-------|-------------|-------------|
| 1 | Super Admin | admin@mityahar.com | `[]` | `false` |
| 2 | Mitihar Admin | admin@mitihar.test | `[]` | `false` |

**Middleware behavior** (`app/core/middleware.py:226`):
```
# If allowed_ips is empty or None, whitelisting is disabled
if not allowed_ips:
    # pass through — any IP allowed
```
The code comment at line 226 explicitly documents: *"If allowed_ips is empty list [], IP whitelisting is DISABLED (any IP allowed)."*

**Impact on R-1:** The original R-1 (Critical) finding documented that `AdminIPWhitelistMiddleware` fails **open on DB error**. This Q5 finding reveals a second, independent path to the same outcome: even when the DB is fully operational, both admins have `allowed_ips = []`, so the IP check is a no-op in normal operation. The R-1 risk is therefore broader than originally characterized:

- **Path A (R-1 original):** DB unreachable → middleware passes request through
- **Path B (Q5 new):** `allowed_ips = []` → middleware passes request through

Both paths are currently active. Admin routes have no effective IP-based access control in this environment.

Additionally: `mfa_enabled = false` for both admins. TOTP-based MFA (`app/services/mfa_service.py`) is implemented but not activated for any admin account.

**Verdict: ⚠️ IP filtering disabled — upgrades R-1**  
Both admins have empty IP lists. This is not a middleware bug but a configuration gap: the capability exists but has not been configured. Recommend setting `allowed_ips` to the expected admin IP ranges and enabling MFA for both accounts before production deployment.

---

## Q6 — COOKIE_SECURE

**`.env` line 15:**
```
COOKIE_SECURE=False
```

**`app/core/config.py:21`:**
```python
COOKIE_SECURE: bool = False  # default
```
The `.env` value matches the code default. No env override is applied.

**Startup guard** (`app/main.py:122–134`):
```python
if not settings.COOKIE_SECURE:
    is_local = hostname in ("localhost", "127.0.0.1") \
        or hostname.startswith("DESKTOP-") \
        or hostname.endswith(".local")
    if not is_local:
        _log.critical("SECURITY WARNING: COOKIE_SECURE=False on a non-localhost host...")
```
The guard only emits a `CRITICAL` log when the hostname does NOT match `localhost`, `127.0.0.1`, `DESKTOP-*`, or `*.local`. On a dev machine with a `DESKTOP-*` hostname (standard Windows naming), the warning is suppressed even if the server is network-accessible on a LAN IP.

**Risk:** If the server is deployed on a cloud VM or container with a non-desktop hostname while still pointing at an HTTP origin, the guard will fire. However, if a developer runs it on a `DESKTOP-*` machine and exposes it via ngrok or a reverse proxy, the warning is silently skipped.

**Verdict: 🔴 Insecure in production**  
`COOKIE_SECURE=False` is expected and documented for local dev. However:
1. It must be explicitly set to `True` in any production `.env` — there is no automatic promotion.
2. The startup guard has a blind spot: `DESKTOP-*` hostnames are treated as local regardless of actual network exposure.

---

## Risk Register Updates

| Question | Risk ID | Change |
|----------|---------|--------|
| Q1 | — | No new risk. Muskmelon issue is inert (markdown-only, not in live DB). |
| Q2 | — | No new risk. Both models alive. Note: `doctor.py:1106` uses `gemini-2.0-flash` while `doctor.py:1660` uses `gemini-2.5-flash-lite` — two different model versions coexist. |
| Q3 | — | Closes uncertainty. Firebase credentials present. |
| Q4 | — | Closes uncertainty. `meal_templates` fully seeded. Bonus: 92% of `food_items` is unverified; meal generator does not filter by `is_verified`. Consider flagging as low-severity info item. |
| Q5 | **R-1 (upgrade)** | R-1 was "fail-open on DB error." Q5 reveals the same outcome in normal operation: `allowed_ips = []` disables IP filtering even when DB is healthy. R-1 should be re-described as "AdminIPWhitelistMiddleware provides no effective IP control — both fail-open on DB error AND both admins have empty IP lists." MFA also disabled for both admins. |
| Q6 | R-3 (existing) | Confirms R-3 (`COOKIE_SECURE=False`). No change in severity. Startup guard partially mitigates production risk but has a `DESKTOP-*` blind spot. |

---

## Recommended Actions (read-only audit — no changes made)

1. **R-1 (Critical — now broader):** Set `allowed_ips` to a known IP range for both admin accounts. Enable `mfa_enabled = true` for both admins. The middleware capability is fully implemented; it just needs to be turned on.
2. **`is_verified` observation:** Consider adding `FoodItem.is_verified == True` to the `MealGenerator` query to exclude unverified recipes from generated plans, or implement a periodic verification workflow.
3. **Q2 model drift:** `doctor.py:1106` uses `gemini-2.0-flash`; the rest of the project documents `gemini-2.5-flash-lite`. Both are alive today, but consolidating to a single model reduces future maintenance surface.
4. **COOKIE_SECURE:** Add deployment checklist step to verify `COOKIE_SECURE=True` before any cloud deployment. The `DESKTOP-*` exception in the startup guard may mask the warning in CI environments.
