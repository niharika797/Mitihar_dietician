# Session 22D — Audit/Design Findings (Bug 2 `scaled_calories` impact map · Beverage reclassification · Confirm-choice schema)

**Date:** 2026-06-12
**Type:** Audit/design only — zero production code changed, zero migrations, zero data writes.
**Inputs:** `docs/session22c_audit_findings.md`, live DB (read-only), full code-path greps.
**Audit scripts (throwaway):** `scripts/audit_22d/q1_inventory.py` (templates / beverage pool / active recs / choices), `q2_combo_rerun.py` (combo math with beverage removed), `q3_misc.py` (beverages table, template `required` flags).

---

## Part 1 — Bug 2: `dishes[].scaled_calories` impact map

**Decision being designed:** `dishes[].calories` stays unscaled per-serving. New persisted field `dishes[].scaled_calories = calories × factor` written at generation. Slot header becomes `Σ(scaled_calories)`.

### 1.1 Recommendation up front: persist `factor` AND a per-slot `Target Calories`, not just `scaled_calories`

Two additions beyond the brief, both cheap at generation time, both resolving downstream problems found below:

1. **Persist `dishes[].factor` alongside `scaled_calories`.** `scaled_calories` alone covers the header, but scaled protein/carbs/fat/fiber (already summed scaled into `Total Protein` etc.) cannot be reconstructed per dish without the factor, and the dish object stays internally inconsistent (scaled ingredients, unscaled macros, scaled calories). One float fixes it permanently; frontends can derive any scaled macro on demand.
2. **Persist `"Target Calories"` on each meal slot.** Today `Total Calories` plays two roles: display header AND `slot_calorie_target` for suggestions (`meal_plan.py:373`). Changing the header to `Σ(scaled_calories)` silently changes Bug 6's ranking target the moment a clamp binds, a pin lands, or a doctor edits. Writing the slot's budget target (`meal_target × Σslot_pcts` — in practice just `meal_target`) as its own field at generation decouples the two permanently. This directly answers 22C open question 2: **Bug 6 reads `Target Calories`; Bug 2 redefines `Total Calories`; no coupling remains.**

### 1.2 Code-path inventory

| # | Location | Current behavior | Proposed (22E) |
|---|---|---|---|
| W1 | `meal_generator.py:360` | writes `dishes[].calories` = unscaled `cal_per_serving` | **stays** unscaled; add `scaled_calories = round(cal × factor, 2)` and `factor` |
| W2 | `meal_generator.py:367` | `Total Calories += cal × factor` (≡ slot target when clamp doesn't bind) | becomes `Σ(scaled_calories)` — same loop, same number at generation, except clamp-bound slots now show truth; also write new `"Target Calories"` field |
| W3 | `meal_generator.py:398-414` (pinned injection) | pinned dish has no factor, `ingredients: []`, **never added to totals**; displaced dish's contribution stays in totals | pinned dish gets `factor=1.0`, `scaled_calories=calories`, **included** in Σ; displaced dish's contribution removed (recompute Σ from final `dishes[]` instead of accumulating — kills both halves of the 22C pinned bug at once). Also populate its `ingredients` ×1.0 (currently empty — separate pre-existing gap) |
| W4 | `doctor.py:893-898` (custom dish add recalc) | `Total Calories = Σ(unscaled calories)` — flips header basis | `Σ(d.get("scaled_calories", d.get("calories", 0)))` — fallback keeps legacy dishes working; `Target Calories` untouched |
| W5 | `doctor.py:1078-1083` (PATCH swap/remove/add recalc) | same unscaled-sum flip; note: PATCH-created dishes have **no `ingredients` key** (pre-existing display gap) | same fix as W4; new dishes get `factor=1.0`, `scaled_calories=calories` |
| W6 | `doctor.py:1264-1276` (`assign_recipe`) | creates a **new meal slot with no `dishes[]` at all** (legacy shape, top-level `food_id`, `Total Calories = cal_per_serving`) | out of strict scope but flag: this is a 4th slot shape; 22E should at least write a 1-dish `dishes[]` with `factor=1.0` so the new world has one shape fewer |
| R1 | `meal_plan.py:373` (suggestions `slot_calorie_target`) | reads `Total Calories` (= budget target today) | switch to `meal.get("Target Calories")`, fallback to current logic for legacy plans |
| R2 | `meal_plan.py:485` (confirm-choice) | writes unscaled `cal_per_serving` into `patient_meal_choices.calories`; budget math at `:385/:513` subtracts it from TDEE | under Bug 6 combos: write Σ over combo dishes. Scaled vs unscaled is 22C Q7 (still open) — budget should subtract what the patient is told to eat; if combos stay unscaled, store unscaled sums |
| R3 | `doctor.py:1128` | returns `total_calories` after PATCH | follows W5 automatically |
| F1 | `PlanTab.tsx:333` (slot kcal pill) | shows `Total Calories` | shows `Σ(scaled_calories)` (i.e. the redefined field); optionally "target X" second line when divergent (see 1.3a) |
| F2 | `PlanTab.tsx:798/874` + `:511/520` (day total vs TDEE banner) | sums `Total Calories` — today this is `Σ targets ≈ 0.85·TDEE`, so the banner always reads "~15% below TDEE" regardless of dishes | no code change needed beyond the field redefinition; banner becomes truthful for the first time |
| F3 | `PlanTab.tsx:114` (DishCard kcal) | shows unscaled `dish.calories` | show `scaled_calories ?? calories` — must match the ingredient grams shown next to it (which ARE scaled) |
| F4 | patient `meal-detail.tsx:83` (per-dish card kcal) | unscaled `dish.calories` next to **scaled** ingredient grams — visibly inconsistent today | `scaled_calories ?? calories` |
| F5 | patient `meal-detail.tsx:245/292` (header + combined summary) | `Total Calories` | follows field redefinition; no code change |
| F6 | patient `meal-detail.tsx:187` ("I Had This" → `meal_logs.calories_consumed`) | logs `Total Calories` (= target) as consumed | follows redefinition: logs `Σ(scaled_calories)` = what the plate actually contains. **This silently improves consumption accuracy** — flag in 22E verification |
| F7 | patient `index.tsx:281` (quick-log from plan), `log-from-plan.tsx:22` (prefill) | same `Total Calories` basis | same as F6, automatic |
| F8 | patient `meals.tsx:312`, `index.tsx:380/426` (plan card displays) | `Total Calories` | automatic |
| F9 | `doctorApi.ts:107` (`'Total Calories': number` type) | — | add optional `scaled_calories`, `factor`, `'Target Calories'` to the Dish/Meal types (both frontends' `types/index.ts` too) |
| — | `progress_service.py` | only sums `meal_logs.calories_consumed`; never reads dishes | no change (input shifts via F6/F7) |
| — | `diet_plans.py` validator | counts slots only | no change |

### 1.3 Edge cases

**(a) Clamp-bound slots** (factor pinned at 0.5 or 3.0 — e.g. 22C's Priya 06-16 Dinner: one_pot at 98 kcal/serving, target 396.7, factor capped at 3.0 → `Σ(scaled_calories)` = ~294 + accomp, not 396.7).
With both fields persisted the UI can show divergence honestly. Recommendation: **show only `Σ(scaled_calories)` by default; add a second line "target ~X kcal" (patient) / amber warning icon with tooltip (doctor) only when `|Σ − Target| / Target > 10%`.** "Plan provides 294, target 397" reads fine to a patient *once*; showing it on every slot (where the gap is 1–3%) is noise. The doctor-side warning doubles as a data-quality flag — a slot that can't reach target even at 3.0× usually means a too-small dish was picked (98 kcal one_pot is itself suspect). **PO decision: threshold + patient-facing wording.**

**(b) Doctor-added custom dishes** (`is_custom_override=True`, JSONB-only).
The doctor types macros for the portion they intend the patient to eat — the entered calories already *are* the portion. **Recommendation: `factor=1.0`, `scaled_calories = calories`. No portion input needed.** A portion-size field can be added later without schema impact (it would just change the factor). No open question unless PO disagrees with the semantics.

**(c) Doctor PATCH swap/add.**
Options: (i) fresh factor against the slot's remaining target, (ii) default 1.0. **Recommendation: `factor=1.0`.** Reasons: a doctor swap is a curated decision — silently rescaling the replacement's ingredients to chase a target second-guesses the doctor; "remaining target" is ill-defined after the first edit (which dish's sub-pct does the new dish inherit? one-pot vs standard shapes differ); and with the header now being an honest Σ, the doctor sees the calorie consequence immediately and can react. After a swap the slot's `Σ(scaled_calories)` is recomputed from the final `dishes[]` (W5) — it is a sum, recalculated against nothing; `Target Calories` stays as the generation-time budget for reference/warning. **PO confirm: accept that doctor-edited slots may drift from target with only a warning indicator.**

**(d) Pinned dishes.**
**Recommendation: `factor=1.0`** — the dish was pinned deliberately; scaling a pinned Chai to 2.4 servings to fill a sub-target nobody assigned it is worse than an honest overshoot. Pin has no slot pct to scale against anyway (it displaces whatever was last, across differing slot shapes). With W3, pinned dishes finally appear in the header and the displaced dish's ghost contribution disappears. Slot may legitimately exceed/undershoot target → handled by the same divergence treatment as (a).

**(e) Existing plans / backfill.**
Three active recommendations exist: **156 (patient 4), 165 (Priya), 166 (Ruchit)** — all 21 slots, all with `dishes[]`, none with `scaled_calories`. Backfill *is* technically computable for untouched generator output (slot shapes are known: Breakfast 70/20/10, standard 35/28/22/15, one-pot 70/30 — recover `factor = clamp(target×pct / cal)` per dish), but it breaks on doctor-edited slots and any pin-displaced slot, and these are all test patients. **Recommendation: forward-only — no backfill migration. Regenerate the 2–3 test plans in 22E (every recent session regenerates anyway).** Interim/legacy UI rule, one line in each frontend: *use `Σ(scaled_calories)` only if every dish in the slot has the field; otherwise display the stored `Total Calories` exactly as today.* Per-dish: `scaled_calories ?? calories`. **PO confirm: forward-only acceptable for any real-patient plans that exist at rollout time** (today: none — all active plans are test accounts).

### 1.4 Collateral findings (not fixed, log only)

- PATCH-created dishes carry no `ingredients` key (`doctor.py:999-1009/1043-1053`) — swapped dishes render with no ingredient list in both apps.
- Pinned dishes are written with `ingredients: []` (`meal_generator.py:408`).
- `assign_recipe` (`doctor.py:1264`) creates dishes[]-less slots — a shape both frontends only partially handle (legacy read-only path).
- The PlanTab "below TDEE" banner (F2) has been tautological since Session 11 (it compares the target-sum to TDEE); the Bug 2 fix makes it meaningful — worth a glance in 22E verification that the messaging still makes sense.

---

## Part 2 — Beverage reclassification: blast radius

### 2.1 Current beverage participation — full inventory

**Templates (DB `meal_templates.slots`, 180 rows):**

| meal_time | slot shape | beverage? |
|---|---|---|
| Breakfast (36 rows — all of them) | main_dish 0.70 (req) / accompaniment 0.20 (req) / **beverage 0.10 (required: false)** | **yes — only here** |
| Lunch (36) | grain 0.35 / dal_protein 0.28 / sabzi 0.22 / accompaniment 0.15 | no |
| Dinner (36) | same as Lunch | no |
| Morning/Evening_Snack (72) | snack_item 1.0 | no (dead since Session 11) |
| ONE_POT_SLOTS (in-code, 22B) | one_pot 0.70 / accompaniment 0.30 | no |

**The brief's premise that beverages pair into Lunch/Dinner combos is wrong in a useful way:** Chaas, Lassi, Masala Chaas, Dahi — the items 22C combos paired with one_pots — are `slot_type='accompaniment'`, not `'beverage'`. Beverage-the-slot-type participates in Breakfast only, optional, 10% of the slot budget (= 40–54 kcal sub-target for these patients).

**food_items with `slot_type='beverage'`: 24 rows total.**

| reachable by generation? | items | cal range |
|---|---|---|
| Breakfast-tagged (live pool) — 10 | Chai/Coffee/Milk ×2 (45.8), Filter Coffee (73.2), Chai (84.5), Banana Shake (109.6), Gulkand Chai (111.7), Espresso (119.1), Piyush (130), Kumbakonam Filter Coffee (146.4), Raab (147) | 45.8–147 |
| Lunch/Dinner-tagged — 9 | dead rows: no L/D template has a beverage slot (incl. **Buttermilk Soup id 591 at 2857.7 kcal — data error**, and Spiced Beetroot Buttermilk 403.6, also suspect) | 35–2857.7 |
| Snack-tagged — 5 | dead since Session 11 | 35–198.6 |

No "real-macro" beverage (protein shake etc.) exists in the DB; everything reachable is ≤147 kcal. In the 3 active plans, beverage dishes are exactly 7 per plan (one per Breakfast), 45.75–84.45 kcal each. **Calorie stakes of removal are small and confined to Breakfast.**

**Redistribute vs shrink.** Removing the 0.10 pct without redistribution shrinks every breakfast by 10% (= 2.5% of daily effective intake) — a silent clinical change. **Recommendation: redistribute within Breakfast to main 0.78 / accompaniment 0.22** (i.e. 0.70/0.90 and 0.20/0.90 — preserves the 7:2 ratio and the meal target). Combo math below confirms it works. **PO confirm (open question d).**

**Mechanism note:** templates are DB rows, but 22B set the precedent of in-code slot-list overrides (`ONE_POT_SLOTS`). Removing beverage can be a generator-side `BREAKFAST_SLOTS` constant (no migration, one file) rather than a 36-row JSONB update. Recommend in-code; the DB templates would then be partially shadowed — note it in code comments.

**Other touchpoints checked:** suggestions endpoint has no beverage-specific logic (Bug 6 rebuild simply omits beverage from combo slot lists); both frontends render `dishes[]` generically (beverage rows just disappear from breakfast cards — no beverage UI exists yet; Session 23's "beverage category UI" was never built); `beverages` standalone table from Session 10 **exists and has 0 rows** — never wired up. The locked product decision ("Beverages: separate manageable category, not tied to meal slots") already points the same direction as this reclassification; the empty table is available if PO wants a real catalog, but the meal_logs route below needs no new table.

### 2.2 Doctor-prescribed exception — does a mechanism exist?

**Yes: `PatientDishPreferences` pin (Session 17), and it structurally works for beverages** — pin injection checks `meal_time_tags`, so a Breakfast-tagged beverage pins into every Breakfast slot. Three caveats:

1. **It inherits the 22C pinned-totals bug** — pinned dish never added to `Total Calories`, displaced dish's contribution remains. The W3 fix in Part 1 resolves this for free (pinned beverage gets factor=1.0, counted in Σ).
2. **Displacement quirk:** at slot capacity the pin evicts `dishes[-1]`. Post-removal Breakfast has 2 dishes (main, accomp), so a pinned chai would evict the accompaniment, not add alongside. 22E needs a rule: pinned beverage *appends* (slot grows to 3) rather than displaces — small generator change, only sensible if beverage exits the standard slot list.
3. **A pin is per-(patient, dish), applied to every compatible slot** — a pinned beverage appears all 7 days. That matches "doctor prescribes a daily protein shake" fine.

**(a) vs (b):** recommendation **(a) — occupy a slot via pin, doctor-only.** It exists today, costs ~10 lines (append rule), and with Part 1's W3 the calories count correctly toward the visible plan. Option (b) (supplement-style, outside the slot structure) means a new table + new patient UI + new budget integration for a use case (genuinely caloric prescribed beverages) that currently has **zero rows in the DB**. Defer (b) until a real protein-shake catalog exists. **PO confirm (open question e).**

### 2.3 Patient-logged tea/coffee — current implementation

There is **no literal tea/coffee feature**; the analog is the Session 21 **Snack quick-log**: `index.tsx:260-272` → `POST /progress/log/meal` with `meal_type="Snack"` + free-entered calories → a `meal_logs` row. Confirmed fully separate from `recommendations.meals`/`dishes[]` and from `patient_meal_choices`: it lives in the consumption ledger, hits `calories.consumed` in `/progress/today`, and never touches the plan or the plan-time budget.

**Can DB-backed beverages fold into this pattern? Yes, two flavors:**

- **(i) Zero-backend:** add beverage presets to the snack sheet (Chai 85 / Coffee 73 / Chaas 45 / Lassi 129 buttons). Free-text style, loses `food_id` linkage. ~20 lines of patient UI.
- **(ii) DB-linked:** a beverage picker listing `food_items WHERE slot_type='beverage'` (or the empty `beverages` table, seeded from those 24 rows), logging via the same endpoint with `MealLog.food_id` set (column exists, nullable, already used by log-from-plan). Keeps traceability for the doctor weekly summary. Modest UI + one list endpoint.

Either way **no schema change is needed** — `meal_logs` already supports both shapes. Recommend (ii) if doctor reporting on beverages matters, else (i). **PO pick.**

### 2.4 Impact on Bug 6 combo-building (re-run, `q2_combo_rerun.py`)

**Lunch/Dinner: zero impact — verified.** Priya 06-12 Lunch (one_pot+accomp, target 555.4) re-run reproduces the 22C table exactly (Dal Chawal 371 + Chaas 90 = 461, −16.9% … Lilva khichdi + Koshimbir = 343, −38.3%), because no beverage was ever in these combos. The "unscaled combos can't hit large targets" viability flag is **neither helped nor hurt** — it remains exactly as scoped in 22C, and neither one_pot nor accompaniment absorbs anything new.

**Breakfast: the burden shifts to the main, and it holds.** Priya (target 396.7):

| Scenario | Top combos | vs target |
|---|---|---|
| A — today (main+accomp+bev 70/20/10) | Masala Dosa+Dahi+Chai/Coffee/Milk 368 · Appam+Dahi Bowl+Filter Coffee 395 · Idli+Dressing+Banana Shake 391 · (4th: Dhokla+Sambar+Gulkand Chai 580) | −7.3% / −0.4% / −1.4% / +46% |
| B — bev removed, redistributed 78/22 | Semiya Upma+Dahi 352 · Raw Banana Paratha+Dahi Bowl 364 · Poha+Dressing 332 · Sweet Corn Upma+Sambar 474 | −11.4% / −8.3% / −16.3% / +19.5% |
| C — bev removed, target shrunk ×0.90 | same combos | −1.5% / +1.9% / −6.9% / +32.8% |

Ruchit Breakfast (537.7, Eggetarian mains, pool of only **7**): best 571 (+6.1%), then +16.7%/+30.4%/+34.0% — high-TDEE breakfasts get rougher without the beverage's flexible 10%, but the main pool (229 veg / 7 egg) was always the constraint, not the beverage. Conclusion: **beverage removal is combo-viable; scenario B's ±10–20% spread is the same order as the 22C breakfast results (±90 kcal).** The accompaniment pool of 4 (and 22C flag #2, small-pool repetition) remains the binding issue; scenario C *looks* tighter only because the target dropped 10% — that's the redistribute-vs-shrink decision, not better math.

**Definitional risk to settle before 22E:** 5 of Priya's 8 lunch accompaniment candidates are drinkable dairy (Chaas ×2, Masala Chaas, Dahi, Lassi). If "beverages drop out of generation" is meant in the *patient-perception* sense (anything you drink), it would also strip these `accompaniment` rows and gut the lunch/dinner accompaniment pool to ~3 items, breaking one_pot combos. **Recommendation: scope strictly to `slot_type='beverage'`; Chaas/Raita/Dahi stay accompaniments.** **PO confirm (open question g).**

---

## Part 3 — Confirm-choice schema for whole-meal combos

### 3.1 Current schema (`patient_meal_choices`, migration c9d0e1f2a3b4)

```
id            SERIAL PK
patient_id    INT NOT NULL FK patients(id) ON DELETE CASCADE
food_item_id  INT NOT NULL FK food_items(id) ON DELETE CASCADE
date          DATE NOT NULL
meal_type     VARCHAR(20) NOT NULL
calories      FLOAT NULL          -- dish cal_per_serving at confirmation
confirmed_at  TIMESTAMPTZ DEFAULT NOW()

UNIQUE (patient_id, date, meal_type)   -- uq_pmc_patient_date_meal (upsert anchor)
INDEX (patient_id, date)               -- idx_pmc_patient_date
```

Session 20 budget math reads only `SUM(calories) WHERE patient, date` (`meal_plan.py:378/:507`); weekly variety reads `food_item_id WHERE patient, date >= week_start` (`:347`); `/choices/{date}` joins food_items for recipe_name. Current contents: 5 stale test rows (patient 2, 06-09/06-10) — migration of existing data is a non-issue.

### 3.2 Option A — JSONB `chosen_dishes` column

`ALTER TABLE patient_meal_choices ADD COLUMN chosen_dishes JSONB NOT NULL DEFAULT '[]'; ALTER COLUMN food_item_id DROP NOT NULL;` Row-level `calories` becomes the combo total (budget math **unchanged, zero code touched**). Array elements: `{food_id, recipe_name, slot_type, calories}` — same shape as `recommendations.meals[].dishes[]`, so both frontends reuse the existing `Dish` type and the `/choices/{date}` response barely changes.

- **Migration complexity:** one ALTER, no new table, no FK churn. Upsert stays a single `ON CONFLICT DO UPDATE` (just adds one column to `set_`).
- **Read-back ("what did the patient choose on date X"):** one row, no joins — names snapshotted in the JSONB (snapshot semantics are arguably *more* correct for a historical choice log than live joins).
- **Budget math:** untouched — still `SUM(calories)` on the parent row.
- **Weekly variety:** the only real cost. SQL-side needs `jsonb_array_elements`/GIN expression index, but the suggestions endpoint already pulls ≤21 rows per patient-week into Python — unpacking member food_ids in Python is a 3-line change to the existing loop.
- **Cons:** no FK integrity on member food_ids (acceptable for a snapshot log); SQL aggregation over chosen dishes (future doctor weekly summary, Session 22-planned) is uglier though workable.

### 3.3 Option B — child table `patient_meal_choice_dishes`

`(id PK, choice_id INT NOT NULL FK patient_meal_choices(id) ON DELETE CASCADE, food_item_id INT NOT NULL FK, slot_type VARCHAR, calories FLOAT)`; parent keeps `calories` as the combo total (budget math unchanged), `food_item_id` dropped or kept as anchor.

- **Migration complexity:** one new table + index; parent column decision adds churn.
- **Upsert complexity:** the real cost — `ON CONFLICT DO UPDATE` no longer covers it; re-confirming a meal needs *delete old children + insert new* inside the transaction (or a MERGE dance). The endpoint grows a second statement and a failure mode.
- **Read-back:** JOIN + GROUP BY or two queries; recipe_name via live join (no snapshot, names drift if recipes renamed).
- **Weekly variety / future analytics:** clean indexed SQL, FK integrity — the one place B genuinely wins.

### 3.4 Recommendation

**Option A.** Reasons, in order of weight:

1. **Session 20 budget code is untouched by A** (parent `calories` stays the summed source of truth) — B can match this only by keeping the same denormalized parent column, at which point the child table buys nothing for the budget path.
2. **Symmetry with `dishes[]`** — the platform already stores meal compositions as JSONB dish arrays; choices are confirmations *of* those arrays. One shape everywhere, shared types, shared rendering.
3. **Upsert semantics stay one statement.** The (patient, date, meal_type) uniqueness is the core invariant; A preserves the existing constraint-driven upsert exactly.
4. Choices are an immutable-ish snapshot log; FK integrity and live joins (B's advantages) are mismatched to that — today's FK CASCADE actually *deletes history* when a food_item is removed, which JSONB snapshotting quietly fixes.

No blocker found in Session 20 code that forces either option. **A is also unambiguously the easier change to scope into 22E** (one ALTER + ~15 endpoint lines + 3-line variety loop change vs new table + rewritten upsert + join changes). The only future fact that would flip this to B: doctor weekly-summary analytics being specced as heavy SQL aggregation over individual chosen dishes — and even then a GIN index on `chosen_dishes` is a credible middle ground.

---

## Open questions for product owner (decide before 22E)

| # | Question | Recommendation on file |
|---|---|---|
| a | **Clamp-divergence UI:** second-line "target ~X kcal" (patient) + amber warning (doctor) only when divergence > threshold — what threshold (10%?) and wording? | 10%, Σ-only below it |
| b | **Factor for non-generated dishes:** confirm `factor=1.0` for doctor custom dishes, PATCH swaps/adds, and pinned dishes (doctor sees honest Σ, no silent rescaling) | yes to all three |
| c | **Backfill:** forward-only `scaled_calories` + regenerate the 3 active test plans; legacy slots keep old header display via fallback. OK? | forward-only |
| d | **Beverage pct redistribution:** Breakfast 0.70/0.20/0.10 → 0.78/0.22 (target preserved) vs shrink (breakfast −10%, daily −2.5%)? | redistribute |
| e | **Prescribed-beverage mechanism:** pin-based (slot grows to 3, counts in Σ via the Bug 2 fix) vs separate supplement-style tracking? | pin-based, defer supplement model |
| f | **Confirm-choice schema:** Option A (JSONB `chosen_dishes`) vs Option B (child table)? | A |
| g | **Beverage scope:** strictly `slot_type='beverage'` (Chaas/Dahi/Lassi remain accompaniments and stay in lunch combos) — confirm the reclassification does NOT extend to drinkable accompaniments | strict slot_type |
| h | **Patient beverage logging:** snack-sheet presets (free-text, zero backend) vs DB-linked beverage picker (food_id traceability for doctor summary)? | (ii) DB-linked if doctor reporting matters |
| i | **New persisted fields:** confirm adding `dishes[].factor` and slot-level `"Target Calories"` alongside `scaled_calories` (decouples Bug 6's target from the header permanently — resolves 22C Q2) | yes |

**Carried over, still open from 22C:** Q7 (scale combos in suggestions vs accept ±30% on 2-dish slots for high-TDEE patients — interacts with R2 above), Q6/pool expansion (accompaniment pools of 4–8 remain the visible-repetition constraint for combo suggestions), Q8 data cleanups (Test Dal Tadka 3676/3677, Chicken Biryani avoid_diabetes — explicitly out of this session's scope, still pending; **also add Buttermilk Soup id 591 at 2857.7 kcal to that cleanup list**).
