# Session 22C — Diagnostic Audit Findings (Bug 2 + Bug 6)

**Date:** 2026-06-12
**Type:** Audit/diagnosis only — no production code changed.
**Data sources:** active recommendations 165 (Priya, patient 2) and 166 (Ruchit, patient 3); live calls to `GET /api/v1/meal-plan/suggestions/{date}/{meal_type}`; food_items pool queries.
**Audit scripts (throwaway, not for app use):** `scripts/audit_22c/part1_divergence.py`, `part2_suggestions.py`, `part3_combo_sim.py`, `misc_checks.py`.

---

## Part 1 — Bug 2: Calorie Display Divergence

### Code-path trace

| What | Where | Basis |
|---|---|---|
| `stored_total` (slot header value) | `meal_generator.py:367` — `meal_option["Total Calories"] += cal_per_serving * factor` | **Scaled.** `factor = target_cal / cal_per_serving` (`:328`), clamped to [0.5, 3.0] (`:332`), where `target_cal = meal_target × slot calorie_pct` (`:305`) |
| `dishes[].calories` | `meal_generator.py:360` — `"calories": float(food_item.cal_per_serving)` | **Unscaled** — raw per-serving DB value, factor never applied |
| `dishes[].ingredients[].amount_g` | `meal_generator.py:347` — `round(float(_raw) * factor, 1)` | **Scaled** — same dish object mixes scaled ingredients with unscaled macros |
| UI slot header | `PlanTab.tsx:333` — `value={meal['Total Calories']}` | Displays stored_total directly |
| UI day total | `PlanTab.tsx:798` — sums `meal['Total Calories']` | Same basis |
| Doctor dish PATCH recalc | `doctor.py:893` and `doctor.py:1078` — `slot["Total Calories"] = sum(d.get("calories", 0) for d in dishes)` | **Unscaled** — a doctor edit silently flips the slot header from target-basis to unscaled-sum-basis |
| Pinned dish injection | `meal_generator.py:398-414` | Pinned dish appended to `dishes[]` but its calories are **never added** to `Total Calories`; the displaced dish's scaled contribution **stays** in the total. (No pins active for either test patient, so not visible in the tables below — but it's a third divergence source in code.) |

### Key empirical finding: stored_total is the slot *target*, not a sum

Because per-slot `calorie_pct` values sum to 1.0 (Breakfast 0.70/0.20/0.10; one-pot 0.70/0.30; standard templates likewise), `Σ(cal × target/cal) = meal_target` exactly whenever the [0.5, 3.0] clamp doesn't bind. The clamp never bound in any of the 42 audited slots, so:

- **Priya (TDEE 1866.91, no split override):** every Breakfast/Dinner slot stores exactly **396.7** (= 1866.91 × 0.85 × 0.25), every Lunch exactly **555.4** (× 0.35).
- **Ruchit (TDEE 2530.38):** every Breakfast/Dinner **537.7**, every Lunch **752.8**.

The header is literally static across all 7 days — this is the observed Bug 2 symptom.

### Divergence table — Priya (rec 165)

| Date | Meal | Composition | stored | dish_sum | div | div% |
|---|---|---|---|---|---|---|
| 06-11 | Breakfast | main+accomp+bev | 396.7 | 296.6 | +100.1 | +33.8% |
| 06-11 | Lunch | standard 4-dish | 555.4 | 520.3 | +35.1 | +6.7% |
| 06-11 | Dinner | one_pot+accomp | 396.7 | 373.7 | +23.1 | +6.2% |
| 06-12 | Breakfast | main+accomp+bev | 396.7 | 387.7 | +9.1 | +2.3% |
| 06-12 | Lunch | one_pot+accomp | 555.4 | 461.4 | +94.0 | +20.4% |
| 06-12 | Dinner | standard 4-dish | 396.7 | 472.2 | −75.5 | −16.0% |
| 06-13 | Breakfast | main+accomp+bev | 396.7 | 334.5 | +62.2 | +18.6% |
| 06-13 | Lunch | standard 4-dish | 555.4 | 568.5 | −13.1 | −2.3% |
| 06-13 | Dinner | standard 4-dish | 396.7 | 625.4 | −228.7 | −36.6% |
| 06-14 | Breakfast | main+accomp+bev | 396.7 | 409.7 | −13.0 | −3.2% |
| 06-14 | Lunch | standard 4-dish | 555.4 | 742.9 | −187.5 | −25.2% |
| 06-14 | Dinner | one_pot+accomp | 396.7 | 367.5 | +29.2 | +8.0% |
| 06-15 | Breakfast | main+accomp+bev | 396.7 | 324.2 | +72.6 | +22.4% |
| 06-15 | Lunch | one_pot+accomp | 555.4 | 568.9 | −13.5 | −2.4% |
| 06-15 | Dinner | one_pot+accomp | 396.7 | 426.7 | −30.0 | −7.0% |
| 06-16 | Breakfast | main+accomp+bev | 396.7 | 436.4 | −39.7 | −9.1% |
| 06-16 | Lunch | standard 4-dish | 555.4 | 655.9 | −100.5 | −15.3% |
| 06-16 | Dinner | one_pot+accomp | 396.7 | 150.4 | +246.3 | +163.8% |
| 06-17 | Breakfast | main+accomp+bev | 396.7 | 436.4 | −39.7 | −9.1% |
| 06-17 | Lunch | one_pot+accomp | 555.4 | 575.1 | −19.7 | −3.4% |
| 06-17 | Dinner | standard 4-dish | 396.7 | 345.3 | +51.4 | +14.9% |

### Divergence table — Ruchit (rec 166)

| Date | Meal | Composition | stored | dish_sum | div | div% |
|---|---|---|---|---|---|---|
| 06-11 | Breakfast | main+accomp+bev | 537.7 | 474.3 | +63.4 | +13.4% |
| 06-11 | Lunch | standard 4-dish | 752.8 | 717.1 | +35.7 | +5.0% |
| 06-11 | Dinner | one_pot+accomp | 537.7 | 463.8 | +73.9 | +15.9% |
| 06-12 | Breakfast | main+accomp+bev | 537.7 | 701.0 | −163.3 | −23.3% |
| 06-12 | Lunch | standard 4-dish | 752.8 | 661.4 | +91.4 | +13.8% |
| 06-12 | Dinner | standard 4-dish | 537.7 | 499.9 | +37.8 | +7.6% |
| 06-13 | Breakfast | main+accomp+bev | 537.7 | 928.1 | −390.4 | −42.1% |
| 06-13 | Lunch | one_pot+accomp | 752.8 | 550.6 | +202.2 | +36.7% |
| 06-13 | Dinner | standard 4-dish | 537.7 | 535.8 | +1.9 | +0.3% |
| 06-14 | Breakfast | main+accomp+bev | 537.7 | 806.5 | −268.8 | −33.3% |
| 06-14 | Lunch | one_pot+accomp | 752.8 | 666.6 | +86.2 | +12.9% |
| 06-14 | Dinner | one_pot+accomp | 537.7 | 461.4 | +76.3 | +16.5% |
| 06-15 | Breakfast | main+accomp+bev | 537.7 | 474.3 | +63.4 | +13.4% |
| 06-15 | Lunch | standard 4-dish | 752.8 | 683.7 | +69.1 | +10.1% |
| 06-15 | Dinner | standard 4-dish | 537.7 | 435.4 | +102.4 | +23.5% |
| 06-16 | Breakfast | main+accomp+bev | 537.7 | 474.3 | +63.4 | +13.4% |
| 06-16 | Lunch | standard 4-dish | 752.8 | 624.3 | +128.5 | +20.6% |
| 06-16 | Dinner | standard 4-dish | 537.7 | 572.9 | −35.2 | −6.1% |
| 06-17 | Breakfast | main+accomp+bev | 537.7 | 474.3 | +63.4 | +13.4% |
| 06-17 | Lunch | standard 4-dish | 752.8 | 751.8 | +1.0 | +0.1% |
| 06-17 | Dinner | one_pot+accomp | 537.7 | 436.1 | +101.6 | +23.3% |

### Patterns

1. **No TDEE split override correlation possible** — neither patient has a `meal_split_override` row; stored side is fully determined by `TDEE × 0.85 × default split`. Any patient with an override would just get different constants.
2. **slot_type correlation exists but is secondary.** One-pot slots skew stored > dish_sum (Priya mean ratio 1.265, Ruchit 1.211) because 2 unscaled servings usually sum below the slot target. Ruchit's Breakfasts skew the other way (ratio min 0.58) because his egg mains are 583–716 kcal per serving vs a 376 kcal sub-target — the generator scales portions *down* ~0.55×, which the unscaled dish sum ignores.
3. **Not a single consistent ratio.** Per-slot ratios range 0.58–2.64. Each dish gets its own factor, so no uniform correction can reconcile the two numbers.
4. **Near-zero divergence slots are coincidence** (Ruchit 06-13 Dinner +0.3%, 06-17 Lunch +0.1%): the picked dishes' per-serving calories happened to land near their sub-targets (factors ≈ 1.0). Nothing structural distinguishes them.
5. **Worst case observed:** Priya 06-16 Dinner — one_pot dish stored at 98 kcal/serving; header says 396.7, dishes sum to 150.4 (+163.8%). The generator's intent is "eat 2.8 servings of this"; nothing in the stored plan or UI conveys that.

### Verdict

**Two genuinely different calorie bases, both legitimate — plus one real data gap.**

- `Total Calories` = the slot's **calorie budget/target** (what the patient should eat). It is correct as a budget number and is exactly what the suggestions endpoint uses as `slot_calorie_target` (`meal_plan.py:373`).
- `dishes[].calories` = **per-serving nutrition at 1.0 serving**. Also correct, as far as it goes.
- The real defect is that the **portion factor is discarded** after generation: it's baked into `dishes[].ingredients[].amount_g` (scaled) but not stored anywhere as a number, and per-dish macros are stored unscaled. So the same dish object is internally inconsistent (scaled ingredients, unscaled macros), the UI can't reconstruct "target = Σ(dish × factor)", and the doctor PATCH recalc (`doctor.py:893/1078`) writes unscaled sums into a field that everywhere else means "scaled target" — silently changing the header's meaning after any dish edit.
- This is **not** a one-line missed scaling step. The fix decision is: persist per-dish `factor` (or scaled per-dish macros) at generation time, and pick one basis for the header (or show both: "target 555 kcal / plan provides 568 kcal"). Doctor PATCH must then recalc on the same basis.

---

## Part 2 — Bug 6: Current Suggestions Behavior

Live endpoint output (backend running, real patient tokens), 3 slots per patient. `slot_calorie_target` confirmed sourced from `recommendations.meals[i]["Total Calories"]` (`meal_plan.py:368-374`) — i.e. the **whole-slot budget** from Part 1.

### Priya (diabetic, vegetarian-leaning)

**06-12 Lunch — plan: one_pot + accompaniment, target 555.4**

| Suggestion | slot_type | kcal | Notes |
|---|---|---|---|
| Test Dal Tadka (id 3676) | dal_protein | 276.0 | **Test artifact leaked to patient** |
| Test Dal Tadka (id 3677) | dal_protein | 276.0 | Duplicate of the above |
| Paneer Karaikudi | dal_protein | 433.6 | Standalone gravy as a whole lunch |
| Chicken Biryani | one_pot | 421.9 | **Non-veg + known missing `avoid_diabetes` tag (Session 18A finding) served to a diabetic** |

If "Test Dal Tadka" (276 kcal) replaces the one_pot anchor in the 2-dish slot: 276 + 90 (Chaas) = 366 vs 555 target (−34%). Taken as the whole meal: −50% of target.

**06-13 Dinner — plan: 4-dish standard, target 396.7** — suggestions are 3 one_pot dishes + 1 dal_protein (363–434 kcal). As whole-meal swaps these are calorically plausible, but they are presented as single dishes against a 4-dish slot; swapping one of the 4 dishes for e.g. Chicken Biryani (421.9) yields 625 − 164 + 422 ≈ 883 kcal vs 397 target (+123%).

**06-13 Breakfast — plan: main+accomp+beverage, target 396.7** — returns `grain` items (Meethi paratha, Sattu Paratha) and main_dishes sized to the whole 397 kcal target; the slot's actual main_dish sub-target is 0.70 × 397 ≈ 278 kcal.

### Ruchit (no conditions)

**06-13 Lunch — one_pot+accomp, target 752.8** — best candidates max out at 433.6 kcal (−42% vs target): the pool simply has no single 753 kcal dish, so calorie-proximity ranking returns the 4 largest-ish dishes regardless of fit. Also returns "Missi paratha" tagged `sabzi` as a whole lunch.

**06-15 Dinner — standard 4-dish, target 537.7** — all 4 suggestions are one_pot/dal_protein in the 434–512 range; same whole-vs-part confusion.

**06-14 Breakfast — target 537.7** — Sattu Paratha (`grain`), Mysore Bonda, Banana Filos, Paneer Wrap — single dishes at 368–430 kcal vs a composed 3-dish slot.

### Severity verdict

**Actively breaks the adaptive-budget feature — not cosmetic.** Concretely:

1. **Unit mismatch poisons the budget math.** `confirm-choice` writes the single dish's calories as the whole meal's consumption. Confirming "Test Dal Tadka" (276) against a 555 kcal lunch slot leaves `calories_remaining_today` overstated by ~279 kcal *if the patient actually eats a full meal*, or the patient genuinely eats a 276 kcal lunch — either way the budget and the plate disagree.
2. **Composition is ignored**: dal-only or sabzi-only "meals" with no carb base; one_pot dishes offered as partial swaps for 4-dish slots; no accompaniment ever suggested alongside.
3. **slot_type is unconstrained** — the query (`meal_plan.py:389-402`) filters only `is_verified` + `meal_time_tags` + avoid_tags; any slot_type ranks.
4. **Collateral data findings:** `Test Dal Tadka` ×2 (ids 3676/3677 — the Session 16 "Doctor2 Private Dal" artifact family, `is_verified=True` so they pass the filter) shown to a real patient; Chicken Biryani still missing `avoid_diabetes` (Layer-2/3 tag gap flagged in Session 18A, confirmed still live).
5. The single redeeming property: `slot_calorie_target` itself is the *correct* budget number (Part 1) — the ranking target is right, the things ranked against it are the wrong unit.

---

## Part 3 — Bug 6 Simulation: Whole-Meal-Combo Approach

Two candidate sources simulated for the same 6 slots (script: `part3_combo_sim.py`):

**Source A — ready-made combos from the patient's own plan week** (other days, same meal type, from `recommendations.meals`): always composition-correct, zero extra query cost, but only ≤6 alternatives exist per slot and they collide with the weekly-variety exclusion (they ARE the rest of the week's plan).

**Source B — fresh combos from slot_type pools**, generator-style: each slot_type pool filtered by `meal_time_tags`, diet, patient avoid_tags; ranked by proximity to `target × calorie_pct`; rank-i items paired across slots. Sample results:

**Priya 06-12 Lunch (one_pot+accomp, target 555)** — pools: one_pot 58, accompaniment 8

| Combo | Sum | vs target |
|---|---|---|
| Dal Chawal (371) + Chaas (90) | 461 | −94 |
| Millet Khichdi (321) + Masala Chaas (45) | 366 | −190 |
| Rajma Chawal (315) + Chaas (45) | 360 | −196 |
| Lilva khichdi (311) + Koshimbir (32) | 343 | −213 |

**Priya 06-13 Dinner (4-dish, target 397)** — pools: grain 47, dal 282, sabzi 786, accomp 11

| Combo | Sum | vs target |
|---|---|---|
| Steamed rice + Dal tadka + Shimla Mirch Launji + Masala Chaas | 404 | +8 |
| Bhakri + Banana Apple Mash + Aloo baingan + Masala chaas | 407 | +10 |
| Chawal + Rasam + Kachumber Salad + Chaas | 414 | +18 |
| Roti + Malabar Curry + Kachumber Salad + Koshimbir | 381 | −16 |

**Ruchit 06-13 Lunch (one_pot+accomp, target 753)** — pools: one_pot 65, accomp 12

| Combo | Sum | vs target |
|---|---|---|
| Savoury Oatmeal Porridge (538) + Lassi (129) | 667 | −86 |
| Varan Bhat (541) + Chaas (90) | 631 | −122 |
| Moong Dal Khichdi (485) + Cucumber Raita (72) | 557 | −195 |
| Mixed Millet Khichdi (479) + Vegetable raita (53) | 532 | −221 |

(Breakfast combos and Ruchit Dinner combos in script output — 4-dish combos land within ±20 kcal of target; breakfast within ±90.)

### Viability note

**Implementable, with three flagged issues for scoping:**

1. **Unscaled combos can't hit large targets.** A 753 kcal one_pot lunch target is unreachable: the biggest one_pot serving is ~541 kcal. The generator solves this with the portion factor (eat 1.4 servings); a combo-suggestion engine must either (a) carry the same per-dish scaling (which re-imports Bug 2's "what does calories mean" question), or (b) accept ±30% misses on 2-dish slots for high-TDEE patients. 4-dish combos hit targets within ±5% without any scaling because four small degrees of freedom are enough.
2. **Small pools get worse, not better.** Accompaniment pools after diet+condition filters: Priya breakfast accomp = 4, beverage = 6; Ruchit breakfast accomp = 5. Every suggested combo must include an accompaniment, so 3–4 combos will visibly share/recycle the same Raita/Chaas/Dahi — the known small-pool repetition issue becomes more visible in the suggestion UI than it is in the weekly plan. Pool expansion is a soft prerequisite for the suggestions to *look* varied.
3. **Cost is fine.** Source B is one indexed query per slot_type (2–4 queries) + in-memory pairing — same order as the current single query. No combinatorial explosion as long as pairing is rank-based, not exhaustive.
4. Caveat: the simulation allowed all of Ruchit's diet types in pools; the real generator applies the non-veg weekly budget (Session 22A), which would shrink his non-veg combo availability somewhat.
5. `confirm-choice` and `patient_meal_choices` are single-`food_item_id` shaped (one row per meal, UNIQUE(patient, date, meal_type), one FK). Whole-meal-combo confirmation needs either a JSONB dish list on the row or a child table — schema change, not just an endpoint rewrite.

---

## Part 4 — Boondi Tag Contradiction

**Already fixed — nothing to do.** ID 173 is an `ingredients`-table row (name "Boondi"), and Session 18C already removed the erroneous `avoid_gluten` ("Boondi contradiction resolved (avoid_gluten removed ID 173)" — BUILD_TRACKER Session 18C summary). Verified live today: `avoid_tags = []`, `prefer_tags = ["gluten_free"]`. The three boondi *recipes* in food_items (1079, 1755, 1872) all carry `gluten_free`, none carry `avoid_gluten`.

Stale doc note: BUILD_TRACKER "Post-Session 18B Technical Debt" item 5 still says the Boondi decision is "awaiting user decision" — it's resolved; that bullet can be deleted whenever that section is next touched.

---

## Open Questions for Product Owner

1. **Which basis should the slot header show?** Options: (a) keep showing the budget/target but label it "Target" and add a second "plan provides ~X kcal" line; (b) persist per-dish factor at generation and show scaled live sums everywhere; (c) show unscaled dish sums and drop the target from the header. Decision drives both the Bug 2 fix and what `dishes[].calories` should mean platform-wide.
2. **Bug 6 must target the budget number (`Total Calories` as stored today).** If Bug 2's fix changes what `Total Calories` stores (e.g. doctor-PATCH-style unscaled sums), `slot_calorie_target` in suggestions silently changes too (`meal_plan.py:373`). The two fixes must be scoped together, or Bug 6 must read the target from TDEE×split directly.
3. **Doctor PATCH recalc basis** (`doctor.py:893/1078`) writes unscaled sums into the scaled-target field. Fix alongside Bug 2, or accept that doctor-edited slots mean something different?
4. **Pinned-dish totals**: pinned dishes are excluded from `Total Calories` and the displaced dish's contribution remains (`meal_generator.py:398-414`). No active pins today, but should be folded into whichever Bug 2 fix is chosen.
5. **Whole-meal-combo confirm schema**: extend `patient_meal_choices` with a dishes JSONB (or child table)? Required before Bug 6 implementation.
6. **Pool expansion before/alongside Bug 6?** Accompaniment/beverage pools of 4–8 items make combo suggestions visibly repetitive. Recommend at least seeding more accompaniments/beverages before shipping combo suggestions.
7. **Scaling in suggestions for 2-dish slots**: accept ±30% calorie misses for high-TDEE patients, or carry per-dish portion factors into suggestions (ties back to Q1)?
8. **Data cleanups surfaced (not fixed, out of audit scope):** test artifacts ids 3676/3677 ("Test Dal Tadka", is_verified=True) are reachable by real patients via suggestions; Chicken Biryani (ids 300, 332) still lacks `avoid_diabetes` and is suggested to a diabetic patient. Both are 1-line data fixes but touch food_items — left for an approved fix session.
