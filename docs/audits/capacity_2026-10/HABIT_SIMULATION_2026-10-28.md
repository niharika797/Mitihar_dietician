# Ingredient-habit learning: simulation (2026-10-28)

Rig DB (1,000 synthetic patients), one Vegetarian patient who eats paneer at breakfast every day for 4 weeks.
Script: `rig/habit_simulation.py` (run with `HABIT=paneer DIET=Vegetarian`). Raw output: `habit_simulation_raw.txt`.
The rig DB was reset afterwards.

| Check | Result |
|---|---|
| Breakfast option 1 containing paneer, before vs after 4 weeks | 0 of 7 days -> 7 of 7 days |
| All 28 breakfast options containing paneer | 0 -> 10 |
| Options flagged "Your usual" in `/meal-plan/week` | 16 of 84 (the 3 most distinctive habit ingredients only) |
| Weekly job run twice | identical `ingredient_intake` |
| Weekly nutrient totals | protein 381 g, fibre 217 g, iron 45 mg, calcium 2,873 mg, 8,195 kcal; protein mostly from paneer, instant oats, green gram dal; 0 ingredients without nutrient data |
| Patient allergic to paneer | 0 paneer options served (hard filter still wins) |
| Every dish marked "avoided" (thin pool) | still 84 options (demotion, not exclusion) |
| Generation cost with habits on vs off (15 interleaved runs) | +5 to +9% time over three runs, statements 655 vs 658. Spec limit about +10% |

## Things to know

- **Option 0 changes too.** Breakfast option 0 differed on all 7 days. The cause is not the habit boost (it only touches option 1). Dishes picked 2+ times now count over 6 weeks instead of last week only, and those "preferred" dishes already boosted every option. The design text said option 0 would not change; that holds for the habit boost only.
- **First attempt was too noisy.** Counting every ingredient as a habit flagged 50 of 84 options (onion, tomato, curd). Fix: ingredients in more than 15% of verified dishes are ignored, and the rest are weighted by how rare they are across dishes.
- **Avoided dishes:** the 18 s "all dishes avoided" run is an artificial worst case (all 2,194 dishes in one list). A real avoided set was 78 dishes with no visible slowdown.
- **Simulation writes to the rig DB** because `compute_weekly_summary` commits.
- Not tested: a real device showing the badge, and the prune cron against a real Cloud Scheduler job.
