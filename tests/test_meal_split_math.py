"""Stage 1 regression tests: TDEE buffer applied exactly once (no double 0.85 discount)."""
from dotenv import load_dotenv

load_dotenv()  # meal_generator import chain reaches app.core.database, which requires DATABASE_URL

from app.services.meal_generator.meal_generator import DEFAULT_SPLIT, compute_meal_targets


def test_default_split_tdee_2000():
    targets = compute_meal_targets(2000, DEFAULT_SPLIT)
    assert targets["Breakfast"] == 500
    assert targets["Lunch"] == 700
    assert targets["Dinner"] == 500
    buffer = 2000 - sum(targets.values())
    assert buffer == 300
    assert sum(targets.values()) + buffer == 2000


def test_custom_doctor_split_sum_invariant():
    # Doctor override arrives as integer pcts summing to 85 (doctor.py validation),
    # divided by 100 in generate_meal_plan before reaching compute_meal_targets.
    override = {"Breakfast": 10 / 100, "Lunch": 45 / 100, "Dinner": 30 / 100}
    tdee = 2000
    targets = compute_meal_targets(tdee, override)
    assert targets == {"Breakfast": 200, "Lunch": 900, "Dinner": 600}
    buffer = tdee - sum(targets.values())
    assert buffer == 300  # 15% of full TDEE, once
    assert sum(targets.values()) + buffer == tdee
