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
2. [ ] N+1 queries: weekly-summary (79 queries), shopping-list (28), streak.
3. [ ] Weekly cron `complete-expired-plans` takes ~58 s.
4. [ ] `weekly_combos` growth and retention.
5. [ ] `/meal-plan/adjust` times out at 10 s. Cause not traced.
6. [ ] DB pool of 5+5 saturates under load.
7. [ ] Gemini endpoints have no timeout.
8. [ ] 19 endpoints never timed.
9. [ ] Profile screen sends `target_weight_kg` and `phone`, which the backend ignores.

## 4. Testing gaps
- [ ] Expo web app freezes on the first real click (cause unknown). The backend `/docs` page takes clicks fine.
- [ ] `full_backend_test.py` and `security_verification_test.py` fail on admin/doctor credential mismatch (74/158 before, 75/158 after). Fix the test credentials, then compare again.
- [ ] Run the new 409 toast on a device or emulator.

## 5. Known results to compare against
Report: `docs/audits/capacity_2026-10/REPORT_1vCPU_API_2vCPU_DB.md`. Median 5.4 ms, login ~210 ms, plan generation 1.0-1.6 CPU-s, ceiling ~80-100 requests/s on 1 vCPU.
