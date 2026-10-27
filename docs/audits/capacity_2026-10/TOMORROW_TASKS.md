# Tasks for next session (written 2026-10-27)

Working branch: `feature/api-remediation-v0.2` (d5dcf5e). `main` and the 3 worktree branches match it. All pushed.

## 1. Decide first
- [ ] Retest size: quick weight-fix check (~15 min) or full retest (~60 min).
- [ ] What to do with uncommitted work:
  - main worktree: 4 modified files + ~12 untracked, including `docs/audits/capacity_2026-10/` (rig, reports).
  - doctor worktree: gate scripts.
  - saha worktree: untracked files.
  - `backup/*` and `claude/silly-sutherland` branches: untouched, keep or delete?

## 2. Retest prep (needed before any run)
- [ ] Start Docker rig `mitihar-perf-api` and `mitihar-perf-pg` (stopped), rebuild API image from current tree.
- [ ] Remint tokens (`mint_tokens.py`, `mint_admin.py`). The old ones expired 2026-10-27.
- [ ] Backdate seeded patients' `created_at` by 40 days, so the 28-day weight rule does not reject the test calls.
- [ ] Change the weight-burst scenario to 100 first-time logs.

## 3. Fixes, in priority order
1. [x] Profile edit: height and activity no longer regenerate the plan (done 2026-10-28, uncommitted in `app/routers/users.py`). Diet type, health condition and region still regenerate inline on purpose. Target weight is not in the profile update schema at all (see item 9).
2. [x] N+1 queries fixed 2026-10-28: weekly-summary 92 -> 7 queries, shopping-list 23 -> 6, streak up to 15 -> 2. Output identical to the old code on the rig DB.
3. [x] Weekly cron `complete-expired-plans`: ~58 s -> 7.8-8.4 s for 1,000 patients (0 failed) on the rig, just from the N+1 fix. Still blocks the single event loop for ~8 s while it runs.
4. [ ] `weekly_combos` growth and retention.
5. [x] `/meal-plan/adjust`: not a hang. It runs a full plan generation inline: 12.8 s cold, 5.9 s warm on the dev machine. The old "timeout" was the test client's 10 s limit; the app's own limit is 30 s. Moving generation off the request is a bigger change, left for a decision.
6. [ ] DB pool: code default is 20+20; the 5+5 was the rig's assumed setting (env DB_POOL_SIZE/DB_MAX_OVERFLOW). Needs the real staging value before any change.
7. [x] Gemini: both doctor endpoints already had timeouts (20 s, 15 s). Fixed a timeout on /doctor/recipes/lookup returning 500 instead of 502. No Gemini calls exist outside doctor.py.
8. [ ] 19 endpoints never timed.
9. [x] Profile update now saves `target_weight_kg` and `phone` (validated; phone also returned by GET /users/me). Verified by replaying the app request.

## 4. Testing gaps
- [ ] Expo web app freezes on the first real click (cause unknown). The backend `/docs` page takes clicks fine.
- [x] Backend live tests fixed 2026-10-28: full_backend_test 103/103, security_verification_test 190/197 (was 75/158). Needed: TEST_ADMIN_* creds from .env, 127.0.0.1 + port 8001, 30 s timeouts, gdpr_consent, dev Redis running (docker start mityahar-redis; FLUSHDB between runs, register is limited to 3/hour). 7 left are test-vs-product drift (see commit message).
- [ ] Run the new 409 toast on a device or emulator.

## 5. Known results to compare against
Report: `docs/audits/capacity_2026-10/REPORT_1vCPU_API_2vCPU_DB.md`. Median 5.4 ms, login ~210 ms, plan generation 1.0-1.6 CPU-s, ceiling ~80-100 requests/s on 1 vCPU.
