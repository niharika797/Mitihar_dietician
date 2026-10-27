# Retest after the security fixes, with Redis

Run 2026-10-28 on the local Docker rig. API 1 CPU / 1 GB, one worker; Postgres 2 CPU; Redis 1 GB with a password and no encryption (stand-in for Memorystore Basic). Code: single-use refresh tokens, per-IP and per-email limits, friendly 429. Scripts: `rig/run_retest_redis.sh`, `rig/run_spike_ab.sh`. Raw numbers: `out_retest_redis/`. Compare with `RETEST_2026-10-28.md` (same code path, no Redis, before the security fixes).

## Load scenarios (typical / slowest 5% / slowest 1%, ms)
| Scenario | Before (no Redis) | Now (Redis) | Failed before | Failed now |
|---|---|---|---|---|
| Steady 11 req/s, 5 min | 22 / 47 / 120 | 22 / 60 / 130 | 0 | 0 |
| Ramp 1 to 100 req/s | 9 / 27 / 120 | 9 / 30 / 140 | 409 | 402 |
| 300 patients in 30 s | 86 / 360 / 550 | 150 / 610 / 930 | 0 | 0 |
| 300 logins in 5 min | 5 / 210 / 480 | 6 / 210 / 390 | 0 | 0 |
| 10 doctors reviewing | 14 / 52 / 120 | 14 / 46 / 130 | 0 | 0 |
| 100 weight logs in 60 s + 50 browsing | 9 / 22 / 29 | 9 / 22 / 33 | 0 | 0 |
| Weekly cron during steady traffic | 23 / 86 / 190 | 21 / 60 / 100 | 0 | 0 |
| **New:** 300 patients rotating refresh tokens every 20 s | n/a | 11 / 370 / 1,100 | n/a | 0 of 11,772 |
| **New:** attacker flood next to normal traffic | n/a | see below | n/a | 0 of 74,980 |

- Ramp: the 402 failures are all `429` from the app's own limit of 10 plan generations per hour per IP. The test's users reopen the Meals tab again and again, which real patients do not. See "What this showed about plan generation" below.
- Refresh storm: 5,744 refreshes, all succeeded; a refresh takes about 12 ms typically (79 ms average). The slow tail (slowest 5% 380 ms) is the 300 logins (about 205 ms of password hashing each) in the first two minutes.

## Redis vs no Redis: the 300-patient spike, repeated 2 times each, alternating
| Run | Typical / slowest 5% / slowest 1% (ms) | Failed |
|---|---|---|
| Redis 1 | 130 / 700 / 1,100 | 0 of 5,700 |
| In-memory 1 | 96 / 420 / 620 | 0 |
| Redis 2 | 110 / 650 / 1,000 | 0 |
| In-memory 2 | 150 / 690 / 1,100 | 0 |

The same setup varies from 96 to 150 ms typical and 420 to 690 ms slowest 5% between runs, as much as the gap between Redis and no Redis. **No Redis cost can be shown from this data**, and it also cannot be ruled out: Redis runs average slightly worse (slowest 5%: 675 vs 555 ms) with only 2 runs each. The limiter's Redis client waits for each answer before the server does anything else, and here Redis is on the same machine (about 0.1 ms away). Memorystore will be 1 to 2 ms away, so each limited request would wait roughly 10 to 20 times longer. Only logins, signups and plan generation are limited, so I expect a small effect, but this rig cannot measure it.

## Attacker flood (40 attacker users + 50 normal users)
- 240 attacker requests per second (120 hitting one email from many IPs, 120 hitting many emails from one IP). Every one was answered 401 or 429; nothing crashed or errored.
- The server CPU averaged 80%. Normal requests slowed from about 22 ms typical to about 180 ms typical (still no errors).
- So a refused request is not free: it still costs about 3 ms of server CPU. A real flood is best stopped before it reaches the app (Cloud Armor rate limit at the load balancer; needs GCP).

## Single requests (one at a time)
Patient, doctor and admin login: 205 to 211 ms before, 211 to 213 ms now. All other endpoints unchanged within noise.

## Plan generation: fixed and re-tested
The patient app called `POST /diet-plans/generate` once each time the Meals screen opened, even when this week's plan was already stored. The server returned the stored plan in about 27 ms, but the 10-per-hour per-IP limit still counted the call, so shared IPs would hit it and the ramp test showed 402 refusals.

Fix (commit `6ecb380`): the app reads the stored plan first and calls `generate` only when it is not this week's; the server counts the limit (10 per hour, per patient) only for real generations, never for reuse.

| Ramp 1 to 100 req/s, 10 min | Typical / slowest 5% / slowest 1% (ms) | Failed | API CPU avg / p95 |
|---|---|---|---|
| Before (per IP, every call counted) | 9 / 30 / 140 | 402 of 30,765 | 35% / 64% |
| After the fix | 11 / 100 / 290 | **0 of 30,877** | 39% / 74% |

The slower tail is the work the refused calls used to skip: the 1,210 `generate` calls now return the stored plan (23 ms on average, 499 ms at worst) instead of being turned away.

## What this does not tell us
- Docker's CPU limit is not Cloud Run's real CPU: treat times as about plus or minus 30%.
- Redis ran on the same machine; real Memorystore is 1 to 2 ms away.
- Pool of 5+5 database connections is an assumption; the staging value is still unknown.
- Spike runs vary a lot (see above); single runs of that scenario should not be compared.
