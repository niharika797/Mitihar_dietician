# Idempotent Plan Generation

*   **Author:** Ruchit
*   **Status:** Revised after EGM review (stages 5-9), awaiting approval
*   **Date:** 2026-10-26

--------------------------------------------------------------------------------

## Overview

`POST /api/v1/diet-plans/generate` builds a seven-day meal plan for the signed-in
patient. Today every call deletes the patient's active plan and builds a new one,
and the patient app calls it each time the Meals tab opens. This design makes the
endpoint return the existing plan while that plan is still valid, and build a new
one only when none exists or the existing one has expired.

Terms used in this document:

*   **Active plan**: the newest `recommendations` row for the patient with
    `is_active = true`. It may be a draft waiting for doctor approval.
*   **Valid**: the active plan's `week_start_date` is no more than 6 days before
    today (`today <= week_start_date + 6 days`), so the plan's seven days include
    today.
*   **Expired**: the active plan is not valid, has no `week_start_date`, or does
    not exist.

## The Problem

Each call costs 1.4 to 1.6 seconds of CPU and about 720 SQL statements, holds a
database connection for the whole call, and writes a new draft plan with about 252
`weekly_combos` rows that a doctor must approve. The API runs on one vCPU with a
database pool of 10 connections (the load rig used `DB_POOL_SIZE=5` and
`DB_MAX_OVERFLOW=5`), so ten simultaneous calls fill the pool and every other
request waits.

The app calls the endpoint once per Meals-tab mount
(`mitihar-patient-app/app/(tabs)/meals.tsx:367`, guarded by a per-mount flag). A
patient who opens the app three times a day opens the Meals tab about 1.5 times a
day, so each patient triggers about 1.5 regenerations a day. Measured on the
local load rig (1 vCPU API, pool of 10, source:
`docs/audits/capacity_2026-10/report.md`):

*   300 patients opening the app within 5 minutes: 1,442 failed requests, p95
    latency 31 seconds.
*   Steady 4.6 requests/s: p99 latency 2.3 seconds, API CPU 29% on average.
*   With a rig-only patch that returned any active plan without a window check:
    the same spike gave 0 failures and p95 42 ms; steady 4.6 requests/s gave p99
    140 ms and CPU 8%. The patch had no lock and no window check, so these are
    the best case, not a measurement of this design.

Returning any active plan is not a valid fix. Nothing else builds the next plan
when the seven days end; the Meals-tab call does. A patient would keep an expired
plan after day 7.

## Goals

*   A call made while the active plan is valid builds and stores nothing and
    returns the existing plan.
*   A call made when the active plan is expired builds one new plan, as the code
    does now.
*   Two simultaneous calls to this endpoint for one patient store at most one new
    plan.
*   On the load rig: 0 failures in the 300-patients-in-5-minutes spike with p95
    under 1 second; at 4.6 requests/s, p99 under 500 ms and average API CPU under
    15%.

## Non-Goals

*   Capping the regeneration that runs after a weight log, pre-generating next
    week's plans, fixing `weight_kg` versus `weight`.
*   Changing the plan generator, the recipe-pool checks, the 503 behaviour, or the
    doctor approval flow.
*   Changing the patient app. It keeps calling the endpoint and ignores the
    response body (`mitihar-patient-app/services/meals.ts:15-17` returns void;
    `meals.tsx:367-368` only refreshes the week-plan query).
*   Locking the other code paths that create plans (see Risks).

--------------------------------------------------------------------------------

## Technical Plan (Architecture)

```text
POST /diet-plans/generate
  1. take a transaction-scoped advisory lock keyed on the patient id
  2. read the newest active plan's week_start_date
  3. valid  -> return the existing plan (get_diet_plan), no writes
  4. expired -> current code: delete active plan, generate, store, return
```

**Lock.** Step 1 runs `pg_advisory_xact_lock(<patient id>)` as the first statement
after authentication. The lock ends when the transaction ends. `get_db`
(`app/core/database.py:49-67`) commits after the handler returns, and the login
dependency and the route share one session, so the lock is held until the new plan
is committed. A second simultaneous call waits for the lock, then reads the plan
the first call stored and returns it (the database default isolation level is READ
COMMITTED). If the first call ends in a 503, the exception path rolls back the
transaction: the soft-delete of the old plan is undone and the old plan stays.
Locks on the patient's row were rejected; see Alternatives.

**Window check.** Step 2 selects `Recommendation.week_start_date` for the newest
active plan (`created_at` descending, limit 1) directly in the router, and
compares it with `date.today()` in Python. `store_diet_plan`
(`app/services/diet_plan_service.py:105`) sets `week_start_date` to
`date.today()`, and the generator creates meal dates from that day through six
days later (`app/services/meal_generator/meal_generator.py:305`), so the window
matches the plan's own days. A missing date or a date in the future counts as
expired. `get_diet_plan` is left unchanged.

**Drafts.** A draft is an active plan. A patient whose plan awaits approval gets
that draft back instead of a second draft.

**Response.** A reused plan is returned through `get_diet_plan`, which builds the
`DietPlan` that `/diet-plans/my-plan` already returns. It has no `used_food_ids`
and no combos, and `meals` is an empty list for v2 plans. A freshly generated
plan returns more fields. This is accepted because the only known caller, the
patient app, ignores the body. Before implementing, confirm with
`grep -r "diet-plans/generate"` that only the patient app and dev scripts call the
endpoint, and that `DietPlanResponse` accepts the reused object.

**Decisions.**

*   Time zone: UTC (`date.today()` on the server). A plan is treated as valid for
    up to 5.5 hours after its seventh day ends in India. Accepted.
*   Doctor-edited plans: an expired window replaces them with a generated plan,
    as any Meals-tab open does now. This design makes that rarer.
*   Rate limit: the endpoint keeps `@limiter.limit("10/hour")` per client IP
    (`app/core/limiter.py`). Reused calls count against it. The load rig and
    tests must send a different client IP per patient, as the earlier audit rig
    did.

**Other plan-creating paths.** Profile update (`users.py:133-134`), weight log
(`progress.py:94-95`), doctor meal configuration (`doctor.py:2824-2825`) and
calorie adjustment (`meal_plan.py:121-122`) replace the active plan themselves,
so the endpoint needs no extra invalidation. Activation (`patients.py:51-54`) and
doctor acceptance (`doctor.py:450-453`) only generate when no plan exists. None
of these paths take the lock. If one fails, the old plan stays and remains valid
by date.

--------------------------------------------------------------------------------

## Alternatives Considered

### A: Remove the call from the app only
*   **Pros**: No server change; saves one request per Meals-tab open.
*   **Cons**: Needs an app release, old versions keep sending the expensive call,
    and the next plan is never built.
*   **Rejected**: leaves the cost in the server and breaks the weekly rollover.

### B: Return any active plan, no window check
*   **Pros**: Simplest; what the rig patch measured.
*   **Cons**: A patient keeps an expired plan after day 7.
*   **Rejected**: wrong behaviour after day 7.

### C: Row lock on the patient (`SELECT ... FOR UPDATE`)
*   **Pros**: Familiar syntax.
*   **Cons**: No precedent in the code (`with_for_update` is used only on
    `SubscriptionCode` rows, `patients.py:213`, `:234`). It blocks the patient's
    profile update, weight log and any insert that references the patient for up
    to 1.6 seconds.
*   **Rejected**: blocks other writers. The advisory lock blocks only this
    endpoint.

### D: Unique partial index on active plans
*   **Pros**: The database rejects a second active plan from any path.
*   **Cons**: A violation returns an error instead of the first plan, and it needs
    a migration and a duplicate cleanup.
*   **Rejected for now**: duplicates are harmless (see Risks). Use it if they ever
    cause a problem.

### E: Lock inside `store_diet_plan` or a shared `get_or_generate`
*   **Cons**: `store_diet_plan` runs after the 1.5-second generation, so it cannot
    stop duplicate generation, and a shared helper changes six callers for a race
    that already exists.
*   **Rejected**: more change than the problem needs.

--------------------------------------------------------------------------------

## Risks and Mitigations

*   **Waiting calls hold a pool connection.** Only calls for the same patient wait,
    and the rate limit is 10 an hour. Mitigation: none; add a lock timeout only if
    production metrics show lock waits.
*   **Thin recipe pool.** When generation fails validation the endpoint returns 503
    after three attempts (about 3.6 CPU-seconds) while holding the lock, and every
    Meals-tab open after expiry retries it. Mitigation: out of scope here; see the
    separate generate-fallback design.
*   **Duplicate active plans from other paths.** They do not take the lock, so a
    weight-log regeneration racing a generate call can leave two active plans. Both
    read paths pick the newest by `created_at`, so the patient sees one plan.
    Accepted; Alternative D is the fix if needed.
*   **Draft expiry.** A draft that is not approved within its seven days is
    replaced by a new draft, discarding doctor edits. A plan approved on day 6 has
    a one-day window. Accepted.
*   **Stale profile after waiting.** `current_user` is loaded before the lock wait.
    A second caller that waited may build a plan from a profile that changed in the
    meantime, but then the first caller's plan is valid and is returned instead.
    Accepted.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

### Files to modify

1.  **`app/routers/diet_plans.py`**, function `generate_diet_plan`, before the
    existing active-plan check:
    1.  Run `select(func.pg_advisory_xact_lock(current_user.id))` on the session.
    2.  Select the newest active `Recommendation.week_start_date` for the patient.
    3.  If it is set and `date.today() - week_start_date` is 0 to 6 days, log
        `reused plan for patient <id>` at info level with the module `logger` and
        return `get_diet_plan(...)`.
    4.  Otherwise continue with the existing code unchanged (its own
        `get_diet_plan` read and `delete_diet_plan` call stay; `store_diet_plan`
        also soft-deletes, so the delete is redundant but harmless).
    Add `from sqlalchemy import func, select` if they are not imported.
2.  **`tests/performance/benchmark_api.py`**: rename the row at line 140 to
    `Generate plan (reuse)` and change the docstring at lines 14-18, which says the
    endpoint "regenerates".
3.  **`docs/architecture/MEAL_GENERATION_FLOW.md`**: after the sentences at lines 12
    and 81 add: "A plan is reused while today is within 6 days of its
    `week_start_date`; otherwise a new plan is generated."

### Files to create

4.  **`tests/test_generate_idempotent.py`**, written like
    `tests/performance/test_fcm_race_real.py`: `asyncpg` for setup against the
    local database and `httpx.AsyncClient` against a running local server
    (`localhost:8001`). It is not added to CI, which has no database. Setup per
    test: create a patient, mint a JWT with a `sub_status` claim (otherwise
    `SubscriptionCheckMiddleware` returns 402), send a distinct
    `X-Forwarded-For` per request to stay under the rate limit, and delete the
    patient's rows at the end. Cases:
    1.  no plan: one plan is created;
    2.  valid plan: a second call returns it; plan id and `weekly_combos` count are
        unchanged;
    3.  expired plan (`UPDATE recommendations SET week_start_date = today - 8`): a
        new plan is stored and `version` goes up by one;
    4.  active draft plan (`approval_status = 'draft'`): reused;
    5.  `week_start_date` null: treated as expired, a new plan is stored;
    6.  two active plans, newest expired and older valid: a new plan is stored;
    7.  two simultaneous calls from two clients on an expired plan: exactly one new
        plan exists afterwards;
    8.  forced 503 (patch `diet_plan_service.generate_diet_plan` to raise): the old
        plan is still active afterwards.

### Verification

*   `ruff check app` and `mypy app` (the settings are in `pyproject.toml`;
    `ruff` gates CI, `mypy` does not).
*   `python -m tests.test_generate_idempotent` against a local server and database.
*   SQL count on the reuse path: with a `before_cursor_execute` counter, expect
    4 statements (patient lookup, advisory lock, `week_start_date`, plan read) plus
    the `get_db` `SELECT 1`. This is to be measured; the earlier figure of 3 came
    from the rig patch without the lock.
*   Load test, after rebuilding the rig from `docs/audits/capacity_2026-10/rig/`
    (`seed_perf.py`, then `reset_db.sh`, which checks table row counts against a
    saved snapshot, and `run_scenario.py`). Every run must start from a verified
    reset. Pass criteria, with distinct client IPs per patient:
    *   300 patients over 5 minutes and over 30 seconds: 0 failures, p95 under
        1 second;
    *   steady 4.6 requests/s: p99 under 500 ms, API CPU under 15%;
    *   steady 6.8 requests/s: 0 failures, p95 under 500 ms (informational).
    Repeat each run twice; the audit saw 62 to 95 requests/s run-to-run variation.

Process note: overwrite `CURRENT_STATE.md` at the end of the implementing session,
as the project working agreement requires.

--------------------------------------------------------------------------------

*Drafted with EGM; revised after review.*
