"""Pins the keyword-collision cases in categorize_ingredient().

categorize_ingredient() resolves an ingredient by LONGEST matching keyword. That
rule is what makes "Mustard seeds" (whole_spice) and "Mustard leaves" (vegetable)
both work off a shared bare "mustard" keyword -- but it also means adding a short
keyword can silently hijack a longer-named ingredient into the wrong category,
with the wrong max_g and therefore the wrong calories.

Every case below is one that actually broke, or that a plausible future keyword
addition would break. No DB required.
"""

import pytest

from scripts.sanity_check_ingredients import (
    categorize_ingredient,
    check_count_vs_grams,
    check_not_food,
)


def cat(name: str) -> str:
    rule = categorize_ingredient(name)
    return rule.name if rule else "UNCATEGORIZED"


@pytest.mark.parametrize("name,expected", [
    # Cooking oils: bare "oil" (3 chars) loses to "coconut"/"sesame"/"mustard",
    # so each needs an explicit "<seed> oil" entry. Getting this wrong filed
    # Mustard oil under powder_spice and capped it 45g -> 10g.
    ("Mustard oil", "oil_fat"),
    ("Coconut oil", "oil_fat"),
    ("Sesame oil", "oil_fat"),
    ("Sunflower oil", "oil_fat"),
    ("Ghee", "oil_fat"),
    # ...while the seeds/flesh themselves stay put
    ("Mustard seeds", "whole_spice"),
    ("Mustard leaves", "vegetable"),
    ("Mustard", "powder_spice"),
    ("Coconut", "nut_seed"),
    ("Coconut milk", "dairy_milk"),
    ("Sesame seeds", "nut_seed"),

    # "butter" would otherwise swallow buttermilk into oil_fat
    ("Buttermilk", "dairy_curd"),
    ("Butter", "oil_fat"),

    # "long" = laung = clove, but must not steal longer-named ingredients
    ("Long", "whole_spice"),
    ("Long garlic", "aromatic"),
    ("Long green brinjal", "vegetable"),

    # US vs British spelling -- both must resolve, and powders must beat wholes
    ("Green chili", "aromatic"),
    ("Green chilli", "aromatic"),
    ("Red chili powder", "powder_spice"),
    ("Red chilli powder", "powder_spice"),

    # curry leaves are their own category (5g tempering cap), not the 30g herb cap
    ("Curry leaves", "curry_leaf"),
    ("Coriander leaves", "fresh_herb"),

    # bare/plural forms that were uncategorized before the vocabulary pass
    ("Bay leaves", "whole_spice"),
    ("Bay leaf", "whole_spice"),
    ("Rye", "whole_spice"),
    ("Cumin", "powder_spice"),
    ("Cumin seeds", "whole_spice"),
    ("Cumin powder", "powder_spice"),
    ("Poha", "cereal_grain"),
    ("Green bell pepper", "vegetable"),
    ("Tofu", "dairy_paneer"),
    ("Raisins", "fruit"),

    # substring false-positives: "oil" hides inside these, they must NOT be oil_fat
    ("Boiled peanuts", "nut_seed"),
    ("semoila", "cereal_grain"),

    # prepared condiments -- a portion is a spoonful, not a bowl
    ("Green chutney", "condiment_sauce"),
    ("Pachranga pickle", "condiment_sauce"),
    ("Soy sauce", "condiment_sauce"),
    ("Vanilla extract", "condiment_sauce"),
    ("Del monte tandoori mayo", "condiment_sauce"),

    # liquid bases -- mostly water, so a 240g glass is fine
    ("Chamomile tea", "beverage_liquid"),
    ("Vegetable stock", "beverage_liquid"),
    ("Lime juice", "beverage_liquid"),
    # ...but "tea leaves" is a dry herb, not a drink
    ("Tea leaves", "fresh_herb"),

    # regional names that were uncategorized and therefore uncapped
    ("Kadhi leaves", "curry_leaf"),      # curry leaves, spelled kadhi
    ("Kandathipli", "whole_spice"),      # Tamil long pepper, used by the pinch
    ("Mor milagai", "aromatic"),         # sun-dried curd chilli
    ("Rabodi", "pulse_legume"),          # Rajasthani dried-lentil sheets
    ("Green channa sprouts", "pulse_legume"),
])
def test_category(name, expected):
    assert cat(name) == expected


def _flag_checks(name: str, qty: float) -> set:
    return {f.check for f in check_not_food({"ingredient_name": name, "quantity_g": str(qty)})}


def test_non_food_rows_are_flagged_for_deletion():
    """Coal/charcoal (dhungar smoking) and toothpicks were ingested as ingredient
    rows with real gram values -- 1,980g of phantom weight and calories across the
    dataset. There is no correct quantity for a toothpick, so these must be
    flagged for DELETION rather than capped to a plausible-looking number."""
    assert _flag_checks("Coal", 16.0) == {"not_food"}
    assert _flag_checks("Charcoal", 80.0) == {"not_food"}
    assert _flag_checks("Toothpicks", 348.5) == {"not_food"}
    # real food is untouched
    assert _flag_checks("Coconut", 50.0) == set()


def test_parse_garbage_is_flagged_but_only_on_exact_name():
    """Fragments the recipe parser left behind ("Green", "Save", "1/2"). Matched
    on the WHOLE name so real ingredients containing the word are unaffected."""
    assert _flag_checks("Green", 68.7) == {"parse_garbage"}
    assert _flag_checks("Save", 120.0) == {"parse_garbage"}
    assert _flag_checks("1/2", 8.0) == {"parse_garbage"}
    # substring must NOT trigger it
    assert _flag_checks("Green chilli", 8.0) == set()
    assert _flag_checks("Green bell pepper", 80.0) == set()
    assert _flag_checks("Curry leaves", 2.0) == set()


def test_non_food_and_garbage_stay_uncategorized():
    """They must have no category rule, so the rebuild's cap pass skips them and
    leaves quantity_g_corrected blank instead of inventing a value."""
    for name in ("Coal", "Toothpicks", "Green", "Save", "Spoon", "1/2"):
        assert cat(name) == "UNCATEGORIZED"


def _count_flags(name: str, qty: float) -> list:
    row = {"ingredient_name": name, "quantity_g": str(qty)}
    return [f for f in check_count_vs_grams(row) if f.check == "count_as_grams"]


def test_count_check_uses_longest_keyword():
    """Regression: "clove" (sensible max 2g) matched "Cloves garlic" before the
    longer "cloves garlic" (max 25g) did, flagging correct 15g garlic rows as
    parsing bugs. Same collision that crushed garlic to 1.0g in the DB."""
    assert _count_flags("Cloves garlic", 15.0) == []
    assert _count_flags("Cloves garlic", 25.0) == []
    # a real clove row is still caught at the tight threshold
    assert _count_flags("Cloves", 160.0)
    # and genuinely absurd garlic still trips its own (looser) threshold
    assert _count_flags("Cloves garlic", 240.0)


def test_count_check_still_catches_the_original_bug():
    assert _count_flags("Curry leaves", 640.0)
    assert _count_flags("Green chillies", 160.0)
    assert _count_flags("Bay leaf", 160.0)
    # ...and leaves corrected values alone
    assert _count_flags("Curry leaves", 2.0) == []
    assert _count_flags("Green chillies", 8.0) == []


def test_curry_leaf_cap_is_tighter_than_generic_herb():
    """Regression: a flat 30g fresh_herb cap let 25g curry-leaf rows (~125-250
    leaves) pass silently. Research SS3K puts one tempering at 1-2g."""
    curry = categorize_ingredient("Curry leaves")
    herb = categorize_ingredient("Coriander leaves")
    assert curry.max_g == 5
    assert curry.max_g < herb.max_g
