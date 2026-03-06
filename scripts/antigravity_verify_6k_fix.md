# Antigravity Prompt — Verify fix_6k_calories.py Results

## Context
`fix_6k_calories.py` was just run against the PostgreSQL DB (`mityahar_db`).
It re-parsed all `source='6k_dataset'` rows from the original CSV ingredient
strings using ingredient-aware cup weights (flour=120g/cup, dal=192g/cup etc.),
re-fetched USDA nutrition, and updated the DB.

Your job is to verify the fix worked correctly. Run all checks below using the
PostgreSQL MCP connection.

---

## Check 1 — Calorie range is now realistic

```sql
SELECT
    ROUND(AVG(cal_per_serving), 1)  AS avg_cal,
    ROUND(MIN(cal_per_serving), 1)  AS min_cal,
    ROUND(MAX(cal_per_serving), 1)  AS max_cal,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cal_per_serving) AS median_cal,
    COUNT(*)                         AS total_rows
FROM food_items
WHERE source = '6k_dataset';
```

**Pass criteria:**
- `avg_cal` is between **200 and 600** kcal/serving
- `min_cal` is above **30** (no zero-cal rows slipped through)
- `max_cal` is below **1200** (CAL_CAP — anything above should have been deleted)

If `avg_cal` is still above 800, the fix did not run properly or the script
still has a bug. Report the exact numbers found.

---

## Check 2 — No zero or negative calorie rows

```sql
SELECT id, recipe_name, cal_per_serving, source
FROM food_items
WHERE source = '6k_dataset'
  AND cal_per_serving <= 0
ORDER BY cal_per_serving;
```

**Pass criteria:** 0 rows returned.

---

## Check 3 — Slot distribution is sensible

```sql
SELECT slot_type, COUNT(*) AS count
FROM food_items
WHERE source = '6k_dataset'
GROUP BY slot_type
ORDER BY count DESC;
```

**Pass criteria:**
- `grain`, `sabzi`, `dal_protein` should each have > 30 rows
- `snack_item` should have > 20 rows
- No slot_type should be NULL or empty string

---

## Check 4 — Diet type distribution

```sql
SELECT diet_type, COUNT(*) AS count
FROM food_items
WHERE source = '6k_dataset'
GROUP BY diet_type
ORDER BY count DESC;
```

**Pass criteria:**
- `Vegetarian` has the most rows (expected ~70% of total)
- `Non-Vegetarian` and `Eggetarian` are also present
- No rows with diet_type = `NULL` or unrecognized strings

---

## Check 5 — ingredients JSONB was updated (not just calories)

```sql
SELECT
    recipe_name,
    cal_per_serving,
    jsonb_array_length(ingredients) AS ingredient_count,
    ingredients->0 AS first_ingredient
FROM food_items
WHERE source = '6k_dataset'
ORDER BY cal_per_serving DESC
LIMIT 5;
```

**Pass criteria:**
- `ingredient_count` is > 0 for all rows
- `first_ingredient` shows `{"name": "...", "amount_g": ...}` format
- `amount_g` values look reasonable (e.g. 120 for "1 cup flour", not 240)

---

## Check 6 — Total food_items count across all sources

```sql
SELECT source, is_verified, COUNT(*) AS count
FROM food_items
GROUP BY source, is_verified
ORDER BY source, is_verified;
```

**Expected output:**
```
 source       | is_verified | count
--------------+-------------+-------
 6k_dataset   | false       |  ???   ← should be 150–308 after deletions
 excel        | true        |  184
 manual       | true        |  ???   ← if any manual entries exist
```

Report the exact numbers. If `6k_dataset` count dropped to below 50, that
indicates the fix deleted too aggressively and we need to review the CAL_CAP.

---

## Check 7 — Calorie breakdown by slot type (generator health check)

```sql
SELECT
    slot_type,
    ROUND(AVG(cal_per_serving), 0) AS avg_cal,
    ROUND(MIN(cal_per_serving), 0) AS min_cal,
    ROUND(MAX(cal_per_serving), 0) AS max_cal,
    COUNT(*) AS count
FROM food_items
WHERE is_verified = true OR source = '6k_dataset'
GROUP BY slot_type
ORDER BY avg_cal DESC;
```

**Pass criteria (slot calorie ranges the generator expects):**
- `grain`: avg 150–350 kcal
- `dal_protein`: avg 100–300 kcal
- `sabzi`: avg 50–200 kcal
- `snack_item`: avg 50–200 kcal
- `main_dish` (breakfast): avg 150–400 kcal
- `accompaniment`: avg 30–150 kcal
- `beverage`: avg 30–150 kcal

If any slot avg is above 600, report the slot and the top 3 offending recipes by name.

---

## Summary report format

After running all checks, produce a table:

| Check | Status | Notes |
|-------|--------|-------|
| 1 — Avg calorie range | ✅ / ❌ | avg=XXX |
| 2 — No zero-cal rows  | ✅ / ❌ | N rows found |
| 3 — Slot distribution | ✅ / ❌ | missing slots if any |
| 4 — Diet distribution | ✅ / ❌ | unexpected values if any |
| 5 — JSONB ingredients updated | ✅ / ❌ | sample first_ingredient |
| 6 — Row counts by source | ✅ / ❌ | exact counts |
| 7 — Slot calorie ranges | ✅ / ❌ | any outlier slots |

If ALL checks pass → "Dataset fix verified. Ready for generator testing."
If ANY check fails → report which check failed and the exact query output.
