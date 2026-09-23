-- Clear staging's three content tables so the already-deduped local dump can be
-- restored into them.
--
-- Must run BEFORE `alembic upgrade head`: the pending uq_fi_canonical migration
-- cannot build against staging's pre-dedup duplicate rows (see that migration's
-- own docstring).
--
-- Guarded: aborts if anything actually references food_items/ingredients, so a
-- CASCADE can never silently eat patient data. Verified 2026-08-04 that all
-- guard tables are empty on staging; the guard is here so this stays safe if
-- re-run later when they aren't.

DO $$
DECLARE
    t   text;
    n   bigint;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'weekly_combos', 'recommendations', 'patient_meal_choices',
        'patient_dish_preferences', 'meal_logs', 'meal_ratings',
        'doctor_meal_overrides'
    ] LOOP
        IF to_regclass('public.' || t) IS NULL THEN
            RAISE NOTICE 'guard %: table does not exist, skipping', t;
            CONTINUE;
        END IF;
        EXECUTE format('SELECT COUNT(*) FROM %I', t) INTO n;
        IF n > 0 THEN
            RAISE EXCEPTION
                'ABORT: % has % rows -- wiping content tables would cascade into patient data', t, n;
        END IF;
        RAISE NOTICE 'guard %: 0 rows, ok', t;
    END LOOP;
END $$;

-- Order matters: recipe_ingredients FKs both others, and
-- ingredients <- recipe_ingredients is RESTRICT (not CASCADE).
DELETE FROM recipe_ingredients;
DELETE FROM food_items;
DELETE FROM ingredients;
