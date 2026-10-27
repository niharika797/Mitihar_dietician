# Quick check after the weight fix (2026-10-28)

Same rig as the main report: API 1 vCPU, Postgres 2 vCPU, no Redis, 1,000 synthetic patients, current code.

| Scenario | Before the fix | After the fix |
|---|---|---|
| Weight burst: 100 first-time weight logs in 60 s + 50 browsing users | `PUT /progress/log/weight` p50 13,000 ms, p95 30,000 ms, 9 failures (37 failures overall) | p50 11 ms, p95 24 ms, 0 failures |
| Steady ~10 requests/s, 5 min | p50 33 ms, p95 120 ms, 0 failures | p50 28 ms, p95 110 ms, 0 failures |

- Weight burst after the fix: 1,909 requests, 0 failures, API CPU avg 12%, Postgres CPU avg 4%.
- Steady run after the fix: 3,375 requests (same count as before), 0 failures, API CPU avg 10.5%, nothing saturated.
- Profile edit (local dev DB): height or activity change takes 0.01-0.02 s and creates no plan. A region change still regenerates a plan (2.13 s), on purpose.

Test setup: for the weight burst the rig sets `PERF_WEIGHT_AGED=1` in `rig/reset_db.sh`. That backdates signups by 40 days and clears stored weights, so the 28-day rule lets each patient's first log through. Without it almost every call would get a 409.

Not covered: the full 6-scenario retest. It waits until the remaining fixes are done.
