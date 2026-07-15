# Stage 6 Spec

Admin, for now, is the developer account only (us) — already confirmed to
exist as a distinct role (`admins` table, `get_current_admin`,
`AdminIPWhitelistMiddleware` — traced in `docs/DISH_DUPLICATE_AUDIT.md`).
Build for a single admin today, but the role is already there for a future
doctor promotion — no new role table needed.

Audit numbers already confirmed (local dev + staging match exactly):
295 duplicate groups / 663 rows. Tier 1 exact: 144 groups, 305 rows
(~140 rows removable after excluding 3 diet-variant groups). Tier 2
conflict: 151 groups, 358 rows — 149 of these differ in both macros and
ingredients, dominant cause is the known 6k-dataset scaling issue (excel-vs-
6k rows disagreeing 2-3x), so the bottom-up recompute step in section 3
should resolve the bulk of these mechanically before any AI research is
even needed.

## Section 1 — Schema: change request + audit log

1. New table `data_change_requests`: id, target_table, target_id,
   field_changed, old_value, new_value (JSONB), proposed_by (doctor
   user_id, or `system:ai_observer`, or `system:tier1_auto`),
   proposal_reason (text), tier (`tier1_auto` / `tier2_review`), status
   (`pending`/`approved`/`rejected`/`auto_applied`), reviewed_by (admin
   user_id, nullable), reviewed_at, created_at.
2. New table `data_change_audit_log`: append-only, one row per state
   transition (proposed → reviewed → applied/rejected), full before/after
   snapshot, actor, timestamp. No UPDATE/DELETE grant on this table for the
   app's DB role — INSERT only, enforced at the DB level.
3. Alembic migrations for both.

## Section 2 — Tier 1: exact-duplicate auto-merge

1. For the 138 confirmed-safe groups (144 total minus 3 diet-variant minus
   3 test-artifact groups already handled): merge function picks the
   Verified row as canonical (else most-complete row), repoints FK
   references per the blast-radius list already documented in
   `docs/DISH_DUPLICATE_AUDIT.md` (meal_logs.food_id,
   doctor_meal_overrides, meal_ratings, patient_dish_preferences,
   patient_meal_choices, patient_meal_choice_dishes, recipe_ingredients,
   plus JSONB refs in recommendations and weekly_combos.dishes), and sets
   `deleted_at` on the duplicate (not a hard delete).
2. Every merge writes to `data_change_audit_log`,
   proposed_by=`system:tier1_auto`, status=`auto_applied`.
3. Dry-run first, print every proposed merge with both rows' full data,
   single "Y" to apply the whole batch — if any row in the batch doesn't
   look genuinely identical on inspection, exclude it and flag for Tier 2
   instead of forcing it through.
4. Add a scheduled monthly sampling check: re-verify 10% of auto-applied
   Tier 1 merges by confirming the deleted row's data really matched the
   canonical row's at merge time (from the audit log) — surface mismatches
   to the admin, don't silently pass.

## Section 3 — Tier 2: AI-researched, admin-approved conflict resolution

**Nothing in this tier auto-applies, regardless of AI confidence.**

1. For each of the 151 Tier 2 groups, and any future doctor-submitted flag
   (from section 4): create a `data_change_requests` row per proposed
   field change, status=`pending`.
2. AI research step (proposed_by=`system:ai_observer`):
   - First, recompute the dish's nutrition bottom-up from its current
     `recipe_ingredients` rows using the existing calculation service. This
     alone should resolve the ~149 groups caused by the known stale 6k-
     scaling issue.
   - Only for genuine ingredient-level conflicts remaining after recompute:
     search authoritative sources only — IFCT 2017 primary values,
     ICMR-NIN publications, and UK FCT/USDA only as fallback when an
     ingredient has no IFCT entry (matching the existing fallback chain
     per `docs/IFCT_NUTRITION_ARCHITECTURE.md`). No general web search, no
     food blogs, no calorie-tracking apps as sources for clinical values.
   - Write full reasoning + every source cited into `proposal_reason`. If
     no authoritative source resolves it, say so explicitly — leave both
     original values visible, don't pick one.
3. Admin review UI (new route under `/api/v1/admin/*`, gated on
   `Depends(get_current_admin)`): queue of pending Tier 2 requests —
   dish name, field, old value(s), AI's recomputed/sourced value + full
   reasoning/citations, Approve / Reject / Edit-and-approve. No auto-
   approve button, no confidence-based bypass, ever.
4. On approval: apply to target table, log to audit table, re-trigger the
   offline nutrition-stamping script for the affected dish, mark approved.
5. On rejection: mark rejected with admin's reason, no data change, dish
   stays flagged for manual resolution later.

## Section 4 — Frontend: Doctor-facing Data Review tab (not yet built — build this)

1. New tab in the doctor dashboard sidebar: "Data Review" — match existing
   nav conventions and component patterns already used for the Recipes tab
   in `mitihar-frontend/apps/`.
2. Read-heavy paginated list of dishes (50/100/200 per page), full
   ingredient breakdown with quantities/units (post Stage 3 schema),
   nutrition values, and source. **Filter out any row where
   `deleted_at IS NOT NULL`** — merged-away Tier 1 duplicates must not
   appear here.
3. Doctors can flag any dish/ingredient/value as "looks wrong" with a
   required reason field — creates a `data_change_requests` row,
   tier=`tier2_review`, proposed_by=doctor's user_id, status=`pending`
   (same AI research pipeline from section 3 runs on it).
4. **No direct edit-and-save on shared master data from this tab** —
   flagging is the only write action here. Existing doctor recipe
   *creation* flow is unaffected.
5. Doctors see status of requests they personally flagged
   (pending/approved/rejected + admin's reasoning if rejected), not the
   full cross-doctor audit log — that stays admin-only.
6. After building, start/confirm both backend and frontend dev servers are
   running clean (same as the earlier app-review session) so the new tab
   can actually be checked in a browser — confirm no console errors and
   give me the URL/path to it.

## Confirmed decisions (do not re-ask)

- 21 test rows deleted (ids 3697-3717) — done, this session.
- Diet-variant groups (3) stay excluded from Tier 1.
- Soft-delete via `deleted_at` already shipped (`81e7c65`) — Data Review
  tab in section 4 filters on `deleted_at IS NULL`, not `is_verified`.
